from flask import Flask, request, jsonify
from mood_detection import get_mood
from personalization import personalize_response
from crisis_detection import check_crisis

app = Flask(__name__)

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message")
    mood = get_mood(user_input)

    if check_crisis(user_input):
        return jsonify({"response": "I'm here for you. Please consider contacting a mental health professional at 116 123 (Samaritans)."})

    response = personalize_response(user_input, mood)
    return jsonify({"response": response})

if __name__ == "__main__":
    app.run(debug=True)
