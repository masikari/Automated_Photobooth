import pywhatkit
import pyautogui
import time
import os

# ---------------- CONFIG ----------------
PHONE = "+254758192712"# international format
VIDEO_PATH = "/home/pi/video.mp4"
WAIT_LOAD = 20               # seconds for WhatsApp Web to load
# ----------------------------------------

pyautogui.FAILSAFE = False

# Open WhatsApp chat
pywhatkit.sendwhatmsg_instantly(
    PHONE,
    " ",          # dummy message
    wait_time=WAIT_LOAD,
    tab_close=False
)

time.sleep(10)

# Click attachment (📎) — adjust coordinates for your screen
pyautogui.click(1250, 720)
time.sleep(2)

# Click "Photos & Videos"
pyautogui.click(1250, 620)
time.sleep(2)

# Type full video path
pyautogui.write(VIDEO_PATH)
time.sleep(1)
pyautogui.press("enter")

# Wait for video to load
time.sleep(10)

# Send video
pyautogui.press("enter")
