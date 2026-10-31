import pytest

from app.llm import extract_profile as module
from app.llm.extract_profile import extract_profile, parse_income


@pytest.mark.parametrize(
    "text, value",
    [
        ("2 lakh", 200000),
        ("2.5 lac", 250000),
        ("income is 2.5 lakhs", 250000),
        ("₹2,00,000", 200000),
        ("Rs. 1,50,000 a year", 150000),
        ("my family income is 180000", 180000),
        ("दो लाख", 200000),
        ("ढाई लाख", 250000),
        ("२ लाख", 200000),
        ("ਦੋ ਲੱਖ", 200000),
        ("60 thousand", 60000),
        ("50k", 50000),
    ],
)
def test_annual_income(text, value):
    parsed = parse_income(text)

    assert (parsed.value, parsed.monthly, parsed.ambiguous) == (value, False, False)


@pytest.mark.parametrize(
    "text, value",
    [
        ("20k/month", 240000),
        ("20k per month", 240000),
        ("₹15,000 monthly", 180000),
        ("15 हज़ार महीना", 180000),
        ("ਵੀਹ ਹਜ਼ਾਰ ਮਹੀਨਾ", 240000),
    ],
)
def test_monthly_income_is_multiplied_and_flagged(text, value):
    parsed = parse_income(text)

    assert (parsed.value, parsed.monthly) == (value, True)


@pytest.mark.parametrize("text", ["2-3 lakh", "2–3 lakh", "2 to 3 lakh", "2 or 3 lakh", "दो या तीन लाख", "2 से 3 लाख", "ਦੋ ਜਾਂ ਤਿੰਨ ਲੱਖ"])
def test_ranges_are_ambiguous_and_pick_no_value(text):
    parsed = parse_income(text)

    assert parsed.ambiguous is True
    assert parsed.value is None


@pytest.mark.parametrize("text", ["I am 19", "class 12", "I study in Ludhiana", "20 years old", "दो बहनें"])
def test_non_income_text_gives_nothing(text):
    parsed = parse_income(text)

    assert (parsed.value, parsed.ambiguous) == (None, False)


def fake_llm(monkeypatch, response):
    monkeypatch.setattr(module, "complete_json", lambda *args, **kwargs: response)


def field(field_id, value_json, evidence, explicit=True):
    return {"field_id": field_id, "value_json": value_json, "evidence": evidence, "explicit": explicit}


def test_the_prompt_asks_only_for_fields_a_rule_reads_and_explains_options(monkeypatch):
    seen = []
    monkeypatch.setattr(module, "complete_json", lambda system, user, schema: seen.append(user))

    extract_profile("hello", {}, "en")

    assert "education_level" not in seen[0]
    assert "pre_matric means Up to class 10" in seen[0]


def test_unquoted_string_values_are_kept(monkeypatch):
    fake_llm(monkeypatch, {"fields": [field("state", "Punjab", "Punjab"), field("marital_status", "widowed", "widow")], "ambiguous_fields": []})

    extracted, _ = extract_profile("I am a widow from Punjab", {}, "en")

    assert {f.field_id: f.value for f in extracted} == {"state": "Punjab", "marital_status": "widowed"}


def test_quoted_string_values_and_other_casing_match_the_option(monkeypatch):
    fake_llm(monkeypatch, {"fields": [field("state", '"punjab"', "Punjab")], "ambiguous_fields": []})

    extracted, _ = extract_profile("I live in Punjab", {}, "en")

    assert extracted[0].value == "Punjab"


def test_an_unquoted_value_outside_the_options_is_dropped(monkeypatch):
    fake_llm(monkeypatch, {"fields": [field("state", "Atlantis", "Atlantis")], "ambiguous_fields": []})

    assert extract_profile("I live in Atlantis", {}, "en")[0] == []


def test_income_comes_from_the_parser_even_if_the_llm_disagrees(monkeypatch):
    fake_llm(monkeypatch, {"fields": [field("annual_family_income", "999999", "2 lakh")], "ambiguous_fields": []})

    extracted, _ = extract_profile("family income 2 lakh", {}, "en")

    assert [(f.field_id, f.value) for f in extracted] == [("annual_family_income", 200000)]


def test_monthly_income_carries_a_note(monkeypatch):
    fake_llm(monkeypatch, None)

    extracted, _ = extract_profile("I earn 20k/month", {}, "en")

    assert extracted[0].value == 240000
    assert "12" in extracted[0].note


def test_no_llm_still_parses_income(monkeypatch):
    fake_llm(monkeypatch, None)

    extracted, clarification = extract_profile("income 2 lakh", {}, "en")

    assert [f.value for f in extracted] == [200000]
    assert clarification is None


def test_ambiguous_income_asks_instead_of_choosing(monkeypatch):
    fake_llm(monkeypatch, {"fields": [], "ambiguous_fields": []})

    extracted, clarification = extract_profile("income is 2-3 lakh", {}, "en")

    assert extracted == []
    assert "Annual family income" in clarification


def test_ambiguous_age_asks_instead_of_choosing(monkeypatch):
    fake_llm(monkeypatch, {"fields": [field("age", "18", "18 or 19")], "ambiguous_fields": []})

    extracted, clarification = extract_profile("I am around 18 or 19", {}, "en")

    assert extracted == []
    assert "Age" in clarification


def test_llm_flagged_ambiguity_becomes_a_clarification(monkeypatch):
    fake_llm(monkeypatch, {"fields": [], "ambiguous_fields": ["occupation"]})

    _, clarification = extract_profile("I do some work", {}, "en")

    assert "Occupation" in clarification


def test_unregistered_field_is_dropped(monkeypatch):
    fake_llm(monkeypatch, {"fields": [field("shoe_size", "9", "size 9")], "ambiguous_fields": []})

    assert extract_profile("size 9", {}, "en")[0] == []


def test_evidence_not_in_the_message_is_dropped(monkeypatch):
    fake_llm(monkeypatch, {"fields": [field("age", "19", "I am nineteen")], "ambiguous_fields": []})

    assert extract_profile("hello", {}, "en")[0] == []


def test_value_out_of_range_is_dropped(monkeypatch):
    fake_llm(monkeypatch, {"fields": [field("age", "500", "500")], "ambiguous_fields": []})

    assert extract_profile("500", {}, "en")[0] == []


def test_enum_value_outside_options_is_dropped(monkeypatch):
    fake_llm(monkeypatch, {"fields": [field("state", '"Atlantis"', "Atlantis")], "ambiguous_fields": []})

    assert extract_profile("Atlantis", {}, "en")[0] == []


def test_implied_sensitive_field_is_dropped(monkeypatch):
    fake_llm(monkeypatch, {"fields": [field("gender", '"female"', "my husband", explicit=False)], "ambiguous_fields": []})

    assert extract_profile("my husband works", {}, "en")[0] == []


def test_stated_sensitive_field_is_kept(monkeypatch):
    fake_llm(monkeypatch, {"fields": [field("gender", '"female"', "I am a woman")], "ambiguous_fields": []})

    assert [f.value for f in extract_profile("I am a woman", {}, "en")[0]] == ["female"]


def test_implied_non_sensitive_field_is_kept(monkeypatch):
    fake_llm(monkeypatch, {"fields": [field("state", '"Punjab"', "Ludhiana", explicit=False)], "ambiguous_fields": []})

    assert [f.value for f in extract_profile("I live in Ludhiana", {}, "en")[0]] == ["Punjab"]


def test_already_answered_fields_are_not_overwritten(monkeypatch):
    fake_llm(monkeypatch, {"fields": [field("age", "30", "30")], "ambiguous_fields": []})

    assert extract_profile("30", {"age": 19}, "en")[0] == []


@pytest.mark.parametrize(
    "text, age",
    [("I am 19", 19), ("I'm 19, in college", 19), ("age 45", 45), ("19 years old", 19), ("मैं 19 साल की हूँ", 19), ("मेरी उम्र १९ साल है", 19), ("ਮੈਂ 19 ਸਾਲ ਦੀ ਹਾਂ", 19)],
)
def test_age_is_parsed_without_an_llm(monkeypatch, text, age):
    fake_llm(monkeypatch, None)

    assert [(f.field_id, f.value) for f in extract_profile(text, {}, "en")[0]] == [("age", age)]


def test_income_figure_is_not_mistaken_for_an_age(monkeypatch):
    fake_llm(monkeypatch, None)

    assert [f.field_id for f in extract_profile("I am 2 lakh in debt, family income 2 lakh", {}, "en")[0]] == ["annual_family_income"]


def test_silence_is_not_a_no(monkeypatch):
    fake_llm(monkeypatch, {"fields": [field("holds_bpl_card", "false", "my mother works")], "ambiguous_fields": []})

    assert extract_profile("my mother works", {}, "en")[0] == []


def test_a_stated_no_is_kept(monkeypatch):
    fake_llm(monkeypatch, {"fields": [field("holds_bpl_card", "false", "we do not have a BPL card")], "ambiguous_fields": []})

    assert [f.value for f in extract_profile("we do not have a BPL card", {}, "en")[0]] == [False]


def test_implied_boolean_is_dropped(monkeypatch):
    fake_llm(monkeypatch, {"fields": [field("currently_enrolled", "true", "my college", explicit=False)], "ambiguous_fields": []})

    assert extract_profile("near my college", {}, "en")[0] == []
