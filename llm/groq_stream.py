"""Async streaming for OpenAI — yields SSE chunks for /api/chat/stream."""
import json
import os
from typing import AsyncGenerator

from openai import AsyncOpenAI

OPENAI_MODEL = "gpt-4.1-mini"


async def stream_groq(prompt: str, system: str | None = None, model: str = OPENAI_MODEL) -> AsyncGenerator[str, None]:
    """Stream OpenAI Chat Completions response as SSE data lines."""
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        yield f'data: {json.dumps({"error": "OPENAI_API_KEY not set"})}\n\n'
        return
    messages = [{"role": "user", "content": prompt}]
    if system:
        messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
    try:
        client = AsyncOpenAI(api_key=key)
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=512,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            token = delta.content or ""
            if token:
                yield f'data: {json.dumps({"response": token})}\n\n'
    except Exception as e:
        yield f'data: {json.dumps({"error": str(e)})}\n\n'
