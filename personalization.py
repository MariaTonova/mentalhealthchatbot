def personalize_response(text, mood):
    if mood == "sad":
        return "I'm sorry you're feeling down. Would you like to try a grounding technique?"
    elif mood == "happy":
        return "That's great to hear! Keep it up!"
    else:
        return "I'm here to listen. Tell me more about how you're feeling."
