# Forex Tracker Pro Ultimate

This is a Streamlit-based forex trade journal app designed for subscription-based use.

## Deploying as a subscription app

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run locally:

```bash
streamlit run sustainable_forex_journal.py
```

3. Deploy to Streamlit Cloud:

- Create a new app in Streamlit Cloud.
- Point it at this repository or upload the project folder.
- Set the following secrets in Streamlit Cloud:
  - `VALID_SUBSCRIPTION_KEYS` as a comma-separated list of active keys, or
  - `valid_subscription_keys` as a list in `secrets.toml`
  - `SUBSCRIPTION_PAYMENT_LINK` or `subscription_payment_link` with your payment/checkout URL, or
  - `SUBSCRIPTION_BACKEND_URL` if you are using the checkout session backend.

## Subscription gating

The app now requires a valid subscription key before it will run.

- `VALID_SUBSCRIPTION_KEYS`: comma-separated keys provided to paid subscribers.
- `valid_subscription_keys`: list of keys stored in `st.secrets`.
- `valid_subscription_keys.txt`: local text file with one key per line.
- `SUBSCRIPTION_PAYMENT_LINK`: optional link to your payment page.

If you use Stripe, Whop, Gumroad, Paddle, or another checkout provider, set `WHOP_CHECKOUT_URL` or `SUBSCRIPTION_PAYMENT_LINK` to your provider's checkout URL.
The app will show a subscription link in the sidebar when the user is not unlocked.

### Whop checkout example

For a Whop direct checkout flow, set:

```toml
whop_checkout_url = "https://whop.com/your-store/your-product/checkout"
```

This opens the Whop payment page directly from the app sidebar. If you also use a generic provider URL, keep `subscription_payment_link` as a fallback.

### Example `secrets.toml`

```toml
whop_checkout_url = "https://your-whop-checkout-url"
subscription_payment_link = "https://your-payment-provider-checkout-url"
one_time_price = "30"
one_time_currency = "$"
one_time_local_price = "R550"
bank_name = "Capitec Bank"
bank_account_holder = "MR E AUGUSTYN"
bank_account_number = "2520993738"
bank_branch_code = "470010"
whatsapp_proof_url = "https://wa.me/27762123384?text=Hi%20Ettiene!%20I%20just%20paid%20for%20the%20Pr1ceForm%20Smart%20Money%20Indicator.%20Please%20find%20my%20proof%20of%20payment%20attached."
valid_subscription_keys = ["PRO-USER-123", "PRO-USER-456"]
```

### Bank transfer and WhatsApp proof

If you want the enrollment flow to match the Pr1ceForm process, configure bank transfer details and a WhatsApp proof-of-payment link. The app will show one-time lifetime access pricing, bank details, and a WhatsApp payment proof link on the locked landing page.

## Optional Checkout backend example

If you want an example server that generates Stripe Checkout session URLs, use `stripe_checkout_server.py`.

1. Install extra dependencies:

```bash
pip install flask stripe
```

2. Set environment variables:

- `STRIPE_SECRET_KEY`
- `STRIPE_PRICE_ID`
- `DOMAIN_URL` (e.g. `https://your-app.example.com`)

3. Start the backend:

```bash
python stripe_checkout_server.py
```

4. Use the returned URL as `SUBSCRIPTION_PAYMENT_LINK` in your app config.

## Optional Whop webhook provisioning backend

If you want purchases to automatically provision license keys in the app, run `whop_webhook_server.py` alongside the Streamlit app and configure Whop webhooks to POST to it.

1. Install extra dependencies:

```bash
pip install flask
```

2. Set environment variables:

- `WHOP_WEBHOOK_SECRET`: your Whop webhook secret (base64-encoded secret string from the Whop dashboard)
- `ADMIN_NOTIFICATION_EMAIL`: admin email to receive provisioning notifications
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` if email notifications are desired
- `WHOP_DB_PATH`: optional path to the same SQLite DB used by the Streamlit app (defaults to `forex_tracker.db`)

3. Start the webhook server:

```bash
python whop_webhook_server.py
```

4. In the Whop dashboard, configure a webhook endpoint for `payment.succeeded` and/or `membership.activated` events to point at `https://<your-server>/whop-webhook`.

5. After a valid purchase, the backend will create a new license key and store it in the same subscription database used by the Streamlit app.

### Example `.env` values

```env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PRICE_ID=price_1Example2
DOMAIN_URL=https://your-app.example.com
```

## Notes

- Replace the payment link with your Stripe, Whop, Paddle, Gumroad, or other subscription checkout URL.
- Manage subscription keys in your chosen order system and add them to secrets.
- New users can request registration directly from the sidebar when they do not yet have a subscription key.
- To verify email delivery locally, you can use the helper script `test_email_notification.py`.

## Local email notification test

1. Create `.streamlit/secrets.toml` or export environment variables with SMTP settings:

```toml
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "your-gmail@gmail.com"
SMTP_PASS = "<YOUR_SMTP_APP_PASSWORD>"
ADMIN_NOTIFICATION_EMAIL = "avogrowk@gmail.com"
```

2. Run:

```bash
python test_email_notification.py
```

3. The script will print whether the notification was sent and show the last email error if it failed.

## Container deployment

A Docker-based deployment is included for local or cloud container hosting.

1. Build the container:

```bash
docker build -t forex-tracker-pro .
```

2. Start the app and reverse proxy:

```bash
docker compose up --build
```

3. Visit `http://localhost` in your browser.

The app listens on port `8501` internally and is proxied through `nginx` on port `80`.

## GitHub Actions security check

A basic CI workflow is included at `.github/workflows/security-check.yml`.
It performs:

- Python environment setup
- dependency install
- syntax validation of `sustainable_forex_journal.py`
- import validation for core runtime packages

This workflow runs on `push` and `pull_request` events.
