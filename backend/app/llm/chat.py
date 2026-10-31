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
DEADLINE_QUESTION = re.compile(
    r"last date|deadline|closing date|due date|when (?:can|do|should|must) i apply|अंतिम तिथि|अंतिम तारीख|आखिरी तारीख|आखिरी तिथि",
    re.IGNORECASE,
)
REASONING = re.compile(r"\b(?:the question asks|let me|looking at the|the user (?:asks|wants))\b", re.IGNORECASE)
URL = re.compile(r"https?://[^\s)\]>\"']+|www\.[^\s)\]>\"']+")

ANSWER_SYSTEM = """Answer the citizen's question using ONLY the numbered excerpts.
- Put the excerpt's id in square brackets after every claim, like [edu_001_c0], and list every id you used in citation_ids.
- Never use outside knowledge. Never add a number, date, fee or URL that is not in a cited excerpt.
- Answer in one or two short sentences, taken from the excerpt that addresses the question most directly.
- Reply in the requested language."""
ANSWER_SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}, "citation_ids": {"type": "array", "items": {"type": "string"}}},
    "required": ["answer", "citation_ids"],
}

TRANSLATE_SYSTEM = "Translate the user's question into English. Keep scheme names as they are."
TRANSLATE_SCHEMA = {"type": "object", "properties": {"english": {"type": "string"}}, "required": ["english"]}


def _canonical_number(match: str) -> str:
    plain = match.replace(",", "")
    return plain.rstrip("0").rstrip(".") if "." in plain else plain


def _numbers(value: str) -> set[str]:
    return {_canonical_number(match) for match in NUMBER.findall(value.translate(DIGITS))}


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


def is_real_answer(answer: str, question: str) -> bool:
    """Reject a model that repeats the question or narrates its reasoning instead of answering."""
    words = lambda text: re.findall(r"\w+", CITATION.sub(" ", text).casefold())
    return words(answer) != words(question) and not REASONING.search(answer)


def _citations(chunks: list[dict]) -> list[Citation]:
    return [Citation(chunk_id=c["chunk_id"], source_url=c["source_url"], source_title=c["source_title"]) for c in chunks]


def _refusal(chunks: list[dict], lang: str) -> ChatResponse:
    return ChatResponse(answer=text(lang, "refusal"), citations=_citations(chunks[:3]), grounded=False)


def _extractive(chunks: list[dict], lang: str) -> ChatResponse:
    excerpts = "\n\n".join(chunk["text"] for chunk in chunks[:3])
    return ChatResponse(answer=f"{text(lang, 'extractive_prefix')}\n\n{excerpts}", citations=_citations(chunks[:3]), grounded=True)


def answer_question(question: str, lang: str) -> ChatResponse:
    if DEADLINE_QUESTION.search(question):
        return _refusal(search(question), lang)

    query = question
    if lang != "en":
        translated = complete_json(TRANSLATE_SYSTEM, question, TRANSLATE_SCHEMA)
        query = (translated or {}).get("english") or question

    if DEADLINE_QUESTION.search(query):
        return _refusal(search(query), lang)

    chunks = search(query)
    if not chunks or chunks[0]["score"] < MIN_SCORE:
        return ChatResponse(answer=text(lang, "refusal"), citations=[], grounded=False)

    excerpts = "\n\n".join(f"[{chunk['chunk_id']}] {chunk['text']}" for chunk in chunks)
    user = f"Language: {lang}\n\nExcerpts:\n{excerpts}\n\nQuestion: {question}"
    response = complete_json(ANSWER_SYSTEM, user, ANSWER_SCHEMA)
    if response is None:
        return _extractive(chunks, lang)

    answer = (response.get("answer") or "").strip()
    if answer and not CITATION.search(answer):
        answer += "".join(f" [{chunk_id}]" for chunk_id in response.get("citation_ids", []))
    if not answer or not is_real_answer(answer, question) or not answer_is_grounded(answer, chunks, known_urls()):
        return _refusal(chunks, lang)

    cited = dict.fromkeys(CITATION.findall(answer))
    return ChatResponse(answer=answer, citations=_citations([c for c in chunks if c["chunk_id"] in cited]), grounded=True)
