# services/backends.py
import os, sys

USE_DIALOGPT = os.getenv("USE_DIALOGPT", "0") == "1"

class Backend:
    def reply(self, history, user, system):
        raise NotImplementedError

class OpenAIBackend(Backend):
    def __init__(self):
        import openai
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY not set")
        openai.api_key = key
        self.openai = openai

    def reply(self, history, user, system):
        msgs = [{"role": "system", "content": system}, *history, {"role": "user", "content": user}]
        out = self.openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=msgs,
            temperature=0.7,
            max_tokens=180
        )
        return out.choices[0].message["content"].strip()

class DialoGPTBackend(Backend):
    def __init__(self):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch
        model_id = os.getenv("DIALOGPT_MODEL_ID", "microsoft/DialoGPT-medium")
        self.tok = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype="auto", device_map="auto")
        self.model.eval()

    def reply(self, history, user, system):
        turns = []
        for h in history[-6:]:
            role = "User" if h["role"] == "user" else "CareBear"
            turns.append(f"{role}: {h['content']}")
        turns.append(f"User: {user}")
        prompt = "\n".join(turns) + "\nCareBear:"
        ids = self.tok.encode(prompt, return_tensors="pt").to(self.model.device)
        out = self.model.generate(
            ids,
            max_new_tokens=120,
            do_sample=True,
            top_p=0.92,
            temperature=0.7,
            pad_token_id=self.tok.eos_token_id
        )
        text = self.tok.decode(out[0], skip_special_tokens=True)
        return text.split("CareBear:")[-1].strip()

def get_backend() -> Backend:
    if USE_DIALOGPT:
        try:
            print("Using DialoGPT backend", flush=True)
            return DialoGPTBackend()
        except Exception as e:
            print("DialoGPT load failed, falling back to OpenAI:", e, file=sys.stderr)
    if os.getenv("OPENAI_API_KEY"):
        print("Using OpenAI backend", flush=True)
        return OpenAIBackend()
    print("Using offline fallback backend", flush=True)
    return Backend()
