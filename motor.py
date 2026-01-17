# Handles motor control via Bluetooth serial

import serial
import time
from threading import Lock
from config import SERIAL_PORT, SERIAL_BAUD
from logger import log

_ser = None
_lock = Lock()

#MOTOR (Bluetooth)
SERIAL_PORT = '/dev/rfcomm0'
SERIAL_BAUD = 9600
ser = None

def init_serial():
    global ser
    try:
        ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
        log(f"Serial opened on {SERIAL_PORT} @ {SERIAL_BAUD}")
    except Exception as e:
        ser = None
        log(f"Serial open error: {e}")
init_serial()

def send_motor_command(cmd):
    if ser and ser.is_open:
        try: ser.write(cmd.encode()); log(f"Motor command sent: {cmd}")
        except Exception as e: log(f"Motor send error: {e}")
    else:
        log(f"Motor command skipped (serial not connected): {cmd}")
