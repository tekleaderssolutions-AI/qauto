"""Async streaming for Ollama — yields SSE chunks for /api/chat/stream."""
import json
from typing import AsyncGenerator

OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:7b"


async def stream_ollama(prompt: str, system: str | None = None, model: str = DEFAULT_MODEL) -> AsyncGenerator[str, None]:
    """Stream Ollama response as SSE data lines."""
    payload = {"model": model, "prompt": prompt, "stream": True, "options": {"num_predict": 512}}
    if system:
        payload["system"] = system
    try:
        import httpx
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", f"{OLLAMA_URL}/api/generate", json=payload) as resp:
                if resp.status_code != 200:
                    yield f"data: {json.dumps({'error': f'Ollama {resp.status_code}'})}\n\n"
                    return
                async for line in resp.aiter_lines():
                    if line.strip():
                        try:
                            obj = json.loads(line)
                            token = obj.get("response", "")
                            if token:
                                yield f"data: {json.dumps({'response': token})}\n\n"
                            if obj.get("done"):
                                break
                        except json.JSONDecodeError:
                            pass
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
