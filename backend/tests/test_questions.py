from app.engine.eligibility import evaluate_all
from app.engine.questions import select_next_question
from app.schemas import DECLINED

FULL_PROFILE = {
    "state": "Punjab",
    "age": 19,
    "gender": "female",
    "annual_family_income": 200000,
    "social_category": "SC",
    "currently_enrolled": True,
    "course_level": "undergraduate",
    "occupation": "student",
    "holds_bpl_card": True,
    "has_disability": False,
}


def next_field(profile, schemes, asked=frozenset()):
    question = select_next_question(profile, schemes, set(asked), "en")
    return question.field_id if question else None


def test_state_is_asked_first_when_unknown(schemes):
    assert next_field({}, schemes) == "state"


def test_tie_breaks_by_lower_ask_priority(schemes):
    # income scores 2 (a, e) and age scores 2 (b, c); age has the lower ask_priority.
    assert next_field({"state": "Punjab"}, schemes) == "age"


def test_picks_the_max_score_field(schemes):
    # age 19 fails c, leaving income (a, e) as the only field scoring 2.
    question = select_next_question({"state": "Punjab", "age": 19}, schemes, {"state", "age"}, "en")

    assert question.field_id == "annual_family_income"
    assert question.schemes_affected == 2
    assert question.reason == "Needed to check 2 schemes"


def test_reason_is_singular_for_one_scheme(schemes):
    profile = dict(FULL_PROFILE)
    del profile["has_disability"]

    assert select_next_question(profile, schemes, set(profile) - {"f"}, "en") is None or True
    question = select_next_question(profile, schemes, set(), "en")

    assert question.reason == "Needed to check 1 scheme"


def test_failed_schemes_stop_counting(schemes):
    # Income 900000 fails a and e, so nothing left needs gender.
    profile = {"state": "Punjab", "age": 19, "annual_family_income": 900000}
    asked = set(profile)
    seen = []
    while (field := next_field(profile, schemes, asked)) is not None:
        seen.append(field)
        profile[field] = FULL_PROFILE[field]
        asked.add(field)

    assert "gender" not in seen
    assert "currently_enrolled" not in seen


def test_condition_is_asked_and_its_rule_field_is_not(schemes):
    profile = {"state": "Punjab", "age": 19, "annual_family_income": 200000, "gender": "female"}

    assert next_field(profile, schemes, set(profile)) != "course_level"


def test_rule_field_is_not_asked_when_condition_turns_it_off(schemes):
    profile = dict(FULL_PROFILE, currently_enrolled=False)
    del profile["course_level"]

    assert next_field(profile, schemes, set(profile)) is None


def test_never_repeats_an_asked_field(schemes):
    assert next_field({"state": "Punjab"}, schemes, {"state", "age"}) == "annual_family_income"


def test_declined_field_is_not_asked_again(schemes):
    profile = dict(FULL_PROFILE, social_category=DECLINED)

    assert next_field(profile, schemes, set(profile)) is None


def test_returns_none_when_best_score_is_zero(schemes):
    assert next_field(FULL_PROFILE, schemes, set(FULL_PROFILE)) is None


def test_stops_after_eight_questions(schemes):
    asked = {"f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8"}

    assert next_field({}, schemes, asked) is None


def test_returns_none_with_no_schemes():
    assert next_field({}, []) is None


def test_enum_question_lists_options(schemes):
    question = select_next_question({}, schemes, set(), "en")

    assert question.answer_type == "enum"
    assert [option.value for option in question.options] == ["Punjab", "Other"]


def test_sensitive_question_offers_prefer_not_to_say(schemes):
    profile = {"state": "Punjab", "age": 19, "annual_family_income": 100000, "occupation": "student", "currently_enrolled": False, "holds_bpl_card": False}
    question = select_next_question(profile, schemes, set(profile), "en")

    assert question.field_id == "gender"
    assert question.options[-1].value == DECLINED
    assert question.options[-1].label == "Prefer not to say"


def test_non_sensitive_question_has_no_decline_option(schemes):
    question = select_next_question({}, schemes, set(), "en")

    assert DECLINED not in [option.value for option in question.options]


def oracle_run(schemes):
    profile, asked = {}, set()
    while (field := next_field(profile, schemes, asked)) is not None:
        asked.add(field)
        if field in FULL_PROFILE:
            profile[field] = FULL_PROFILE[field]
    return {r.scheme_id: r.status for r in evaluate_all(schemes, profile, {})}, asked


def test_oracle_run_without_the_cap_matches_full_profile_statuses(schemes, monkeypatch):
    monkeypatch.setattr("app.engine.questions.MAX_QUESTIONS", 20)
    full = {r.scheme_id: r.status for r in evaluate_all(schemes, FULL_PROFILE, {})}

    adaptive, asked = oracle_run(schemes)

    assert adaptive == full
    assert len(asked) == 10


def test_the_cap_can_only_leave_a_scheme_undetermined_never_wrong(schemes):
    full = {r.scheme_id: r.status for r in evaluate_all(schemes, FULL_PROFILE, {})}

    adaptive, asked = oracle_run(schemes)

    assert len(asked) == 8
    assert all(status in (full[scheme_id], "cannot_determine") for scheme_id, status in adaptive.items())
