from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import logging
import os

# Flask app setup
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///chat.db"
db = SQLAlchemy(app)

# Logging configuration
logging.basicConfig(filename="chat_log.txt", level=logging.INFO)

# Database model for conversations
class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String(100))
    message = db.Column(db.Text)
    mood = db.Column(db.String(20))
    crisis = db.Column(db.Boolean)

# Create tables
with app.app_context():
    db.create_all()

# Mood detection
def get_mood(text):
    text = text.lower()
    if any(word in text for word in ["happy", "great", "good", "excited", "joy"]):
        return "happy"
    elif any(word in text for word in ["sad", "down", "depressed", "unhappy", "cry"]):
        return "sad"
    elif any(word in text for word in ["angry", "mad", "furious", "annoyed"]):
        return "angry"
    elif any(word in text for word in ["anxious", "nervous", "worried", "scared"]):
        return "anxious"
    else:
        return "neutral"

# Crisis keyword scanner
def check_crisis(text):
    crisis_keywords = ["pointless", "suicidal", "end it", "hopeless", "worthless", "i want to die", "can't go on"]
    return any(word in text.lower() for word in crisis_keywords)

# Response generation
def get_response(mood):
    responses = {
        "happy": "🎉 That's fantastic! I'm so proud of you.",
        "sad": "🧸 That sounds incredibly hard. You're not alone. I'm here to listen if you're ready.",
        "angry": "🔥 I hear you. It's okay to feel angry. Want to talk about it?",
        "anxious": "🌸 That sounds tough. You're safe here. Let's take a breath together.",
        "neutral": "🤍 I'm here for you. Feel free to share whatever's on your mind."
    }
    return responses.get(mood, responses["neutral"])

# Emergency resources
def get_crisis_resources():
    return (
        "If you're in the UK and need urgent help:\n"
        "- 📞 Samaritans: 116 123 (free, 24/7)\n"
        "- 🌐 Mind UK: https://www.mind.org.uk\n"
        "- 🆘 NHS Mental Health Helpline: https://www.nhs.uk/service-search/mental-health"
    )

# Log interaction to file
def log_interaction(message, mood, crisis):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] Message: '{message}' | Mood: {mood} | Crisis: {crisis}"
    logging.info(log_entry)

# Flask route
@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "")
    mood = get_mood(user_message)
    crisis = check_crisis(user_message)

    log_interaction(user_message, mood, crisis)

    new_entry = Conversation(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        message=user_message,
        mood=mood,
        crisis=crisis
    )
    db.session.add(new_entry)
    db.session.commit()

    if crisis:
        response = (
            "🚨 It sounds like you're going through something really difficult. "
            "You're not alone. Please consider reaching out to a professional or a crisis line. "
            "I'm here to support you. 💗\n\n" + get_crisis_resources()
        )
    else:
        response = get_response(mood)

    return jsonify({"response": response, "mood": mood})

# Launch app using dynamic port for Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
