# cbt_responses.py
CBT_RESPONSES = {
    "sad": [
        {"message": "I hear how heavy things feel right now. You’re not alone in this 💛", "reason": "Grounding helps shift focus from painful emotions to the present moment."},
        {"message": "That sounds really hard. I’m here with you.", "reason": "Empathetic validation builds trust and emotional safety."}
    ],
    "anxious": [
        {"message": "I can sense the worry in your words. Let’s slow things down together.", "reason": "Slowing down helps regulate breathing and reduce anxious energy."},
        {"message": "Anxiety can feel intense. I’m here to help you find calm.", "reason": "Reassurance helps the nervous system feel safe."}
    ],
    "happy": [
        {"message": "That’s wonderful to hear! 🌟", "reason": "Celebrating positive moments reinforces wellbeing."},
        {"message": "I’m so glad you’re feeling this way!", "reason": "Positive reinforcement helps strengthen good moods."}
    ],
    "neutral": [
        {"message": "I’m here with you. Tell me more about what’s been on your mind.", "reason": "Open questions encourage self-expression."}
    ]
}

import random
def get_cbt_response(mood):
    responses = CBT_RESPONSES.get(mood.lower(), CBT_RESPONSES["neutral"])
    return random.choice(responses)
