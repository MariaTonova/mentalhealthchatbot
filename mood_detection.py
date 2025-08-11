from textblob import TextBlob
import re
import random
from datetime import datetime

# In-memory session storage for personalization (privacy-friendly)
user_sessions = {}

class MentalHealthChatbot:
    def __init__(self):
        self.crisis_keywords = [
            "suicide", "kill myself", "end it all", "can't go on", "cant go on",
            "no reason to live", "give up completely", "want to die", 
            "life is pointless", "i'm done", "nothing matters", "hopeless",
            "better off dead", "end my life", "self harm", "hurt myself"
        ]
        self.positive_keywords = [
            "happy", "excited", "good", "great", "wonderful", "amazing",
            "fantastic", "excellent", "brilliant", "awesome", "perfect",
            "love", "joy", "grateful", "blessed", "optimistic"
        ]
        self.sad_keywords = [
            "sad", "depressed", "down", "low", "upset", "crying", "tears",
            "disappointed", "hurt", "broken", "lonely", "empty", "numb"
        ]
        self.anxiety_keywords = [
            "anxious", "worried", "nervous", "scared", "panic", "stress",
            "overwhelmed", "fear", "terrified", "tense"
        ]

    def analyze_sentiment_enhanced(self, message):
        blob = TextBlob(message)
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity
        message_lower = message.lower()
        emotions = []
        if any(w in message_lower for w in self.positive_keywords):
            emotions.append("positive")
        if any(w in message_lower for w in self.sad_keywords):
            emotions.append("sad")
        if any(w in message_lower for w in self.anxiety_keywords):
            emotions.append("anxious")
        if polarity < -0.3 or "sad" in emotions:
            mood = "sad"
        elif polarity > 0.3 or "positive" in emotions:
            mood = "happy"
        elif "anxious" in emotions:
            mood = "anxious"
        else:
            mood = "neutral"
        if subjectivity > 0.7 or len(emotions) > 1:
            intensity = "high"
        elif subjectivity > 0.4:
            intensity = "medium"
        else:
            intensity = "low"
        return {
            "mood": mood,
            "emotions": emotions,
            "intensity": intensity,
            "polarity": polarity,
            "subjectivity": subjectivity
        }

    def check_crisis(self, text):
        normalized = re.sub(r'[^\w\s\']', '', text.lower())
        desperation_phrases = [
            "can't take it anymore", "nothing left", "no way out",
            "tired of living", "end the pain", "nobody cares"
        ]
        return any(kw in normalized for kw in self.crisis_keywords) or \
               any(p in normalized for p in desperation_phrases)

    def get_personalized_response(self, message, user_id, sentiment_data):
        if user_id not in user_sessions:
            user_sessions[user_id] = {
                "conversation_count": 0,
                "mood_history": [],
                "last_interaction": None
            }
        session = user_sessions[user_id]
        session["conversation_count"] += 1
        session["mood_history"].append({
            "mood": sentiment_data["mood"],
            "timestamp": datetime.now().isoformat(),
            "intensity": sentiment_data["intensity"]
        })
        session["mood_history"] = session["mood_history"][-10:]
        mood = sentiment_data["mood"]
        intensity = sentiment_data["intensity"]
        if self.check_crisis(message):
            return {
                "message": "I'm really concerned about what you're going through right now. You don't have to face this alone.",
                "resources": [
                    "🇬🇧 Samaritans: 116 123 (free, 24/7)",
                    "🌍 Crisis Text Line: Text HOME to 741741",
                    "🆘 Emergency Services: 999",
                    "💭 Mind: 0300 123 3393"
                ]
            }
        if mood == "sad":
            return {
                "message": "I can hear that you're feeling sad. Sometimes it helps to talk it through.",
                "question": "Would you like to share what's been on your mind?",
                "suggestions": ["Tell me more", "I'd rather do an activity", "I need some comfort"]
            }
        elif mood == "anxious":
            return {
                "message": "I notice you're feeling anxious. Would you like to try a quick grounding technique?",
                "technique": "5-4-3-2-1: 5 things to see, 4 to touch, 3 to hear, 2 to smell, 1 to taste.",
                "suggestions": ["Try grounding", "Breathing exercise", "Talk it through"]
            }
        elif mood == "happy":
            return {
                "message": "It's wonderful to hear you're feeling good! What's been bringing you joy lately?",
                "suggestions": ["Share good news", "Build on this feeling", "Help others feel good too"]
            }
        else:
            return {
                "message": "Thanks for checking in. What's been occupying your thoughts today?",
                "suggestions": ["Share what's on my mind", "Set a small goal", "Practice mindfulness"]
            }

# Export bot instance
mh_bot = MentalHealthChatbot()
