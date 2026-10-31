"""Disk cache keyed by a hash of (provider, prompt) (SPEC §7.1)."""
import hashlib
import json
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parents[2] / ".llm_cache"


def _path(provider: str, prompt: str) -> Path:
    digest = hashlib.sha256(f"{provider}\0{prompt}".encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{digest}.json"


def get(provider: str, prompt: str) -> dict | None:
    path = _path(provider, prompt)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def put(provider: str, prompt: str, response: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _path(provider, prompt).write_text(json.dumps(response, ensure_ascii=False), encoding="utf-8")
