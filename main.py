from flask import Flask, render_template, request, jsonify, session
from datetime import datetime
from collections import defaultdict
from mood_detection import get_mood
from crisis_detection import check_crisis
from personalization import personalize_response
import os, sys, uuid
import random

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

# ----------------------- System & helpers ----------------------------
def build_system_prompt(last_user_msg: str | None) -> str:
    base = (
        "You are CareBear, a warm, trauma-informed mental health support bot.\n"
        "STYLE: Respond in 2–3 short sentences, using simple, kind words. Use soft emojis sparingly 🙂.\n"
        "DO: First reflect the user's feelings, then normalize them, and offer ONE gentle step forward "
        "(like 5-4-3-2-1 grounding, short breathing, or a small positive focus) OR ask a gentle open question.\n"
        "AVOID: repeating yourself, giving long lists, diagnosing, or using clinical jargon.\n"
        "Be adaptive — change your language slightly each time so it doesn’t feel scripted.\n"
        "EXAMPLES OF OPENING LINES FOR SAD MOOD: 'I’m here with you. That sounds tough.', "
        "'I hear you — you’re not alone in this.', 'I’m here, and I care about what you’re going through.'\n"
        "EXAMPLES OF OPENING LINES FOR HAPPY MOOD: 'I’m here with you. Love that spark.', "
        "'That’s wonderful to hear!', 'I’m so glad you’re having a bright moment.'\n"
        "EXAMPLES OF OPENING LINES FOR NEUTRAL MOOD: 'I’m here with you. Tell me a bit more about what’s on your mind.', "
        "'I’m here with you. How’s your day been going?', 'I’m here with you. What’s been on your mind today?'\n"
        "If crisis language appears, respond with a short crisis safety message encouraging immediate help."
    )
    if last_user_msg:
        base += f"\nConversation note: The user previously said: \"{last_user_msg}\"."
    return base

def offline_reply(user_message: str, mood: str, last_msg: str | None) -> str:
    grounding_variations = [
        "Let’s try 5-4-3-2-1 grounding: 5 things you see, 4 you touch, 3 you hear, 2 you smell, 1 you taste — breathe slowly.",
        "Try the 5-4-3-2-1 grounding: notice 5 sights, 4 touches, 3 sounds, 2 scents, and 1 taste. Slow your breath each step.",
        "Focus on your senses: 5 things to see, 4 to touch, 3 to hear, 2 to smell, 1 to taste — breathing gently."
    ]

    tips_by_trigger = {
        "exam": "Try a 60-second box breath (inhale 4, hold 4, exhale 4, hold 4), then jot one small next step.",
        "sleep": "Dim the lights and try 4-7-8 breathing for four rounds; avoid screens for 20 minutes.",
        "panic": "Place a hand on your chest, lengthen the exhale, and name 5 things you can see right now.",
        "lonely": "Consider texting one safe person just to say hi and share how you feel."
    }

    triggers_found = [k for k in tips_by_trigger if k in user_message.lower()]
    tip = tips_by_trigger[triggers_found[0]] if triggers_found else random.choice(grounding_variations)

    if mood == "sad":
        pre = random.choice(["I’m really sorry it feels heavy. ", "That sounds really hard. ", "I hear how tough this is. "])
        ask = " What part feels most present right now?"
    elif mood == "happy":
        pre = random.choice(["Love that spark. ", "That’s wonderful! ", "I’m so glad to hear that. "])
        ask = " What’s one thing that’s been going well?"
    else:
        pre = random.choice(["I’m here with you. ", "I’m listening. ", "I’m right here. "])
        ask = " What’s been on your mind most today?"

    follow = " Is this connected to what you shared earlier?" if last_msg and last_msg != user_message else ""
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
                    {"role": "system", "content": build_system_prompt(last_user)},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.6,
                max_tokens=180,
                presence_penalty=0.1,
                frequency_penalty=0.2,
            )
            reply = gpt.choices[0].message["content"].strip()
            text = reply
        except Exception as e:
            print("❌ OpenAI error:", e, file=sys.stderr, flush=True)
            text = maybe_prepend_intro(intro, offline_reply(user_message, mood, last_user))
    else:
        text = maybe_prepend_intro(intro, offline_reply(user_message, mood, last_user))

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
