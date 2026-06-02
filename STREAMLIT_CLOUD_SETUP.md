# Streamlit Cloud Deployment Guide

This guide will help you deploy your Forex Tracker Pro app to Streamlit Cloud with all required secrets.

## Step 1: Prepare Your Repository

Ensure your GitHub repository contains:
- `sustainable_forex_journal.py` (main app)
- `requirements.txt` (dependencies)
- `valid_subscription_keys.csv` (optional, for local keys)
- `.streamlit/config.toml` (optional, for custom settings)

## Step 2: Create Streamlit Cloud Account

1. Go to [Streamlit Cloud](https://streamlit.io/cloud)
2. Sign up with GitHub (required for deployment)
3. Click "New app"

## Step 3: Deploy the App

1. Click "New app" → "From existing repo"
2. Select your GitHub repo and branch
3. Set the main file path to: `sustainable_forex_journal.py`
4. Click "Deploy"

## Step 4: Add Secrets to Streamlit Cloud

Once deployed, go to your app dashboard:

1. Click the ⚙️ **Settings** icon (top right of app)
2. Select **Secrets** from the sidebar
3. Click **Edit secrets**
4. Paste the secrets below (replacing placeholder values with your actual values)

### Complete Secrets Configuration

Copy and paste this entire block into the Streamlit Cloud secrets editor:

```toml
# ========================================
# PAYMENT & SUBSCRIPTION
# ========================================
WHOP_CHECKOUT_URL = "https://your-whop-checkout-url"
SUBSCRIPTION_PAYMENT_LINK = "https://buy.stripe.com/test_..."

# ========================================
# KEY MANAGEMENT
# ========================================
SUBSCRIPTION_KEY_HASH_SECRET = "your-super-secret-random-string-change-me"

# Initial subscription keys (comma-separated)
VALID_SUBSCRIPTION_KEYS = "PRO-USER-001,PRO-USER-002,PRO-USER-003"

# ========================================
# ADMIN ACCESS
# ========================================
ADMIN_KEY = "your-admin-secret-key-change-me"
ADMIN_NOTIFICATION_EMAIL = "avogrowk@gmail.com"

# ========================================
# ONE-TIME PURCHASE / ENROLLMENT
# ========================================
ONE_TIME_PRICE = "30"
ONE_TIME_CURRENCY = "$"
ONE_TIME_LOCAL_PRICE = "R550"
BANK_NAME = "Capitec Bank"
BANK_ACCOUNT_HOLDER = "MR E AUGUSTYN"
BANK_ACCOUNT_NUMBER = "2520993738"
BANK_BRANCH_CODE = "470010"
WHATSAPP_PROOF_URL = "https://wa.me/27762123384?text=Hi%20Ettiene!%20I%20just%20paid%20for%20the%20Pr1ceForm%20Smart%20Money%20Indicator.%20Please%20find%20my%20proof%20of%20payment%20attached."

# ========================================
# OPTIONAL: EMAIL NOTIFICATIONS
# ========================================
# SMTP_SERVER = "smtp.gmail.com"
# SMTP_PORT = "587"
# SMTP_USER = "your-email@gmail.com"
# SMTP_PASSWORD = "your-app-password"

# ========================================
# OPTIONAL: WHOP WEBHOOK
# ========================================
# WHOP_WEBHOOK_SECRET = "your-whop-webhook-secret"
```

## Step 5: Generate Required Secrets (First Time Setup)

### Generate a Random Hash Secret

In Python:
```python
import secrets
print(secrets.token_hex(32))
```

Output example: `a3f8e9b2c1d7f4e6a5b9c2d8e1f7a4b5`

### Generate an Admin Key

In Python:
```python
import secrets
print(secrets.token_urlsafe(32))
```

Output example: `8Zyh_N-4f5K2pL9qR3sT6uV1wX2yZ3aB`

## Step 6: Verify Secrets Are Working

1. After adding secrets, click **Save**
2. Your app will automatically redeploy
3. Check the app logs for any errors (View logs)
4. The app should load without subscription errors

## Secrets Summary Table

| Secret | Purpose | Required | Default |
|--------|---------|----------|---------|
| `VALID_SUBSCRIPTION_KEYS` | Comma-separated list of active subscription keys | ✓ | None |
| `SUBSCRIPTION_PAYMENT_LINK` | Link to payment/checkout page | ✓ | None |
| `WHOP_CHECKOUT_URL` | Direct Whop checkout URL (alternative) | ✗ | None |
| `SUBSCRIPTION_KEY_HASH_SECRET` | Secret for hashing keys (security) | ✓ | "change-me" |
| `ADMIN_KEY` | Secret to unlock admin dashboard | ✓ | None |
| `ADMIN_NOTIFICATION_EMAIL` | Email for registration notifications | ✓ | "avogrowk@gmail.com" |
| `ONE_TIME_PRICE` | Price in USD | ✗ | "30" |
| `ONE_TIME_CURRENCY` | Currency symbol | ✗ | "$" |
| `ONE_TIME_LOCAL_PRICE` | Price in local currency | ✗ | "R550" |
| `BANK_NAME` | Bank name for manual payment | ✗ | "Capitec Bank" |
| `BANK_ACCOUNT_HOLDER` | Account holder name | ✗ | "MR E AUGUSTYN" |
| `BANK_ACCOUNT_NUMBER` | Account number | ✗ | "2520993738" |
| `BANK_BRANCH_CODE` | Bank branch code | ✗ | "470010" |
| `WHATSAPP_PROOF_URL` | WhatsApp URL for payment proof | ✗ | WhatsApp link |

## Troubleshooting

### App won't load / "Please enter a valid subscription key"

**Solution**: Ensure `VALID_SUBSCRIPTION_KEYS` is set in secrets. Check app logs for errors.

### Secrets not appearing in app

**Solution**: 
1. Secrets only take effect after redeployment
2. Check that secrets are in the correct TOML format
3. Restart the app: Settings → Advanced → Reboot app

### "StreamlitAPIException: Secrets file not found"

**Solution**: This is normal on first run. Just add the secrets and redeploy.

## Local Testing Before Cloud Deployment

To test locally with secrets:

1. Create `.streamlit/secrets.toml` in your project folder:
```
mkdir .streamlit
```

2. Copy your secrets into `.streamlit/secrets.toml`

3. Test locally:
```bash
streamlit run sustainable_forex_journal.py
```

**Note**: Never commit `.streamlit/secrets.toml` to GitHub. Add it to `.gitignore`.

## Next Steps

1. Update your README with deployment instructions
2. Set up subscription key management in your admin dashboard
3. Configure email notifications (optional)
4. Monitor app usage in Streamlit Cloud dashboard

## Resources

- [Streamlit Cloud Docs](https://docs.streamlit.io/deploy/streamlit-cloud)
- [Managing Secrets in Streamlit](https://docs.streamlit.io/deploy/streamlit-cloud/manage-your-app/secrets-management)
- [Advanced Configuration](https://docs.streamlit.io/library/advanced-features/configuration)
