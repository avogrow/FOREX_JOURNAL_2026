# STREAMLIT CLOUD - READY TO DEPLOY
# Generated: June 2, 2026
# Your app is ready! Follow these steps to deploy.

## STEP 1: Create Streamlit Cloud Account
Visit: https://streamlit.io/cloud
- Sign up (you can use your GitHub account)
- This takes 2 minutes

## STEP 2: Deploy Your App
1. Go to: https://share.streamlit.io
2. Click "New app"
3. Select your GitHub repo
4. Select the branch (main or master)
5. Set main file to: sustainable_forex_journal.py
6. Click "Deploy"
7. Wait 2-3 minutes for initial deployment

Your app URL will be: https://share.streamlit.io/@yourname/appname

## STEP 3: Add Your Secrets (CRITICAL!)
1. Go to your app page (from Step 2)
2. Click Settings (gear icon, top right)
3. Click "Secrets" in the sidebar
4. Click "Edit secrets"
5. Delete the default secrets
6. Copy the ENTIRE block below (everything from [client] to the last line)
7. Paste into the secrets editor
8. Click "Save"

## ========== COPY FROM HERE ==========

[client]
showErrorDetails = false

# ========================================
# PAYMENT & SUBSCRIPTION
# ========================================
WHOP_CHECKOUT_URL = "https://whop.com/sustainable-journal"
SUBSCRIPTION_PAYMENT_LINK = "https://whop.com/sustainable-journal"

# ========================================
# KEY MANAGEMENT
# ========================================
SUBSCRIPTION_KEY_HASH_SECRET = "87b5b302992d6a0c4d01e86da0dfdda63d7a1e8f89fb97bf28237e3b5f1f2a7c"

VALID_SUBSCRIPTION_KEYS = "PRO-DF543F27BF86,PRO-980EF74CD0E2,PRO-DF6D962E0CF8,PRO-0A2DD604EED2,PRO-6E2496271F40"

# ========================================
# ADMIN ACCESS
# ========================================
ADMIN_KEY = "cxeyAFTLFKRp7nBIlvLCRNadV35DW50gxK_bAIrEANY"
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

## ========== COPY TO HERE ==========

## STEP 4: Verify Deployment
After clicking "Save":
- App will auto-redeploy (1-2 minutes)
- Click "View logs" to check for errors
- Visit your app URL
- Should see login/subscription page (no errors)
- Try entering a test key: PRO-DF543F27BF86
- Should unlock the app

## STEP 5: Test Everything
[] App loads without errors
[] Subscription gate appears (asks for key when not logged in)
[] Test key works: PRO-DF543F27BF86
[] Payment link appears in sidebar
[] Admin dashboard accessible with key: cxeyAFTLFKRp7nBIlvLCRNadV35DW50gxK_bAIrEANY

## Your Test Subscription Keys
1. PRO-DF543F27BF86
2. PRO-980EF74CD0E2
3. PRO-DF6D962E0CF8
4. PRO-0A2DD604EED2
5. PRO-6E2496271F40

Use any of these to test your app. Give them to initial users/beta testers.

## Your Security Keys (KEEP SAFE!)
- ADMIN_KEY: cxeyAFTLFKRp7nBIlvLCRNadV35DW50gxK_bAIrEANY
- HASH_SECRET: 87b5b302992d6a0c4d01e86da0dfdda63d7a1e8f89fb97bf28237e3b5f1f2a7c

Never share these keys!

## Next: Share with Users
Once verified, share your app URL: https://share.streamlit.io/@yourname/appname

Users can:
- Sign up with email
- Pay for subscription (via Whop)
- Receive subscription key
- Unlock app with their key

## Troubleshooting

Problem: "Please enter a valid subscription key" won't go away
Solution: Check you pasted VALID_SUBSCRIPTION_KEYS correctly (no extra spaces)

Problem: Secrets error when saving
Solution: Make sure you're using double quotes: "value" not 'value'

Problem: App won't load
Solution: Check View logs for Python errors

Problem: Subscription links don't appear
Solution: Verify WHOP_CHECKOUT_URL is set (it's: https://whop.com/sustainable-journal)
