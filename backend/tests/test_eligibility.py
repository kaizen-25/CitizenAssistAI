import pytest

from app.engine.eligibility import evaluate_all, evaluate_scheme
from app.schemas import DECLINED, Scheme

ELIGIBLE_FOR_A = {"annual_family_income": 100000, "currently_enrolled": False, "social_category": "SC"}
ALL_DOCS_FOR_A = {"income_certificate": "have", "caste_certificate": "have", "passport_photo": "have"}


def rule(rule_id, field, operator, value):
    return {"rule_id": rule_id, "field": field, "operator": operator, "value": value, "kind": "hard", "source_excerpt": "x"}


def with_rules(base: Scheme, *rules) -> Scheme:
    return base.model_copy(update={"rules": [base.rules[0].model_validate(r) for r in rules], "documents": []})


# §4.2 status precedence


def test_fail_outranks_unknown(by_id):
    scheme = with_rules(by_id["syn_a"], rule("a", "age", "gte", 18), rule("b", "state", "eq", "Punjab"))
    assert evaluate_scheme(scheme, {"age": 10}, {}).status == "not_eligible"


def test_unknown_without_fail_cannot_determine(by_id):
    scheme = with_rules(by_id["syn_a"], rule("a", "age", "gte", 18), rule("b", "state", "eq", "Punjab"))
    assert evaluate_scheme(scheme, {"age": 20}, {}).status == "cannot_determine"


def test_all_pass_is_potentially_eligible(by_id):
    scheme = with_rules(by_id["syn_a"], rule("a", "age", "gte", 18), rule("b", "state", "eq", "Punjab"))
    assert evaluate_scheme(scheme, {"age": 20, "state": "Punjab"}, {}).status == "potentially_eligible"


def test_manual_rules_do_not_block_status_and_are_listed(by_id):
    result = evaluate_scheme(by_id["syn_a"], ELIGIBLE_FOR_A, ALL_DOCS_FOR_A)

    assert result.status == "potentially_eligible"
    assert result.manual_checks == ["SYNTHETIC attendance of at least 75 percent"]


def test_not_applicable_rule_does_not_block(by_id):
    assert evaluate_scheme(by_id["syn_a"], ELIGIBLE_FOR_A, {}).rules[1].outcome == "NOT_APPLICABLE"


def test_declined_value_gives_cannot_determine_and_names_the_field(by_id):
    result = evaluate_scheme(by_id["syn_e"], {"gender": DECLINED, "annual_family_income": 100000}, {})

    assert result.status == "cannot_determine"
    assert result.unknown_fields == ["gender"]


def test_unknown_fields_are_unique(by_id):
    assert evaluate_scheme(by_id["syn_b"], {"occupation": "farmer"}, {}).unknown_fields == ["age"]


# §4.3 documents are separate from eligibility


@pytest.mark.parametrize("answer", ["have", "missing", "unsure", None])
@pytest.mark.parametrize(
    "profile",
    [
        ELIGIBLE_FOR_A,
        {"currently_enrolled": False},
        {"annual_family_income": 900000, "currently_enrolled": False},
    ],
)
def test_missing_document_never_changes_status(by_id, profile, answer):
    docs = {} if answer is None else {key: answer for key in ALL_DOCS_FOR_A}

    assert evaluate_scheme(by_id["syn_a"], profile, docs).status == evaluate_scheme(by_id["syn_a"], profile, ALL_DOCS_FOR_A).status


def test_documents_are_classified_by_answer(by_id):
    result = evaluate_scheme(
        by_id["syn_a"],
        ELIGIBLE_FOR_A,
        {"income_certificate": "have", "caste_certificate": "missing", "passport_photo": "missing"},
    )

    assert result.documents.held == ["income_certificate"]
    assert result.documents.missing == ["caste_certificate"]
    assert result.documents.optional_missing == ["passport_photo"]


def test_unsure_is_kept_apart_from_missing(by_id):
    result = evaluate_scheme(by_id["syn_a"], ELIGIBLE_FOR_A, {**ALL_DOCS_FOR_A, "caste_certificate": "unsure"})

    assert result.documents.unsure == ["caste_certificate"]
    assert result.documents.missing == []
    assert result.document_ready is False


def test_unanswered_document_counts_as_unsure(by_id):
    documents = evaluate_scheme(by_id["syn_b"], {}, {}).documents

    assert documents.unsure == ["income_certificate", "bank_passbook"]
    assert documents.missing == []


def test_conditional_document_is_skipped_when_condition_is_false(by_id):
    profile = {**ELIGIBLE_FOR_A, "social_category": "General"}
    result = evaluate_scheme(by_id["syn_a"], profile, {"income_certificate": "have"})

    assert "caste_certificate" not in result.documents.unsure + result.documents.possibly_required
    assert result.document_ready is True


def test_conditional_document_is_possibly_required_when_condition_is_unknown(by_id):
    profile = {"annual_family_income": 100000, "currently_enrolled": False}
    result = evaluate_scheme(by_id["syn_a"], profile, {"income_certificate": "have"})

    assert result.documents.possibly_required == ["caste_certificate"]


def test_possibly_required_alone_does_not_block_document_ready(by_id):
    profile = {"annual_family_income": 100000, "currently_enrolled": False}

    assert evaluate_scheme(by_id["syn_a"], profile, {"income_certificate": "have"}).document_ready is True


def test_optional_document_never_blocks_document_ready(by_id):
    docs = {"income_certificate": "have", "caste_certificate": "have", "passport_photo": "missing"}

    assert evaluate_scheme(by_id["syn_a"], ELIGIBLE_FOR_A, docs).document_ready is True


def test_document_ready_requires_potentially_eligible(by_id):
    result = evaluate_scheme(by_id["syn_b"], {"age": 20}, {"income_certificate": "have", "bank_passbook": "have"})

    assert result.status == "cannot_determine"
    assert result.document_ready is False


# §4.4 result shape


def test_result_carries_source_and_conditions(by_id):
    result = evaluate_scheme(by_id["syn_a"], ELIGIBLE_FOR_A, {})

    assert result.source.url == "https://example.invalid/source/syn_a"
    assert result.application_url == "https://example.invalid/syn_a"
    assert result.unmapped_conditions == ["SYNTHETIC condition that could not be encoded"]


def test_evaluate_all_keeps_scheme_order(schemes):
    assert [r.scheme_id for r in evaluate_all(schemes, {}, {})] == [s.scheme_id for s in schemes]
