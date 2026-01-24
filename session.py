# session.py
import os
import time
import csv
import threading
import cv2
import pygame
import tkinter as tk
from datetime import datetime
import subprocess

from settings import settings
from logger import log
from motor import send_motor_command
from music import play_selected_song

SESSIONS_CSV = "sessions.csv"
CASCADE_FILE = "haarcascade_frontalface_default.xml"
countdown_window = None

face_cascade = cv2.CascadeClassifier(CASCADE_FILE)
if face_cascade.empty():
    raise Exception("Haar cascade not found!")

pygame.mixer.init()

def convert_to_whatsapp_mp4(input_file):
    """Convert OpenCV mp4 to WhatsApp-compatible mp4 using H264"""
    output_file = input_file.replace(".mp4", "_wa.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-i", input_file,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        output_file
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_file

def start_session(root, countdown_label, phone_number, on_complete=None):
    """
    Starts a 360 booth session with countdown, recording, motor + music control.
    Calls on_complete() after session finishes if provided.
    """
    duration = int(settings.get("record_time", 10))

    def update_countdown(text):
        root.after(0, lambda: countdown_label.config(text=text))

    def fullscreen_countdown(seconds, callback):
        global countdown_window

        if countdown_window is not None:
            try:
                countdown_window.destroy()
            except:
                pass
            countdown_window = None

        countdown_window = tk.Toplevel(root)
        countdown_window.attributes("-fullscreen", True)
        countdown_window.configure(bg="black")
        countdown_window.title("countdown")

        label = tk.Label(
            countdown_window,
            text=str(seconds),
            font=("Helvetica", 160),
            fg="white",
            bg="black"
        )
        label.pack(expand=True)

        def tick(t):
            global countdown_window
            if t <= 0:
                try:
                    countdown_window.destroy()
                except:
                    pass
                countdown_window = None
                callback()
                return

            label.config(text=str(t))
            countdown_window.after(1000, lambda: tick(t - 1))

        tick(seconds)

    def record():
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            log("❌ Webcam not detected")
            return

        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        os.makedirs("videos", exist_ok=True)
        path = f"videos/Finetake_Photography_{ts}.mp4"

        out = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), 30, (w, h))

        send_motor_command("F")
        play_selected_song()

        start = time.time()
        while time.time() - start < duration:
            ret, frame = cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)

            if len(faces):
                x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
                cx, cy = x + fw // 2, y + fh // 2
                size = min(w, h) // 2
                x1, y1 = max(cx - size // 2, 0), max(cy - size // 2, 0)
                crop = frame[y1:y1+size, x1:x1+size]
                frame = cv2.resize(crop, (w, h))

            out.write(frame)
            remaining = duration - int(time.time() - start)
            update_countdown(f"Recording... {remaining}s")

        cap.release()
        out.release()
        send_motor_command("S")
        pygame.mixer.music.stop()

        update_countdown("Done")

        # Convert to WhatsApp-friendly mp4 but do not send automatically
        wa_video = convert_to_whatsapp_mp4(path)
        log(f"Session completed → {wa_video}")

        # Log session
        with open(SESSIONS_CSV, "a", newline="") as f:
            csv.writer(f).writerow([
                datetime.now().isoformat(),
                phone_number,
                duration,
                settings.get("price")
            ])

        # Callback if provided
        if on_complete:
            on_complete()

    fullscreen_countdown(3, lambda: threading.Thread(target=record, daemon=True).start())
