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

def get_cbt_response(mood: str) -> dict:
    """Returns a random CBT-style message dict: {message, reason, follow_up}."""
    responses = CBT_RESPONSES.get(mood.lower(), CBT_RESPONSES["neutral"])
    return random.choice(responses)
