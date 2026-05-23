from flask import Flask, request
import requests
import os
from dotenv import load_dotenv

# =========================================
# LOAD ENV VARIABLES
# =========================================

load_dotenv()

ACCESS_TOKEN = os.getenv("INSTAGRAM_PAGE_ACCESS_TOKEN")
PAGE_ID = os.getenv("PAGE_ID")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
GOVERNOR_URL = os.getenv("GOVERNOR_URL")

# =========================================
# WHITELISTED SENDER IDs
# Add both Instagram and Facebook tester IDs
# =========================================

WHITELISTED_IDS = [
    "2381442649051546",   # Instagram test account
    # Facebook Messenger tester IDs go here
    # "FACEBOOK_SENDER_ID",
]

# =========================================
# DEBUG PRINTS
# =========================================

print("\n======================")
print("ENV VARIABLES LOADED")
print("======================")
print("ACCESS TOKEN:", ACCESS_TOKEN[:25] if ACCESS_TOKEN else "MISSING")
print("PAGE ID:", PAGE_ID if PAGE_ID else "MISSING")
print("INSTAGRAM ACCOUNT ID:", INSTAGRAM_ACCOUNT_ID)
print("VERIFY TOKEN:", VERIFY_TOKEN)
print("GOVERNOR URL:", GOVERNOR_URL)
print("WHITELISTED IDs:", WHITELISTED_IDS)

# =========================================
# FLASK APP
# =========================================

app = Flask(__name__)

# =========================================
# HOME ROUTE
# =========================================

@app.route("/")
def home():
    return "Meta AI Bot Running — Instagram + Facebook Messenger"


# =========================================
# WAKE GOVERNOR
# =========================================

def wake_governor():
    try:
        base_url = GOVERNOR_URL.replace("/process_message", "")
        requests.get(base_url, timeout=30)
        print("\n✅ Governor is awake")
    except Exception as e:
        print("\n⚠️ Governor wake ping failed:", str(e))


# =========================================
# ASK GOVERNOR AI
# =========================================

def ask_governor(platform, user_id, message):
    payload = {
        "platform": platform,
        "user_id": user_id,
        "message": message
    }

    try:
        response = requests.post(
            GOVERNOR_URL,
            json=payload,
            timeout=60
        )

        print("\n======================")
        print("🧠 GOVERNOR RESPONSE")
        print("======================")
        print("STATUS:", response.status_code)
        print("RAW:", response.text)

        data = response.json()
        return data.get("reply", "Temporary AI issue.")

    except Exception as e:
        print("\n❌ GOVERNOR ERROR ❌")
        print(str(e))
        return "Sorry, something went wrong."


# =========================================
# SEND INSTAGRAM REPLY
# =========================================

def send_instagram_reply(recipient_id, message_text):
    url = f"https://graph.facebook.com/v25.0/{PAGE_ID}/messages"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text},
        "messaging_type": "RESPONSE"
    }

    print("\n======================")
    print("📤 SENDING INSTAGRAM MESSAGE")
    print("======================")
    print("RECIPIENT:", recipient_id)
    print("MESSAGE:", message_text)

    response = requests.post(url, headers=headers, json=data)
    print("STATUS:", response.status_code)
    print("BODY:", response.text)


# =========================================
# SEND FACEBOOK MESSENGER REPLY
# =========================================

def send_facebook_reply(recipient_id, message_text):
    url = "https://graph.facebook.com/v25.0/me/messages"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text},
        "messaging_type": "RESPONSE"
    }

    print("\n======================")
    print("📤 SENDING FACEBOOK MESSAGE")
    print("======================")
    print("RECIPIENT:", recipient_id)
    print("MESSAGE:", message_text)

    response = requests.post(url, headers=headers, json=data)
    print("STATUS:", response.status_code)
    print("BODY:", response.text)


# =========================================
# PROCESS MESSAGING EVENT
# Shared logic for both platforms
# =========================================

def process_messaging_event(platform, event):
    sender_id = event["sender"]["id"]

    if "message" not in event:
        return

    # Ignore echo messages (bot's own messages)
    if event["message"].get("is_echo"):
        return

    user_message = event["message"].get("text", "")

    if not user_message or len(user_message.strip()) < 2:
        return

    print("\n==============================")
    print(f"NEW {platform.upper()} MESSAGE")
    print("==============================")
    print("Sender ID:", sender_id)
    print("Message:", user_message)

    # Whitelist check
    if sender_id not in WHITELISTED_IDS:
        print(f"\n⛔ IGNORED — sender not whitelisted: {sender_id}")
        return

    print("\n✅ Sender is whitelisted — processing...")

    # Wake Governor
    wake_governor()

    # Ask Governor AI
    ai_reply = ask_governor(platform, sender_id, user_message)

    print("\n🤖 AI REPLY:")
    print(ai_reply)

    # Send reply to correct platform
    if platform == "instagram":
        send_instagram_reply(sender_id, ai_reply)
    elif platform == "facebook":
        send_facebook_reply(sender_id, ai_reply)


# =========================================
# UNIFIED META WEBHOOK — VERIFICATION
# Handles both Instagram and Facebook
# =========================================

@app.route("/meta/webhook", methods=["GET"])
def verify_meta_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("\n✅ META WEBHOOK VERIFIED")
        return challenge, 200

    print("\n❌ WEBHOOK VERIFICATION FAILED")
    return "Verification failed", 403


@app.route("/meta/webhook", methods=["POST"])
def meta_webhook():
    data = request.get_json()

    print("\n======================")
    print("📩 META WEBHOOK RECEIVED")
    print("======================")
    print(data)

    try:
        object_type = data.get("object", "")

        if object_type == "instagram":
            for entry in data.get("entry", []):
                for event in entry.get("messaging", []):
                    process_messaging_event("instagram", event)

        elif object_type == "page":
            for entry in data.get("entry", []):
                for event in entry.get("messaging", []):
                    process_messaging_event("facebook", event)

        else:
            print(f"⚠️ Unknown object type: {object_type}")

    except Exception as e:
        print("\n❌ META WEBHOOK ERROR ❌")
        print(str(e))

    return "EVENT_RECEIVED", 200


# =========================================
# LEGACY INSTAGRAM WEBHOOK ROUTE
# Keeps existing Meta webhook config working
# =========================================

@app.route("/instagram/webhook", methods=["GET"])
def verify_instagram_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("\n✅ INSTAGRAM WEBHOOK VERIFIED")
        return challenge, 200

    return "Verification failed", 403


@app.route("/instagram/webhook", methods=["POST"])
def instagram_webhook():
    data = request.get_json()

    print("\n======================")
    print("📩 INSTAGRAM WEBHOOK (legacy route)")
    print("======================")

    try:
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                process_messaging_event("instagram", event)
    except Exception as e:
        print("\n❌ INSTAGRAM ERROR ❌")
        print(str(e))

    return "EVENT_RECEIVED", 200


# =========================================
# LEGACY FACEBOOK WEBHOOK ROUTE
# Keeps existing Facebook webhook config working
# =========================================

@app.route("/webhook", methods=["GET"])
def verify_facebook_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("\n✅ FACEBOOK WEBHOOK VERIFIED")
        return challenge, 200

    return "Verification failed", 403


@app.route("/webhook", methods=["POST"])
def facebook_webhook():
    data = request.get_json()

    print("\n======================")
    print("📩 FACEBOOK WEBHOOK (legacy route)")
    print("======================")
    print(data)

    try:
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                process_messaging_event("facebook", event)
    except Exception as e:
        print("\n❌ FACEBOOK ERROR ❌")
        print(str(e))

    return "EVENT_RECEIVED", 200


# =========================================
# START SERVER
# =========================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
