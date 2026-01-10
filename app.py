from flask import Flask, request

app = Flask(__name__)

# This must match what you entered in Meta dashboard
VERIFY_TOKEN = "my_verify_token_123"


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    # 🔴 THIS LINE IS IMPORTANT FOR DEBUGGING
    print("WEBHOOK HIT:", request.method)

    # Facebook verification request
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200

        return "Verification failed", 403

    # Message delivery (later we’ll process Facebook messages here)
    if request.method == "POST":
        data = request.get_json()
        print("RAW DATA RECEIVED:")
        print(data)
        print("-" * 40)

        return "EVENT_RECEIVED", 200


if __name__ == "__main__":
    app.run(port=5000)
