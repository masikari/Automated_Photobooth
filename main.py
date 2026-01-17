# Central entry point for Automated_Photobooth
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox

from settings import load_settings, save_settings, settings, verify_password, set_password
from logger import log, set_ui_callback, log_session
from music import search_music, preview_song, select_song, play_selected_song, stop_music
from webcam import record_session
from motor import init_serial, send_motor_command, close_serial
from mpesa import initiate_mpesa_payment, is_valid_phone
from config import DEFAULT_SETTINGS, VIDEO_DIR

# Initialize
load_settings()
init_serial()

root = tk.Tk()
root.title("360 Booth System")

frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

# Scrolled text log
from tkinter import scrolledtext
log_text = scrolledtext.ScrolledText(root, width=70, height=15, state='disabled')
log_text.pack(pady=10)

# Countdown label
countdown_label = tk.Label(root, text="Waiting...", font=("Arial", 14))
countdown_label.pack(pady=5)

# Hook logger to Tkinter
def update_ui_log(msg):
    log_text.config(state='normal')
    log_text.insert(tk.END, msg + "\n")
    log_text.see(tk.END)
    log_text.config(state='disabled')
set_ui_callback(update_ui_log)


# Countdown
def fullscreen_countdown(seconds, on_complete):
    cs = tk.Toplevel(root)
    cs.attributes('-fullscreen', True)
    cs.configure(bg='black')
    lbl = tk.Label(cs, text=str(seconds), font=("Helvetica", 160), fg='white', bg='black')
    lbl.pack(expand=True)

    def tick(t):
        if t <= 0:
            cs.destroy()
            on_complete()
            return
        lbl.config(text=str(t))
        cs.after(1000, lambda: tick(t-1))

    tick(seconds)
    
# Session Flow
last_payment_phone = None

def start_session_flow():
    global last_payment_phone
    # Get phone
    phone = simpledialog.askstring("Payment", "Enter phone (07... or 01...):")
    if not phone: return
    phone = phone.strip()
    if phone.startswith("07") or phone.startswith("01"): phone = "254" + phone[1:]
    if not is_valid_phone(phone):
        messagebox.showerror("Invalid", "Invalid phone number")
        return

    if not select_check_song():
        messagebox.showwarning("Music", "Please select music first.")
        return

    amount = settings.get("price", 0)
    log(f"Initiating payment for {phone} amount {amount}")

    def payment_thread():
        try:
            success = initiate_mpesa_payment(phone, amount)
            if success:
                global last_payment_phone
                last_payment_phone = phone
                update_countdown_text("Payment confirmed. Starting soon...")
                # Start recording in separate thread
                threading.Thread(target=lambda: start_recording("F"), daemon=True).start()
            else:
                root.after(0, lambda: messagebox.showerror("Payment Failed", "M-Pesa payment not confirmed."))
        except Exception as e:
            log(f"[ERROR] Payment thread exception: {e}")

    threading.Thread(target=payment_thread, daemon=True).start()


def update_countdown_text(text):
    root.after(0, lambda: countdown_label.config(text=text))


def select_check_song():
    """
    Ensure there is a selected song
    """
    import os
    from config import MUSIC_FILE
    return os.path.exists(MUSIC_FILE)


def start_recording(direction="F"):
    """
    Full countdown and start recording session
    """
    def after_countdown():
        duration = int(settings.get("record_time", 10))
        video_path = record_session(
            duration=duration,
            video_dir=VIDEO_DIR,
            motor_command_func=send_motor_command,
            music_play_func=play_selected_song,
            countdown_callback=update_countdown_text,
            direction=direction
        )
        if video_path:
            # Log session to CSV
            log_session(
                phone=last_payment_phone,
                song_title="Selected Song",
                duration=duration,
                status="OK",
                amount=settings.get("price", 0)
            )

    fullscreen_countdown(3, after_countdown)


# Music UI
def search_music_ui():
    query = simpledialog.askstring("Search Music", "Enter song or artist:")
    if not query: return
    win = tk.Toplevel(root)
    win.title("Music Results")
    try:
        videos = search_music(query, limit=6)
        for i, v in enumerate(videos):
            title = v['title']
            link = v['url']
            tk.Label(win, text=title, wraplength=500, justify='left').grid(row=i, column=0, sticky='w')
            tk.Button(win, text="Preview", command=lambda u=link: preview_song(u)).grid(row=i, column=1)
            tk.Button(win, text="Select", command=lambda u=link: select_song() or log(f"Selected: {title}")).grid(row=i, column=2)
    except Exception as e:
        messagebox.showerror("Search Error", str(e))


# Admin Settings
def admin_login():
    if not settings.get("password"):
        pw = simpledialog.askstring("Set Password", "Create a password:", show='*')
        if not pw: return
        set_password(pw)
        messagebox.showinfo("Password Set", "Password saved. Opening settings now.")
        open_settings()
        return
    pw = simpledialog.askstring("Admin Login", "Enter password:", show='*')
    if not pw: return
    if verify_password(pw):
        open_settings()
    else:
        messagebox.showerror("Error", "Incorrect password")


def open_settings():
    def save_and_close():
        try:
            settings["price"] = float(entry_price.get())
            settings["till_number"] = entry_till.get()
            settings["record_time"] = int(entry_record_time.get())
            settings["email"] = entry_email.get()
            settings["camera_type"] = camera_var.get()
            save_settings()
            win.destroy()
            log("Settings saved")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    win = tk.Toplevel(root)
    win.title("Owner Settings")
    tk.Label(win, text="Price (KES)").grid(row=0, column=0)
    entry_price = tk.Entry(win); entry_price.insert(0, settings.get("price", 50)); entry_price.grid(row=0, column=1)
    tk.Label(win, text="Till Number").grid(row=1, column=0)
    entry_till = tk.Entry(win); entry_till.insert(0, settings.get("till_number", '')); entry_till.grid(row=1, column=1)
    tk.Label(win, text="Recording Time (s)").grid(row=2, column=0)
    entry_record_time = tk.Entry(win); entry_record_time.insert(0, settings.get("record_time", 20)); entry_record_time.grid(row=2, column=1)
    tk.Label(win, text="Email").grid(row=3, column=0)
    entry_email = tk.Entry(win); entry_email.insert(0, settings.get("email", '')); entry_email.grid(row=3, column=1)
    tk.Label(win, text="Camera Type").grid(row=4, column=0)
    camera_var = tk.StringVar(value=settings.get("camera_type", "webcam"))
    tk.OptionMenu(win, camera_var, "front", "back").grid(row=4, column=1)
    tk.Button(win, text="Save", command=save_and_close).grid(row=5, column=0, columnspan=2, pady=10)


# Tkinter Buttons
tk.Button(frame, text="Search Music", command=search_music_ui).grid(row=0, column=0, padx=5)
tk.Button(frame, text="Start Session", command=start_session_flow).grid(row=0, column=1, padx=5)
tk.Button(frame, text="Admin", command=admin_login).grid(row=0, column=2, padx=5)


# Start Mainloop
log("System ready")
root.mainloop()

# Cleanup
close_serial()
stop_music()
