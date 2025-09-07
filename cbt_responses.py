import random

CBT_RESPONSES = {
    "sad": [
        {
            "message": "I hear how heavy things feel right now. You’re not alone in this 💛",
            "reason": "Empathetic validation builds trust and emotional safety.",
            "follow_up": "Would you like to try a small exercise together?"
        },
        {
            "message": "That sounds really hard. I’m here with you.",
            "reason": "Validation helps people feel understood and less isolated.",
            "follow_up": "I can guide you through a short technique — would that help?"
        }
    ],
    "anxious": [
        {
            "message": "I can sense the worry in your words. Let’s slow things down together.",
            "reason": "Slowing down helps regulate breathing and reduce anxious energy.",
            "follow_up": "Want to try a calming technique together?"
        },
        {
            "message": "Anxiety can feel intense. I’m here to help you find calm.",
            "reason": "Reassurance helps the nervous system feel safe.",
            "follow_up": "Shall I guide you through a quick exercise?"
        }
    ],
    "happy": [
        {
            "message": "That’s wonderful to hear! 🌟",
            "reason": "Celebrating positive moments reinforces wellbeing.",
            "follow_up": "What made your day feel good?"
        },
        {
            "message": "I’m so glad you’re feeling this way!",
            "reason": "Positive reinforcement helps strengthen good moods.",
            "follow_up": "Anything you’d like to hold onto or share more about?"
        }
    ],
    "neutral": [
        {
            "message": "I’m here with you. Tell me more about what’s been on your mind.",
            "reason": "Open questions encourage self-expression.",
            "follow_up": "Would you like to try a short technique together?"
        }
    ]
}

# 🌱 Grounding Exercise
GROUNDING_RESPONSE = {
    "message": (
        "Let’s try the 5-4-3-2-1 grounding technique 🌱:\n\n"
        "• 5 things you can see 👀\n"
        "• 4 things you can touch ✋\n"
        "• 3 things you can hear 👂\n"
        "• 2 things you can smell 👃\n"
        "• 1 thing you can taste 👅\n\n"
        "Take your time, and let me know how you feel after."
    ),
    "reason": "Grounding brings attention back to the present and reduces anxiety.",
    "follow_up": "Would you like to try breathing or reframing next?"
}

# 🌬️ Paced Breathing Exercise
BREATHING_RESPONSE = {
    "message": (
        "Alright, let’s try paced breathing together 🌬️:\n\n"
        "• Inhale slowly for 4 seconds 🫁\n"
        "• Hold your breath for 4 seconds ✋\n"
        "• Exhale gently for 6 seconds 😮‍💨\n\n"
        "Repeat this cycle 3–4 times. It helps calm the nervous system."
    ),
    "reason": "Paced breathing activates the parasympathetic system to reduce stress.",
    "follow_up": "Would you like to try grounding or reframing next?"
}

# 🪞 Thought Reframing Exercise
REFRAMING_RESPONSE = {
    "message": (
        "Let’s practice reframing 🪞. Think of a difficult thought you’ve had, "
        "and let’s look at it differently:\n\n"
        "• What evidence supports this thought?\n"
        "• What evidence goes against it?\n"
        "• If a friend had this thought, what would you tell them?\n"
        "• What’s a more balanced way of looking at this?\n\n"
        "This helps soften harsh self-talk into something kinder."
    ),
    "reason": "Reframing challenges unhelpful thinking and creates balance.",
    "follow_up": "Would you like me to walk you through another example?"
}

# Pool of all structured CBT techniques
CBT_TECHNIQUES = [GROUNDING_RESPONSE, BREATHING_RESPONSE, REFRAMING_RESPONSE]

def get_cbt_response(mood: str, user_message: str = "", last_bot_message: str = "") -> dict:
    """
    Returns a CBT-style response:
    - If user explicitly asks for grounding, breathing, or reframing → give that.
    - If user says 'yes' after bot offered → repeat the suggested technique.
    - Else → random supportive mood response, with a chance of offering a random CBT technique.
    """
    text = (user_message or "").lower().strip()
    last_bot = (last_bot_message or "").lower()

    # ✅ Explicit technique requests
    if any(keyword in text for keyword in ["grounding", "5-4-3-2-1", "exercise"]):
        return GROUNDING_RESPONSE
    if any(keyword in text for keyword in ["breathe", "breathing", "paced breathing"]):
        return BREATHING_RESPONSE
    if any(keyword in text for keyword in ["reframe", "reframing", "thoughts", "thinking"]):
        return REFRAMING_RESPONSE

    # ✅ Yes-intent detection
    if text in ["yes", "sure", "okay", "alright", "let’s do it"]:
        if "grounding" in last_bot:
            return GROUNDING_RESPONSE
        if "breathing" in last_bot:
            return BREATHING_RESPONSE
        if "reframe" in last_bot or "thought" in last_bot:
            return REFRAMING_RESPONSE

    # ✅ Default: mood-based + occasional random CBT technique
    responses = CBT_RESPONSES.get(mood.lower(), CBT_RESPONSES["neutral"])
    chosen = random.choice(responses)

    # 40% chance of offering a structured CBT technique even if not asked
    if random.random() < 0.4:
        return random.choice(CBT_TECHNIQUES)

    return chosen
