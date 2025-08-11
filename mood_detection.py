from textblob import TextBlob
import re
from difflib import get_close_matches

# -----------------------
# Mood Detection Function
# -----------------------

positive_keywords = [
    "happy", "excited", "good", "great", "wonderful", "amazing",
    "fantastic", "excellent", "brilliant", "awesome", "perfect",
    "love", "joy", "grateful", "blessed", "optimistic"
]

sad_keywords = [
    "sad", "depressed", "down", "low", "upset", "crying", "tears",
    "disappointed", "hurt", "broken", "lonely", "empty", "numb",
    "unwell", "sick", "ill"
]

anxiety_keywords = [
    "anxious", "worried", "nervous", "scared", "panic", "stress",
    "overwhelmed", "fear", "terrified", "tense"
]

# Common negative phrases that might indicate sadness
sad_phrases = [
    "not feeling well", "not good", "not okay", "feeling bad", 
    "feel unwell", "feel down", "under the weather"
]

def fuzzy_match(text, keywords, cutoff=0.85):
    """Return True if any word in text closely matches a keyword."""
    words = text.split()
    for word in words:
        if get_close_matches(word, keywords, n=1, cutoff=cutoff):
            return True
    return False

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
       any(phrase in message_lower for phrase in ["feeling good", "doing great"]):
        return "happy"

    if fuzzy_match(message_lower, sad_keywords) or \
       any(phrase in message_lower for phrase in sad_phrases):
        return "sad"

    if fuzzy_match(message_lower, anxiety_keywords):
        return "anxious"

    # Sentiment fallback
    if polarity < -0.3:
        return "sad"
    elif polarity > 0.3:
        return "happy"
    else:
        return "neutral"

