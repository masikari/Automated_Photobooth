# email_service.py
import smtplib
from email.message import EmailMessage
from settings import settings
from logger import log

# ====== DEVELOPER-SIDE SMTP CONFIG ======
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = "masikariemmanuel@gmail.com"   # developer email
SMTP_PASSWORD = "YOUR_APP_PASSWORD"         # developer email app password

# Check if admin email is set
def email_configured():
    """Check if admin email is set."""
    return bool(settings.get("email"))

# Core email sender
def send_email(to: str, subject: str, body: str) -> bool:
    if not email_configured():
        log("[EMAIL] Admin email not configured")
        return False

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = SMTP_EMAIL
        msg["To"] = to
        msg.set_content(body)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()

        log(f"[EMAIL] Email sent to {to}")
        return True

    except Exception as e:
        log(f"[EMAIL ERROR] {e}")
        return False

# Password recovery email
def send_recovery_email(to_email: str, temp_password: str) -> bool:
    subject = "360 Booth Admin Password Recovery"
    body = f"""
Hello Admin,

A password recovery request was made for your 360 Booth system.

Temporary Password:
{temp_password}

Please log in and change your password immediately.

— 360 Booth System
"""
    return send_email(to_email, subject, body)

# Session notification
def send_session_email(phone: str, amount: float) -> bool:
    admin_email = settings.get("email")
    if not admin_email:
        log("[EMAIL] Admin email not set")
        return False

    subject = "360 Booth – New Session Completed"
    body = f"""
A new booth session has been completed.

Client Phone: {phone}
Amount Paid: KES {amount}

— 360 Booth System
"""
    return send_email(admin_email, subject, body)
