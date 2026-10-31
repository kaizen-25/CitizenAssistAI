import pytest

from app.engine.rules import evaluate_condition, evaluate_rule
from app.schemas import DECLINED, Condition, Rule


def hard_rule(field="age", operator="gte", value=18, applies_if=None):
    return Rule(rule_id="r", field=field, operator=operator, value=value, applies_if=applies_if, kind="hard", source_excerpt="x")


ENROLLED = Condition(field="currently_enrolled", operator="eq", value=True)


@pytest.mark.parametrize(
    "operator, expected, actual, result",
    [
        ("eq", "Punjab", "Punjab", True),
        ("eq", "Punjab", "Other", False),
        ("eq", True, True, True),
        ("eq", True, False, False),
        ("neq", "salaried", "farmer", True),
        ("neq", "salaried", "salaried", False),
        ("gt", 59, 60, True),
        ("gt", 59, 59, False),
        ("gte", 18, 18, True),
        ("gte", 18, 17, False),
        ("lt", 30, 29, True),
        ("lt", 30, 30, False),
        ("lte", 250000, 250000, True),
        ("lte", 250000, 250001, False),
        ("in", ["SC", "ST"], "SC", True),
        ("in", ["SC", "ST"], "OBC", False),
        ("not_in", ["General"], "SC", True),
        ("not_in", ["General"], "General", False),
    ],
)
def test_every_operator(operator, expected, actual, result):
    cond = Condition(field="f", operator=operator, value=expected)
    assert evaluate_condition(cond, {"f": actual}) is result


@pytest.mark.parametrize("profile", [{}, {"age": None}, {"age": DECLINED}])
@pytest.mark.parametrize("operator, value", [("gte", 18), ("neq", 18), ("not_in", [18])])
def test_condition_on_unknown_field_is_none(profile, operator, value):
    assert evaluate_condition(Condition(field="age", operator=operator, value=value), profile) is None


def test_false_answer_is_known_not_unknown():
    assert evaluate_condition(ENROLLED, {"currently_enrolled": False}) is False


def test_zero_is_known_not_unknown():
    assert evaluate_condition(Condition(field="age", operator="gte", value=18), {"age": 0}) is False


# §4.1, row by row


def test_row_manual_check_is_manual():
    rule = Rule(rule_id="r", kind="manual_check", source_excerpt="attendance")
    assert evaluate_rule(rule, {}).outcome == "MANUAL"


def test_row_manual_check_precedes_applies_if():
    rule = Rule(rule_id="r", kind="manual_check", source_excerpt="attendance", applies_if=ENROLLED)
    assert evaluate_rule(rule, {"currently_enrolled": False}).outcome == "MANUAL"


def test_row_unknown_applies_if_reports_the_condition_field():
    result = evaluate_rule(hard_rule(applies_if=ENROLLED), {"age": 20})
    assert (result.outcome, result.unknown_field) == ("UNKNOWN", "currently_enrolled")


def test_row_unknown_applies_if_wins_when_rule_field_is_also_unknown():
    result = evaluate_rule(hard_rule(applies_if=ENROLLED), {})
    assert (result.outcome, result.unknown_field) == ("UNKNOWN", "currently_enrolled")


def test_row_false_applies_if_is_not_applicable():
    result = evaluate_rule(hard_rule(applies_if=ENROLLED), {"currently_enrolled": False, "age": 5})
    assert (result.outcome, result.unknown_field) == ("NOT_APPLICABLE", None)


def test_row_missing_field_is_unknown():
    result = evaluate_rule(hard_rule(), {})
    assert (result.outcome, result.unknown_field) == ("UNKNOWN", "age")


def test_row_declined_field_is_unknown():
    result = evaluate_rule(hard_rule(), {"age": DECLINED})
    assert (result.outcome, result.unknown_field) == ("UNKNOWN", "age")


def test_row_declined_applies_if_is_unknown():
    result = evaluate_rule(hard_rule(applies_if=ENROLLED), {"currently_enrolled": DECLINED, "age": 20})
    assert (result.outcome, result.unknown_field) == ("UNKNOWN", "currently_enrolled")


def test_row_true_comparison_passes():
    assert evaluate_rule(hard_rule(), {"age": 18}).outcome == "PASS"


def test_row_false_comparison_fails():
    assert evaluate_rule(hard_rule(), {"age": 17}).outcome == "FAIL"


def test_true_applies_if_falls_through_to_comparison():
    assert evaluate_rule(hard_rule(applies_if=ENROLLED), {"currently_enrolled": True, "age": 17}).outcome == "FAIL"


def test_result_carries_what_explanations_need():
    result = evaluate_rule(hard_rule(), {"age": 20})
    assert (result.rule_id, result.field, result.operator, result.value, result.source_excerpt) == ("r", "age", "gte", 18, "x")
