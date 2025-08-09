def personalize_response(text: str, mood: str, tone: str = "friendly") -> str:
    """
    Returns a short warm intro that adapts to the user's mood and preferred tone.
    tone: "friendly" (default) or "formal"
    """
    style = "I’m here with you." if tone == "friendly" else "I’m here to support you."

    if mood == "sad":
        return f"{style} Would you like to try a grounding technique? "
    elif mood == "happy":
        return f"{style} Great to hear that spark. "
    else:  # neutral / unsure
        return f"{style} Tell me a little more about what’s on your mind. "

