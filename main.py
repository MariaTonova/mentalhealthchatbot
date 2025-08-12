from flask import Flask, render_template, request, jsonify, session
from textblob import TextBlob
import random
import re
from difflib import get_close_matches

app = Flask(__name__)
app.secret_key = "carebear_secret_key"

# -----------------------
# Mood Detection
# -----------------------
positive_keywords = [
    "happy", "excited", "good", "great", "wonderful", "amazing",
    "fantastic", "excellent", "brilliant", "awesome", "perfect",
    "love", "joy", "grateful", "blessed", "optimistic", "smile"
]

sad_keywords = [
    "sad", "depressed", "down", "low", "upset", "crying", "tears",
    "disappointed", "hurt", "broken", "lonely", "empty", "numb",
    "unwell", "sick", "ill", "bored"
]

anxiety_keywords = [
    "anxious", "worried", "nervous", "scared", "panic", "stress",
    "overwhelmed", "fear", "terrified", "tense"
]

sad_phrases = [
    "not feeling well", "not good", "not okay", "feeling bad",
    "feel unwell", "feel down", "under the weather"
]

def fuzzy_match(text, keywords, cutoff=0.85):
    words = text.split()
    return any(get_close_matches(word, keywords, n=1, cutoff=cutoff) for word in words)

def get_mood(message):
    if not message or not message.strip():
        return "neutral"
    message_lower = message.lower().strip()
    blob = TextBlob(message)
    polarity = blob.sentiment.polarity

    if fuzzy_match(message_lower, positive_keywords):
        return "happy"
    if fuzzy_match(message_lower, sad_keywords) or any(phrase in message_lower for phrase in sad_phrases):
        return "sad"
    if fuzzy_match(message_lower, anxiety_keywords):
        return "anxious"

    if polarity < -0.3:
        return "sad"
    elif polarity > 0.3:
        return "happy"
    return "neutral"

# -----------------------
# Offline Reply Bank
# -----------------------
responses = {
    "happy": [
        "That's amazing! 🌟 What's been making you feel this way?",
        "I’m so glad to hear that 😊 What’s been the highlight of your day so far?",
        "That’s wonderful news! 💛 Any exciting plans ahead?",
        "You sound like you’re in a good place — tell me more!",
        "Yay! 🎉 I’d love to hear what’s making you smile today."
    ],
    "sad": [
        "I’m really sorry you’re feeling this way 😔 Do you want to share what’s been on your mind?",
        "That sounds rough 💙 I’m here to listen if you want to talk more.",
        "I hear you, and I’m here with you. 💛 What happened?",
        "That’s not easy to go through 😞 How can I best support you right now?",
        "I care about what you’re going through 💜 Tell me more."
    ],
    "anxious": [
        "It sounds like you’re feeling on edge 😟 Would some grounding exercises help?",
        "That must be a lot to carry 😥 Do you want to try a calming technique together?",
        "I understand anxiety can be overwhelming 💙 Do you know what might be triggering it?",
        "Let’s take a deep breath together 🌿",
        "I’m here with you — one step at a time."
    ],
    "neutral": [
        "How’s your day going so far?",
        "What’s been on your mind lately?",
        "Tell me something interesting about your day.",
        "Is there anything fun or relaxing you’ve done today?",
        "What’s something small that made you smile recently?"
    ],
    "fun": [
        "Here’s something fun: Did you know sea otters hold hands while they sleep so they don’t drift apart? 🦦",
        "Okay, fun fact time! Bananas are berries, but strawberries aren’t! 🍌🍓",
        "How about a lighthearted challenge? Describe your day using only emojis!",
        "Want to play a quick word game? I say a word, you reply with the first thing you think of.",
        "Here’s a joke: Why did the teddy bear say no to dessert? Because it was already stuffed! 🧸"
    ]
}

# -----------------------
# Avoid repetition
# -----------------------
def get_unique_response(mood):
    if "recent" not in session:
        session["recent"] = []
    recent = session["recent"]
    available = [r for r in responses[mood] if r not in recent]
    if not available:
        recent.clear()
        available = responses[mood]
    choice = random.choice(available)
    recent.append(choice)
    session["recent"] = recent[-5:]
    return choice

# -----------------------
# Chat route
# -----------------------
@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "")
    mood = get_mood(user_message)

    # Detect special request for fun
    if "fun" in user_message.lower():
        reply = get_unique_response("fun")
    else:
        reply = get_unique_response(mood)

    return jsonify({"response": reply, "mood": mood})

# -----------------------
# HTML route
# -----------------------
@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
