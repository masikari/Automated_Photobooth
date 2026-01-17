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
  
# Session Flow
last_payment_phone = None

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
    
# start mainloop
log('System ready')
root.mainloop()
