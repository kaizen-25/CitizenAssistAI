"""Deterministic income parser, then LLM extraction (SPEC §7.2). Implemented in Phase 5."""
from app.schemas import MessageResponse


def extract_profile(text: str, profile: dict, lang: str) -> MessageResponse:
    raise NotImplementedError
