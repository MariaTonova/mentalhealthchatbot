from flask import Flask, render_template, request, jsonify, session
from datetime import datetime
from collections import defaultdict
from mood_detection import get_mood
from crisis_detection import check_crisis
from personalization import personalize_response
import os, sys, uuid, random

# ----------------------- App Setup -----------------------
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

# ----------------------- Data Stores -----------------------
USER_PREFS = {}
USER_NOTES = defaultdict(list)
USER_GOALS = defaultdict(list)
USER_HISTORY = defaultdict(list)  # store last 10 messages per session
CRISIS_MODE = set()

def sid():
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    return session["sid"]

# ----------------------- Explainability -----------------------
SUGGESTION_EXPLAINS = {
    "5-4-3-2-1 grounding": "Grounding redirects attention to present-moment senses and can lower arousal (CBT skill).",
    "paced breathing": "Slower, longer exhales stimulate the parasympathetic system so the body can settle.",
    "thought reframing": "CBT reframing examines evidence for/against a thought and finds a more balanced view."
}

# ----------------------- Helpers -----------------------
def build_system_prompt(last_user_msg: str | None, history: list) -> str:
    base = (
        "You are CareBear, a warm and friendly chatbot that can both offer emotional support "
        "and engage in everyday conversation.\n"
        "STYLE: Respond in 2–4 short sentences, with a natural and conversational flow. "
        "Use a warm and empathetic tone when the user seems upset, but feel free to be light and casual "
        "when they are in a positive or neutral mood.\n"
        "GOAL: Balance listening, reflecting feelings, and keeping the conversation going naturally. "
        "Avoid sounding repetitive or scripted. Use emojis only if they fit naturally."
    )
    if history:
        convo = "\n".join([f"{h['role']}: {h['content']}" for h in history[-5:]])
        base += f"\nConversation so far:\n{convo}"
    elif last_user_msg:
        base += f"\nPrevious message from user: \"{last_user_msg}\"."
    return base

def offline_reply(user_message: str, mood: str, history: list, memory_enabled=False, notes=None) -> str:
    """Generate natural, mood-aware replies when GPT is unavailable."""
    mood_responses = {
        "sad": [
            "I hear you. That sounds tough. What’s been going on lately?",
            "It sounds like you’ve been having a rough time. Want to share more?",
            "That’s not easy. I’m here to listen — tell me a bit more."
        ],
        "happy": [
            "That’s great to hear! What’s been making you feel this way?",
            "Love hearing that! Any special moments recently?",
            "That’s wonderful! What’s been going well?"
        ],
        "anxious": [
            "I can sense some worry there. What’s been on your mind?",
            "Sounds like you’ve got a lot on your plate. Want to talk it through?",
            "That sounds stressful. What’s the biggest thing weighing on you?"
        ],
        "neutral": [
            "Gotcha. How’s your day been so far?",
            "I hear you. What’s been keeping you busy?",
            "Fair enough. What’s on your mind right now?"
        ]
    }

    reply = random.choice(mood_responses.get(mood, mood_responses["neutral"]))

    if memory_enabled and notes:
        if random.random() < 0.3:  # 30% chance to recall past topic
            past_note = random.choice(notes)
            reply += f" Earlier you mentioned '{past_note['point']}'. How’s that going?"

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

    mood = get_mood(user_message)

    # Crisis detection
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

    intro = personalize_response(user_message, mood, prefs.get("tone", "friendly"))

    if openai:
        try:
            gpt = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": build_system_prompt(last_user, USER_HISTORY[this_sid])},
                    *USER_HISTORY[this_sid]
                ],
                temperature=0.6,
                max_tokens=180
            )
            reply = gpt.choices[0].message["content"].strip()
            text = reply
            USER_HISTORY[this_sid].append({"role": "assistant", "content": text})
        except Exception as e:
            print("❌ OpenAI error:", e, file=sys.stderr, flush=True)
            text = offline_reply(user_message, mood, USER_HISTORY[this_sid],
                                 prefs.get("memory_opt_in"), USER_NOTES.get(this_sid, []))
            USER_HISTORY[this_sid].append({"role": "assistant", "content": text})
    else:
        text = offline_reply(user_message, mood, USER_HISTORY[this_sid],
                             prefs.get("memory_opt_in"), USER_NOTES.get(this_sid, []))
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
