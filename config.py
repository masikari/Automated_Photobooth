import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
SESSIONS_CSV = os.path.join(BASE_DIR, "sessions.csv")

SELECTED_FILE = os.path.join(BASE_DIR, "selected_song.mp3")
PREVIEW_FILE  = os.path.join(BASE_DIR, "preview_temp.mp3")

SERIAL_PORT = "/dev/rfcomm0"
SERIAL_BAUD = 9600
VIDEO_DIR = os.path.join(BASE_DIR, "videos")
