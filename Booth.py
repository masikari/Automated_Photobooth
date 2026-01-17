# 360_booth_main.py
# Upgraded integrated 360 Photo Booth system (Pi-friendly)
# - Replaced youtubesearchpython with yt-dlp search
# - Dynamic M-Pesa timestamp & password per request
# - Thread-safe Tkinter UI updates via root.after
# - Fullscreen countdown before session
# - Improved serial (Bluetooth) handling and clear error messages
# - Admin flow: set password then open settings immediately
# - Safe music download to 'selected_song.mp3' (overwrites intentionally)
# - Basic session logging to sessions.csv

import tkinter as tk
from tkinter import messagebox, simpledialog, scrolledtext
import os
import json
import hashlib
import threading
import subprocess
import time
import cv2
import base64
import re
from datetime import datetime, timedelta
import requests
from requests.auth import HTTPBasicAuth
import serial
import yt_dlp
import pygame
import csv
import shutil
from PIL import Image, ImageTk
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import qrcode

PI_SAVE_DIR = "/home/pi/booth_videos"
SETTINGS_FILE = 'settings.json'
SESSIONS_CSV = 'sessions.csv'
MUSIC_FILE = "selected_song.mp3"
PREVIEW_FILE = "preview_temp.mp3"
SELECTED_FILE = "selected_song.mp3"
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.pickle"


# === SETTINGS LOAD/SAVE ===
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

# === LOGGER ===
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

# === YOUTUBE SEARCH / PREVIEW ===
def search_youtube(query, max_results=5):
    ydl_opts = {'quiet': True, 'skip_download': True, 'format': 'bestaudio/best', 'default_search': f'ytsearch{max_results}'}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
    results = []
    if 'entries' in info:
        for entry in info['entries']:
            results.append({'title': entry.get('title'), 'url': entry.get('webpage_url')})
    return results

def preview_song(youtube_url):
    ydl_opts = {"format": "bestaudio/best", "outtmpl": "preview_temp.%(ext)s",
                "quiet": True, "noplaylist": True,
                "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "128"}]}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])
    subprocess.Popen(["vlc", "--play-and-exit", PREVIEW_FILE])

def select_song(youtube_url):
    if os.path.exists(PREVIEW_FILE):
        shutil.copy(PREVIEW_FILE, SELECTED_FILE)
        try:
            os.remove(PREVIEW_FILE)
        except: pass
        log("Song selected from preview!")
    else:
        ydl_opts = {"format": "bestaudio/best", "outtmpl": "selected_song.%(ext)s",
                    "quiet": True, "noplaylist": True,
                    "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
        log("Song downloaded directly as selection.")

def search_music(auto_start=False):
    query = simpledialog.askstring("Search Music", "Enter song or artist:")
    if not query: return
    win = tk.Toplevel(root)
    win.title("Music Results")
    try:
        videos = search_youtube(query, max_results=6)
        for i, v in enumerate(videos):
            title = v['title']
            link = v['url']
            tk.Label(win, text=title, wraplength=500, justify='left').grid(row=i, column=0, sticky='w')
            tk.Button(win, text="Preview", command=lambda u=link: preview_song(u)).grid(row=i, column=1)
            tk.Button(win, text="Select", command=lambda u=link: select_song(u)).grid(row=i, column=2)
    except Exception as e:
        messagebox.showerror("Search Error", str(e))

# === MOTOR (Bluetooth) ===
SERIAL_PORT = '/dev/rfcomm0'
SERIAL_BAUD = 9600
ser = None
def init_serial():
    global ser
    try:
        ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
        log(f"Serial opened on {SERIAL_PORT} @ {SERIAL_BAUD}")
    except Exception as e:
        ser = None
        log(f"Serial open error: {e}")
init_serial()

def send_motor_command(cmd):
    if ser and ser.is_open:
        try: ser.write(cmd.encode()); log(f"Motor command sent: {cmd}")
        except Exception as e: log(f"Motor send error: {e}")
    else:
        log(f"Motor command skipped (serial not connected): {cmd}")

# === M-PESA ===
class MpesaConfig:
    consumer_key = '1iJq9SGuGYWjcmeOGICmpdPe9FU4w23sfkhzAW87eT1FiqQ2'
    consumer_secret = 'tPYL0zY4DyUr7OQftOOGU08Yhqrhu8L22EuI5LqmqG2u6uUhAEV8KGGSeSh4RV5a'
    oauth_url = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
    process_url = 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
    query_url = 'https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query'
    business_shortcode = '174379'
    passkey = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919'

_token_cache = {'token': None, 'expiry': datetime.min}

def get_access_token():
    now = datetime.now()
    if _token_cache['token'] and now < _token_cache['expiry'] - timedelta(seconds=10):
        return _token_cache['token']
    try:
        r = requests.get(MpesaConfig.oauth_url,
                         auth=HTTPBasicAuth(MpesaConfig.consumer_key, MpesaConfig.consumer_secret), timeout=10)
        r.raise_for_status()
        data = r.json()
        token = data.get('access_token')
        expires_in = int(data.get('expires_in', 3600))
        _token_cache['token'] = token
        _token_cache['expiry'] = now + timedelta(seconds=expires_in)
        log('Obtained new M-Pesa access token')
        return token
    except Exception as e:
        log(f"Error obtaining access token: {e}")
        return None

def generate_lipana_password():
    lipa_time = datetime.now().strftime('%Y%m%d%H%M%S')
    data_to_encode = MpesaConfig.business_shortcode + MpesaConfig.passkey + lipa_time
    password = base64.b64encode(data_to_encode.encode()).decode('utf-8')
    return password, lipa_time

def is_valid_phone(phone): return re.match(r"^(2547|2541)\d{8}$", phone)

def query_mpesa_status(checkout_request_id):
    token = get_access_token()
    if not token: return False
    password, lipa_time = generate_lipana_password()
    payload = {"BusinessShortCode": MpesaConfig.business_shortcode, "Password": password, "Timestamp": lipa_time,
               "CheckoutRequestID": checkout_request_id}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        resp = requests.post(MpesaConfig.query_url, json=payload, headers=headers, timeout=10)
        data = resp.json()
        log(json.dumps(data, indent=2))
        return str(data.get("ResultCode")) == "0"
    except Exception as e:
        log(f"STK query error: {e}")
        return False

def initiate_mpesa_payment(phone_number, amount):
    token = get_access_token()
    if not token: return False
    password, lipa_time = generate_lipana_password()
    payload = {"BusinessShortCode": MpesaConfig.business_shortcode, "Password": password, "Timestamp": lipa_time,
               "TransactionType": "CustomerPayBillOnline", "Amount": int(amount), "PartyA": phone_number,
               "PartyB": MpesaConfig.business_shortcode, "PhoneNumber": phone_number,
               "CallBackURL": "https://sandbox.safaricom.co.ke/mpesa/",
               "AccountReference": "360Booth", "TransactionDesc": "360 Booth Payment"}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        resp = requests.post(MpesaConfig.process_url, json=payload, headers=headers, timeout=10)
        data = resp.json()
        log(json.dumps(data, indent=2))
        if data.get("ResponseCode") == "0":
            checkout_id = data.get("CheckoutRequestID")
            for _ in range(30):
                time.sleep(1)
                if query_mpesa_status(checkout_id):
                    return True
        return False
    except Exception as e:
        log(f"MPesa initiation error: {e}")
        return False

# === SESSION / RECORDING ===
pygame.mixer.init()
def play_selected_song():
    if os.path.exists(SELECTED_FILE):
        pygame.mixer.music.load(SELECTED_FILE)
        pygame.mixer.music.play()
        log(" Playing selected song...")
    else:
        log("[ERR] No selected song available!")

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
    
def start_session(direction):
    log("Starting session...")
    duration = int(settings.get('record_time', 10))
    def after_countdown():
        cap = cv2.VideoCapture(0)
        if not cap.isOpened(): log("❌ Webcam not detected"); return
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = 30
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs("videos", exist_ok=True)
        video_path = f"videos/Finetake_Photography_{ts}.mp4"
        out = cv2.VideoWriter(video_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
        send_motor_command(direction)
        play_selected_song()
        
        start_time = time.time()
        
        cv2.namedWindow("Live View", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Live View", 640, 480)
        def record_loop():
            while time.time() - start_time < duration:
                ret, frame = cap.read()
                if not ret: break
                
                # --- FACE DETECTION ---
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                
                if len(faces) > 0:
                    # pick largest face
                    x, y, w, h = max(faces, key=lambda f: f[2]*f[3])
                    cx, cy = x + w//2, y + h//2
                    crop_size = min(width, height) // 2  # half-frame crop
                    x1 = max(cx - crop_size//2, 0)
                    y1 = max(cy - crop_size//2, 0)
                    x2 = min(x1 + crop_size, width)
                    y2 = min(y1 + crop_size, height)
                    cropped_frame = frame[y1:y2, x1:x2]
                    frame_resized = cv2.resize(cropped_frame, (width, height))
                else:
                    frame_resized = frame  # no face detected, show full frame
                out.write(frame_resized)
                
                # --- SHOW LIVE PREVIEW ---
                cv2.imshow("Live View", frame_resized)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
                remaining = duration - int(time.time() - start_time)
                update_countdown_text(f"Recording... {remaining}s")
            cap.release(); out.release(); cv2.destroyAllWindows()
            send_motor_command('S'); pygame.mixer.music.stop()
            update_countdown_text("Done")
            try:
                with open(SESSIONS_CSV, 'a', newline='') as f:
                    csv.writer(f).writerow([datetime.now().isoformat(), last_payment_phone,
                                             settings.get('last_song_title', ''), duration, 'OK', settings.get('price')])
            except Exception as e: log(f"CSV write error: {e}")
            log(f"✅ Session completed → {video_path}")
        threading.Thread(target=record_loop, daemon=True).start()
    fullscreen_countdown(3, after_countdown)

def start_flow():
    global last_payment_phone
    try:
        phone = simpledialog.askstring("Payment", "Enter phone (07... or 01...):")
        if not phone: return
        phone = phone.strip()
        if phone.startswith("07") or phone.startswith("01"): phone = "254" + phone[1:]
        if not is_valid_phone(phone):
            messagebox.showerror("Invalid", "Invalid phone number")
            return
        if not os.path.exists(SELECTED_FILE):
            messagebox.showwarning("Missing", "Please select music first.")
            return
        amount = settings.get('price', 0)
        log(f"Initiating payment for {phone} amount {amount}")
        def payment_thread():
            try:
                success = initiate_mpesa_payment(phone, amount)
                if success:
                    global last_payment_phone; last_payment_phone = phone
                    update_countdown_text('Payment confirmed. Starting soon...')
                    threading.Thread(target=lambda: start_session('F'), daemon=True).start()
                else:
                    root.after(0, lambda: messagebox.showerror('Payment Failed', 'M-Pesa payment not confirmed.'))
            except Exception as e: log(f"[ERROR] Payment thread exception: {e}")
        threading.Thread(target=payment_thread, daemon=True).start()
    except Exception as e: log(f"[ERROR] start_flow exception: {e}")

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

# start mainloop
log('System ready')
root.mainloop()
