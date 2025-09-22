import random

# Track an exercise flow per session id
EXERCISE_STATE = {}
# Track sessions that declined suggestions
DECLINED_SUGGESTIONS = set()

CBT_RESPONSES = {
    "sad": [
        {
            "message": "I hear how heavy things feel right now. You are not alone in this 💛",
            "reason": "Empathetic validation builds safety.",
            "follow_up": "Would you like to try grounding, breathing, or reframing?"
        }
    ],
    "anxious": [
        {
            "message": "I can sense the worry in your words. Let us slow things down together 🌱",
            "reason": "Breathing and grounding help regulate anxious energy.",
            "follow_up": "Shall we try grounding, paced breathing, or reframing?"
        }
    ],
    "happy": [
        {
            "message": "That is wonderful to hear 🌟",
            "reason": "Celebrating positives reinforces wellbeing.",
            "follow_up": "What made your day feel good?"
        }
    ],
    "neutral": [
        {
            "message": "I am here with you. Tell me more about what has been on your mind.",
            "reason": "Open questions encourage expression.",
            "follow_up": "Would you like to try grounding, breathing, or reframing?"
        }
    ]
}

# Grounding
def start_grounding(sid):
    EXERCISE_STATE[sid] = {"exercise": "grounding", "step": 1}
    return {"message": "Let us start grounding 🌱. Can you name 5 things you see?", "reason": "Shift focus to present.", "follow_up": None}

def continue_grounding(sid):
    prompts = {
        2: "Great job. Now name 4 things you can touch ✋",
        3: "Nice work. Now tell me 3 things you can hear 👂",
        4: "Good job. Next, notice 2 things you can smell 👃",
        5: "Almost there. What is 1 thing you can taste 👅"
    }
    step = EXERCISE_STATE[sid]["step"]
    if step in prompts:
        EXERCISE_STATE[sid]["step"] += 1
        return {"message": prompts[step], "reason": "Progressing grounding.", "follow_up": None}
    EXERCISE_STATE.pop(sid, None)
    return {"message": "Excellent work 🌟. You completed grounding. How do you feel now?", "reason": "Close grounding.", "follow_up": "If you want, we can try breathing or reframing next."}

# Breathing
def start_breathing(sid):
    EXERCISE_STATE[sid] = {"exercise": "breathing", "step": 1}
    return {"message": "Let us practice a breathing exercise 🌬️. First, inhale slowly for 4 seconds 🫁", "reason": "Breathing calms the body.", "follow_up": None}

def continue_breathing(sid):
    prompts = {
        2: "Great. Now hold for 4 seconds.",
        3: "Good. Now exhale gently for 6 seconds 😮‍💨",
        4: "If you can, repeat that 2 or 3 times. How do you feel now?"
    }
    step = EXERCISE_STATE[sid]["step"]
    if step in prompts:
        EXERCISE_STATE[sid]["step"] += 1
        return {"message": prompts[step], "reason": "Progressing breathing.", "follow_up": None}
    EXERCISE_STATE.pop(sid, None)
    return {"message": "Well done 🌟. You completed the breathing exercise.", "reason": "Close breathing.", "follow_up": "If you want, we can try grounding or reframing next."}

# Reframing
def start_reframing(sid):
    EXERCISE_STATE[sid] = {"exercise": "reframing", "step": 1}
    return {"message": "Let us try a reframing exercise 🪞. What is a difficult thought you have been having?", "reason": "Challenge negative thoughts.", "follow_up": None}

def continue_reframing(sid):
    prompts = {
        2: "Thanks for sharing. What evidence supports this thought?",
        3: "And what evidence might go against it?",
        4: "If a friend had that thought, what would you tell them?",
        5: "What is a more balanced way of looking at this?"
    }
    step = EXERCISE_STATE[sid]["step"]
    if step in prompts:
        EXERCISE_STATE[sid]["step"] += 1
        return {"message": prompts[step], "reason": "Progressing reframing.", "follow_up": None}
    EXERCISE_STATE.pop(sid, None)
    return {"message": "Great work 🌟. You completed the reframing exercise. How do you feel now?", "reason": "Close reframing.", "follow_up": "If you want, we can try grounding or breathing next."}

# Dispatcher
def get_cbt_response(mood: str, user_message: str = "", last_bot_message: str = "", sid: str = None) -> dict:
    text = (user_message or "").lower().strip()
    last_bot = (last_bot_message or "").lower()

    # Continue active exercise
    if sid in EXERCISE_STATE:
        ex = EXERCISE_STATE[sid]["exercise"]
        if ex == "grounding":
            return continue_grounding(sid)
        if ex == "breathing":
            return continue_breathing(sid)
        if ex == "reframing":
            return continue_reframing(sid)

    # Explicit exercise requests
    if "grounding" in text or "5-4-3-2-1" in text:
        return start_grounding(sid)
    if "breathe" in text or "breathing" in text:
        return start_breathing(sid)
    if "reframe" in text or "thought" in text:
        return start_reframing(sid)

    # Yes or no to previous suggestion
    if text in ["yes", "sure", "okay", "ok", "alright", "lets do it", "let us do it"]:
        if "grounding" in last_bot:
            return start_grounding(sid)
        if "breathing" in last_bot:
            return start_breathing(sid)
        if "reframe" in last_bot or "thought" in last_bot:
            return start_reframing(sid)

    if text in ["no", "nope", "nah", "no thank you", "no thanks", "not now", "not really"]:
        if any(w in last_bot for w in ["grounding", "breathing", "reframing"]):
            DECLINED_SUGGESTIONS.add(sid)
            return {"message": "No worries 😊 We can just talk about whatever you like.", "reason": "Respecting choice.", "follow_up": None}

    # Small talk reflection to avoid generic reply
    weather_words = ["weather", "sunny", "rain", "rainy", "cloud", "cloudy", "hot", "cold", "snow", "wind", "storm", "windy"]
    if any(w in text for w in weather_words):
        if "sun" in text or "sunny" in text:
            return {
                "message": "It is nice that it is sunny ☀️. A bit of sunshine can lift mood.",
                "reason": "Reflect small talk and link to feelings.",
                "follow_up": "How does the good weather make you feel today?"
            }
        return {
            "message": "Talking about the weather can be grounding.",
            "reason": "Reflect small talk and link to feelings.",
            "follow_up": "Is the weather affecting your mood right now?"
        }

    # Default mood based response
    resp_options = CBT_RESPONSES.get(mood.lower(), CBT_RESPONSES["neutral"])
    response = random.choice(resp_options).copy()

    # Throttle repeat suggestions
    if "would you like to try" in last_bot:
        response["follow_up"] = None
    if sid in DECLINED_SUGGESTIONS and response.get("follow_up"):
        response["follow_up"] = None

    return response
