#!/usr/bin/env python3
"""Regenerate frontend/src/fixtures/ from the real API running on the SYNTHETIC schemes. Run with the backend venv."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.schemas import Scheme  # noqa: E402

FIXTURES = ROOT / "frontend" / "src" / "fixtures"
SYNTHETIC = json.loads((ROOT / "backend" / "tests" / "fixtures" / "synthetic_schemes.json").read_text(encoding="utf-8"))
PROFILE = {
    "state": "Punjab", "age": 19, "gender": "female", "annual_family_income": 200000, "currently_enrolled": True,
    "course_level": "undergraduate", "occupation": "student", "holds_bpl_card": True, "has_disability": False,
}
DOCUMENTS = {
    "income_certificate": "missing", "caste_certificate": "unsure", "passport_photo": "missing",
    "bank_passbook": "have", "ration_card": "have",
}


def write(name: str, data) -> None:
    (FIXTURES / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    schemes = tuple(Scheme.model_validate(record) for record in SYNTHETIC)
    client = TestClient(app)
    with patch("app.api.session.load_schemes", lambda: schemes), patch("app.api.schemes.load_schemes", lambda: schemes):
        session = client.post("/api/session", json={"language": "en"}).json()
        base = f"/api/session/{session['session_id']}"
        write("session", session)

        flow, questions, question = [], {}, session["first_question"]
        while question:
            questions[question["field_id"]] = question
            response = client.post(f"{base}/answer", json={"field_id": question["field_id"], "value": PROFILE[question["field_id"]]}).json()
            flow.append(response)
            question = response["next_question"]
        write("flow", flow)

        questions["social_category"] = client.get(f"{base}/question/social_category").json()
        write("questions", questions)
        write("checklist", client.get(f"{base}/documents").json())

        client.post(f"{base}/documents", json=DOCUMENTS)
        client.post(f"{base}/confirm", json={})
        write("results", client.get(f"{base}/results").json())
        write("unlock", client.get(f"{base}/unlock").json())
        write("packet", client.get(f"{base}/packet").json())
        write("schemes", {s["scheme_id"]: s for s in client.get("/api/schemes").json()})

    write("message", {
        "extracted": [{"field_id": "age", "value": 19, "evidence": "I am 19", "explicit": True, "source": "extracted"}],
        "clarification": None,
        "profile": flow[0]["profile"],
        "next_question": flow[0]["next_question"],
    })
    write("chat", {
        "answer": "I cannot verify this from the available official sources.",
        "citations": [],
        "grounded": False,
    })


if __name__ == "__main__":
    main()
