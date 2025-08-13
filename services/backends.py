import os
import sys

def get_backend():
    use_dialogpt = os.getenv("USE_DIALOGPT", "0") == "1"

    if use_dialogpt:
        print("🤖 Using DialoGPT backend", flush=True)
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch

            model_id = os.getenv("DIALOGPT_MODEL_ID", "microsoft/DialoGPT-medium")
            tokenizer = AutoTokenizer.from_pretrained(model_id)
            model = AutoModelForCausalLM.from_pretrained(model_id)

            class DialoGPTBackend:
                def reply(self, history, user_message, system_prompt):
                    # Flatten history into a single string
                    past_text = "\n".join(
                        [f"{h['role']}: {h['content']}" for h in history]
                    )
                    prompt = f"{system_prompt}\n{past_text}\nuser: {user_message}\nassistant:"

                    inputs = tokenizer(prompt, return_tensors="pt")
                    outputs = model.generate(
                        **inputs,
                        max_length=200,
                        pad_token_id=tokenizer.eos_token_id
                    )
                    return tokenizer.decode(outputs[:, inputs["input_ids"].shape[-1]:][0],
                                            skip_special_tokens=True)

            return DialoGPTBackend()
        except Exception as e:
            print("❌ Failed to load DialoGPT:", e, file=sys.stderr, flush=True)

    # Default to GPT if key exists
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print("✅ Using OpenAI GPT backend", flush=True)
        client = OpenAI(api_key=api_key)

        class GPTBackend:
            def reply(self, history, user_message, system_prompt):
                messages = [{"role": "system", "content": system_prompt}] + history + [
                    {"role": "user", "content": user_message}
                ]
                resp = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.7
                )
                return resp.choices[0].message.content.strip()

        return GPTBackend()

    # Offline fallback
    print("💬 Offline backend active", flush=True)

    class OfflineBackend:
        def reply(self, history, user_message, system_prompt):
            return "I’m here to listen — can you tell me more?"

    return OfflineBackend()
