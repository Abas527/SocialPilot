"""Optional dense retrieval via Ollama embeddings. Disabled unless USE_EMBEDDINGS=1."""
import math

import httpx

from config import settings


def embed(text: str) -> list[float]:
    r = httpx.post(
        f"{settings.ollama_host}/api/embeddings",
        json={"model": settings.embed_model, "prompt": text},
        timeout=settings.llm_timeout_s,
    )
    r.raise_for_status()
    return r.json()["embedding"]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0
