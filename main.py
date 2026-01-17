# main.py - Modular 360 Photo Booth Entry Point
import os
import csv
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext
from datetime import datetime

from settings import load_settings, save_settings, settings, hash_password
from music import search_music, play_selected_song, stop_music, set_log_callback
from motor import init_serial, send_motor_command, close_serial
from session import start_session
from mpesa import initiate_mpesa_payment, is_valid_phone

# --- Initialize ---
load_settings()
init_serial()

root = tk.Tk()
root.title("360 Booth System")

# --- Logger / ScrolledText ---
frame = tk.Frame(root)
frame.pack(padx=10, pady=10)
log_text = scrolledtext.ScrolledText(root, width=70, height=15, state='disabled')
log_text.pack(pady=10)
countdown_label = tk.Label(root, text="Waiting...", font=("Arial", 14))
countdown_label.pack(pady=5)

def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    full = f"[{timestamp}] {msg}"
    log_text.config(state='normal')
    log_text.insert(tk.END, full + "\n")
    log_text.see(tk.END)
    log_text.config(state='disabled')
    print(full)

set_log_callback(log)  # connect music.py logging to GUI

# --- SESSION FLOW ---
last_payment_phone = None
SESSIONS_CSV = 'sessions.csv'
os.makedirs("videos", exist_ok=True)
if not os.path.exists(SESSIONS_CSV):
    with open(SESSIONS_CSV, 'w', newline='') as f:
        csv.writer(f).writerow(['timestamp', 'phone', 'song_title', 'duration', 'status', 'amount'])

def start_flow():
    global last_payment_phone
    phone = simpledialog.askstring("Payment", "Enter phone (07... or 01...):")
    if not phone: return
    phone = phone.strip()
    if phone.startswith("07") or phone.startswith("01"):
        phone = "254" + phone[1:]
    if not is_valid_phone(phone):
        messagebox.showerror("Invalid", "Invalid phone number")
        return
    if not os.path.exists("selected_song.mp3"):
        messagebox.showwarning("Missing", "Please select music first.")
        return

    amount = settings.get('price', 0)
    log(f"Initiating payment for {phone} amount {amount}")

    def payment_thread():
        try:
            success = initiate_mpesa_payment(phone, amount)
            if success:
                global last_payment_phone
                last_payment_phone = phone
                countdown_label.config(text='Payment confirmed. Starting soon...')
                threading.Thread(target=lambda: start_session('F', last_payment_phone), daemon=True).start()
            else:
                root.after(0, lambda: messagebox.showerror('Payment Failed', 'M-Pesa payment not confirmed.'))
        except Exception as e:
            log(f"[ERROR] Payment thread exception: {e}")

    threading.Thread(target=payment_thread, daemon=True).start()

# --- ADMIN SETTINGS ---
def admin_login():
    if settings.get("password") is None:
        pw = simpledialog.askstring("Set Password", "Create a password:", show='*')
        if not pw: return
        settings["password"] = hash_password(pw)
        save_settings()
        messagebox.showinfo("Password Set", "Password saved. Opening settings now.")
        open_settings()
        return

    pw = simpledialog.askstring("Admin Login", "Enter password:", show='*')
    if not pw: return
    if hash_password(pw) == settings.get("password"):
        open_settings()
    else:
        messagebox.showerror("Error", "Incorrect password")

def open_settings():
    win = tk.Toplevel(root)
    win.title("Owner Settings")

    tk.Label(win, text="Price (KES)").grid(row=0, column=0)
    entry_price = tk.Entry(win); entry_price.insert(0, settings.get("price", 0)); entry_price.grid(row=0, column=1)
    tk.Label(win, text="Till Number").grid(row=1, column=0)
    entry_till = tk.Entry(win); entry_till.insert(0, settings.get("till_number", '')); entry_till.grid(row=1, column=1)
    tk.Label(win, text="Recording Time (s)").grid(row=2, column=0)
    entry_record_time = tk.Entry(win); entry_record_time.insert(0, settings.get("record_time", 10)); entry_record_time.grid(row=2, column=1)
    tk.Label(win, text="Email").grid(row=3, column=0)
    entry_email = tk.Entry(win); entry_email.insert(0, settings.get("email", '')); entry_email.grid(row=3, column=1)

    def save_and_close():
        try:
            settings["price"] = float(entry_price.get())
            settings["till_number"] = entry_till.get()
            settings["record_time"] = int(entry_record_time.get())
            settings["email"] = entry_email.get()
            save_settings()
            win.destroy()
            log('Settings saved')
        except Exception as e:
            messagebox.showerror('Save Error', str(e))

    tk.Button(win, text="Save", command=save_and_close).grid(row=4, column=0, columnspan=2, pady=10)

# --- UI BUTTONS ---
tk.Button(frame, text="Search Music", command=search_music).grid(row=0, column=0, padx=5)
tk.Button(frame, text="Start Session", command=start_flow).grid(row=0, column=1, padx=5)
tk.Button(frame, text="Admin", command=admin_login).grid(row=0, column=2, padx=5)

# --- START ---
log('System ready')
root.mainloop()
close_serial()
