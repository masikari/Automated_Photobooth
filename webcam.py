# Handles video capture, face detection, and session recording

import cv2
import os
import time
from datetime import datetime
from config import FACE_CASCADE, MUSIC_FILE
from logger import log

face_cascade = cv2.CascadeClassifier(FACE_CASCADE)
if face_cascade.empty():
    raise Exception("Failed to load Haar cascade. Ensure haarcascade_frontalface_default.xml exists.")


def record_session(
    duration: int,
    video_dir: str,
    motor_command_func=None,
    music_play_func=None,
    countdown_callback=None,
    direction="F"
):
    """
    Records a video session with face detection.

    Args:
        duration: recording duration in seconds
        video_dir: folder to save video
        motor_command_func: callable(cmd) to move motor
        music_play_func: callable() to play selected song
        countdown_callback: callable(text) for GUI updates
        direction: motor direction ("F" or "R")
    Returns:
        video_path (str)
    """
    os.makedirs(video_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_path = os.path.join(video_dir, f"Finetake_Photography_{ts}.mp4")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        log("❌ Webcam not detected")
        return None

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = 30

    out = cv2.VideoWriter(video_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))

    # Start motor and music
    if motor_command_func:
        motor_command_func(direction)
    if music_play_func:
        music_play_func()

    start_time = time.time()

    cv2.namedWindow("Live View", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Live View", 640, 480)

    while time.time() - start_time < duration:
        ret, frame = cap.read()
        if not ret:
            break

        #FACE DETECTION
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        small_gray = cv2.resize(gray, (0, 0), fx=0.5, fy=0.5)
        faces = face_cascade.detectMultiScale(small_gray, 1.3, 5)

        if len(faces) > 0:
            # pick largest face
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            cx, cy = (x + w//2) * 2, (y + h//2) * 2  # scale back
            crop_size = min(width, height) // 2
            x1 = max(cx - crop_size//2, 0)
            y1 = max(cy - crop_size//2, 0)
            x2 = min(x1 + crop_size, width)
            y2 = min(y1 + crop_size, height)
            frame_resized = cv2.resize(frame[y1:y2, x1:x2], (width, height))
        else:
            frame_resized = frame

        out.write(frame_resized)

        # Show live preview
        cv2.imshow("Live View", frame_resized)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        # Countdown text
        remaining = duration - int(time.time() - start_time)
        if countdown_callback:
            countdown_callback(f"Recording... {remaining}s")

    # Cleanup
    cap.release()
    out.release()
    cv2.destroyAllWindows()

    # Stop motor and music
    if motor_command_func:
        motor_command_func("S")
    if music_play_func:
        from music import stop_music
        stop_music()

    if countdown_callback:
        countdown_callback("Done")

    log(f"✅ Session completed → {video_path}")
    return video_path
