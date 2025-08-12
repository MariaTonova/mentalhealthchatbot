from flask import Flask, render_template, request, jsonify, session
from datetime import datetime
from collections import defaultdict
from mood_detection import get_mood
from crisis_detection import check_crisis
from personalization import personalize_response
import os, sys, uuid, random, time

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    import openai
    openai.api_key = OPENAI_API_KEY
else:
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
    "5-4-3-2-1 grounding": "This helps you shift focus to the present moment and reduce anxiety.",
    "paced breathing": "Slowing your breathing calms your nervous system.",
    "thought reframing": "Helps replace negative thoughts with more balanced ones."
}

FUN_FACTS = [
    "Did you know? Koalas sleep up to 22 hours a day. Lazy legends!",
    "Fun fact: Smiling can actually trick your brain into feeling happier.",
    "Otters hold hands while sleeping so they don’t drift apart.",
    "Laughter boosts your immune system — so here’s a virtual chuckle! 😄"
]

FUN_GAMES = [
    "Gratitude game: Name 3 things you’re grateful for today.",
    "Mindful moment: Spot 5 things you can see around you right now.",
    "Tiny challenge: Send me one word that describes your mood in colour."
]

def crisis_message():
    return (
        "I can tell you’re going through something intense right now 💛. "
        "Your safety is the most important thing.\n"
        "If you’re in danger, please call emergency services.\n"
        "🇬🇧 Samaritans: 116 123 (free, 24/7)\n"
        "🌍 Crisis Text Line: Text HOME to 741741\n"
        "🆘 Emergency Services: 999 (UK)\n"
        "You matter, and I’m here to listen too."
    )

def build_system_prompt(last_user_msg, history):
    base = (
        "You are CareBear, a warm, playful, and empathetic mental health support bot. "
        "You respond with kindness, short conversational paragraphs, and the occasional light joke or uplifting comment. "
        "You directly answer questions when asked, and you may offer a fun fact or tiny activity if the mood is right. "
        "Avoid medical diagnoses; keep it safe and supportive."
    )
    if history:
        convo = "\n".join([f"{h['role']}: {h['content']}" for h in history[-5:]])
        base += f"\nConversation so far:\n{convo}"
    elif last_user_msg:
        base += f"\nPrevious message from user: \"{last_user_msg}\"."
    return base

def offline_reply(user_message, mood, history):
    # Detect if it's a question
    if "?" in user_message or user_message.lower().startswith(("how", "what", "why", "when", "where")):
        responses = [
            "That’s a great question! Here’s my take: ",
            "Hmm, I think it works like this — ",
            "Let’s think about that together: "
        ]
        base = random.choice(responses) + "I may not know everything, but I’ll give my best supportive answer."
    else:
        mood_responses = {
            "happy": [
                "I’m so glad to hear that! 🌟",
                "That’s a bright spot worth holding onto.",
                random.choice(FUN_FACTS)
            ],
            "sad": [
                "I can feel the heaviness in your words. You’re not alone 💛",
                "That sounds really hard. I’m here with you.",
                random.choice(FUN_GAMES)
            ],
            "anxious": [
                "I sense the tension. Let’s slow things down together.",
                "Anxiety can feel overwhelming — let’s ground ourselves.",
                random.choice(FUN_GAMES)
            ],
            "neutral": [
                "I’m here with you. What’s been on your mind?",
                random.choice(FUN_FACTS),
                random.choice(FUN_GAMES)
            ]
        }
        base = random.choice(mood_responses.get(mood, mood_responses["neutral"]))
    return base

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/ask-why", methods=["POST"])
def ask_why():
    item = (request.json or {}).get("item", "").strip().lower()
    for k, v in SUGGESTION_EXPLAINS.items():
        if k.lower() in item:
            return jsonify({"why": v})
    return jsonify({"why": "I responded that way to match your mood and the context of our conversation, keeping it safe and helpful."})

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

    if openai:
        try:
            gpt = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": build_system_prompt(last_user, USER_HISTORY[this_sid])},
                    *USER_HISTORY[this_sid]
                ],
                temperature=0.7,
                max_tokens=220
            )
            text = gpt.choices[0].message["content"].strip()
            USER_HISTORY[this_sid].append({"role": "assistant", "content": text})
        except Exception as e:
            text = offline_reply(user_message, mood, USER_HISTORY[this_sid])
            USER_HISTORY[this_sid].append({"role": "assistant", "content": text})
    else:
        time.sleep(1)  # typing simulation
        text = offline_reply(user_message, mood, USER_HISTORY[this_sid])
        USER_HISTORY[this_sid].append({"role": "assistant", "content": text})

    session["last_user"] = user_message
    return jsonify({"response": text, "mood": mood})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

