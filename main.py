from flask import Flask, render_template, request, jsonify, session
from datetime import datetime
from collections import defaultdict
from mood_detection import get_mood
from crisis_detection import check_crisis
from personalization import personalize_response
import os, sys, uuid, random

# ----------------------- App -----------------------
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

# Optional OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    print("✅ GPT mode: key detected", flush=True)
    import openai
    openai.api_key = OPENAI_API_KEY
else:
    print("💬 Offline mode: no OPENAI_API_KEY found", flush=True)
    openai = None

# ----------------------- Stores -----------------------
USER_PREFS = {}
USER_NOTES = defaultdict(list)
USER_GOALS = defaultdict(list)
USER_HISTORY = defaultdict(list)
CRISIS_MODE = set()

# ----------------------- Local Fact Bank -----------------------
FACTS = {
    "cbt": "CBT stands for Cognitive Behavioural Therapy — a structured, goal-oriented form of therapy that helps people identify and change unhelpful thinking patterns.",
    "mindfulness": "Mindfulness means paying attention to the present moment, on purpose and without judgment. It can reduce stress and improve emotional regulation.",
    "carebear": "CareBear is your warm, supportive mental health companion, designed to listen and respond with empathy.",
    "leap year": "A leap year occurs every 4 years. The next one is in 2028.",
}

QUESTION_KEYWORDS = ["what is", "who is", "when is", "where is", "tell me about", "define", "meaning of"]

# ----------------------- Utilities -----------------------
def sid():
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    return session["sid"]

def build_system_prompt(last_user_msg, history):
    base = (
        "You are CareBear, a warm, trauma-informed mental health support bot.\n"
        "STYLE: Respond in 2–3 short sentences, using simple, kind words. Use soft emojis sparingly 🙂.\n"
        "If the user asks a factual question, give a short, accurate answer but keep a compassionate tone.\n"
        "DO: Reflect feelings, normalize them, and offer ONE gentle next step or ask an open question.\n"
        "AVOID: repetition, long lists, diagnoses, or clinical jargon.\n"
        "If crisis language appears, respond with a short crisis safety message encouraging immediate help."
    )
    if history:
        convo = "\n".join([f"{h['role']}: {h['content']}" for h in history[-5:]])
        base += f"\nConversation so far:\n{convo}"
    elif last_user_msg:
        base += f"\nPrevious message from user: \"{last_user_msg}\"."
    return base

def offline_reply(user_message, mood, history):
    mood_responses = {
        "sad": [
            "I hear how heavy things feel right now 💛",
            "That sounds really hard. I’m here with you.",
            "It’s okay to feel this way. Let’s take it slow."
        ],
        "happy": [
            "That’s wonderful to hear! 🌟",
            "I’m so glad you’re feeling this way!",
            "That’s a bright moment worth holding onto."
        ],
        "anxious": [
            "I can sense the worry in your words. Let’s slow things down together.",
            "That sounds overwhelming. Want to try a grounding exercise?",
            "Anxiety can feel intense. I’m here to help you find calm."
        ],
        "neutral": [
            "I’m here with you. Tell me more about what’s been on your mind.",
            "How’s your day been going so far?",
            "What’s been occupying your thoughts lately?"
        ]
    }
    reply = random.choice(mood_responses.get(mood, mood_responses["neutral"]))
    return reply

def crisis_message():
    return (
        "I’m really sorry you’re feeling this way. Your safety matters so much. "
        "If you’re in danger, please call emergency services. 📞\n"
        "🇬🇧 Samaritans: 116 123 (free, 24/7)\n"
        "🌍 Crisis Text Line: Text HOME to 741741\n"
        "🆘 Emergency Services: 999 (UK)"
    )

def is_question(message):
    msg = message.lower().strip()
    return any(q in msg for q in QUESTION_KEYWORDS)

def answer_question(message):
    for key, value in FACTS.items():
        if key in message.lower():
            return value + " I hope that helps 💛"
    return "Hmm, I’m not completely sure, but I can help you look it up if you’d like 💡"

# ----------------------- Routes -----------------------
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
        "I’m an AI, not a clinician. I offer supportive wellbeing guidance and crisis resources when needed."
    )
    return jsonify({"ok": True, "disclosure": disclosure, "prefs": USER_PREFS[sid()]})

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

    # Store conversation
    USER_HISTORY[this_sid].append({"role": "user", "content": user_message})
    USER_HISTORY[this_sid] = USER_HISTORY[this_sid][-10:]

    # Handle factual Q&A
    if is_question(user_message):
        if openai:
            try:
                gpt = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": build_system_prompt(last_user, USER_HISTORY[this_sid])},
                        *USER_HISTORY[this_sid]
                    ],
                    temperature=0.6,
                    max_tokens=150
                )
                reply = gpt.choices[0].message["content"].strip()
            except:
                reply = answer_question(user_message)
        else:
            reply = answer_question(user_message)

        USER_HISTORY[this_sid].append({"role": "assistant", "content": reply})
        return jsonify({"response": reply, "mood": mood})

    # Otherwise normal supportive chat
    if openai:
        try:
            gpt = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": build_system_prompt(last_user, USER_HISTORY[this_sid])},
                    *USER_HISTORY[this_sid]
                ],
                temperature=0.7,
                max_tokens=180
            )
            reply = gpt.choices[0].message["content"].strip()
        except Exception as e:
            print("❌ OpenAI error:", e, file=sys.stderr, flush=True)
            reply = offline_reply(user_message, mood, USER_HISTORY[this_sid])
    else:
        reply = offline_reply(user_message, mood, USER_HISTORY[this_sid])

    USER_HISTORY[this_sid].append({"role": "assistant", "content": reply})
    session["last_user"] = user_message
    return jsonify({"response": reply, "mood": mood})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
