# Handles persistent booth settings and password management
import os
import json
import hashlib
from config import SETTINGS_FILE, DEFAULT_SETTINGS
from logger import log

# Global settings dictionary
settings = {}


# Password hashing
def hash_password(password: str) -> str:
    """
    Returns SHA-256 hash of a password
    """
    return hashlib.sha256(password.encode()).hexdigest()

# Load / Save Settings
def load_settings():
    """
    Load settings from JSON file or create defaults
    """
    global settings
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
        except Exception as e:
            log(f"[Settings] Error loading {SETTINGS_FILE}: {e}")
            settings = DEFAULT_SETTINGS.copy()
    else:
        settings = DEFAULT_SETTINGS.copy()
        save_settings()
        log(f"[Settings] Created default settings at {SETTINGS_FILE}")


def save_settings():
    """
    Save current settings to JSON
    """
    global settings
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
        log("[Settings] Settings saved successfully")
    except Exception as e:
        log(f"[Settings] Error saving settings: {e}")


# Password Management
def is_password_set() -> bool:
    """
    Returns True if a password exists
    """
    return bool(settings.get("password"))


def verify_password(password: str) -> bool:
    """
    Checks if given password matches stored hash
    """
    stored = settings.get("password")
    return stored == hash_password(password) if stored else False


def set_password(password: str):
    """
    Hash and store new password
    """
    settings["password"] = hash_password(password)
    save_settings()
    log("[Settings] Admin password set")
