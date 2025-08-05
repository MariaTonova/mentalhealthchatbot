from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from mood_detection import get_mood

app = Flask(__name__)
CORS(app)

# Serve the CareBear-themed chatbot interface
@app.route('/')
def home():
    return render_template('index.html')

# Generate chatbot response based on detected mood
def get_response(mood):
    if mood == "sad":
        return "🧸 I'm sorry you're feeling this way. I'm here to listen if you want to talk. 🧸 CareBear"
    elif mood == "anxious":
        return "🧸 Deep breath. You're stronger than you think—want to talk it through? 🧸 CareBear"
    elif mood == "happy":
        return "🧸 That's fantastic! I'm so proud of you 🎉 🧸 CareBear"
    elif mood == "angry":
        return "🧸 I hear you. It's okay to vent here—what happened? 🧸 CareBear"
    elif mood == "neutral":
        return "🧸 Hey there. How's your day going? 🧸 CareBear"
    else:
        return "🧸 Whatever you're feeling, I'm right here with you. 🧸 CareBear"

# Handle POST requests from the frontend
@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    mood = get_mood(user_message)
    response = get_response(mood)
    return jsonify({'mood': mood, 'response': response})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
