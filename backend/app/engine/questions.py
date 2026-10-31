"""Adaptive question selection (SPEC §5, §14.11)."""
from app.config import load_fields
from app.engine.eligibility import evaluate_all
from app.engine.explain import field_option_label, localized
from app.i18n import text
from app.schemas import DECLINED, MAX_QUESTIONS, ProfileField, Question, QuestionOption, Scheme


def select_next_question(profile: dict, schemes: list[Scheme], asked: set[str], lang: str) -> Question | None:
    if len(asked) >= MAX_QUESTIONS:
        return None

    open_results = [r for r in evaluate_all(schemes, profile, {}) if r.status != "not_eligible"]
    if not open_results:
        return None

    fields = load_fields()
    scores: dict[str, int] = {}
    for result in open_results:
        for field_id in result.unknown_fields:
            if field_id not in profile and field_id not in asked:
                scores[field_id] = scores.get(field_id, 0) + 1

    if "state" not in profile and "state" not in asked:
        return _build_question(fields["state"], scores.get("state", 0), lang)
    if not scores:
        return None

    best = min(scores, key=lambda field_id: (-scores[field_id], fields[field_id].ask_priority, field_id))
    return _build_question(fields[best], scores[best], lang)


def question_for_field(field_id: str, profile: dict, schemes: list[Scheme], lang: str) -> Question:
    """The question for one chosen field, used by "Answer now"."""
    results = [r for r in evaluate_all(schemes, profile, {}) if r.status != "not_eligible"]
    return _build_question(load_fields()[field_id], sum(field_id in r.unknown_fields for r in results), lang)


def _build_question(field: ProfileField, score: int, lang: str) -> Question:
    options = [QuestionOption(value=o.value, label=field_option_label(o, lang)) for o in field.options or []]
    if field.allow_prefer_not_to_say:
        options.append(QuestionOption(value=DECLINED, label=text(lang, "prefer_not_to_say")))
    return Question(
        field_id=field.field_id,
        question_text=localized(field.question, lang),
        answer_type=field.type,
        options=options,
        schemes_affected=score,
        reason=text(lang, "question_reason").format(n=score),
    )
