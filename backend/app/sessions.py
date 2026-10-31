"""In-memory session store (dict + 2-hour TTL) and the operations on a session."""
import time
import uuid
from dataclasses import dataclass, field

from app.config import load_documents, load_fields
from app.engine.eligibility import evaluate_all
from app.engine.explain import format_answer, localized
from app.engine.rules import evaluate_condition
from app.schemas import (
    DECLINED,
    AnswerSource,
    ChecklistItem,
    Labels,
    ProfileEntry,
    ProfileField,
    Progress,
    ResultGroups,
    Scheme,
    SchemeResult,
)

SESSION_TTL_SECONDS = 2 * 60 * 60


class SessionNotFound(Exception):
    pass


class InvalidAnswer(Exception):
    pass


@dataclass
class Session:
    session_id: str
    language: str
    answers: dict[str, ProfileEntry] = field(default_factory=dict)
    asked: set[str] = field(default_factory=set)
    documents: dict[str, str] = field(default_factory=dict)
    confirmed: bool = False
    last_used: float = field(default_factory=time.monotonic)

    @property
    def profile(self) -> dict:
        return {field_id: entry.value for field_id, entry in self.answers.items()}


_sessions: dict[str, Session] = {}


def _purge_expired() -> None:
    cutoff = time.monotonic() - SESSION_TTL_SECONDS
    for session_id in [s.session_id for s in _sessions.values() if s.last_used < cutoff]:
        del _sessions[session_id]


def create_session(language: str) -> Session:
    _purge_expired()
    session = Session(session_id=uuid.uuid4().hex, language=language)
    _sessions[session.session_id] = session
    return session


def get_session(session_id: str) -> Session:
    _purge_expired()
    session = _sessions.get(session_id)
    if session is None:
        raise SessionNotFound(session_id)
    session.last_used = time.monotonic()
    return session


def value_is_valid(value, field_def: ProfileField) -> bool:
    if value == DECLINED:
        return field_def.allow_prefer_not_to_say
    if field_def.type == "boolean":
        return isinstance(value, bool)
    if field_def.type == "enum":
        return value in [option.value for option in field_def.options or []]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if field_def.type == "integer" and int(value) != value:
        return False
    low, high = field_def.min, field_def.max
    return (low is None or value >= low) and (high is None or value <= high)


def set_answer(session: Session, field_id: str, value, source: AnswerSource = "answered") -> None:
    field_def = load_fields().get(field_id)
    if field_def is None:
        raise InvalidAnswer(f"Unknown field: {field_id}")
    if not value_is_valid(value, field_def):
        raise InvalidAnswer(f"Invalid value for {field_id}")
    session.answers[field_id] = ProfileEntry(value=value, source=source)
    session.asked.add(field_id)


def set_documents(session: Session, answers: dict[str, str]) -> None:
    unknown = set(answers) - set(load_documents())
    if unknown:
        raise InvalidAnswer(f"Unknown documents: {sorted(unknown)}")
    session.documents.update(answers)


def progress(session: Session) -> Progress:
    return Progress(answered=len(session.asked))


def readback(session: Session, lang: str) -> dict[str, ProfileEntry]:
    fields = load_fields()
    return {
        field_id: entry.model_copy(update={
            "label": localized(fields[field_id].label, lang),
            "display": format_answer(entry.value, fields[field_id], lang),
        })
        for field_id, entry in session.answers.items()
    }


def checklist(session: Session, schemes: list[Scheme], lang: str) -> list[ChecklistItem]:
    """Every document applicable to a scheme that is still open (SPEC §5)."""
    open_ids = {r.scheme_id for r in evaluate_all(schemes, session.profile, {}) if r.status != "not_eligible"}
    catalogue = load_documents()
    items: dict[str, ChecklistItem] = {}
    for scheme in schemes:
        if scheme.scheme_id not in open_ids:
            continue
        for entry in scheme.documents:
            applies = entry.applies_if is None or evaluate_condition(entry.applies_if, session.profile) is not False
            if applies and entry.document_id not in items:
                document = catalogue[entry.document_id]
                items[entry.document_id] = ChecklistItem(
                    document_id=entry.document_id,
                    label=localized(document.label, lang),
                    issued_by_hint=document.issued_by_hint,
                    answer=session.documents.get(entry.document_id),
                )
    return list(items.values())


def group_results(results: list[SchemeResult]) -> ResultGroups:
    groups = ResultGroups()
    for result in results:
        getattr(groups, result.status).append(result)
    return groups


def labels(lang: str) -> Labels:
    return Labels(
        fields={field_id: localized(f.label, lang) for field_id, f in load_fields().items()},
        documents={doc_id: localized(d.label, lang) for doc_id, d in load_documents().items()},
    )
