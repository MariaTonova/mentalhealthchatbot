from flask import Flask, render_template, request, jsonify
from mood_detection import get_mood
from crisis_detection import check_crisis
from personalization import personalize_response
import os, random, sys

app = Flask(__name__)

# --- OpenAI setup (optional) ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    print("✅ GPT mode: key detected (len=%d)" % len(OPENAI_API_KEY), flush=True)
    import openai
    openai.api_key = OPENAI_API_KEY
else:
    print("💬 Offline mode: no OPENAI_API_KEY found", flush=True)
    openai = None

# --- Routes ---
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/status")
def status():
    return {"mode": "gpt" if openai else "offline"}

# --- Helpers ---
def offline_reply(user_message: str, mood: str) -> str:
    t = user_message.lower()

    # Topic-aware gentle tips
    if any(w in t for w in ["exam", "test", "deadline", "assignment"]):
        tip = "Try a 60-second box breath (4-4-4-4), then jot one tiny 5-minute next step."
    elif any(w in t for w in ["sleep", "insomnia", "can't sleep", "cant sleep", "tired", "exhausted"]):
        tip = "Dim lights, put your phone face-down for 20 minutes, and try 4-7-8 breathing for four rounds."
    elif any(w in t for w in ["panic", "anxious", "anxiety", "worry", "worried", "tight chest"]):
        tip = "Place a hand on your chest and lengthen your exhale; notice 5 things you can see around you."
    elif any(w in t for w in ["lonely", "alone", "isolated"]):
        tip = "Consider texting one safe person just to say hi or share a sentence about how you feel."
    else:
        tip = "Try the 5-4-3-2-1 grounding: 5 see, 4 touch, 3 hear, 2 smell, 1 taste."

    pre = (
        "I’m really sorry you’re going through this. " if mood == "sad"
        else "That’s wonderful to hear. " if mood == "happy"
        else "I’m here with you. "
    )
    return f"{pre}{tip}"

# --- Chat endpoint ---
@app.route("/chat", methods=["POST"])
def chat():
    user_message = (request.json or {}).get("message", "").strip()
    if not user_message:
        return jsonify({"response": "Please type a message to start.", "mood": "neutral"})

    mood = get_mood(user_message)

    # Crisis first
    if check_crisis(user_message):
        return jsonify({
            "response": (
                "I’m really glad you told me. You deserve immediate support. "
                "If you’re in the UK, call Samaritans 116 123 (24/7). "
                "If you’re elsewhere, please contact your local emergency number "
                "or a trusted person nearby."
            ),
            "mood": mood
        })

    intro = personalize_response(user_message, mood)

    # GPT path (if available)
    if openai:
        try:
            gpt_response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are CareBear, a warm, trauma-informed mental health support bot. "
                            "ALWAYS be brief (2–4 sentences), compassionate, validating, and practical. "
                            "Use simple language. Offer exactly one gentle next step "
                            "(e.g., a short grounding or breathing idea). "
                            "Avoid diagnosis or medical advice. If crisis language appears, "
                            "return a short crisis message encouraging immediate help."
                        ),
                    },
                    {"role": "user", "content": user_message},
                ],
                temperature=0.6,
                max_tokens=220,
            )
            ai_text = gpt_response.choices[0].message["content"].strip()
            final_response = f"{intro}{ai_text}"
        except Exception as e:
            print("❌ OpenAI error:", e, file=sys.stderr, flush=True)
            final_response = f"{intro}{offline_reply(user_message, mood)}"
    else:
        final_response = f"{intro}{offline_reply(user_message, mood)}"

    return jsonify({"response": final_response, "mood": mood})

# --- Entrypoint ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

