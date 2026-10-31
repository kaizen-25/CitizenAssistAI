"""Template-based explanations and labels, no LLM (SPEC §4.5, §14.10)."""
from app.config import load_documents, load_fields
from app.i18n import text
from app.schemas import DECLINED, FieldOption, Localized, ProfileField, RuleResult, SchemeResult, UnlockReport


def format_inr(amount: float) -> str:
    whole, _, fraction = f"{amount:.2f}".partition(".")
    last_three, rest = whole[-3:], whole[:-3]
    groups = []
    while rest:
        groups.insert(0, rest[-2:])
        rest = rest[:-2]
    grouped = ",".join([*groups, last_three])
    return f"₹{grouped}" if fraction == "00" else f"₹{grouped}.{fraction}"


def localized(value: Localized, lang: str) -> str:
    return getattr(value, lang) or value.en


def field_option_label(option: FieldOption, lang: str) -> str:
    return localized(option.label, lang)


def _format_scalar(value, field: ProfileField, lang: str) -> str:
    if isinstance(value, bool):
        return text(lang, "yes" if value else "no")
    if field.unit == "INR_per_year":
        return format_inr(value)
    for option in field.options or []:
        if option.value == value:
            return field_option_label(option, lang)
    return str(value)


def _format_value(value, field: ProfileField, lang: str) -> str:
    if isinstance(value, list):
        return ", ".join(_format_scalar(item, field, lang) for item in value)
    return _format_scalar(value, field, lang)


def format_answer(value, field: ProfileField, lang: str) -> str:
    """A profile value for read-back. Declined is shown as such, never as a value."""
    return text(lang, "prefer_not_to_say") if value == DECLINED else _format_value(value, field, lang)


def explain_rule(rule_result: RuleResult, lang: str) -> str:
    if rule_result.field is None or rule_result.operator is None:
        return rule_result.source_excerpt
    field = load_fields()[rule_result.field]
    return text(lang, "operators", rule_result.operator).format(
        label=localized(field.label, lang),
        value=_format_value(rule_result.value, field, lang),
    )


def localize_results(results: list[SchemeResult], lang: str) -> list[SchemeResult]:
    return [
        result.model_copy(
            update={"rules": [r.model_copy(update={"explanation": explain_rule(r, lang)}) for r in result.rules]}
        )
        for result in results
    ]


def localize_report(report: UnlockReport, lang: str) -> UnlockReport:
    documents = load_documents()
    ranking = [
        entry.model_copy(update={"label": localized(documents[entry.document_id].label, lang)})
        for entry in report.ranking
    ]
    return report.model_copy(update={"ranking": ranking})
