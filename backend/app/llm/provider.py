"""Gemini -> Ollama -> None with one interface (SPEC §7.1)."""
import json
import logging
import urllib.error
import urllib.request
from collections.abc import Callable
from functools import lru_cache

from google import genai
from google.genai import types

from app.config import Settings, get_settings
from app.llm import cache

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434"
OLLAMA_CONTEXT = 8192


@lru_cache
def _gemini_client(api_key: str) -> genai.Client:
    # Held for the process: a garbage-collected client closes its transport mid-call.
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1)),
    )


def _call_gemini(settings: Settings, system: str, user: str, json_schema: dict, timeout: int) -> str:
    response = _gemini_client(settings.gemini_api_key).models.generate_content(
        model=settings.gemini_model,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_json_schema=json_schema,
            temperature=0,
            http_options=types.HttpOptions(timeout=timeout * 1000),
        ),
    )
    return response.text


def _call_ollama(settings: Settings, system: str, user: str, json_schema: dict, timeout: int) -> str:
    body = {
        "model": settings.ollama_model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "format": json_schema,  # a schema, not "json": plain JSON mode invents wrapper keys
        "stream": False,
        "think": False,
        # The default 4096 silently cuts the start of a prompt holding six excerpts.
        "options": {"temperature": 0, "num_ctx": OLLAMA_CONTEXT},
    }
    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        json.dumps(body).encode("utf-8"),
        {"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)["message"]["content"]


def _chain(settings: Settings) -> list[tuple[str, Callable]]:
    gemini = (f"gemini:{settings.gemini_model}", _call_gemini)
    ollama = (f"ollama:{settings.ollama_model}", _call_ollama)
    if settings.llm_provider == "gemini":
        return [gemini, ollama] if settings.gemini_api_key and settings.gemini_model else [ollama]
    if settings.llm_provider == "ollama":
        return [ollama]
    return []


def _parse(text: str) -> dict | None:
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def complete_json(system: str, user: str, json_schema: dict, timeout: int = 15) -> dict | None:
    settings = get_settings()
    prompt = json.dumps([system, user, json_schema], ensure_ascii=False, sort_keys=True)

    for name, call in _chain(settings):
        cached = cache.get(name, prompt)
        if cached is not None:
            return cached
        if settings.demo_mode:
            continue
        try:
            parsed = _parse(call(settings, system, user, json_schema, timeout))
        except Exception as error:
            logger.warning("%s failed: %s", name, type(error).__name__)
            continue
        if parsed is not None:
            cache.put(name, prompt, parsed)
            return parsed
        logger.warning("%s returned invalid JSON", name)
    return None


def _ollama_reachable() -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=1):
            return True
    except (urllib.error.URLError, OSError):
        return False


def is_available() -> bool:
    settings = get_settings()
    chain = _chain(settings)
    if not chain or settings.demo_mode:
        return bool(chain)
    return chain[0][0].startswith("gemini:") or _ollama_reachable()
