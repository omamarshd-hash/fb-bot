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
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "my_verify_token_123")
GOVERNOR_URL = os.getenv("GOVERNOR_URL", "https://governor-ai-1odr.onrender.com/process_message")
GOVERNOR_BASE = GOVERNOR_URL.replace("/process_message", "")

# Default whitelist (fallback for your existing setup)
DEFAULT_WHITELIST = [
    "2381442649051546",
    "33227605106886622",
]

print("\n======================")
print("ENV VARIABLES LOADED")
print("======================")
print("ACCESS TOKEN:", ACCESS_TOKEN[:25] if ACCESS_TOKEN else "MISSING")
print("PAGE ID:", PAGE_ID)
print("GOVERNOR:", GOVERNOR_URL)

app = Flask(__name__)

# =========================================
# MULTI-TENANT HELPERS
# =========================================

def get_ceo_config(page_id):
    """Get CEO config from Governor by page_id"""
    try:
        res = requests.get(
            f"{GOVERNOR_BASE}/platforms/by_page/{page_id}",
            timeout=10
        )
        if res.status_code == 200:
            return res.json()
        return None
    except:
        return None


def get_test_accounts(ceo_id):
    """Get whitelisted test accounts for a CEO"""
    try:
        res = requests.get(
            f"{GOVERNOR_BASE}/test_accounts/by_ceo/{ceo_id}",
            timeout=10
        )
        if res.status_code == 200:
            return [t["account_id"] for t in res.json().get("test_accounts", [])]
        return []
    except:
        return []


def is_allowed(sender_id, ceo_config):
    """Check if sender is allowed to message this CEO's bot"""
    if not ceo_config:
        # Fall back to default whitelist (your existing setup)
        return sender_id in DEFAULT_WHITELIST

    # If CEO is meta verified — everyone is allowed
    if ceo_config.get("meta_verified"):
        return True

    # Otherwise check CEO's test accounts
    test_accounts = get_test_accounts(ceo_config.get("ceo_id"))
    return sender_id in test_accounts


# =========================================
# WAKE GOVERNOR
# =========================================

def wake_governor():
    try:
        requests.get(GOVERNOR_BASE, timeout=30)
        print("✅ Governor is awake")
    except Exception as e:
        print("⚠️ Governor wake failed:", str(e))


# =========================================
# ASK GOVERNOR AI
# =========================================

def ask_governor(platform, sender_id, message, page_id=None, ceo_id=None):
    payload = {
        "platform": platform,
        "user_id": sender_id,
        "message": message,
        "page_id": page_id or PAGE_ID,
    }
    if ceo_id:
        payload["ceo_id"] = ceo_id

    try:
        response = requests.post(GOVERNOR_URL, json=payload, timeout=60)
        print("GOVERNOR STATUS:", response.status_code)
        return response.json().get("reply", "Temporary AI issue.")
    except Exception as e:
        print("❌ GOVERNOR ERROR:", str(e))
        return "Sorry, something went wrong."


# =========================================
# SEND REPLY HELPERS
# =========================================

def get_token_for_page(page_id, ceo_config):
    """Get access token — use CEO's stored token or fall back to env var"""
    if ceo_config and ceo_config.get("access_token"):
        return ceo_config["access_token"]
    return ACCESS_TOKEN


def send_instagram_reply(recipient_id, message_text, page_id=None, token=None):
    pid = page_id or PAGE_ID
    tok = token or ACCESS_TOKEN
    url = f"https://graph.facebook.com/v25.0/{pid}/messages"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {tok}"}
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text},
        "messaging_type": "RESPONSE"
    }
    print(f"📤 INSTAGRAM → {recipient_id}: {message_text[:50]}")
    response = requests.post(url, headers=headers, json=data)
    print("STATUS:", response.status_code, response.text[:100])


def send_facebook_reply(recipient_id, message_text, token=None):
    tok = token or ACCESS_TOKEN
    url = "https://graph.facebook.com/v25.0/me/messages"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {tok}"}
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text},
        "messaging_type": "RESPONSE"
    }
    print(f"📤 FACEBOOK → {recipient_id}: {message_text[:50]}")
    response = requests.post(url, headers=headers, json=data)
    print("STATUS:", response.status_code, response.text[:100])


# =========================================
# PROCESS MESSAGING EVENT
# =========================================

def process_messaging_event(platform, event, entry_page_id=None):
    sender_id = event["sender"]["id"]

    if "message" not in event:
        return
    if event["message"].get("is_echo"):
        return

    user_message = event["message"].get("text", "")
    if not user_message or len(user_message.strip()) < 2:
        return

    print(f"\n{'='*30}")
    print(f"NEW {platform.upper()} MESSAGE")
    print(f"{'='*30}")
    print("Sender:", sender_id)
    print("Page:", entry_page_id)
    print("Message:", user_message)

    # Look up CEO for this page
    ceo_config = get_ceo_config(entry_page_id) if entry_page_id else None
    if not ceo_config:
        print("ℹ️ No CEO found for page — using default config")

    # Check if sender is allowed
    if not is_allowed(sender_id, ceo_config):
        print(f"⛔ IGNORED — sender not whitelisted: {sender_id}")
        return

    print("✅ Sender allowed — processing...")
    wake_governor()

    # Get token for this CEO
    token = get_token_for_page(entry_page_id, ceo_config)
    ceo_id = ceo_config.get("ceo_id") if ceo_config else None

    # Ask Governor AI
    ai_reply = ask_governor(platform, sender_id, user_message, entry_page_id, ceo_id)
    print("🤖 AI REPLY:", ai_reply[:100])

    # Send reply
    if platform == "instagram":
        send_instagram_reply(sender_id, ai_reply, entry_page_id, token)
    elif platform == "facebook":
        send_facebook_reply(sender_id, ai_reply, token)


# =========================================
# WEBHOOK ROUTES
# =========================================

@app.route("/")
def home():
    return "Meta AI Bot Running — Multi-tenant Instagram + Facebook"


@app.route("/meta/webhook", methods=["GET"])
@app.route("/instagram/webhook", methods=["GET"])
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ WEBHOOK VERIFIED")
        return challenge, 200
    print("❌ WEBHOOK VERIFICATION FAILED")
    return "Verification failed", 403


@app.route("/meta/webhook", methods=["POST"])
def meta_webhook():
    data = request.get_json()
    print("\n📩 META WEBHOOK RECEIVED")
    try:
        object_type = data.get("object", "")
        if object_type == "instagram":
            for entry in data.get("entry", []):
                entry_page_id = entry.get("id")
                for event in entry.get("messaging", []):
                    process_messaging_event("instagram", event, entry_page_id)
        elif object_type == "page":
            for entry in data.get("entry", []):
                entry_page_id = entry.get("id")
                for event in entry.get("messaging", []):
                    process_messaging_event("facebook", event, entry_page_id)
    except Exception as e:
        print("❌ META WEBHOOK ERROR:", str(e))
    return "EVENT_RECEIVED", 200


@app.route("/instagram/webhook", methods=["POST"])
def instagram_webhook():
    data = request.get_json()
    print("\n📩 INSTAGRAM WEBHOOK")
    try:
        for entry in data.get("entry", []):
            entry_page_id = entry.get("id")
            for event in entry.get("messaging", []):
                process_messaging_event("instagram", event, entry_page_id)
    except Exception as e:
        print("❌ INSTAGRAM ERROR:", str(e))
    return "EVENT_RECEIVED", 200


@app.route("/webhook", methods=["POST"])
def facebook_webhook():
    data = request.get_json()
    print("\n📩 FACEBOOK WEBHOOK")
    try:
        for entry in data.get("entry", []):
            entry_page_id = entry.get("id")
            for event in entry.get("messaging", []):
                process_messaging_event("facebook", event, entry_page_id)
    except Exception as e:
        print("❌ FACEBOOK ERROR:", str(e))
    return "EVENT_RECEIVED", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
