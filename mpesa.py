# Handles all M-Pesa STK Push logic (sandbox & production-ready structure)
import base64
import time
import requests
import re
from datetime import datetime, timedelta
from requests.auth import HTTPBasicAuth

from config import MPESA
from logger import log

# Internal token cache
_token_cache = {
    "token": None,
    "expiry": datetime.min
}


# Utilities
def normalize_phone(phone: str) -> str | None:
    """
    Converts 07xxxxxxxx / 01xxxxxxxx to 2547xxxxxxxx / 2541xxxxxxxx
    Returns None if invalid
    """
    phone = phone.strip()
    if phone.startswith("07") or phone.startswith("01"):
        phone = "254" + phone[1:]

    if re.fullmatch(r"254[17]\d{8}", phone):
        return phone
    return None


# Access Token
def get_access_token() -> str | None:
    """
    Fetches and caches OAuth token from Safaricom
    """
    now = datetime.now()

    if _token_cache["token"] and now < _token_cache["expiry"]:
        return _token_cache["token"]

    try:
        url = (
            "https://sandbox.safaricom.co.ke/oauth/v1/generate"
            "?grant_type=client_credentials"
        )

        response = requests.get(
            url,
            auth=HTTPBasicAuth(
                MPESA["consumer_key"],
                MPESA["consumer_secret"]
            ),
            timeout=10
        )
        response.raise_for_status()

        data = response.json()
        token = data["access_token"]
        expires_in = int(data.get("expires_in", 3600))

        _token_cache["token"] = token
        _token_cache["expiry"] = now + timedelta(seconds=expires_in - 30)

        log("M-Pesa access token obtained")
        return token

    except Exception as e:
        log(f"[MPESA] Token error: {e}")
        return None


# Password Generator
def generate_password() -> tuple[str, str]:
    """
    Generates dynamic STK password + timestamp
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    raw = MPESA["shortcode"] + MPESA["passkey"] + timestamp
    password = base64.b64encode(raw.encode()).decode()
    return password, timestamp


# STK Push Initiation
def initiate_stk_push(phone: str, amount: int) -> dict | None:
    """
    Sends STK Push request
    Returns raw Safaricom response
    """
    token = get_access_token()
    if not token:
        return None

    password, timestamp = generate_password()

    payload = {
        "BusinessShortCode": MPESA["shortcode"],
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": MPESA["shortcode"],
        "PhoneNumber": phone,
        "CallBackURL": "https://example.com/callback",
        "AccountReference": "AutomatedPhotobooth",
        "TransactionDesc": "360 Booth Session"
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers=headers,
            timeout=10
        )
        data = response.json()
        log(f"[MPESA] STK Push response: {data}")
        return data

    except Exception as e:
        log(f"[MPESA] STK push error: {e}")
        return None

# STK Query
def query_stk_status(checkout_request_id: str) -> dict | None:
    """
    Queries payment status using CheckoutRequestID
    """
    token = get_access_token()
    if not token:
        return None

    password, timestamp = generate_password()

    payload = {
        "BusinessShortCode": MPESA["shortcode"],
        "Password": password,
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_request_id
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            "https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query",
            json=payload,
            headers=headers,
            timeout=10
        )
        data = response.json()
        log(f"[MPESA] STK Query: {data}")
        return data

    except Exception as e:
        log(f"[MPESA] STK query error: {e}")
        return None



# Blocking Payment Wait
def wait_for_payment(checkout_request_id: str, timeout: int = 90) -> str:
    """
    Polls STK status until SUCCESS, FAILED, or TIMEOUT
    Returns: SUCCESS | FAILED | TIMEOUT
    """
    start = time.time()

    while time.time() - start < timeout:
        time.sleep(3)

        result = query_stk_status(checkout_request_id)
        if not result:
            continue

        code = str(result.get("ResultCode"))
        desc = result.get("ResultDesc", "")

        if code == "0":
            return "SUCCESS"

        if code not in ("", "None"):
            log(f"[MPESA] Payment failed: {desc}")
            return "FAILED"

    return "TIMEOUT"
