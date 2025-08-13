# services/backends.py
import os, sys
from typing import List, Dict

def _flag(name: str, default="1") -> bool:
    """Env flag helper: treats 1/true/yes/on as True."""
    return str(os.getenv(name, default)).strip().lower() in {"1", "true", "yes", "on"}

# -------------------- Base interface --------------------
class Backend:
    def reply(self, history: List[Dict[str, str]], user: str, system: str) -> str:
        raise NotImplementedError

# -------------------- DialoGPT (PRIMARY) --------------------
class DialoGPTBackend(Backend):
    def __init__(self):
        print("💬 Loading DialoGPT backend…", flush=True)
        from transformers import AutoModelForCausalLM, AutoTokenizer
        # Torch is required when this path is active (see requirements.txt)
        import torch  # noqa: F401

        model_id = os.getenv("DIALOGPT_MODEL_ID", "microsoft/DialoGPT-medium")
        self.tok = AutoTokenizer.from_pretrained(model_id)
        # CPU-friendly load; if you later add GPU, it'll still work
        self.model = AutoModelForCausalLM.from_pretrained(model_id)
        self.model.eval()
        print(f"✅ DialoGPT ready: {model_id}", flush=True)

    def reply(self, history, user, system):
        # Short, chatty formatting compatible with DialoGPT
        turns = []
        for h in history[-6:]:
            role = "User" if h["role"] == "user" else "CareBear"
            turns.append(f"{role}: {h['content']}")
        turns.append(f"User: {user}")
        prompt = "\n".join(turns) + "\nCareBear:"

        import torch
        with torch.no_grad():
            ids = self.tok.encode(prompt, return_tensors="pt")
            out = self.model.generate(
                ids,
                max_new_tokens=120,
                do_sample=True,
                top_p=0.92,
                temperature=0.7,
                pad_token_id=self.tok.eos_token_id,
                eos_token_id=self.tok.eos_token_id,
            )
        text = self.tok.decode(out[0], skip_special_tokens=True)
        # Only return the latest CareBear turn
        return text.split("\nCareBear:")[-1].split("\nUser:")[0].strip()

# -------------------- OpenAI GPT (FALLBACK) --------------------
class OpenAIBackend(Backend):
    def __init__(self):
        import openai  # compatible with openai==0.28.1
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY not set")
        openai.api_key = key
        self.openai = openai
        print("✅ OpenAI GPT backend ready", flush=True)

    def reply(self, history, user, system):
        # Legacy ChatCompletion API to match your current codebase/pin
        messages = [{"role": "system", "content": system}, *history, {"role": "user", "content": user}]
        try:
            out = self.openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=180,
                presence_penalty=0.4,
                frequency_penalty=0.6,
            )
            return out.choices[0].message["content"].strip()
        except Exception as e:
            # If quota or any other error — bubble up so caller can handle
            print("⚠️ OpenAI error in backend:", e, file=sys.stderr, flush=True)
            raise

# -------------------- Offline (FINAL) --------------------
class OfflineBackend(Backend):
    def reply(self, history, user, system):
        return "I’m here with you. What feels most important to talk about right now?"

# -------------------- Loader --------------------
def get_backend() -> Backend:
    """
    DialoGPT is PRIMARY by default (USE_DIALOGPT defaults to on).
    If DialoGPT is disabled or fails, try GPT if an API key exists.
    Else, use Offline.
    """
    use_dialogpt = _flag("USE_DIALOGPT", default="1")  # default ON as requested
    openai_key = os.getenv("OPENAI_API_KEY")

    if use_dialogpt:
        try:
            print("→ Selecting DialoGPT (primary)", flush=True)
            return DialoGPTBackend()
        except Exception as e:
            print("❌ DialoGPT load failed:", e, file=sys.stderr, flush=True)

    if openai_key:
        try:
            print("→ Selecting OpenAI GPT (fallback)", flush=True)
            return OpenAIBackend()
        except Exception as e:
            print("❌ OpenAI GPT load failed:", e, file=sys.stderr, flush=True)

    print("→ Selecting Offline backend (final fallback)", flush=True)
    return OfflineBackend()
