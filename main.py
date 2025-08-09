from flask import Flask, render_template, request, jsonify
from mood_detection import get_mood
from crisis_detection import check_crisis
from personalization import personalize_response
import openai
import os

app = Flask(__name__)

# Set your OpenAI API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get("message", "")

    # Detect mood
    mood = get_mood(user_message)

    # Crisis detection
    if check_crisis(user_message):
        return jsonify({
            "response": "🚨 Crisis detected! Please reach out to a professional or call 116 123 (Samaritans).",
            "mood": mood
        })

    # Personalized intro
    personalized_intro = personalize_response(user_message, mood)

    try:
        gpt_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are CareBear, a warm, supportive mental health chatbot."},
                {"role": "user", "content": user_message}
            ],
            max_tokens=200,
            temperature=0.7
        )
        ai_text = gpt_response.choices[0].message.content.strip()
        final_response = f"{personalized_intro} {ai_text}"
    except Exception as e:
        print(f"Error calling GPT API: {e}")
        final_response = "I'm sorry, but I can't respond right now. Please try again later."

    return jsonify({"response": final_response, "mood": mood})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
