import random

def personalize_response(text: str, mood: str, tone: str = "friendly") -> str:
    """
    Returns a short warm intro that adapts to the user's mood and preferred tone.
    Uses varied templates to avoid repetition and better match mood.
    """

    # Friendly tone options
    friendly_styles = {
        "sad": [
            "I’m here with you. That sounds tough.",
            "I hear you — you’re not alone in this.",
            "I’m here, and I care about what you’re going through."
        ],
        "happy": [
            "I’m here with you. Love that spark.",
            "That’s wonderful to hear!",
            "I’m so glad you’re having a bright moment."
        ],
        "neutral": [
            "I’m here with you. Tell me a bit more about what’s on your mind.",
            "I’m here with you. How’s your day been going?",
            "I’m here with you. What’s been on your mind today?"
        ]
    }

    # Formal tone options
    formal_styles = {
        "sad": [
            "I’m here to support you during this difficult time.",
            "I understand this must be hard — I’m here to help.",
            "You’re not alone; I’m here to listen."
        ],
        "happy": [
            "It’s encouraging to hear that.",
            "I’m pleased you’re feeling positive today.",
            "That’s wonderful to hear — let’s explore what’s making it good."
        ],
        "neutral": [
            "I’m here to support you — please tell me more.",
            "I’d like to understand more about your current thoughts.",
            "How has your day been so far?"
        ]
    }

    styles = friendly_styles if tone == "friendly" else formal_styles
    return random.choice(styles[mood]) + " "
