import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
import csv
import io
import os
import glob
import json
import re
import smtplib
import hashlib
import hmac
import secrets
from email.message import EmailMessage
import numpy as np
from reportlab.platypus import SimpleDocTemplate, Paragraph

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def format_currency(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"${value:,.2f}"


def color_for_value(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "black"
    if value > 0:
        return "teal"
    if value < 0:
        return "red"
    return "black"


def safe_float(value, default=np.nan):
    try:
        if value is None:
            return default
        if isinstance(value, str) and not value.strip():
            return default
        return float(value)
    except Exception:
        return default


def get_first_nonempty(row, *keys):
    for key in keys:
        if key in row.index:
            value = row.get(key)
            if value is not None and not (isinstance(value, str) and not value.strip()):
                return value
    return None


def render_currency_metric(col, label, value):
    col.markdown(
        f"**{label}**  \n<span style='font-size:1.5rem; color:{color_for_value(value)};'>{format_currency(value)}</span>",
        unsafe_allow_html=True
    )


def style_profit_column(df):
    if "profit" not in df.columns:
        return df

    def profit_color(val):
        try:
            v = float(val)
        except (TypeError, ValueError):
            return ""
        if v > 0:
            return "color: teal"
        if v < 0:
            return "color: red"
        return "color: black"

    return df.style.map(profit_color, subset=["profit"])


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
            if entry:
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
            if entry:
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
            account_id TEXT DEFAULT '',
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
        "SELECT key_hash, key_label, user, email, plan, expires, active, account_id FROM subscription_keys WHERE key_hash = ?",
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
        "account_id": row[7],
        "source": "db"
    }


def get_saved_account_id_for_key(key):
    if not key:
        return ""
    meta = get_db_subscription_metadata(key)
    return meta.get("account_id", "") if meta else ""


def save_subscription_account_id(key, account_id):
    if not key:
        return False
    key_hash = hash_subscription_key(key)
    now = datetime.now().isoformat()
    try:
        cursor.execute(
            "UPDATE subscription_keys SET account_id = ?, updated_at = ? WHERE key_hash = ?",
            (account_id, now, key_hash)
        )
        if cursor.rowcount == 0:
            cursor.execute(
                "INSERT OR REPLACE INTO subscription_keys(key_hash, key_label, user, email, plan, expires, active, account_id, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    key_hash,
                    key_hash[:8],
                    "",
                    "",
                    "",
                    "",
                    1,
                    account_id,
                    now,
                    now
                )
            )
        conn.commit()
        return True
    except Exception:
        return False


def restore_saved_account_from_key():
    current_key = get_current_subscription_key()
    if not current_key:
        return

    if st.session_state.get("account_id") or st.session_state.get("account_id_saved", False):
        return

    account_id = get_saved_account_id_for_key(current_key)
    if account_id:
        st.session_state["account_id"] = account_id
        st.session_state["account_id_saved"] = True


def get_all_db_subscription_keys():

    cursor.execute(
        "SELECT id, key_hash, key_label, user, email, plan, expires, active, account_id, created_at, updated_at FROM subscription_keys ORDER BY id DESC"
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
            "account_id": row[8],
            "created_at": row[9],
            "updated_at": row[10]
        })

    return keys


def set_db_subscription_key(key, user, email, plan, expires, active=True, account_id=""):

    key_hash = hash_subscription_key(key)
    key_label = key_hash[:8]
    now = datetime.now().isoformat()

    try:
        cursor.execute(
            "INSERT OR REPLACE INTO subscription_keys(key_hash, key_label, user, email, plan, expires, active, account_id, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                key_hash,
                key_label,
                user,
                email,
                plan,
                expires,
                1 if active else 0,
                account_id,
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
    return


def show_subscription_gate():
    return


# ==================================
# DATABASE
# ==================================
conn = sqlite3.connect(
    "forex_tracker.db",
    check_same_thread=False
)

cursor = conn.cursor()

create_subscription_keys_table()
try:
    cursor.execute(
        "ALTER TABLE subscription_keys ADD COLUMN account_id TEXT DEFAULT ''"
    )
    conn.commit()
except Exception:
    pass

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

mistake_type TEXT,

entry_time TEXT,

exit_time TEXT,

duration REAL DEFAULT 0,

screenshot TEXT,

subscription_key TEXT
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
def add_column_if_missing(table_name, column_name, definition):

    try:
        cursor.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"
        )
        conn.commit()
    except:
        pass

add_column_if_missing("trades", "commission", "REAL DEFAULT 0")
add_column_if_missing("trades", "risk", "REAL DEFAULT 0")
add_column_if_missing("trades", "r_multiple", "REAL DEFAULT 0")
add_column_if_missing("trades", "session", "TEXT")
add_column_if_missing("trades", "timeframe", "TEXT")
add_column_if_missing("trades", "setup_score", "INTEGER DEFAULT 0")
add_column_if_missing("trades", "mistake_type", "TEXT")
add_column_if_missing("trades", "entry_time", "TEXT")
add_column_if_missing("trades", "exit_time", "TEXT")
add_column_if_missing("trades", "duration", "REAL DEFAULT 0")
add_column_if_missing("trades", "screenshot", "TEXT")
add_column_if_missing("trades", "subscription_key", "TEXT")
add_column_if_missing("subscription_keys", "account_id", "TEXT DEFAULT ''")

# ==================================
# LOAD DATA
# ==================================
def load_trades():

    current_key = get_current_subscription_key()
    if current_key:
        df = pd.read_sql(
            "SELECT * FROM trades WHERE subscription_key = ? ORDER BY date ASC",
            conn,
            params=(current_key,)
        )
    else:
        df = pd.read_sql(
            "SELECT * FROM trades ORDER BY date ASC",
            conn
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

        df["equity"] = 10000 + df["profit"].cumsum()

        df["running_max"] = (
            df["equity"]
            .cummax()
        )

        df["drawdown"] = (
            df["equity"]
            - df["running_max"]
        )

    return df


def count_trades_for_key(key):
    try:
        if not key:
            return cursor.execute("SELECT COUNT(*) FROM trades").fetchone()[0] or 0
        return cursor.execute(
            "SELECT COUNT(*) FROM trades WHERE subscription_key = ?",
            (key,)
        ).fetchone()[0] or 0
    except Exception:
        return 0


def find_report_history_files():
    return sorted(glob.glob(os.path.join(BASE_DIR, "ReportHistory-*.xlsx")))


def parse_legacy_report_time(value):
    if pd.isna(value) or value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    # Normalize trailing milliseconds and timezone-like suffix
    text = re.sub(r"\.(\d{1,6})(?:Z|[+-]\d{2}:?\d{2})?$", "", text)

    for fmt in (
        "%Y.%m.%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d.%m.%Y %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d.%m.%Y %H:%M",
        "%Y-%m-%d %H:%M",
    ):
        try:
            return datetime.strptime(text, fmt)
        except Exception:
            pass

    return None


def restore_trades_from_report_history(file_path, subscription_key):
    if not file_path or not os.path.exists(file_path):
        return 0

    try:
        xls = pd.ExcelFile(file_path)
    except Exception:
        return 0

    imported = 0
    for sheet_name in xls.sheet_names:
        df_raw = xls.parse(sheet_name, header=None)

        header_row: int | None = None
        for idx in range(len(df_raw)):
            row = df_raw.iloc[idx]
            values = [
                str(v).strip().lower() if not pd.isna(v) else ""
                for v in row.tolist()
            ]
            if "symbol" in values and ("closing time" in values or "time" in values or "opening" in values) and "net $" in values:
                header_row = idx
                break

        if header_row is None:
            continue

        raw_header = df_raw.iloc[header_row].tolist()
        header = []
        counts = {}
        for raw_col in raw_header:
            name = str(raw_col).strip() if not pd.isna(raw_col) else ""
            key = name.lower().replace(" ", "_")
            if key in counts:
                counts[key] += 1
                key = f"{key}.{counts[key]}"
            else:
                counts[key] = 0
            header.append(key)

        data_df = df_raw.iloc[int(header_row) + 1 :].copy()
        data_df.columns = header
        data_df = data_df.dropna(how="all")

        for _, row in data_df.iterrows():
            symbol = str(get_first_nonempty(row, "symbol", "symbol_", "symbol.1") or "").strip()
            if not symbol:
                continue

            direction = str(get_first_nonempty(row, "type", "opening_di", "opening_direction", "closing_type", "direction") or "").strip().lower()
            if direction in ("b", "s"):
                direction = "buy" if direction == "b" else "sell"
            if direction not in ("buy", "sell"):
                continue

            profit = safe_float(get_first_nonempty(row, "profit", "net_$", "net", "balance_$"))
            entry_price = safe_float(get_first_nonempty(row, "price", "entry_price", "entry price", "opening_price", "opening_price"))
            exit_price = safe_float(get_first_nonempty(row, "price.1", "closing_price", "closing price", "exit_price", "exit price"))

            if pd.isna(profit) and pd.isna(exit_price):
                continue

            open_time = parse_legacy_report_time(get_first_nonempty(row, "time", "opening_time", "opening time", "closing_time", "closing time"))
            close_time = parse_legacy_report_time(get_first_nonempty(row, "time.1", "closing_time", "closing time", "close time"))
            if close_time is None:
                close_time = parse_legacy_report_time(get_first_nonempty(row, "close time", "closing_time", "closing time"))

            date_value = ""
            if open_time:
                date_value = open_time.date().isoformat()
            elif close_time:
                date_value = close_time.date().isoformat()

            duration = 0.0
            if open_time and close_time:
                duration = (close_time - open_time).total_seconds() / 60

            commission = safe_float(row.get("commission"))
            if pd.isna(commission):
                commission = 0.0

            lot = safe_float(row.get("volume"))
            if pd.isna(lot):
                lot = 0.0

            cursor.execute(
                """
                INSERT INTO trades(
                    date, symbol, direction, entry, exit, lot, profit,
                    commission, setup, notes, risk, r_multiple, session,
                    timeframe, setup_score, mistake_type,
                    entry_time, exit_time, duration, screenshot,
                    subscription_key
                )
                VALUES(
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    date_value,
                    symbol,
                    direction,
                    None if pd.isna(entry_price) else float(entry_price),
                    None if pd.isna(exit_price) else float(exit_price),
                    float(lot),
                    0.0 if pd.isna(profit) else float(profit),
                    float(commission),
                    "",
                    "",
                    0.0,
                    0.0,
                    "",
                    "",
                    0,
                    "",
                    open_time.isoformat() if open_time else "",
                    close_time.isoformat() if close_time else "",
                    float(duration),
                    "",
                    subscription_key
                )
            )
            imported += 1

    conn.commit()
    return imported


def rerun_app():
    if hasattr(st, "rerun"):
        st.rerun()


def offer_legacy_trade_restore():
    current_key = get_current_subscription_key()
    if not current_key:
        return

    if count_trades_for_key(current_key) > 0:
        return

    report_files = find_report_history_files()
    if not report_files:
        return

    backup_file = report_files[0]
    st.sidebar.markdown("---")
    st.sidebar.warning(
        f"No saved trades were found for your current license key. A legacy backup file was detected: `{os.path.basename(backup_file)}`."
    )

    if st.sidebar.button("Restore legacy trade history"):
        imported = restore_trades_from_report_history(backup_file, current_key)
        if imported:
            st.sidebar.success(
                f"Imported {imported} legacy trade(s) from {os.path.basename(backup_file)}."
            )
            rerun_app()
        else:
            st.sidebar.error(
                "No trades were imported. The backup file may not contain compatible trade rows."
            )

offer_legacy_trade_restore()


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
    render_currency_metric(st, "Net Profit", metrics['total_profit'])
    st.metric("Win Rate", f"{metrics['win_rate']:.1f}%")
    # Account size and balance
    account_size = st.session_state.get("account_size", None)
    account_size = st.number_input("Account Size (USD)", value=float(account_size) if account_size else 10000.0, step=100.0, format="%.2f", key="account_size")
    balance = account_size + metrics['total_profit']
    render_currency_metric(st, "Account Balance", balance)
    render_currency_metric(st, "0.5% of Balance", balance * 0.005)
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

# ==================================
# TABS
# ==================================
(
    dashboard,
    journal,
    analytics,
    risk_tab,
    compounding,
    goals,
    psychology,
    admin
) = st.tabs([
    "📊 Dashboard",
    "📖 Journal",
    "📈 Analytics",
    "🛡 Risk Archive",
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

    # ==========================
    # KPI ROW 1
    # ==========================
    c1,c2,c3,c4,c5,c6 = st.columns(6)

    render_currency_metric(c1, "💰 Net Profit", metrics['total_profit'])

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

    render_currency_metric(c5, "⚡ Expectancy", metrics['expectancy'])

    c6.metric(
        "📊 Average R",
        round(metrics["avg_r"],2)
    )

    st.divider()

    # ==========================
    # KPI ROW 2
    # ==========================
    c1,c2,c3,c4,c5,c6 = st.columns(6)

    render_currency_metric(c1, "🥇 Largest Win", metrics['largest_win'])

    render_currency_metric(c2, "🥉 Largest Loss", metrics['largest_loss'])

    render_currency_metric(c3, "📈 Avg Winner", metrics['avg_win'])

    render_currency_metric(c4, "📉 Avg Loser", metrics['avg_loss'])

    render_currency_metric(c5, "🔻 Max DD", metrics['max_dd'])

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
        # EQUITY SUMMARY
        # ======================
        starting_capital = 10000
        equity_value = starting_capital + metrics['total_profit']

        st.subheader("📌 Equity Summary")
        c1, c2, c3 = st.columns(3)

        render_currency_metric(
            c1,
            "Starting Capital",
            starting_capital
        )

        render_currency_metric(
            c2,
            "Current Equity",
            equity_value
        )

        render_currency_metric(
            c3,
            "Max Drawdown",
            metrics['max_dd']
        )

        st.markdown(
            "_Full equity and drawdown charts are available in the Analytics tab._"
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

            st.divider()

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

        st.divider()

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

            st.write(
                style_profit_column(
                    df.sort_values(
                        "profit",
                        ascending=False
                    )
                    .head(10)
                )
            )

        with c2:

            st.subheader(
                "💀 Worst 10 Trades"
            )

            st.write(
                style_profit_column(
                    df.sort_values(
                        "profit",
                        ascending=True
                    )
                    .head(10)
                )
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
            account_balance = st.session_state.get("account_size", None)
            account_balance_value = float(account_balance) if account_balance else 10000.0
            default_risk = account_balance_value * 0.0025

            risk = st.number_input(
                "Risk Amount ($)",
                value=default_risk,
                key="risk"
            )

            st.caption("0.25% of account size")

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
            render_currency_metric(
                col1,
                "Net Profit/Loss",
                net_profit
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
                "Fibonacchi",
                "FVG",
                "CHoCH",
                "CRT",
                "20 EMA",
                "News Trading",
                "No Strategy"
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

            higher_high = st.checkbox(
                "Higher High",
                key="higher_high"
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

            lower_low = st.checkbox(
                "Lower Low",
                key="lower_low"
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

            lower_high = st.checkbox(
                "Lower High",
                key="lower_high"
            )

            higher_low = st.checkbox(
                "Higher Low",
                key="higher_low"
            )

            v_shape = st.checkbox(
                "V-Shape (Momentum)",
                key="v_shape"
            )

            delivery_from_fvg = st.checkbox(
                "Delivery from FVG",
                key="delivery_from_fvg"
            )

            silver_bullet = st.checkbox(
                "Silver Bullet",
                key="silver_bullet"
            )

        setup_score = min(sum([
            liquidity_sweep,
            htf_bias,
            equal_high,
            higher_high,
            fvg_present,
            cisd_present,
            ifvg_present,
            lower_low,
            session_valid,
            displacement,
            equal_low,
            lower_high,
            higher_low,
            v_shape,
            delivery_from_fvg,
            silver_bullet
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

        st.markdown("---")

        mistakes = st.session_state.get('mistakes', [])

        submitted = st.form_submit_button(
            "💾 Save Trade"
        )

        if submitted:
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
                        mistake_type,
                        entry_time,
                        exit_time,
                        duration,
                        screenshot,
                        subscription_key
                    )

                    VALUES(
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
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
                        ",".join(mistakes),
                        str(entry_time),
                        str(exit_time),
                        duration,
                        screenshot_path,
                        get_current_subscription_key()
                    )
                )

                conn.commit()

                st.success(
                    "Trade Saved Successfully ✅"
                )

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

                if hasattr(st, "rerun"):
                    st.rerun()

    st.divider()

    # ==================================
    # BULK IMPORT FROM CSV / XLSX
    # ==================================
    # Allow uploading a CSV or Excel export to import legacy trades

    st.divider()

    current_key = get_current_subscription_key()

    st.subheader("📥 Bulk import trades (CSV / Excel)")
    st.caption("Upload a ReportHistory Excel file or a CSV export. Imported rows will be assigned to your active subscription key if one is set.")

    uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xls", "xlsx"], key="bulk_import_file")

    if uploaded_file is not None:
        preview_df = None
        preview_error = None
        try:
            suffix = os.path.splitext(uploaded_file.name)[1].lower() or ".xlsx"
            raw_bytes = uploaded_file.getvalue()
            if suffix in (".xls", ".xlsx"):
                xls = pd.ExcelFile(io.BytesIO(raw_bytes))
                preview_df = xls.parse(xls.sheet_names[0], header=None)
            else:
                preview_df = pd.read_csv(io.BytesIO(raw_bytes), nrows=10)
        except Exception as e:
            preview_error = str(e)

        if preview_error:
            st.warning(f"Preview unavailable: {preview_error}")
        elif preview_df is not None:
            st.write("### Uploaded file preview")
            st.dataframe(preview_df.head(10))

        if current_key:
            st.info(f"Ready to import into subscription key: {current_key}")
        else:
            st.info("Ready to import without a subscription key. Imported rows will be stored with a blank key.")

        if st.button("Import uploaded file"):
            import tempfile
            try:
                suffix = os.path.splitext(uploaded_file.name)[1] or ".xlsx"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name

                imported = 0
                if suffix.lower() in (".xls", ".xlsx"):
                    imported = restore_trades_from_report_history(tmp_path, current_key)
                else:
                    # For CSV, attempt to parse as a simple table and reuse the excel restore by converting
                    # to a temporary Excel file for compatibility with existing parser
                    try:
                        df_csv = pd.read_csv(tmp_path)
                        excel_tmp = tmp_path + ".xlsx"
                        df_csv.to_excel(excel_tmp, index=False)
                        imported = restore_trades_from_report_history(excel_tmp, current_key)
                        try:
                            os.remove(excel_tmp)
                        except Exception:
                            pass
                    except Exception:
                        imported = 0

                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

                if imported:
                    st.success(f"Imported {imported} legacy trade(s).")
                    rerun_app()
                else:
                    st.error("No trades were imported. The file may not contain compatible trade rows.")
            except Exception as e:
                st.error(f"Import failed: {e}")

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
    

def load_latest_risk_answers(subscription_key):
    try:
        if subscription_key:
            cursor.execute(
                "SELECT note FROM psych_journal WHERE subscription_key=? AND mood=? ORDER BY id DESC LIMIT 1",
                (subscription_key, "Risk Reflection")
            )
        else:
            cursor.execute(
                "SELECT note FROM psych_journal WHERE mood=? ORDER BY id DESC LIMIT 1",
                ("Risk Reflection",)
            )
        row = cursor.fetchone()
        if not row:
            return {}
        note = row[0] or ""
        try:
            answers = json.loads(note)
            if isinstance(answers, dict):
                return answers
        except Exception:
            return {}
    except Exception:
        return {}
    return {}


# ==================================
# RISK ARCHIVE
# ==================================
with risk_tab:
    st.markdown("## 🛡 Risk Archive")
    st.markdown(
        "This Risk Archive tab is read-only. Use the Psychology tab to create and edit self-reflection and risk reflection entries."
    )
    st.markdown("---")

    subscription_key = get_current_subscription_key()
    saved_note = load_latest_risk_answers(subscription_key)

    if saved_note:
        st.subheader("Latest Risk Reflection")
        st.write(saved_note)
        st.info("Risk reflections are managed in the Psychology tab.")
    else:
        st.info("No saved risk reflection found. Use the Psychology tab to create one.")

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

def get_development_plan_items():
    return [
        "Reframed my goal around consistency and process, not proving myself.",
        "Followed my trading plan instead of acting impulsively.",
        "Defined my risk before entering the trade.",
        "Avoided revenge trading after a loss.",
        "Stayed calm and avoided trading under strong emotion.",
        "Reviewed my trades and identified one lesson.",
        "Tracked process metrics instead of only judging the result.",
        "Completed a weekly review and noted one improvement."
    ]


def load_latest_development_plan_state():
    plan_entries = [
        entry for entry in st.session_state.get("psych_journal", [])
        if entry.get("mood") == "Development Plan"
    ]
    if not plan_entries:
        return [], ""

    latest_entry = plan_entries[0]
    try:
        payload = json.loads(latest_entry.get("note", "{}"))
        completed = payload.get("completed", [])
        reflection = payload.get("reflection", "")
    except Exception:
        completed = []
        reflection = ""

    return completed, reflection


with psychology:
    st.markdown("## 🧠 Trading Psychology & Mindset")
    st.markdown("Log your mindset, track your mood, and get actionable psychology prompts.")

    st.markdown("### 🧭 Development Plan for a Non-Profitable Trader")
    st.caption("Use this checklist to build discipline, manage risk, and focus on the process instead of short-term results.")

    plan_items = get_development_plan_items()
    saved_completed, saved_reflection = load_latest_development_plan_state()
    selected_plan_items = st.multiselect(
        "Today’s development checkpoints",
        plan_items,
        default=saved_completed,
        key="development_plan_checklist"
    )

    progress_value = len(selected_plan_items) / len(plan_items) if plan_items else 0
    st.progress(progress_value)
    st.caption(f"{len(selected_plan_items)}/{len(plan_items)} checkpoints completed")

    weekly_reflection = st.text_area(
        "Weekly reflection",
        value=saved_reflection,
        key="development_plan_reflection",
        height=120
    )

    if st.button("💾 Save Development Plan Progress"):
        payload = {
            "completed": selected_plan_items,
            "reflection": weekly_reflection.strip(),
            "updated_at": datetime.now().isoformat()
        }
        note = json.dumps(payload, ensure_ascii=False)
        try:
            cursor.execute(
                "INSERT INTO psych_journal(date, mood, note, subscription_key) VALUES (?,?,?,?)",
                (str(datetime.now()), "Development Plan", note, get_current_subscription_key())
            )
            conn.commit()
            st.session_state.setdefault('psych_journal', [])
            st.session_state['psych_journal'].insert(0, {
                "id": cursor.lastrowid,
                "date": str(datetime.now()),
                "mood": "Development Plan",
                "note": note
            })
            st.success("Development plan progress saved.")
            rerun_app()
        except Exception as e:
            st.error(f"Failed to save development plan progress: {e}")

    st.markdown("#### Recent plan notes")
    plan_entries = [
        entry for entry in st.session_state.get("psych_journal", [])
        if entry.get("mood") == "Development Plan"
    ]
    if plan_entries:
        for entry in plan_entries[:3]:
            try:
                payload = json.loads(entry.get("note", "{}"))
                completed = payload.get("completed", [])
                reflection = payload.get("reflection", "")
            except Exception:
                completed = []
                reflection = ""
            st.markdown(f"**{entry.get('date')}**")
            if completed:
                st.caption("Completed: " + ", ".join(completed))
            if reflection:
                st.write(reflection)
            st.markdown("---")
    else:
        st.info("No development plan progress saved yet.")

    st.markdown("---")
    moods = ["😃 Great", "🙂 Good", "😐 Neutral", "😟 Stressed", "😢 Down"]
    # Load persisted psychology notes for this subscription or globally if no key
    if 'psych_journal' not in st.session_state:
        try:
            current_key = get_current_subscription_key()
            if current_key:
                cursor.execute(
                    "SELECT id, date, mood, note FROM psych_journal WHERE subscription_key=? ORDER BY id DESC",
                    (current_key,)
                )
            else:
                cursor.execute(
                    "SELECT id, date, mood, note FROM psych_journal ORDER BY id DESC"
                )
            rows = cursor.fetchall()
            st.session_state['psych_journal'] = [
                {"id": r[0], "date": r[1], "mood": r[2], "note": r[3]} for r in rows
            ]
        except Exception:
            st.session_state['psych_journal'] = []

    st.markdown("### Today's Mood")
    mood = st.radio("How do you feel about your trading today?", moods, horizontal=True)

    mistake_options = {
        "FOMO": "Review your plan before each trade and only act when your setup criteria are met.",
        "Overtrading": "Limit yourself to a predefined number of trades per session and prioritize quality over quantity.",
        "Moved Stop Loss": "Set your stop loss before entering the position and avoid adjusting it unless your edge changes.",
        "Moved Take Profit": "Define profit targets in advance and trust the process instead of reacting to short-term noise.",
        "Revenge Trading": "Take a break after a loss, journal the emotion, and only return when you are calm and objective.",
        "Ignored HTF Bias": "Always verify the higher-timeframe trend before taking lower-timeframe entries.",
        "Early Exit": "Use a consistent exit rule and avoid closing trades based on fear or temporary market fluctuations.",
        "Late Entry": "Wait for your signal to complete and don’t force trades before your edge is established.",
        "No Confirmation": "Require at least one confirmation signal before committing risk to a trade.",
        "Risked Too Much": "Use a fixed risk percentage and calculate position size based on stop loss distance."
    }

    st.markdown("### Mistake Tracking")
    st.session_state.setdefault('mistakes', [])
    mistakes = st.multiselect(
        "Mistakes Made",
        list(mistake_options.keys()),
        key="mistakes"
    )
    if mistakes:
        st.info("These mistakes will be included with the next trade save.")
        for mistake in mistakes:
            st.caption(f"**{mistake}**: {mistake_options[mistake]}")

    st.markdown("### Save Daily Mistakes")
    with st.form("daily_mistakes_form"):
        daily_mistakes = st.multiselect(
            "Mistakes to log for today",
            list(mistake_options.keys()),
            key="daily_mistakes"
        )
        if daily_mistakes:
            st.markdown("#### Suggested solutions")
            for mistake in daily_mistakes:
                st.caption(f"**{mistake}**: {mistake_options[mistake]}")
        daily_mistake_comments = st.text_area(
            "Optional journal notes for today's mistake log",
            key="daily_mistake_comments"
        )
        save_daily_mistakes = st.form_submit_button("Save Daily Mistakes")
        if save_daily_mistakes:
            if not daily_mistakes:
                st.warning("Select at least one mistake to save.")
            else:
                note = "Mistakes: " + ", ".join(daily_mistakes)
                if daily_mistake_comments.strip():
                    note += "\nComments: " + daily_mistake_comments.strip()
                try:
                    date_str = str(datetime.now())
                    cursor.execute(
                        "INSERT INTO psych_journal(date, mood, note, subscription_key) VALUES (?,?,?,?)",
                        (date_str, "Mistake Log", note, get_current_subscription_key())
                    )
                    conn.commit()
                    new_id = cursor.lastrowid
                    st.session_state.setdefault('psych_journal', [])
                    st.session_state['psych_journal'].insert(0, {
                        "id": new_id,
                        "date": date_str,
                        "mood": "Mistake Log",
                        "note": note
                    })
                    st.success("Daily mistakes saved independently.")
                    rerun_app()
                except Exception as e:
                    st.error(f"Failed to save daily mistakes: {e}")

    st.markdown("---")

    # ==========================
    # MISTAKE ANALYSIS
    # ==========================
    st.subheader("🚨 Mistake Analysis")

    trade_mistakes = pd.Series(dtype=str)
    if "mistake_type" in df.columns:
        trade_mistakes = (
            df["mistake_type"]
            .fillna("")
            .str.split(",")
            .explode()
            .str.strip()
        )
        trade_mistakes = trade_mistakes[trade_mistakes != ""]

    psych_mistake_notes = [
        entry.get("note", "") for entry in st.session_state.get("psych_journal", [])
        if entry.get("mood") == "Mistake Log"
    ]
    psych_mistakes = []
    for note in psych_mistake_notes:
        if note.startswith("Mistakes:"):
            mistake_text = note.split("Mistakes:", 1)[1].split("\n", 1)[0].strip()
            psych_mistakes.extend([m.strip() for m in mistake_text.split(",") if m.strip()])

    all_mistakes = pd.Series(list(trade_mistakes) + psych_mistakes)

    mistake_solutions = {
        "FOMO": "Review your plan before each trade and only act when your setup criteria are met.",
        "Overtrading": "Limit yourself to a predefined number of trades per session and prioritize quality over quantity.",
        "Moved Stop Loss": "Set your stop loss before entering the position and avoid adjusting it unless your edge changes.",
        "Moved Take Profit": "Define profit targets in advance and trust the process instead of reacting to noise.",
        "Revenge Trading": "Take a break after a loss, journal the emotion, and only return when you are calm and objective.",
        "Ignored HTF Bias": "Always verify the higher-timeframe trend before taking lower-timeframe entries.",
        "Early Exit": "Use a consistent exit rule and avoid closing trades based on fear or temporary market noise.",
        "Late Entry": "Wait for your signal to complete and don’t force trades before your edge is established.",
        "No Confirmation": "Require at least one confirmation signal before committing risk to a trade.",
        "Risked Too Much": "Use a fixed risk percentage and calculate position size based on stop loss distance."
    }

    if len(all_mistakes):
        mistake_counts = all_mistakes.value_counts()
        st.bar_chart(mistake_counts)

        st.markdown("### Mistake Analysis with Suggested Solutions")
        for mistake, count in mistake_counts.items():
            solution = mistake_solutions.get(str(mistake), "Review your trade journal and identify a corrective action.")
            st.markdown(f"**{mistake}** — {count} occurrence{'s' if count != 1 else ''}  ")
            st.markdown(f"- **Solution:** {solution}")

        if psych_mistake_notes:
            st.markdown("### Latest Daily Mistake Logs")
            for entry in [e for e in st.session_state.get("psych_journal", []) if e.get("mood") == "Mistake Log"]:
                st.markdown(f"**{entry.get('date')}**")
                st.write(entry.get("note"))
                st.markdown("---")
    else:
        if "mistake_type" not in df.columns and not psych_mistake_notes:
            st.info("No mistake-type data available for analysis.")
        else:
            st.info("No mistake categories found in your trading or psychology data.")

    st.divider()
    st.markdown("---")

    st.markdown("### Saved Risk Reflections")
    risk_reflections = [
        entry for entry in st.session_state.get('psych_journal', [])
        if entry.get('mood') == 'Risk Reflection'
    ]
    if risk_reflections:
        for i, entry in enumerate(risk_reflections):
            entry_id = str(entry.get('id') or f'noid_{i}')
            editing_key = f"edit_risk_{entry_id}"
            edit_mode = st.session_state.get(editing_key, False)
            with st.expander(entry['date'], expanded=False):
                note_text = entry.get('note', '') or ''
                if edit_mode:
                    with st.form(f"edit_risk_form_{entry_id}"):
                        new_note = st.text_area(
                            "Risk reflection",
                            value=note_text,
                            key=f"edit_risk_note_{entry_id}"
                        )
                        save_changes = st.form_submit_button("Save Risk Reflection Changes")
                        if save_changes:
                            try:
                                cursor.execute(
                                    "UPDATE psych_journal SET note=? WHERE id=?",
                                    (new_note, entry.get('id'))
                                )
                                conn.commit()
                                st.session_state[editing_key] = False
                                st.success("Risk reflection updated.")
                                rerun_app()
                            except Exception as e:
                                st.error(f"Failed to update reflection: {e}")
                else:
                    parsed = None
                    if note_text:
                        try:
                            parsed = json.loads(note_text)
                        except Exception:
                            parsed = None
                    if isinstance(parsed, dict):
                        for k, v in parsed.items():
                            st.markdown(f"**{k}.** {v}")
                            st.markdown("---")
                    else:
                        st.write(note_text)
                    if st.button("Edit this risk reflection", key=f"edit_risk_btn_{entry_id}"):
                        st.session_state[editing_key] = True
                        rerun_app()
    else:
        st.info("No saved risk reflections yet. Use the section below to create one.")

    st.markdown("---")
    st.markdown("### New Risk Reflection")
    with st.form("new_risk_reflection_form"):
        new_risk_note = st.text_area(
            "Write a new risk reflection note",
            key="new_risk_note"
        )

        save_risk_reflection = st.form_submit_button("Save Risk Reflection")

        if save_risk_reflection:
            if not new_risk_note.strip():
                st.warning("Enter a reflection note before saving.")
            else:
                try:
                    cursor.execute(
                        "INSERT INTO psych_journal(date, mood, note, subscription_key) VALUES (?,?,?,?)",
                        (
                            str(datetime.now()),
                            "Risk Reflection",
                            new_risk_note.strip(),
                            get_current_subscription_key()
                        )
                    )
                    conn.commit()
                    new_id = cursor.lastrowid
                    st.session_state.setdefault('psych_journal', [])
                    st.session_state['psych_journal'].insert(0, {
                        "id": new_id,
                        "date": str(datetime.now()),
                        "mood": "Risk Reflection",
                        "note": new_risk_note.strip()
                    })
                    st.success("Risk reflection saved.")
                    rerun_app()
                except Exception as e:
                    st.error(f"Failed to save risk reflection: {e}")

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
                new_id = cursor.lastrowid
            except Exception as e:
                st.error(f"Failed to save quick reflections: {e}")
            else:
                st.session_state.setdefault('psych_journal', [])
                st.session_state['psych_journal'].insert(0, {"id": new_id, "date": date_str, "mood": mood, "note": note})
                st.success("Quick reflections saved")
                st.rerun()
        else:
            st.warning("No responses entered to save.")

    st.markdown("---")
    st.markdown("### Reflection Analysis")
    psych_entries = st.session_state.get('psych_journal', [])
    if psych_entries:
        try:
            df_ref = pd.DataFrame(psych_entries)
            total_logs = len(df_ref)
            risk_count = int((df_ref['mood'] == 'Risk Reflection').sum()) if 'mood' in df_ref.columns else 0
            mistake_log_count = int((df_ref['mood'] == 'Mistake Log').sum()) if 'mood' in df_ref.columns else 0
            other_notes = total_logs - risk_count - mistake_log_count
            latest_log = psych_entries[0]

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Logs", total_logs)
            col2.metric("Risk Reflections", risk_count)
            col3.metric("Mistake Logs", mistake_log_count)
            col4.metric("Other Notes", other_notes)

            st.markdown("#### Mood / Log Breakdown")
            if 'mood' in df_ref.columns:
                mood_counts = df_ref['mood'].value_counts()
                st.bar_chart(mood_counts)
            else:
                st.info("No mood data available for log breakdown.")

            st.markdown("#### Log Tracker")
            tracker_cols = st.columns(3)
            tracker_cols[0].metric("Last Log Saved", latest_log.get('date', 'N/A'))
            tracker_cols[1].metric("Last Mood", latest_log.get('mood', 'N/A'))
            tracker_cols[2].metric("Latest Entry Type", latest_log.get('mood', 'N/A'))

            st.markdown("#### Recent Reflections")
            for entry in psych_entries[:5]:
                st.markdown(f"**{entry.get('date')}** — {entry.get('mood')}")
                st.write(entry.get('note'))
                st.markdown("---")
        except Exception as e:
            st.error(f"Failed to generate reflection analysis: {e}")
    else:
        st.info("No reflection entries yet. Save a note, mistake log, or risk reflection to start tracking.")

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
                sent_time = datetime.fromisoformat(otp_time) if isinstance(otp_time, str) else None
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
                        key_label = selected_meta.get("key_label") if selected_meta and selected_meta.get("key_label") else (sel_hash[:8] if isinstance(sel_hash, str) else "")
                        subject = tpl.get("subject", "Subscription key updated: {key}").format(key=key_label)
                        body = tpl.get("body", "Admin {admin} updated key {key}").format(
                            admin=admin_user,
                            key=key_label,
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
                        key_label = selected_meta.get("key_label") if selected_meta and selected_meta.get("key_label") else (sel_hash[:8] if isinstance(sel_hash, str) else "")
                        subject = tpl.get("subject", "Subscription key removed: {key}").format(key=key_label)
                        body = tpl.get("body", "Admin {admin} removed key {key}").format(admin=admin_user, key=key_label)
                        send_admin_email(subject, body)
                        st.rerun()
                    else:
                        st.error("Failed to remove key.")
        else:
            st.info("No database-subscription keys to edit. Add a key above.")

