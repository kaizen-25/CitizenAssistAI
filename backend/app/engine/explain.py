"""Template-based explanations, no LLM (SPEC §4.5). Implemented in Phase 1."""
from app.schemas import RuleResult


def explain_rule(rule_result: RuleResult, lang: str) -> str:
    raise NotImplementedError
