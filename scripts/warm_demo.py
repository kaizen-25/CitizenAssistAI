#!/usr/bin/env python3
"""Warm the LLM cache with the demo script, or replay it offline (PROMPTS §E). Run with the backend venv.

Usage:
  python scripts/warm_demo.py          # calls the LLM and fills backend/.llm_cache
  python scripts/warm_demo.py --replay # DEMO_MODE=true with all network sockets blocked

Type the demo lines below exactly. The cache is keyed on the exact prompt.
"""
import argparse
import json
import os
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

INTAKE = "मैं 19 साल की हूँ और परिवार की आय 1.8 लाख रुपये सालाना है"
ANSWERS = {
    "state": "Punjab", "age": 19, "annual_family_income": 180000, "currently_enrolled": True, "course_level": "undergraduate",
    "social_category": "OBC", "holds_bpl_card": False, "gender": "female", "has_disability": False, "marital_status": "unmarried",
    "pregnant_or_lactating": False, "occupation": "student", "residence_area": "urban", "education_level": "class_12",
}
MISSING = {"income_certificate", "caste_certificate"}
OLLAMA_PORT = 11434
QUESTIONS = [
    ("पीएम-यूएसपी छात्रवृत्ति के लिए पारिवारिक आय सीमा क्या है?", "hi", True),
    ("What is the family income limit for the PM-USP scholarship?", "en", True),
    ("What is the last date to apply for the PM-USP scholarship this year?", "en", False),
    ("Who won the cricket world cup?", "en", False),
]


def run_demo() -> dict:
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    created = client.post("/api/session", json={"language": "hi"}).json()
    base = f"/api/session/{created['session_id']}"
    message = client.post(f"{base}/message", json={"text": INTAKE}, headers={"Accept-Language": "hi"}).json()
    question = message["next_question"]
    asked = []
    while question:
        asked.append(question["field_id"])
        question = client.post(f"{base}/answer", json={"field_id": question["field_id"], "value": ANSWERS[question["field_id"]]}).json()["next_question"]

    documents = client.get(f"{base}/documents").json()["documents"]
    client.post(f"{base}/documents", json={d["document_id"]: "missing" if d["document_id"] in MISSING else "have" for d in documents})
    client.post(f"{base}/confirm", json={})
    groups = client.get(f"{base}/results").json()["groups"]
    plan = client.get(f"{base}/unlock").json()["plan"]
    chats = [client.post("/api/chat", json={"question": q, "language": lang}).json() for q, lang, _ in QUESTIONS]
    packet = client.get(f"{base}/packet")
    return {
        "extracted": {field["field_id"]: field["value"] for field in message["extracted"]}, "asked": asked,
        "groups": {status: sorted(s["scheme_id"] for s in rows) for status, rows in groups.items()},
        "plan": [step["document_id"] for step in plan],
        "chats": [{"grounded": c["grounded"], "answer": c["answer"]} for c in chats],
        "packet_status": packet.status_code,
    }


def problems(demo: dict) -> list[str]:
    found = []
    if demo["extracted"].get("age") != 19 or demo["extracted"].get("annual_family_income") != 180000:
        found.append(f"intake did not extract age and income: {demo['extracted']}")
    for (question, _, expected), chat in zip(QUESTIONS, demo["chats"]):
        if chat["grounded"] is not expected or chat["answer"].startswith(("Relevant official excerpts", "संबंधित")):
            found.append(f"chat not as scripted: {question}")
    if demo["packet_status"] != 200:
        found.append(f"packet returned {demo['packet_status']}")
    if not demo["plan"]:
        found.append("no unlock plan")
    return found


def block_network() -> None:
    def refuse(*_, **__):
        raise OSError("network blocked for the replay")

    connect = socket.socket.connect

    def guarded(sock, address):
        # asyncio needs its own loopback pipe on Windows. Everything else, Ollama included, is refused.
        if address[0] != "127.0.0.1" or address[1] == OLLAMA_PORT:
            refuse()
        return connect(sock, address)

    socket.socket.connect = guarded


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--replay", action="store_true")
    args = parser.parse_args()

    if args.replay:
        os.environ["DEMO_MODE"] = "true"
        block_network()
    demo = run_demo()
    print(json.dumps(demo, ensure_ascii=False, indent=2))
    found = problems(demo)
    for problem in found:
        print(f"PROBLEM: {problem}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
