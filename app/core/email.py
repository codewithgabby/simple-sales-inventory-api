import smtplib
from email.message import EmailMessage

from app.core.config import settings


def send_password_reset_email(to_email: str, reset_link: str):
    msg = EmailMessage()
    msg["Subject"] = "Reset your Simple Sales password"
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to_email

    msg.set_content(
        f"""
Hi,

You requested to reset your password.

Click the link below to set a new password:
{reset_link}

This link will expire in {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes.

If you did not request this, you can safely ignore this email.

— Simple Sales Team
"""
    )

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg)
