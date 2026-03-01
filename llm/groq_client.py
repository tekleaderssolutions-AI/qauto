"""Groq API client for cloud LLM (Render deployment). Use when GROQ_API_KEY is set."""
import os
from typing import Optional

GROQ_MODEL = "llama-3.1-70b-versatile"


def generate(prompt: str, system: Optional[str] = None, max_tokens: int = 256) -> str:
    """Call Groq API. Returns empty string if key missing or error."""
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        return ""
    try:
        from groq import Groq
        client = Groq(api_key=key)
        messages = [{"role": "user", "content": prompt}]
        if system:
            messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        r = client.chat.completions.create(model=GROQ_MODEL, messages=messages, max_tokens=max_tokens)
        return (r.choices[0].message.content or "").strip()
    except Exception:
        return ""
