# Central configuration for Automated_Photobooth
import os
from dotenv import load_dotenv

# Load .env for credentials
ENV_PATH = os.path.join(os.path.dirname(__file__), "env", ".env")
load_dotenv(ENV_PATH)

# Project Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
SESSIONS_CSV = os.path.join(BASE_DIR, "sessions.csv")

MUSIC_FILE = os.path.join(BASE_DIR, "selected_song.mp3")
PREVIEW_FILE = os.path.join(BASE_DIR, "preview_temp.mp3")

FACE_CASCADE = os.path.join(BASE_DIR, "haarcascade_frontalface_default.xml")
VIDEO_DIR = os.path.join(BASE_DIR, "videos")

# Motor / Serial
SERIAL_PORT = "/dev/rfcomm0"  # Pi Bluetooth RFCOMM
SERIAL_BAUD = 9600

# M-Pesa Credentials (from .env)
MPESA = {
    "consumer_key": os.getenv("MPESA_CONSUMER_KEY"),
    "consumer_secret": os.getenv("MPESA_CONSUMER_SECRET"),
    "passkey": os.getenv("MPESA_PASSKEY"),
    "shortcode": os.getenv("MPESA_SHORTCODE", "174379"),
    "env": os.getenv("MPESA_ENV", "sandbox"),
}
# Default Booth Settings
DEFAULT_SETTINGS = {
    "password": None,
    "price": 50.0,
    "till_number": "",
    "record_time": 20,
    "email": "",
    "camera_type": "webcam"
}
