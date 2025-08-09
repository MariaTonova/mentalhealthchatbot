from textblob import TextBlob

# Treat weak-positive phrases as NEUTRAL on purpose
_WEAK_POS = {
    "okay", "ok", "fine", "alright", "not bad", "so-so", "so so"
}

# Strong cues for happy/sad to override polarity for short inputs
_STRONG_POS = {
    "great", "amazing", "awesome", "fantastic", "good",
    "very good", "really good", "happy", "excited", "wonderful"
}
_STRONG_NEG = {
    "awful", "terrible", "horrible", "depressed", "miserable",
    "really sad", "very sad", "anxious", "panicking", "overwhelmed"
}

def get_mood(text: str) -> str:
    """
    Return 'happy' | 'sad' | 'neutral'.
    - Weak positives like "okay/fine" are neutral by design.
    - Strong keyword cues override polarity.
    - Otherwise fall back to TextBlob polarity with conservative thresholds.
    """
    t = (text or "").lower().strip()
    if not t:
        return "neutral"

    # Strong keyword overrides first
    if any(k in t for k in _STRONG_NEG):
        return "sad"
    if any(k in t for k in _STRONG_POS):
        return "happy"
    if any(k in t for k in _WEAK_POS):
        return "neutral"  # "okay", "fine", etc.

    # Polarity fallback
    pol = TextBlob(t).sentiment.polarity
    if pol <= -0.35:
        return "sad"
    if pol >= 0.35:
        return "happy"
    return "neutral"
