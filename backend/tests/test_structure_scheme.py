import json
import sys

import pytest

from app.config import DATA_DIR, REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "scripts"))

import structure_scheme as tool  # noqa: E402
import verify  # noqa: E402

FIELDS = {f["field_id"]: f for f in json.loads((DATA_DIR / "profile_fields.json").read_text(encoding="utf-8"))}
FIELD_LIST = list(FIELDS.values())
DOCUMENTS = json.loads((DATA_DIR / "documents.json").read_text(encoding="utf-8"))

SOURCE_TEXT = """SYNTHETIC Scholarship guideline.
Family income should not exceed Rs. 2.5 lakh per annum.  The
applicant must be a resident of Punjab. Students must have 75 percent attendance.
Applicants must submit an income certificate. Apply at https://example.invalid/apply today.
Selection is at the discretion of the committee."""

SOURCE = {"url": "https://example.invalid/g", "title": "T", "published": None, "retrieved_on": "2026-11-01", "file": "sources/x.txt"}


def hard(field="annual_family_income", operator="lte", value="250000", excerpt="Family income should not exceed Rs. 2.5 lakh per annum.", **extra):
    return {"kind": "hard", "field": field, "operator": operator, "value_json": value, "source_excerpt": excerpt, **extra}


def raw(**overrides):
    return {
        "name": "SYNTHETIC", "level": "central", "category": "education", "department": "D", "summary": "S", "benefits": "B",
        "rules": [hard()],
        "documents": [{"document_id": "income_certificate", "source_text": "an income certificate", "requirement": "mandatory"}],
        "application_url": "https://example.invalid/apply",
        "application_mode": ["online"],
        **overrides,
    }


def sanitize(**overrides):
    return tool.sanitize_draft(raw(**overrides), SOURCE_TEXT, "edu_001", SOURCE, FIELDS, DOCUMENTS)


def test_clean_draft_keeps_its_rule_and_stays_unverified():
    draft = sanitize()

    assert draft["rules"][0] == {
        "rule_id": "edu_001_r1", "field": "annual_family_income", "operator": "lte", "value": 250000,
        "applies_if": None, "kind": "hard", "source_excerpt": "Family income should not exceed Rs. 2.5 lakh per annum.",
    }
    assert draft["verification"] == {"status": "unverified", "verified_by": None, "verified_on": None}
    assert draft["_review_notes"] == []


def test_status_can_never_come_from_the_llm():
    draft = sanitize(verification={"status": "verified", "verified_by": "llm"})

    assert draft["verification"]["status"] == "unverified"


def test_invented_excerpt_is_rejected_and_not_shown_to_citizens():
    draft = sanitize(rules=[hard(excerpt="Family income must be below 3 lakh.")])

    assert draft["rules"] == []
    assert draft["unmapped_conditions"] == []
    assert "not verbatim" in draft["_review_notes"][0]


def test_excerpt_match_tolerates_line_breaks_only():
    draft = sanitize(rules=[hard("state", "eq", '"Punjab"', "per annum. The applicant must be a resident of Punjab.")])

    assert len(draft["rules"]) == 1


def test_number_missing_from_its_excerpt_goes_to_unmapped():
    draft = sanitize(rules=[hard(value="300000")])

    assert draft["rules"] == []
    assert draft["unmapped_conditions"] == ["Family income should not exceed Rs. 2.5 lakh per annum."]
    assert "300000" in draft["_review_notes"][0]


@pytest.mark.parametrize(
    "value, text, expected",
    [
        (250000, "not exceed Rs. 2.5 lakh", True),
        (250000, "up to 2.50 lakhs", True),
        (250000, "₹2,50,000 per year", True),
        (250000, "Rs 2,50,000/-", True),
        (250000, "2.5 lacs", True),
        (250000, "should not exceed Rs.2.50 lakh per annum", True),
        (250000, "exceed Rs.2,50,000/- per annum", True),
        (100000, "1 lakh", True),
        (60000, "60 thousand", True),
        (18, "aged 18 years", True),
        (250000, "2.6 lakh", False),
        (18, "aged 180 years", False),
        (18, "1.18 percent", False),
        (75, "175 days", False),
        (250000, "12.5 lakh", False),
    ],
)
def test_number_in_text(value, text, expected):
    assert tool.number_in_text(value, text) is expected


def test_unregistered_field_goes_to_unmapped():
    draft = sanitize(rules=[hard("shoe_size", "lte", "250000")])

    assert draft["rules"] == []
    assert len(draft["unmapped_conditions"]) == 1


def test_enum_value_outside_options_goes_to_unmapped():
    draft = sanitize(rules=[hard("state", "eq", '"Atlantis"', "applicant must be a resident of Punjab")])

    assert draft["rules"] == []


def test_unparseable_value_goes_to_unmapped():
    draft = sanitize(rules=[hard(value="2.5 lakh")])

    assert draft["rules"] == []
    assert "not valid JSON" in draft["_review_notes"][0]


def test_applies_if_is_rebuilt_from_flat_fields():
    draft = sanitize(rules=[hard(applies_if_field="currently_enrolled", applies_if_operator="eq", applies_if_value_json="true")])

    assert draft["rules"][0]["applies_if"] == {"field": "currently_enrolled", "operator": "eq", "value": True}


def test_manual_check_keeps_only_its_excerpt():
    rule = {"kind": "manual_check", "field": "x", "source_excerpt": "Students must have 75 percent attendance."}

    assert sanitize(rules=[rule])["rules"] == [
        {"rule_id": "edu_001_r1", "kind": "manual_check", "source_excerpt": "Students must have 75 percent attendance."}
    ]


def test_url_not_in_source_is_dropped():
    draft = sanitize(application_url="https://fake.invalid/apply")

    assert draft["application_url"] is None
    assert "fake.invalid" in draft["_review_notes"][0]


def test_url_in_source_is_kept():
    assert sanitize()["application_url"] == "https://example.invalid/apply"


def test_invented_unmapped_condition_is_dropped():
    draft = sanitize(unmapped_conditions=["Selection is at the discretion of the committee.", "Applicants need a blue pen."])

    assert draft["unmapped_conditions"] == ["Selection is at the discretion of the committee."]
    assert "blue pen" in draft["_review_notes"][0]


def test_unknown_document_is_kept_for_the_reader_not_invented_as_an_id():
    draft = sanitize(documents=[{"document_id": "library_card", "source_text": "an income certificate", "requirement": "mandatory"}])

    assert draft["documents"] == []
    assert draft["unmapped_conditions"] == ["Document: an income certificate"]


def test_duplicate_documents_collapse():
    entry = {"document_id": "income_certificate", "source_text": "an income certificate", "requirement": "mandatory"}

    assert len(sanitize(documents=[entry, entry])["documents"]) == 1


def test_state_scheme_without_state_rule_is_flagged():
    assert "§14.8" in sanitize(level="state")["_review_notes"][0]


def test_html_source_drops_scripts_and_keeps_links(tmp_path):
    page = tmp_path / "s.html"
    page.write_text('<script>evil()</script><p>Income up to 2 lakh</p><a href="https://example.invalid/a">Apply</a>', encoding="utf-8")

    text = tool.read_source(page)

    assert "Income up to 2 lakh" in text
    assert "https://example.invalid/a" in text
    assert "evil" not in text


def test_prompt_contains_registry_and_source():
    prompt = tool.build_user_prompt(SOURCE_TEXT, FIELD_LIST, DOCUMENTS)

    assert "annual_family_income (number, unit INR_per_year)" in prompt
    assert "income_certificate: Income Certificate" in prompt
    assert "2.5 lakh" in prompt


# verify.py


def publishable():
    draft = sanitize()
    draft["application_mode"] = ["online"]
    return draft


def test_clean_draft_has_no_blockers():
    assert verify.blockers(publishable(), SOURCE_TEXT, [], FIELD_LIST, DOCUMENTS) == []


def test_tampered_excerpt_blocks_publishing():
    draft = publishable()
    draft["rules"][0]["source_excerpt"] = "Family income should not exceed Rs. 9 lakh per annum."

    assert "not in the source" in verify.blockers(draft, SOURCE_TEXT, [], FIELD_LIST, DOCUMENTS)[0]


def test_duplicate_scheme_blocks_publishing():
    draft = publishable()
    found = verify.blockers(draft, SOURCE_TEXT, [{**draft, "scheme_id": "edu_001", "rules": []}], FIELD_LIST, DOCUMENTS)

    assert any("already in schemes.json" in reason for reason in found)


def test_draft_with_no_rules_blocks_publishing():
    draft = publishable()
    draft["rules"] = []

    assert "no rules" in verify.blockers(draft, SOURCE_TEXT, [], FIELD_LIST, DOCUMENTS)[0]


def test_publish_sets_verification_and_strips_notes(tmp_path):
    path = tmp_path / "schemes.json"
    path.write_text("[]", encoding="utf-8")

    verify.publish(publishable(), "claude", path, "2026-11-01")

    record = json.loads(path.read_text(encoding="utf-8"))[0]
    assert record["verification"] == {"status": "verified", "verified_by": "claude", "verified_on": "2026-11-01"}
    assert "_review_notes" not in record


def test_focus_names_the_one_scheme_and_start_slices_the_source():
    prompt = tool.build_user_prompt(SOURCE_TEXT, FIELD_LIST, DOCUMENTS, focus="Scheme X", start="Selection is")

    assert "Structure ONLY this one: Scheme X" in prompt
    assert "Selection is at the discretion" in prompt
    assert "2.5 lakh" not in prompt
