"""Operator templates, status labels and refusals. A blank translation falls back to English."""
import json
from functools import lru_cache
from pathlib import Path


@lru_cache
def _load(lang: str) -> dict:
    return json.loads((Path(__file__).parent / f"{lang}.json").read_text(encoding="utf-8"))


def _lookup(strings: dict, keys: tuple[str, ...]) -> str:
    for key in keys:
        strings = strings[key]
    return strings


def text(lang: str, *keys: str) -> str:
    return _lookup(_load(lang), keys) or _lookup(_load("en"), keys)
