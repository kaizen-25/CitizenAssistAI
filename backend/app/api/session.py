from fastapi import APIRouter, Depends, Header, HTTPException

from app import sessions
from app.config import load_fields, load_schemes
from app.engine.eligibility import evaluate_all
from app.engine.explain import localize_report, localize_results
from app.engine.questions import question_for_field, select_next_question
from app.i18n import text
from app.llm.extract_profile import extract_profile
from app.schemas import (
    AnswerRequest,
    AnswerResponse,
    ChecklistResponse,
    ConfirmRequest,
    ConfirmResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    DocumentsRequest,
    MessageRequest,
    MessageResponse,
    OkResponse,
    PacketResponse,
    Question,
    ResultGroups,
    ResultsResponse,
    UnlockReport,
)
from app.sessions import InvalidAnswer, Session, SessionNotFound
from app.unlock.graph import calculate_unlocks

router = APIRouter(prefix="/session")


def current_session(session_id: str) -> Session:
    try:
        return sessions.get_session(session_id)
    except SessionNotFound:
        raise HTTPException(404, "Session not found or expired") from None


def language(session: Session = Depends(current_session), accept_language: str | None = Header(None)) -> str:
    tag = (accept_language or "").split(",")[0].split("-")[0].strip().lower()
    return tag if tag in ("en", "hi") else session.language


def require_confirmed(session: Session = Depends(current_session)) -> Session:
    if not session.confirmed:
        raise HTTPException(409, "Confirm your answers first")
    return session


def next_question(session: Session, lang: str) -> Question | None:
    return select_next_question(session.profile, list(load_schemes()), session.asked, lang)


def evaluated(session: Session):
    return evaluate_all(list(load_schemes()), session.profile, session.documents)


@router.post("")
def create_session(request: CreateSessionRequest) -> CreateSessionResponse:
    session = sessions.create_session(request.language)
    return CreateSessionResponse(session_id=session.session_id, first_question=next_question(session, request.language))


@router.post("/{session_id}/answer")
def answer(
    request: AnswerRequest,
    session: Session = Depends(current_session),
    lang: str = Depends(language),
) -> AnswerResponse:
    try:
        sessions.set_answer(session, request.field_id, request.value)
    except InvalidAnswer as error:
        raise HTTPException(422, str(error)) from None
    return AnswerResponse(
        profile=sessions.readback(session, lang),
        next_question=next_question(session, lang),
        progress=sessions.progress(session),
    )


@router.post("/{session_id}/message")
def message(
    request: MessageRequest,
    session: Session = Depends(current_session),
    lang: str = Depends(language),
) -> MessageResponse:
    extracted, clarification = extract_profile(request.text, session.profile, lang)
    for field in extracted:
        sessions.set_answer(session, field.field_id, field.value, "extracted")
    return MessageResponse(
        extracted=extracted,
        clarification=clarification,
        profile=sessions.readback(session, lang),
        next_question=next_question(session, lang),
    )


@router.get("/{session_id}/question/{field_id}")
def question(
    field_id: str,
    session: Session = Depends(current_session),
    lang: str = Depends(language),
) -> Question:
    if field_id not in load_fields():
        raise HTTPException(404, "Unknown field")
    return question_for_field(field_id, session.profile, list(load_schemes()), lang)


@router.get("/{session_id}/documents")
def get_documents(session: Session = Depends(current_session), lang: str = Depends(language)) -> ChecklistResponse:
    return ChecklistResponse(documents=sessions.checklist(session, list(load_schemes()), lang))


@router.post("/{session_id}/documents")
def post_documents(request: DocumentsRequest, session: Session = Depends(current_session)) -> OkResponse:
    try:
        sessions.set_documents(session, request.root)
    except InvalidAnswer as error:
        raise HTTPException(422, str(error)) from None
    return OkResponse(ok=True)


@router.post("/{session_id}/confirm")
def confirm(request: ConfirmRequest, session: Session = Depends(current_session)) -> ConfirmResponse:
    try:
        for field_id, value in (request.profile_overrides or {}).items():
            sessions.set_answer(session, field_id, value, "override")
    except InvalidAnswer as error:
        raise HTTPException(422, str(error)) from None
    session.confirmed = True
    return ConfirmResponse(confirmed=True)


@router.get("/{session_id}/results")
def results(session: Session = Depends(current_session), lang: str = Depends(language)) -> ResultsResponse:
    groups = sessions.group_results(localize_results(evaluated(session), lang)) if session.confirmed else ResultGroups()
    return ResultsResponse(
        confirmed=session.confirmed,
        profile=sessions.readback(session, lang),
        groups=groups,
        labels=sessions.labels(lang),
    )


@router.get("/{session_id}/unlock")
def unlock(session: Session = Depends(require_confirmed), lang: str = Depends(language)) -> UnlockReport:
    return localize_report(calculate_unlocks(evaluated(session)), lang)


@router.get("/{session_id}/packet")
def packet(session: Session = Depends(require_confirmed), lang: str = Depends(language)) -> PacketResponse:
    results_now = evaluated(session)
    return PacketResponse(
        profile=sessions.readback(session, lang),
        groups=sessions.group_results(localize_results(results_now, lang)),
        unlock=localize_report(calculate_unlocks(results_now), lang),
        labels=sessions.labels(lang),
        disclaimer=text(lang, "disclaimer"),
    )
