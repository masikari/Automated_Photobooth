# settings.py
import os
import json
import hashlib

SETTINGS_FILE = 'settings.json'
SESSIONS_CSV = 'sessions.csv'

DEFAULT_SETTINGS = {
    "password": None,
    "price": 50.0,
    "till_number": "",
    "record_time": 20,
    "email": "",
    "camera_type": "webcam",
    "last_song_title": ""
}

settings = {}

def load_settings():
    global settings
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            settings = json.load(f)
    else:
        settings = DEFAULT_SETTINGS.copy()
    return settings

def save_settings():
    global settings
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()
