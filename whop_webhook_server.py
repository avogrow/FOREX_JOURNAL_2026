import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from datetime import datetime
from email.message import EmailMessage
import smtplib
from flask import Flask, request, jsonify

app = Flask(__name__)

DB_PATH = os.getenv("WHOP_DB_PATH", "forex_tracker.db")
WHOP_WEBHOOK_SECRET = os.getenv("WHOP_WEBHOOK_SECRET", "")
SUBSCRIPTION_KEY_HASH_SECRET = os.getenv("SUBSCRIPTION_KEY_HASH_SECRET", "change-me")
ADMIN_NOTIFICATION_EMAIL = os.getenv("ADMIN_NOTIFICATION_EMAIL", "")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "0") or 0)
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")


def get_db_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS subscription_keys(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_hash TEXT UNIQUE,
            key_label TEXT,
            user TEXT,
            email TEXT,
            plan TEXT,
            expires TEXT,
            active INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS whop_webhook_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            webhook_id TEXT UNIQUE,
            event_type TEXT,
            received_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def get_hash_secret_bytes():
    return SUBSCRIPTION_KEY_HASH_SECRET.encode("utf-8")


def hash_subscription_key(key: str) -> str:
    return hmac.new(get_hash_secret_bytes(), key.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_whop_webhook(raw_body: str, headers: dict) -> dict:
    if not WHOP_WEBHOOK_SECRET:
        raise ValueError("WHOP_WEBHOOK_SECRET is not configured.")

    webhook_id = headers.get("webhook-id") or headers.get("Webhook-Id")
    webhook_timestamp = headers.get("webhook-timestamp") or headers.get("Webhook-Timestamp")
    webhook_signature = headers.get("webhook-signature") or headers.get("Webhook-Signature")

    if not webhook_id or not webhook_timestamp or not webhook_signature:
        raise ValueError("Missing Whop webhook signature headers.")

    if "," in webhook_signature:
        _, received_sig = webhook_signature.split(",", 1)
    else:
        received_sig = webhook_signature

    try:
        secret_bytes = base64.b64decode(WHOP_WEBHOOK_SECRET)
    except Exception as exc:
        raise ValueError("Invalid WHOP_WEBHOOK_SECRET format; must be base64-encoded.") from exc

    signed_content = f"{webhook_id}.{webhook_timestamp}.{raw_body}".encode("utf-8")
    expected_sig = base64.b64encode(
        hmac.new(secret_bytes, signed_content, hashlib.sha256).digest()
    ).decode("utf-8")

    if not hmac.compare_digest(received_sig, expected_sig):
        raise ValueError("Invalid Whop webhook signature.")

    try:
        return json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise ValueError("Could not parse JSON payload") from exc


def save_webhook_event(webhook_id: str, event_type: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO whop_webhook_events(webhook_id, event_type, received_at) VALUES (?, ?, ?)",
            (webhook_id, event_type, datetime.utcnow().isoformat())
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def add_or_update_subscription_key(key: str, user: str, email: str, plan: str, expires: str, active: bool = True) -> bool:
    key_hash = hash_subscription_key(key)
    now = datetime.utcnow().isoformat()
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT id FROM subscription_keys WHERE key_hash = ?",
            (key_hash,)
        )
        if cursor.fetchone():
            cursor.execute(
                "UPDATE subscription_keys SET user = ?, email = ?, plan = ?, expires = ?, active = ?, updated_at = ? WHERE key_hash = ?",
                (user, email, plan, expires, 1 if active else 0, now, key_hash)
            )
        else:
            cursor.execute(
                "INSERT INTO subscription_keys(key_hash, key_label, user, email, plan, expires, active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (key_hash, key_hash[:8], user, email, plan, expires, 1 if active else 0, now, now)
            )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def build_provisioning_metadata(payload: dict) -> dict:
    event_type = payload.get("type", "")
    data = payload.get("data") or {}

    if isinstance(data, dict) and data.get("type") and data.get("data"):
        data = data.get("data")

    # Extract user and membership details
    user = data.get("user") or data.get("member") or {}
    membership = data.get("membership") or {}

    email = user.get("email") or member_email_from_payload(data)
    name = user.get("name") or user.get("username") or "Whop customer"
    plan = ""
    expires = ""

    if isinstance(data.get("plan"), dict):
        plan = data["plan"].get("id") or data["plan"].get("name") or ""

    if isinstance(membership, dict):
        expires_at = membership.get("renewal_period_end") or membership.get("updated_at") or membership.get("created_at")
        if expires_at:
            expires = expires_at.split("T")[0]
        if not plan and isinstance(membership.get("plan"), dict):
            plan = membership["plan"].get("id") or membership["plan"].get("name") or plan

    if not expires and isinstance(data.get("renewal_period_end"), str):
        expires = data["renewal_period_end"].split("T")[0]

    if not expires and event_type == "payment.succeeded":
        expires = ""

    if not email:
        email = ""

    return {
        "email": email,
        "user": name,
        "plan": plan,
        "expires": expires,
        "event_type": event_type
    }


def member_email_from_payload(data: dict) -> str:
    member = data.get("member") or {}
    if isinstance(member, dict):
        return member.get("email") or member.get("user", {}).get("email") or ""
    return ""


def send_admin_notification(subject: str, body: str) -> bool:
    if not (SMTP_HOST and SMTP_PORT and SMTP_USER and SMTP_PASS and ADMIN_NOTIFICATION_EMAIL):
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = ADMIN_NOTIFICATION_EMAIL
    msg.set_content(body)

    try:
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        return True
    except Exception:
        return False


def make_license_key() -> str:
    return f"FOREX-{secrets.token_hex(4).upper()}"


@app.route("/whop-webhook", methods=["POST"])
def whop_webhook():
    raw_body = request.get_data(as_text=True)

    try:
        event = verify_whop_webhook(raw_body, dict(request.headers))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    webhook_id = request.headers.get("webhook-id") or request.headers.get("Webhook-Id")
    event_type = event.get("type") or "unknown"
    if not webhook_id:
        return jsonify({"error": "Missing webhook-id header."}), 400

    if not save_webhook_event(webhook_id, event_type):
        return jsonify({"status": "duplicate", "message": "Event already processed."}), 200

    if event_type not in {"payment.succeeded", "membership.activated"}:
        return jsonify({"status": "ignored", "event_type": event_type}), 200

    payload_data = event.get("data") or {}
    license_key = ""
    if isinstance(payload_data, dict):
        license_key = payload_data.get("license_key") or payload_data.get("membership", {}).get("license_key") or ""

    metadata = build_provisioning_metadata(event)
    if not license_key:
        license_key = make_license_key()

    success = add_or_update_subscription_key(
        license_key,
        metadata["user"],
        metadata["email"],
        metadata["plan"],
        metadata["expires"],
        active=True
    )

    if success:
        subject = f"Whop purchase provisioned: {license_key}"
        body = (
            f"Whop event received: {event_type}\n"
            f"License key: {license_key}\n"
            f"Customer: {metadata['user']}\n"
            f"Email: {metadata['email']}\n"
            f"Plan: {metadata['plan']}\n"
            f"Expires: {metadata['expires']}\n"
            f"Webhook ID: {webhook_id}\n"
        )
        send_admin_notification(subject, body)
        return jsonify({"status": "provisioned", "license_key": license_key}), 200

    return jsonify({"error": "Unable to provision subscription key."}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    init_tables()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "4243")), debug=True)
