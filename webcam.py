import cv2
import os
import time
import numpy as np
from datetime import datetime
from logger import log

CASCADE_FILE = "haarcascade_frontalface_default.xml"
VIDEO_DIR = "/home/user/Automated_Photobooth/videos"

face_cascade = cv2.CascadeClassifier(CASCADE_FILE)
if face_cascade.empty():
    raise Exception("Haar cascade not found")

_camera = None
_preview_running = False
LAST_RECORDED_VIDEO = None

# Tracking state
_last_center = None
SMOOTHING = 0.85
DEAD_ZONE = 20

# Ensure video directory exists
os.makedirs(VIDEO_DIR, exist_ok=True)

def safe_set(cam, prop, value):
    try:
        cam.set(prop, value)
    except:
        pass

#Camera Preview
def open_camera_preview():
    global _camera, _preview_running

    if _preview_running:
        return

    _camera = cv2.VideoCapture(0)
    if not _camera.isOpened():
        log("❌ Webcam not available")
        return

    safe_set(_camera, cv2.CAP_PROP_AUTOFOCUS, 0)
    _preview_running = True
    log("Camera preview opened")

    while _preview_running:
        ret, frame = _camera.read()
        if not ret:
            break

        frame = _center_object(frame)
        frame = _auto_brightness(frame, _camera)
        frame = _auto_focus(frame)
        cv2.imshow("Camera Preview", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            close_camera_preview()

    close_camera_preview()

def close_camera_preview():
    global _camera, _preview_running
    _preview_running = False
    if _camera:
        _camera.release()
        _camera = None
    cv2.destroyAllWindows()
    log("Camera preview closed")

#Video Recording
def record_video(duration, phone_number=None):
    global LAST_RECORDED_VIDEO

    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        log("Webcam not available")
        return None

    ret, frame = cam.read()
    if not ret:
        log("Failed to read from webcam")
        cam.release()
        return None

    frame = _center_object(frame)
    h, w, _ = frame.shape
    fps = 30

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(VIDEO_DIR, f"Finetake_Photography_{ts}.mp4")

    out = cv2.VideoWriter(
        path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (w, h)
    )
    if not out.isOpened():
        log("❌ VideoWriter failed to open")
        cam.release()
        return None

    log("Recording started")
    start = time.time()

    while time.time() - start < duration:
        ret, frame = cam.read()
        if not ret:
            break

        frame = _center_object(frame)
        frame = _auto_brightness(frame, cam)
        frame = _auto_focus(frame)
        frame = cv2.resize(frame, (w, h))
        out.write(frame)
        cv2.imshow("Recording", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cam.release()
    out.release()
    cv2.destroyAllWindows()

    if not os.path.exists(path) or os.path.getsize(path) < 10000:
        log("Video file not saved correctly")
        return None

    LAST_RECORDED_VIDEO = path
    log(f"Session completed → {path}")
    return path

# Object Centering
def _center_object(frame):
    """
    Smooth digital pan to keep object centered (NO zooming).
    Only moves the frame slightly if the object is far from center.
    """
    global _last_center
    h, w, _ = frame.shape
    frame_cx, frame_cy = w // 2, h // 2

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    if len(faces):
        x, y, fw, fh = max(faces, key=lambda f: f[2]*f[3])
        cx, cy = x + fw // 2, y + fh // 2

        if _last_center is None:
            _last_center = (cx, cy)
        else:
            # Smooth movement
            cx = int(SMOOTHING * _last_center[0] + (1 - SMOOTHING) * cx)
            cy = int(SMOOTHING * _last_center[1] + (1 - SMOOTHING) * cy)
            _last_center = (cx, cy)
    else:
        return frame  # no object detected, return full frame

    dx = cx - frame_cx
    dy = cy - frame_cy

    # Apply dead zone
    if abs(dx) < DEAD_ZONE:
        dx = 0
    if abs(dy) < DEAD_ZONE:
        dy = 0

    # Digital pan only (shift frame slightly)
    M = np.float32([[1, 0, -dx], [0, 1, -dy]])
    shifted_frame = cv2.warpAffine(frame, M, (w, h), borderMode=cv2.BORDER_REPLICATE)

    return shifted_frame

#Brightness & Focus
def _auto_brightness(frame, cam):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    diff = 120 - gray.mean()
    exposure = cam.get(cv2.CAP_PROP_EXPOSURE)

    if diff > 15:
        safe_set(cam, cv2.CAP_PROP_EXPOSURE, exposure - 0.01)
    elif diff < -15:
        safe_set(cam, cv2.CAP_PROP_EXPOSURE, exposure + 0.01)

    alpha = 1.0 + diff / 300
    return cv2.convertScaleAbs(frame, alpha=alpha, beta=0)

def _auto_focus(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()

    if sharpness < 80:
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        frame = cv2.filter2D(frame, -1, kernel)
    return frame
