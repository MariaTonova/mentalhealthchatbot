def check_crisis(text):
    crisis_keywords = [
        "suicide", "kill myself", "end it", "can't go on", "hopeless", "overwhelmed",
        "end it all", "no way out", "give up", "worthless", "ending my life", "die", "life is pointless"
    ]
    lowered = text.lower()
    return any(keyword in lowered for keyword in crisis_keywords)
