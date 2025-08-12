from flask import Flask, render_template, request, jsonify, session
from datetime import datetime
from collections import defaultdict
from mood_detection import get_mood
from crisis_detection import check_crisis
from personalization import personalize_response
import os, sys, uuid, random

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
    "5-4-3-2-1 grounding": "This focuses your senses on the present moment to calm the mind. 🌱",
    "paced breathing": "Long, slow exhales relax your body and can ease anxiety. 🌬️",
    "thought reframing": "Helps you challenge unhelpful thoughts and see new perspectives. 🪞"
}

def build_system_prompt(last_user_msg: str | None, history: list) -> str:
    base = (
        "You are CareBear 🧸 — a warm, curious, and supportive mental health companion.\n"
        "STYLE: Chat naturally, like a caring friend. Use 2–3 short sentences. Sprinkle in soft emojis 🌸💛 sparingly.\n"
        "TONE: Empathetic, encouraging, a bit playful when appropriate.\n"
        "GOAL: Reflect feelings, answer questions directly, and offer one gentle suggestion or open question.\n"
        "DO: Adapt to the user's mood, respond with compassion, and give context if they ask 'why'.\n"
        "AVOID: Repetition, long lists, diagnosing, or formal jargon.\n"
        "If crisis language appears, respond with crisis safety guidance."
    )
    if history:
        convo = "\n".join([f"{h['role']}: {h['content']}" for h in history[-6:]])
        base += f"\nConversation so far:\n{convo}"
    elif last_user_msg:
        base += f"\nPrevious message from user: \"{last_user_msg}\"."
    return base

def offline_reply(user_message: str, mood: str, history: list) -> str:
    """Friendly fallback replies when GPT isn't available."""
    responses = {
        "happy": [
            "That’s amazing! 🌟 What’s making you smile today?",
            "Love that energy! 💛 Want to tell me more?",
            "Sounds like a bright moment — let’s celebrate it 🎉"
        ],
        "sad": [
            "I’m really sorry you’re feeling this way. 💜 What’s been weighing on you?",
            "That sounds tough. I’m here to listen, no rush. 🌱",
            "You’re not alone — I’m here for you. 💛"
        ],
        "anxious": [
            "I can hear the worry in your words. Want to slow down together? 🌬️",
            "That’s a lot to carry — we can break it into smaller steps.",
            "Your feelings are valid. Let’s find a calming thought. 🌸"
        ],
        "neutral": [
            "I’m here with you. What’s been on your mind lately?",
            "How’s your day going so far?",
            "Anything in particular you feel like chatting about?"
        ]
    }
    reply = random.choice(responses.get(mood, responses["neutral"]))
    if history and history[-1]["role"] == "user" and history[-1]["content"] != user_message:
        reply += " And about earlier — how are you feeling now?"
    return reply

def crisis_message() -> str:
    return (
        "I’m really concerned for your safety. 💜\n"
        "If you’re in danger or thinking of harming yourself, please reach out now:\n"
        "🇬🇧 Samaritans: 116 123 (free, 24/7)\n"
        "🌍 Crisis Text Line: Text HOME to 741741\n"
        "🆘 Emergency Services: 999 (UK)\n"
        "You matter so much — can you tell me if you’re safe right now?"
    )

def goal_nudge(this_sid: str) -> str:
    open_goals = [g for g in USER_GOALS[this_sid] if not g["done"]]
    return f"\n\nBy the way, last time you set: “{open_goals[0]['goal']}”. How’s that going? 🌟" if open_goals else ""

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
        "I’m an AI, not a clinician — but I care about your wellbeing. 💛 "
        "I can remember this conversation if you choose, and you can opt out anytime."
    )
    return jsonify({"ok": True, "disclosure": disclosure, "prefs": USER_PREFS[sid()]})

@app.route("/ask-why", methods=["POST"])
def ask_why():
    item = (request.json or {}).get("item", "").strip().lower()
    for k, v in SUGGESTION_EXPLAINS.items():
        if k.lower() in item:
            return jsonify({"why": v})
    return jsonify({"why": "I suggest things based on your mood and our recent chat to best support you."})

@app.route("/set-goal", methods=["POST"])
def set_goal():
    g = (request.json or {}).get("goal", "").strip()
    if not g:
        return jsonify({"ok": False, "error": "empty"})
    USER_GOALS[sid()].append({"goal": g, "done": False, "ts": datetime.utcnow().isoformat()})
    return jsonify({"ok": True, "msg": "Got it — I’ll check in on this later. 🌟"})

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
    return jsonify({"response": "Welcome back 💛 How are you feeling now?"})

@app.route("/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    user_message = (payload.get("message") or "").strip()
    if not user_message:
        return jsonify({"response": "Please type a message so I can reply 🙂", "mood": "neutral"})

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
                temperature=0.75,
                max_tokens=220
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
