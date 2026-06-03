import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
import csv
import os
import json
import smtplib
import hashlib
import hmac
import secrets
from email.message import EmailMessage
import numpy as np
from reportlab.platypus import SimpleDocTemplate, Paragraph

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ==================================
# CONFIG
# ==================================
st.set_page_config(
    page_title="Forex Tracker Pro",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Forex Tracker Pro Ultimate")
st.markdown(
    "A polished forex trade journal to log entries, review quality, and track performance with clean dashboards and actionable analytics."
)
st.markdown(
    "Use the tabs to navigate between Dashboard, Journal, Analytics, Risk, Compounding, Goals, Psychology, and Admin tools."
)
st.markdown("---")

TERMS_AND_CONDITIONS = '''
Forex Tracker Pro is a personal trading journal and performance tracking tool. By using this app to save trade details, you agree to the following terms:

1. Personal Use Only
   - This app is designed for your personal trade journaling, analysis, and record-keeping.
   - It does not provide financial advice, investment recommendations, or trading signals.
   - You are solely responsible for all trading decisions and outcomes.

2. No Guarantee of Accuracy
   - Data entered into the app is user-provided. The app may display calculated metrics based on your input, but it does not verify accuracy.
   - Screenshots uploaded are stored locally in the screenshots folder and are not reviewed or validated by the app.

3. Liability and Risk
   - The app owner and developers are not liable for any losses, damages, or claims resulting from your use of this app.
   - Past results, performance dashboards, and simulated metrics are not guarantees of future performance.

4. Privacy and Data Storage
   - Your trade logs and uploads are stored locally or in the configured database.
   - You are responsible for protecting any personally identifiable information or sensitive data you provide.

5. Subscription and Access
   - Access to the app may require a valid subscription key.
   - Any admin or email notification features are provided as convenience tools and are subject to your local configuration.

6. Acceptance
   - By checking the acceptance box and saving a trade, you confirm that you have read, understood, and agreed to these Terms and Conditions.
'''

os.makedirs("screenshots", exist_ok=True)

# ==================================
# SUBSCRIPTION GATE
# ==================================
VALID_KEYS_ENV = os.getenv("VALID_SUBSCRIPTION_KEYS", "")
SUBSCRIPTION_LINK = os.getenv("SUBSCRIPTION_PAYMENT_LINK", "")
WHOP_CHECKOUT_URL = os.getenv("WHOP_CHECKOUT_URL", "https://whop.com/sustainable-journal")
SUBSCRIPTION_BACKEND_URL = os.getenv("SUBSCRIPTION_BACKEND_URL", "")
WHOP_WEBHOOK_SECRET = os.getenv("WHOP_WEBHOOK_SECRET", "")
ONE_TIME_PRICE = os.getenv("ONE_TIME_PRICE", "10")
ONE_TIME_CURRENCY = os.getenv("ONE_TIME_CURRENCY", "$")
WHATSAPP_PROOF_URL = os.getenv("WHATSAPP_PROOF_URL", "https://wa.me/254729425630?text=Hi%20Dennis!%20I%20just%20paid%20for%20the%20Journal.%20Please%20find%20my%20proof%20of%20payment%20attached.")
KEY_HASH_SECRET = os.getenv("SUBSCRIPTION_KEY_HASH_SECRET", "change-me")
KEY_HASH_ALGORITHM = "sha256"
VALID_KEYS_TXT = os.path.join(BASE_DIR, "valid_subscription_keys.txt")
VALID_KEYS_CSV = os.path.join(BASE_DIR, "valid_subscription_keys.csv")
SUB_KEYS_BACKUP_TXT = os.path.join(BASE_DIR, "backup_valid_subscription_keys.txt")
SUB_KEYS_BACKUP_CSV = os.path.join(BASE_DIR, "backup_valid_subscription_keys.csv")
REGISTRATION_REQUESTS_JSON = os.path.join(BASE_DIR, "subscription_registration_requests.json")
REGISTRATION_REQUESTS_CSV = os.path.join(BASE_DIR, "subscription_registration_requests.csv")


def load_csv_subscription_keys():

    keys = {}

    if not os.path.exists(VALID_KEYS_CSV):
        return keys

    try:
        with open(VALID_KEYS_CSV, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = str(row.get("key", "")).strip()
                if not key or key.startswith("#"):
                    continue

                expires = str(row.get("expires", "")).strip()
                active = str(row.get("active", "true")).strip().lower() in (
                    "1",
                    "true",
                    "yes",
                    "y"
                )

                keys[key] = {
                    "key": key,
                    "user": str(row.get("user", "")).strip(),
                    "email": str(row.get("email", "")).strip(),
                    "plan": str(row.get("plan", "")).strip(),
                    "expires": expires,
                    "active": active,
                    "source": "csv"
                }
    except Exception:
        pass

    return keys


def hash_subscription_key(key):

    if not key:
        return ""

    return hmac.new(
        KEY_HASH_SECRET.encode("utf-8"),
        key.encode("utf-8"),
        getattr(hashlib, KEY_HASH_ALGORITHM)
    ).hexdigest()


def _get_admin_otp_history():

    raw_history = st.session_state.get("admin_otp_history", [])
    parsed = []
    for entry in raw_history:
        try:
            parsed.append(datetime.fromisoformat(entry))
        except Exception:
            pass
    return parsed


def can_send_admin_otp():

    history = [ts for ts in _get_admin_otp_history() if datetime.now() - ts <= timedelta(minutes=15)]
    st.session_state["admin_otp_history"] = [ts.isoformat() for ts in history]
    if len(history) >= 3:
        return False
    return True


def record_admin_otp_request():

    history = [ts.isoformat() for ts in _get_admin_otp_history()]
    history.append(datetime.now().isoformat())
    st.session_state["admin_otp_history"] = history


def can_attempt_admin_otp_verify():

    raw_history = st.session_state.get("admin_otp_verify_attempts", [])
    attempts = []
    for entry in raw_history:
        try:
            attempts.append(datetime.fromisoformat(entry))
        except Exception:
            pass

    attempts = [ts for ts in attempts if datetime.now() - ts <= timedelta(minutes=10)]
    st.session_state["admin_otp_verify_attempts"] = [ts.isoformat() for ts in attempts]
    return len(attempts) < 5


def record_admin_otp_verify_attempt():

    history = [ts.isoformat() for ts in st.session_state.get("admin_otp_verify_attempts", []) if ts]
    history.append(datetime.now().isoformat())
    st.session_state["admin_otp_verify_attempts"] = history


def create_subscription_keys_table():

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
    conn.commit()


def get_db_subscription_metadata(key):

    if not key:
        return None

    key_hash = hash_subscription_key(key)
    cursor.execute(
        "SELECT key_hash, key_label, user, email, plan, expires, active FROM subscription_keys WHERE key_hash = ?",
        (key_hash,)
    )
    row = cursor.fetchone()

    if not row:
        return None

    return {
        "key_hash": row[0],
        "key_label": row[1],
        "user": row[2],
        "email": row[3],
        "plan": row[4],
        "expires": row[5],
        "active": bool(row[6]),
        "source": "db"
    }


def get_all_db_subscription_keys():

    cursor.execute(
        "SELECT id, key_hash, key_label, user, email, plan, expires, active, created_at, updated_at FROM subscription_keys ORDER BY id DESC"
    )
    rows = cursor.fetchall()

    keys = []
    for row in rows:
        keys.append({
            "id": row[0],
            "key_hash": row[1],
            "key_label": row[2],
            "user": row[3],
            "email": row[4],
            "plan": row[5],
            "expires": row[6],
            "active": bool(row[7]),
            "created_at": row[8],
            "updated_at": row[9]
        })

    return keys


def set_db_subscription_key(key, user, email, plan, expires, active=True):

    key_hash = hash_subscription_key(key)
    key_label = key_hash[:8]
    now = datetime.now().isoformat()

    try:
        cursor.execute(
            "INSERT OR REPLACE INTO subscription_keys(key_hash, key_label, user, email, plan, expires, active, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (
                key_hash,
                key_label,
                user,
                email,
                plan,
                expires,
                1 if active else 0,
                now,
                now
            )
        )
        conn.commit()
        return True
    except Exception:
        return False


def update_db_subscription_key(key_hash, user, email, plan, expires, active=True):

    now = datetime.now().isoformat()
    try:
        cursor.execute(
            "UPDATE subscription_keys SET user = ?, email = ?, plan = ?, expires = ?, active = ?, updated_at = ? WHERE key_hash = ?",
            (
                user,
                email,
                plan,
                expires,
                1 if active else 0,
                now,
                key_hash,
            )
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        return False


def delete_db_subscription_key(key_hash):

    try:
        cursor.execute(
            "DELETE FROM subscription_keys WHERE key_hash = ?",
            (key_hash,)
        )
        conn.commit()
        return True
    except Exception:
        return False


def export_subscription_keys_backup():

    keys = get_all_db_subscription_keys()
    try:
        with open(SUB_KEYS_BACKUP_JSON := "backup_subscription_keys.json", "w", encoding="utf-8") as f:
            json.dump(keys, f, indent=2)
        with open(SUB_KEYS_BACKUP_CSV, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "key_hash", "key_label", "user", "email", "plan", "expires", "active", "created_at", "updated_at"])
            writer.writeheader()
            for entry in keys:
                writer.writerow(entry)
        return True
    except Exception:
        return False


def get_subscription_keys_map():

    keys = {}

    if VALID_KEYS_ENV:
        for k in [x.strip() for x in VALID_KEYS_ENV.split(",") if x.strip()]:
            keys[k] = {
                "key": k,
                "user": "",
                "email": "",
                "plan": "",
                "expires": "",
                "active": True,
                "source": "env"
            }

    try:
        seckeys = st.secrets["valid_subscription_keys"]

        if isinstance(seckeys, str):
            for k in [x.strip() for x in seckeys.split(",") if x.strip()]:
                keys.setdefault(k, {
                    "key": k,
                    "user": "",
                    "email": "",
                    "plan": "",
                    "expires": "",
                    "active": True,
                    "source": "secrets"
                })
        elif isinstance(seckeys, list):
            for k in seckeys:
                k = str(k).strip()
                if k:
                    keys.setdefault(k, {
                        "key": k,
                        "user": "",
                        "email": "",
                        "plan": "",
                        "expires": "",
                        "active": True,
                        "source": "secrets"
                    })
    except Exception:
        pass

    if os.path.exists(VALID_KEYS_TXT):
        try:
            with open(VALID_KEYS_TXT, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        keys.setdefault(line, {
                            "key": line,
                            "user": "",
                            "email": "",
                            "plan": "",
                            "expires": "",
                            "active": True,
                            "source": "txt"
                        })
        except Exception:
            pass

    csv_keys = load_csv_subscription_keys()
    keys.update(csv_keys)

    return keys


def get_valid_subscription_keys():
    return list(get_subscription_keys_map().keys())


def get_subscription_metadata(key):
    if not key:
        return None

    db_meta = get_db_subscription_metadata(key)
    if db_meta:
        return db_meta

    return get_subscription_keys_map().get(key)


def is_subscription_key_valid(key):
    if not key:
        return False

    meta = get_subscription_metadata(key)
    if not meta:
        return False

    if not meta.get("active", True):
        return False

    expires = meta.get("expires", "")
    if expires:
        try:
            expiry_date = datetime.strptime(expires, "%Y-%m-%d").date()
            if expiry_date < datetime.now().date():
                return False
        except Exception:
            pass

    return True


def save_subscription_csv(keys_map):

    fieldnames = ["key", "user", "email", "plan", "expires", "active"]

    try:
        with open(VALID_KEYS_CSV, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for k, meta in keys_map.items():
                row = {
                    "key": k,
                    "user": meta.get("user", ""),
                    "email": meta.get("email", ""),
                    "plan": meta.get("plan", ""),
                    "expires": meta.get("expires", ""),
                    "active": "TRUE" if meta.get("active", True) else "FALSE"
                }
                writer.writerow(row)

        return True
    except Exception:
        return False


def save_subscription_txt(keys_map):

    try:
        with open(VALID_KEYS_TXT, "w", encoding="utf-8") as f:
            for k, meta in keys_map.items():
                if meta.get("active", True):
                    f.write(f"{k}\n")
        return True
    except Exception:
        return False


def save_registration_request(request_data):

    try:
        with open(REGISTRATION_REQUESTS_JSON, "a", encoding="utf-8") as f:
            f.write(json.dumps(request_data, ensure_ascii=False) + "\n")
    except Exception:
        pass

    try:
        write_header = not os.path.exists(REGISTRATION_REQUESTS_CSV)
        with open(REGISTRATION_REQUESTS_CSV, "a", encoding="utf-8", newline="") as f:
            fieldnames = ["time", "name", "email", "plan", "notes", "checkout_url"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()
            writer.writerow({
                "time": request_data.get("time", ""),
                "name": request_data.get("name", ""),
                "email": request_data.get("email", ""),
                "plan": request_data.get("plan", ""),
                "notes": request_data.get("notes", ""),
                "checkout_url": request_data.get("checkout_url", "")
            })
    except Exception:
        pass

    return True


def load_registration_requests():

    requests_list = []
    if not os.path.exists(REGISTRATION_REQUESTS_JSON):
        return requests_list

    try:
        with open(REGISTRATION_REQUESTS_JSON, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    requests_list.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        pass

    return requests_list


def log_admin_action(action, key, meta, admin_user="admin"):
    """Append an audit line to subscription_admin_audit.log"""
    try:
        entry = {
            "time": datetime.now().isoformat(),
            "action": action,
            "admin": admin_user,
            "key": key,
            "meta": meta
        }

        with open("subscription_admin_audit.log", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        return True
    except Exception:
        return False


def send_admin_email(subject, body):
    """Send notification email to admin notification address if configured."""
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "0") or 0)
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASS = os.getenv("SMTP_PASS", "")
    ADMIN_NOTIFY = os.getenv("ADMIN_NOTIFICATION_EMAIL", "")

    if not (SMTP_HOST and SMTP_PORT and SMTP_USER and SMTP_PASS and ADMIN_NOTIFY):
        try:
            with open("email_send_error.log", "a", encoding="utf-8") as ef:
                ef.write(json.dumps({"time": datetime.now().isoformat(), "error": "SMTP not fully configured"}) + "\n")
        except Exception:
            pass
        return False

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
        return True
    except Exception as e:
        # log error details to a local logfile for diagnostics (do not expose secrets)
        try:
            import traceback
            err = {"time": datetime.now().isoformat(), "error": str(e), "trace": traceback.format_exc()}
            with open("email_send_error.log", "a", encoding="utf-8") as ef:
                ef.write(json.dumps(err) + "\n")
        except Exception:
            pass
        return False


TEMPLATES_FILE = "admin_email_templates.json"


def load_email_templates():
    default = {
        "add": {
            "subject": "Subscription key added: {key}",
            "body": "Admin {admin} added key {key} for user {user} ({email}) plan={plan} expires={expires}"
        },
        "update": {
            "subject": "Subscription key updated: {key}",
            "body": "Admin {admin} updated key {key}: user={user} email={email} plan={plan} expires={expires} active={active}"
        },
        "remove": {
            "subject": "Subscription key removed: {key}",
            "body": "Admin {admin} removed key {key}"
        },
        "otp": {
            "subject": "Your admin login code",
            "body": "Your admin login code is: {code} (valid for 10 minutes)"
        },
        "registration_request": {
            "subject": "New registration request: {name}",
            "body": "A new registration request was submitted by {name} ({email}) for plan {plan}. Notes: {notes}"
        }
    }

    if not os.path.exists(TEMPLATES_FILE):
        try:
            with open(TEMPLATES_FILE, "w", encoding="utf-8") as f:
                json.dump(default, f, indent=2)
        except Exception:
            pass
        return default

    try:
        with open(TEMPLATES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {**default, **data}
    except Exception:
        return default


def save_email_templates(data):
    try:
        with open(TEMPLATES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def get_last_email_error():
    """Return a short last error message from email_send_error.log if present."""
    path = "email_send_error.log"
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        if not lines:
            return ""
        last = json.loads(lines[-1])
        return last.get("error", "")
    except Exception:
        return ""


def get_current_subscription_key():

    if "subscription_key" in st.session_state and st.session_state[
        "subscription_key"
    ]:
        return st.session_state["subscription_key"]

    try:
        return st.secrets.get("subscription_key", "")
    except Exception:
        return ""


def get_checkout_url_from_backend():

    if not SUBSCRIPTION_BACKEND_URL:
        return ""

    endpoint = SUBSCRIPTION_BACKEND_URL.strip().rstrip("/")
    if not endpoint.endswith("/create-checkout-session"):
        endpoint = f"{endpoint}/create-checkout-session"

    try:
        response = requests.post(endpoint, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("url", "")
    except Exception:
        return ""


def get_subscription_payment_link():
    return WHOP_CHECKOUT_URL or SUBSCRIPTION_LINK


def render_enrollment_page():
    provider_link = get_subscription_payment_link()
    checkout_url = st.session_state.get("checkout_url", "")

    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown("## Journal Your Trading Journey.")
        st.write("Forex Tracker Pro Ultimate helps serious traders capture every move, stay accountable, and improve performance with an intuitive journal. Whether you're a discretionary trader or systematically executing Smart Money concepts, this journal is designed to grow with you.")

        st.markdown("### Why traders choose this Journal")
        st.markdown(
            "- 🧠 Psychology tracking to capture mood, discipline, confidence, and emotional triggers\n"
            "- 🎯 Goal setting for daily, weekly, and monthly trading targets\n"
            "- 🔍 Trade review that forces accountability and improves decision-making\n"
            "- 🛡️ Risk management tracking for position sizing, stop loss, and reward/risk discipline\n"
            "- 📈 Performance analytics that turn intuition into real trading data\n"
            "- 📸 Screenshot uploads to capture charts, setups, and market conditions\n"
        )

        st.markdown("### Why this makes the Journal stronger")
        st.markdown(
            "- Traders stop trading from memory and start trading from evidence.\n"
            "- Emotional patterns become visible and improvable instead of hidden and repeated.\n"
            "- Goals and progress turn habits into momentum, not random setups.\n"
        )

        st.markdown("---")
        st.markdown("### How to get access")
        if provider_link:
            st.markdown(f"[👉 Get Instant Access]({provider_link})")
            if WHOP_WEBHOOK_SECRET:
                st.info(
                    "Automatic Whop provisioning is configured. "
                    "After a successful purchase, your webhook backend can provision a license key automatically."
                )
        elif checkout_url:
            st.markdown(f"[👉 Get Instant Access]({checkout_url})")
            st.write("A checkout session link has been generated. Complete payment to receive access.")
        else:
            st.info(
                "No direct checkout link is configured. Use the bank transfer option below or set `WHOP_CHECKOUT_URL` / `SUBSCRIPTION_PAYMENT_LINK` in secrets."
            )


def require_terms_agreement():
    if st.session_state.get("terms_accepted", False):
        return

    st.markdown("# Terms and Agreement")
    st.markdown(TERMS_AND_CONDITIONS)
    terms_checkbox = st.checkbox(
        "I have read and agree to the Terms and Conditions",
        value=False,
        key="terms_agreement_prompt"
    )

    if terms_checkbox:
        st.session_state["terms_accepted"] = True
        st.success("Thank you. You may now continue using the app.")
        if hasattr(st, "rerun"):
            st.rerun()
        elif hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
        else:
            st.stop()

    st.warning("You must accept the Terms and Conditions before logging in or using the app.")
    st.stop()


def show_subscription_gate():

    current_key = get_current_subscription_key()
    valid = is_subscription_key_valid(current_key)

    if valid:
        if not st.session_state.get("terms_accepted", False):
            require_terms_agreement()
        return

    st.sidebar.header("Unlock access")
    st.sidebar.write("Enter your license key below or choose a payment option on the main page.")

    subscription_key = st.sidebar.text_input(
        "License key",
        value=current_key,
        type="password",
        key="subscription_key_input"
    )

    if st.sidebar.button("Unlock app"):
        if is_subscription_key_valid(subscription_key):
            st.session_state["subscription_key"] = subscription_key
            st.rerun()
        else:
            st.sidebar.error("Invalid license key.")

    render_enrollment_page()

    st.sidebar.markdown("---")
    st.sidebar.subheader("New here? Request support")
    with st.sidebar.form("new_user_registration_form"):
        reg_name = st.text_input("Full name")
        reg_email = st.text_input("Email")
        reg_plan = st.selectbox("Desired plan", ["monthly", "annual", "lifetime", "custom"], index=2)
        reg_notes = st.text_area("Tell us why you want access")
        reg_submit = st.form_submit_button("Request registration")

    if reg_submit:
        if not reg_name or not reg_email:
            st.sidebar.error("Please provide both name and email.")
        else:
            provider_link = get_subscription_payment_link()
            pending_data = {
                "time": datetime.now().isoformat(),
                "name": reg_name,
                "email": reg_email,
                "plan": reg_plan,
                "notes": reg_notes,
                "checkout_url": provider_link or ""
            }
            save_registration_request(pending_data)

            tpl = load_email_templates().get("registration_request", {})
            subject = tpl.get("subject", "New registration request: {name}").format(name=reg_name)
            body = tpl.get(
                "body",
                "A new registration request was submitted by {name} ({email}) for plan {plan}. Notes: {notes}"
            ).format(
                name=reg_name,
                email=reg_email,
                plan=reg_plan,
                notes=reg_notes or "N/A"
            )

            email_ok = send_admin_email(subject, body)
            if email_ok:
                st.sidebar.success("Request submitted. Admin has been notified.")
            else:
                err = get_last_email_error()
                msg = "Request saved, but email notification is not configured or failed."
                if err:
                    msg = f"{msg} Error: {err}"
                st.sidebar.warning(msg)

    st.stop()


# ==================================
# DATABASE
# ==================================
conn = sqlite3.connect(
    "forex_tracker.db",
    check_same_thread=False
)

cursor = conn.cursor()

create_subscription_keys_table()

show_subscription_gate()

# ==================================
# MAIN TABLE
# ==================================
cursor.execute("""
CREATE TABLE IF NOT EXISTS trades(
id INTEGER PRIMARY KEY AUTOINCREMENT,

date TEXT,

symbol TEXT,

direction TEXT,

entry REAL,

exit REAL,

lot REAL,

profit REAL,

commission REAL DEFAULT 0,

setup TEXT,

notes TEXT,

risk REAL DEFAULT 0,

r_multiple REAL DEFAULT 0,

session TEXT,

timeframe TEXT,

setup_score INTEGER DEFAULT 0,

tags TEXT,

mistake_type TEXT,

entry_time TEXT,

exit_time TEXT,

duration REAL DEFAULT 0,

screenshot TEXT,

subscription_key TEXT,

ai_review TEXT
)
""")

conn.commit()

create_subscription_keys_table()

# ==================================
# PSYCHOLOGY JOURNAL TABLE
# ==================================
cursor.execute("""
CREATE TABLE IF NOT EXISTS psych_journal(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    mood TEXT,
    note TEXT,
    subscription_key TEXT
)
""")

conn.commit()

# ==================================
# SAFE COLUMN MIGRATION
# ==================================
def add_column_if_missing(column_name, definition):

    try:
        cursor.execute(
            f"ALTER TABLE trades ADD COLUMN {column_name} {definition}"
        )
        conn.commit()
    except:
        pass

add_column_if_missing("commission", "REAL DEFAULT 0")
add_column_if_missing("risk", "REAL DEFAULT 0")
add_column_if_missing("r_multiple", "REAL DEFAULT 0")
add_column_if_missing("session", "TEXT")
add_column_if_missing("timeframe", "TEXT")
add_column_if_missing("setup_score", "INTEGER DEFAULT 0")
add_column_if_missing("tags", "TEXT")
add_column_if_missing("mistake_type", "TEXT")
add_column_if_missing("entry_time", "TEXT")
add_column_if_missing("exit_time", "TEXT")
add_column_if_missing("duration", "REAL DEFAULT 0")
add_column_if_missing("screenshot", "TEXT")
add_column_if_missing("subscription_key", "TEXT")
add_column_if_missing("ai_review", "TEXT")

# ==================================
# LOAD DATA
# ==================================
def load_trades():

    current_key = get_current_subscription_key()
    df = pd.read_sql(
        "SELECT * FROM trades WHERE subscription_key = ? ORDER BY date ASC",
        conn,
        params=(current_key,)
    )

    if len(df):

        df["profit"] = pd.to_numeric(
            df["profit"],
            errors="coerce"
        ).fillna(0)

        if "commission" in df.columns:
            df["commission"] = pd.to_numeric(
                df["commission"],
                errors="coerce"
            ).fillna(0)

        df["equity"] = df["profit"].cumsum()

        df["running_max"] = (
            df["equity"]
            .cummax()
        )

        df["drawdown"] = (
            df["equity"]
            - df["running_max"]
        )

    return df

def parse_time_string(time_str):
    try:
        if pd.isna(time_str) or not str(time_str).strip():
            return datetime.now().time()
        try:
            return datetime.strptime(str(time_str), "%H:%M:%S").time()
        except ValueError:
            return datetime.strptime(str(time_str), "%H:%M").time()
    except Exception:
        return datetime.now().time()


def calc_metrics(df):

    if df.empty:
        return {
            "total_profit": 0,
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "largest_win": 0,
            "largest_loss": 0,
            "profit_factor": 0,
            "expectancy": 0,
            "avg_r": 0,
            "total_commission": 0,
            "avg_commission": 0,
            "max_dd": 0,
            "recovery_factor": 0,
            "max_win_streak": 0,
            "max_loss_streak": 0
        }

    wins_df = df[df["profit"] > 0]
    losses_df = df[df["profit"] < 0]

    wins = len(wins_df)
    losses = len(losses_df)

    total_profit = df["profit"].sum()
    total_trades = len(df)

    win_rate = (
        wins / total_trades * 100
        if total_trades > 0 else 0
    )

    avg_win = (
        wins_df["profit"].mean()
        if wins > 0 else 0
    )

    avg_loss = (
        losses_df["profit"].mean()
        if losses > 0 else 0
    )

    largest_win = (
        wins_df["profit"].max()
        if wins > 0 else 0
    )

    largest_loss = (
        losses_df["profit"].min()
        if losses > 0 else 0
    )

    gross_profit = wins_df["profit"].sum()

    gross_loss = abs(
        losses_df["profit"].sum()
    )

    profit_factor = (
        gross_profit / gross_loss
        if gross_loss > 0 else 0
    )

    expectancy = (
        total_profit / total_trades
        if total_trades > 0 else 0
    )

    avg_r = (
        df["r_multiple"].mean()
        if "r_multiple" in df.columns
        else 0
    )

    total_commission = (
        df["commission"].sum()
        if "commission" in df.columns
        else 0
    )

    avg_commission = (
        df["commission"].mean()
        if "commission" in df.columns and len(df) > 0
        else 0
    )

    max_dd = (
        abs(df["drawdown"].min())
        if "drawdown" in df.columns
        else 0
    )

    recovery_factor = (
        total_profit / max_dd
        if max_dd > 0 else 0
    )

    max_win_streak = 0
    max_loss_streak = 0

    current_win = 0
    current_loss = 0

    for p in df["profit"]:

        if p > 0:

            current_win += 1
            current_loss = 0

        elif p < 0:

            current_loss += 1
            current_win = 0

        max_win_streak = max(
            max_win_streak,
            current_win
        )

        max_loss_streak = max(
            max_loss_streak,
            current_loss
        )

    return {
        "total_profit": total_profit,
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "largest_win": largest_win,
        "largest_loss": largest_loss,
        "profit_factor": profit_factor,
        "expectancy": expectancy,
        "avg_r": avg_r,
        "total_commission": total_commission,
        "avg_commission": avg_commission,
        "max_dd": max_dd,
        "recovery_factor": recovery_factor,
        "max_win_streak": max_win_streak,
        "max_loss_streak": max_loss_streak
    }

# ==================================
# LOAD DATA
# ==================================
df = load_trades()
metrics = calc_metrics(df)

with st.sidebar:
    st.header("Quick Snapshot")
    st.metric("Trades", metrics["total_trades"])
    st.metric("Net Profit", f"${metrics['total_profit']:,.2f}")
    st.metric("Win Rate", f"{metrics['win_rate']:.1f}%")
    # Account size and balance
    account_size = st.session_state.get("account_size", None)
    account_size = st.number_input("Account Size (USD)", value=float(account_size) if account_size else 10000.0, step=100.0, format="%.2f", key="account_size")
    balance = account_size + metrics['total_profit']
    st.metric("Account Balance", f"${balance:,.2f}")

    saved_account = st.session_state.get("account_id", "")
    if saved_account:
        st.markdown(f"**Account:** `{saved_account}`")
    else:
        st.markdown("**Account:** _not set_")
    st.markdown("---")
    # Average trade duration
    avg_duration = 0
    if "duration" in df.columns and len(df) > 0:
        try:
            avg_duration = float(df['duration'].mean())
        except Exception:
            avg_duration = 0
    # display avg duration in minutes, and as hh:mm if >60
    if avg_duration >= 60:
        hours = int(avg_duration // 60)
        minutes = int(avg_duration % 60)
        dur_str = f"{hours}h {minutes}m"
    else:
        dur_str = f"{avg_duration:.0f}m"
    st.metric("Avg Duration", dur_str)
    st.markdown("Tip: Save the Account ID from the Dashboard tab to lock this report.")

# ==================================
# TABS
# ==================================
(
    dashboard,
    journal,
    analytics,
    risk,
    compounding,
    goals,
    psychology,
    admin
) = st.tabs([
    "📊 Dashboard",
    "📖 Journal",
    "📈 Analytics",
    "🛡 Risk",
    "💰 Compounding",
    "🎯 Goals",
    "🧠 Psychology",
    "🔧 Admin"
])

# ==================================
# TELEGRAM
# ==================================
def send_telegram(message):

    BOT_TOKEN = "YOUR_BOT_TOKEN"
    CHAT_ID = "YOUR_CHAT_ID"

    if BOT_TOKEN == "YOUR_BOT_TOKEN":
        return

    try:

        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": message
            }
        )

    except:
        pass

# ==================================
# WIN STREAKS
# ==================================
def calculate_streaks(df):

    max_win = 0
    max_loss = 0

    current_win = 0
    current_loss = 0

    for p in df["profit"]:

        if p > 0:

            current_win += 1
            current_loss = 0

        elif p < 0:

            current_loss += 1
            current_win = 0

        max_win = max(
            max_win,
            current_win
        )

        max_loss = max(
            max_loss,
            current_loss
        )

    return max_win, max_loss

# ==================================
# KPI ENGINE
# ==================================
def calc_metrics(df):

    if df.empty:

        return {
            "total_profit":0,
            "total_trades":0,
            "wins":0,
            "losses":0,
            "win_rate":0,
            "avg_win":0,
            "avg_loss":0,
            "largest_win":0,
            "largest_loss":0,
            "profit_factor":0,
            "expectancy":0,
            "avg_r":0,
            "total_commission":0,
            "avg_commission":0,
            "max_dd":0,
            "recovery_factor":0,
            "max_win_streak":0,
            "max_loss_streak":0
        }

    wins_df = df[df["profit"] > 0]
    losses_df = df[df["profit"] < 0]

    wins = len(wins_df)
    losses = len(losses_df)

    total_profit = df["profit"].sum()

    total_trades = len(df)

    win_rate = (
        wins / total_trades * 100
    ) if total_trades else 0

    avg_win = (
        wins_df["profit"].mean()
    ) if wins else 0

    avg_loss = (
        losses_df["profit"].mean()
    ) if losses else 0

    largest_win = (
        wins_df["profit"].max()
    ) if wins else 0

    largest_loss = (
        losses_df["profit"].min()
    ) if losses else 0

    gross_profit = (
        wins_df["profit"].sum()
    )

    gross_loss = abs(
        losses_df["profit"].sum()
    )

    profit_factor = (
        gross_profit / gross_loss
        if gross_loss
        else 0
    )

    expectancy = (
        (win_rate / 100) * avg_win
        +
        ((100 - win_rate) / 100)
        * avg_loss
    )

    avg_r = (
        df["r_multiple"].mean()
        if "r_multiple" in df.columns
        else 0
    )

    total_commission = (
        df["commission"].sum()
        if "commission" in df.columns
        else 0
    )

    avg_commission = (
        df["commission"].mean()
        if "commission" in df.columns and len(df) > 0
        else 0
    )

    max_dd = (
        abs(df["drawdown"].min())
        if "drawdown" in df.columns
        else 0
    )

    recovery_factor = (
        total_profit / max_dd
        if max_dd > 0
        else 0
    )

    max_win_streak, max_loss_streak = (
        calculate_streaks(df)
    )

    return {

        "total_profit": total_profit,

        "total_trades": total_trades,

        "wins": wins,

        "losses": losses,

        "win_rate": win_rate,

        "avg_win": avg_win,

        "avg_loss": avg_loss,

        "largest_win": largest_win,

        "largest_loss": largest_loss,

        "profit_factor": profit_factor,

        "expectancy": expectancy,

        "avg_r": avg_r,

        "total_commission": total_commission,

        "avg_commission": avg_commission,

        "max_dd": max_dd,

        "recovery_factor": recovery_factor,

        "max_win_streak": max_win_streak,

        "max_loss_streak": max_loss_streak
    }

# ==================================
# AI REVIEW ENGINE
# ==================================
def generate_ai_review(
        profit,
        setup_score,
        mistakes,
        session,
        notes
):

    review = []

    if setup_score >= 6:
        review.append(
            "Excellent A+ setup quality."
        )

    elif setup_score >= 5:
        review.append(
            "Strong setup conditions."
        )

    elif setup_score >= 4:
        review.append(
            "Acceptable setup but not elite."
        )

    else:
        review.append(
            "Low-quality setup."
        )

    if profit > 0:

        review.append(
            "Execution produced profit."
        )

    else:

        review.append(
            "Review execution and management."
        )

    if mistakes:

        review.append(
            f"Mistakes detected: {mistakes}"
        )

    if session:

        review.append(
            f"Executed during {session} session."
        )

    if notes:

        review.append(
            "Review notes for recurring patterns."
        )

    review.append(
        "Focus on process over outcome."
    )

    return " ".join(review)

# ==================================
# SAVE SCREENSHOT
# ==================================
# ==================================
# LOAD TRADES
# ==================================
df = load_trades()
metrics = calc_metrics(df)

# ==================================
# DASHBOARD
# ==================================
with dashboard:

    st.subheader("📈 Sustainable Style Performance Dashboard")

    if "account_id_saved" not in st.session_state:
        st.session_state["account_id_saved"] = False

    saved_account = st.session_state.get("account_id", "")
    account_id = st.text_input(
        "Account ID",
        value=saved_account,
        key="dashboard_account_id",
        disabled=st.session_state.get("account_id_saved", False)
    )

    if not st.session_state.get("account_id_saved", False):
        if account_id:
            if st.button("Save Account", key="save_dashboard_account"):
                st.session_state["account_id"] = account_id.strip()
                st.session_state["account_id_saved"] = True
                if hasattr(st, "rerun"):
                    st.rerun()
                elif hasattr(st, "experimental_rerun"):
                    st.experimental_rerun()
                else:
                    st.success("Account ID saved. Refresh the page to continue.")
        else:
            st.info("Enter an Account ID to represent this dashboard.")
    else:
        st.markdown(f"**Current Account:** `{saved_account}`")
        st.caption("This Account ID has been saved and is now read-only.")

    # ==========================
    # KPI ROW 1
    # ==========================
    c1,c2,c3,c4,c5,c6 = st.columns(6)

    c1.metric(
        "💰 Net Profit",
        f"${metrics['total_profit']:,.2f}"
    )

    c2.metric(
        "🎯 Trades",
        metrics["total_trades"]
    )

    c3.metric(
        "🏆 Win Rate",
        f"{metrics['win_rate']:.1f}%"
    )

    c4.metric(
        "📈 Profit Factor",
        round(metrics["profit_factor"],2)
    )

    c5.metric(
        "⚡ Expectancy",
        f"${metrics['expectancy']:.2f}"
    )

    c6.metric(
        "📊 Average R",
        round(metrics["avg_r"],2)
    )

    st.divider()

    # ==========================
    # KPI ROW 2
    # ==========================
    c1,c2,c3,c4,c5,c6 = st.columns(6)

    c1.metric(
        "🥇 Largest Win",
        f"${metrics['largest_win']:,.2f}"
    )

    c2.metric(
        "🥉 Largest Loss",
        f"${metrics['largest_loss']:,.2f}"
    )

    c3.metric(
        "📈 Avg Winner",
        f"${metrics['avg_win']:,.2f}"
    )

    c4.metric(
        "📉 Avg Loser",
        f"${metrics['avg_loss']:,.2f}"
    )

    c5.metric(
        "🔻 Max DD",
        f"${metrics['max_dd']:,.2f}"
    )

    c6.metric(
        "🔄 Recovery Factor",
        round(metrics["recovery_factor"],2)
    )

    st.divider()

    # ==========================
    # KPI ROW 3
    # ==========================
    c1,c2,c3,c4,c5 = st.columns(5)

    c1.metric(
        "✅ Wins",
        metrics["wins"]
    )

    c2.metric(
        "❌ Losses",
        metrics["losses"]
    )

    c3.metric(
        "🔥 Max Win Streak",
        metrics["max_win_streak"]
    )

    c4.metric(
        "⚠️ Max Loss Streak",
        metrics["max_loss_streak"]
    )

    c5.metric(
        "💸 Total Commission",
        f"${metrics['total_commission']:,.2f}"
    )

    st.divider()

    if not df.empty:

        # ======================
        # EQUITY CURVE
        # ======================
        st.subheader("📈 Equity Curve")

        fig = px.line(
            df,
            x=df.index,
            y="equity",
            markers=True
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        # ======================
        # DRAWDOWN CURVE
        # ======================
        st.subheader("📉 Drawdown Curve")

        fig = px.area(
            df,
            x=df.index,
            y="drawdown"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        # ======================
        # MONTHLY PROFITS
        # ======================
        st.subheader("📅 Monthly Performance")

        monthly = df.copy()

        monthly["date"] = pd.to_datetime(
            monthly["date"]
        )

        monthly["month"] = (
            monthly["date"]
            .dt.to_period("M")
            .astype(str)
        )

        monthly_perf = (
            monthly
            .groupby("month")
            ["profit"]
            .sum()
            .reset_index()
        )

        fig = px.bar(
            monthly_perf,
            x="month",
            y="profit"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

# ==================================
# ANALYTICS
# ==================================
with analytics:

    st.subheader("📊 Advanced Analytics")

    if df.empty:

        st.info(
            "No trades available."
        )

    else:

        # ==========================
        # SYMBOL PERFORMANCE
        # ==========================
        st.subheader("🏆 Symbol Leaderboard")

        symbol_perf = (
            df.groupby("symbol")
            ["profit"]
            .sum()
            .sort_values(
                ascending=False
            )
        )

        st.bar_chart(symbol_perf)

        st.divider()

        # ==========================
        # SESSION ANALYTICS
        # ==========================
        st.subheader("🌍 Session Performance")

        if "session" in df.columns:

            session_perf = (
                df.groupby("session")
                ["profit"]
                .sum()
            )

            st.bar_chart(
                session_perf
            )

        st.divider()

        # ==========================
        # SETUP PERFORMANCE
        # ==========================
        st.subheader("🎯 Setup Performance")

        setup_perf = (
            df.groupby("setup")
            ["profit"]
            .sum()
            .sort_values(
                ascending=False
            )
        )

        st.bar_chart(
            setup_perf
        )

        st.divider()

        # ==========================
        # SETUP SCORE ANALYTICS
        # ==========================
        st.subheader(
            "⭐ Setup Quality Score"
        )

        if "setup_score" in df.columns:

            score_perf = (
                df.groupby(
                    "setup_score"
                )
                ["profit"]
                .sum()
            )

            st.bar_chart(
                score_perf
            )

        st.divider()

        # ==========================
        # DIRECTION ANALYSIS
        # ==========================
        st.subheader(
            "⬆️⬇️ Direction Analysis"
        )

        direction_perf = (
            df.groupby(
                "direction"
            )
            ["profit"]
            .sum()
        )

        st.bar_chart(
            direction_perf
        )

        st.divider()

        # ==========================
        # R-MULTIPLE ANALYSIS
        # ==========================
        st.subheader(
            "📏 R Multiple Distribution"
        )

        if "r_multiple" in df.columns:

            fig = px.histogram(
                df,
                x="r_multiple",
                nbins=30
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        st.divider()

        # ==========================
        # TRADE DURATION
        # ==========================
        st.subheader(
            "⏳ Duration vs Profit"
        )

        if "duration" in df.columns:

            fig = px.scatter(
                df,
                x="duration",
                y="profit",
                color="direction",
                hover_data=[
                    "symbol"
                ]
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        st.divider()

        # ==========================
        # MISTAKE ANALYSIS
        # ==========================
        st.subheader(
            "🚨 Mistake Analysis"
        )

        if (
            "mistake_type"
            in df.columns
        ):

            mistakes = (
                df["mistake_type"]
                .fillna("")
                .str.split(",")
                .explode()
            )

            mistakes = (
                mistakes[
                    mistakes != ""
                ]
                .value_counts()
            )

            if len(mistakes):

                st.bar_chart(
                    mistakes
                )

        st.divider()

        # ==========================
        # TAG ANALYSIS
        # ==========================
        st.subheader(
            "🏷️ Tag Performance"
        )

        if "tags" in df.columns:

            tag_data = (
                df["tags"]
                .fillna("")
                .str.split(",")
                .explode()
            )

            tag_data = (
                tag_data[
                    tag_data != ""
                ]
                .value_counts()
            )

            if len(tag_data):

                st.bar_chart(
                    tag_data
                )

        st.divider()

        # ==========================
        # CALENDAR HEATMAP DATA
        # ==========================
        st.subheader(
            "📅 Daily Profit Calendar"
        )

        cal = (
            df.groupby("date")
            ["profit"]
            .sum()
            .reset_index()
        )

        cal["date"] = (
            pd.to_datetime(
                cal["date"]
            )
        )

        fig = px.scatter(
            cal,
            x="date",
            y="profit",
            size=abs(
                cal["profit"]
            ),
            hover_data=[
                "profit"
            ]
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.divider()

        # ==========================
        # TOP/WORST TRADES
        # ==========================
        c1,c2 = st.columns(2)

        with c1:

            st.subheader(
                "🏆 Top 10 Trades"
            )

            st.dataframe(

                df.sort_values(
                    "profit",
                    ascending=False
                )
                .head(10),

                use_container_width=True
            )

        with c2:

            st.subheader(
                "💀 Worst 10 Trades"
            )

            st.dataframe(

                df.sort_values(
                    "profit",
                    ascending=True
                )
                .head(10),

                use_container_width=True
            )

# ==================================
# TRADE JOURNAL
# ==================================
with journal:

    st.subheader("📖 Advanced Trade Journal")
    st.info(
        "Enter your trade details clearly, review the setup quality score, and save a complete trade review with notes and screenshot proof."
    )
    
    # Download CSV section
    if not df.empty:
        csv_data = df.to_csv(index=False)
        col1, col2 = st.columns([1, 4])
        with col1:
            st.download_button(
                label="📥 Download CSV",
                data=csv_data,
                file_name="trades_export.csv",
                mime="text/csv"
            )
        with col2:
            st.caption("Export your trade history for offline review or import into Excel.")

    st.markdown("---")

    with st.form("trade_form"):

        # ==========================
        # BASIC TRADE INFO
        # ==========================
        st.markdown("### Trade Information")

        trade_date = st.date_input(
            "Trade Date",
            value=datetime.today().date(),
            key="trade_date"
        )

        symbol = st.selectbox(
            "Symbol",
            [
                "XAUUSD",
                "XAGUSD",
                "US100.cash",
                "NAS100",
                "US30.cash",
                "GER40",
                "EURUSD",
                "GBPUSD",
                "USDJPY"
            ],
            key="symbol"
        )

        direction = st.selectbox(
            "Direction",
            [
                "BUY",
                "SELL"
            ],
            key="direction"
        )

        col1,col2 = st.columns(2)

        with col1:

            entry = st.number_input(
                "Entry Price",
                value=0.0,
                key="entry"
            )

            lot = st.number_input(
                "Lot Size",
                value=0.10,
                key="lot"
            )

        with col2:

            exit_price = st.number_input(
                "Exit Price",
                value=0.0,
                key="exit_price"
            )

            profit = st.number_input(
                "Profit ($)",
                value=0.0,
                key="profit"
            )
            
            commission = st.number_input(
                "Commission ($)",
                value=0.0,
                key="commission"
            )
            
            net_profit = profit - commission

        # ==========================
        # RISK MANAGEMENT
        # ==========================
        st.markdown("### Risk Management")

        col1,col2,col3 = st.columns(3)

        with col1:

            risk = st.number_input(
                "Risk Amount ($)",
                value=100.0,
                key="risk"
            )

        with col2:

            stop_loss = st.number_input(
                "Stop Loss",
                key="stop_loss"
            )

        with col3:

            take_profit = st.number_input(
                "Take Profit",
                key="take_profit"
            )

        r_multiple = (
            net_profit / risk
            if risk > 0
            else 0
        )

        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "Net Profit/Loss",
                f"${net_profit:.2f}"
            )
        with col2:
            st.metric(
                "Calculated R Multiple",
                round(r_multiple, 2)
            )

        st.markdown("---")

        # ==========================
        # SESSION TRACKING
        # ==========================
        st.markdown("### Session")

        session = st.selectbox(
            "Trading Session",
            [
                "Asian",
                "London",
                "London Open",
                "New York",
                "New York Open"
            ],
            key="trade_session"
        )

        timeframe = st.selectbox(
            "Trading Timeframe",
            [
                "1 min",
                "5 min",
                "15 min",
                "30 min",
                "1H",
                "4H",
                "1D"
            ],
            index=4,
            key="timeframe"
        )

        # ==========================
        # ENTRY & EXIT TIMES
        # ==========================
        st.markdown("### Timing")

        col1, col2, col3 = st.columns(3)

        with col1:

            entry_time = st.time_input(
                "Entry Time",
                value=datetime.now().time().replace(second=0, microsecond=0),
                step=timedelta(minutes=1),
                key="entry_time"
            )

        with col2:

            exit_time = st.time_input(
                "Exit Time",
                value=datetime.now().time().replace(second=0, microsecond=0),
                step=timedelta(minutes=1),
                key="exit_time"
            )

        auto_duration = (

            datetime.combine(
                datetime.today(),
                exit_time
            )

            -

            datetime.combine(
                datetime.today(),
                entry_time
            )

        ).seconds / 60

        with col3:

            duration = st.number_input(
                "Duration (minutes)",
                value=float(auto_duration),
                min_value=0.0,
                step=1.0,
                key="duration"
            )

        st.info(
            f"Trade Duration: {duration:.0f} minutes"
        )

        st.markdown("---")

        # ==========================
        # MAIN SETUP
        # ==========================
        st.markdown("### Primary Setup")

        setup = st.selectbox(
            "Setup",
            [
                "Order Block",
                "Breaker Block",
                "FVG",
                "iFVG",
                "CHoCH",
                "BOS",
                "SMT",
                "Liquidity Sweep",
                "CISD",
                "CRT"
            ],
            key="setup"
        )

        # ==========================
        # ICT SCORECARD
        # ==========================
        st.markdown(
            "### ICT Setup Quality Score"
        )

        c1,c2,c3 = st.columns(3)

        with c1:

            liquidity_sweep = st.checkbox(
                "Liquidity Sweep"
            )

            htf_bias = st.checkbox(
                "HTF Bias"
            )

            equal_high = st.checkbox(
                "Equal High",
                key="equal_high"
            )

        with c2:

            fvg_present = st.checkbox(
                "FVG Present",
                key="fvg_present"
            )

            cisd_present = st.checkbox(
                "CISD Confirmed",
                key="cisd_present"
            )

            ifvg_present = st.checkbox(
                "iFVG Present",
                key="ifvg_present"
            )

        with c3:

            session_valid = st.checkbox(
                "Correct Session",
                key="session_valid"
            )

            displacement = st.checkbox(
                "Displacement",
                key="displacement"
            )

            equal_low = st.checkbox(
                "Equal Low",
                key="equal_low"
            )

            v_shape = st.checkbox(
                "V-Shape (Momentum)",
                key="v_shape"
            )

            delivery_from_fvg = st.checkbox(
                "Delivery from FVG",
                key="delivery_from_fvg"
            )

        setup_score = min(sum([
            liquidity_sweep,
            htf_bias,
            equal_high,
            fvg_present,
            cisd_present,
            ifvg_present,
            session_valid,
            displacement,
            equal_low,
            v_shape,
            delivery_from_fvg
        ]), 6)

        if setup_score == 6:
            grade = "A+"

        elif setup_score == 5:
            grade = "A"

        elif setup_score == 4:
            grade = "B"

        elif setup_score == 3:
            grade = "C"

        else:
            grade = "D"

        st.metric(
            "Setup Grade",
            f"{grade}",
            f"{setup_score}/6"
        )
        st.caption("Grading is capped at a maximum of 6 quality points.")

        st.markdown("---")

        screenshot_path = ""
        notes = ""

        with st.expander("🧠 Optional review + tags", expanded=False):
            st.markdown("### Trade Tags")
            tags = st.multiselect(
                "Tags",
                [
                    "Liquidity Sweep",
                    "FVG",
                    "iFVG",
                    "Order Block",
                    "Breaker",
                    "SMT",
                    "CISD",
                    "CRT",
                    "20 EMA",
                    "News",
                    "London Open",
                    "New York Open",
                    "Continuation",
                    "Reversal",
                    "Scalp",
                    "Intraday",
                    "Swing"
                ],
                key="tags"
            )

            st.markdown("### Mistake Tracking")
            mistakes = st.multiselect(
                "Mistakes Made",
                [
                    "FOMO",
                    "Overtrading",
                    "Moved Stop Loss",
                    "Moved Take Profit",
                    "Revenge Trading",
                    "Ignored HTF Bias",
                    "Early Exit",
                    "Late Entry",
                    "No Confirmation",
                    "Risked Too Much"
                ],
                key="mistakes"
            )

            st.markdown("### Screenshot Upload")
            uploaded_screenshot = st.file_uploader(
                "Upload a PNG, JPG, or JPEG screenshot of the trade.",
                type=["png", "jpg", "jpeg"],
                key="uploaded_screenshot"
            )

            if uploaded_screenshot is not None:
                screenshot_filename = (
                    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_"
                    f"{secrets.token_hex(4)}_{uploaded_screenshot.name}"
                )
                screenshot_path = os.path.join("screenshots", screenshot_filename)
                try:
                    with open(screenshot_path, "wb") as file:
                        file.write(uploaded_screenshot.getbuffer())
                    st.image(screenshot_path, caption="Uploaded screenshot", use_column_width=True)
                except Exception as exc:
                    st.error(f"Unable to save screenshot: {exc}")
                    screenshot_path = ""

            st.markdown("### Trade Notes")
            notes = st.text_area(
                "Journal Notes",
                key="journal_notes"
            )

        st.markdown("---")

        # ==========================
        # AI REVIEW
        # ==========================
        ai_review = generate_ai_review(
            net_profit,
            setup_score,
            ",".join(mistakes),
            session,
            notes
        )

        st.info(ai_review)

        # ==========================
        # SAVE
        # ==========================
        with st.expander("📄 Terms and Conditions", expanded=False):
            st.markdown(TERMS_AND_CONDITIONS)

        tc_agreed = st.checkbox(
            "I have read and agree to the Terms and Conditions",
            value=False,
            key="accept_terms"
        )

        submitted = st.form_submit_button(
            "💾 Save Trade"
        )

        if submitted:
            if not tc_agreed:
                st.warning(
                    "You must agree to the Terms and Conditions before saving a trade."
                )
            else:
                cursor.execute(
                """
                INSERT INTO trades(
                    date,
                    symbol,
                    direction,
                    entry,
                    exit,
                    lot,
                    profit,
                    commission,
                    setup,
                    notes,
                    risk,
                    r_multiple,
                    session,
                    timeframe,
                    setup_score,
                    tags,
                    mistake_type,
                    entry_time,
                    exit_time,
                    duration,
                    screenshot,
                    subscription_key,
                    ai_review
                )

                VALUES(
                    ?,?,?,?,?,?,
                    ?,?,?,?,?,?,
                    ?,?,?,?,?,?,
                    ?,?,?,?,?
                )
                """,
                (
                    str(trade_date),
                    symbol,
                    direction,
                    entry,
                    exit_price,
                    lot,
                    net_profit,
                    commission,
                    setup,
                    notes,
                    risk,
                    r_multiple,
                    session,
                    timeframe,
                    setup_score,
                    ",".join(tags),
                    ",".join(mistakes),
                    str(entry_time),
                    str(exit_time),
                    duration,
                    screenshot_path,
                    get_current_subscription_key(),
                    ai_review
                )
            )

            conn.commit()

            st.success(
                "Trade Saved Successfully ✅"
            )
            
            # Rerun to reset the form
            st.rerun()
            
            # Add CSV download option
            if not df.empty:
                csv_data = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Trades as CSV",
                    data=csv_data,
                    file_name="trades_export.csv",
                    mime="text/csv"
                )
            
            st.rerun()

            send_telegram(
                f"""
New Trade Logged

{symbol}
{direction}

Net Profit: ${net_profit:.2f}
R Multiple: {r_multiple:.2f}

Setup Grade: {grade}
Session: {session}
                """
            )

    st.divider()

    # ==================================
    # BULK IMPORT FROM CSV / XLSX
    # ==================================
    # Bulk import feature removed - users must manually key in data

    st.divider()

    if not df.empty:

        trade_id = st.selectbox(
            "Select Trade",
            df["id"]
        )

        trade = df[
            df["id"] == trade_id
        ].iloc[0]

        c1,c2 = st.columns([1,2])

        with c1:

            st.write(
                f"Symbol: {trade['symbol']}"
            )

            st.write(
                f"Profit: ${trade['profit']}"
            )

            st.write(
                f"R Multiple: {trade['r_multiple']}"
            )

            st.write(
                f"Session: {trade['session']}"
            )

            st.write(
                f"Timeframe: {trade.get('timeframe', 'N/A')}"
            )

            st.write(
                f"Score: {trade['setup_score']}/6"
            )

        with c2:

            if trade["screenshot"]:

                if os.path.exists(
                    trade["screenshot"]
                ):

                    st.image(
                        trade["screenshot"],
                        use_container_width=True
                    )

        st.info(
            trade["ai_review"]
        )

        st.divider()

        st.subheader("📚 Trade History")

        if not df.empty:

            history_cols = [

                "date",
                "symbol",
                "direction",
                "profit",
                "r_multiple",
                "session",
                "timeframe",
                "setup_score",
                "entry_time",
                "exit_time",
                "duration"

            ]

            st.dataframe(
                df[history_cols],
                use_container_width=True
            )
    
# ==================================
# COMPOUNDING TAB
# ==================================
with compounding:
    st.markdown("## 💰 Compounding Growth Simulator")
    st.markdown("Simulate your account growth with period-by-period breakdown, just like Sustainable's compounding tools.")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        initial_balance = st.number_input("Initial Balance ($)", value=1000.0, min_value=0.0, step=100.0)
    with col2:
        percent_return = st.number_input("% Return per Period", value=2.0, min_value=-100.0, max_value=100.0, step=0.1)
    with col3:
        periods = st.number_input("Number of Periods", value=12, min_value=1, step=1)
    with col4:
        add_contrib = st.number_input("Add per Period ($)", value=0.0, min_value=0.0, step=10.0)

    data = []
    balance = initial_balance
    for i in range(1, int(periods)+1):
        growth = balance * (percent_return / 100)
        balance += growth + add_contrib
        data.append({"Period": i, "Growth": growth, "Contribution": add_contrib, "Balance": balance})

    df_comp = pd.DataFrame(data)
    st.line_chart(df_comp["Balance"], use_container_width=True)
    st.dataframe(df_comp, use_container_width=True, hide_index=True)
    st.success(f"**Final Balance after {int(periods)} periods: ${balance:,.2f}**")

# ==================================
# GOALS TAB
# ==================================
with goals:
    st.markdown("## 🎯 My Trading Goals")
    st.markdown("Set, track, and visualize your trading goals in a Sustainable-inspired format.")
    if 'goals_list' not in st.session_state:
        st.session_state['goals_list'] = []
    with st.form("goal_form"):
        col1, col2, col3 = st.columns([5,2,2])
        with col1:
            new_goal = st.text_input("Goal Description")
        with col2:
            target_date = st.date_input("Target Date", value=datetime.now().date())
        with col3:
            progress = st.slider("Progress %", min_value=0, max_value=100, value=0)
        submitted = st.form_submit_button("Add Goal")
        if submitted and new_goal:
            st.session_state['goals_list'].append({"goal": new_goal, "date": str(target_date), "progress": progress})
    for idx, goal in enumerate(st.session_state['goals_list']):
        st.markdown(f"**{goal['goal']}**  ")
        st.progress(goal['progress'])
        st.caption(f"Target: {goal['date']}")
        col1, col2 = st.columns([1,1])
        with col1:
            new_progress = st.slider(f"Update Progress for Goal {idx+1}", min_value=0, max_value=100, value=goal['progress'], key=f'progress_{idx}')
            if new_progress != goal['progress']:
                st.session_state['goals_list'][idx]['progress'] = new_progress
        with col2:
            if st.button("❌ Remove", key=f"del_goal_{idx}"):
                st.session_state['goals_list'].pop(idx)
                st.rerun()

# ==================================
# PSYCHOLOGY TAB
# ==================================
with psychology:
    st.markdown("## 🧠 Trading Psychology & Mindset")
    st.markdown("Log your mindset, track your mood, and get actionable psychology prompts.")
    moods = ["😃 Great", "🙂 Good", "😐 Neutral", "😟 Stressed", "😢 Down"]
    # Load persisted psychology notes for this subscription
    if 'psych_journal' not in st.session_state:
        try:
            cursor.execute(
                "SELECT date, mood, note FROM psych_journal WHERE subscription_key=? ORDER BY id DESC",
                (get_current_subscription_key(),)
            )
            rows = cursor.fetchall()
            st.session_state['psych_journal'] = [
                {"date": r[0], "mood": r[1], "note": r[2]} for r in rows
            ]
        except Exception:
            st.session_state['psych_journal'] = []

    st.markdown("### Today's Mood")
    mood = st.radio("How do you feel about your trading today?", moods, horizontal=True)
    st.markdown("---")
    st.markdown("### Quick Reflection Prompts")
    prompts = [
        "What did I do well today?",
        "What challenged me emotionally?",
        "How did I handle losses or wins?",
        "What will I improve next session?"
    ]
    for prompt in prompts:
        st.text_input(prompt, key=f"prompt_{prompt}")
    if st.button("Save Quick Reflections"):
        responses = []
        for prompt in prompts:
            resp = st.session_state.get(f"prompt_{prompt}", "").strip()
            if resp:
                responses.append(f"{prompt}: {resp}")
        if responses:
            note = "\n".join(responses)
            date_str = str(datetime.now())
            try:
                cursor.execute(
                    "INSERT INTO psych_journal(date, mood, note, subscription_key) VALUES (?,?,?,?)",
                    (date_str, mood, note, get_current_subscription_key()),
                )
                conn.commit()
            except Exception as e:
                st.error(f"Failed to save quick reflections: {e}")
            else:
                st.session_state.setdefault('psych_journal', [])
                st.session_state['psych_journal'].insert(0, {"date": date_str, "mood": mood, "note": note})
                st.success("Quick reflections saved")
                st.rerun()
        else:
            st.warning("No responses entered to save.")
    st.markdown("---")
    st.markdown("### Psychology Journal")
    with st.form("psych_form"):
        psych_note = st.text_area("Write a detailed psychology note or reflection")
        submitted = st.form_submit_button("Add Note")
        if submitted and psych_note:
            date_str = str(datetime.now())
            try:
                cursor.execute(
                    "INSERT INTO psych_journal(date, mood, note, subscription_key) VALUES (?,?,?,?)",
                    (date_str, mood, psych_note, get_current_subscription_key()),
                )
                conn.commit()
            except Exception as e:
                st.error(f"Failed to save note: {e}")
            else:
                # update session cache and rerun to refresh UI
                st.session_state['psych_journal'].insert(0, {"date": date_str, "mood": mood, "note": psych_note})
                st.success("Psychology note saved")
                st.rerun()

    # Display persisted notes
    for entry in st.session_state.get('psych_journal', []):
        st.write(f"{entry['date']} {entry['mood']}: {entry['note']}")

    # CSV export for psychology notes
    if st.session_state.get('psych_journal'):
        try:
            df_psych = pd.DataFrame(st.session_state['psych_journal'])
            csv_data = df_psych.to_csv(index=False)
            st.download_button(label="📥 Download Psychology Notes as CSV", data=csv_data, file_name="psych_notes.csv")
        except Exception:
            pass

# ==================================
# ADMIN TAB
# ==================================
with admin:
    st.markdown("## 🔧 Admin - Subscription Keys")

    admin_key_env = os.getenv("ADMIN_KEY", "")
    try:
        admin_key_secret = st.secrets.get("admin_key", "")
    except Exception:
        admin_key_secret = ""

    admin_input = st.text_input("Admin Key (enter to manage keys)", type="password", key="admin_input")

    if st.button("Login as Admin"):
        if admin_input and (admin_input == admin_key_env or admin_input == admin_key_secret):
            st.session_state["is_admin"] = True
            st.session_state["admin_user"] = admin_input
            st.rerun()
        else:
            st.error("Invalid admin key.")

    # Email-based admin 2FA
    st.markdown("---")
    st.markdown("### Admin Email 2FA")
    send_code = st.button("Send admin login code to configured admin email")
    templates = load_email_templates()
    if send_code:
        admin_notify = os.getenv("ADMIN_NOTIFICATION_EMAIL", "")
        if not admin_notify:
            st.error("No ADMIN_NOTIFICATION_EMAIL configured in env.")
        elif not can_send_admin_otp():
            st.error("Too many OTP requests. Please wait 15 minutes before requesting a new code.")
        else:
            code = str(int.from_bytes(os.urandom(3), "big") % 1000000).zfill(6)
            st.session_state["admin_otp"] = code
            st.session_state["admin_otp_time"] = datetime.now().isoformat()
            record_admin_otp_request()
            tpl = templates.get("otp", {})
            subject = tpl.get("subject", "Your admin login code")
            body = tpl.get("body", "Your admin login code is: {code}").format(code=code)
            ok = send_admin_email(subject, body)
            if ok:
                st.success(f"OTP sent to {admin_notify}")
            else:
                err = get_last_email_error()
                if err:
                    st.error(f"Failed to send OTP email. {err}")
                else:
                    st.error("Failed to send OTP email. Check SMTP settings.")

    otp_input = st.text_input("Enter admin code", key="otp_input")
    if st.button("Verify code"):
        otp = st.session_state.get("admin_otp")
        otp_time = st.session_state.get("admin_otp_time")
        if not otp:
            st.error("No code sent. Click 'Send admin login code' first.")
        elif not can_attempt_admin_otp_verify():
            st.error("Too many invalid OTP attempts. Please wait 10 minutes and try again.")
        else:
            try:
                sent_time = datetime.fromisoformat(otp_time)
            except Exception:
                sent_time = None

            if otp_input == otp and sent_time and datetime.now() - sent_time <= timedelta(minutes=10):
                st.session_state["is_admin"] = True
                st.session_state["admin_user"] = st.session_state.get("admin_user", "email_admin")
                st.success("Admin verified via email OTP")
                st.rerun()
            else:
                record_admin_otp_verify_attempt()
                st.error("Invalid or expired code.")

    if not st.session_state.get("is_admin", False):
        st.warning("Admin access required to manage subscription keys.")
    else:
        st.success("Admin mode enabled")

        st.markdown("### Email notification status")
        last_email_error = get_last_email_error()
        if last_email_error:
            st.warning(f"Last email error: {last_email_error}")
        else:
            st.info("No recent email errors logged. Email notifications are either working or not yet exercised.")

        db_keys = get_all_db_subscription_keys()
        fallback_keys = get_subscription_keys_map() if not db_keys else {}

        st.markdown("### Current subscription key metadata")
        if db_keys:
            try:
                st.dataframe(pd.DataFrame(db_keys).fillna(""), use_container_width=True)
            except Exception:
                st.write(db_keys)
        else:
            st.info("No database subscription keys found. Falling back to file-based keys.")
            try:
                df_keys = pd.DataFrame.from_dict(fallback_keys, orient="index")
                st.dataframe(df_keys.fillna(""), use_container_width=True)
            except Exception:
                st.write(fallback_keys)

        st.markdown("### Backup / Export")
        if st.button("Export DB subscription backup"):
            if export_subscription_keys_backup():
                st.success("Subscription key backup exported to backup_subscription_keys.json/csv")
            else:
                st.error("Failed to export subscription keys backup.")

        st.markdown("### Admin Audit Log")
        if os.path.exists("subscription_admin_audit.log"):
            try:
                with open("subscription_admin_audit.log", "r", encoding="utf-8") as f:
                    lines = [json.loads(l) for l in f.read().splitlines() if l.strip()]
                    lines = list(reversed(lines))
                    max_show = st.number_input("Entries to show", min_value=1, max_value=500, value=50)
                    show = lines[:int(max_show)]
                    st.dataframe(pd.DataFrame(show), use_container_width=True)
                    if st.button("Download audit log"):
                        with open("subscription_admin_audit.log", "rb") as fh:
                            st.download_button("Download log", fh, file_name="subscription_admin_audit.log")
            except Exception:
                st.error("Unable to read audit log.")
        else:
            st.info("No audit log found yet.")

        st.markdown("### Pending registration requests")
        registration_requests = load_registration_requests()
        if registration_requests:
            try:
                st.dataframe(
                    pd.DataFrame(list(reversed(registration_requests))).fillna(""),
                    use_container_width=True
                )
            except Exception:
                st.write(list(reversed(registration_requests)))
        else:
            st.info("No registration requests have been submitted yet.")

        st.markdown("### Email Templates")
        templates = load_email_templates()
        tpl_name = st.selectbox("Template", list(templates.keys()))
        tpl = templates.get(tpl_name, {})
        subj = st.text_input("Subject", value=tpl.get("subject", ""), key=f"tpl_subj_{tpl_name}")
        body = st.text_area("Body", value=tpl.get("body", ""), key=f"tpl_body_{tpl_name}")
        if st.button("Save template"):
            templates[tpl_name] = {"subject": subj, "body": body}
            if save_email_templates(templates):
                st.success("Template saved")
            else:
                st.error("Failed to save template")

        st.markdown("### Add / Update Key")
        with st.form("admin_add_form"):
            new_key = st.text_input("Key")
            new_user = st.text_input("User")
            new_email = st.text_input("Email")
            new_plan = st.text_input("Plan")
            new_expires = st.text_input("Expires (YYYY-MM-DD)")
            new_active = st.checkbox("Active", value=True)
            submitted = st.form_submit_button("Save Key")

            if submitted and new_key:
                ok = set_db_subscription_key(new_key, new_user, new_email, new_plan, new_expires, new_active)
                if ok:
                    st.success("Key saved to database")
                    admin_user = st.session_state.get("admin_user", "admin")
                    log_admin_action("add", new_key, {
                        "user": new_user,
                        "email": new_email,
                        "plan": new_plan,
                        "expires": new_expires,
                        "active": new_active
                    }, admin_user)
                    tpl = load_email_templates().get("add", {})
                    subject = tpl.get("subject", "Subscription key added: {key}").format(key=new_key)
                    body = tpl.get("body", "Admin {admin} added key {key}").format(
                        admin=admin_user,
                        key=new_key,
                        user=new_user,
                        email=new_email,
                        plan=new_plan,
                        expires=new_expires
                    )
                    send_admin_email(subject, body)
                    st.rerun()
                else:
                    st.error("Failed to save key to database.")

        st.markdown("### Edit / Remove Key")
        if db_keys:
            options = [f"{entry['key_label']} | {entry['user']} | {entry['email']} | {entry['plan']}" for entry in db_keys]
            option_map = {options[i]: entry['key_hash'] for i, entry in enumerate(db_keys)}
            sel_label = st.selectbox("Select key to edit", options)
            sel_hash = option_map.get(sel_label)
            selected_meta = next((entry for entry in db_keys if entry['key_hash'] == sel_hash), None)

            if selected_meta:
                col1, col2 = st.columns(2)
                with col1:
                    e_user = st.text_input("User", value=selected_meta.get("user", ""), key="e_user")
                    e_email = st.text_input("Email", value=selected_meta.get("email", ""), key="e_email")
                    e_plan = st.text_input("Plan", value=selected_meta.get("plan", ""), key="e_plan")
                with col2:
                    e_expires = st.text_input("Expires (YYYY-MM-DD)", value=selected_meta.get("expires", ""), key="e_expires")
                    e_active = st.checkbox("Active", value=selected_meta.get("active", True), key="e_active")

                if st.button("Update Key"):
                    ok = update_db_subscription_key(sel_hash, e_user, e_email, e_plan, e_expires, e_active)
                    if ok:
                        st.success("Key updated")
                        admin_user = st.session_state.get("admin_user", "admin")
                        log_admin_action("update", sel_hash, {
                            "user": e_user,
                            "email": e_email,
                            "plan": e_plan,
                            "expires": e_expires,
                            "active": e_active
                        }, admin_user)
                        tpl = load_email_templates().get("update", {})
                        subject = tpl.get("subject", "Subscription key updated: {key}").format(key=selected_meta.get("key_label", sel_hash[:8]))
                        body = tpl.get("body", "Admin {admin} updated key {key}").format(
                            admin=admin_user,
                            key=selected_meta.get("key_label", sel_hash[:8]),
                            user=e_user,
                            email=e_email,
                            plan=e_plan,
                            expires=e_expires,
                            active=e_active
                        )
                        send_admin_email(subject, body)
                        st.rerun()
                    else:
                        st.error("Failed to update key.")

                if st.button("Remove Key"):
                    ok = delete_db_subscription_key(sel_hash)
                    if ok:
                        st.success("Key removed from database")
                        admin_user = st.session_state.get("admin_user", "admin")
                        log_admin_action("remove", sel_hash, selected_meta, admin_user)
                        tpl = load_email_templates().get("remove", {})
                        subject = tpl.get("subject", "Subscription key removed: {key}").format(key=selected_meta.get("key_label", sel_hash[:8]))
                        body = tpl.get("body", "Admin {admin} removed key {key}").format(admin=admin_user, key=selected_meta.get("key_label", sel_hash[:8]))
                        send_admin_email(subject, body)
                        st.rerun()
                    else:
                        st.error("Failed to remove key.")
        else:
            st.info("No database-subscription keys to edit. Add a key above.")

