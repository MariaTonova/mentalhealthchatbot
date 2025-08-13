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
USE_OPENAI = bool(OPENAI_API_KEY) and not USE_HF  # GPT only if HF not available

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

# ---------------- Load Dataset Few-Shots ----------------
def load_mental_health_examples():
    """
    Loads a small few-shot set from the mental_health_counseling_conversations dataset (UK-adapted tone).
    """
    try:
        url = "https://huggingface.co/datasets/Amod/mental_health_counseling_conversations/resolve/main/data/train.json"
        data = requests.get(url, timeout=10).json()
        # Pick first 5 examples and adapt to UK style
        examples = []
        for ex in data[:5]:
            user_text = ex.get("Context", "").strip()
            bot_text = ex.get("Response", "").strip()
            if user_text and bot_text:
                examples.append(f"User: {user_text}\nAssistant: {bot_text}")
        print(f"✅ Loaded {len(examples)} few-shot examples from dataset.")
        return "\n".join(examples)
    except Exception as e:
        print("⚠ Could not load dataset examples:", e)
        return ""

FEW_SHOT_EXAMPLES = load_mental_health_examples()

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

def build_system_prompt(last_user_msg, history):
    base = (
        "You are CareBear, a warm, friendly UK-based mental health companion.\n"
        "Provide empathetic, supportive, non-clinical advice and UK resources.\n"
        "STYLE: Respond in 2–3 short sentences, with warmth and empathy.\n"
        "Avoid over-clinical tone. Use light emojis for friendliness.\n"
        "Here are example conversations:\n"
        f"{FEW_SHOT_EXAMPLES}\n"
    )
    if history:
        convo = "\n".join([f"{h['role']}: {h['content']}" for h in history[-5:]])
        base += f"\nConversation so far:\n{convo}"
    elif last_user_msg:
        base += f'\nPrevious message from user: "{last_user_msg}".'
    return base

def offline_reply(user_message, mood, history):
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
        reply += " Try 5-4-3-2-1 grounding: name 5 things you see, 4 you touch, 3 you hear, 2 you smell, 1 you taste. What’s the first thing you see?"
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
    try:
        url = "https://api-inference.huggingface.co/models/google/flan-t5-large"
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        payload = {"inputs": f"{system_prompt}\nUser: {user_message}\nAssistant:"}
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        if response.status_code == 200:
            return response.json()[0]["generated_text"].strip()
    except Exception as e:
        print("❌ HuggingFace error:", e, file=sys.stderr)
    return None

def call_openai(history, user_message, system_prompt):
    try:
        gpt = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                *history,
                {"role": "user", "content": user_message}
            ],
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

    mood = get_mood(user_message)

    if check_crisis(user_message):
        CRISIS_MODE.add(this_sid)
        return jsonify({"response": crisis_message(), "mood": mood, "crisis": True})
    if this_sid in CRISIS_MODE:
        return jsonify({"response": crisis_message(), "mood": mood, "crisis": True})

    USER_HISTORY[this_sid].append({"role": "user", "content": user_message})
    USER_HISTORY[this_sid] = USER_HISTORY[this_sid][-10:]

    if prefs.get("memory_opt_in"):
        USER_NOTES[this_sid].append({
            "ts": datetime.utcnow().isoformat(),
            "mood": mood,
            "point": user_message[:160]
        })

    intro = personalize_response(user_message, mood, prefs.get("tone", "friendly"))
    system_prompt = build_system_prompt(last_user, USER_HISTORY[this_sid]) + \
                    f"\nCurrent detected mood: {mood}. Keep replies to 2–3 short sentences and end with a gentle, open question."

    reply = None
    if USE_HF:
        reply = call_huggingface(USER_HISTORY[this_sid], user_message, system_prompt)
    elif USE_OPENAI:
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
