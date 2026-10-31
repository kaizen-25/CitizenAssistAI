from fastapi import APIRouter, HTTPException

from app.config import load_schemes
from app.llm.chat import answer_question
from app.schemas import ChatRequest, ChatResponse, Scheme

router = APIRouter()


@router.get("/schemes")
def list_schemes() -> list[Scheme]:
    return list(load_schemes())


@router.get("/schemes/{scheme_id}")
def get_scheme(scheme_id: str) -> Scheme:
    for scheme in load_schemes():
        if scheme.scheme_id == scheme_id:
            return scheme
    raise HTTPException(404, "Scheme not found")


@router.post("/chat")
def chat(request: ChatRequest) -> ChatResponse:
    return answer_question(request.question, request.language)
