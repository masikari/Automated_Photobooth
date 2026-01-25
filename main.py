
import os
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext
import csv
import random
import string
import subprocess

from settings import (
    load_settings,
    save_settings,
    settings,
    hash_password,
    is_locked,
    register_failed_attempt,
    reset_failed_attempts
)

from logger import log, set_ui_callback
from music import search_music
from session import start_session
from email_service import send_recovery_email, send_session_email
from mpesa import initiate_mpesa_payment, is_valid_phone
from motor import init_serial
from webcam import open_camera_preview

#FIXED IMPORTS
from share import (
    share_via_whatsapp,
    login_whatsapp,
    get_last_video
)

#INITIALIZATION
load_settings()
init_serial()

root = tk.Tk()
root.title("360 Booth System")

frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

log_text = scrolledtext.ScrolledText(root, width=70, height=15, state="disabled")
log_text.pack(pady=10)

countdown_label = tk.Label(root, text="Waiting...", font=("Arial", 14))
countdown_label.pack(pady=5)

#LOGGER
def ui_log(msg):
    log_text.config(state="normal")
    log_text.insert(tk.END, msg + "\n")
    log_text.see(tk.END)
    log_text.config(state="disabled")

set_ui_callback(ui_log)

#ADMIN FUNCTIONS
def admin_login():
    if settings.get("password") is None:
        pw = simpledialog.askstring("Set Admin Password", "Create password:", show="*")
        if not pw:
            return
        settings["password"] = hash_password(pw)
        save_settings()
        messagebox.showinfo("Saved", "Admin password set")
        return

    if is_locked():
        messagebox.showerror("Locked", "Too many failed attempts.\nTry again later.")
        return

    pw = simpledialog.askstring("Admin Login", "Enter password:", show="*")
    if not pw:
        return

    if hash_password(pw) == settings.get("password"):
        reset_failed_attempts()
        open_settings()
    else:
        register_failed_attempt()
        messagebox.showerror("Denied", "Incorrect password")

def change_password():
    old = simpledialog.askstring("Change Password", "Old password:", show="*")
    if not old:
        return

    if hash_password(old) != settings.get("password"):
        messagebox.showerror("Error", "Incorrect old password")
        return

    new = simpledialog.askstring("Change Password", "New password:", show="*")
    if not new:
        return

    settings["password"] = hash_password(new)
    save_settings()
    messagebox.showinfo("Success", "Password changed")

def recover_password():
    email = settings.get("email")
    if not email:
        messagebox.showerror("Error", "Admin email not set")
        return

    temp_pw = "".join(random.choices(string.ascii_letters + string.digits, k=8))
    settings["password"] = hash_password(temp_pw)
    settings["lock_until"] = 0
    reset_failed_attempts()
    save_settings()

    if send_recovery_email(email, temp_pw):
        messagebox.showinfo("Success", "Temporary password sent to admin email")
    else:
        messagebox.showerror("Email Error", "Failed to send email")

# ======== ADMIN SETTINGS GUI ========
def open_settings():
    win = tk.Toplevel(root)
    win.title("Admin Settings")

    tk.Label(win, text="Amount per Session (KES)").grid(row=0, column=0)
    e_price = tk.Entry(win)
    e_price.insert(0, settings.get("price", 0))
    e_price.grid(row=0, column=1)

    tk.Label(win, text="Till Number").grid(row=1, column=0)
    e_till = tk.Entry(win)
    e_till.insert(0, settings.get("till_number", ""))
    e_till.grid(row=1, column=1)

    tk.Label(win, text="Recording Time (seconds)").grid(row=2, column=0)
    e_time = tk.Entry(win)
    e_time.insert(0, settings.get("record_time", 10))
    e_time.grid(row=2, column=1)

    tk.Label(win, text="Admin Email").grid(row=3, column=0)
    e_email = tk.Entry(win)
    e_email.insert(0, settings.get("email", ""))
    e_email.grid(row=3, column=1)

    def save_and_close():
        try:
            settings["price"] = float(e_price.get())
        except ValueError:
            settings["price"] = 0

        settings["till_number"] = e_till.get()

        try:
            settings["record_time"] = int(e_time.get())
        except ValueError:
            settings["record_time"] = 10

        settings["email"] = e_email.get()
        save_settings()
        log("Settings updated")
        win.destroy()

    tk.Button(win, text="Save", command=save_and_close)\
        .grid(row=4, column=0, columnspan=2, pady=5)

    def login_whatsapp_button():
        threading.Thread(target=login_whatsapp, daemon=True).start()
        messagebox.showinfo("WhatsApp", "WhatsApp Web opened.\nScan QR code if required.")

    tk.Button(win, text="Login WhatsApp", command=login_whatsapp_button)\
        .grid(row=5, column=0, columnspan=2, pady=5)

# ======== SESSION CSV ========
if not os.path.exists("sessions.csv"):
    with open("sessions.csv", "w", newline="") as f:
        csv.writer(f).writerow(["timestamp", "phone_number", "duration", "price"])

def replay_last_video():
    video = get_last_video()
    if not video:
        log("No recorded video to replay")
        return
    subprocess.run(["xdg-open", video])

#SESSION FLOW
def on_session_complete(phone, amount):
    log(f"Session completed for {phone}, amount {amount}")
    if not send_session_email(phone, amount):
        log("[EMAIL] Failed to send session notification")

def start_flow():
    phone = simpledialog.askstring("Payment", "Enter phone (07... or 01...):")
    if not phone:
        return

    phone = phone.strip()
    if phone.startswith(("07", "01")):
        phone = "254" + phone[1:]

    if not is_valid_phone(phone):
        messagebox.showerror("Invalid", "Invalid phone number")
        return

    if not os.path.exists("selected_song.mp3"):
        messagebox.showwarning("Missing", "Select music first")
        return

    amount = settings.get("price", 0)
    log(f"Initiating payment for {phone} amount {amount}")

    def pay():
        try:
            if initiate_mpesa_payment(phone, amount):
                start_session(
                    root,
                    countdown_label,
                    phone,
                    on_complete=lambda: on_session_complete(phone, amount)
                )
            else:
                messagebox.showerror("Payment Failed", "Payment not confirmed")
        except Exception as e:
            log(f"[ERROR] Payment exception: {e}")

    threading.Thread(target=pay, daemon=True).start()

#SHARE VIA WHATSAPP
def share_last_session():
    client_phone = simpledialog.askstring(
        "Share via WhatsApp",
        "Enter client WhatsApp number (2547...)"
    )
    if not client_phone:
        return

    client_phone = client_phone.strip()
    if client_phone.startswith(("07", "01")):
        client_phone = "254" + client_phone[1:]

    #NO DOUBLE THREADING
    share_via_whatsapp(client_phone)

#MENU BAR 
menubar = tk.Menu(root)
root.config(menu=menubar)

settings_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="Settings", menu=settings_menu)

settings_menu.add_command(label="Admin", command=admin_login)
settings_menu.add_command(label="Change Password", command=change_password)
settings_menu.add_command(label="Forgot Password", command=recover_password)
settings_menu.add_separator()
settings_menu.add_command(label="Exit", command=root.quit)

#BUTTONS
tk.Button(frame, text="Music", command=search_music)\
    .grid(row=0, column=0, padx=5)

tk.Button(frame, text="Start", command=start_flow)\
    .grid(row=0, column=1, padx=5)

tk.Button(frame, text="Camera", command=lambda:
    threading.Thread(target=open_camera_preview, daemon=True).start()
).grid(row=0, column=2, padx=5)

tk.Button(frame, text="Replay", command=lambda:
    threading.Thread(target=replay_last_video, daemon=True).start()
).grid(row=0, column=3, padx=5)

tk.Button(frame, text="Share", command=share_last_session)\
    .grid(row=0, column=4, padx=5)

#START
log("System ready")
root.mainloop()
