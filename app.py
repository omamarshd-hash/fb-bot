from flask import Flask, request

app = Flask(__name__)

# This MUST match the Verify Token in Meta Dashboard
VERIFY_TOKEN = "my_verify_token_123"


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    # 🔹 DEBUG: confirm webhook is hit
    print("WEBHOOK HIT:", request.method)

    # ================================
    # Facebook Webhook Verification
    # ================================
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("Webhook verified successfully")
            return challenge, 200

        print("Webhook verification failed")
        return "Verification failed", 403

    # ================================
    # Incoming Facebook Messages
    # ================================
    if request.method == "POST":
        data = request.get_json()
        print("RAW PAYLOAD RECEIVED:")
        print(data)
        print("-" * 50)

        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                sender_id = messaging_event.get("sender", {}).get("id")

                # Only process real user messages
                if "message" in messaging_event:
                    message_text = messaging_event["message"].get("text")

                    if message_text:
                        print("NEW MESSAGE RECEIVED")
                        print("From sender ID:", sender_id)
                        print("Message:", message_text)
                        print("-" * 50)

        return "EVENT_RECEIVED", 200


# ================================
# Render / Production Entry Point
# ================================
if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
