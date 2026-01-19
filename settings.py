import json
import os
import hashlib
from datetime import datetime, timedelta

SETTINGS_FILE = "settings.json"
LOCK_TIME_MINUTES = 10

settings = {
    "price": 0,
    "till_number": "",
    "record_time": 10,
    "email": "",
    "password": None,
    "failed_attempts": 0,
    "lock_until": None
}

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def load_settings():
    global settings
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                settings.update(json.load(f))
        except Exception:
            pass

def save_settings():
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)

def is_locked():
    lock_until = settings.get("lock_until")
    if lock_until:
        return datetime.now() < datetime.fromisoformat(lock_until)
    return False

def register_failed_attempt():
    settings["failed_attempts"] += 1

    if settings["failed_attempts"] >= 3:
        lock_time = datetime.now() + timedelta(minutes=LOCK_TIME_MINUTES)
        settings["lock_until"] = lock_time.isoformat()
        settings["failed_attempts"] = 0

    save_settings()

def reset_failed_attempts():
    settings["failed_attempts"] = 0
    settings["lock_until"] = None
    save_settings()
