# settings.py
import os
import json
import hashlib

SETTINGS_FILE = "settings.json"
settings = {}

# ======== LOAD SETTINGS ========
def load_settings():
    global settings
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
        except Exception as e:
            print(f"[SETTINGS] Failed to load settings: {e}")
            settings = {}
    else:
        settings = {}

    # Ensure defaults
    defaults = {
        "price": 0,
        "till_number": "",
        "record_time": 10,
        "email": "",
        "password": None,
        "lock_until": 0,
        "failed_attempts": 0,
        "admin_whatsapp": "",
        "whatsapp_logged_in": False  # <=== Persist WhatsApp login
    }
    for key, val in defaults.items():
        if key not in settings:
            settings[key] = val

# ======== SAVE SETTINGS ========
def save_settings():
    global settings
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print(f"[SETTINGS] Failed to save settings: {e}")

# ======== PASSWORD HANDLING ========
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def is_locked() -> bool:
    """Check if too many failed attempts or lock time active"""
    import time
    lock_until = settings.get("lock_until", 0)
    failed = settings.get("failed_attempts", 0)
    return failed >= 5 and time.time() < lock_until

def register_failed_attempt():
    import time
    settings["failed_attempts"] = settings.get("failed_attempts", 0) + 1
    if settings["failed_attempts"] >= 5:
        settings["lock_until"] = time.time() + 300  # lock for 5 minutes
    save_settings()

def reset_failed_attempts():
    settings["failed_attempts"] = 0
    settings["lock_until"] = 0
    save_settings()
