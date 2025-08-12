from flask import Flask, render_template, request, jsonify, session
from datetime import datetime
from collections import defaultdict
from mood_detection import get_mood
from crisis_detection import check_crisis
from personalization import personalize_response
import os, sys, uuid, random, re

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

# Explanations for skills
SUGGESTION_EXPLAINS = {
    "5-4-3-2-1 grounding": "Grounding redirects attention to present-moment senses and can lower anxiety.",
    "paced breathing": "Slower, longer exhales calm the nervous system.",
    "thought reframing": "Helps find a more balanced way of looking at situations."
}

# Simple question/answer bank for offline mode
QA_RESPONSES = {
    "what is your name": "I’m CareBear 🧸, your friendly wellbeing buddy!",
    "who are you": "I’m CareBear — here to listen, support, and share gentle tips.",
    "how are you": "I’m always happy to chat and here to support you 💛",
    "what can you do": "I can listen, help you reflect on feelings, and share gentle coping strategies.",
    "are you a human": "Nope — I’m an AI, but I try to be warm and caring."
}

def detect_question(msg):
    """Check if the message looks like a question and match to QA bank."""
    text = msg.lower().strip("?!. ")
    if text in QA_RESPONSES:
        return QA_RESPONSES[text]
    if re.match(r"(what|why|how|who|where|when)\b", text):
        return "That’s a thoughtful question — tell me a bit more so I can help."
    return None

def build_system_prompt(last_user_msg: str | None, history: list) -> str:
    base = (
        "You are CareBear, a warm, trauma-informed mental health support bot.\n"
        "Respond like a caring friend, with gentle curiosity and a sprinkle of encouragement.\n"
        "Ask open questions, reflect feelings, and share ONE short tip if it fits.\n"
        "Avoid long lists or heavy clinical terms.\n"
        "If you notice crisis language, give a short crisis safety message."
    )
    if history:
        convo = "\n".join([f"{h['role']}: {h['content']}" for h in history[-5:]])
        base += f"\nConversation so far:\n{convo}"
    elif last_user_msg:
        base += f"\nPrevious message from user: \"{last_user_msg}\"."
    return base

def offline_reply(user_message: str, mood: str, history: list) -> str:
    q_response = detect_question(user_message)
    if q_response:
        return q_response

    mood_responses = {
        "sad": [
            "I hear how heavy this feels. You matter and you’re not alone 💛",
            "That sounds tough. I’m here with you.",
            "I can feel the weight in your words — let’s take it one step at a time."
        ],
        "happy": [
            "That’s lovely to hear! 🌟",
            "I’m so glad you’re feeling this way!",
            "That’s a bright moment worth holding onto."
        ],
        "anxious": [
            "I can sense the worry. Let’s pause and take a slow breath together.",
            "That sounds overwhelming — want to try grounding?",
            "Anxiety can feel intense. I’m here to help you find calm."
        ],
        "neutral": [
            "I’m here and listening — what’s been on your mind?",
            "How’s your day going so far?",
            "What’s been keeping your thoughts busy today?"
        ]
    }
    grounding_tip = " You could try 5-4-3-2-1 grounding: notice 5 things you see, 4 touch, 3 hear, 2 smell, 1 taste."
    reply = random.choice(mood_responses.get(mood, mood_responses["neutral"]))
    return reply + grounding_tip

def crisis_message() -> str:
    return (
        "I’m really sorry you’re feeling this way. Your safety matters so much. "
        "If you’re in danger, please call emergency services 📞\n"
        "🇬🇧 Samaritans: 116 123 (free, 24/7)\n"
        "🌍 Crisis Text Line: Text HOME to 741741\n"
        "🆘 Emergency Services: 999 (UK)\n"
        "If you feel safe, I’m here to listen."
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
        "I’m an AI, not a clinician. I offer supportive wellbeing guidance and crisis resources when needed."
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
    return jsonify({"ok": True, "msg": "Got it — I’ll check in next time."})

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
    return jsonify({"response": "Thanks for checking back in. How are you feeling now?"})

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

    if openai:
        try:
            gpt = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": build_system_prompt(last_user, USER_HISTORY[this_sid])},
                    *USER_HISTORY[this_sid]
                ],
                temperature=0.65,
                max_tokens=180
            )
            reply = gpt.choices[0].message["content"].strip()
            text = reply
            USER_HISTORY[this_sid].append({"role": "assistant", "content": text})
        except Exception as e:
            print("❌ OpenAI error:", e, file=sys.stderr, flush=True)
            text = offline_reply(user_message, mood, USER_HISTORY[this_sid])
            USER_HISTORY[this_sid].append({"role": "assistant", "content": text})
    else:
        text = offline_reply(user_message, mood, USER_HISTORY[this_sid])
        USER_HISTORY[this_sid].append({"role": "assistant", "content": text})

    if prefs.get("memory_opt_in"):
        text += goal_nudge(this_sid)

    session["last_user"] = user_message
    return jsonify({"response": text, "mood": mood})

@app.route("/status")
def status():
    return {"mode": "gpt" if openai else "offline"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
