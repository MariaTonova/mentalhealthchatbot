from flask import Flask, render_template, request, jsonify, session
from mood_detection import get_mood
from crisis_detection import check_crisis
from personalization import personalize_response
import os, random, sys

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")  # for per-session memory (non-sensitive)

# --- OpenAI setup (optional) -----------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    print("✅ GPT mode: key detected (len=%d)" % len(OPENAI_API_KEY), flush=True)
    import openai
    openai.api_key = OPENAI_API_KEY
else:
    print("💬 Offline mode: no OPENAI_API_KEY found", flush=True)
    openai = None


# --- Routes ----------------------------------------------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/status")
def status():
    return {"mode": "gpt" if openai else "offline"}


# --- Helpers ---------------------------------------------------------------
def build_system_prompt(last_msg: str | None) -> str:
    """Shapes GPT’s tone: short, loving, and practical; never medical advice."""
    base = (
        "You are CareBear, a warm, trauma-informed mental health support bot.\n"
        "STYLE: 2–4 short sentences, very kind and validating, simple words, soft emojis sparingly 🙂.\n"
        "DO: Reflect feelings, normalize, then ask ONE gentle open question or give ONE tiny step "
        "(e.g., 30–60s breath, 5-4-3-2-1 grounding, write one small win). "
        "Be strengths-based and non-judgmental.\n"
        "DON'T: diagnose, prescribe, or claim to replace professional help. "
        "If crisis language appears, respond with a brief crisis message encouraging immediate help.\n"
    )
    if last_msg:
        base += f"\nConversation note: The user previously said: \"{last_msg}\". "
    return base

def offline_reply(user_message: str, mood: str, last_msg: str | None) -> str:
    """Loving, topic-aware fallback when GPT isn’t available."""
    t = user_message.lower()

    # Topic cues → tiny next step
    if any(w in t for w in ["exam", "test", "deadline", "assignment", "study"]):
        tip = "Try a 60-second box breath (inhale 4, hold 4, exhale 4, hold 4), then jot one 5-minute next step."
    elif any(w in t for w in ["sleep", "insomnia", "can't sleep", "cant sleep", "tired", "exhausted"]):
        tip = "Dim the lights, put your phone face-down for 20 minutes, and do 4-7-8 breathing for four rounds."
    elif any(w in t for w in ["panic", "anxious", "anxiety", "worry", "worried", "tight chest"]):
        tip = "Place a hand on your chest, lengthen the exhale, and name 5 things you can see right now."
    elif any(w in t for w in ["lonely", "alone", "isolated"]):
        tip = "Consider texting one safe person just to say hi or share one line about how you feel."
    elif any(w in t for w in ["wake", "woke", "morning"]):
        tip = "Before moving on, write one tiny ‘today win’ you can do in 5 minutes. I’ll cheer you on."
    else:
        tip = "Try 5-4-3-2-1 grounding: 5 see, 4 touch, 3 hear, 2 smell, 1 taste—slow the exhale as you go."

    pre = (
        "I’m really sorry it feels heavy. " if mood == "sad"
        else "Love that spark you’re bringing. " if mood == "happy"
        else "I’m here with you. "
    )

    # A small context touch using last message (kept only for this session)
    follow = ""
    if last_msg and last_msg != user_message:
        follow = " Is this connected to what you mentioned earlier?"

    ask = (
        " What part feels most present right now?" if mood == "sad"
        else " What’s one tiny thing that might help a little right now?"
    )

    return f"{pre}{tip}{follow}{ask}"

def crisis_payload(mood: str) -> dict:
    return {
        "response": (
            "I’m really glad you told me. You deserve immediate support. "
            "If you’re in the UK, call Samaritans 116 123 (24/7). "
            "If you’re elsewhere, please contact your local emergency number "
            "or reach a trusted person nearby."
        ),
        "mood": mood
    }


# --- Chat ------------------------------------------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    user_message = (payload.get("message") or "").strip()

    if not user_message:
        return jsonify({"response": "Please type a message to start.", "mood": "neutral"})

    # Read ephemeral session memory (last user line & mood)
    last_user = session.get("last_user")  # kept client-side via session cookie
    last_mood = session.get("last_mood")

    # Quick mood read
    mood = get_mood(user_message)

    # Safety first
    if check_crisis(user_message):
        # Reset memory so we don't continue normal chat in crisis
        session["last_user"] = None
        session["last_mood"] = None
        return jsonify(crisis_payload(mood))

    # Warm intro line (short & non-repetitive)
    intro = personalize_response(user_message, mood)  # e.g., “I’m here with you. ”

    # Prefer GPT if available
    if openai:
        try:
            gpt = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": build_system_prompt(last_user)},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.6,
                max_tokens=220,
            )
            ai_text = gpt.choices[0].message["content"].strip()
            result = f"{intro}{ai_text}"
        except Exception as e:
            print("❌ OpenAI error:", e, file=sys.stderr, flush=True)
            result = f"{intro}{offline_reply(user_message, mood, last_user)}"
    else:
        result = f"{intro}{offline_reply(user_message, mood, last_user)}"

    # Update ephemeral memory for next turn
    session["last_user"] = user_message
    session["last_mood"] = mood

    return jsonify({"response": result, "mood": mood})


# --- Entrypoint ------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
