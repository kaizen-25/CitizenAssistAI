"""Rule evaluation (SPEC §4.1). Deterministic and pure."""
import operator as op

from app.schemas import DECLINED, Condition, Rule, RuleResult

COMPARISONS = {
    "eq": op.eq,
    "neq": op.ne,
    "gt": op.gt,
    "gte": op.ge,
    "lt": op.lt,
    "lte": op.le,
    "in": lambda actual, expected: actual in expected,
    "not_in": lambda actual, expected: actual not in expected,
}


def is_known(profile: dict, field: str) -> bool:
    return profile.get(field) not in (None, DECLINED)


def evaluate_condition(cond: Condition, profile: dict) -> bool | None:
    """None means the field is missing or declined. Unknown is never a pass."""
    if not is_known(profile, cond.field):
        return None
    return bool(COMPARISONS[cond.operator](profile[cond.field], cond.value))


def evaluate_rule(rule: Rule, profile: dict) -> RuleResult:
    outcome, unknown_field = _outcome(rule, profile)
    return RuleResult(
        rule_id=rule.rule_id,
        outcome=outcome,
        source_excerpt=rule.source_excerpt,
        field=rule.field,
        operator=rule.operator,
        value=rule.value,
        unknown_field=unknown_field,
    )


def _outcome(rule: Rule, profile: dict) -> tuple[str, str | None]:
    if rule.kind == "manual_check":
        return "MANUAL", None

    if rule.applies_if is not None:
        applies = evaluate_condition(rule.applies_if, profile)
        if applies is None:
            return "UNKNOWN", rule.applies_if.field
        if not applies:
            return "NOT_APPLICABLE", None

    passed = evaluate_condition(Condition(field=rule.field, operator=rule.operator, value=rule.value), profile)
    if passed is None:
        return "UNKNOWN", rule.field
    return ("PASS" if passed else "FAIL"), None
