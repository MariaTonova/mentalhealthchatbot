# services/backends.py
# Minimal, legacy-compatible backend that restores get_backend() and
# ONLY uses OpenAI chat (no new dependencies, no behavior surprises).

import os
from typing import List, Dict, Optional

def _recent(history: List[Dict[str, str]], n: int = 5) -> List[Dict[str, str]]:
    return history[-n:] if history else []

def _build_messages(history: List[Dict[str, str]], user_message: str, system_prompt: Optional[str]):
    msgs = []
    if system_prompt:
        msgs.append({"role": "system", "content": system_prompt})
    for h in _recent(history, 5):
        role = h.get("role") or "user"
        content = (h.get("content") or "").strip()
        if content:
            msgs.append({"role": role, "content": content})
    msgs.append({"role": "user", "content": (user_message or "").strip()})
    return msgs

class OpenAIBackend:
    name = "openai"

    def __init__(self):
        self.client = None
        self.model_base = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        self.model_ft = (os.getenv("OPENAI_FINETUNE_MODEL") or "").strip() or None
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.5"))
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "300"))
        self._init_client()

    def _init_client(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("[OpenAIBackend] OPENAI_API_KEY not set")
            return
        try:
            from openai import OpenAI  # SDK v1
            base_url = os.getenv("OPENAI_API_BASE") or None  # optional
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        except Exception as e:
            print(f"[OpenAIBackend] init failed: {e}")
            self.client = None

    def reply(self, history: List[Dict[str, str]], user_message: str, system_prompt: Optional[str]) -> str:
        # Return a STRING to match your existing main.py contract
        if not self.client:
            # conservative fallback text if OpenAI missing
            return "I’m here to listen. How are you feeling right now?"
        try:
            messages = _build_messages(history, user_message, system_prompt)
            model_name = self.model_ft or self.model_base
            resp = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as e:
            print(f"[OpenAIBackend] call failed: {e}")
            # conservative fallback text
            return "Sorry, I had trouble generating a response. Could you try again?"

# ---- what your main.py expects ----
def get_backend():
    """
    Legacy export used by main.py:
        from services.backends import get_backend
        backend = get_backend()
        text = backend.reply(history, user_msg, system_prompt)
    """
    return OpenAIBackend()


