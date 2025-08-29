from textblob import TextBlob
from difflib import get_close_matches

# -----------------------
# Mood Keywords & Phrases
# -----------------------

MOOD_KEYWORDS = {
    "happy": [
        "happy", "excited", "good", "great", "wonderful", "amazing", "fantastic",
        "excellent", "brilliant", "awesome", "perfect", "love", "joy", "grateful",
        "blessed", "optimistic", "smile", "smiling", "chill", "relaxed", "calm"
    ],
    "sad": [
        "sad", "depressed", "down", "low", "upset", "crying", "tears", "disappointed",
        "hurt", "broken", "lonely", "empty", "numb", "unwell", "sick", "ill",
        "tired", "exhausted", "drained", "burnt out", "miserable", "hopeless",
        "worthless", "pointless"
    ],
    "anxious": [
        "anxious", "worried", "nervous", "scared", "panic", "stressed", "overwhelmed",
        "fear", "terrified", "tense", "shaky", "uneasy"
    ]
}

MOOD_PHRASES = {
    "happy": [
        "feeling good", "doing great", "can't complain", "all good",
        "pretty good", "feeling fine", "in a good place"
    ],
    "sad": [
        "not feeling well", "not good", "not okay", "feeling bad", "feel unwell",
        "feel down", "under the weather", "don't care anymore", "can't be bothered",
        "not worth it", "feel empty", "nothing matters"
    ],
    "anxious": [
        "on edge", "butterflies in my stomach", "heart racing", "can't relax",
        "losing control", "mind won't stop", "can't sleep", "restless"
    ]
}

# -----------------------
# Fuzzy Matching Helper
# -----------------------

def fuzzy_match(text, keywords, cutoff=0.82):
    words = text.split()
    for word in words:
        if get_close_matches(word, keywords, n=1, cutoff=cutoff):
            return True
    return False

# -----------------------
# Mood Detection
# -----------------------

def get_mood(message: str) -> str:
    """
    Returns: 'happy', 'sad', 'anxious', or 'neutral'
    """
    if not message or not message.strip():
        return "neutral"

    message = message.lower().strip()
    blob = TextBlob(message)
    polarity = blob.sentiment.polarity

    # Phrase + keyword detection (more confident than polarity alone)
    for mood in ["happy", "sad", "anxious"]:
        if any(phrase in message for phrase in MOOD_PHRASES[mood]):
            return mood
        if fuzzy_match(message, MOOD_KEYWORDS[mood]):
            return mood

    # Sentiment fallback (for short/mixed messages)
    if len(message.split()) <= 3:
        if polarity <= -0.15:
            return "sad"
        elif polarity >= 0.15:
            return "happy"
        else:
            return "neutral"

    # Full message polarity fallback
    if polarity < -0.35:
        return "sad"
    elif polarity > 0.35:
        return "happy"
    else:
        return "neutral"
