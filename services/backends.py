# services/backends.py
import os, sys, requests
from typing import List, Dict

def _flag(name: str, default="1") -> bool:
    """Env flag helper: treats 1/true/yes/on as True."""
    return str(os.getenv(name, default)).strip().lower() in {"1", "true", "yes", "on"}

# -------------------- Base interface --------------------
class Backend:
    def reply(self, history: List[Dict[str, str]], user: str, system: str) -> str:
        raise NotImplementedError

# -------------------- OpenAI GPT (PRIMARY) --------------------
class OpenAIBackend(Backend):
    def __init__(self):
        import openai  # compatible with openai==0.28.1
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY not set")
        openai.api_key = key
        self.openai = openai
        print("✅ OpenAI GPT backend ready (PRIMARY)", flush=True)

    def reply(self, history, user, system):
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
            print("⚠️ OpenAI error in backend:", e, file=sys.stderr, flush=True)
            raise

# -------------------- Hugging Face (SECOND) --------------------
class HuggingFaceBackend(Backend):
    def __init__(self):
        key = os.getenv("HF_API_KEY")
        if not key:
            raise RuntimeError("HF_API_KEY not set")
        self.api_key = key
        # Use a better conversational model
        self.model_url = os.getenv("HF_MODEL_URL", "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium")
        print("✅ Hugging Face backend ready (SECOND)", flush=True)

    def reply(self, history, user, system):
        try:
            # Format conversation for DialoGPT-style models on HF
            turns = []
            for h in history[-6:]:
                role = "User" if h["role"] == "user" else "Bot"
                turns.append(f"{role}: {h['content']}")
            turns.append(f"User: {user}")
            prompt = "\n".join(turns) + "\nBot:"

            headers = {"Authorization": f"Bearer {self.api_key}"}
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 120,
                    "temperature": 0.7,
                    "do_sample": True,
                    "top_p": 0.92,
                    "return_full_text": False
                }
            }
            
            response = requests.post(self.model_url, headers=headers, json=payload, timeout=20)
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    text = result[0].get("generated_text", "").strip()
                    # Clean up the response - remove any remaining "Bot:" prefixes
                    text = text.replace("Bot:", "").strip()
                    return text if text else "I'm here with you. What would you like to talk about?"
                    
            print(f"⚠️ HF API error: {response.status_code} - {response.text}", file=sys.stderr, flush=True)
            raise Exception(f"HF API returned status {response.status_code}")
            
        except Exception as e:
            print("⚠️ Hugging Face error in backend:", e, file=sys.stderr, flush=True)
            raise

# -------------------- DialoGPT Local (THIRD) --------------------
class DialoGPTBackend(Backend):
    def __init__(self):
        print("💬 Loading DialoGPT local backend…", flush=True)
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch  # noqa: F401

        model_id = os.getenv("DIALOGPT_MODEL_ID", "microsoft/DialoGPT-medium")
        self.tok = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForCausalLM.from_pretrained(model_id)
        self.model.eval()
        print(f"✅ DialoGPT local ready (THIRD): {model_id}", flush=True)

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

# -------------------- Offline (FINAL FALLBACK) --------------------
class OfflineBackend(Backend):
    def reply(self, history, user, system):
        return "I'm here with you. What feels most important to talk about right now?"

# -------------------- Loader with New Priority Order --------------------
def get_backend() -> Backend:
    """
    NEW PRIORITY ORDER:
    1. OpenAI GPT (FIRST - if API key exists)
    2. Hugging Face API (SECOND - if API key exists) 
    3. DialoGPT Local (THIRD - if enabled and dependencies available)
    4. Offline (FINAL fallback)
    """
    
    # 1. Try OpenAI first (PRIMARY)
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            print("→ Selecting OpenAI GPT (primary)", flush=True)
            return OpenAIBackend()
        except Exception as e:
            print("❌ OpenAI GPT load failed:", e, file=sys.stderr, flush=True)

    # 2. Try Hugging Face API second
    hf_key = os.getenv("HF_API_KEY")
    if hf_key:
        try:
            print("→ Selecting Hugging Face API (second)", flush=True)
            return HuggingFaceBackend()
        except Exception as e:
            print("❌ Hugging Face API load failed:", e, file=sys.stderr, flush=True)

    # 3. Try DialoGPT local third (if enabled)
    use_dialogpt = _flag("USE_DIALOGPT", default="0")  # default OFF since it requires heavy dependencies
    if use_dialogpt:
        try:
            print("→ Selecting DialoGPT local (third)", flush=True)
            return DialoGPTBackend()
        except Exception as e:
            print("❌ DialoGPT local load failed:", e, file=sys.stderr, flush=True)

    # 4. Final fallback
    print("→ Selecting Offline backend (final fallback)", flush=True)
    return OfflineBackend()
