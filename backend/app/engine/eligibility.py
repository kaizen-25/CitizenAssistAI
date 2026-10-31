"""Scheme status and document classification (SPEC §4.2, §4.3). Deterministic and pure."""
from app.engine.rules import evaluate_condition, evaluate_rule
from app.schemas import DocumentBuckets, ResultSource, RuleResult, Scheme, SchemeResult, SchemeStatus


def evaluate_scheme(scheme: Scheme, profile: dict, held_docs: dict) -> SchemeResult:
    rules = [evaluate_rule(rule, profile) for rule in scheme.rules]
    status = _status(rules)
    documents = _classify_documents(scheme, profile, held_docs)
    return SchemeResult(
        scheme_id=scheme.scheme_id,
        name=scheme.name.en,
        department=scheme.department,
        status=status,
        rules=rules,
        unknown_fields=list(dict.fromkeys(r.unknown_field for r in rules if r.unknown_field)),
        manual_checks=[r.source_excerpt for r in rules if r.outcome == "MANUAL"],
        documents=documents,
        document_ready=status == "potentially_eligible" and not documents.missing and not documents.unsure,
        unmapped_conditions=scheme.unmapped_conditions,
        source=ResultSource(url=scheme.source.url, title=scheme.source.title, retrieved_on=scheme.source.retrieved_on),
        application_url=scheme.application_url,
    )


def evaluate_all(schemes: list[Scheme], profile: dict, held_docs: dict) -> list[SchemeResult]:
    return [evaluate_scheme(scheme, profile, held_docs) for scheme in schemes]


def _status(rules: list[RuleResult]) -> SchemeStatus:
    outcomes = {rule.outcome for rule in rules}
    if "FAIL" in outcomes:
        return "not_eligible"
    if "UNKNOWN" in outcomes:
        return "cannot_determine"
    return "potentially_eligible"


def _classify_documents(scheme: Scheme, profile: dict, held_docs: dict) -> DocumentBuckets:
    buckets = DocumentBuckets()
    for entry in scheme.documents:
        applies = True if entry.applies_if is None else evaluate_condition(entry.applies_if, profile)
        if applies is False:
            continue
        if applies is None:
            buckets.possibly_required.append(entry.document_id)
            continue

        answer = held_docs.get(entry.document_id)
        if answer == "have":
            buckets.held.append(entry.document_id)
        elif entry.requirement == "optional":
            buckets.optional_missing.append(entry.document_id)
        elif answer == "missing":
            buckets.missing.append(entry.document_id)
        else:
            buckets.unsure.append(entry.document_id)
    return buckets
