"""Document Unlock Plan (SPEC §6). Deterministic and pure."""
from app.schemas import PendingInfo, SchemeResult, UnlockPlanStep, UnlockRankingEntry, UnlockReport


def calculate_unlocks(results: list[SchemeResult]) -> UnlockReport:
    """Labels are left blank; localize_report adds them for the session language (SPEC §14.10)."""
    eligible = [r for r in results if r.status == "potentially_eligible"]
    blockers = {
        r.scheme_id: set(r.documents.missing + r.documents.unsure)
        for r in eligible
        if not r.document_ready
    }
    return UnlockReport(
        ready_now=[r.scheme_id for r in eligible if r.document_ready],
        ranking=_rank(blockers),
        plan=_plan(blockers),
        pending_info=[
            PendingInfo(
                scheme_id=r.scheme_id,
                unknown_fields=r.unknown_fields,
                missing_documents=r.documents.missing + r.documents.unsure,
            )
            for r in results
            if r.status == "cannot_determine"
        ],
    )


def _required_by(document_id: str, blockers: dict[str, set[str]]) -> list[str]:
    return [scheme_id for scheme_id, documents in blockers.items() if document_id in documents]


def _sole_blocker_for(document_id: str, blockers: dict[str, set[str]]) -> list[str]:
    return [scheme_id for scheme_id, documents in blockers.items() if documents == {document_id}]


def _rank(blockers: dict[str, set[str]]) -> list[UnlockRankingEntry]:
    counted = sorted(
        (
            (-len(_required_by(doc, blockers)), -len(_sole_blocker_for(doc, blockers)), doc)
            for doc in set().union(*blockers.values())
        )
    )
    entries, previous, rank = [], None, 0
    for position, (required, sole, doc) in enumerate(counted, start=1):
        if (required, sole) != previous:
            rank, previous = position, (required, sole)
        entries.append(
            UnlockRankingEntry(
                document_id=doc,
                label="",
                rank=rank,
                required_by=_required_by(doc, blockers),
                sole_blocker_for=_sole_blocker_for(doc, blockers),
            )
        )
    return entries


def _plan(blockers: dict[str, set[str]]) -> list[UnlockPlanStep]:
    remaining = {scheme_id: set(documents) for scheme_id, documents in blockers.items()}
    steps: list[UnlockPlanStep] = []
    cumulative = 0
    while remaining:
        doc = min(
            set().union(*remaining.values()),
            key=lambda d: (-len(_sole_blocker_for(d, remaining)), -len(_required_by(d, remaining)), d),
        )
        newly_ready = _sole_blocker_for(doc, remaining)
        cumulative += len(newly_ready)
        steps.append(
            UnlockPlanStep(step=len(steps) + 1, document_id=doc, newly_ready=newly_ready, cumulative_ready=cumulative)
        )
        for scheme_id in newly_ready:
            del remaining[scheme_id]
        for documents in remaining.values():
            documents.discard(doc)
    return steps
