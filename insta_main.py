from flask import Flask, request
import requests
import os
from dotenv import load_dotenv

# =========================================
# LOAD ENV VARIABLES
# =========================================

load_dotenv()

ACCESS_TOKEN = "EAAUA4t3PrrQBRmnwi6LPMNjpdqXjEZByCMjZBZCtREkvtngqEx2Fm69OZCJNp8Ud6NjullZBDETv1sJRm5TBOatwrJ6vZA3ZB6bV2XCoxaLCZBlcztIvybHBUzQIcjfv1cciUjxmiDFQxOCan7dgskZClIO8lOjLFBmdD5HDEb2ovFQJhWsm7ZCzxxzoeZAoe7vncMigiEWGmpkRXyM4LgDp5DIjYDTdzKE7dl4qfXGZBXmFpoLl160IoZBAgesHNtLFNXSNpzZBnKwUBfXcKswo7JXaOv"

INSTAGRAM_ACCOUNT_ID = "17841478520495248"

print("FULL TOKEN:", ACCESS_TOKEN)

# =========================================
# CREATE FLASK APP
# =========================================

app = Flask(__name__)

# =========================================
# HOME ROUTE
# =========================================

@app.route("/")
def home():
    return "Instagram Governor Bot Running"

# =========================================
# WEBHOOK VERIFICATION
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
# SEND INSTAGRAM REPLY
# =========================================

def send_instagram_reply(recipient_id, message_text):

    url = f"https://graph.facebook.com/v19.0/{INSTAGRAM_ACCOUNT_ID}/messages"

    headers = {
        "Content-Type": "application/json"
    }

    params = {
        "access_token": ACCESS_TOKEN
    }

    data = {
        "recipient": {
            "id": recipient_id
        },
        "messaging_type": "RESPONSE",
        "message": {
            "text": message_text
        }
    }

    response = requests.post(
        url,
        headers=headers,
        params=params,
        json=data
    )

    print("\n==============================")
    print("INSTAGRAM REPLY RESPONSE")
    print("==============================")
    print("STATUS:", response.status_code)
    print("BODY:", response.text)

# =========================================
# RECEIVE INSTAGRAM WEBHOOK
# =========================================

@app.route("/instagram/webhook", methods=["POST"])
def receive_instagram_message():

    data = request.get_json()

    print("\n==============================")
    print("INSTAGRAM WEBHOOK RECEIVED")
    print("==============================")
    print(data)

    try:

        if "entry" in data:

            for entry in data["entry"]:

                if "messaging" in entry:

                    for message_event in entry["messaging"]:

                        sender_id = message_event["sender"]["id"]

                        if "message" in message_event:

                            user_message = message_event["message"].get("text", "")

                            print("\n==============================")
                            print("NEW MESSAGE")
                            print("==============================")

                            print(f"Sender ID: {sender_id}")
                            print(f"Message: {user_message}")

                            # =========================================
                            # AUTO REPLY
                            # =========================================

                            send_instagram_reply(
                                sender_id,
                                f"You said: {user_message}"
                            )

    except Exception as e:

        print("\n==============================")
        print("ERROR")
        print("==============================")

        print(str(e))

    return "EVENT_RECEIVED", 200

# =========================================
# START SERVER
# =========================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)