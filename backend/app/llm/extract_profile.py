"""Deterministic income parser, then LLM extraction (SPEC §7.2)."""
import json
import re
from dataclasses import dataclass

from app.config import load_fields, load_schemes
from app.engine.explain import localized
from app.i18n import text as i18n_text
from app.llm.provider import complete_json
from app.schemas import ExtractedField, ProfileField
from app.sessions import value_is_valid

INCOME_FIELD = "annual_family_income"
LAKH = 100000

DIGITS = str.maketrans("०१२३४५६७८९੦੧੨੩੪੫੬੭੮੯", "01234567890123456789")
NUMBER_WORDS = {
    "डेढ़": 1.5, "डेढ": 1.5, "ढाई": 2.5, "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5, "पाँच": 5,
    "छह": 6, "छः": 6, "सात": 7, "आठ": 8, "नौ": 9, "दस": 10, "बीस": 20, "तीस": 30,
    "ਡੇਢ": 1.5, "ਢਾਈ": 2.5, "ਇੱਕ": 1, "ਦੋ": 2, "ਤਿੰਨ": 3, "ਚਾਰ": 4, "ਪੰਜ": 5, "ਛੇ": 6,
    "ਸੱਤ": 7, "ਅੱਠ": 8, "ਨੌਂ": 9, "ਦਸ": 10, "ਵੀਹ": 20, "ਤੀਹ": 30,
}
WORD_PATTERN = "|".join(sorted(map(re.escape, NUMBER_WORDS), key=len, reverse=True))
NUMBER = rf"(?:\d[\d,]*(?:\.\d+)?|{WORD_PATTERN})"
LAKH_UNIT = r"lakhs?|lacs?|लाख|ਲੱਖ"
THOUSAND_UNIT = r"thousand|हज़ार|हजार|ਹਜ਼ਾਰ|k\b"
UNIT = rf"{LAKH_UNIT}|{THOUSAND_UNIT}"
CURRENCY = r"(?:₹|rs\.?|inr|रु\.?|रुपये|रुपए|ਰੁਪਏ)"
MONTHLY = r"(?:/\s*month|/\s*mo\b|per month|a month|monthly|p\.?\s?m\.?\b|every month|महीना|महीने|मासिक|हर महीने|ਮਹੀਨਾ|ਮਹੀਨੇ)"
INCOME_WORD = r"(?:income|earn|salary|आय|आमदनी|कमाई|ਆਮਦਨ|ਕਮਾਈ)"

RANGE = re.compile(
    rf"({NUMBER})\s*(?:{UNIT})?\s*(?:-|–|—|to|or|se|से|या|ਤੋਂ|ਜਾਂ)\s*({NUMBER})\s*(?:{UNIT})",
    re.IGNORECASE,
)
AMOUNT_WITH_UNIT = re.compile(rf"(?:{CURRENCY}\s*)?({NUMBER})\s*({UNIT})", re.IGNORECASE)
AMOUNT_WITH_CURRENCY = re.compile(rf"{CURRENCY}\s*(\d[\d,]*(?:\.\d+)?)", re.IGNORECASE)
AMOUNT_AFTER_INCOME = re.compile(rf"{INCOME_WORD}\D{{0,20}}?(\d[\d,]{{3,}}(?:\.\d+)?)", re.IGNORECASE)
AGE = re.compile(
    r"(?:\b(?:i am|i'm|im|aged?|age is)\s+(?:around\s+)?(\d{1,3})\b(?!\s*(?:lakh|lac|k\b|thousand)))"
    r"|(?:\b(\d{1,3})\s*(?:years?|yrs?|साल|वर्ष|ਸਾਲ))",
    re.IGNORECASE,
)
NEGATION = re.compile(r"\b(?:no|not|don't|dont|never|without|none)\b|नहीं|ना\b|ਨਹੀਂ", re.IGNORECASE)
AGE_RANGE = re.compile(r"\b(\d{1,3})\s*(?:or|to|-|–|या|ਜਾਂ)\s*(\d{1,3})\s*(?:years?|yrs?|साल|ਸਾਲ)?", re.IGNORECASE)

SYSTEM_PROMPT = """You extract facts a citizen stated about themselves into JSON. Never guess or infer.
- Use only the listed fields. A value on an enum field must be one of its options.
- Leave out every field the message does not mention. Silence about something is not a "no".
- evidence must be the exact words from the user's message.
- explicit is true only when the user stated the fact directly, not when it is implied.
- value_json holds JSON: 19, true or "Punjab".
- Saying you study in a class or course states that currently_enrolled is true.
- If the message is ambiguous about a field, such as a range, list it in ambiguous_fields and leave it out of fields.
- The message may be in English, Hindi or Punjabi."""

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "fields": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "field_id": {"type": "string"},
                    "value_json": {"type": "string"},
                    "evidence": {"type": "string"},
                    "explicit": {"type": "boolean"},
                },
                "required": ["field_id", "value_json", "evidence", "explicit"],
            },
        },
        "ambiguous_fields": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["fields", "ambiguous_fields"],
}


@dataclass
class IncomeParse:
    value: float | None = None
    evidence: str = ""
    monthly: bool = False
    ambiguous: bool = False


def _to_number(token: str) -> float:
    return NUMBER_WORDS[token] if token in NUMBER_WORDS else float(token.replace(",", ""))


def _scale(unit: str) -> int:
    return LAKH if re.fullmatch(LAKH_UNIT, unit, re.IGNORECASE) else 1000


def parse_income(raw: str) -> IncomeParse:
    text = raw.translate(DIGITS)

    range_match = RANGE.search(text)
    if range_match and _to_number(range_match[1]) != _to_number(range_match[2]):
        return IncomeParse(ambiguous=True, evidence=range_match[0])

    amount, match = None, None
    if unit_match := AMOUNT_WITH_UNIT.search(text):
        match, amount = unit_match, _to_number(unit_match[1]) * _scale(unit_match[2])
    elif currency_match := AMOUNT_WITH_CURRENCY.search(text):
        match, amount = currency_match, _to_number(currency_match[1])
    elif income_match := AMOUNT_AFTER_INCOME.search(text):
        match, amount = income_match, _to_number(income_match[1])
    if amount is None:
        return IncomeParse()

    monthly = bool(re.search(MONTHLY, text[match.start():match.end() + 25], re.IGNORECASE))
    return IncomeParse(value=amount * 12 if monthly else amount, evidence=match[0], monthly=monthly)


def _rule_fields() -> set[str]:
    """Fields a verified rule reads. Asking for others only invites wrong values on the confirm screen."""
    rules = [rule for scheme in load_schemes() for rule in scheme.rules]
    return {rule.field for rule in rules if rule.field} | {rule.applies_if.field for rule in rules if rule.applies_if}


def _prompt_fields(fields: dict[str, ProfileField], skip: set[str]) -> str:
    lines = []
    used = _rule_fields()
    for field in fields.values():
        if field.field_id in skip or field.field_id not in used:
            continue
        options = ""
        if field.options:
            options = ", options: " + "; ".join(f"{o.value} means {localized(o.label, 'en')}" for o in field.options)
        lines.append(f"- {field.field_id} ({field.type}{options})")
    return "\n".join(lines)


def _decode(raw: str, field: ProfileField):
    """Models often leave strings unquoted in value_json: Punjab, not "Punjab"."""
    try:
        value = json.loads(raw)
    except ValueError:
        value = raw.strip()
    if field.options and isinstance(value, str):
        return next((option.value for option in field.options if option.value.casefold() == value.casefold()), value)
    return value


def _validated(raw_fields: list, text: str, fields: dict[str, ProfileField]) -> list[ExtractedField]:
    kept = []
    for raw in raw_fields:
        field = fields.get(raw.get("field_id"))
        evidence = (raw.get("evidence") or "").strip()
        if field is None or not evidence or evidence.casefold() not in text.casefold():
            continue
        if (field.sensitive or field.type == "boolean") and not raw.get("explicit"):
            continue
        value = _decode(raw.get("value_json") or "null", field)
        if value is None or isinstance(value, (list, dict)) or not value_is_valid(value, field):
            continue
        if value is False and not NEGATION.search(evidence):
            continue
        kept.append(ExtractedField(field_id=field.field_id, value=value, evidence=evidence, explicit=bool(raw.get("explicit"))))
    return kept


def _clarification(field_id: str, fields: dict[str, ProfileField], lang: str) -> str:
    return i18n_text(lang, "clarify_field").format(label=localized(fields[field_id].label, lang))


def extract_profile(text: str, profile: dict, lang: str) -> tuple[list[ExtractedField], str | None]:
    """Return (validated fields, a clarification question or None). Ambiguity never picks a value."""
    fields = load_fields()
    extracted: list[ExtractedField] = []
    clarification = None

    income = parse_income(text)
    if income.ambiguous:
        clarification = _clarification(INCOME_FIELD, fields, lang)
    elif income.value is not None:
        note = i18n_text(lang, "income_monthly_note") if income.monthly else None
        extracted.append(ExtractedField(field_id=INCOME_FIELD, value=income.value, evidence=income.evidence, explicit=True, note=note))

    age_range = AGE_RANGE.search(text.translate(DIGITS))
    if age_range and clarification is None and not income.evidence and age_range[1] != age_range[2]:
        clarification = _clarification("age", fields, lang)

    if clarification is None and "age" not in profile and (age := AGE.search(text.translate(DIGITS))):
        value = int(age[1] or age[2])
        if value_is_valid(value, fields["age"]):
            extracted.append(ExtractedField(field_id="age", value=value, evidence=age[0], explicit=True))

    skip = set(profile) | {INCOME_FIELD, "age"}
    user = f"Fields:\n{_prompt_fields(fields, skip)}\n\nMessage:\n{text}"
    response = complete_json(SYSTEM_PROMPT, user, EXTRACTION_SCHEMA)
    if response:
        extracted += [f for f in _validated(response.get("fields", []), text, fields) if f.field_id not in skip]
        ambiguous = [f for f in response.get("ambiguous_fields", []) if f in fields and f not in skip]
        if ambiguous and clarification is None:
            clarification = _clarification(ambiguous[0], fields, lang)
    return extracted, clarification
