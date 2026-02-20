import requests

from app.core.config import settings


def send_password_reset_email(to_email: str, reset_link: str):
    url = "https://api.resend.com/emails"

    payload = {
        "from": settings.RESEND_FROM_EMAIL,
        "to": [to_email],
        "subject": "Reset your Simple Sales password",
        "text": f"""
Hi,

You requested to reset your password.

Click the link below to set a new password:
{reset_link}

This link will expire in {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes.

If you did not request this, you can safely ignore this email.

— Simple Sales Team
""",
    }

    headers = {
        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code >= 400:
        raise Exception(f"Email sending failed: {response.text}")