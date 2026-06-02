# Streamlit Cloud Deployment Checklist

## Phase 1: GitHub Setup ✅

- [ ] Create GitHub account (if not already)
- [ ] Create new public repo: `forex-tracker-pro`
- [ ] Clone the repo locally
- [ ] Copy all project files into the repo
- [ ] Create `.gitignore` (template in DEPLOYMENT_STREAMLIT_CLOUD.md)
- [ ] Run: `git add . && git commit -m "Initial setup" && git push origin main`

## Phase 2: Stripe Setup ✅

- [ ] Create a Stripe or Whop account
- [ ] Create a subscription product or plan
- [ ] Copy your checkout URL from the provider
- [ ] If using Stripe backend checkout, copy the Price ID and secret key as needed

## Phase 3: Streamlit Cloud Deploy ✅

- [ ] Go to share.streamlit.io
- [ ] Click **"New app"**
- [ ] Connect GitHub account
- [ ] Select: Repository = `forex-tracker-pro`, Branch = `main`, File = `sustainable_forex_journal.py`
- [ ] Click **"Deploy"** and wait ~2 mins for first load
- [ ] Copy your live app URL: `https://<username>-forex-tracker-pro.streamlit.app`

## Phase 4: Configure Secrets ✅

- [ ] In Streamlit Cloud dashboard, click **"Manage secrets"**
- [ ] Paste the template from `secrets.toml.example`
- [ ] Replace with your actual values:
  - `WHOP_CHECKOUT_URL` or `SUBSCRIPTION_PAYMENT_LINK`: Your payment provider checkout URL
  - `SUBSCRIPTION_KEY_HASH_SECRET`: A random unique string
  - `ADMIN_KEY`: A random admin password
  - `ADMIN_NOTIFICATION_EMAIL`: avogrowk@gmail.com (already set)
- [ ] Click **"Save"** and wait for app to reload

## Phase 5: Generate Initial Keys ✅

Option A: Create via Admin Dashboard
- [ ] Visit your live app
- [ ] Click **🔧 Admin** tab → Unlock with your `ADMIN_KEY`
- [ ] Create first subscription key manually

Option B: Add to secrets
- [ ] Update secrets.toml with initial keys:
  ```toml
  VALID_SUBSCRIPTION_KEYS = "PRO-USER-001,PRO-USER-002"
  ```
- [ ] Save and app will reload

## Phase 6: Test Deployment ✅

- [ ] Visit live app URL in browser
- [ ] Try invalid key → should show "Subscription required"
- [ ] Click "Request registration" → fill form → submit
- [ ] Check registration request shows in Admin tab
- [ ] Click "Subscribe now" → should go to your payment provider checkout page
- [ ] Try valid key → app unlocks
- [ ] Access **Dashboard**, **Journal**, **Analytics** tabs
- [ ] Verify Admin tab shows audit logs

## Phase 7: Optional - Email Notifications ✅

- [ ] Enable 2FA on Gmail (if not already)
- [ ] Generate Gmail App Password (https://myaccount.google.com/apppasswords)
- [ ] Update secrets with SMTP config:
  ```toml
  SMTP_HOST = "smtp.gmail.com"
  SMTP_PORT = 587
  SMTP_USER = "your-gmail@gmail.com"
  SMTP_PASS = "xxxx xxxx xxxx xxxx"
  ```
- [ ] Test locally with `python test_email_notification.py`
- [ ] Submit a registration request in the app and confirm the email to `avogrowk@gmail.com`

## Phase 8: Go Live ✅

- [ ] Add real Stripe checkout URL to secrets (not test URL)
- [ ] Create first paying customer keys
- [ ] Share live URL: `https://<username>-forex-tracker-pro.streamlit.app`
- [ ] Monitor app logs in Streamlit Cloud dashboard
- [ ] Track registrations in Admin tab

---

## Quick URLs Reference

- **Live App**: https://<username>-forex-tracker-pro.streamlit.app
- **GitHub Repo**: https://github.com/<username>/forex-tracker-pro
- **Streamlit Dashboard**: https://share.streamlit.io
- **Stripe Dashboard**: https://dashboard.stripe.com
- **Gmail App Passwords**: https://myaccount.google.com/apppasswords

## Support Resources

- [Streamlit Cloud Docs](https://docs.streamlit.io/streamlit-cloud/get-started)
- [Stripe Checkout Docs](https://stripe.com/docs/payments/checkout)
- [Streamlit Secrets Docs](https://docs.streamlit.io/streamlit-cloud/get-started/deploy-an-app#deploy-your-app)

