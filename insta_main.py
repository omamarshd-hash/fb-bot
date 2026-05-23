from flask import Flask, request
import requests
import os
from dotenv import load_dotenv

# =========================================
# LOAD ENV VARIABLES
# =========================================

load_dotenv()

ACCESS_TOKEN = os.getenv(
    "INSTAGRAM_PAGE_ACCESS_TOKEN"
)

PAGE_ID = os.getenv(
    "PAGE_ID"
)

INSTAGRAM_ACCOUNT_ID = os.getenv(
    "INSTAGRAM_ACCOUNT_ID"
)

VERIFY_TOKEN = os.getenv(
    "VERIFY_TOKEN"
)

GOVERNOR_URL = os.getenv(
    "GOVERNOR_URL"
)

# =========================================
# DEBUG PRINTS
# =========================================

print("\n======================")
print("ENV VARIABLES LOADED")
print("======================")

print(
    "ACCESS TOKEN:",
    ACCESS_TOKEN[:25] if ACCESS_TOKEN else "MISSING"
)

print(
    "PAGE ID:",
    PAGE_ID if PAGE_ID else "MISSING"
)

print(
    "INSTAGRAM ACCOUNT ID:",
    INSTAGRAM_ACCOUNT_ID
)

print(
    "VERIFY TOKEN:",
    VERIFY_TOKEN
)

print(
    "GOVERNOR URL:",
    GOVERNOR_URL
)

# =========================================
# CREATE FLASK APP
# =========================================

app = Flask(__name__)

# =========================================
# HOME ROUTE
# =========================================

@app.route("/")
def home():

    return "Instagram AI Bot Running"


# =========================================
# WEBHOOK VERIFICATION
# =========================================

@app.route("/instagram/webhook", methods=["GET"])
def verify_instagram_webhook():

    mode = request.args.get("hub.mode")

    token = request.args.get("hub.verify_token")

    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:

        print("\n✅ INSTAGRAM WEBHOOK VERIFIED")

        return challenge, 200

    print("\n❌ WEBHOOK VERIFICATION FAILED")

    return "Verification failed", 403


# =========================================
# ASK GOVERNOR AI
# =========================================

def ask_governor(user_id, message):

    payload = {

        "platform": "instagram",

        "user_id": user_id,

        "message": message
    }

    try:

        response = requests.post(

            GOVERNOR_URL,

            json=payload,

            timeout=30
        )

        data = response.json()

        print("\n======================")
        print("🧠 GOVERNOR RESPONSE")
        print("======================")

        print(data)

        return data.get(
            "reply",
            "Temporary AI issue."
        )

    except Exception as e:

        print("\n❌ GOVERNOR ERROR ❌")

        print(str(e))

        return (
            "Sorry, something went wrong."
        )


# =========================================
# SEND INSTAGRAM REPLY
# =========================================

def send_instagram_reply(

    recipient_id,
    message_text
):

    # ✅ FIX: Use PAGE_ID instead of INSTAGRAM_ACCOUNT_ID
    url = (
        f"https://graph.facebook.com/v25.0/"
        f"{PAGE_ID}/messages"
    )

    # ✅ FIX: Use Authorization Bearer header instead of param
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    data = {

        "recipient": {
            "id": recipient_id
        },

        "message": {
            "text": message_text
        },

        # ✅ FIX: Added messaging_type required by Meta
        "messaging_type": "RESPONSE"
    }

    print("\n======================")
    print("📤 SENDING INSTAGRAM MESSAGE")
    print("======================")

    print("URL:", url)

    print("RECIPIENT:", recipient_id)

    print("MESSAGE:", message_text)

    response = requests.post(

        url,

        headers=headers,

        json=data
    )

    print("\n======================")
    print("📤 INSTAGRAM SEND RESPONSE")
    print("======================")

    print("STATUS:", response.status_code)

    print("BODY:", response.text)


# =========================================
# INSTAGRAM WEBHOOK EVENTS
# =========================================

@app.route("/instagram/webhook", methods=["POST"])
def instagram_webhook():

    data = request.get_json()

    print("\n======================")
    print("📩 INSTAGRAM WEBHOOK RECEIVED")
    print("======================")

    print(data)

    try:

        if "entry" in data:

            for entry in data["entry"]:

                if "messaging" in entry:

                    for event in entry["messaging"]:

                        sender_id = event[
                            "sender"
                        ]["id"]

                        if "message" in event:

                            user_message = (
                                event["message"]
                                .get("text", "")
                            )

                            print("\n==============================")
                            print("NEW MESSAGE")
                            print("==============================")

                            print(
                                "Sender ID:",
                                sender_id
                            )

                            print(
                                "Message:",
                                user_message
                            )

                            # ======================
                            # ASK GOVERNOR AI
                            # ======================

                            ai_reply = ask_governor(

                                sender_id,

                                user_message
                            )

                            print("\n🤖 AI REPLY:")

                            print(ai_reply)

                            # ======================
                            # SEND REPLY
                            # ======================

                            send_instagram_reply(

                                sender_id,

                                ai_reply
                            )

    except Exception as e:

        print("\n❌ INSTAGRAM ERROR ❌")

        print(str(e))

    return "EVENT_RECEIVED", 200


# =========================================
# START SERVER
# =========================================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=10000
    )