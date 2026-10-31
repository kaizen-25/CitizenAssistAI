#!/usr/bin/env python3
"""Generate evaluation/results/ from real runs (SPEC §11, §14). Run with the backend venv."""
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.config import get_settings, load_schemes, verified_by_category  # noqa: E402
from app.engine.eligibility import evaluate_all  # noqa: E402
from app.engine.questions import select_next_question  # noqa: E402
from app.llm.chat import answer_question, known_urls  # noqa: E402
from app.llm.extract_profile import extract_profile  # noqa: E402
from app.retrieval.bm25 import search  # noqa: E402
from app.unlock.graph import calculate_unlocks  # noqa: E402

EVALUATION = ROOT / "evaluation"
RESULTS = EVALUATION / "results"
STATUSES = ["potentially_eligible", "cannot_determine", "not_eligible"]
REQUIRED_CASES = [
    "all criteria pass", "a single hard fail", "a single unknown", "a missing mandatory doc", "a missing optional-only doc",
    "two docs shared across schemes", "no matches at all", "a declined sensitive field", "an ambiguous income input",
    "a Hindi free-text intake",
]


def read(name: str):
    return json.loads((EVALUATION / name).read_text(encoding="utf-8"))


def status_metrics(profiles: list, schemes: list) -> dict:
    confusion = {expected: Counter() for expected in STATUSES}
    mismatches = []
    for profile in profiles:
        results = {r.scheme_id: r.status for r in evaluate_all(schemes, profile["profile"], profile["documents"])}
        for scheme_id, expected in profile["expected"].items():
            confusion[expected][results[scheme_id]] += 1
            if results[scheme_id] != expected:
                mismatches.append({"profile": profile["id"], "scheme": scheme_id, "expected": expected, "actual": results[scheme_id]})

    total = sum(sum(row.values()) for row in confusion.values())
    correct = sum(confusion[status][status] for status in STATUSES)
    true_positive = confusion["potentially_eligible"]["potentially_eligible"]
    predicted = sum(confusion[status]["potentially_eligible"] for status in STATUSES)
    actual = sum(confusion["potentially_eligible"].values())
    return {
        "labels": total,
        "accuracy": correct / total if total else None,
        "precision_potentially_eligible": true_positive / predicted if predicted else None,
        "recall_potentially_eligible": true_positive / actual if actual else None,
        "confusion": {expected: {status: row[status] for status in STATUSES} for expected, row in confusion.items()},
        "mismatches": mismatches,
    }


def unlock_metrics(profiles: list, schemes: list) -> dict:
    checked = matched = 0
    misses = []
    for profile in profiles:
        expected = profile.get("expected_top_document")
        if expected is None:
            continue
        accepted = expected if isinstance(expected, list) else [expected]
        report = calculate_unlocks(evaluate_all(schemes, profile["profile"], profile["documents"]))
        top = report.ranking[0].document_id if report.ranking else None
        checked += 1
        if top in accepted:
            matched += 1
        else:
            misses.append({"profile": profile["id"], "expected": expected, "actual": top})
    return {"checked": checked, "top1_rate": matched / checked if checked else None, "misses": misses}


def adaptive_metrics(profiles: list, schemes: list) -> dict:
    counts, differing = [], []
    for profile in profiles:
        known, asked = {}, set()
        while (question := select_next_question(known, schemes, asked, "en")) is not None:
            asked.add(question.field_id)
            if question.field_id in profile["profile"]:
                known[question.field_id] = profile["profile"][question.field_id]
        counts.append(len(asked))
        adaptive = {r.scheme_id: r.status for r in evaluate_all(schemes, known, {})}
        full = {r.scheme_id: r.status for r in evaluate_all(schemes, profile["profile"], {})}
        differing += [
            {"profile": profile["id"], "scheme": scheme_id, "adaptive": adaptive[scheme_id], "full": full[scheme_id]}
            for scheme_id in full
            if adaptive[scheme_id] != full[scheme_id]
        ]
    static = {rule.field for scheme in schemes for rule in scheme.rules if rule.kind == "hard"}
    static |= {rule.applies_if.field for scheme in schemes for rule in scheme.rules if rule.applies_if}
    return {
        "mean_questions": sum(counts) / len(counts) if counts else None,
        "max_questions": max(counts, default=None),
        "static_form_size": len(static),
        "profiles_with_a_status_difference": len({d["profile"] for d in differing}),
        "status_differences": differing,
    }


def intake_metrics(profiles: list) -> dict:
    runs = []
    for profile in profiles:
        intake = profile.get("intake")
        if not intake:
            continue
        fields, clarification = extract_profile(intake["text"], {}, intake["language"])
        got = {field.field_id: field.value for field in fields}
        passed = all(got.get(k) == v for k, v in intake["expected_fields"].items()) and bool(clarification) == intake["expect_clarification"]
        runs.append({"profile": profile["id"], "language": intake["language"], "passed": passed, "fields": got, "clarification": bool(clarification)})
    return {"runs": runs, "pass_rate": sum(r["passed"] for r in runs) / len(runs) if runs else None}


def qa_metrics(questions: list) -> dict:
    urls = known_urls()
    runs = []
    for question in questions:
        response = answer_question(question["question"], question["language"])
        chunk_ids = {hit["chunk_id"] for hit in search(question["question"], top_k=50)}
        runs.append({
            "id": question["id"], "language": question["language"], "type": question["type"],
            "grounded": response.grounded, "answer": response.answer[:300],
            "citations_valid": all(c.source_url in urls for c in response.citations),
            "citations": [c.chunk_id for c in response.citations],
            "retrieved": len(chunk_ids),
        })
    answerable = [r for r in runs if r["type"] == "answerable"]
    unanswerable = [r for r in runs if r["type"] != "answerable"]
    cited = [r for r in runs if r["grounded"]]
    return {
        "questions": len(runs),
        "answerable_answered_rate": sum(r["grounded"] for r in answerable) / len(answerable) if answerable else None,
        "correct_refusal_rate": sum(not r["grounded"] for r in unanswerable) / len(unanswerable) if unanswerable else None,
        "citation_validity_rate": sum(r["citations_valid"] for r in cited) / len(cited) if cited else None,
        "languages": sorted({r["language"] for r in runs}),
        "runs": runs,
    }


def percent(value) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def write_report(metrics: dict) -> None:
    status, unlock, adaptive, intake, qa = (metrics[k] for k in ("status", "unlock", "adaptive", "intake", "qa"))
    lines = [
        "# CitizenAssist evaluation report", "",
        f"Date: {metrics['date']}. Verified schemes: {metrics['verified_schemes']} {metrics['by_category']}. "
        f"LLM provider setting: {metrics['llm_provider']}.", "",
        "## Limits of this evaluation",
        "- Scheme records were structured and verified by Claude, not by a human.",
        "- Evaluation labels were written by Claude from the scheme rules, so they are not independent.",
        "- Hindi is machine-translated and unreviewed. Punjabi was cut and is not claimed.",
        "- Answer correctness was not scored, because `qa_scores.json` needs a human reviewer.", "",
        "## Eligibility status",
        f"- Labels: {status['labels']}",
        f"- 3-class accuracy: {percent(status['accuracy'])}",
        f"- Precision for potentially eligible: {percent(status['precision_potentially_eligible'])}",
        f"- Recall for potentially eligible: {percent(status['recall_potentially_eligible'])}", "",
        "| Expected \\ Actual | " + " | ".join(STATUSES) + " |", "| --- | --- | --- | --- |",
    ]
    lines += [f"| {e} | " + " | ".join(str(status["confusion"][e][a]) for a in STATUSES) + " |" for e in STATUSES]
    lines += [
        "", f"Mismatches: {len(status['mismatches'])}",
        *[f"- {m['profile']} {m['scheme']}: expected {m['expected']}, got {m['actual']}" for m in status["mismatches"]],
        "", "## Document unlock",
        f"- Profiles checked: {unlock['checked']}",
        f"- Top-1 document match: {percent(unlock['top1_rate'])}",
        "", "## Adaptive questioning",
        f"- Mean questions asked: {adaptive['mean_questions']:.2f} (most: {adaptive['max_questions']})",
        f"- Static form size: {adaptive['static_form_size']} fields",
        f"- Profiles whose final status differed from the full profile: {adaptive['profiles_with_a_status_difference']} of {metrics['profile_count']}",
        f"- Individual scheme status differences: {len(adaptive['status_differences'])}",
        "", "## Free-text intake",
        f"- Pass rate: {percent(intake['pass_rate'])} across {len(intake['runs'])} runs",
        "", "## Grounded Q&A",
        f"- Questions: {qa['questions']} ({', '.join(qa['languages'])})",
        f"- Answerable questions answered: {percent(qa['answerable_answered_rate'])}",
        f"- Correct refusal rate: {percent(qa['correct_refusal_rate'])}",
        f"- Citation validity: {percent(qa['citation_validity_rate'])}",
        "", "## Coverage gaps",
        *[f"- No profile covers the required case: {case}" for case in metrics["uncovered_cases"]],
    ]
    (RESULTS / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    schemes = list(load_schemes())
    profiles = read("profiles.json")
    metrics = {
        "date": date.today().isoformat(),
        "verified_schemes": len(schemes),
        "by_category": verified_by_category(tuple(schemes)),
        "llm_provider": get_settings().llm_provider,
        "profile_count": len(profiles),
        "uncovered_cases": [case for case in REQUIRED_CASES if case not in {p["case"] for p in profiles}],
        "status": status_metrics(profiles, schemes),
        "unlock": unlock_metrics(profiles, schemes),
        "adaptive": adaptive_metrics(profiles, schemes),
        "intake": intake_metrics(profiles),
        "qa": qa_metrics(read("qa_set.json")),
    }
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(metrics)
    print((RESULTS / "report.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
