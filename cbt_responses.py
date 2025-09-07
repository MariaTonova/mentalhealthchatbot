import random

# Store exercise state in memory (in practice, move this to USER_HISTORY or a dedicated dict in main.py)
EXERCISE_STATE = {}

def start_grounding(sid):
    EXERCISE_STATE[sid] = {"exercise": "grounding", "step": 1}
    return {
        "message": "Let’s begin grounding 🌱. Can you name 5 things you see around you?",
        "reason": "Grounding helps by shifting attention to the present.",
        "follow_up": None
    }

def continue_grounding(sid):
    step_prompts = {
        2: "Great 👀. Now, can you name 4 things you can touch ✋?",
        3: "Nice work! Now, 3 things you can hear 👂?",
        4: "Good. Now, 2 things you can smell 👃?",
        5: "Almost there! Finally, 1 thing you can taste 👅?",
    }
    step = EXERCISE_STATE[sid]["step"]
    if step in step_prompts:
        EXERCISE_STATE[sid]["step"] += 1
        return {"message": step_prompts[step], "reason": "Progressing grounding.", "follow_up": None}
    else:
        EXERCISE_STATE.pop(sid, None)
        return {
            "message": "Excellent 🌟 You’ve completed the grounding exercise. How do you feel now?",
            "reason": "Closing grounding.",
            "follow_up": "Would you like to try breathing or reframing next?"
        }

def start_breathing(sid):
    EXERCISE_STATE[sid] = {"exercise": "breathing", "step": 1}
    return {
        "message": "Let’s practice paced breathing 🌬️. Inhale slowly for 4 seconds 🫁.",
        "reason": "Paced breathing calms the nervous system.",
        "follow_up": None
    }

def continue_breathing(sid):
    step_prompts = {
        2: "Now, hold your breath for 4 seconds ✋.",
        3: "Exhale gently for 6 seconds 😮‍💨.",
        4: "Repeat this cycle 2–3 times. How do you feel after?",
    }
    step = EXERCISE_STATE[sid]["step"]
    if step in step_prompts:
        EXERCISE_STATE[sid]["step"] += 1
        return {"message": step_prompts[step], "reason": "Progressing breathing.", "follow_up": None}
    else:
        EXERCISE_STATE.pop(sid, None)
        return {
            "message": "Well done 🌟 You’ve completed the breathing exercise.",
            "reason": "Closing breathing.",
            "follow_up": "Would you like to try grounding or reframing next?"
        }

def start_reframing(sid):
    EXERCISE_STATE[sid] = {"exercise": "reframing", "step": 1}
    return {
        "message": "Let’s reframe a thought 🪞. Can you share a difficult thought you’ve had?",
        "reason": "Reframing helps challenge negative thinking.",
        "follow_up": None
    }

def continue_reframing(sid):
    step_prompts = {
        2: "Thanks for sharing 🙏. What evidence supports this thought?",
        3: "And what evidence goes against it?",
        4: "If a friend had this thought, what would you tell them?",
        5: "What’s a more balanced way of looking at this?",
    }
    step = EXERCISE_STATE[sid]["step"]
    if step in step_prompts:
        EXERCISE_STATE[sid]["step"] += 1
        return {"message": step_prompts[step], "reason": "Progressing reframing.", "follow_up": None}
    else:
        EXERCISE_STATE.pop(sid, None)
        return {
            "message": "Great work 🌟 You’ve completed reframing. How does that new perspective feel?",
            "reason": "Closing reframing.",
            "follow_up": "Would you like to try grounding or breathing next?"
        }

def get_cbt_response(mood: str, user_message: str = "", last_bot_message: str = "", sid: str = None) -> dict:
    """
    Step-by-step CBT response system.
    - Tracks state of ongoing exercises (grounding, breathing, reframing).
    - Handles explicit requests and yes-intent.
    """
    text = (user_message or "").lower().strip()
    last_bot = (last_bot_message or "").lower()

    # If user is in the middle of an exercise
    if sid in EXERCISE_STATE:
        ex = EXERCISE_STATE[sid]["exercise"]
        if ex == "grounding":
            return continue_grounding(sid)
        if ex == "breathing":
            return continue_breathing(sid)
        if ex == "reframing":
            return continue_reframing(sid)

    # Explicit start requests
    if any(keyword in text for keyword in ["grounding", "5-4-3-2-1"]):
        return start_grounding(sid)
    if any(keyword in text for keyword in ["breathe", "breathing", "paced breathing"]):
        return start_breathing(sid)
    if any(keyword in text for keyword in ["reframe", "reframing", "thought"]):
        return start_reframing(sid)

    # Yes-intent (continue last suggested exercise)
    if text in ["yes", "sure", "okay", "alright", "let’s do it"]:
        if "grounding" in last_bot:
            return start_grounding(sid)
        if "breathing" in last_bot:
            return start_breathing(sid)
        if "reframe" in last_bot or "thought" in last_bot:
            return start_reframing(sid)

    # Default: fallback to mood-based supportive response
    responses = CBT_RESPONSES.get(mood.lower(), CBT_RESPONSES["neutral"])
    return random.choice(responses)
