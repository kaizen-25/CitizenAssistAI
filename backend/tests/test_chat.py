import sys

import pytest

from app.config import REPO_ROOT
from app.llm import chat
from app.llm.chat import answer_is_grounded, answer_question

sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_chunks  # noqa: E402

CHUNKS = [
    {"chunk_id": "edu_001_c0", "scheme_id": "edu_001", "source_url": "https://a.invalid", "source_title": "A", "text": "Family income up to Rs. 4.5 lakh is eligible. Age limit 25 years. Pension is Rs. 1500 per month.", "score": 20.0},
    {"chunk_id": "edu_002_c0", "scheme_id": "edu_002", "source_url": "https://b.invalid", "source_title": "B", "text": "Scholarship of Rs. 12,000 per annum.", "score": 15.0},
]
URLS = {"https://a.invalid"}


def grounded(answer):
    return answer_is_grounded(answer, CHUNKS, URLS)


def test_cited_claim_passes():
    assert grounded("The income limit is 4.5 lakh [edu_001_c0].")


def test_fabricated_citation_is_rejected():
    assert not grounded("The limit is 4.5 lakh [edu_999_c0].")


def test_answer_without_citation_is_rejected():
    assert not grounded("The limit is 4.5 lakh.")


def test_unseen_number_is_rejected():
    assert not grounded("The limit is 9.5 lakh [edu_001_c0].")


def test_a_number_is_not_equal_to_itself_without_its_zeros():
    assert grounded("The pension is Rs. 1500 [edu_001_c0].")
    assert not grounded("The pension is Rs. 15 [edu_001_c0].")
    assert not grounded("The pension is Rs. 150 [edu_001_c0].")


def test_trailing_decimal_zeros_are_the_same_number():
    assert grounded("The limit is 4.50 lakh [edu_001_c0].")


def test_number_from_an_uncited_chunk_is_rejected():
    assert not grounded("You get Rs. 12,000 [edu_001_c0].")


def test_number_formatting_differences_are_tolerated():
    assert grounded("You get Rs. 12000 [edu_002_c0].")


def test_devanagari_digits_are_compared_as_numbers():
    assert grounded("आयु सीमा २५ वर्ष है [edu_001_c0].")


def test_digits_in_a_chunk_id_do_not_count_as_numbers():
    assert grounded("Income is the main criterion [edu_001_c0].")


def test_unknown_url_is_rejected():
    assert not grounded("Apply at https://evil.invalid/apply [edu_001_c0].")


def test_known_url_is_allowed():
    assert grounded("See https://a.invalid [edu_001_c0].")


def test_www_url_is_rejected_unless_known():
    assert not grounded("See www.evil.invalid [edu_001_c0].")


@pytest.fixture
def wired(monkeypatch):
    monkeypatch.setattr(chat, "search", lambda query: [dict(c) for c in CHUNKS])
    monkeypatch.setattr(chat, "known_urls", lambda: URLS)


def llm(monkeypatch, *responses):
    queue = list(responses)
    monkeypatch.setattr(chat, "complete_json", lambda *args, **kwargs: queue.pop(0))


def test_grounded_answer_cites_only_what_it_used(wired, monkeypatch):
    llm(monkeypatch, {"answer": "Up to 4.5 lakh [edu_001_c0]."})

    response = answer_question("income limit?", "en")

    assert response.grounded is True
    assert [c.chunk_id for c in response.citations] == ["edu_001_c0"]


def test_uncited_answer_gets_its_listed_citations(wired, monkeypatch):
    llm(monkeypatch, {"answer": "Up to 4.5 lakh.", "citation_ids": ["edu_001_c0"]})

    response = answer_question("income limit?", "en")

    assert response.grounded is True
    assert [c.chunk_id for c in response.citations] == ["edu_001_c0"]


def test_listed_citation_that_was_not_retrieved_is_rejected(wired, monkeypatch):
    llm(monkeypatch, {"answer": "Up to 4.5 lakh.", "citation_ids": ["edu_999_c0"]})

    assert answer_question("income limit?", "en").grounded is False


def test_answer_that_repeats_the_question_is_refused(wired, monkeypatch):
    llm(monkeypatch, {"english": "income limit"}, {"answer": "आय सीमा क्या है? [edu_001_c0]", "citation_ids": ["edu_001_c0"]})

    assert answer_question("आय सीमा क्या है?", "hi").grounded is False


def test_answer_that_narrates_its_reasoning_is_refused(wired, monkeypatch):
    llm(monkeypatch, {"answer": "The question asks about income. Let me analyze. 4.5 lakh [edu_001_c0]."})

    assert answer_question("income limit?", "en").grounded is False


@pytest.mark.parametrize("answer", [
    "The provided excerpts do not specify the number of students. [edu_001_c0]",
    "The excerpts contain no such figure. [edu_001_c0]",
    "दिए गए उद्धरणों में यह जानकारी नहीं है। [edu_001_c0]",
])
def test_answer_saying_the_excerpts_lack_it_is_refused(wired, monkeypatch, answer):
    llm(monkeypatch, {"answer": answer})

    assert answer_question("How many students received it?", "en").grounded is False


def test_answer_with_not_in_it_is_still_an_answer(wired, monkeypatch):
    llm(monkeypatch, {"answer": "Income must not exceed 4.5 lakh [edu_001_c0]."})

    assert answer_question("income limit?", "en").grounded is True


@pytest.mark.parametrize("question", ["What schemes are available for students?", "Which scholarships can I apply for?"])
def test_list_question_names_only_education_schemes_without_any_llm_call(monkeypatch, question):
    monkeypatch.setattr(chat, "complete_json", lambda *_: pytest.fail("the catalogue needs no LLM"))

    response = answer_question(question, "en")

    assert response.grounded is True
    assert "PM-USP" in response.answer
    assert "Old Age" not in response.answer


def test_hindi_list_question_is_answered_after_translation(monkeypatch):
    monkeypatch.setattr(chat, "complete_json", lambda *_: {"english": "What schemes are there for students?"})

    assert "PM-USP" in answer_question("छात्रों के लिए कौन सी योजनाएँ हैं?", "hi").answer


@pytest.mark.parametrize("question", ["What is the income limit for the Post Matric Scholarship?", "How much is the Punjab pension?"])
def test_detail_questions_are_not_list_questions(question):
    assert chat.LIST_QUESTION.search(question) is None


def test_question_naming_a_scheme_reaches_the_llm_despite_a_low_score(monkeypatch):
    seen = {}
    monkeypatch.setattr(chat, "search", lambda *_: [])

    def reply(system, user, schema):
        seen["user"] = user
        return {"answer": "A maternity benefit [soc_009_c0].", "citation_ids": ["soc_009_c0"]}

    monkeypatch.setattr(chat, "complete_json", reply)

    assert answer_question("What is PMMVY?", "en").grounded is True
    assert "[soc_009_c0]" in seen["user"]


def test_low_score_question_naming_no_scheme_is_still_refused(monkeypatch):
    monkeypatch.setattr(chat, "search", lambda *_: [{"chunk_id": "x", "score": 1.0}])
    monkeypatch.setattr(chat, "complete_json", lambda *_: pytest.fail("off-topic questions never reach the LLM"))

    assert answer_question("Who won the cricket world cup?", "en").grounded is False


def test_email_that_is_not_in_the_cited_excerpt_is_rejected():
    chunks = [{"chunk_id": "a", "text": "Write to help@gov.in for details."}]

    assert answer_is_grounded("Write to help@gov.in [a].", chunks, set()) is True
    assert answer_is_grounded("Write to other@gov.in [a].", chunks, set()) is False


def test_english_reply_to_a_hindi_question_is_asked_for_again_in_hindi(wired, monkeypatch):
    replies = iter([
        {"english": "income limit"},
        {"answer": "The limit is 4.5 lakh [edu_001_c0].", "citation_ids": ["edu_001_c0"]},
        {"answer": "सीमा 4.5 लाख है [edu_001_c0]।", "citation_ids": ["edu_001_c0"]},
    ])
    monkeypatch.setattr(chat, "complete_json", lambda *_: next(replies))

    assert answer_question("आय सीमा?", "hi").answer.startswith("सीमा")


def test_the_prompt_names_the_language_in_full(wired, monkeypatch):
    seen = {}

    def reply(system, user, schema):
        seen.setdefault("user", user) if "Excerpts" in user else None
        return {"english": "income limit", "answer": "४.५ लाख [edu_001_c0]", "citation_ids": ["edu_001_c0"]}

    monkeypatch.setattr(chat, "complete_json", reply)
    answer_question("आय सीमा?", "hi")

    assert "Language: Hindi" in seen["user"]


def test_failed_validation_refuses_with_top_sources(wired, monkeypatch):
    llm(monkeypatch, {"answer": "Up to 9 lakh [edu_001_c0]."})

    response = answer_question("income limit?", "en")

    assert response.grounded is False
    assert response.answer == "I cannot verify this from the available official sources."
    assert [c.chunk_id for c in response.citations] == ["edu_001_c0", "edu_002_c0"]


def test_empty_llm_answer_refuses(wired, monkeypatch):
    llm(monkeypatch, {"answer": ""})

    assert answer_question("anything", "en").grounded is False


def test_weak_retrieval_refuses_without_calling_the_llm(monkeypatch):
    monkeypatch.setattr(chat, "search", lambda query: [{**CHUNKS[0], "score": 0.1}])
    llm(monkeypatch)

    response = answer_question("who won the cricket?", "en")

    assert response.grounded is False
    assert response.citations == []


def test_no_chunks_refuses(monkeypatch):
    monkeypatch.setattr(chat, "search", lambda query: [])
    llm(monkeypatch)

    assert answer_question("anything", "en").grounded is False


def test_no_llm_falls_back_to_official_excerpts(wired, monkeypatch):
    llm(monkeypatch, None)

    response = answer_question("income limit?", "en")

    assert response.answer.startswith("Relevant official excerpts:")
    assert "4.5 lakh" in response.answer
    assert len(response.citations) == 2


@pytest.mark.parametrize("question", ["What is the last date to apply?", "PM-USP deadline?", "आवेदन की अंतिम तिथि क्या है?"])
def test_deadline_questions_are_refused_before_any_llm_call(wired, monkeypatch, question):
    llm(monkeypatch)

    response = answer_question(question, "en")

    assert response.grounded is False
    assert response.answer == "I cannot verify this from the available official sources."


def test_translated_deadline_question_is_refused(wired, monkeypatch):
    llm(monkeypatch, {"english": "What is the last date?"})

    assert answer_question("कब तक?", "hi").grounded is False


def test_hindi_question_is_translated_before_retrieval(monkeypatch):
    queries = []
    monkeypatch.setattr(chat, "search", lambda query: queries.append(query) or [])
    llm(monkeypatch, {"english": "income limit"})

    answer_question("आय सीमा क्या है?", "hi")

    assert queries == ["income limit"]


def test_hindi_question_without_llm_still_searches(monkeypatch):
    queries = []
    monkeypatch.setattr(chat, "search", lambda query: queries.append(query) or [])
    llm(monkeypatch, None)

    answer_question("आय सीमा", "hi")

    assert queries == ["आय सीमा"]


# build_chunks


def test_chunks_overlap_by_fifty_words():
    words = [f"w{i}" for i in range(800)]
    pieces = build_chunks.chunk_words(" ".join(words))

    assert len(pieces[0].split()) == 400
    assert pieces[0].split()[-50:] == pieces[1].split()[:50]
    assert pieces[-1].split()[-1] == "w799"


def test_short_text_is_one_chunk():
    assert build_chunks.chunk_words("just a few words") == ["just a few words"]


def test_empty_text_gives_no_chunks():
    assert build_chunks.chunk_words("  ") == []


def test_only_verified_schemes_are_chunked(by_id):
    verified = by_id["syn_a"].model_dump()
    unverified = {**by_id["syn_b"].model_dump(), "verification": {"status": "unverified"}}

    chunks = build_chunks.build([verified, unverified])

    assert {chunk["scheme_id"] for chunk in chunks} == {"syn_a"}
    assert chunks[0]["chunk_id"] == "syn_a_c0"
    assert chunks[0]["source_url"] == "https://example.invalid/source/syn_a"
