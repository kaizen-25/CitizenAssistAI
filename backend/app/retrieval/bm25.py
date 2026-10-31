"""BM25 over chunks.jsonl (SPEC §7.3)."""
import json
import re
from functools import lru_cache

from rank_bm25 import BM25Okapi

from app.config import DATA_DIR

CHUNKS_PATH = DATA_DIR / "chunks.jsonl"
MIN_SCORE = 7.0


STOPWORDS = frozenset(
    """a about after all also am an and any are as at be been best but by can could did do does for from get got had
    has have how i if in into is it its me my no not of on or our should so than that the their them then there these
    they this to under up us was we were what when where which who whom why will with would you your""".split()
)


def tokenize(text: str) -> list[str]:
    return [token for token in re.findall(r"\w+", text.casefold()) if token not in STOPWORDS]


@lru_cache
def _index() -> tuple[list[dict], BM25Okapi | None]:
    if not CHUNKS_PATH.exists():
        return [], None
    lines = CHUNKS_PATH.read_text(encoding="utf-8").splitlines()
    chunks = [json.loads(line) for line in lines if line.strip()]
    return chunks, BM25Okapi([tokenize(chunk["text"]) for chunk in chunks]) if chunks else None


def search(query: str, top_k: int = 6) -> list[dict]:
    """Best chunks first, each with its score. Chunks that match no query term are left out."""
    chunks, bm25 = _index()
    if bm25 is None:
        return []
    scores = bm25.get_scores(tokenize(query))
    ranked = sorted(zip(scores, range(len(chunks))), key=lambda pair: (-pair[0], pair[1]))
    return [{**chunks[index], "score": float(score)} for score, index in ranked[:top_k] if score > 0]
