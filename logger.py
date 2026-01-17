# logger.py
from datetime import datetime

_ui_callback = None

def set_ui_callback(callback):
    """Set a function to output log messages to UI."""
    global _ui_callback
    _ui_callback = callback

def log(msg):
    """Logs to console and optionally to UI."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    full = f"[{timestamp}] {msg}"
    print(full)
    if _ui_callback:
        _ui_callback(full)
