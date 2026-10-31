import copy
import json

import pytest
from pydantic import ValidationError

from app.config import DATA_DIR
from app.schemas import DocumentDef, ProfileField, Rule, Scheme

SPEC_EXAMPLE = {
    "scheme_id": "syn_a",
    "name": {"en": "SYNTHETIC scheme"},
    "level": "central",
    "state": None,
    "category": "education",
    "department": "SYNTHETIC",
    "summary": "SYNTHETIC",
    "benefits": "SYNTHETIC",
    "rules": [
        {
            "rule_id": "syn_a_r1",
            "field": "annual_family_income",
            "operator": "lte",
            "value": 250000,
            "applies_if": None,
            "kind": "hard",
            "source_excerpt": "SYNTHETIC excerpt",
        },
        {
            "rule_id": "syn_a_r2",
            "field": "course_level",
            "operator": "in",
            "value": ["post_matric", "undergraduate"],
            "applies_if": {"field": "currently_enrolled", "operator": "eq", "value": True},
            "kind": "hard",
            "source_excerpt": "SYNTHETIC excerpt",
        },
    ],
    "documents": [
        {"document_id": "income_certificate", "requirement": "mandatory", "applies_if": None},
        {
            "document_id": "caste_certificate",
            "requirement": "mandatory",
            "applies_if": {"field": "social_category", "operator": "in", "value": ["SC", "ST", "OBC"]},
        },
    ],
    "unmapped_conditions": [],
    "application_url": "https://example.invalid/apply",
    "application_mode": ["online"],
    "source": {"url": "https://example.invalid", "title": "SYNTHETIC", "published": None, "retrieved_on": "2026-11-01", "file": None},
    "verification": {"status": "verified", "verified_by": "XX", "verified_on": "2026-11-01"},
}


def test_spec_shaped_scheme_parses_with_exact_value_types():
    scheme = Scheme.model_validate(copy.deepcopy(SPEC_EXAMPLE))

    assert scheme.rules[0].value == 250000 and type(scheme.rules[0].value) is int
    assert scheme.rules[1].applies_if.value is True


def test_hard_rule_without_field_is_rejected():
    with pytest.raises(ValidationError):
        Rule(rule_id="r", kind="hard", source_excerpt="x")


def test_manual_check_needs_no_field():
    rule = Rule(rule_id="r", kind="manual_check", source_excerpt="attendance of at least 75%")

    assert rule.field is None


def test_seed_files_match_models():
    fields = json.loads((DATA_DIR / "profile_fields.json").read_text(encoding="utf-8"))
    documents = json.loads((DATA_DIR / "documents.json").read_text(encoding="utf-8"))

    parsed = [ProfileField.model_validate(field) for field in fields]
    for definition in documents.values():
        DocumentDef.model_validate(definition)

    assert len({field.field_id for field in parsed}) == len(parsed)
    assert {f.field_id for f in parsed if f.sensitive} == {"gender", "social_category", "has_disability"}
    assert all(f.allow_prefer_not_to_say for f in parsed if f.sensitive)
    assert len({f.ask_priority for f in parsed}) == len(parsed)


def test_no_issued_by_hint_beyond_the_human_supplied_one():
    documents = json.loads((DATA_DIR / "documents.json").read_text(encoding="utf-8"))

    hinted = {doc_id for doc_id, doc in documents.items() if doc["issued_by_hint"]}
    assert hinted == {"income_certificate"}
