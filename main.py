from flask import Flask, render_template, request, jsonify, session
from datetime import datetime
from collections import defaultdict
from mood_detection import get_mood
from crisis_detection import check_crisis, get_crisis_message
from personalization import personalize_response
from cbt_responses import get_cbt_response
from services.backends import get_backend
import os, uuid, json
import random  # NEW: for varied greeting

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

# Initialize backend once
backend = get_backend()

# In-memory session stores
USER_PREFS = {}
USER_NOTES = defaultdict(list)
USER_GOALS = defaultdict(list)
USER_HISTORY = defaultdict(list)  # list of {role: "user"|"assistant", content: str}
CRISIS_MODE = set()

LOG_FILE = os.getenv("CHAT_LOG_FILE", "chat_logs.jsonl")


# ---------------- Helpers ----------------
def sid():
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    return session["sid"]


def build_system_prompt(last_user_msg, history):
    base = (
        "You are CareBear, a warm, friendly mental health companion.\n"
        "STYLE: Reply in 2 to 3 short sentences with warmth and empathy. Light emojis are ok.\n"
        "If mood is anxious, begin with reassurance and one simple technique.\n"
        "Avoid clinical claims or diagnosis. Keep it supportive and conversational.\n"
    )
    if history:
        convo = "\n".join([f"{h['role']}: {h['content']}" for h in history[-5:]])
        base += f"\nConversation so far:\n{convo}"
    elif last_user_msg:
        base += f'\nPrevious message from user: "{last_user_msg}".'
    return base


def goal_nudge(this_sid):
    open_goals = [g for g in USER_GOALS[this_sid] if not g.get("done")]
    if open_goals:
        return f'\n\nLast time you set: "{open_goals[0]["goal"]}". Any tiny step today?'
    return ""


def log_interaction(this_sid, user_message, bot_reply, mood, crisis=False, backend_used="unknown"):
    entry = {
        "sid": this_sid,
        "ts": datetime.utcnow().isoformat(),
        "user_message": user_message,
        "bot_reply": bot_reply,
        "mood": mood,
        "crisis": crisis,
        "backend": backend_used,
    }
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"Log error: {e}", flush=True)


def _first_sentence(s: str) -> str:
    s = (s or "").strip()
    for sep in [".", "!", "?"]:
        if sep in s:
            return s.split(sep, 1)[0].strip()
    return s


def _last_bot_message(history):
    for h in reversed(history):
        if h["role"] == "assistant":
            return h["content"]
    return ""


def combine_with_intro(intro: str, reply: str, last_bot_message: str = "") -> str:
    """
    Prevent duplicated openings and back-to-back identical intros.
    """
    intro_clean = (intro or "").strip()
    if not intro_clean:
        return reply

    # If reply already starts with the same opening, skip intro
    if reply.lower().startswith(intro_clean.lower()):
        return reply

    # If first sentences match, skip intro
    if _first_sentence(reply).rstrip(".!?").lower() == _first_sentence(intro_clean).rstrip(".!?").lower():
        return reply

    # If previous bot turn opened the same way, skip intro
    if last_bot_message:
        if _first_sentence(last_bot_message).rstrip(".!?").lower() == _first_sentence(intro_clean).rstrip(".!?").lower():
            return reply

    return f"{intro}{reply}"


# ---------------- Routes ----------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    if not user_message:
        return jsonify({"response": "Please type a message to start.", "mood": "neutral"})

    this_sid = sid()
    prefs = USER_PREFS.get(this_sid, {"tone": "friendly", "memory_opt_in": False})

    # Ensure session flags exist (for one-time greeting)
    if "greeted" not in session:
        session["greeted"] = False
    if "last_user" not in session:
        session["last_user"] = ""

    # Append user message to history first (keeps logs consistent)
    USER_HISTORY[this_sid].append({"role": "user", "content": user_message})

    mood = get_mood(user_message)

    # Crisis check (kept exactly as before)
    if check_crisis(user_message):
        CRISIS_MODE.add(this_sid)
        crisis_msg = get_crisis_message()
        USER_HISTORY[this_sid].append({"role": "assistant", "content": crisis_msg})
        log_interaction(this_sid, user_message, crisis_msg, mood, crisis=True, backend_used="crisis")
        return jsonify({"response": crisis_msg, "mood": mood, "crisis": True})

    if this_sid in CRISIS_MODE:
        crisis_msg = get_crisis_message()
        USER_HISTORY[this_sid].append({"role": "assistant", "content": crisis_msg})
        log_interaction(this_sid, user_message, crisis_msg, mood, crisis=True, backend_used="crisis")
        return jsonify({"response": crisis_msg, "mood": mood, "crisis": True})

    # One-time friendly greeting on the true first non-crisis turn, only if the message is a greeting
    if not session["greeted"]:
        lw = user_message.lower()
        if any(w in lw for w in ["hi", "hello", "hey", "good morning", "good evening", "good afternoon"]):
            session["greeted"] = True
            greet = random.choice([
                "Hi there. I am glad you reached out. How are you feeling today?",
                "Hello. I am here with you. What is on your mind?",
                "Hey. Thanks for saying hi. How is your day going so far?"
            ])
            USER_HISTORY[this_sid].append({"role": "assistant", "content": greet})
            session["last_user"] = user_message
            log_interaction(this_sid, user_message, greet, mood, crisis=False, backend_used="greeting")
            return jsonify({"response": greet, "mood": "neutral"})
        # If it was not a greeting, still mark greeted to avoid repeatedly testing
        session["greeted"] = True

    # Personalize intro and system prompt (kept)
    last_user = session.get("last_user")
    system_prompt = build_system_prompt(last_user, USER_HISTORY[this_sid])
    intro = personalize_response(user_message, mood, prefs.get("tone", "friendly"))

    # Try model backend (kept)
    backend_used = "unknown"
    bot_text = None
    try:
        bot_text = backend.reply(USER_HISTORY[this_sid], user_message, system_prompt)
        backend_used = type(backend).__name__
    except Exception as e:
        print(f"Backend error: {e}", flush=True)

    # Fallback to CBT logic (kept, but benefits from improved cbt_responses)
    if not bot_text:
        last_bot = _last_bot_message(USER_HISTORY[this_sid])
        cbt = get_cbt_response(mood, user_message, last_bot, sid=this_sid)
        bot_text = f'{cbt["message"]} {(cbt.get("follow_up") or "")}'.strip()
        backend_used = "cbt"

    # Combine with intro, and add goal nudge if memory on (kept)
    last_bot_before = _last_bot_message(USER_HISTORY[this_sid])
    reply = combine_with_intro(intro, bot_text, last_bot_before)
    if prefs.get("memory_opt_in"):
        reply += goal_nudge(this_sid)

    USER_HISTORY[this_sid].append({"role": "assistant", "content": reply})
    session["last_user"] = user_message

    log_interaction(this_sid, user_message, reply, mood, crisis=False, backend_used=backend_used)
    return jsonify({"response": reply, "mood": mood})


@app.route("/session-summary", methods=["GET"])
def session_summary():
    this_sid = sid()
    # Gather recent user lines for a quick recap
    recent_user_msgs = [h["content"] for h in USER_HISTORY[this_sid] if h["role"] == "user"][-8:]
    if not recent_user_msgs:
        return jsonify({"response": "We have not chatted yet. Say hi to start.", "mood": "neutral"})
    bullets = "\n".join([f"• {m}" for m in recent_user_msgs])
    summary = f"Here is a quick recap of what you shared today:\n{bullets}\n\nWould you like a small next step to try?"
    return jsonify({"response": summary, "mood": "neutral"})


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
            USER_GOALS[this_sid].append({"goal": goal_text, "time": datetime.utcnow().isoformat(), "done": False})
    return jsonify({"goals": USER_GOALS[this_sid]})


@app.route("/preferences", methods=["GET", "POST"])
def preferences():
    this_sid = sid()
    if request.method == "POST":
        prefs = request.get_json(silent=True) or {}
        USER_PREFS[this_sid] = {
            "tone": prefs.get("tone", "friendly"),
            "memory_opt_in": bool(prefs.get("memory_opt_in", False)),
        }
    return jsonify(USER_PREFS.get(this_sid, {}))


@app.route("/health")
def health():
    return jsonify({"backend": type(backend).__name__})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))


