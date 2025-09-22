from flask import Flask, render_template, request, jsonify, session
from datetime import datetime
from collections import defaultdict
from mood_detection import get_mood
from crisis_detection import check_crisis, get_crisis_message
from personalization import personalize_response
from cbt_responses import get_cbt_response
from services.backends import get_backend
import os, uuid, json

# ---------------- Flask App ----------------
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

# Initialize backend once at startup
print("🚀 Initializing backend...", flush=True)
backend = get_backend()
print("✅ Backend ready", flush=True)

# ---------------- In-memory stores ----------------
USER_PREFS = {}
USER_NOTES = defaultdict(list)
USER_GOALS = defaultdict(list)
USER_HISTORY = defaultdict(list)
CRISIS_MODE = set()

LOG_FILE = os.getenv("CHAT_LOG_FILE", "chat_logs.jsonl")

# ---------------- Helpers ----------------
def sid():
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    return session["sid"]

def build_system_prompt(last_user_msg, history):
    base = (
        "You are CareBear, a warm, friendly mental health companion who also enjoys casual conversation.\n"
        "STYLE: Respond in 2–3 short sentences, with warmth and empathy. Use light emojis for friendliness.\n"
        "If mood is anxious, begin with reassurance and grounding advice.\n"
        "AVOID: lists, over-clinical tone, or long lectures.\n"
        "For casual greetings, respond naturally as a human friend would."
    )
    if history:
        convo = "\n".join([f"{h['role']}: {h['content']}" for h in history[-5:]])
        base += f"\nConversation so far:\n{convo}"
    elif last_user_msg:
        base += f'\nPrevious message from user: "{last_user_msg}".'
    return base

def goal_nudge(this_sid):
    open_goals = [g for g in USER_GOALS[this_sid] if not g["done"]]
    if open_goals:
        return f"\n\nLast time you set: “{open_goals[0]['goal']}”. Any tiny step today?"
    return ""

def log_interaction(this_sid, user_message, bot_reply, mood, crisis=False, backend_used="unknown"):
    log_entry = {
        "sid": this_sid,
        "timestamp": datetime.utcnow().isoformat(),
        "user_message": user_message,
        "bot_reply": bot_reply,
        "mood": mood,
        "crisis": crisis,
        "backend": backend_used
    }
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"⚠️ Logging error: {e}", flush=True)

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

    try:
        # Crisis detection
        if check_crisis(user_message):
            CRISIS_MODE.add(this_sid)
            bot_reply = get_crisis_message()
            log_interaction(this_sid, user_message, bot_reply, mood, crisis=True, backend_used="crisis")
            return jsonify({"response": bot_reply, "mood": mood, "crisis": True})
        if this_sid in CRISIS_MODE:
            bot_reply = get_crisis_message()
            log_interaction(this_sid, user_message, bot_reply, mood, crisis=True, backend_used="crisis")
            return jsonify({"response": bot_reply, "mood": mood, "crisis": True})

        # Personalize system prompt (tone + mood context)
        system_prompt = build_system_prompt(last_user, USER_HISTORY[this_sid])
        intro = personalize_response(user_message, mood, prefs.get("tone", "friendly"))

        # Backend reply
        reply = None
        backend_used = "unknown"
        try:
            reply = backend.reply(USER_HISTORY[this_sid], user_message, system_prompt)
            backend_used = backend.__class__.__name__.lower()
        except Exception as e:
            print(f"❌ Backend error: {e}", flush=True)

        # Fallback to CBT
        if not reply:
            last_bot_message = USER_HISTORY[this_sid][-1]['content'] if USER_HISTORY[this_sid] else ""
            cbt_response = get_cbt_response(mood, user_message, last_bot_message, sid=this_sid)
            reply = f"{cbt_response['message']} {cbt_response.get('follow_up', '') or ''}".strip()
            backend_used = "cbt"

        # Add personalization + goals
        reply = f"{intro}{reply}"
        if prefs.get("memory_opt_in"):
            reply += goal_nudge(this_sid)

        # Save history
        USER_HISTORY[this_sid].append({"role": "assistant", "content": reply})
        session["last_user"] = user_message

        log_interaction(this_sid, user_message, reply, mood, crisis=False, backend_used=backend_used)
        return jsonify({"response": reply, "mood": mood})
    except Exception as e:
        print(f"⚠️ Error in chat handling: {e}", flush=True)
        return jsonify({"response": "Sorry, something went wrong. Can we try again?"})

@app.route("/notes", methods=["GET", "POST"])
def notes():
    this_sid = sid()
    if request.method == "POST":
        note = (request.get_json(silent=True) or {}).get("note", "").strip()
        if note:
            USER_NOTES[this_sid].append({"note": note, "time": datetime.utcnow().isoformat()})
    return jsonify({"notes": USER_NOTES[this_sid]})

@app.route("/goals", methods=["GET", "POST"])
def goals():
    this_sid = sid()
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        goal_text = data.get("goal", "").strip()
        if goal_text:
            goal_entry = {"goal": goal_text, "time": datetime.utcnow().isoformat(), "done": False}
            USER_GOALS[this_sid].append(goal_entry)
    return jsonify({"goals": USER_GOALS[this_sid]})

@app.route("/preferences", methods=["GET", "POST"])
def preferences():
    this_sid = sid()
    if request.method == "POST":
        prefs = request.get_json(silent=True) or {}
        USER_PREFS[this_sid] = {
            "tone": prefs.get("tone", "friendly"),
            "memory_opt_in": bool(prefs.get("memory_opt_in", False))
        }
    return jsonify(USER_PREFS.get(this_sid, {}))

