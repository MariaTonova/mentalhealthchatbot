import re

# -------------------------------------------------
# Crisis detection for self-harm / suicide language
# -------------------------------------------------

# Expanded list of patterns for regex matching
CRISIS_PATTERNS = [
    r"\bsuicide\b",
    r"\bkill\s*myself\b",
    r"\bkill\b",  # catch lone "kill" too
    r"\bend\s*(it|it all|my life)\b",
    r"\b(can't|cant)\s*go\s*on\b",
    r"\bno\s*reason\s*to\s*live\b",
    r"\bi\s*want\s*to\s*die\b",
    r"\b(self[-\s]?harm|hurt\s*myself)\b",
    r"\bhopeless\b",
    r"\blife\s*is\s*pointless\b",
    r"\bi'?m\s*done\b",
    r"\bgive\s*up\b",
    r"\bbetter\s*off\s*dead\b",
    r"\bend\s*my\s*life\b"
]

# Additional desperation phrases (not regex-boundary strict)
EXTRA_DESPERATION_PHRASES = [
    "can't take it anymore",
    "nothing left",
    "no way out",
    "tired of living",
    "end the pain",
    "nobody cares"
]

def check_crisis(text: str) -> bool:
    """
    Returns True if the text contains language that may indicate
    crisis, self-harm, or suicidal intent.
    """
    if not text:
        return False

    t = text.lower()

    # Check regex patterns
    if any(re.search(p, t) for p in CRISIS_PATTERNS):
        return True

    # Check desperation phrases (simple substring)
    if any(phrase in t for phrase in EXTRA_DESPERATION_PHRASES):
        return True

    return False
