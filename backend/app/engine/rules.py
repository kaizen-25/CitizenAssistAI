"""Rule evaluation (SPEC §4.1). Implemented in Phase 1."""
from app.schemas import Condition, Rule, RuleResult


def evaluate_condition(cond: Condition, profile: dict) -> bool | None:
    raise NotImplementedError


def evaluate_rule(rule: Rule, profile: dict) -> RuleResult:
    raise NotImplementedError
