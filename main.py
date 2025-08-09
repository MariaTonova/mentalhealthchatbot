from flask import Flask, render_template, request, jsonify
from mood_detection import get_mood
from crisis_detection import check_crisis
from personalization import personalize_response
import os, random, sys

app = Flask(__name__)

# Detect key and init OpenAI if available
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    print("✅ GPT mode: key detected (len=%d)" % len(OPENAI_API_KEY), flush=True)
    import openai
    openai.api_key = OPENAI_API_KEY
else:
    print("💬 Offline mode: no OPENAI_API_KEY found", flush=True)
    openai = None

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/status")
def status():
    return {"mode": "gpt" if openai else "offline"}

def offline_reply(user_message: str, mood: str) -> str:
    tips = [
        "Try a 4-7-8 breath: inhale 4, hold 7, exhale 8.",
        "A short walk or stretch can help reset your mind.",
        "Write down one small win from today.",
        "Ground yourself: 5 see, 4 touch, 3 hear, 2 smell, 1 taste."
    ]
    if mood == "sad":
        return "I’m sorry you’re feeling this way. " + random.choice(tips)
    elif mood == "happy":
        return "Glad to hear that. Keep it up. " + random.choice(tips)
    else:
        return "I’m here to listen. " + random.choice(tips)

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "").strip()
    if not user_message:
        return jsonify({"response": "Please type a message to start.", "mood": "neutral"})

    mood = get_mood(user_message)

    if check_crisis(user_message):
        return jsonify({
            "response": "🚨 Crisis detected. Please reach out to a professional or call 116 123 (Samaritans).",
            "mood": mood
        })

    personalized_intro = personalize_response(user_message, mood)

    # Try GPT if available
    if openai:
        try:
            gpt_response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are CareBear, a warm, supportive mental health chatbot. Keep replies brief, empathetic, and practical. Avoid medical advice."},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=220,
                temperature=0.7
            )
            ai_text = gpt_response.choices[0].message["content"].strip()
            final_response = f"{personalized_intro} {ai_text}"
        except Exception as e:
            print("❌ OpenAI error:", e, file=sys.stderr, flush=True)
            final_response = f"{personalized_intro} {offline_reply(user_message, mood)}"
    else:
        final_response = f"{personalized_intro} {offline_reply(user_message, mood)}"

    return jsonify({"response": final_response, "mood": mood})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
