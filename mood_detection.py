from textblob import TextBlob
import re
from difflib import get_close_matches

# -----------------------
# Mood Keywords & Phrases
# -----------------------

positive_keywords = [
    "happy", "excited", "good", "great", "wonderful", "amazing",
    "fantastic", "excellent", "brilliant", "awesome", "perfect",
    "love", "joy", "grateful", "blessed", "optimistic", "smile", "smiling",
    "chill", "relaxed", "calm"
]

sad_keywords = [
    "sad", "depressed", "down", "low", "upset", "crying", "tears",
    "disappointed", "hurt", "broken", "lonely", "empty", "numb",
    "unwell", "sick", "ill", "tired", "exhausted", "drained", "burnt out",
    "miserable", "hopeless", "worthless", "pointless"
]

anxiety_keywords = [
    "anxious", "worried", "nervous", "scared", "panic", "stressed",
    "overwhelmed", "fear", "terrified", "tense", "shaky", "uneasy"
]

# Common negative phrases that might indicate sadness
sad_phrases = [
    "not feeling well", "not good", "not okay", "feeling bad", 
    "feel unwell", "feel down", "under the weather", "don't care anymore",
    "can't be bothered", "not worth it", "feel empty", "nothing matters"
]

anxious_phrases = [
    "on edge", "butterflies in my stomach", "heart racing", "can't relax",
    "losing control", "mind won't stop", "can't sleep", "restless"
]

positive_phrases = [
    "feeling good", "doing great", "can't complain", "all good",
    "pretty good", "feeling fine", "in a good place"
]

# -----------------------
# Fuzzy Matching Helper
# -----------------------

def fuzzy_match(text, keywords, cutoff=0.82):
    """Return True if any word in text closely matches a keyword."""
    words = text.split()
    for word in words:
        if get_close_matches(word, keywords, n=1, cutoff=cutoff):
            return True
    return False

# -----------------------
# Mood Detection Function
# -----------------------

def get_mood(message: str) -> str:
    """
    Analyzes the mood of the user message.
    Returns one of: 'happy', 'sad', 'anxious', or 'neutral'.
    """
    if not message or not message.strip():
        return "neutral"

    message_lower = message.lower().strip()

    # Sentiment analysis
    blob = TextBlob(message)
    polarity = blob.sentiment.polarity

    # Keyword & phrase-based detection
    if fuzzy_match(message_lower, positive_keywords) or \
       any(phrase in message_lower for phrase in positive_phrases):
        return "happy"

    if fuzzy_match(message_lower, sad_keywords) or \
       any(phrase in message_lower for phrase in sad_phrases):
        return "sad"

    if fuzzy_match(message_lower, anxiety_keywords) or \
       any(phrase in message_lower for phrase in anxious_phrases):
        return "anxious"

    # Sentiment fallback (subtler thresholds for short messages)
    if len(message.split()) <= 3:  
        if polarity < -0.15:
            return "sad"
        elif polarity > 0.15:
            return "happy"
        else:
            return "neutral"

    if polarity < -0.3:
        return "sad"
    elif polarity > 0.3:
        return "happy"
    else:
        return "neutral"
