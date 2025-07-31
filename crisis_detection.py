def check_crisis(text):
    crisis_keywords = ["suicide", "kill myself", "end it", "can't go on"]
    return any(keyword in text.lower() for keyword in crisis_keywords)
