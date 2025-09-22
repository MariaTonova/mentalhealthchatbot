import random

def personalize_response(text: str, mood: str, tone: str = "friendly") -> str:
    """
    Short warm intro that adapts to mood and preferred tone.
    Variety prevents repetition. Returns a trailing space.
    """
    friendly = {
        "sad": [
            "I am here with you. That sounds really tough.",
            "I hear you. You are not alone in this.",
            "That sounds hard. I care about what you are going through."
        ],
        "happy": [
            "I am here with you. Love that spark.",
            "That is wonderful to hear.",
            "I am glad you are having a bright moment."
        ],
        "neutral": [
            "I am here with you. Tell me a bit more about what is on your mind.",
            "I am listening. How has your day been going?",
            "I hear you. What has been on your mind today?"
        ],
        "anxious": [
            "It sounds like you are feeling anxious. Let us take a slow breath together.",
            "I know things might feel overwhelming right now. I am by your side.",
            "It is okay to feel anxious. We can work through that feeling together."
        ],
    }

    formal = {
        "sad": [
            "I am here to support you during this difficult time.",
            "I understand this is hard. You are not alone.",
            "You are not alone. I am here to listen."
        ],
        "happy": [
            "It is encouraging to hear that.",
            "I am pleased you are feeling positive today.",
            "That is wonderful to hear. Let us explore what made it good."
        ],
        "neutral": [
            "I am here to support you. Please tell me more.",
            "I would like to understand more about your thoughts.",
            "How has your day been so far?"
        ],
        "anxious": [
            "It seems you are feeling anxious. Let us take a moment to breathe.",
            "I understand you may be experiencing anxiety. I am here to help.",
            "Feeling anxious can be challenging. We can take this step by step."
        ],
    }

    styles = friendly if tone == "friendly" else formal
    pool = styles.get(mood, styles["neutral"])
    return random.choice(pool) + " "

