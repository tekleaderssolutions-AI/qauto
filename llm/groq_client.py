"""OpenAI API client for cloud LLM (Render deployment)."""
import os
from typing import Optional

OPENAI_MODEL = "gpt-4.1-mini"


def generate(prompt: str, system: Optional[str] = None, max_tokens: int = 256) -> str:
    """Call OpenAI Chat Completions API. Returns empty string if key missing or error."""
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        return ""
    try:
        from openai import OpenAI

        client = OpenAI(api_key=key)
        messages = [{"role": "user", "content": prompt}]
        if system:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ]
        r = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            max_tokens=max_tokens,
        )
        return (r.choices[0].message.content or "").strip()
    except Exception:
        return ""
