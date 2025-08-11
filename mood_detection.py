from textblob import TextBlob
import re

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
    "disappointed", "hurt", "broken", "lonely", "empty", "numb"
]

anxiety_keywords = [
    "anxious", "worried", "nervous", "scared", "panic", "stress",
    "overwhelmed", "fear", "terrified", "tense"
]

def get_mood(message: str) -> str:
    """
    Analyzes the mood of the user message.
    Returns one of: 'happy', 'sad', 'anxious', or 'neutral'.
    """
    if not message or not message.strip():
        return "neutral"

    # Sentiment analysis
    blob = TextBlob(message)
    polarity = blob.sentiment.polarity
    subjectivity = blob.sentiment.subjectivity

    # Keyword-based emotion detection
    message_lower = message.lower()
    emotions = []

    if any(word in message_lower for word in positive_keywords):
        emotions.append("positive")
    if any(word in message_lower for word in sad_keywords):
        emotions.append("sad")
    if any(word in message_lower for word in anxiety_keywords):
        emotions.append("anxious")

    # Determine primary mood
    if polarity < -0.3 or "sad" in emotions:
        mood = "sad"
    elif polarity > 0.3 or "positive" in emotions:
        mood = "happy"
    elif "anxious" in emotions:
        mood = "anxious"
    else:
        mood = "neutral"

    return mood
