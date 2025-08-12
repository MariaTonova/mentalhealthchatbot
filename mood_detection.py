# mood_detection.py
from textblob import TextBlob
import re
from difflib import get_close_matches

# -----------------------
# Keyword & Phrase Lists
# -----------------------

POSITIVE_KEYWORDS = [
    "happy", "excited", "good", "great", "wonderful", "amazing",
    "fantastic", "excellent", "brilliant", "awesome", "perfect",
    "love", "joy", "grateful", "blessed", "optimistic", "cheerful"
]

NEGATIVE_KEYWORDS = [
    "sad", "upset", "depressed", "bad", "terrible", "awful", "angry",
    "lonely", "tired", "exhausted", "overwhelmed", "bored", "meh",
    "hurt", "broken", "empty", "hopeless", "unwell", "sick", "ill"
]

ANXIOUS_KEYWORDS = [
    "nervous", "worried", "scared", "anxious", "uneasy", "overthinking",
    "panic", "stressed", "fear", "tense", "restless"
]

SAD_PHRASES = [
    "not great", "not okay", "not good", "could be better", "not feeling well",
    "feeling bad", "feel unwell", "feel down", "under the weather"
]

NEGATION_WORDS = {"not", "never", "no", "hardly"}

# -----------------------
# Helpers
# -----------------------

def fuzzy_match(text, keywords, cutoff=0.85):
    """Return True if any word in text closely matches a keyword."""
    words = text.split()
    for word in words:
        if get_close_matches(word, keywords, n=1, cutoff=cutoff):
            return True
    return False

# -----------------------
# Main Function
# -----------------------

def get_mood(message: str) -> str:
    if not message or not message.strip():
        return "neutral"

    msg = message.lower().strip()

    # 1️⃣ Direct phrase matches first
    if any(phrase in msg for phrase in SAD_PHRASES):
        return "sad"

    if fuzzy_match(msg, POSITIVE_KEYWORDS) or "feeling good" in msg or "doing great" in msg:
        return "happy"

    if fuzzy_match(msg, NEGATIVE_KEYWORDS):
        return "sad"

    if fuzzy_match(msg, ANXIOUS_KEYWORDS):
        return "anxious"

    # 2️⃣ Negation handling
    tokens = re.findall(r"\b\w+\b", msg)
    for i, word in enumerate(tokens):
        if word in NEGATION_WORDS and i + 1 < len(tokens):
            if tokens[i+1] in POSITIVE_KEYWORDS:
                return "sad"
            elif tokens[i+1] in NEGATIVE_KEYWORDS:
                return "happy"

    # 3️⃣ Sentiment fallback
    blob = TextBlob(message)
    polarity = blob.sentiment.polarity

    if polarity < -0.3:
        return "sad"
    elif polarity > 0.3:
        return "happy"
    else:
        return "neutral"

# -----------------------
# Quick Tests
# -----------------------
if __name__ == "__main__":
    tests = [
        "I am happy", "not great", "I feel awful", "not sad", "I'm anxious",
        "meh", "could be better", "feeling good", "I'm blessed", "not happy",
        "doing great", "under the weather"
    ]
    for t in tests:
        print(f"{t} -> {get_mood(t)}")


