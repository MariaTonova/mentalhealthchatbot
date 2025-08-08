from flask import Flask, render_template, request, jsonify
from mood_detection import get_mood
from crisis_detection import check_crisis
from personalization import personalize_response
import os

app = Flask(__name__)

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get("message", "")
    print(f"User message received: {user_message}")

    mood = get_mood(user_message)
    print(f"Mood detected: {mood}")

    if check_crisis(user_message):
        print("Crisis detected: True")
        print("Activating crisis protocol.")
        return jsonify({
            "response": "🚨 Crisis detected! Please reach out to a professional or call 116 123 (Samaritans).",
            "mood": mood
        })

    print("Crisis detected: False")
    response = personalize_response(user_message, mood)
    return jsonify({"response": response, "mood": mood})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

