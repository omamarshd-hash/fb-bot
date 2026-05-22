from flask import Flask, request

app = Flask(__name__)


# =========================================
# HOME ROUTE
# =========================================

@app.route("/")
def home():
    return "Instagram Governor Backend Running"


# =========================================
# INSTAGRAM WEBHOOK VERIFICATION
# =========================================

@app.route("/instagram/webhook", methods=["GET"])
def verify_instagram_webhook():

    VERIFY_TOKEN = "12345"

    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200

    return "Verification failed", 403


# =========================================
# INSTAGRAM MESSAGE RECEIVER
# =========================================

@app.route("/instagram/webhook", methods=["POST"])
def receive_instagram_message():

    data = request.get_json()

    print("INSTAGRAM WEBHOOK RECEIVED:")
    print(data)

    return "EVENT_RECEIVED", 200


# =========================================
# START SERVER
# =========================================

if __name__ == "__main__":
    app.run(debug=True)