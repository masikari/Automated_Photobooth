# share.py
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
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
import tkinter as tk
from logger import log

VIDEO_DIR = "/home/user/Automated_Photobooth/videos"

def get_last_video():
    """Return the most recent .mp4 video in VIDEO_DIR"""
    if not os.path.exists(VIDEO_DIR):
        return None

    videos = sorted(
        [os.path.join(VIDEO_DIR, f) for f in os.listdir(VIDEO_DIR) if f.endswith(".mp4")],
        key=os.path.getmtime,
        reverse=True
    )
    return videos[0] if videos else None

def login_whatsapp():
    """Open WhatsApp Web for admin login (reuse session)"""
    log("Opening WhatsApp Web for login...")
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--user-data-dir=/home/user/.whatsapp_session")
    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get("https://web.whatsapp.com")
    log("Admin should scan QR code if first time. Session saved for future use.")
    return driver

def share_via_whatsapp(client_phone, root):
    """Send last recorded video to the client WhatsApp (manual send)"""
    video = get_last_video()
    if not video:
        log("No recorded video available")
        return

    log(f"📤 Preparing WhatsApp send → {client_phone}")

    def send_thread():
        driver = None
        try:
            chrome_options = Options()
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--user-data-dir=/home/user/.whatsapp_session")
            service = Service("/usr/bin/chromedriver")
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.get(f"https://web.whatsapp.com/send?phone={client_phone}")

            # Wait for chat input to load
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true' and @data-tab]"))
            )
            log("💬 Chat loaded")
            time.sleep(2)  # extra buffer

            # Attach video
            for attempt in range(3):
                try:
                    file_input = WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.XPATH, "//input[@type='file']"))
                    )
                    file_input.send_keys(video)
                    log("📎 Video attached")
                    break
                except StaleElementReferenceException:
                    log("⚠️ StaleElementReferenceException: retrying file input")
                    time.sleep(1)
            else:
                driver.save_screenshot("whatsapp_attach_fail.png")
                raise Exception("Failed to attach video")

            time.sleep(2)  # wait for preview
            log("🎞️ Video preview ready")

            # Manual Send Button
            def show_send_button(driver_inner):
                popup = tk.Toplevel(root)
                popup.title("Send WhatsApp Video")
                popup.geometry("300x100")

                tk.Label(popup, text=f"Video ready to send to {client_phone}").pack(pady=10)

                def send_now():
                    try:
                        send_xpaths = [
                            "//span[@data-testid='send']",
                            "//button[@data-icon='send']",
                            "//div[@role='button' and @data-testid='send']"
                        ]
                        send_btn = None
                        for xpath in send_xpaths:
                            try:
                                send_btn = WebDriverWait(driver_inner, 10).until(
                                    EC.element_to_be_clickable((By.XPATH, xpath))
                                )
                                if send_btn:
                                    break
                            except TimeoutException:
                                continue

                        if send_btn is None:
                            log("❌ Send button not found. Cannot send video.")
                            return

                        send_btn.click()
                        log(f"✅ Video sent to {client_phone} successfully")
                    except Exception as e:
                        log(f"❌ Error sending video: {e}")
                    finally:
                        popup.destroy()

                tk.Button(popup, text="Send Video Now", command=send_now, bg="blue", fg="white").pack(pady=5)

            root.after(500, lambda: show_send_button(driver))

        except Exception as e:
            if driver:
                driver.save_screenshot("whatsapp_debug.png")
            log(f"❌ WhatsApp error: {e}\nScreenshot saved as whatsapp_debug.png\n{traceback.format_exc()}")
        # Do not quit driver: keep WhatsApp Web session open for manual send

    threading.Thread(target=send_thread, daemon=True).start()
