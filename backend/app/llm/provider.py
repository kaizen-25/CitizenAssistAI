"""Gemini -> Ollama -> None with one interface (SPEC §7.1). Implemented in Phase 2."""


def complete_json(system: str, user: str, json_schema: dict, timeout: int = 15) -> dict | None:
    raise NotImplementedError
