"""Scheme status and document classification (SPEC §4.2, §4.3). Implemented in Phase 1."""
from app.schemas import Scheme, SchemeResult


def evaluate_scheme(scheme: Scheme, profile: dict, held_docs: dict) -> SchemeResult:
    raise NotImplementedError


def evaluate_all(schemes: list[Scheme], profile: dict, held_docs: dict) -> list[SchemeResult]:
    raise NotImplementedError
