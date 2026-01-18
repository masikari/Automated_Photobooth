import requests
import base64
import time
import re
from datetime import datetime, timedelta
from requests.auth import HTTPBasicAuth
from logger import log


class MpesaConfig:
    CONSUMER_KEY = "1iJq9SGuGYWjcmeOGICmpdPe9FU4w23sfkhzAW87eT1FiqQ2"
    CONSUMER_SECRET = "tPYL0zY4DyUr7OQftOOGU08Yhqrhu8L22EuI5LqmqG2u6uUhAEV8KGGSeSh4RV5a"

    BUSINESS_SHORTCODE = "174379"
    PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"

    BASE_URL = "https://sandbox.safaricom.co.ke"
    CALLBACK_URL = "https://example.com/mpesa/callback"  # required, even if unused


#Access Token Cache
_token = None
_token_expiry = datetime.min


def get_access_token():
    global _token, _token_expiry

    if _token and datetime.now() < _token_expiry:
        return _token

    try:
        url = f"{MpesaConfig.BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
        r = requests.get(
            url,
            auth=HTTPBasicAuth(
                MpesaConfig.CONSUMER_KEY,
                MpesaConfig.CONSUMER_SECRET
            ),
            timeout=10
        )
        r.raise_for_status()
        data = r.json()

        _token = data["access_token"]
        _token_expiry = datetime.now() + timedelta(seconds=int(data["expires_in"]) - 30)

        log("M-Pesa access token obtained")
        return _token

    except Exception as e:
        log(f"[MPESA ERROR] Access token fetch failed: {e}")
        return None


def generate_lipana_password():
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    raw = MpesaConfig.BUSINESS_SHORTCODE + MpesaConfig.PASSKEY + timestamp
    password = base64.b64encode(raw.encode()).decode()
    return password, timestamp


def is_valid_phone(phone):
    return re.match(r"^(2547|2541)\d{8}$", phone)


def query_payment_status(checkout_id):
    token = get_access_token()
    if not token:
        return False

    password, timestamp = generate_lipana_password()

    payload = {
        "BusinessShortCode": MpesaConfig.BUSINESS_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_id
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        url = f"{MpesaConfig.BASE_URL}/mpesa/stkpushquery/v1/query"
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        res = r.json()

        log(f"[MPESA QUERY] {res}")

        return str(res.get("ResultCode")) == "0"

    except Exception as e:
        log(f"[MPESA ERROR] Status query failed: {e}")
        return False


def initiate_mpesa_payment(phone, amount):
    token = get_access_token()
    if not token:
        log("[MPESA ERROR] No access token")
        return False

    password, timestamp = generate_lipana_password()

    payload = {
        "BusinessShortCode": MpesaConfig.BUSINESS_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": MpesaConfig.BUSINESS_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": MpesaConfig.CALLBACK_URL,
        "AccountReference": "360Booth",
        "TransactionDesc": "360 Booth Session"
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        url = f"{MpesaConfig.BASE_URL}/mpesa/stkpush/v1/processrequest"
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        res = r.json()

        log(f"[MPESA STK] {res}")

        if res.get("ResponseCode") != "0":
            log("[MPESA ERROR] STK push rejected")
            return False

        checkout_id = res["CheckoutRequestID"]

        # Poll for confirmation (30 seconds)
        for _ in range(30):
            time.sleep(1)
            if query_payment_status(checkout_id):
                log("Payment CONFIRMED")
                return True

        log("[MPESA ERROR] Payment not confirmed (timeout)")
        return False

    except Exception as e:
        log(f"[MPESA ERROR] STK exception: {e}")
        return False
