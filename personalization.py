import random

def personalize_response(text: str, mood: str, tone: str = "friendly") -> str:
    """
    Returns a short warm intro that adapts to the user's mood and preferred tone.
    Uses varied templates to avoid repetition and better match mood.
    """

    # Friendly tone options
    friendly_styles = {
        "sad": [
            "I’m here with you. That sounds really tough.",
            "I hear you — you’re not alone in this.",
            "That sounds really hard. I care about what you’re going through."
        ],
        "happy": [
            "I’m here with you. Love that spark.",
            "That’s wonderful to hear!",
            "I’m so glad you’re having a bright moment."
        ],
        "neutral": [
            "I’m here with you. Tell me a bit more about what’s on your mind.",
            "I’m listening. How has your day been going?",
            "I hear you. What’s been on your mind today?"
        ],
        "anxious": [
            "It sounds like you’re feeling anxious. Let’s take a deep breath together.",
            "I know things might feel overwhelming right now. I’m here by your side.",
            "It’s okay to feel anxious sometimes. We can work through that feeling together."
        ]
    }

    # Formal tone options
    formal_styles = {
        "sad": [
            "I’m here to support you during this difficult time.",
            "I understand this must be hard. You’re not alone in this.",
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
        ],
        "anxious": [
            "It seems you’re feeling anxious at the moment. Let’s take a moment to breathe and gather our thoughts.",
            "I understand you may be experiencing anxiety. I’m here to help you through this.",
            "Feeling anxious can be challenging. We can take things step by step together."
        ]
    }

    styles = friendly_styles if tone == "friendly" else formal_styles
    return random.choice(styles[mood]) + " "
