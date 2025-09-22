import os
from typing import List, Dict, Any

class OfflineBackend:
    """Fallback backend using simple pattern matching"""
    
    def reply(self, history: List[Dict], user_message: str, system_prompt: str) -> str:
        # Simple response generation based on keywords
        user_lower = user_message.lower()
        
        if any(word in user_lower for word in ['hello', 'hi', 'hey']):
            return "It's good to hear from you! How are you feeling today? "
        elif any(word in user_lower for word in ['thank', 'thanks']):
            return "You're very welcome! Is there anything else on your mind? "
        elif any(word in user_lower for word in ['bye', 'goodbye']):
            return "Take care of yourself, and remember I'm here whenever you need to talk. "
        elif any(word in user_lower for word in ['weather', 'rain', 'sunny', 'cloud', 'hot', 'cold', 'snow']):
            return "Talking about the weather can be nice. It can really affect our mood sometimes, can't it? "
        elif any(word in user_lower for word in ['music', 'song', 'movie', 'show', 'book', 'game', 'sport', 'hobby', 'hobbies']):
            return "That sounds interesting! Having hobbies and interests is great. How do they make you feel? "
        elif '?' in user_message:
            return "That's a thoughtful question. Can you tell me more about what's behind it? "
        else:
            excerpt = user_message.strip()
            if len(excerpt) > 100:
                excerpt = excerpt[:100] + "..."
            if excerpt.endswith((".", "?", "!")):
                excerpt = excerpt[:-1]
            return f'You mentioned, "{excerpt}". I hear you - let\u2019s talk more about that. '

class OpenAIBackend:
    """OpenAI GPT backend (updated for new API)"""
    
    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def reply(self, history: List[Dict], user_message: str, system_prompt: str) -> str:
        try:
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend([{"role": h["role"], "content": h["content"]} for h in history[-5:]])
            messages.append({"role": "user", "content": user_message})
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=150,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI error: {e}")
            return None

class HuggingFaceBackend:
    """DialoGPT backend for conversational AI"""
    
    def __init__(self):
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch
            
            model_name = "microsoft/DialoGPT-small"
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(model_name)
            self.tokenizer.pad_token = self.tokenizer.eos_token
        except Exception as e:
            print(f"Failed to load HuggingFace model: {e}")
            raise
    
    def reply(self, history: List[Dict], user_message: str, system_prompt: str) -> str:
        try:
            # Build conversation context
            context = ""
            for h in history[-3:]:  # Use last 3 exchanges
                if h["role"] == "user":
                    context += f"User: {h['content']}\n"
                else:
                    context += f"Bot: {h['content']}\n"
            context += f"User: {user_message}\nBot:"
            
            # Generate response
            inputs = self.tokenizer.encode(context, return_tensors="pt", max_length=512, truncation=True)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_length=inputs.shape[1] + 50,
                    temperature=0.8,
                    pad_token_id=self.tokenizer.eos_token_id,
                    do_sample=True,
                    top_p=0.9
                )
            
            response = self.tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)
            return response.strip() if response else None
        except Exception as e:
            print(f"HuggingFace error: {e}")
            return None

def get_backend():
    """Initialize the appropriate backend based on available resources"""
    
    # Try OpenAI first if API key is available
    if os.getenv("OPENAI_API_KEY"):
        try:
            print("Attempting to use OpenAI backend...")
            return OpenAIBackend()
        except Exception as e:
            print(f"OpenAI init failed: {e}")
    # Try HuggingFace if OpenAI is not available or fails
    try:
        print("Attempting to use HuggingFace backend...")
        return HuggingFaceBackend()
    except Exception as e:
        print(f"HuggingFace init failed: {e}")
        # Fallback to OfflineBackend
        print("Using Offline backend as fallback.")
        return OfflineBackend()

