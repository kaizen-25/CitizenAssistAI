"""Environment settings and verified-data loading."""
import json
import os
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.schemas import DocumentDef, ProfileField, Scheme

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "app" / "data"


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


def _flag(value: str) -> bool:
    return value.strip().lower() == "true"


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    gemini_api_key: str
    gemini_model: str
    ollama_model: str
    demo_mode: bool
    show_unverified: bool


@lru_cache
def get_settings() -> Settings:
    env = {**_read_env_file(REPO_ROOT / ".env"), **os.environ}
    return Settings(
        llm_provider=env.get("LLM_PROVIDER", "none"),
        gemini_api_key=env.get("GEMINI_API_KEY", ""),
        gemini_model=env.get("GEMINI_MODEL", ""),
        ollama_model=env.get("OLLAMA_MODEL", "qwen3:8b"),
        demo_mode=_flag(env.get("DEMO_MODE", "false")),
        show_unverified=_flag(env.get("SHOW_UNVERIFIED", "false")),
    )


def _read_data(name: str):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


@lru_cache
def load_fields() -> dict[str, ProfileField]:
    fields = (ProfileField.model_validate(record) for record in _read_data("profile_fields.json"))
    return {field.field_id: field for field in fields}


@lru_cache
def load_documents() -> dict[str, DocumentDef]:
    return {doc_id: DocumentDef.model_validate(record) for doc_id, record in _read_data("documents.json").items()}


@lru_cache
def load_schemes() -> tuple[Scheme, ...]:
    schemes = [Scheme.model_validate(record) for record in _read_data("schemes.json")]
    if get_settings().show_unverified:
        return tuple(schemes)
    return tuple(s for s in schemes if s.verification.status == "verified")


def verified_by_category(schemes: tuple[Scheme, ...]) -> dict[str, int]:
    return dict(Counter(s.category for s in schemes if s.verification.status == "verified"))
