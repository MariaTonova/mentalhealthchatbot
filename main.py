from flask import Flask, render_template, request, jsonify, session
from datetime import datetime
from collections import defaultdict
from mood_detection import get_mood
from crisis_detection import check_crisis
from personalization import personalize_response
from cbt_responses import get_cbt_response  # NEW
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

MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")  # future fine-tuned model name

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

# ----------------------- Tone Modulation ----------------------
tone_templates = {
    "sad": "Use a gentle, empathetic tone. Avoid sounding overly cheerful.",
    "anxious": "Respond calmly and reassuringly. Offer grounding techniques where appropriate.",
    "neutral": "Respond in a supportive and friendly tone.",
    "happy": "Respond in an encouraging and celebratory tone."
}

def get_tone_instruction(mood):
    return tone_templates.get(mood, tone_templates["neutral"])

# ----------------------- Explainability store ----------------------
LAST_RATIONALES = {}

# ----------------------- Crisis message -----------------------
def crisis_message() -> str:
    return (
        "I’m really sorry you’re feeling this way. Your safety matters so much. "
        "If you’re in danger, please call emergency services. 📞\n"
        "🇬🇧 Samaritans: 116 123 (free, 24/7)\n"
        "🌍 Crisis Text Line: Text HOME to 741741\n"
        "🆘 Emergency Services: 999 (UK)\n"
        "If you feel safe, we can talk more — but please make sure you’re supported right now."
    )

# ----------------------- Goal nudge -----------------------
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
    last_reason = LAST_RATIONALES.get(sid())
    if last_reason:
        return jsonify({"why": last_reason})
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

    # Personalized intro
    intro = personalize_response(user_message, mood, prefs.get("tone", "friendly"))

    # GPT Mode
    if openai:
        try:
            tone_instruction = get_tone_instruction(mood)
            gpt = openai.ChatCompletion.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": f"You are CareBear, a trauma-informed mental health support bot. {tone_instruction}"},
                    *USER_HISTORY[this_sid]
                ],
                temperature=0.6,
                max_tokens=180
            )
            reply = gpt.choices[0].message["content"].strip()
            text = reply
            USER_HISTORY[this_sid].append({"role": "assistant", "content": text})

            # Save rationale placeholder for Ask Why
            LAST_RATIONALES[this_sid] = f"This advice was chosen to match your current mood ({mood}) and encourage emotional regulation."
        except Exception as e:
            print("❌ OpenAI error:", e, file=sys.stderr, flush=True)
            cbt_reply = get_cbt_response(mood)
            text = cbt_reply["message"]
            LAST_RATIONALES[this_sid] = cbt_reply["reason"]
            USER_HISTORY[this_sid].append({"role": "assistant", "content": text})
    else:
        cbt_reply = get_cbt_response(mood)
        text = cbt_reply["message"]
        LAST_RATIONALES[this_sid] = cbt_reply["reason"]
        USER_HISTORY[this_sid].append({"role": "assistant", "content": text})

    # Goal nudge
    if prefs.get("memory_opt_in"):
        text += goal_nudge(this_sid)

    return jsonify({"response": intro + " " + text, "mood": mood})

@app.route("/status")
def status():
    return {"mode": "gpt" if openai else "offline"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
