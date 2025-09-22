import random

# Store exercise state in memory (per session ID)
EXERCISE_STATE = {}

# Track sessions where coping suggestion was declined
DECLINED_SUGGESTIONS = set()

# Default CBT supportive messages
CBT_RESPONSES = {
    "sad": [
        {
            "message": "I hear how heavy things feel right now. You’re not alone in this 💛",
            "reason": "Empathetic validation builds trust and emotional safety.",
            "follow_up": "Would you like to try grounding, breathing, or reframing?"
        }
    ],
    "anxious": [
        {
            "message": "I can sense the worry in your words. Let’s slow things down together 🌱",
            "reason": "Breathing and grounding help regulate anxious energy.",
            "follow_up": "Shall we try grounding, paced breathing, or reframing?"
        }
    ],
    "happy": [
        {
            "message": "That’s wonderful to hear! 🌟",
            "reason": "Celebrating positive moments reinforces wellbeing.",
            "follow_up": "What made your day feel good?"
        }
    ],
    "neutral": [
        {
            "message": "I’m here with you. Tell me more about what’s been on your mind.",
            "reason": "Open questions encourage self-expression.",
            "follow_up": "Would you like to try grounding, breathing, or reframing?"
        }
    ]
}

# 🌱 Grounding Exercise
def start_grounding(sid):
    EXERCISE_STATE[sid] = {"exercise": "grounding", "step": 1}
    return {"message": "Let’s start grounding 🌱. Can you name 5 things you see?", "reason": "Grounding shifts focus to the present.", "follow_up": None}

def continue_grounding(sid):
    prompts = {
        2: "Great job 👀! Now, can you name 4 things you can touch around you ✋?",
        3: "Nice work! Now, can you tell me 3 things you can hear 👂?",
        4: "Good job! Next, can you notice 2 things you can smell 👃?",
        5: "Almost there! Finally, what’s 1 thing you can taste 👅?"
    }
    step = EXERCISE_STATE[sid]["step"]
    if step in prompts:
        EXERCISE_STATE[sid]["step"] += 1
        return {"message": prompts[step], "reason": "Progressing grounding.", "follow_up": None}
    else:
        EXERCISE_STATE.pop(sid, None)
        return {"message": "Excellent job 🌟, you’ve completed the grounding exercise. How do you feel now?", "reason": "Closing grounding.", "follow_up": "If you’re up for it, we could try a breathing or reframing exercise next."}

# 🌬️ Breathing Exercise
def start_breathing(sid):
    EXERCISE_STATE[sid] = {"exercise": "breathing", "step": 1}
    return {"message": "Let’s practice a breathing exercise 🌬️. First, inhale slowly for 4 seconds 🫁.", "reason": "Breathing calms the body.", "follow_up": None}

def continue_breathing(sid):
    prompts = {
        2: "Great. Now hold your breath for 4 seconds ✋.",
        3: "Good job. Now exhale gently for 6 seconds 😮‍💨.",
        4: "If you can, repeat that 2–3 times. How do you feel now?"
    }
    step = EXERCISE_STATE[sid]["step"]
    if step in prompts:
        EXERCISE_STATE[sid]["step"] += 1
        return {"message": prompts[step], "reason": "Progressing breathing.", "follow_up": None}
    else:
        EXERCISE_STATE.pop(sid, None)
        return {"message": "Well done 🌟, you’ve completed the breathing exercise.", "reason": "Closing breathing.", "follow_up": "If you’re up for it, we could try a grounding or reframing exercise next."}

# 🪞 Reframing Exercise
def start_reframing(sid):
    EXERCISE_STATE[sid] = {"exercise": "reframing", "step": 1}
    return {"message": "Let’s try a reframing exercise 🪞. Could you tell me about a difficult thought you’ve been having?", "reason": "Reframing challenges negative thoughts.", "follow_up": None}

def continue_reframing(sid):
    prompts = {
        2: "Thanks for sharing that 🙏. Now, what evidence supports this thought?",
        3: "Okay. And what evidence might go against it?",
        4: "If a friend had that thought, what would you tell them?",
        5: "What’s a more balanced way of looking at this?"
    }
    step = EXERCISE_STATE[sid]["step"]
    if step in prompts:
        EXERCISE_STATE[sid]["step"] += 1
        return {"message": prompts[step], "reason": "Progressing reframing.", "follow_up": None}
    else:
        EXERCISE_STATE.pop(sid, None)
        return {"message": "Great work 🌟, you’ve completed the reframing exercise. How do you feel now?", "reason": "Closing reframing.", "follow_up": "If you’re up for it, we could try a grounding or breathing exercise next."}

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

    # Explicit requests
    if "grounding" in text or "5-4-3-2-1" in text:
        return start_grounding(sid)
    if "breathe" in text or "breathing" in text:
        return start_breathing(sid)
    if "reframe" in text or "thought" in text:
        return start_reframing(sid)

    # Yes intent
    if text in ["yes", "sure", "okay", "alright", "let’s do it"]:
        if "grounding" in last_bot:
            return start_grounding(sid)
        if "breathing" in last_bot:
            return start_breathing(sid)
        if "reframe" in last_bot or "thought" in last_bot:
            return start_reframing(sid)

    # No intent
    if text in ["no", "nope", "nah", "no thank you", "no thanks", "not now", "not really"]:
        if any(word in last_bot for word in ["grounding", "breathing", "reframing"]):
            DECLINED_SUGGESTIONS.add(sid)
            return {"message": "No worries at all 😊 We can just talk about whatever you like.", "reason": "Respecting user choice to skip exercise.", "follow_up": None}

    # Default mood-based
    resp_options = CBT_RESPONSES.get(mood.lower(), CBT_RESPONSES["neutral"])
    response = random.choice(resp_options).copy()
    if sid in DECLINED_SUGGESTIONS and mood.lower() in ["sad", "anxious", "neutral"] and response.get("follow_up"):
        response["follow_up"] = None
    return response
