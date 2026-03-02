"""Async OpenAI client for non-streaming chat completions."""
import os
from typing import Optional

from openai import AsyncOpenAI

OPENAI_MODEL = "gpt-4.1-mini"


async def generate_async(prompt: str, system: Optional[str] = None, max_tokens: int = 256) -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        return ""
    messages = [{"role": "user", "content": prompt}]
    if system:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
    try:
        client = AsyncOpenAI(api_key=key)
        resp = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            stream=False,
        )
        content = (resp.choices[0].message.content or "").strip()
        return content
    except Exception:
        return ""

