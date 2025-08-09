import re

# Returns True if the text contains crisis language (self-harm / suicide / immediate danger)
def check_crisis(text: str) -> bool:
    t = text.lower()

    phrases = [
        r"\bsuicide\b",
        r"\bkill\s*myself\b",
        r"\bkill\b",                    # catch lone "kill" too
        r"\bend (it|it all|my life)\b",
        r"\b(can't|cant)\s*go\s*on\b",
        r"\bno\s*reason\s*to\s*live\b",
        r"\bi\s*want\s*to\s*die\b",
        r"\b(self[-\s]?harm|hurt\s*myself)\b",
        r"\bhopeless\b",
        r"\blife\s*is\s*pointless\b",
        r"\bi'?m\s*done\b",
        r"\bgive\s*up\b"
    ]

    return any(re.search(p, t) for p in phrases)
