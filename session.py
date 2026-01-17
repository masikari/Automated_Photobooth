# session.py
import os
import threading
import time
import cv2
import pygame
import csv

from settings import settings, SESSIONS_CSV
from logger import log

# Motor functions must be initialized in main.py and passed here
_motor_send = None

# Pygame for music playback
pygame.mixer.init()

# Haar cascade
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
if face_cascade.empty():
    raise Exception("Haar cascade not found! Download from OpenCV repo.")

def init_session(motor_send_function):
    """Initialize session with motor send callback"""
    global _motor_send
    _motor_send = motor_send_function

def play_music(file_path):
    if os.path.exists(file_path):
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        log("Playing selected song...")
    else:
        log("[ERR] No selected song available!")

def stop_music():
    pygame.mixer.music.stop()

def start_session(duration, direction, update_countdown_text, music_file):
    log("Starting session...")

    def after_countdown():
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            log("❌ Webcam not detected")
            return

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = 30
        ts = time.strftime("%Y%m%d_%H%M%S")
        os.makedirs("videos", exist_ok=True)
        video_path = f"videos/Finetake_Photography_{ts}.mp4"
        out = cv2.VideoWriter(video_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))

        if _motor_send:
            _motor_send(direction)

        play_music(music_file)
        start_time = time.time()

        cv2.namedWindow("Live View", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Live View", 640, 480)

        def record_loop():
            while time.time() - start_time < duration:
                ret, frame = cap.read()
                if not ret:
                    break

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.3, 5)

                if len(faces) > 0:
                    x, y, w, h = max(faces, key=lambda f: f[2]*f[3])
                    cx, cy = x + w//2, y + h//2
                    crop_size = min(width, height)//2
                    x1 = max(cx - crop_size//2, 0)
                    y1 = max(cy - crop_size//2, 0)
                    x2 = min(x1 + crop_size, width)
                    y2 = min(y1 + crop_size, height)
                    cropped = frame[y1:y2, x1:x2]
                    frame_resized = cv2.resize(cropped, (width, height))
                else:
                    frame_resized = frame

                out.write(frame_resized)
                cv2.imshow("Live View", frame_resized)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

                remaining = duration - int(time.time() - start_time)
                update_countdown_text(f"Recording... {remaining}s")

            cap.release()
            out.release()
            cv2.destroyAllWindows()
            if _motor_send:
                _motor_send('S')
            stop_music()
            update_countdown_text("Done")

            # Save session log
            try:
                with open(SESSIONS_CSV, 'a', newline='') as f:
                    csv.writer(f).writerow([
                        time.strftime("%Y-%m-%d %H:%M:%S"),
                        settings.get("last_phone", ""),
                        settings.get("last_song_title", ""),
                        duration,
                        "OK",
                        settings.get("price", 0)
                    ])
            except Exception as e:
                log(f"CSV write error: {e}")

            log(f"✅ Session completed → {video_path}")

        threading.Thread(target=record_loop, daemon=True).start()

    # Return the after_countdown callback for main.py to call in fullscreen_countdown
    return after_countdown
