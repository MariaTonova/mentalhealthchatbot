from typing import Optional
import random

# Track an exercise flow per session id
EXERCISE_STATE = {}
# Track sessions that declined suggestions
DECLINED_SUGGESTIONS = set()

# Lightweight conversation state for progressive choices (separate from exercises)
# _CONVO_STATE[sid] = {"stage": "start"|"choice"|"pick_ex"|"free_chat"}
_CONVO_STATE = {}

CBT_RESPONSES = {
    "sad": [
        {
            "message": "I hear how heavy things feel right now. You are not alone in this 💛",
            "reason": "Empathetic validation builds safety.",
            "follow_up": "Would you like to try grounding, breathing, or reframing?"
        }
    ],
    "anxious": [
        {
            "message": "I can sense the worry in your words. Let us slow things down together 🌱",
            "reason": "Breathing and grounding help regulate anxious energy.",
            "follow_up": "Shall we try grounding, paced breathing, or reframing?"
        }
    ],
    "happy": [
        {
            "message": "That is wonderful to hear 🌟",
            "reason": "Celebrating positives reinforces wellbeing.",
            "follow_up": "What made your day feel good?"
        }
    ],
    "neutral": [
        {
            "message": "I am here with you. Tell me more about what has been on your mind.",
            "reason": "Open questions encourage expression.",
            "follow_up": "Would you like to try grounding, breathing, or reframing?"
        }
    ]
}

# -----------------------------
# Helpers
# -----------------------------

def _wants_to_talk(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in ["talk", "share", "chat", "listen", "keep talking"])

def _is_decline(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in ["no", "nope", "nah", "no thank you", "no thanks",
                                "not now", "not really", "maybe later", "skip", "pass", "another time"])

def _picked_exercise(text: str) -> Optional[str]:
    t = (text or "").lower()
    for k in ["grounding", "breathing", "reframing"]:
        if k in t:
            return k
    return None

def _polite_intercepts(text: str):
    t = (text or "").lower()
    if any(w in t for w in ["thank you", "thanks", "thx"]):
        return {
            "message": "You are very welcome. Is there anything else you would like to talk about?",
            "reason": "Acknowledge gratitude and keep door open.",
            "follow_up": None
        }
    if any(w in t for w in ["maybe", "not sure", "perhaps"]):
        return {
            "message": "No problem. We can go at your pace. We can keep talking or try something gentle whenever you like.",
            "reason": "Respect uncertainty; reduce pressure.",
            "follow_up": None
        }
    return None

def _throttle_suggestions(last_bot: str, sid: str, follow_up: Optional[str]) -> Optional[str]:
    if not follow_up:
        return None
    lb = (last_bot or "").lower()
    if "would you like to try" in lb or "shall we try" in lb:
        return None
    if sid in DECLINED_SUGGESTIONS:
        return None
    return follow_up

# -----------------------------
# Exercise flows (fixed steppers)
# -----------------------------

# Grounding
def start_grounding(sid):
    EXERCISE_STATE[sid] = {"exercise": "grounding", "step": 1}
    return {"message": "Let us do 5 4 3 2 1. Name 5 things you can see.", "reason": "Shift focus to present.", "follow_up": None}

def continue_grounding(sid):
    prompts = {
        2: "Great. Now 4 things you can touch ✋",
        3: "Nice. Tell me 3 things you can hear 👂",
        4: "Good job. Notice 2 things you can smell 👃",
        5: "Almost there. What is 1 thing you can taste 👅"
    }
    step = EXERCISE_STATE[sid]["step"]

    # FIX: after start(step=1), advance to step 2
    if step == 1:
        EXERCISE_STATE[sid]["step"] = 2
        return {"message": prompts[2], "reason": "Progressing grounding.", "follow_up": None}

    if step in prompts:
        EXERCISE_STATE[sid]["step"] += 1
        return {"message": prompts[step], "reason": "Progressing grounding.", "follow_up": None}

    # Completed
    EXERCISE_STATE.pop(sid, None)
    return {"message": "Excellent work 🌟. You completed grounding. How do you feel now?",
            "reason": "Close grounding.", "follow_up": "Would you like to keep talking or set a tiny goal for today?"}

# Breathing
def start_breathing(sid):
    EXERCISE_STATE[sid] = {"exercise": "breathing", "step": 1}
    return {"message": "Box breathing. Inhale 4, hold 4, exhale 4, hold 4. Ready to try 3 rounds?",
            "reason": "Regulates the nervous system.", "follow_up": None}

def continue_breathing(sid):
    prompts = {
        2: "Great. Now hold for 4 seconds.",
        3: "Good. Now exhale gently for 4 seconds 😮‍💨",
        4: "Nice. Hold for 4. If you can, repeat 2 more rounds. Notice any shift right now?"
    }
    step = EXERCISE_STATE[sid]["step"]

    # FIX: after start(step=1), advance to step 2
    if step == 1:
        EXERCISE_STATE[sid]["step"] = 2
        return {"message": prompts[2], "reason": "Progressing breathing.", "follow_up": None}

    if step in prompts:
        EXERCISE_STATE[sid]["step"] += 1
        return {"message": prompts[step], "reason": "Progressing breathing.", "follow_up": None}

    EXERCISE_STATE.pop(sid, None)
    return {"message": "Well done 🌟. You completed the breathing exercise.",
            "reason": "Close breathing.", "follow_up": "Would you like to keep talking or set a tiny goal for today?"}

# Reframing
def start_reframing(sid):
    EXERCISE_STATE[sid] = {"exercise": "reframing", "step": 1}
    return {"message": "Let us try a reframing exercise 🪞. What is a difficult thought you have been having?",
            "reason": "Challenge negative thoughts.", "follow_up": None}

def continue_reframing(sid):
    prompts = {
        2: "Thanks for sharing. What evidence supports this thought?",
        3: "And what evidence might go against it?",
        4: "If a friend had that thought, what would you tell them?",
        5: "What is a more balanced way of looking at this?"
    }
    step = EXERCISE_STATE[sid]["step"]

    # FIX: after start(step=1), advance to step 2
    if step == 1:
        EXERCISE_STATE[sid]["step"] = 2
        return {"message": prompts[2], "reason": "Progressing reframing.", "follow_up": None}

    if step in prompts:
        EXERCISE_STATE[sid]["step"] += 1
        return {"message": prompts[step], "reason": "Progressing reframing.", "follow_up": None}

    EXERCISE_STATE.pop(sid, None)
    return {"message": "Great work 🌟. You completed the reframing exercise. How do you feel now?",
            "reason": "Close reframing.", "follow_up": "Would you like to keep talking or set a tiny goal for today?"}

# ---------------------------------
# Dispatcher (progressive flow)
# ---------------------------------

def get_cbt_response(mood: str, user_message: str = "", last_bot_message: str = "", sid: str = None) -> dict:
    """
    Progressive, gentle flow while remaining fully compatible with your
    original return structure.
    """
    text = (user_message or "").lower().strip()
    last_bot = (last_bot_message or "").lower()
    sid = sid or "anon"

    # 1) Continue any active exercise first
    if sid in EXERCISE_STATE:
        ex = EXERCISE_STATE[sid]["exercise"]
        if ex == "grounding":
            return continue_grounding(sid)
        if ex == "breathing":
            return continue_breathing(sid)
        if ex == "reframing":
            return continue_reframing(sid)

    # 2) Polite intercepts (gratitude / uncertainty)
    intercept = _polite_intercepts(text)
    if intercept:
        return intercept

    # 3) Explicit exercise triggers
    if "grounding" in text or "5-4-3-2-1" in text:
        return start_grounding(sid)
    if "breathe" in text or "breathing" in text:
        return start_breathing(sid)
    if "reframe" in text or "thought" in text:
        return start_reframing(sid)

    # Yes/OK to previous suggestion, incl “let’s start/let us start”
    if text in ["yes", "sure", "okay", "ok", "alright", "lets do it", "let us do it",
                "lets start", "let's start", "let us start"]:
        if "grounding" in last_bot:
            return start_grounding(sid)
        if "breathing" in last_bot:
            return start_breathing(sid)
        if "reframe" in last_bot or "thought" in last_bot:
            return start_reframing(sid)

    # Respect declines to recent suggestions
    if _is_decline(text):
        if any(w in last_bot for w in ["grounding", "breathing", "reframing", "calming"]):
            DECLINED_SUGGESTIONS.add(sid)
            _CONVO_STATE[sid] = {"stage": "free_chat"}
            return {"message": "No worries 😊 We can just talk about whatever you like.",
                    "reason": "Respecting choice.", "follow_up": None}

    # 4) Progressive “talk or calming” invite and branching
    state = _CONVO_STATE.get(sid, {"stage": "start"})
    if state["stage"] == "start":
        _CONVO_STATE[sid] = {"stage": "choice"}
        return {
            "message": "Would you like to talk about it, or try something calming?",
            "reason": "Gradual choices reduce cognitive load.",
            "follow_up": None
        }

    if state["stage"] == "choice":
        if _wants_to_talk(text):
            _CONVO_STATE[sid] = {"stage": "free_chat"}
            return {
                "message": "I am listening. What feels most important right now?",
                "reason": "Open exploration before techniques.",
                "follow_up": None
            }
        if "calming" in text:
            _CONVO_STATE[sid] = {"stage": "pick_ex"}
            return {
                "message": "Okay. Which one feels right?",
                "reason": "Offer techniques only after consent.",
                "follow_up": None
            }
        # otherwise fall through

    if state["stage"] == "pick_ex":
        picked = _picked_exercise(text)
        if picked == "grounding":
            return start_grounding(sid)
        if picked == "breathing":
            return start_breathing(sid)
        if picked == "reframing":
            return start_reframing(sid)
        if _is_decline(text):
            _CONVO_STATE[sid] = {"stage": "free_chat"}
            return {"message": "No problem. We can just chat. What would you like to share?",
                    "reason": "Respecting choice.", "follow_up": None}

    # 5) Small talk: weather reflection
    weather_words = ["weather", "sunny", "rain", "rainy", "cloud", "cloudy", "hot", "cold", "snow", "wind", "storm", "windy"]
    if any(w in text for w in weather_words):
        if "sun" in text or "sunny" in text:
            return {
                "message": "It is nice that it is sunny ☀️. A bit of sunshine can lift mood.",
                "reason": "Reflect small talk and link to feelings.",
                "follow_up": "How does the good weather make you feel today?"
            }
        return {
            "message": "Talking about the weather can be grounding.",
            "reason": "Reflect small talk and link to feelings.",
            "follow_up": "Is the weather affecting your mood right now?"
        }

    # 6) Default mood response (with suggestion throttling)
    resp_options = CBT_RESPONSES.get((mood or "neutral").lower(), CBT_RESPONSES["neutral"])
    response = random.choice(resp_options).copy()
    response["follow_up"] = _throttle_suggestions(last_bot, sid, response.get("follow_up"))
    return response
