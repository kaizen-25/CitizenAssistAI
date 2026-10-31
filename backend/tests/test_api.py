import time

import pytest
from fastapi.testclient import TestClient

from app import sessions
from app.main import app
from app.schemas import DECLINED

client = TestClient(app)

STUDENT = {
    "state": "Punjab", "age": 19, "gender": "female", "annual_family_income": 200000, "social_category": "SC",
    "currently_enrolled": True, "course_level": "undergraduate", "occupation": "student",
    "holds_bpl_card": True, "has_disability": False,
}


@pytest.fixture(autouse=True)
def synthetic_data(schemes, monkeypatch):
    monkeypatch.setattr("app.api.session.load_schemes", lambda: tuple(schemes))
    monkeypatch.setattr("app.api.schemes.load_schemes", lambda: tuple(schemes))


def start(language="en"):
    response = client.post("/api/session", json={"language": language})
    assert response.status_code == 200
    return response.json()


def url(session, path):
    return f"/api/session/{session['session_id']}/{path}"


def answer(session, field, value):
    return client.post(url(session, "answer"), json={"field_id": field, "value": value})


def complete_intake(session, profile=STUDENT):
    question = session["first_question"]
    while question:
        response = answer(session, question["field_id"], profile[question["field_id"]])
        assert response.status_code == 200
        question = response.json()["next_question"]


def test_session_starts_with_the_state_question():
    assert start()["first_question"]["field_id"] == "state"


def test_full_form_flow():
    session = start()
    complete_intake(session)
    # The 8-question cap leaves some fields unasked; "Answer now" reaches them.
    for field, value in STUDENT.items():
        answer(session, field, value)

    checklist = client.get(url(session, "documents")).json()["documents"]
    assert "income_certificate" in [item["document_id"] for item in checklist]

    client.post(url(session, "documents"), json={
        "income_certificate": "missing", "caste_certificate": "missing", "passport_photo": "missing",
        "bank_passbook": "have", "ration_card": "have",
    })
    assert client.post(url(session, "confirm"), json={}).json() == {"confirmed": True}

    groups = client.get(url(session, "results")).json()["groups"]
    assert [r["scheme_id"] for r in groups["potentially_eligible"]] == ["syn_a", "syn_b", "syn_d", "syn_e"]
    assert [r["scheme_id"] for r in groups["not_eligible"]] == ["syn_c", "syn_f"]
    assert groups["potentially_eligible"][0]["rules"][0]["explanation"].endswith("₹2,50,000")
    assert groups["potentially_eligible"][0]["name"] == "SYNTHETIC Scholarship A"

    unlock = client.get(url(session, "unlock")).json()
    assert unlock["ranking"][0]["label"] == "Income Certificate"
    assert [s["document_id"] for s in unlock["plan"]] == ["income_certificate", "caste_certificate"]

    packet = client.get(url(session, "packet")).json()
    assert packet["profile"]["annual_family_income"]["display"] == "₹2,00,000"
    assert packet["disclaimer"].startswith("CitizenAssist is an independent")


def test_results_are_withheld_until_confirmed():
    session = start()
    answer(session, "state", "Punjab")

    body = client.get(url(session, "results")).json()

    assert body["confirmed"] is False
    assert body["groups"]["potentially_eligible"] == []
    assert body["profile"]["state"]["display"] == "Punjab"
    assert client.get(url(session, "unlock")).status_code == 409
    assert client.get(url(session, "packet")).status_code == 409


def test_answer_now_moves_a_scheme_out_of_cannot_determine():
    session = start()
    profile = {k: v for k, v in STUDENT.items() if k != "social_category"}
    for field, value in profile.items():
        answer(session, field, value)
    client.post(url(session, "confirm"), json={})

    before = client.get(url(session, "results")).json()["groups"]
    assert "syn_d" in [r["scheme_id"] for r in before["cannot_determine"]]

    question = client.get(url(session, "question/social_category")).json()
    assert question["field_id"] == "social_category"
    answer(session, "social_category", "SC")

    after = client.get(url(session, "results")).json()["groups"]
    assert "syn_d" in [r["scheme_id"] for r in after["potentially_eligible"]]


def test_missing_documents_never_change_results():
    session = start()
    for field, value in STUDENT.items():
        answer(session, field, value)
    client.post(url(session, "confirm"), json={})
    statuses = lambda: {
        status: [r["scheme_id"] for r in rows]
        for status, rows in client.get(url(session, "results")).json()["groups"].items()
    }

    before = statuses()
    client.post(url(session, "documents"), json={"income_certificate": "missing"})

    assert statuses() == before


def test_confirm_overrides_are_marked():
    session = start()
    answer(session, "age", 19)

    client.post(url(session, "confirm"), json={"profile_overrides": {"age": 20}})
    profile = answer(session, "state", "Punjab").json()["profile"]

    assert (profile["age"]["value"], profile["age"]["source"]) == (20, "override")
    assert profile["age"]["label"] == "Age"


def test_declined_is_read_back_as_declined():
    session = start()

    profile = answer(session, "gender", DECLINED).json()["profile"]

    assert profile["gender"]["display"] == "Prefer not to say"


@pytest.mark.parametrize(
    "field, value",
    [
        ("shoe_size", 9),
        ("age", 500),
        ("age", 18.5),
        ("age", "nineteen"),
        ("age", True),
        ("state", "Atlantis"),
        ("currently_enrolled", "yes"),
        ("age", DECLINED),
    ],
)
def test_invalid_answers_are_rejected(field, value):
    assert answer(start(), field, value).status_code == 422


def test_unknown_document_is_rejected():
    assert client.post(url(start(), "documents"), json={"library_card": "have"}).status_code == 422


def test_invalid_document_answer_is_rejected():
    assert client.post(url(start(), "documents"), json={"income_certificate": "maybe"}).status_code == 422


def test_unknown_session_is_404():
    assert client.get("/api/session/nope/results").status_code == 404


def test_session_expires_after_the_ttl(monkeypatch):
    session = start()
    later = time.monotonic() + sessions.SESSION_TTL_SECONDS + 1
    monkeypatch.setattr(sessions.time, "monotonic", lambda: later)

    assert client.get(url(session, "results")).status_code == 404


def test_language_header_changes_labels():
    session = start()

    response = client.get(url(session, "documents"), headers={"Accept-Language": "hi"})

    assert response.status_code == 200
    labels = {item["document_id"]: item["label"] for item in response.json()["documents"]}
    assert labels["income_certificate"] == "आय प्रमाण पत्र"


def test_session_language_is_the_fallback():
    session = start("hi")

    labels = {i["document_id"]: i["label"] for i in client.get(url(session, "documents")).json()["documents"]}

    assert labels["income_certificate"] == "आय प्रमाण पत्र"


def test_checklist_leaves_out_failed_schemes():
    session = start()
    answer(session, "has_disability", False)

    ids = [item["document_id"] for item in client.get(url(session, "documents")).json()["documents"]]

    assert "disability_certificate" not in ids


def test_scheme_endpoints():
    assert len(client.get("/api/schemes").json()) == 6
    assert client.get("/api/schemes/syn_a").json()["name"]["en"] == "SYNTHETIC Scholarship A"
    assert client.get("/api/schemes/nope").status_code == 404


def test_message_saves_extracted_fields_and_marks_them(monkeypatch):
    monkeypatch.setattr("app.llm.extract_profile.complete_json", lambda *args, **kwargs: None)
    session = start()

    body = client.post(url(session, "message"), json={"text": "family income 2 lakh"}).json()

    assert body["extracted"][0]["value"] == 200000
    assert body["profile"]["annual_family_income"]["source"] == "extracted"
    assert body["clarification"] is None


def test_ambiguous_message_saves_nothing_and_asks(monkeypatch):
    monkeypatch.setattr("app.llm.extract_profile.complete_json", lambda *args, **kwargs: None)
    session = start()

    body = client.post(url(session, "message"), json={"text": "income is 2-3 lakh"}).json()

    assert body["profile"] == {}
    assert body["clarification"]


def test_chat_route_returns_the_refusal_when_nothing_matches(monkeypatch):
    monkeypatch.setattr("app.llm.chat.search", lambda query: [])

    body = client.post("/api/chat", json={"question": "who won the match?"}).json()

    assert body == {"answer": "I cannot verify this from the available official sources.", "citations": [], "grounded": False}
