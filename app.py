from flask import Flask, request, jsonify
from mood_detection import get_mood

app = Flask(__name__)

def get_response(mood):
    if mood == "sad":
        return "I'm sorry you're feeling this way. I'm here to listen if you want to talk."
    elif mood == "anxious":
        return "Deep breath. You’re stronger than you think—want to talk it through?"
    elif mood == "happy":
        return "That’s fantastic! I’m so proud of you 🎉"
    elif mood == "angry":
        return "I hear you. It’s okay to vent here—what happened?"
    elif mood == "neutral":
        return "Hey there. How’s your day going?"
    else:
        return "Whatever you’re feeling, I'm right here with you."

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    mood = get_mood(user_message)
    response = get_response(mood)
    return jsonify({'mood': mood, 'response': response})

if __name__ == '__main__':
    app.run(port=5000)