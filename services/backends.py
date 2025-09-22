# services/backends.py
# Complete backend module with OpenAI fine-tune support, HF fallback, Offline fallback,
# and a get_backend() export for backward compatibility with main.py.

import os
import json
from typing import List, Dict, Optional

# -------------------------
# Helpers
# -------------------------

def _is_truthy(val: Optional[str]) -> bool:
    if val is None:
        return False
    return str(val).strip().lower() in {"1", "true", "yes", "y", "on"}

def _recent_history(history: List[Dict[str, str]], n: int = 5) -> List[Dict[str, str]]:
    if not history:
        return []
    return history[-n:]

def _build_messages(history: List[Dict[str, str]], user_message: str, system_prompt: Optional[str]) -> List[Dict[str, str]]:
    msgs: List[Dict[str, str]] = []
    if system_prompt:
        msgs.append({"role": "system", "content": system_prompt})
    for h in _recent_history(history, 5):
        role = h.get("role", "")
        content = (h.get("content") or "").strip()
        if role in {"user", "assistant", "system"} and content:
            msgs.append({"role": role, "content": content})
    msgs.append({"role": "user", "content": (user_message or "").strip()})
    return msgs

# -------------------------
# Offline Fallback
# -------------------------

class OfflineBackend:
    """Very simple keyword fallback so you always get something."""
    name = "offline"

    def reply(self, history: List[Dict[str, str]], user_message: str, system_prompt: Optional[str]) -> Dict[str, str]:
        text = self._generate(user_message or "")
        return {"text": text, "backend": self.name, "model": "offline"}

    def _generate(self, user_message: str) -> str:
        u = user_message.lower()

        if any(x in u for x in ["hello", "hi ", " hi", "hey"]):
            return "It is good to hear from you. How are you feeling today?"
        if "thank" in u:
            return "You are very welcome. Is there anything else on your mind?"
        if any(x in u for x in ["how are you", "how are u", "how r u"]):
            return "I am a program here to support you. How are you feeling right now?"

        if any(x in u for x in ["anxious", "anxiety", "nervous"]):
            return "I am sorry you are feeling anxious. Would you like a short breathing or grounding exercise?"
        if any(x in u for x in ["sad", "depressed", "low mood"]):
            return "I am sorry you are feeling down. I am here to listen. Would a small step like a brief walk or music help?"
        if any(x in u for x in ["stress", "stressed", "overwhelmed"]):
            return "Stress can feel heavy. We can try a 2 minute breathing break or plan one small next step."

        if "breath" in u or "breathing" in u:
            return "Let us try box breathing. Inhale 4, hold 4, exhale 4, hold 4. Want to do 3 rounds together?"

        return "I am here for you. Tell me a bit more about what is on your mind."

# -------------------------
# Hugging Face Fallback (DialoGPT)
# -------------------------

class HuggingFaceBackend:
    """
    Uses DialoGPT from Hugging Face as a non-OpenAI fallback.
    Tries local transformers; if unavailable and HF_API_KEY is set, uses the HF Inference API.
    """
    name = "huggingface"

    def __init__(self):
        self._local_pipeline = None
        self._use_hf_api = False
        self._hf_model_id = os.getenv("DIALOGGPT_MODEL_ID", "microsoft/DialoGPT-small")
        self._hf_api_key = os.getenv("HF_API_KEY")

        # Try local transformers
        try:
            from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM  # type: ignore
            tok = AutoTokenizer.from_pretrained(self._hf_model_id)
            mdl = AutoModelForCausalLM.from_pretrained(self._hf_model_id)
            self._local_pipeline = pipeline("text-generation", model=mdl, tokenizer=tok)
        except Exception as e:
            print(f"[HuggingFaceBackend] local transformers unavailable: {e}")
            self._local_pipeline = None

        # If no local pipeline, consider HF Inference API
        if self._local_pipeline is None and self._hf_api_key:
            self._use_hf_api = True

    def reply(self, history: List[Dict[str, str]], user_message: str, system_prompt: Optional[str]) -> Optional[Dict[str, str]]:
        try:
            prompt = self._compose_prompt(history, user_message, system_prompt)
            if self._local_pipeline:
                out = self._local_pipeline(prompt, max_length=len(prompt.split()) + 64, do_sample=True, top_p=0.9, temperature=0.8)
                text = out[0]["generated_text"]
                text = text.split("Assistant:")[-1].strip() if "Assistant:" in text else text.strip()
                return {"text": text, "backend": self.name, "model": self._hf_model_id}

            if self._use_hf_api:
                import requests  # type: ignore
                url = f"https://api-inference.huggingface.co/models/{self._hf_model_id}"
                headers = {"Authorization": f"Bearer {self._hf_api_key}"}
                payload = {"inputs": prompt, "parameters": {"max_new_tokens": 120, "temperature": 0.8}}
                r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
                r.raise_for_status()
                data = r.json()
                if isinstance(data, list) and data and "generated_text" in data[0]:
                    text = data[0]["generated_text"]
                    text = text.split("Assistant:")[-1].strip() if "Assistant:" in text else text.strip()
                    return {"text": text, "backend": self.name, "model": self._hf_model_id}
        except Exception as e:
            print(f"[HuggingFaceBackend] generation failed: {e}")
        return None

    def _compose_prompt(self, history: List[Dict[str, str]], user_message: str, system_prompt: Optional[str]) -> str:
        lines = []
        if system_prompt:
            lines.append(f"System: {system_prompt.strip()}")
        for h in _recent_history(history, 4):
            role = h.get("role", "user").capitalize()
            content = (h.get("content") or "").strip()
            lines.append(f"{role}: {content}")
        lines.append(f"User: {(user_message or '').strip()}")
        lines.append("Assistant:")
        return "\n".join(lines)

# -------------------------
# OpenAI Backend with Fine-Tune support
# -------------------------

class OpenAIBackend:
    """OpenAI chat backend that prefers a fine-tuned model if OPENAI_FINETUNE_MODEL is set."""
    name = "openai"

    def __init__(self):
        self.client = None
        # default base model if your env doesn't specify one
        self.model_base = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        self.model_ft = os.getenv("OPENAI_FINETUNE_MODEL", "").strip() or None
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.5"))
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "300"))
        self._init_client()

    def _init_client(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("[OpenAIBackend] OPENAI_API_KEY not set")
            return
        try:
            from openai import OpenAI  # type: ignore
            base_url = os.getenv("OPENAI_API_BASE") or None  # optional
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        except Exception as e:
            self.client = None
            print(f"[OpenAIBackend] failed to init client: {e}")

    def reply(self, history: List[Dict[str, str]], user_message: str, system_prompt: Optional[str]) -> Optional[Dict[str, str]]:
        if not self.client:
            return None
        try:
            messages = _build_messages(history, user_message, system_prompt)
            model_name = self.model_ft or self.model_base
            resp = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            text = resp.choices[0].message.content.strip()
            which = "ft" if self.model_ft else "base"
            return {"text": text, "backend": self.name, "model": f"{which}:{model_name}"}
        except Exception as e:
            print(f"[OpenAIBackend] call failed: {e}")
            return None

# -------------------------
# Orchestrator + compatibility shims
# -------------------------

def _backend_order() -> List[str]:
    """
    Order can be influenced by USE_DIALOGGPT.
    If USE_DIALOGGPT=true, try HF first (handy for comparisons).
    Otherwise default to OpenAI first.
    """
    use_dialogpt = _is_truthy(os.getenv("USE_DIALOGGPT"))
    if use_dialogpt:
        return ["huggingface", "openai", "offline"]
    return ["openai", "huggingface", "offline"]

def _make_backend(name: str):
    if name == "openai":
        return OpenAIBackend()
    if name == "huggingface":
        return HuggingFaceBackend()
    return OfflineBackend()

def chat_reply(history: List[Dict[str, str]], user_message: str, system_prompt: Optional[str]) -> Dict[str, str]:
    """
    Call backends in order until one returns a response.
    Returns a dict: {text, backend, model}.
    """
    for name in _backend_order():
        backend = _make_backend(name)
        result = backend.reply(history, user_message, system_prompt)
        if result and isinstance(result, dict) and result.get("text"):
            return result
    return OfflineBackend().reply(history, user_message, system_prompt)

# Backward-compatible alias if other code imports this
def generate_response(history: List[Dict[str, str]], user_message: str, system_prompt: Optional[str]) -> Dict[str, str]:
    return chat_reply(history, user_message, system_prompt)

# ---- THIS IS WHAT main.py EXPECTS ----
class _Router:
    """
    Small adapter so existing code that does:
        from services.backends import get_backend
        backend = get_backend()
        text = backend.reply(history, user_msg, system_prompt)
    still works. It returns a STRING (text only), just like many older backends.
    """
    def reply(self, history: List[Dict[str, str]], user_message: str, system_prompt: Optional[str]) -> str:
        result = chat_reply(history, user_message, system_prompt)
        # Return text only for legacy compatibility
        return result.get("text", "")

def get_backend() -> _Router:
    """
    Exported for legacy imports in main.py.
    Returns an object with .reply(...) -> str
    """
    return _Router()

