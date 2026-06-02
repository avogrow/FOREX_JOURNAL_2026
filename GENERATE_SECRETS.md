# Generate Required Secrets

Run these Python commands to generate secure random secrets for your deployment:

## 1. Generate Hash Secret (for subscription key security)
```python
import secrets
hash_secret = secrets.token_hex(32)
print(f"SUBSCRIPTION_KEY_HASH_SECRET = \"{hash_secret}\"")
```

Example output:
```
SUBSCRIPTION_KEY_HASH_SECRET = "a3f8e9b2c1d7f4e6a5b9c2d8e1f7a4b5c9d2e1f7a4b5c9d2e1f7a4b5c9d2"
```

## 2. Generate Admin Key (for admin dashboard access)
```python
import secrets
admin_key = secrets.token_urlsafe(32)
print(f"ADMIN_KEY = \"{admin_key}\"")
```

Example output:
```
ADMIN_KEY = "8Zyh_N-4f5K2pL9qR3sT6uV1wX2yZ3aBcDeFgH"
```

## 3. Generate Subscription Keys (for paid users)
```python
import secrets
keys = [f"PRO-{secrets.token_hex(6).upper()}" for _ in range(5)]
print("VALID_SUBSCRIPTION_KEYS = \"" + ",".join(keys) + "\"")
```

Example output:
```
VALID_SUBSCRIPTION_KEYS = "PRO-A3F8E9B2C1,PRO-D7F4E6A5B9,PRO-C2D8E1F7A4,PRO-B5C9D2E1F7,PRO-A4B5C9D2E1"
```

## Secrets Checklist

After generating all secrets, ensure you have:

- [ ] `WHOP_CHECKOUT_URL` or `SUBSCRIPTION_PAYMENT_LINK` (payment URL)
- [ ] `SUBSCRIPTION_KEY_HASH_SECRET` (generated)
- [ ] `VALID_SUBSCRIPTION_KEYS` (generated list of test/user keys)
- [ ] `ADMIN_KEY` (generated)
- [ ] `ADMIN_NOTIFICATION_EMAIL` (your email)
- [ ] Bank details (for manual payments)

## How to Use These Secrets

### For Local Development
1. Create `.streamlit/secrets.toml`
2. Copy the generated secrets into it
3. Run `streamlit run sustainable_forex_journal.py`

### For Streamlit Cloud
1. Go to your app's Settings → Secrets
2. Paste all secrets in TOML format
3. Click Save
4. App will auto-redeploy with new secrets

## Security Notes

- **Never** commit `.streamlit/secrets.toml` to GitHub
- **Never** share your secret keys in public repos
- Rotate keys periodically
- Use environment variables for all sensitive data
- Add `.streamlit/secrets.toml` to `.gitignore`
