# Handles persistent booth settings and password management
import os
import json
import hashlib
from config import SETTINGS_FILE, DEFAULT_SETTINGS
from logger import log

# Global settings dictionary
settings = {}

#SETTINGS LOAD/SAVE
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    return {"password": None, "price": 50.0, "till_number": "",
            "record_time": 20, "email": "", "camera_type": "webcam"}

def save_settings():
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

settings = load_settings()

#LOGGER
root = tk.Tk()
root.title("360 Booth System")
frame = tk.Frame(root)
frame.pack(padx=10, pady=10)
log_text = scrolledtext.ScrolledText(root, width=70, height=15, state='disabled')
log_text.pack(pady=10)
countdown_label = tk.Label(root, text="Waiting...", font=("Arial", 14))
countdown_label.pack(pady=5)

if not os.path.exists(SESSIONS_CSV):
    with open(SESSIONS_CSV, 'w', newline='') as f:
        csv.writer(f).writerow(['timestamp', 'phone', 'song_title', 'duration', 'status', 'amount'])
        
def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    full = f"[{timestamp}] {msg}"
    log_text.config(state='normal')
    log_text.insert(tk.END, full + "\n")
    log_text.see(tk.END)
    log_text.config(state='disabled')
    print(full)
    
def update_countdown_text(text):
    root.after(0, lambda: countdown_label.config(text=text))
    
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

# Load Haar cascade from local file
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
if face_cascade.empty():
    raise Exception("Failed to load face cascade! Ensure haarcascade_frontalface_default.xml exists.")

# === ADMIN SETTINGS ===
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
    if hash_password(pw) == settings.get("password"): open_settings()
    else: messagebox.showerror("Error", "Incorrect password")

def open_settings():
    def save_and_close():
        try:
            settings["price"] = float(entry_price.get())
            settings["till_number"] = entry_till.get()
            settings["record_time"] = int(entry_record_time.get())
            settings["email"] = entry_email.get()
            settings["camera_type"] = camera_var.get()
            save_settings(); win.destroy(); log('Settings saved')
        except Exception as e: messagebox.showerror('Save Error', str(e))

    win = tk.Toplevel(root)
    win.title("Owner Settings")
    tk.Label(win, text="Price (KES)").grid(row=0, column=0)
    entry_price = tk.Entry(win); entry_price.insert(0, settings.get("price", 0)); entry_price.grid(row=0, column=1)
    tk.Label(win, text="Till Number").grid(row=1, column=0)
    entry_till = tk.Entry(win); entry_till.insert(0, settings.get("till_number", '')); entry_till.grid(row=1, column=1)
    tk.Label(win, text="Recording Time (s)").grid(row=2, column=0)
    entry_record_time = tk.Entry(win); entry_record_time.insert(0, settings.get("record_time", 10)); entry_record_time.grid(row=2, column=1)
    tk.Label(win, text="Email").grid(row=5, column=0)
    entry_email = tk.Entry(win); entry_email.insert(0, settings.get("email", '')); entry_email.grid(row=5, column=1)
    tk.Label(win, text="Camera Type").grid(row=6, column=0)
    camera_var = tk.StringVar(value=settings.get("camera_type", 'back'))
    camera_dropdown = tk.OptionMenu(win, camera_var, "back", "front"); camera_dropdown.grid(row=6, column=1)
    tk.Button(win, text="Save", command=save_and_close).grid(row=7, column=0, columnspan=2, pady=10)

# === UI BUTTONS ===
tk.Button(frame, text="Search Music", command=search_music).grid(row=0, column=0, padx=5)
tk.Button(frame, text="Start Session", command=start_flow).grid(row=0, column=1, padx=5)
tk.Button(frame, text="Admin", command=admin_login).grid(row=0, column=2, padx=5)
