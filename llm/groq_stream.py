"""Async streaming for Groq — yields SSE chunks for /api/chat/stream."""
import json
import os
from typing import AsyncGenerator

GROQ_MODEL = "llama-3.1-70b-versatile"


async def stream_groq(prompt: str, system: str | None = None, model: str = GROQ_MODEL) -> AsyncGenerator[str, None]:
    """Stream Groq API response as SSE data lines."""
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        yield f'data: {json.dumps({"error": "GROQ_API_KEY not set"})}\n\n'
        return
    messages = [{"role": "user", "content": prompt}]
    if system:
        messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
    try:
        import httpx
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "stream": True, "max_tokens": 512},
            ) as resp:
                if resp.status_code != 200:
                    yield f'data: {json.dumps({"error": f"Groq {resp.status_code}"})}\n\n'
                    return
                async for line in resp.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            obj = json.loads(line[6:])
                            delta = obj.get("choices", [{}])[0].get("delta", {})
                            token = delta.get("content", "")
                            if token:
                                yield f'data: {json.dumps({"response": token})}\n\n'
                        except json.JSONDecodeError:
                            pass
    except Exception as e:
        yield f'data: {json.dumps({"error": str(e)})}\n\n'
