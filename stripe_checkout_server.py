import os
from flask import Flask, redirect, request, jsonify
import stripe

app = Flask(__name__)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

DOMAIN_URL = os.getenv("DOMAIN_URL", "http://localhost:4242")
PRICE_ID = os.getenv("STRIPE_PRICE_ID")


@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    if not stripe.api_key:
        return jsonify({"error": "STRIPE_SECRET_KEY is not configured."}), 500

    if not PRICE_ID:
        return jsonify({"error": "STRIPE_PRICE_ID is not configured."}), 500

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[
                {
                    "price": PRICE_ID,
                    "quantity": 1,
                }
            ],
            success_url=f"{DOMAIN_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{DOMAIN_URL}/cancel",
        )
        return jsonify({"url": session.url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/success")
def success():
    return "Subscription created. Use the checkout session details to provision subscriber access."


@app.route("/cancel")
def cancel():
    return "Subscription canceled. Try again if you want to subscribe."


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4242, debug=True)
