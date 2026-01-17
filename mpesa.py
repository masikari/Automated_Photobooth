import os
import base64
import json
import re
from datetime import datetime, timedelta
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# =========================
# Load .env safely
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, "env", ".env")  # your chosen structure

if not os.path.exists(dotenv_path):
    raise FileNotFoundError(f".env file not found at {dotenv_path}")

load_dotenv(dotenv_path)

# =========================
# Credentials
# =========================
class MpesaC2bCredential:
    consumer_key = os.getenv("MPESA_CONSUMER_KEY")
    consumer_secret = os.getenv("MPESA_CONSUMER_SECRET")

    oauth_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    process_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    query_url = "https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query"


class LipanaMpesaPassword:
    business_short_code = os.getenv("MPESA_BUSINESS_SHORTCODE")
    passkey = os.getenv("MPESA_PASSKEY")

    @classmethod
    def generate_password(cls):
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        data_to_encode = cls.business_short_code + cls.passkey + timestamp
        encoded_password = base64.b64encode(data_to_encode.encode()).decode('utf-8')
        return encoded_password, timestamp


# =========================
# Token cache
# =========================
_token_cache = {
    "token": None,
    "expiry": datetime.min
}

# =========================
# Logger
# =========================
def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


# =========================
# Helpers
# =========================
def normalize_phone(phone):
    phone = phone.strip()
    if phone.startswith("+"):
        phone = phone[1:]
    if phone.startswith("0"):
        phone = "254" + phone[1:]
    if re.match(r"^2547\d{8}$", phone):
        return phone
    raise ValueError("Invalid Safaricom phone number")


# =========================
# Access Token
# =========================
def get_access_token():
    now = datetime.now()

    if _token_cache["token"] and now < _token_cache["expiry"] - timedelta(seconds=10):
        return _token_cache["token"]

    try:
        r = requests.get(
            MpesaC2bCredential.oauth_url,
            auth=HTTPBasicAuth(
                MpesaC2bCredential.consumer_key,
                MpesaC2bCredential.consumer_secret
            ),
            timeout=10
        )
        r.raise_for_status()

        data = r.json()
        token = data.get("access_token")
        expires_in = int(data.get("expires_in", 3600))

        _token_cache["token"] = token
        _token_cache["expiry"] = now + timedelta(seconds=expires_in)

        log("Obtained new M-Pesa access token")
        return token

    except Exception as e:
        log(f"Error obtaining access token: {e}")
        return None


# =========================
# STK Push
# =========================
def send_stk_push(phone, amount, callback_url=None):
    if amount is None:
        raise ValueError("Amount cannot be None")

    phone = normalize_phone(phone)
    amount = int(amount)

    token = get_access_token()
    if not token:
        raise Exception("Failed to obtain access token")

    password, timestamp = LipanaMpesaPassword.generate_password()

    if not callback_url:
        callback_url = os.getenv("MPESA_CALLBACK_URL")

    if not callback_url:
        raise ValueError("MPESA_CALLBACK_URL not set in .env")

    payload = {
        "BusinessShortCode": LipanaMpesaPassword.business_short_code,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": LipanaMpesaPassword.business_short_code,
        "PhoneNumber": phone,
        "CallBackURL": callback_url,
        "AccountReference": "POOL_TABLE",
        "TransactionDesc": "Pool Table Payment"
    }

    r = requests.post(
        MpesaC2bCredential.process_url,
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30
    )
    r.raise_for_status()
    res = r.json()

    log(f"STK Push response:\n{json.dumps(res, indent=2)}")

    if res.get("ResponseCode") != "0":
        raise Exception(res.get("ResponseDescription", "STK Push rejected"))

    return res.get("CheckoutRequestID")


# =========================
# Query payment status
# =========================
def query_mpesa_status(checkout_request_id):
    token = get_access_token()
    if not token:
        log("No access token available for STK query")
        return False

    password, timestamp = LipanaMpesaPassword.generate_password()

    payload = {
        "BusinessShortCode": LipanaMpesaPassword.business_short_code,
        "Password": password,
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_request_id
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        r = requests.post(
            MpesaC2bCredential.query_url,
            json=payload,
            headers=headers,
            timeout=10
        )
        data = r.json()
        log(json.dumps(data, indent=2))
        return str(data.get("ResultCode")) == "0"

    except Exception as e:
        log(f"STK query error: {e}")
        return False
def wait_for_payment(checkout_request_id, timeout=90, interval=5):
    """
    Polls M-Pesa STK query API until payment resolves.

    Returns:
        dict {
            status: SUCCESS | FAILED | CANCELLED | TIMEOUT | ERROR
            result_code
            result_desc
        }
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        token = get_access_token()
        if not token:
            return {
                "status": "ERROR",
                "result_code": None,
                "result_desc": "No access token"
            }

        password, timestamp = LipanaMpesaPassword.generate_password()

        payload = {
            "BusinessShortCode": LipanaMpesaPassword.Business_short_code,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            resp = requests.post(
                MpesaC2bCredential.query_url,
                json=payload,
                headers=headers,
                timeout=10
            )

            data = resp.json()
            log(json.dumps(data, indent=2))

            result_code = str(data.get("ResultCode"))
            result_desc = data.get("ResultDesc")

            # SUCCESS
            if result_code == "0":
                return {
                    "status": "SUCCESS",
                    "result_code": result_code,
                    "result_desc": result_desc
                }

            # USER CANCELLED
            if result_code == "1032":
                return {
                    "status": "CANCELLED",
                    "result_code": result_code,
                    "result_desc": result_desc
                }

            # FAILED (insufficient funds, etc.)
            if result_code not in ("0", "1032"):
                return {
                    "status": "FAILED",
                    "result_code": result_code,
                    "result_desc": result_desc
                }

        except Exception as e:
            log(f"STK query exception: {e}")

        time.sleep(interval)

    return {
        "status": "TIMEOUT",
        "result_code": None,
        "result_desc": "Payment timeout"
    }
    
