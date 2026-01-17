# Handles motor control via Bluetooth serial

import serial
import time
from threading import Lock
from config import SERIAL_PORT, SERIAL_BAUD
from logger import log

_ser = None
_lock = Lock()


def init_serial():
    """
    Initialize serial connection to motor
    """
    global _ser
    try:
        _ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
        time.sleep(2)  # allow connection to stabilize
        log(f"✅ Serial motor connected on {SERIAL_PORT} @ {SERIAL_BAUD}")
    except Exception as e:
        _ser = None
        log(f"❌ Serial motor connection failed: {e}")


def send_motor_command(cmd: str):
    """
    Sends command to motor ('F'/'R'/'S')
    """
    global _ser
    if cmd not in ("F", "R", "S"):
        log(f"[Motor] Invalid command: {cmd}")
        return

    with _lock:
        if _ser and _ser.is_open:
            try:
                _ser.write(cmd.encode())
                log(f"[Motor] Command sent: {cmd}")
            except Exception as e:
                log(f"[Motor] Send error: {e}")
        else:
            log(f"[Motor] Serial not connected, command skipped: {cmd}")


def close_serial():
    """
    Close serial safely
    """
    global _ser
    with _lock:
        if _ser and _ser.is_open:
            _ser.close()
            log("✅ Serial motor closed")
