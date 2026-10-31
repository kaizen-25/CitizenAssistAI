"""Adaptive question selection (SPEC §5). Implemented in Phase 1."""
from app.schemas import Question, Scheme


def select_next_question(profile: dict, schemes: list[Scheme], asked: set[str], lang: str) -> Question | None:
    raise NotImplementedError
