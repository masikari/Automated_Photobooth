import os
import base64
import json
import re
from datetime import datetime, timedelta
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# Load .env safely
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, "env", ".env")  # your chosen structure

if not os.path.exists(dotenv_path):
    raise FileNotFoundError(f".env file not found at {dotenv_path}")

load_dotenv(dotenv_path)

class MpesaConfig:
    consumer_key = os.getenv("MPESA_CONSUMER_KEY") 
    consumer_secret = os.getenv("MPESA_CONSUMER_SECRET")
    oauth_url = os.getenv("OAUTH_URL")
    process_url = os.getenv("PROCESS_URL")
    query_url = os.getenv("QUERY_URL")
    business_shortcode = os.getenv("MPESA_BUSINESS_SHORTCODE")
    passkey = os.getenv("MPESA_PASSKEY")

_token_cache = {'token': None, 'expiry': datetime.min}

def get_access_token():
    now = datetime.now()
    if _token_cache['token'] and now < _token_cache['expiry'] - timedelta(seconds=10):
        return _token_cache['token']
    try:
        r = requests.get(MpesaConfig.oauth_url,
                         auth=HTTPBasicAuth(MpesaConfig.consumer_key, MpesaConfig.consumer_secret), timeout=10)
        r.raise_for_status()
        data = r.json()
        token = data.get('access_token')
        expires_in = int(data.get('expires_in', 3600))
        _token_cache['token'] = token
        _token_cache['expiry'] = now + timedelta(seconds=expires_in)
        log('Obtained new M-Pesa access token')
        return token
    except Exception as e:
        log(f"Error obtaining access token: {e}")
        return None

def generate_lipana_password():
    lipa_time = datetime.now().strftime('%Y%m%d%H%M%S')
    data_to_encode = MpesaConfig.business_shortcode + MpesaConfig.passkey + lipa_time
    password = base64.b64encode(data_to_encode.encode()).decode('utf-8')
    return password, lipa_time

def is_valid_phone(phone): return re.match(r"^(2547|2541)\d{8}$", phone)

def query_mpesa_status(checkout_request_id):
    token = get_access_token()
    if not token: return False
    password, lipa_time = generate_lipana_password()
    payload = {"BusinessShortCode": MpesaConfig.business_shortcode, "Password": password, "Timestamp": lipa_time,
               "CheckoutRequestID": checkout_request_id}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        resp = requests.post(MpesaConfig.query_url, json=payload, headers=headers, timeout=10)
        data = resp.json()
        log(json.dumps(data, indent=2))
        return str(data.get("ResultCode")) == "0"
    except Exception as e:
        log(f"STK query error: {e}")
        return False

def initiate_mpesa_payment(phone_number, amount):
    token = get_access_token()
    if not token: return False
    password, lipa_time = generate_lipana_password()
    payload = {"BusinessShortCode": MpesaConfig.business_shortcode, "Password": password, "Timestamp": lipa_time,
               "TransactionType": "CustomerPayBillOnline", "Amount": int(amount), "PartyA": phone_number,
               "PartyB": MpesaConfig.business_shortcode, "PhoneNumber": phone_number,
               "CallBackURL": "https://sandbox.safaricom.co.ke/mpesa/",
               "AccountReference": "360Booth", "TransactionDesc": "360 Booth Payment"}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        resp = requests.post(MpesaConfig.process_url, json=payload, headers=headers, timeout=10)
        data = resp.json()
        log(json.dumps(data, indent=2))
        if data.get("ResponseCode") == "0":
            checkout_id = data.get("CheckoutRequestID")
            for _ in range(30):
                time.sleep(1)
                if query_mpesa_status(checkout_id):
                    return True
        return False
    except Exception as e:
        log(f"MPesa initiation error: {e}")
        return False

