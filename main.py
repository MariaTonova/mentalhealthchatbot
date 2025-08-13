from flask import Flask, render_template, request, jsonify, session
from datetime import datetime
from collections import defaultdict
from mood_detection import get_mood
from crisis_detection import check_crisis
from personalization import personalize_response
import os, sys, uuid, random

# Unified backend (OpenAI or DialoGPT)
from services.backends import get_backend

# Show what Render actually passed in (helps debug)
print("ENV USE_DIALOGPT =", os.getenv("USE_DIALOGPT"), flush=True)
print("ENV DIALOGPT_MODEL_ID =", os.getenv("DIALOGPT_MODEL_ID"), flush=True)

backend = get_backend()
BACKEND_NAME = getattr(backend, "NAME", "unknown")
print("ACTIVE BACKEND =", BACKEND_NAME, flush=True)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    print("✅ GPT mode: key detected", flush=True)
    import openai
    openai.api_key = OPENAI_API_KEY
else:
    print("💬 Offline mode: no OPENAI_API_KEY found", flush=True)
    openai = None

USER_PREFS = {}
USER_NOTES = defaultdict(list)
USER_GOALS = defaultdict(list)
USER_HISTORY = defaultdict(list)
CRISIS_MODE = set()

def sid():
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    return session["sid"]

SUGGESTION_EXPLAINS = {
    "5-4-3-2-1 grounding": "Grounding redirects attention to present-moment senses and can lower arousal (CBT skill).",
    "paced breathing": "Slower, longer exhales stimulate the parasympathetic system so the body can settle.",
    "thought reframing": "CBT reframing examines evidence for/against a thought and finds a more balanced view."
}

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

def build_system_prompt(last_user_msg: str | None, history: list) -> str:
    base = (
        "You are CareBear, a warm, friendly mental health companion who also enjoys casual conversation.\n"
        "STYLE: Respond in 2–3 short sentences, with warmth and empathy. Use light emojis for friendliness.\n"
        "If mood is anxious, begin with reassurance and grounding advice.\n"
        "AVOID: lists, over-clinical tone, or long lectures.\n"
        "For casual greetings, respond naturally as a human friend would."
    )
    if history:
        convo = "\n".join([f\"{h['role']}: {h['content']}\" for h in history[-5:]])
        base += f\"\\nConversation so far:\\n{convo}\"
    elif last_user_msg:
        base += f'\\nPrevious message from user: \"{last_user_msg}\".'
    return base

def offline_reply(user_message: str, mood: str, history: list) -> str:
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

def crisis_message() -> str:
    return (
        "I’m really sorry you’re feeling this way. Your safety matters so much. "
        "If you’re in danger, please call emergency services. 📞\n"
        "🇬🇧 Samaritans: 116 123 (free, 24/7)\n"
        "🌍 Crisis Text Line: Text HOME to 741741\n"
        "🆘 Emergency Services: 999 (UK)\n"
        "If you feel safe, we can talk more — but please make sure you’re supported right now."
    )

def goal_nudge(this_sid: str) -> str:
    open_goals = [g for g in USER_GOALS[this_sid] if not g["done"]]
    return f"\n\nLast time you set: “{open_goals[0]['goal']}”. Any tiny step today?" if open_goals else ""

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/start", methods=["POST"])
def start():
    data = request.json or {}
    tone = data.get("tone", "friendly")
    memory_opt_in = bool(data.get("memory_opt_in", False))
    USER_PREFS[sid()] = {"tone": tone, "memory_opt_in": memory_opt_in}
    disclosure = (
        "I’m an AI, not a clinician. I offer supportive wellbeing guidance and crisis resources when needed. "
        "You can opt out of memory anytime."
    )
    return jsonify({"ok": True, "disclosure": disclosure, "prefs": USER_PREFS[sid()]})

@app.route("/ask-why", methods=["POST"])
def ask_why():
    item = (request.json or {}).get("item", "").strip().lower()
    for k, v in SUGGESTION_EXPLAINS.items():
        if k.lower() in item:
            return jsonify({"why": v})
    return jsonify({"why": "I suggest skills from CBT/mindfulness that match your mood and recent messages."})

@app.route("/set-goal", methods=["POST"])
def set_goal():
    g = (request.json or {}).get("goal", "").strip()
    if not g:
        return jsonify({"ok": False, "error": "empty"})
    USER_GOALS[sid()].append({"goal": g, "done": False, "ts": datetime.utcnow().isoformat()})
    return jsonify({"ok": True, "msg": "Got it—I'll check in on this next time."})

@app.route("/session-summary", methods=["GET"])
def summary():
    notes = USER_NOTES.get(sid(), [])[-6:]
    moods = [n["mood"] for n in notes]
    trend = " → ".join(moods) if moods else "n/a"
    bullets = [f"- {n['point']}" for n in notes]
    return jsonify({"mood_trend": trend, "highlights": bullets})

@app.route("/resume", methods=["POST"])
def resume():
    CRISIS_MODE.discard(sid())
    return jsonify({"response": "Thanks for checking back in. How are you feeling right now?"})

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

    # Store history
    USER_HISTORY[this_sid].append({"role": "user", "content": user_message})
    USER_HISTORY[this_sid] = USER_HISTORY[this_sid][-10:]

    # Store notes if memory is on
    if prefs.get("memory_opt_in"):
        USER_NOTES[this_sid].append({
            "ts": datetime.utcnow().isoformat(),
            "mood": mood,
            "point": user_message[:160]
        })

    # Turn repair for partial inputs like "I am..."
    low = user_message.lower().strip()
    if low in {"i am", "i'm", "im"}:
        reply = "It can help to name it. Would you say you feel okay, low, stressed, or something else?"
        USER_HISTORY[this_sid].append({"role": "assistant", "content": reply})
        return jsonify({"response": reply, "mood": "neutral", "mode": BACKEND_NAME})

    # Small talk detection (prefix match)
    key = next((k for k in SMALL_TALK if low.startswith(k)), None)
    if key:
        reply = SMALL_TALK[key]
        USER_HISTORY[this_sid].append({"role": "assistant", "content": reply})
        return jsonify({"response": reply, "mood": mood, "mode": BACKEND_NAME})

    # Personalized intro
    intro = personalize_response(user_message, mood, prefs.get("tone", "friendly"))

    # Unified backend call with framing
    system_prompt = build_system_prompt(last_user, USER_HISTORY[this_sid]) + \
                    f"\nCurrent detected mood: {mood}. Keep replies to 2–3 short sentences and end with a gentle, open question."
    try:
        reply = backend.reply(USER_HISTORY[this_sid], user_message, system_prompt)
    except Exception as e:
        print("❌ Backend error:", e, file=sys.stderr, flush=True)
        reply = offline_reply(user_message, mood, USER_HISTORY[this_sid])

    reply = f"{intro}{reply}"
    if prefs.get("memory_opt_in"):
        reply += goal_nudge(this_sid)

    USER_HISTORY[this_sid].append({"role": "assistant", "content": reply})
    session["last_user"] = user_message

    return jsonify({"response": reply, "mood": mood, "mode": BACKEND_NAME})

@app.route("/status")
def status():
    # Report the actual, selected backend
    return {"mode": BACKEND_NAME}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

