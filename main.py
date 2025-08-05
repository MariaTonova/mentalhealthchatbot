from flask import Flask, render_template, request, jsonify
from mood_detection import get_mood
from crisis_detection import check_crisis
from personalization import personalize_response
import os

app = Flask(__name__)

# Homepage route (renders your CareBear chatbot interface)
@app.route('/')
def home():
    return render_template("index.html")

# Chat API route (handles frontend messages)
@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get("message", "")
    mood = get_mood(user_message)
    if check_crisis(user_message):
        return jsonify({
            "response": "🚨 Crisis detected! Please reach out to a professional or call 116 123 (Samaritans)."
        })
    response = personalize_response(user_message, mood)
    return jsonify({"response": response, "mood": mood})

# NOTE for Render:
# Do NOT call app.run() here if using gunicorn! (startCommand: gunicorn main:app)
# Gunicorn will launch the app by importing 'main:app'.

# If you want to also run the app locally (for testing), uncomment this:
if __name__ == '__main__':
   port = int(os.environ.get("PORT", 10000))
   app.run(host="0.0.0.0", port=port)


