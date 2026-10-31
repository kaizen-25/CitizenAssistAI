import pytest

from app.engine.explain import explain_rule, format_inr, localize_report, localize_results
from app.engine.eligibility import evaluate_all
from app.schemas import RuleResult, UnlockRankingEntry, UnlockReport


@pytest.mark.parametrize(
    "amount, text",
    [
        (0, "₹0"),
        (999, "₹999"),
        (1000, "₹1,000"),
        (99999, "₹99,999"),
        (100000, "₹1,00,000"),
        (250000, "₹2,50,000"),
        (2500000, "₹25,00,000"),
        (10000000, "₹1,00,00,000"),
        (250000.0, "₹2,50,000"),
        (1234.5, "₹1,234.50"),
    ],
)
def test_indian_number_formatting(amount, text):
    assert format_inr(amount) == text


def result(field, operator, value, outcome="PASS"):
    return RuleResult(rule_id="r", outcome=outcome, source_excerpt="official words", field=field, operator=operator, value=value)


def test_income_rule_uses_rupee_format():
    assert explain_rule(result("annual_family_income", "lte", 250000), "en") == "Annual family income must be at most ₹2,50,000"


def test_age_rule_uses_plain_number():
    assert explain_rule(result("age", "gte", 18), "en") == "Age must be at least 18"


def test_enum_value_uses_its_label():
    assert explain_rule(result("residence_area", "eq", "rural"), "en") == "Area of residence must be Rural"


def test_list_value_joins_labels():
    text = explain_rule(result("course_level", "in", ["post_matric", "undergraduate"]), "en")

    assert text == "Course level must be one of: Class 11, 12, ITI or diploma, Undergraduate"


def test_boolean_value_is_yes_or_no():
    assert explain_rule(result("holds_bpl_card", "eq", True), "en") == "Holds a BPL card must be Yes"


def test_manual_check_shows_the_official_excerpt():
    manual = RuleResult(rule_id="r", outcome="MANUAL", source_excerpt="attendance of 75 percent")

    assert explain_rule(manual, "en") == "attendance of 75 percent"


def test_blank_hindi_falls_back_to_english_with_the_same_number():
    assert "₹2,50,000" in explain_rule(result("annual_family_income", "lte", 250000), "hi")


def test_localize_results_fills_every_rule_without_touching_the_input(schemes):
    results = evaluate_all(schemes, {}, {})
    localized = localize_results(results, "en")

    assert all(rule.explanation for item in localized for rule in item.rules)
    assert results[0].rules[0].explanation == ""


def test_localize_report_adds_document_labels():
    entry = UnlockRankingEntry(document_id="income_certificate", label="", rank=1, required_by=["a"], sole_blocker_for=["a"])
    report = UnlockReport(ranking=[entry])

    assert localize_report(report, "hi").ranking[0].label == "आय प्रमाण पत्र"
    assert localize_report(report, "en").ranking[0].label == "Income Certificate"
    assert report.ranking[0].label == ""
