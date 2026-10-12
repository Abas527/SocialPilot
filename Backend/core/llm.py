"""Thin provider abstraction. One function in, text/JSON out."""
import json
import re
import time
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from config import settings

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    pass


def _transient(exc: Exception) -> bool:
    """Connection problems and 429/5xx are worth retrying; timeouts are not (they are slow)."""
    if isinstance(exc, httpx.TimeoutException):
        return False
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return isinstance(exc, httpx.TransportError)


def complete(
    prompt: str,
    system: str | None = None,
    json_mode: bool = False,
    json_schema: dict | None = None,
) -> str:
    attempts = max(0, settings.llm_max_retries) + 1
    for attempt in range(attempts):
        try:
            if settings.llm_provider == "ollama":
                return _ollama(prompt, system, json_mode, json_schema)
            if settings.llm_provider == "openai_compatible":
                return _openai(prompt, system, json_mode)
            raise LLMError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")
        except httpx.TimeoutException as e:
            raise LLMError("Model request timed out. Your existing work is preserved; retry.") from e
        except httpx.HTTPError as e:
            if attempt + 1 < attempts and _transient(e):
                time.sleep(settings.llm_retry_backoff_s * (2 ** attempt))
                continue
            raise LLMError(f"Model provider unavailable: {e}") from e
    raise LLMError("Model request failed.")  # pragma: no cover


def _ollama(
    prompt: str,
    system: str | None,
    json_mode: bool,
    json_schema: dict | None = None,
) -> str:
    messages = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": prompt}
    ]
    body = {
        "model": settings.llm_model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": settings.llm_temperature,
            "num_ctx": settings.llm_num_ctx,
        },
    }
    # Only Qwen3-family models are "thinking" models; qwen2.5(-coder) rejects the flag.
    if settings.llm_model.startswith("qwen3"):
        body["think"] = False
    if json_mode:
        body["format"] = json_schema or "json"
    r = httpx.post(f"{settings.ollama_host}/api/chat", json=body, timeout=settings.llm_timeout_s)
    r.raise_for_status()
    return r.json()["message"]["content"]


def _openai(prompt: str, system: str | None, json_mode: bool) -> str:
    messages = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": prompt}
    ]
    body: dict = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": settings.llm_temperature,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    r = httpx.post(
        f"{settings.openai_base_url}/chat/completions",
        json=body,
        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
        timeout=settings.llm_timeout_s,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _extract_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


def complete_text(prompt: str, system: str | None = None) -> str:
    """Plain (non-JSON) completion, trimmed; raises if the model returns nothing."""
    text = complete(prompt, system=system).strip()
    if not text:
        raise LLMError("Model returned an empty response.")
    return text


def complete_json(prompt: str, model_cls: type[T], system: str | None = None, retries: int = 2) -> T:
    """Call the model, parse into a Pydantic model; on invalid output, retry with the error."""
    last_err: Exception | None = None
    current = prompt
    for _ in range(retries + 1):
        raw = complete(
            current,
            system=system,
            json_mode=True,
            json_schema=model_cls.model_json_schema(),
        )
        try:
            return model_cls.model_validate(_extract_json(raw))
        except (json.JSONDecodeError, ValidationError) as e:
            last_err = e
            current = (
                f"{prompt}\n\nYour previous reply was invalid ({str(e)[:300]}). "
                f"Previous reply (truncated): {raw[:600]!r}\n"
                "Return ONLY a valid JSON object matching the schema."
            )
    raise LLMError(f"Model returned invalid structured output: {last_err}")
