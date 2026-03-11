""" import requests
from app.core.config import settings


TERMII_URL = "https://api.termii.com/api/sms/send"


def send_sms(phone_number: str, message: str):

    payload = {
        "to": phone_number,
        "from": "settings.TERMII_SENDER_ID",
        "sms": message,
        "type": "plain",
        "channel": "generic",
        "api_key": settings.TERMII_API_KEY,
    }


    try:
        requests.post(TERMII_URL, json=payload, timeout=10)
    except Exception as e:
        print("SMS sending failed:", e) """

import requests
from app.core.config import settings

TERMII_URL = "https://api.termii.com/api/sms/send"


def send_sms(phone_number: str, message: str):

    payload = {
        "to": phone_number,
        "from": "SALESZY",
        "sms": message,
        "type": "plain",
        "channel": "generic",
        "api_key": settings.TERMII_API_KEY,
    }

    print("Sending SMS to:", phone_number)
    print("Payload:", payload)

    response = requests.post(TERMII_URL, json=payload)

    print("Termii response:", response.text)