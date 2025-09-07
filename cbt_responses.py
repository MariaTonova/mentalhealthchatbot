import random

# Store exercise state in memory (per session ID)
EXERCISE_STATE = {}

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
        2: "Great 👀. Now, can you name 4 things you can touch ✋?",
        3: "Nice work! Now, 3 things you can hear 👂?",
        4: "Good. Now, 2 things you can smell 👃?",
        5: "Almost there! Finally, 1 thing you can taste 👅?",
    }
    step = EXERCISE_STATE[sid]["step"]
    if step in prompts:
        EXERCISE_STATE[sid]["step"] += 1
        return {"message": prompts[step], "reason": "Progressing grounding.", "follow_up": None}
    else:
        EXERCISE_STATE.pop(sid, None)
        return {"message": "Excellent 🌟 You’ve completed grounding. How do you feel now?", "reason": "Closing grounding.", "follow_up": "Would you like to try breathing or reframing next?"}

# 🌬️ Breathing Exercise
def start_breathing(sid):
    EXERCISE_STATE[sid] = {"exercise": "breathing", "step": 1}
    return {"message": "Let’s practice paced breathing 🌬️. Inhale slowly for 4 seconds 🫁.", "reason": "Breathing calms the body.", "follow_up": None}

def continue_breathing(sid):
    prompts = {
        2: "Now hold your breath for 4 seconds ✋.",
        3: "Exhale gently for 6 seconds 😮‍💨.",
        4: "Repeat this 2–3 times. How do you feel now?",
    }
    step = EXERCISE_STATE[sid]["step"]
    if step in prompts:
        EXERCISE_STATE[sid]["step"] += 1
        return {"message": prompts[step], "reason": "Progressing breathing.", "follow_up": None}
    else:
        EXERCISE_STATE.pop(sid, None)
        return {"message": "Well done 🌟 You’ve completed breathing.", "reason": "Closing breathing.", "follow_up": "Would you like to try grounding or reframing next?"}

# 🪞 Reframing Exercise
def start_reframing(sid):
    EXERCISE_STATE[sid] = {"exercise": "reframing", "step": 1}
    return {"message": "Let’s reframe a thought 🪞. Can you share a difficult thought you’ve had?", "reason": "Reframing challenges negative thoughts.", "follow_up": None}

def continue_reframing(sid):
    prompts = {
        2: "Thanks for sharing 🙏. What evidence supports this thought?",
        3: "And what evidence goes against it?",
        4: "If a friend had this thought, what would you tell them?",
        5: "What’s a more balanced way of looking at this?",
    }
    step = EXERCISE_STATE[sid]["step"]
    if step in prompts:
        EXERCISE_STATE[sid]["step"] += 1
        return {"message": prompts[step], "reason": "Progressing reframing.", "follow_up": None}
    else:
        EXERCISE_STATE.pop(sid, None)
        return {"message": "Great work 🌟 You’ve completed reframing. How does that feel?", "reason": "Closing reframing.", "follow_up": "Would you like to try grounding or breathing next?"}

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

    # Default mood-based
    return random.choice(CBT_RESPONSES.get(mood.lower(), CBT_RESPONSES["neutral"]))
