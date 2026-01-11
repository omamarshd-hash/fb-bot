from flask import Flask, request
import requests
from groq import Groq
import os
from datetime import datetime

app = Flask(__name__)

# ================================
# Tokens
# ================================
VERIFY_TOKEN = "my_verify_token_123"

# ⚠️ Hardcoded for now (move to env vars later)
PAGE_ACCESS_TOKEN = "EAAUA4t3PrrQBQVEhZASv2ZCwziqqVYnGhGeR4OkSH9t4gcczIQFbFj8y3ruBVnIInqDZABp7TZAdZAOxUzjTUWFASxH2igNUlo9QAnv6gXlIf18t292aWqHwZAW0pWPTY4GipiW7ZBxdjbzPkNg8FhjqYTktoszaWPHWwryzRT5k2MjyQ8h2sHta536JlCGy2ZCIemtZAFSNYWAZDZD"

# ================================
# Groq Setup
# ================================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY)

# ================================
# Conversation Memory
# ================================
conversation_memory = {}
MAX_MEMORY_MESSAGES = 10  # total (user + assistant)

def update_memory(user_id, role, content):
    if user_id not in conversation_memory:
        conversation_memory[user_id] = []

    conversation_memory[user_id].append({
        "role": role,
        "content": content
    })

    conversation_memory[user_id] = conversation_memory[user_id][-MAX_MEMORY_MESSAGES:]

# ================================
# Spam / Automation Filter
# ================================
def is_real_user_message(messaging_event):
    message = messaging_event.get("message")
    if not message:
        return False

    if message.get("is_echo"):
        return False

    text = message.get("text")
    if not text:
        return False

    text = text.strip()
    if len(text) < 2:
        return False

    return True

# ================================
# Groq AI Function (with memory)
# ================================
def generate_ai_reply(user_id, user_message):
    history = conversation_memory.get(user_id, [])

    messages = [
        {
            "role": "system",
            "content": "You are a helpful, polite assistant replying to Facebook messages."
        }
    ]

    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    response = groq_client.chat.completions.create(
        model="llama3-8b-8192",
        messages=messages,
        max_tokens=150,
        temperature=0.6
    )

    return response.choices[0].message.content.strip()

# ================================
# Facebook Send API
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
# Chat Logger (Notepad file)
# ================================
def log_conversation(user_id, user_message, bot_reply):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_entry = (
        f"[{timestamp}]\n"
        f"User ID: {user_id}\n"
        f"User: {user_message}\n"
        f"Bot: {bot_reply}\n"
        f"{'-'*40}\n"
    )

    with open("messenger_chat_log.txt", "a", encoding="utf-8") as f:
        f.write(log_entry)

# ================================
# Webhook
# ================================
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    print("WEBHOOK HIT:", request.method)

    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200

        return "Verification failed", 403

    if request.method == "POST":
        data = request.get_json()

        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):

                if not is_real_user_message(messaging_event):
                    continue

                sender_id = messaging_event["sender"]["id"]
                message_text = messaging_event["message"]["text"]

                # 🧠 store user message
                update_memory(sender_id, "user", message_text)

                try:
                    reply = generate_ai_reply(sender_id, message_text)
                except Exception as e:
                    print("GROQ ERROR:", str(e))
                    reply = "Sorry, I’m having trouble replying right now."

                send_message(sender_id, reply)

                # 🧠 store bot reply
                update_memory(sender_id, "assistant", reply)

                # 📝 log to notepad file
                log_conversation(sender_id, message_text, reply)

        return "EVENT_RECEIVED", 200

# ================================
# Render Entry Point
# ================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
