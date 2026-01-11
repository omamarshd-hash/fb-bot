from flask import Flask, request
import requests
from groq import Groq
import os

app = Flask(__name__)

# ================================
# Tokens
# ================================
VERIFY_TOKEN = "my_verify_token_123"

# ⚠️ For now this is hardcoded (later move to env var)
PAGE_ACCESS_TOKEN = "EAAUA4t3PrrQBQVEhZASv2ZCwziqqVYnGhGeR4OkSH9t4gcczIQFbFj8y3ruBVnIInqDZABp7TZAdZAOxUzjTUWFASxH2igNUlo9QAnv6gXlIf18t292aWqHwZAW0pWPTY4GipiW7ZBxdjbzPkNg8FhjqYTktoszaWPHWwryzRT5k2MjyQ8h2sHta536JlCGy2ZCIemtZAFSNYWAZDZD"

# ✅ Groq API key from Render env vars
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY)

# ================================
# Groq AI function
# ================================
def generate_ai_reply(user_message):
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful, polite assistant replying to Facebook messages."
            },
            {
                "role": "user",
                "content": user_message
            }
        ],
        max_tokens=150,
        temperature=0.6
    )
    return response.choices[0].message.content.strip()

# ================================
# Facebook Send API helper
# ================================
def send_message(recipient_id, text):
    url = "https://graph.facebook.com/v18.0/me/messages"
    params = {"access_token": PAGE_ACCESS_TOKEN}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    requests.post(url, params=params, json=payload)

# ================================
# Webhook
# ================================
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    print("WEBHOOK HIT:", request.method)

    # ---- Verification ----
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("Webhook verified successfully")
            return challenge, 200

        return "Verification failed", 403

    # ---- Incoming messages ----
    if request.method == "POST":
        data = request.get_json()
        print("RAW PAYLOAD RECEIVED:")
        print(data)
        print("-" * 50)

        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):

                # Ignore echoes
                if messaging_event.get("message", {}).get("is_echo"):
                    continue

                sender_id = messaging_event.get("sender", {}).get("id")

                if "message" in messaging_event:
                    message_text = messaging_event["message"].get("text")

                    if message_text:
                        print("NEW MESSAGE RECEIVED")
                        print("From sender ID:", sender_id)
                        print("Message:", message_text)
                        print("-" * 50)

                        # ✅ AI reply with safety
                        try:
                            reply = generate_ai_reply(message_text)
                        except Exception as e:
                            print("GROQ ERROR:", str(e))
                            reply = "Sorry, I’m having trouble replying right now."

                        send_message(sender_id, reply)

        return "EVENT_RECEIVED", 200

# ================================
# Render Entry Point
# ================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
