"""Grounded Q&A with code-level post-validation (SPEC §7.3)."""
import re

from app.config import load_schemes
from app.i18n import text
from app.llm.provider import complete_json
from app.retrieval.bm25 import MIN_SCORE, search
from app.schemas import ChatResponse, Citation

DIGITS = str.maketrans("०१२३४५६७८९੦੧੨੩੪੫੬੭੮੯", "01234567890123456789")
CITATION = re.compile(r"\[([\w.-]+)\]")
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
URL = re.compile(r"https?://[^\s)\]>\"']+|www\.[^\s)\]>\"']+")

ANSWER_SYSTEM = """Answer the citizen's question using ONLY the numbered excerpts.
- Put the excerpt's id in square brackets after every claim, like [edu_001_c0].
- Never use outside knowledge. Never add a number, date, fee or URL that is not in a cited excerpt.
- If the excerpts do not answer the question, reply with an empty answer.
- Reply in the requested language."""
ANSWER_SCHEMA = {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"]}

TRANSLATE_SYSTEM = "Translate the user's question into English. Keep scheme names as they are."
TRANSLATE_SCHEMA = {"type": "object", "properties": {"english": {"type": "string"}}, "required": ["english"]}


def _numbers(value: str) -> set[str]:
    return {match.replace(",", "").rstrip("0").rstrip(".") or "0" for match in NUMBER.findall(value.translate(DIGITS))}


def known_urls() -> set[str]:
    urls = set()
    for scheme in load_schemes():
        urls.add(scheme.source.url)
        if scheme.application_url:
            urls.add(scheme.application_url)
    return urls


def answer_is_grounded(answer: str, chunks: list[dict], urls: set[str]) -> bool:
    """Every cited id was retrieved, every number is in a cited chunk, every URL is a known one."""
    by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
    cited = CITATION.findall(answer)
    if not cited or any(chunk_id not in by_id for chunk_id in cited):
        return False

    body = CITATION.sub(" ", answer)
    found_urls = [url.rstrip(".,;") for url in URL.findall(body)]
    if any(url not in urls for url in found_urls):
        return False

    body = URL.sub(" ", body)
    allowed = set().union(*(_numbers(by_id[chunk_id]["text"]) for chunk_id in cited))
    return _numbers(body) <= allowed


def _citations(chunks: list[dict]) -> list[Citation]:
    return [Citation(chunk_id=c["chunk_id"], source_url=c["source_url"], source_title=c["source_title"]) for c in chunks]


def _refusal(chunks: list[dict], lang: str) -> ChatResponse:
    return ChatResponse(answer=text(lang, "refusal"), citations=_citations(chunks[:3]), grounded=False)


def _extractive(chunks: list[dict], lang: str) -> ChatResponse:
    excerpts = "\n\n".join(chunk["text"] for chunk in chunks[:3])
    return ChatResponse(answer=f"{text(lang, 'extractive_prefix')}\n\n{excerpts}", citations=_citations(chunks[:3]), grounded=True)


def answer_question(question: str, lang: str) -> ChatResponse:
    query = question
    if lang != "en":
        translated = complete_json(TRANSLATE_SYSTEM, question, TRANSLATE_SCHEMA)
        query = (translated or {}).get("english") or question

    chunks = search(query)
    if not chunks or chunks[0]["score"] < MIN_SCORE:
        return ChatResponse(answer=text(lang, "refusal"), citations=[], grounded=False)

    excerpts = "\n\n".join(f"[{chunk['chunk_id']}] {chunk['text']}" for chunk in chunks)
    user = f"Language: {lang}\n\nExcerpts:\n{excerpts}\n\nQuestion: {question}"
    response = complete_json(ANSWER_SYSTEM, user, ANSWER_SCHEMA)
    if response is None:
        return _extractive(chunks, lang)

    answer = (response.get("answer") or "").strip()
    if not answer or not answer_is_grounded(answer, chunks, known_urls()):
        return _refusal(chunks, lang)

    cited = dict.fromkeys(CITATION.findall(answer))
    return ChatResponse(answer=answer, citations=_citations([c for c in chunks if c["chunk_id"] in cited]), grounded=True)
