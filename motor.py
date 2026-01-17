# motor.py
import serial
from logger import log

_ser = None

def init_serial(port='/dev/rfcomm0', baud=9600):
    global _ser
    try:
        _ser = serial.Serial(port, baud, timeout=1)
        log(f"Serial opened on {port} @ {baud}")
    except Exception as e:
        _ser = None
        log(f"Serial open error: {e}")

def send_motor_command(cmd):
    if _ser and _ser.is_open:
        try:
            _ser.write(cmd.encode())
            log(f"Motor command sent: {cmd}")
        except Exception as e:
            log(f"Motor send error: {e}")
    else:
        log(f"Motor command skipped (serial not connected): {cmd}")

def close_serial():
    global _ser
    if _ser and _ser.is_open:
        _ser.close()
        log("Serial closed")
