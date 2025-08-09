from flask import Flask, render_template, request, jsonify, session
from datetime import datetime
from collections import defaultdict
from mood_detection import get_mood
from crisis_detection import check_crisis
from personalization import personalize_response
import os, sys, uuid

# ----------------------- App & Optional OpenAI -----------------------
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")  # session cookie signing

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    print(f"✅ GPT mode: key detected", flush=True)
    import openai
    openai.api_key = OPENAI_API_KEY
else:
    print("💬 Offline mode: no OPENAI_API_KEY found", flush=True)
    openai = None

# ----------------------- In-memory demo stores -----------------------
USER_PREFS = {}                  # {sid: {"tone": "friendly|formal", "memory_opt_in": bool}}
USER_NOTES = defaultdict(list)   # {sid: [{"ts":..., "mood":..., "point":...}]}
USER_GOALS = defaultdict(list)   # {sid: [{"goal": str, "done": bool, "ts": ...}]}
CRISIS_MODE = set()              # {sid}

def sid():
    """Stable per-session id (demo-safe)."""
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    return session["sid"]

# ----------------------- Explainability ("Ask Why") ------------------
SUGGESTION_EXPLAINS = {
    "5-4-3-2-1 grounding": "Grounding redirects attention to present-moment senses and can lower arousal (CBT skill).",
    "paced breathing": "Slower, longer exhales stimulate the parasympathetic system so the body can settle.",
    "thought reframing": "CBT reframing examines evidence for/against a thought and finds a more balanced view."
}

# ----------------------- System & helpers ----------------------------
def build_system_prompt(last_user_msg: str | None) -> str:
    base = (
        "You are CareBear, a warm, trauma-informed mental health support bot.\n"
        "STYLE: 2–3 short sentences, kind and validating, simple words, soft emojis sparingly 🙂.\n"
        "DO: Reflect feelings, normalize, then ONE tiny step (5-4-3-2-1 grounding, 30–60s breath, or one small win) "
        "OR one gentle open question.\n"
        "AVOID: repeating yourself, long lists, diagnoses, or clinical advice.\n"
        "If crisis language appears, give a brief crisis message encouraging immediate help."
    )
    if last_user_msg:
        base += f"\nConversation note: The user previously said: \"{last_user_msg}\"."
    return base

def offline_reply(user_message: str, mood: str, last_msg: str | None) -> str:
    t = (user_message or "").lower()
    if any(w in t for w in ["exam", "deadline", "assignment", "study", "test"]):
        tip = "Try a 60-second box breath (inhale 4, hold 4, exhale 4, hold 4), then jot one 5-minute next step."
    elif any(w in t for w in ["sleep", "insomnia", "can't sleep", "cant sleep", "tired", "exhausted"]):
        tip = "Dim the lights and try 4-7-8 breathing for four rounds; keep your phone face-down for 20 min."
    elif any(w in t for w in ["panic", "anxious", "anxiety", "worry", "worried", "tight chest"]):
        tip = "Place a hand on your chest, lengthen the exhale, and name 5 things you can see right now."
    elif any(w in t for w in ["lonely", "alone", "isolated"]):
        tip = "Consider texting one safe person just to say hi and share one line about how you feel."
    else:
        tip = "Try 5-4-3-2-1 grounding: 5 see, 4 touch, 3 hear, 2 smell, 1 taste—slow your exhale as you go."
    pre = "I’m really sorry it feels heavy. " if mood == "sad" else ("Love that spark. " if mood == "happy" else "I’m here with you. ")
    follow = " Is this connected to what you shared earlier?" if last_msg and last_msg != user_message else ""
    ask = " What part feels most present right now?" if mood == "sad" else " What’s one tiny thing that might help a little?"
    return f"{pre}{tip}{follow}{ask}"

def maybe_prepend_intro(intro: str, reply: str) -> str:
    head = intro.strip().lower()[:35]
    if head and reply.strip().lower().startswith(head[:20]):
        return reply.strip()
    return f"{intro}{reply}".strip()

def crisis_message() -> str:
    return (
        "I’m really sorry you’re feeling this way. I can’t keep chatting right now—your safety matters. "
        "If you’re in danger, call emergency services. In the UK/ROI, Samaritans 116 123 is 24/7. "
        "If you’re safe and want to continue later, say “resume”."
    )

def goal_nudge(this_sid: str) -> str:
    open_goals = [g for g in USER_GOALS[this_sid] if not g["done"]]
    return f"\n\nLast time you set: “{open_goals[0]['goal']}”. Any tiny step today?" if open_goals else ""

# ----------------------- Routes: UI ----------------------------------
@app.route("/")
def home():
    return render_template("index.html")

# ----------------------- Routes: onboarding & prefs ------------------
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

# ----------------------- Routes: explainability ----------------------
@app.route("/ask-why", methods=["POST"])
def ask_why():
    item = (request.json or {}).get("item", "").strip().lower()
    for k, v in SUGGESTION_EXPLAINS.items():
        if k.lower() in item:
            return jsonify({"why": v})
    return jsonify({"why": "I suggest skills from CBT/mindfulness that match your mood and recent messages."})

# ----------------------- Routes: goals & summary ---------------------
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

# ----------------------- Routes: crisis resume -----------------------
@app.route("/resume", methods=["POST"])
def resume():
    CRISIS_MODE.discard(sid())
    return jsonify({"response": "Thanks for checking back in. How are you feeling right now?"})

# ----------------------- Routes: chat core ---------------------------
@app.route("/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    user_message = (payload.get("message") or "").strip()
    if not user_message:
        return jsonify({"response": "Please type a message to start.", "mood": "neutral"})

    this_sid = sid()
    prefs = USER_PREFS.get(this_sid, {"tone": "friendly", "memory_opt_in": False})
    last_user = session.get("last_user")

    # mood + crisis detection
    mood = get_mood(user_message)
    if check_crisis(user_message):
        CRISIS_MODE.add(this_sid)
        return jsonify({"response": crisis_message(), "mood": mood, "crisis": True})
    if this_sid in CRISIS_MODE:
        return jsonify({"response": crisis_message(), "mood": mood, "crisis": True})

    # store brief session notes if memory is on
    if prefs.get("memory_opt_in"):
        USER_NOTES[this_sid].append({
            "ts": datetime.utcnow().isoformat(),
            "mood": mood,
            "point": user_message[:160]
        })

    # personalized intro by mood + tone
    intro = personalize_response(user_message, mood, prefs.get("tone", "friendly"))

    # generate reply (OpenAI optional)
    if openai:
        try:
            gpt = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": build_system_prompt(last_user)},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.6,
                max_tokens=180,
                presence_penalty=0.1,
                frequency_penalty=0.2,
            )
            reply = gpt.choices[0].message["content"].strip()
            text = reply  # no intro prefix in GPT mode to avoid repetition
        except Exception as e:
            print("❌ OpenAI error:", e, file=sys.stderr, flush=True)
            fallback = offline_reply(user_message, mood, last_user)
            text = maybe_prepend_intro(intro, fallback)
    else:
        fallback = offline_reply(user_message, mood, last_user)
        text = maybe_prepend_intro(intro, fallback)

    # gentle goal nudge if opted-in memory
    if prefs.get("memory_opt_in"):
        text += goal_nudge(this_sid)

    session["last_user"] = user_message
    return jsonify({"response": text, "mood": mood})

# ----------------------- Dev status route (optional) -----------------
@app.route("/status")
def status():
    return {"mode": "gpt" if openai else "offline"}

# ----------------------- Run ----------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
