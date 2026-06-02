# 🚀 Quick Start: Deploy to Streamlit Cloud

This is a quick reference for deploying your Forex Tracker Pro to Streamlit Cloud.

## Prerequisites
- GitHub account with your repo pushed
- Streamlit account (free: streamlit.io/cloud)
- Subscription keys and payment URLs ready

## Deployment in 5 Minutes

### Step 1: Connect to Streamlit Cloud
```
1. Go to https://share.streamlit.io
2. Click "New app"
3. Select your GitHub repo and branch
4. Set main file: sustainable_forex_journal.py
5. Click "Deploy"
```

App will deploy (takes 2-3 minutes on first run).

### Step 2: Add Secrets (CRITICAL)
```
1. Go to your app's page: https://share.streamlit.io/@yourname/appname
2. Click ⚙️ Settings (top right)
3. Click "Secrets" in sidebar
4. Click "Edit secrets"
5. Paste the complete secrets block below:
```

### Complete Secrets Block (Copy & Paste)

Replace the `your-...` values with your actual values:

```toml
# ========================================
# REQUIRED: PAYMENT CONFIGURATION
# ========================================
SUBSCRIPTION_PAYMENT_LINK = "https://buy.stripe.com/YOUR_STRIPE_LINK"
WHOP_CHECKOUT_URL = "https://whop.com/YOUR_STORE/YOUR_PRODUCT/checkout"

# ========================================
# REQUIRED: SUBSCRIPTION KEYS
# ========================================
VALID_SUBSCRIPTION_KEYS = "PRO-001,PRO-002,PRO-003,PRO-004,PRO-005"

# ========================================
# REQUIRED: SECURITY SECRETS
# ========================================
SUBSCRIPTION_KEY_HASH_SECRET = "your-random-secret-string-32-chars"
ADMIN_KEY = "your-admin-secret-key-change-me"

# ========================================
# REQUIRED: ADMIN EMAIL
# ========================================
ADMIN_NOTIFICATION_EMAIL = "avogrowk@gmail.com"

# ========================================
# BANKING DETAILS (for manual payments)
# ========================================
ONE_TIME_PRICE = "30"
ONE_TIME_CURRENCY = "$"
ONE_TIME_LOCAL_PRICE = "R550"
BANK_NAME = "Capitec Bank"
BANK_ACCOUNT_HOLDER = "MR E AUGUSTYN"
BANK_ACCOUNT_NUMBER = "2520993738"
BANK_BRANCH_CODE = "470010"
WHATSAPP_PROOF_URL = "https://wa.me/27762123384"
```

### Step 3: Save & Deploy
```
1. Click "Save" button
2. App auto-redeploys (1-2 min)
3. Check app logs for errors: View logs (top right)
4. App should now load without subscription prompts
```

## Verify It's Working

Your app URL: `https://share.streamlit.io/@yourname/appname`

✅ App loads → Secrets working
❌ "Please enter valid subscription key" → Check secrets (typos, missing values)
❌ "StreamlitAPIException" in logs → Check TOML format (use only double quotes)

## Generating Secure Secrets

See **[GENERATE_SECRETS.md](GENERATE_SECRETS.md)** for Python commands to generate:
- Random `SUBSCRIPTION_KEY_HASH_SECRET`
- Random `ADMIN_KEY`
- Random `VALID_SUBSCRIPTION_KEYS` list

## Common Issues

### ❌ "Please enter a valid subscription key"
- **Fix**: Ensure `VALID_SUBSCRIPTION_KEYS` is set and restart app

### ❌ "TOML parsing error"
- **Fix**: Use only double quotes `"`, not single quotes `'`
- **Fix**: Check each line ends with quote, no trailing commas

### ❌ App takes forever to load
- **Fix**: Check logs for errors (View logs button)
- **Fix**: App may be spinning up (takes 2-3 min first run)

### ❌ Secrets don't appear in code
- **Fix**: Redeploy app or refresh page
- **Fix**: Check `.streamlit/secrets.toml` is in `.gitignore`

## Update Secrets Later

Go to Settings → Secrets → Edit secrets anytime to:
- Add new subscription keys
- Update payment links
- Change admin email
- Fix typos

Changes take effect on save (auto-redeploy).

## Local Testing (Optional)

To test locally before cloud deployment:

```bash
# 1. Copy example secrets
cp .streamlit/secrets.toml.example .streamlit/secrets.toml

# 2. Edit with your values
nano .streamlit/secrets.toml

# 3. Run locally
streamlit run sustainable_forex_journal.py
```

## Next Steps

1. ✅ Deploy to Streamlit Cloud
2. ✅ Add secrets from this guide
3. ✅ Test app loads and subscription gate works
4. 📧 Share your app URL with users
5. 🔑 Distribute subscription keys to paying customers
6. 💰 Monitor user registrations in admin dashboard

## Resources

- [Streamlit Cloud Docs](https://docs.streamlit.io/deploy/streamlit-cloud)
- [Secrets Management](https://docs.streamlit.io/deploy/streamlit-cloud/manage-your-app/secrets-management)
- [Full Setup Guide](STREAMLIT_CLOUD_SETUP.md)
- [Detailed Deployment Docs](DEPLOYMENT_STREAMLIT_CLOUD.md)

---

**Questions?** Check:
1. [STREAMLIT_CLOUD_SETUP.md](STREAMLIT_CLOUD_SETUP.md) - Full deployment guide
2. [GENERATE_SECRETS.md](GENERATE_SECRETS.md) - How to generate secure secrets
3. View logs in your Streamlit app (top right)
