# Thread-safe logging for Automated_Photobooth

import csv
import threading
from datetime import datetime
from config import SESSIONS_CSV

_lock = threading.Lock()

# Optional callback to update Tkinter UI
_ui_callback = None


def set_ui_callback(callback):
    """
    Set a function to receive log messages for GUI display
    """
    global _ui_callback
    _ui_callback = callback


def log(message: str):
    """
    Logs message with timestamp to console and GUI
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] {message}"

    with _lock:
        print(full_msg)
        if _ui_callback:
            _ui_callback(full_msg)


def log_session(phone="", song_title="", duration=0, status="OK", amount=0):
    """
    Appends a session record to CSV
    """
    timestamp = datetime.now().isoformat()
    with _lock:
        # create CSV if it doesn't exist
        if not os.path.exists(SESSIONS_CSV):
            with open(SESSIONS_CSV, "w", newline="") as f:
                csv.writer(f).writerow(
                    ["timestamp", "phone", "song_title", "duration", "status", "amount"]
                )

        # append row
        with open(SESSIONS_CSV, "a", newline="") as f:
            csv.writer(f).writerow(
                [timestamp, phone, song_title, duration, status, amount]
            )
