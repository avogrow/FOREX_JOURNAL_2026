# Deploy Forex Tracker Pro to Streamlit Cloud

This guide walks through deploying the subscription-gated Forex Tracker Pro to Streamlit Cloud with payment integration.

## Prerequisites

1. **GitHub account** (required for Streamlit Cloud connection)
2. **Payment provider account** such as Stripe or Whop
3. **Admin email**: avogrowk@gmail.com

## Step 1: Create GitHub Repository

1. Create a new public GitHub repository named `forex-tracker-pro`
2. Clone it locally:
   ```bash
   git clone https://github.com/<your-username>/forex-tracker-pro.git
   cd forex-tracker-pro
   ```
3. Copy all files from this project into the repo:
   ```bash
   cp -r c:\Users\USER\Desktop\2026\ Trading\* .
   ```
4. Create `.gitignore`:
   ```
   __pycache__/
   *.pyc
   *.db
   .streamlit/secrets.toml
   *.csv
   *.json
   screenshots/
   venv/
   .DS_Store
   ```
5. Commit and push:
   ```bash
   git add .
   git commit -m "Initial Forex Tracker Pro subscription setup"
   git push origin main
   ```

## Step 2: Set Up Payment Checkout

If you are using Stripe, Whop, or another checkout provider, configure your subscription product and payment page.

For a direct checkout link (recommended for Whop):
1. Create or copy your Whop checkout URL
2. Set `WHOP_CHECKOUT_URL` to that link in your Streamlit secrets

Example:

```toml
WHOP_CHECKOUT_URL = "https://whop.com/your-store/your-product/checkout"
```

If you also want a generic provider fallback, set `SUBSCRIPTION_PAYMENT_LINK` as well.

If you want a backend-generated checkout session, you can still use Stripe or another provider with a webhook/backend integration.

## Optional Whop webhook provisioning

If you want Whop purchases to automatically provision app access, run `whop_webhook_server.py` alongside the Streamlit app and configure your Whop webhook endpoint to post to `/whop-webhook`.

1. Set the following environment variables in Streamlit Cloud or your hosting environment:
   - `WHOP_WEBHOOK_SECRET` (base64-encoded secret from Whop webhook settings)
   - `ADMIN_NOTIFICATION_EMAIL`
   - optional SMTP values: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`
   - optional `WHOP_DB_PATH` if the webhook server should use a different SQLite path than `forex_tracker.db`
2. Deploy `whop_webhook_server.py` to a host that can receive Whop webhooks.
3. In Whop dashboard, configure the webhook for `payment.succeeded` and/or `membership.activated` events.
4. After a purchase, the webhook server will generate a license key and store it in the same SQLite DB used by the app.

## Step 3: Deploy to Streamlit Cloud

1. Go to [Streamlit Cloud Dashboard](https://share.streamlit.io)
2. Click **"New app"**
3. Connect your GitHub account if not already connected
4. Select:
   - **Repository**: `<your-username>/forex-tracker-pro`
   - **Branch**: `main`
   - **Main file path**: `sustainable_forex_journal.py`
5. Click **"Deploy"** and wait for the app to load

## Step 4: Configure Secrets in Streamlit Cloud

1. In the Streamlit Cloud dashboard for your app, click **"Manage secrets"**
2. Add the following to `secrets.toml`:

```toml
# Payment provider integration (Stripe, Whop, Gumroad, Paddle, etc.)
WHOP_CHECKOUT_URL = "https://your-whop-checkout-url"
SUBSCRIPTION_PAYMENT_LINK = "https://your-payment-provider-checkout-url"

# One-time purchase pricing and enrollment details
ONE_TIME_PRICE = "30"
ONE_TIME_CURRENCY = "$"
ONE_TIME_LOCAL_PRICE = "R550"
BANK_NAME = "Capitec Bank"
BANK_ACCOUNT_HOLDER = "MR E AUGUSTYN"
BANK_ACCOUNT_NUMBER = "2520993738"
BANK_BRANCH_CODE = "470010"
WHATSAPP_PROOF_URL = "https://wa.me/27762123384?text=Hi%20Ettiene!%20I%20just%20paid%20for%20the%20Pr1ceForm%20Smart%20Money%20Indicator.%20Please%20find%20my%20proof%20of%20payment%20attached."

# Or use backend checkout generation:
SUBSCRIPTION_BACKEND_URL = "https://your-backend.com/create-checkout-session"

# Key Management
SUBSCRIPTION_KEY_HASH_SECRET = "your-random-secret-key-change-me"

# Admin Notification
ADMIN_NOTIFICATION_EMAIL = "avogrowk@gmail.com"
ADMIN_KEY = "admin-secret-key"

# SMTP (for email notifications) - Optional
# Example Gmail setup (recommended: use App Passwords with 2FA):
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "your-gmail@gmail.com"
SMTP_PASS = "<YOUR_SMTP_APP_PASSWORD>"

# Initial Subscription Keys (comma-separated or list format)
# VALID_SUBSCRIPTION_KEYS = "PRO-USER-001,PRO-USER-002,PRO-USER-003"
```

3. Click **"Save"**
4. The app will auto-reload with the new secrets

## Step 5: Manage Subscription Keys

### Option A: Via Admin Dashboard (Recommended)

1. Access your deployed app at: `https://<your-username>-forex-tracker-pro.streamlit.app`
2. Unlock with your initial `ADMIN_KEY`
3. Go to the **🔧 Admin** tab
4. Create, enable, or disable subscription keys directly in the UI

### Option B: Via Stripe

1. Each customer purchases through your Stripe checkout
2. After payment, manually create a subscription key in the Admin tab
3. Send the key to the customer via email

### Option C: Direct CSV Updates

1. Update `valid_subscription_keys.csv` in your repo:
   ```csv
   key,user,email,plan,expires,active
   PRO-USER-001,John Doe,john@example.com,monthly,2026-12-31,true
   ```
2. Commit and push: `git push origin main`
3. Streamlit will auto-redeploy with new keys

## Step 6: Test the Live App

1. Visit your live app URL
2. Test subscription gate:
   - Try entering an invalid key → should see "Subscription required"
   - Click "New here? Register for access"
   - Fill registration form → request saved
3. Click **"Subscribe now"** → redirects to your payment provider checkout
4. After simulated purchase, test unlock with new key

## Step 7: Enable Admin Email Notifications (Optional)

To send registration requests via email:

1. Use Gmail App Password:
   - Enable 2FA on your Gmail account
   - Go to [Google Account Security](https://myaccount.google.com/security)
   - Create an App Password (for Gmail)
   - Copy the 16-character password

2. Update secrets:
   ```toml
   ADMIN_NOTIFICATION_EMAIL = "avogrowk@gmail.com"
   SMTP_HOST = "smtp.gmail.com"
   SMTP_PORT = 587
   SMTP_USER = "your-gmail@gmail.com"
   SMTP_PASS = "xxxx xxxx xxxx xxxx"  # 16-char app password
   ```

3. Save and redeploy
4. Optionally test locally before deploy with:
   ```bash
   python test_email_notification.py
   ```

## Monitoring & Support

- View logs in Streamlit Cloud dashboard: **"Manage app" → "View logs"**
- Admin tab shows:
  - Subscription key audit log
  - Pending registration requests
  - Email template customization

## Quick Reference: URLs

| Component | URL |
|-----------|-----|
| **Live App** | `https://<your-username>-forex-tracker-pro.streamlit.app` |
| **Admin Dashboard** | Same app URL + unlock with ADMIN_KEY |
| **Stripe Checkout** | Configured in secrets.toml |
| **GitHub Repo** | `https://github.com/<your-username>/forex-tracker-pro` |

## Troubleshooting

**"Subscription required" always shows:**
- Check secrets are saved (click "Manage secrets" again)
- Verify `SUBSCRIPTION_PAYMENT_LINK` is set
- Clear browser cache and reload

**Email notifications not working:**
- Verify SMTP credentials are correct
- Check Gmail 2FA is enabled and App Password is generated
- Review logs in Streamlit Cloud dashboard

**Admin tab not visible:**
- Ensure you're using a valid `ADMIN_KEY` to unlock
- Check app code includes admin section (it does by default)

