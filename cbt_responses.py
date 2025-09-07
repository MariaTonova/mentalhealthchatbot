import random

CBT_RESPONSES = {
    "sad": [
        {
            "message": "I hear how heavy things feel right now. You’re not alone in this 💛",
            "reason": "Grounding helps shift focus from painful emotions to the present moment.",
            "follow_up": "Would you like to try a grounding exercise together?"
        },
        {
            "message": "That sounds really hard. I’m here with you.",
            "reason": "Empathetic validation builds trust and emotional safety.",
            "follow_up": "What's been weighing on your mind the most today?"
        }
    ],
    "anxious": [
        {
            "message": "I can sense the worry in your words. Let’s slow things down together.",
            "reason": "Slowing down helps regulate breathing and reduce anxious energy.",
            "follow_up": "Shall we try the 5-4-3-2-1 grounding technique?"
        },
        {
            "message": "Anxiety can feel intense. I’m here to help you find calm.",
            "reason": "Reassurance helps the nervous system feel safe.",
            "follow_up": "Can you take one deep breath with me right now?"
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
            "follow_up": "Anything you'd like to focus on today?"
        }
    ]
}

# Explicit grounding exercise response
GROUNDING_RESPONSE = {
    "message": (
        "Let's try the 5-4-3-2-1 grounding technique 🌱\n"
        "• Look around and name 5 things you can see 👀\n"
        "• 4 things you can touch ✋\n"
        "• 3 things you can hear 👂\n"
        "• 2 things you can smell 👃\n"
        "• 1 thing you can taste 👅\n\n"
        "Take your time, and let me know how you feel after."
    ),
    "reason": "Grounding brings attention back to the present and helps calm overwhelming feelings.",
    "follow_up": "Would you like to try another exercise afterwards?"
}

def get_cbt_response(mood: str, user_message: str = "") -> dict:
    """
    Returns a CBT-style message dict: {message, reason, follow_up}.
    Prioritises grounding exercise if detected in user message.
    """
    text = user_message.lower()

    # Check for explicit grounding intent
    if any(word in text for word in ["grounding", "exercise", "5-4-3-2-1"]):
        return GROUNDING_RESPONSE

    # Otherwise return a mood-based response
    responses = CBT_RESPONSES.get(mood.lower(), CBT_RESPONSES["neutral"])
    return random.choice(responses)
