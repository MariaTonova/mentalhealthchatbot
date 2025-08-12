from flask import Flask, render_template, request, jsonify, session
from mood_detection import get_mood
from personalization import personalize_response
import re

app = Flask(__name__)
app.secret_key = "yoursecretkey"

# In-memory store for short-term conversation
MAX_MEMORY = 3

def remember_message(role, text):
    if "history" not in session:
        session["history"] = []
    session["history"].append({"role": role, "text": text})
    if len(session["history"]) > MAX_MEMORY * 2:  # store both user+bot turns
        session["history"].pop(0)

def is_question(message):
    return message.strip().endswith("?") or re.search(r'\b(what|why|how|where|when|who)\b', message.lower())

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "").strip()
    if not user_message:
        return jsonify({"response": "I didn’t catch that — could you repeat?", "mood": "neutral"})

    # Detect mood
    mood = get_mood(user_message)

    # Memory store
    remember_message("user", user_message)

    # Detect if question
    question = is_question(user_message)

    # Generate empathetic + varied response
    bot_response = generate_bot_reply(user_message, mood, question)

    remember_message("bot", bot_response)

    return jsonify({"response": bot_response, "mood": mood})

def generate_bot_reply(message, mood, question):
    """
    Generates a human-like, mood-sensitive response.
    """

    # Base empathetic styles
    empathetic_responses = {
        "happy": [
            "That’s wonderful to hear! 🌟",
            "I’m so glad you’re feeling good today! 😊",
            "That’s great — tell me more about what’s making you happy!"
        ],
        "sad": [
            "That sounds really hard. I’m here with you 🤍",
            "I hear you — that must be tough. Want to talk more about it?",
            "I’m here to listen whenever you’re ready to share."
        ],
        "anxious": [
            "I can sense you’re feeling tense — want to try a quick grounding exercise?",
            "It’s okay to feel this way. Let’s take it one step at a time.",
            "Your feelings are valid — I’m here for you."
        ],
        "neutral": [
            "I get that. What’s been on your mind lately?",
            "I hear you. Want to share more?",
            "Tell me more — I’m listening."
        ]
    }

    # For questions, make the bot answer conversationally
    question_responses = {
        "happy": "That’s a fun question! Here’s my take: ",
        "sad": "I hear the question behind your words — here’s what I think: ",
        "anxious": "Let’s think about that together: ",
        "neutral": "Hmm, here’s my perspective: "
    }

    if question:
        # Answer with a friendly lead-in
        base = question_responses.get(mood, question_responses["neutral"])
        return f"{base}I’d love to explore that with you — what do you think?"

    # Otherwise, respond based on mood
    return personalize_response(message, mood, empathetic_responses[mood])

@app.route("/start", methods=["POST"])
def start_session():
    data = request.json
    tone = data.get("tone", "friendly")
    memory_opt_in = data.get("memory_opt_in", False)
    session["tone"] = tone
    session["memory_enabled"] = memory_opt_in
    session["history"] = []
    return jsonify({
        "disclosure": f"Session started with tone '{tone}'. Memory enabled: {memory_opt_in}"
    })

@app.route("/set-goal", methods=["POST"])
def set_goal():
    goal = request.json.get("goal", "")
    if not goal:
        return jsonify({"error": "No goal provided"})
    session["goal"] = goal
    return jsonify({"msg": f"Goal set to: {goal}"})

@app.route("/session-summary")
def session_summary():
    history = session.get("history", [])
    mood_trend = [get_mood(msg["text"]) for msg in history if msg["role"] == "user"]
    return jsonify({
        "mood_trend": mood_trend,
        "highlights": [msg["text"] for msg in history if msg["role"] == "user"]
    })

if __name__ == "__main__":
    app.run(debug=True)

