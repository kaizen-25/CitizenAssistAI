"""Disk cache keyed by a hash of (provider, prompt) (SPEC §7.1). Implemented in Phase 2."""


def get(provider: str, prompt: str) -> dict | None:
    raise NotImplementedError


def put(provider: str, prompt: str, response: dict) -> None:
    raise NotImplementedError
