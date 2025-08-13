# services/backends.py
import os, sys
from typing import List, Dict

def _flag(name: str, default="0") -> bool:
    return str(os.getenv(name, default)).strip().lower() in {"1", "true", "yes", "on"}

class Backend:
    def reply(self, history: List[Dict[str, str]], user: str, system: str) -> str:
        raise NotImplementedError

# ---------- GPT (default) ----------
class OpenAIBackend(Backend):
    def __init__(self):
        import openai  # compatible with openai==0.28.1
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY not set")
        openai.api_key = key
        self.openai = openai
        print("✅ Using OpenAI GPT backend", flush=True)

    def reply(self, history, user, system):
        messages = [{"role": "system", "content": system}, *history, {"role": "user", "content": user}]
        out = self.openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=180,
            presence_penalty=0.4,
            frequency_penalty=0.6,
        )
        return out.choices[0].message["content"].strip()

# ---------- DialoGPT (opt-in via USE_DIALOGPT=1) ----------
class DialoGPTBackend(Backend):
    def __init__(self):
        print("🤖 Loading DialoGPT backend…", flush=True)
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch  # requires torch in requirements when you enable this path

        model_id = os.getenv("DIALOGPT_MODEL_ID", "microsoft/DialoGPT-medium")
        self.tok = AutoTokenizer.from_pretrained(model_id)
        # auto dtype/device works on Render CPU; if you add GPU later, it will map accordingly
        self.model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype="auto")
        self.model.eval()
        print(f"✅ DialoGPT ready: {model_id}", flush=True)

    def reply(self, history, user, system):
        # lightweight turn formatting for small context windows
        turns = []
        for h in history[-6:]:
            role = "User" if h["role"] == "user" else "CareBear"
            turns.append(f"{role}: {h['content']}")
        turns.append(f"User: {user}")
        prompt = "\n".join(turns) + "\nCareBear:"

        import torch
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
        # return only the latest CareBear turn
        return text.split("\nCareBear:")[-1].split("\nUser:")[0].strip()

# ---------- Loader ----------
def get_backend() -> Backend:
    # Keep CURRENT SETTINGS: default to GPT if key present
    if not _flag("USE_DIALOGPT"):
        if os.getenv("OPENAI_API_KEY"):
            return OpenAIBackend()
        print("💬 Using offline fallback (no OPENAI_API_KEY)", flush=True)
        class Offline(Backend):
            def reply(self, history, user, system):
                return "I’m here with you. What feels most important to talk about right now?"
        return Offline()

    # USE_DIALOGPT=1 → try DialoGPT, fall back to GPT/offline if needed
    try:
        return DialoGPTBackend()
    except Exception as e:
        print("⚠️ DialoGPT load failed, falling back:", e, file=sys.stderr, flush=True)
        if os.getenv("OPENAI_API_KEY"):
            return OpenAIBackend()
        class Offline(Backend):
            def reply(self, history, user, system):
                return "I’m here with you. What feels most important to talk about right now?"
        return Offline()
