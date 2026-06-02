# ✅ Streamlit Cloud Deployment Checklist

Use this checklist to ensure your Streamlit Cloud deployment is complete and secure.

## Pre-Deployment Setup

- [ ] **GitHub Account**: Have a GitHub account and this project is pushed to a repo
- [ ] **Streamlit Account**: Sign up at [streamlit.io/cloud](https://streamlit.io/cloud)
- [ ] **Repository Ready**: Main app file is `sustainable_forex_journal.py`
- [ ] **Dependencies**: All dependencies in `requirements.txt`
- [ ] **No secrets in repo**: `.streamlit/secrets.toml` is in `.gitignore`

## Generate Your Secrets

Before deploying, generate and prepare these values:

- [ ] **SUBSCRIPTION_KEY_HASH_SECRET**: Run `python -c "import secrets; print(secrets.token_hex(32))"`
- [ ] **ADMIN_KEY**: Run `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- [ ] **VALID_SUBSCRIPTION_KEYS**: Generate list of subscriber keys (comma-separated)
- [ ] **SUBSCRIPTION_PAYMENT_LINK**: Your Stripe/Whop checkout URL
- [ ] **WHOP_CHECKOUT_URL** (optional): Direct Whop checkout link
- [ ] **ADMIN_NOTIFICATION_EMAIL**: Your email address

## Prepare Payment Information

- [ ] One-time price: `$30` (or your amount)
- [ ] Bank account details ready:
  - [ ] Bank name: `Capitec Bank`
  - [ ] Account holder: `MR E AUGUSTYN`
  - [ ] Account number: `2520993738`
  - [ ] Branch code: `470010`
- [ ] WhatsApp payment proof URL configured

## Streamlit Cloud Deployment

- [ ] Open [share.streamlit.io](https://share.streamlit.io)
- [ ] Click **"New app"**
- [ ] Select your GitHub repo
- [ ] Select the correct branch (usually `main` or `master`)
- [ ] Set main file to: **`sustainable_forex_journal.py`**
- [ ] Click **"Deploy"**
- [ ] Wait 2-3 minutes for initial deployment

## Add Secrets to Streamlit Cloud

- [ ] Go to your app's page: `https://share.streamlit.io/@yourname/appname`
- [ ] Click **⚙️ Settings** (top right)
- [ ] Click **"Secrets"** in the left sidebar
- [ ] Click **"Edit secrets"**
- [ ] Paste entire secrets block (see **STREAMLIT_CLOUD_QUICKSTART.md**)
- [ ] Verify all values are correct:
  - [ ] `SUBSCRIPTION_PAYMENT_LINK` is correct Stripe/Whop URL
  - [ ] `VALID_SUBSCRIPTION_KEYS` has at least one key
  - [ ] `SUBSCRIPTION_KEY_HASH_SECRET` is a random string
  - [ ] `ADMIN_KEY` is a random string
  - [ ] `ADMIN_NOTIFICATION_EMAIL` is correct
- [ ] Click **"Save"** button
- [ ] App auto-redeploys (1-2 minutes)

## Verify Deployment

After secrets are added:

- [ ] **No errors in logs**: Click "View logs" (top right), check for errors
- [ ] **App loads successfully**: Visit app URL, should not show loading spinner for >30 sec
- [ ] **Subscription gate works**: Try to access without entering a valid key
  - [ ] Should show "Please enter a valid subscription key"
  - [ ] Should show payment/subscription links
- [ ] **Test subscription key**: Enter a key from `VALID_SUBSCRIPTION_KEYS`
  - [ ] Should unlock the app
  - [ ] Should show the main dashboard

## Security Checks

- [ ] **Secrets not in GitHub**: Verify `.streamlit/secrets.toml` is in `.gitignore`
- [ ] **No credentials in code**: Check no hardcoded API keys in `.py` files
- [ ] **Admin key is random**: Not "admin123" or obvious values
- [ ] **Hash secret is random**: Not a simple password
- [ ] **Secret format correct**: Only double quotes, no special chars outside quotes

## Testing Access Scenarios

Test these user scenarios to ensure subscription gate works:

- [ ] **No subscription key**: App shows subscribe/payment prompt
- [ ] **Invalid key format**: App rejects and shows error
- [ ] **Expired key** (if using CSV): App rejects key
- [ ] **Valid key**: App unlocks and shows dashboard
- [ ] **Admin access**: Can access admin panel with `ADMIN_KEY`

## Post-Deployment

- [ ] **Share app URL**: Give this to customers: `https://share.streamlit.io/@yourname/appname`
- [ ] **Subscription distribution**: Provide subscription keys to paying users
- [ ] **Monitor usage**: Check Streamlit Cloud app analytics
- [ ] **Update keys**: Add/revoke keys as needed (Settings → Secrets)
- [ ] **Email notifications**: Test that admin gets registration notifications
- [ ] **Payment links work**: Click payment links to verify they work

## Ongoing Maintenance

- [ ] **Weekly**: Check app logs for errors
- [ ] **Monthly**: Review subscription keys and active users
- [ ] **Quarterly**: Update dependencies in `requirements.txt`
- [ ] **As needed**: 
  - [ ] Add new subscription keys
  - [ ] Update payment URLs
  - [ ] Fix bugs or add features
  - [ ] Redeploy from GitHub (automatic)

## If Deployment Fails

Check these in order:

1. **App won't load at all**
   - [ ] Check "View logs" for Python errors
   - [ ] Verify `requirements.txt` has all dependencies
   - [ ] Verify main file is `sustainable_forex_journal.py`

2. **Secrets error**
   - [ ] Check TOML format (use `"` not `'`)
   - [ ] Verify no trailing commas
   - [ ] Check each line is valid TOML

3. **Subscription gate not working**
   - [ ] Verify `VALID_SUBSCRIPTION_KEYS` is set
   - [ ] Restart app: Settings → Advanced → Reboot app
   - [ ] Check secrets actually saved (refresh page)

4. **Payment links not showing**
   - [ ] Verify `SUBSCRIPTION_PAYMENT_LINK` or `WHOP_CHECKOUT_URL` is set
   - [ ] Test links are valid URLs
   - [ ] Check app logs for payment URL errors

## Rollback / Revert Changes

If something breaks:

- [ ] Go to your app on Streamlit Cloud
- [ ] Click **Settings** → **Deployment** (if available)
- [ ] Revert to last working version
- [ ] Fix the issue and redeploy from GitHub

Or manually:

- [ ] Fix the code locally
- [ ] Commit and push to GitHub
- [ ] Streamlit Cloud auto-redeploys

## Documentation References

- [STREAMLIT_CLOUD_QUICKSTART.md](STREAMLIT_CLOUD_QUICKSTART.md) - 5-minute setup
- [STREAMLIT_CLOUD_SETUP.md](STREAMLIT_CLOUD_SETUP.md) - Detailed guide
- [GENERATE_SECRETS.md](GENERATE_SECRETS.md) - How to generate secrets
- [DEPLOYMENT_STREAMLIT_CLOUD.md](DEPLOYMENT_STREAMLIT_CLOUD.md) - Original deployment docs

---

**You're all set!** ✨ Your Streamlit Cloud app is now live and secure.

**App URL**: `https://share.streamlit.io/@yourname/appname`

**Need help?** Check the logs or review the documentation files listed above.
