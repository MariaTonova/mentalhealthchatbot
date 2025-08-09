def personalize_response(text: str, mood: str) -> str:
    # Small, sincere, and warm intro line that adapts to mood.
    if mood == "sad":
        return "I’m really sorry it feels heavy right now. "
    if mood == "happy":
        return "That’s wonderful to hear. "
    return "I’m here with you. "
