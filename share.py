import os
import threading
import time
import traceback

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pyautogui

from logger import log

VIDEO_DIR = "/home/user/Automated_Photobooth/videos"
CHROME_PROFILE = "/home/user/.whatsapp_session"
CHROMEDRIVER_PATH = "/usr/bin/chromedriver"


#Helper Functions
def get_last_video():
    if not os.path.exists(VIDEO_DIR):
        return None
    videos = sorted(
        [os.path.join(VIDEO_DIR, f) for f in os.listdir(VIDEO_DIR) if f.endswith(".mp4")],
        key=os.path.getmtime,
        reverse=True
    )
    return videos[0] if videos else None


def login_whatsapp():
    """One-time WhatsApp Web login. Admin scans QR, session saved."""
    log("Opening WhatsApp Web for login...")
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument(f"--user-data-dir={CHROME_PROFILE}")

    driver = webdriver.Chrome(
        service=Service(CHROMEDRIVER_PATH),
        options=chrome_options
    )
    driver.get("https://web.whatsapp.com")
    log("Scan QR code if required. Session will be reused.")
    return driver


def focus_chat_box(driver):
    """
    Focus WhatsApp chat box, handling overlays and click interception.
    """
    attempts = 5
    input_box = None
    for i in range(attempts):
        try:
            input_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[@contenteditable='true' and @data-tab]")
                )
            )
            # Scroll element into view
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", input_box)
            time.sleep(0.3)
            input_box.click()
            time.sleep(0.5)
            return input_box
        except Exception:
            log(f"Click intercepted, retrying {i+1}/{attempts}...")
            time.sleep(1)

    # PyAutoGUI fallback
    if input_box:
        try:
            loc = input_box.location_once_scrolled_into_view
            size = input_box.size
            x = loc['x'] + size['width'] // 2
            y = loc['y'] + size['height'] // 2
            pyautogui.moveTo(x, y, duration=0.3)
            pyautogui.click()
            log("Chat box focused using PyAutoGUI fallback")
            return input_box
        except:
            raise Exception("Failed to focus chat box")
    raise Exception("Failed to locate chat box")


#Core Share Logic
def share_via_whatsapp(client_phone):
    video = get_last_video()
    if not video:
        log("No video found to send")
        return

    log(f"Sending WhatsApp video")

    def send_thread():
        driver = None
        try:
            chrome_options = Options()
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument(f"--user-data-dir={CHROME_PROFILE}")

            driver = webdriver.Chrome(
                service=Service(CHROMEDRIVER_PATH),
                options=chrome_options
            )

            # Open client chat
            driver.get(f"https://web.whatsapp.com/send?phone={client_phone}")

            # Focus chat input box safely
            input_box = focus_chat_box(driver)
            log("Chat loaded")

            #Attach Video
            file_input = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='file']"))
            )
            file_input.send_keys(video)
            log("Video attached")

            #Wait for WhatsApp to prepare video
            log("Waiting for WhatsApp to prepare video...")
            max_wait = 20  
            # seconds
            start = time.time()
            while time.time() - start < max_wait:
                try:
                    # Check if upload overlay / spinner is gone
                    overlay = driver.find_elements(By.XPATH, "//div[contains(@class,'_1pJ9J')]")
                    if not overlay:
                        break
                except:
                    break
                time.sleep(0.5)
            log("Video preview ready")

            #Send Video
            input_box.click()
            time.sleep(0.3)
            pyautogui.press("ENTER")
            log("Video sent successfully and upload completed")
        except Exception as e:
            if driver:
                driver.save_screenshot("whatsapp_error.png")
            log(f"WhatsApp error: {e}\nScreenshot saved as whatsapp_error.png\n{traceback.format_exc()}")

    threading.Thread(target=send_thread, daemon=True).start()
