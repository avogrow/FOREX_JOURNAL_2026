import os
import json
import smtplib
from email.message import EmailMessage
from datetime import datetime

def send_admin_email(subject, body):
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "0") or 0)
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASS = os.getenv("SMTP_PASS", "")
    ADMIN_NOTIFY = os.getenv("ADMIN_NOTIFICATION_EMAIL", "")

    if not (SMTP_HOST and SMTP_PORT and SMTP_USER and SMTP_PASS and ADMIN_NOTIFY):
        return False, "SMTP not fully configured. Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, and ADMIN_NOTIFICATION_EMAIL."

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = ADMIN_NOTIFY
        msg.set_content(body)

        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            server.starttls()

        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        return True, "Email sent successfully."
    except Exception as e:
        return False, str(e)


def main():
    subject = "Test registration notification"
    body = (
        "This is a test message from Forex Tracker Pro. "
        "If this arrives, your SMTP settings are working correctly."
    )
    ok, message = send_admin_email(subject, body)
    print("Success:" if ok else "Failed:", message)

    if not ok:
        log_file = "email_send_error.log"
        if os.path.exists(log_file):
            print(f"See {log_file} for details.")

if __name__ == "__main__":
    main()
