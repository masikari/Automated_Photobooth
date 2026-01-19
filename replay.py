import os
import cv2
from webcam import LAST_RECORDED_VIDEO, VIDEO_DIR
from logger import log

def replay_last_video():
    video_path = None

    # Try to get the newest video from VIDEO_DIR
    if os.path.exists(VIDEO_DIR):
        videos = [os.path.join(VIDEO_DIR, f) for f in os.listdir(VIDEO_DIR)
                  if f.lower().endswith(('.mp4', '.avi'))]
        if videos:
            # Sort by creation time, newest first
            videos.sort(key=os.path.getmtime, reverse=True)
            video_path = videos[0]

    # Fall back to LAST_RECORDED_VIDEO
    if not video_path and LAST_RECORDED_VIDEO:
        video_path = LAST_RECORDED_VIDEO

    if not video_path or not os.path.exists(video_path):
        log("No recorded video available for replay")
        return

    log(f"Replaying video → {video_path}")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        log("Cannot open video for replay")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        cv2.imshow("Replay", frame)
        if cv2.waitKey(30) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    log("Replay finished")
