import requests
from app.core.config import settings

TERMII_URL = "https://api.termii.com/api/sms/send"


def send_sms(phone_number: str, message: str):

    payload = {
        "to": phone_number,
        "from": settings.TERMII_SENDER_ID or "SALESZY",
        "sms": message,
        "type": "plain",
        "channel": "generic",
        "api_key": settings.TERMII_API_KEY,
    }
    

    safe_payload = payload.copy()
    safe_payload.pop("api_key", None)
    print("Sending SMS to:", phone_number)
    print("Payload:", safe_payload)

    try:
        response = requests.post(TERMII_URL, json=payload, timeout=10)
        print("Termii response:", response.text)
    except Exception as e:
        print("SMS sending failed:", e)