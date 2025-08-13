from flask import Flask, render_template, request, jsonify, session
from datetime import datetime
from collections import defaultdict
from mood_detection import get_mood
from crisis_detection import check_crisis
from personalization import personalize_response
import os, sys, uuid, random, requests

# ---------------- Backend Preference ----------------
HF_API_KEY = os.getenv("HF_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

USE_HF = bool(HF_API_KEY)
USE_OPENAI = bool(OPENAI_API_KEY)  # GPT fallback if HF fails

if USE_HF:
    print("🤗 HF mode: Hugging Face API key detected", flush=True)
elif USE_OPENAI:
    import openai
    openai.api_key = OPENAI_API_KEY
    print("✅ GPT mode: OpenAI API key detected", flush=True)
else:
    print("💬 Offline mode: no API key found", flush=True)

# ---------------- Flask App ----------------
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

USER_PREFS = {}
USER_NOTES = defaultdict(list)
USER_GOALS = defaultdict(list)
USER_HISTORY = defaultdict(list)
CRISIS_MODE = set()

# ---------------- Small Talk ----------------
SMALL_TALK = {
    "hi": "Hey there! 👋 How’s your day going so far?",
    "hello": "Hello! 😊 What’s been on your mind today?",
    "hey": "Hey! 🌟 How are you feeling right now?",
    "thanks": "You’re so welcome! 💛",
    "thank you": "Always happy to help 💛",
    "how are you": "I’m doing well, thanks for asking! How about you?",
    "good morning": "Good morning! ☀️ How’s your start to the day?",
    "good evening": "Good evening! 🌙 How has your day been?",
    "what's up": "Not much — just happy to chat with you! 💬"
}

# ---------------- Helpers ----------------
def sid():
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    return session["sid"]

SUGGESTION_EXPLAINS = {
    "5-4-3-2-1 grounding": "Grounding redirects attention to present-moment senses and can lower arousal (CBT skill).",
    "paced breathing": "Slower, longer exhales stimulate the parasympathetic system so the body can settle.",
    "thought reframing": "CBT reframing examines evidence for/against a thought and finds a more balanced view."
}

def build_system_prompt(last_user_msg, history, mood):
    """Builds mental health conversation system prompt with mood-specific guidance."""
    base_prompt = (
        "You are CareBear, a warm, friendly mental health companion.\n"
        "STYLE: Respond in 2–3 short sentences, with warmth and empathy. Use gentle emojis 💛.\n"
        "Avoid lists or clinical jargon. Encourage sharing, validate feelings.\n"
        "If user expresses crisis thoughts, offer crisis helplines and urge seeking help immediately.\n"
    )

    # Mood-specific tailoring
    if mood == "anxious":
        base_prompt += "If mood is anxious, start with reassurance and suggest grounding techniques like 5-4-3-2-1.\n"
    elif mood == "sad":
        base_prompt += "If mood is sad, acknowledge pain and gently invite them to share what's been weighing on them.\n"
    elif mood == "happy":
        base_prompt += "If mood is happy, share in their joy and ask what’s been bringing them happiness.\n"
    elif mood == "neutral":
        base_prompt += "If mood is neutral, invite gentle self-reflection and open-ended sharing.\n"

    if history:
        convo = "\n".join([f"{h['role']}: {h['content']}" for h in history[-5:]])
        base_prompt += f"\nConversation so far:\n{convo}"
    elif last_user_msg:
        base_prompt += f'\nPrevious message from user: "{last_user_msg}".'

    return base_prompt

def offline_reply(user_message, mood, history):
    """Local fallback replies if no API is available."""
    mood_responses = {
        "sad": [
            "I hear how heavy things feel right now. You’re not alone in this 💛",
            "That sounds really hard. I’m here with you.",
            "I can feel the weight in your words. Let’s take this one step at a time."
        ],
        "happy": [
            "That’s wonderful to hear! 🌟",
            "I’m so glad you’re feeling this way!",
            "That’s a bright moment worth holding onto."
        ],
        "anxious": [
            "It’s okay to feel this way — let’s take a slow deep breath together 🌿",
            "Your feelings are valid. We can slow things down right now.",
            "I hear your worry. Let’s ground ourselves together."
        ],
        "neutral": [
            "I’m here with you. Tell me more about what’s been on your mind.",
            "How’s your day been going so far?",
            "What’s been occupying your thoughts lately?"
        ]
    }
    reply = random.choice(mood_responses.get(mood, mood_responses["neutral"]))
    if mood == "anxious":
        reply += " Try 5-4-3-2-1 grounding: name 5 things you see, 4 you touch, 3 you hear, 2 you smell, 1 you taste."
    else:
        reply += " What feels most important to talk about right now?"
    return reply

def crisis_message():
    return (
        "I’m really sorry you’re feeling this way. Your safety matters so much. "
        "If you’re in danger, please call emergency services. 📞\n"
        "🇬🇧 Samaritans: 116 123 (free, 24/7)\n"
        "🌍 Crisis Text Line: Text HOME to 741741\n"
        "🆘 Emergency Services: 999 (UK)\n"
        "If you feel safe, we can talk more — but please make sure you’re supported right now."
    )

def goal_nudge(this_sid):
    open_goals = [g for g in USER_GOALS[this_sid] if not g["done"]]
    return f"\n\nLast time you set: “{open_goals[0]['goal']}”. Any tiny step today?" if open_goals else ""

# ---------------- API Calls ----------------
def call_huggingface(history, user_message, system_prompt):
    """Hugging Face inference with mental-health tuned prompt."""
    try:
        url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        payload = {
            "inputs": f"{system_prompt}\nUser: {user_message}\nAssistant:",
            "parameters": {"max_new_tokens": 200, "temperature": 0.7}
        }
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and "generated_text" in data[0]:
                return data[0]["generated_text"].strip()
    except Exception as e:
        print("❌ HuggingFace error:", e, file=sys.stderr)
    return None

def call_openai(history, user_message, system_prompt):
    try:
        gpt = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": system_prompt}, *history, {"role": "user", "content": user_message}],
            temperature=0.6,
            max_tokens=180,
        )
        return gpt.choices[0].message["content"].strip()
    except Exception as e:
        print("❌ OpenAI error:", e, file=sys.stderr)
    return None

# ---------------- Routes ----------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    user_message = (payload.get("message") or "").strip()
    if not user_message:
        return jsonify({"response": "Please type a message to start.", "mood": "neutral"})

    this_sid = sid()
    prefs = USER_PREFS.get(this_sid, {"tone": "friendly", "memory_opt_in": False})
    last_user = session.get("last_user")

    # Mood + crisis detection
    mood = get_mood(user_message)
    if check_crisis(user_message):
        CRISIS_MODE.add(this_sid)
        return jsonify({"response": crisis_message(), "mood": mood, "crisis": True})
    if this_sid in CRISIS_MODE:
        return jsonify({"response": crisis_message(), "mood": mood, "crisis": True})

    # Save message history
    USER_HISTORY[this_sid].append({"role": "user", "content": user_message})
    USER_HISTORY[this_sid] = USER_HISTORY[this_sid][-10:]

    if prefs.get("memory_opt_in"):
        USER_NOTES[this_sid].append({"ts": datetime.utcnow().isoformat(), "mood": mood, "point": user_message[:160]})

    # Small talk
    low = user_message.lower().strip()
    if low in SMALL_TALK:
        reply = SMALL_TALK[low]
        USER_HISTORY[this_sid].append({"role": "assistant", "content": reply})
        return jsonify({"response": reply, "mood": mood})

    # Build personalized intro & system prompt
    intro = personalize_response(user_message, mood, prefs.get("tone", "friendly"))
    system_prompt = build_system_prompt(last_user, USER_HISTORY[this_sid], mood)

    # Backend priority: HF → GPT → Offline
    reply = None
    if USE_HF:
        reply = call_huggingface(USER_HISTORY[this_sid], user_message, system_prompt)
    if not reply and USE_OPENAI:
        reply = call_openai(USER_HISTORY[this_sid], user_message, system_prompt)
    if not reply:
        reply = offline_reply(user_message, mood, USER_HISTORY[this_sid])

    reply = f"{intro}{reply}"
    if prefs.get("memory_opt_in"):
        reply += goal_nudge(this_sid)

    USER_HISTORY[this_sid].append({"role": "assistant", "content": reply})
    session["last_user"] = user_message

    return jsonify({"response": reply, "mood": mood})

@app.route("/status")
def status():
    if USE_HF:
        return {"mode": "huggingface"}
    elif USE_OPENAI:
        return {"mode": "gpt"}
    return {"mode": "offline"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

