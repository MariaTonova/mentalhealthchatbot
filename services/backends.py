import os

class OfflineBackend:
    """Simple pattern based fallback."""

    def reply(self, history, user_message, system_prompt):
        user_lower = (user_message or "").lower()

        # Greetings and polite phrases
        if any(w in user_lower for w in ["hello", "hi ", " hi", "hey"]):
            return "It is good to hear from you. How are you feeling today?"
        if "thank" in user_lower:
            return "You are very welcome. Is there anything else on your mind?"
        if any(w in user_lower for w in ["bye", "goodbye", "see you"]):
            return "Take care. I am here whenever you want to talk."

        # Small talk: weather and hobbies
        if any(w in user_lower for w in ["weather", "sunny", "rain", "cloud", "hot", "cold", "wind", "snow", "storm"]):
            return "The weather can shape how we feel. How does it feel where you are?"
        if any(w in user_lower for w in ["music", "song", "movie", "show", "book", "game", "sport", "hobby", "hobbies"]):
            return "That sounds interesting. How do your hobbies make you feel lately?"

        # If question, invite more context
        if "?" in user_message:
            return "That is a thoughtful question. Can you tell me more about what is behind it?"

        # Generic reflection
        excerpt = user_message.strip()
        if len(excerpt) > 140:
            excerpt = excerpt[:140] + "..."
        excerpt = excerpt.rstrip(".?!")
        return f'You mentioned "{excerpt}". Tell me a bit more about that.'


class OpenAIBackend:
    """OpenAI GPT backend with simple chat API call."""

    def __init__(self):
        # Import lazily so the project runs even without the package
        try:
            from openai import OpenAI
            self._OpenAI = OpenAI
        except Exception as e:
            self._OpenAI = None
            print(f"OpenAI import failed: {e}")

        self.client = None
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and self._OpenAI:
            try:
                self.client = self._OpenAI(api_key=api_key)
            except Exception as e:
                print(f"OpenAI client init failed: {e}")

    def reply(self, history, user_message, system_prompt):
        if not self.client:
            return None
        try:
            messages = [{"role": "system", "content": system_prompt}]
            # include a short recent window
            for h in history[-5:]:
                messages.append({"role": h["role"], "content": h["content"]})
            messages.append({"role": "user", "content": user_message})

            # Using chat completions for compatibility with many setups
            resp = self.client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                messages=messages,
                temperature=0.7,
                max_tokens=220,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI call failed: {e}")
            return None


class HuggingFaceBackend:
    """DialoGPT small local model as a backup."""

    def __init__(self):
        self.model = None
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch  # noqa
            self._AutoModelForCausalLM = AutoModelForCausalLM
            self._AutoTokenizer = AutoTokenizer
            self._torch = __import__("torch")
            model_name = os.getenv("HF_MODEL", "microsoft/DialoGPT-small")
            self.tokenizer = self._AutoTokenizer.from_pretrained(model_name)
            self.model = self._AutoModelForCausalLM.from_pretrained(model_name)
            self.tokenizer.pad_token = self.tokenizer.eos_token
        except Exception as e:
            print(f"HuggingFace init failed: {e}")

    def reply(self, history, user_message, system_prompt):
        if not self.model:
            return None
        try:
            ctx = []
            for h in history[-3:]:
                role = "User" if h["role"] == "user" else "Bot"
                ctx.append(f"{role}: {h['content']}")
            ctx.append(f"User: {user_message}")
            ctx.append("Bot:")

            prompt = "\n".join(ctx)
            inputs = self.tokenizer.encode(prompt, return_tensors="pt", max_length=512, truncation=True)
            with self._torch.no_grad():
                output = self.model.generate(
                    inputs,
                    max_length=min(768, inputs.shape[1] + 70),
                    temperature=0.8,
                    do_sample=True,
                    top_p=0.9,
                    pad_token_id=self.tokenizer.eos_token_id,
                )
            text = self.tokenizer.decode(output[0][inputs.shape[1]:], skip_special_tokens=True)
            return text.strip() or None
        except Exception as e:
            print(f"HuggingFace call failed: {e}")
            return None


def get_backend():
    # Try OpenAI if available
    if os.getenv("OPENAI_API_KEY"):
        b = OpenAIBackend()
        if b.client:
            print("Using OpenAIBackend")
            return b
        print("OpenAI not available, trying HuggingFace")

    # Try HuggingFace
    b2 = HuggingFaceBackend()
    if b2.model:
        print("Using HuggingFaceBackend")
        return b2

    # Fallback
    print("Using OfflineBackend")
    return OfflineBackend()




