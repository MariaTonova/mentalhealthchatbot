from flask import Flask, render_template, request, jsonify, session
from datetime import datetime
from collections import defaultdict
from mood_detection import get_mood
from crisis_detection import check_crisis
from personalization import personalize_response
import os, sys, uuid, random

# ----------------------- App & Optional OpenAI -----------------------
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

# ----------------------- In-memory demo stores -----------------------
USER_PREFS = {}
USER_NOTES = defaultdict(list)
USER_GOALS = defaultdict(list)
USER_HISTORY = defaultdict(list)  # store last 10 messages per session
CRISIS_MODE = set()

def sid():
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    return session["sid"]

# ----------------------- Explainability content ----------------------
SUGGESTION_EXPLAINS = {
    "5-4-3-2-1 grounding": "Grounding redirects attention to present-moment senses and can lower arousal (CBT skill).",
    "paced breathing": "Slower, longer exhales stimulate the parasympathetic system so the body can settle.",
    "thought reframing": "CBT reframing examines evidence for/against a thought and finds a more balanced view."
}

# ----------------------- GPT Prompt Builder --------------------------
def build_system_prompt(last_user_msg: str | None, history: list) -> str:
    base = (
        "You are CareBear, a warm, compassionate mental health support companion.\n"
        "STYLE: Speak like a friendly, supportive friend with gentle curiosity. Use short to medium sentences and natural flow.\n"
        "TONE: Empathetic, encouraging, and validating. Use warm emojis sparingly to convey care (🌸, 💛, 🙂).\n"
        "CONTENT: Always acknowledge what the user said, reflect their feelings, and either ask a relevant open question "
        "or offer a small, practical suggestion (e.g., grounding, breathing, gratitude reflection).\n"
        "AVOID: repeating the exact same phrases, clinical jargon, overly formal tone, or giving diagnoses.\n"
        "GOAL: Help the user feel heard, safe, and understood while encouraging small, positive steps.\n"
        "If the user expresses crisis language, respond with a short, direct crisis safety message first, then offer to listen if they feel safe.\n"
    )
    if history:
        convo = "\n".join([f"{h['role']}: {h['content']}" for h in history[-6:]])
        base += f"\nConversation so far:\n{convo}"
    elif last_user_msg:
        base += f"\nPrevious message from user: \"{last_user_msg}\"."
    return base

# ----------------------- Offline Fallback ----------------------------
def offline_reply(user_message: str, mood: str, history: list) -> str:
    mood_responses = {
        "sad": [
            "I hear how heavy things feel right now 💛. Want to share what’s been weighing on you?",
            "That sounds tough — I’m here to listen, no rush 💕. What’s been on your mind?",
            "It’s okay to feel this way. We can take it one step at a time together 🌸.",
            "I’m here with you. Sometimes just talking it out can help a little — want to try?"
        ],
        "happy": [
            "That’s wonderful to hear 🌟. What’s been making you feel this way?",
            "I’m glad you’re feeling good — let’s make the most of it 💫. Anything exciting ahead?",
            "That’s a bright spot worth holding onto 🌸. What’s one thing you’re grateful for today?",
            "It’s lovely hearing this from you! What’s been going well lately?"
        ],
        "anxious": [
            "It sounds like you’ve been feeling tense 😌. Want to try a calming exercise together?",
            "That’s a lot to carry — would you like a grounding tip that might help?",
            "I hear the worry in your words. Let’s take a deep breath first 🌿. What’s been on your mind?",
            "Anxiety can be overwhelming — but you don’t have to face it alone. What’s the biggest thought right now?"
        ],
        "neutral": [
            "I’m here with you. What’s been on your mind lately?",
            "How’s your day been going so far?",
            "What’s one thing that’s been important to you today?",
            "What’s been keeping you busy recently?"
        ]
    }
    grounding_tip = " Try 5-4-3-2-1 grounding: notice 5 things you see, 4 you touch, 3 you hear, 2 you smell, and 1 you taste."
    reply = random.choice(mood_responses.get(mood, mood_responses["neutral"]))
    if history and history[-1]["role"] == "user" and history[-1]["content"] != user_message:
        reply += " Is this connected to what you shared earlier?"
    return reply + grounding_tip

# ----------------------- Crisis Response -----------------------------
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
                temperature=0.6,
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
