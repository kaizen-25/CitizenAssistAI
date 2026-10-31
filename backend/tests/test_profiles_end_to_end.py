"""Five synthetic citizens run through engine and unlock. Expected values are hand-calculated from the fixture rules."""
import importlib.util
import json
import sys

from app.config import REPO_ROOT
from app.engine.eligibility import evaluate_all
from app.unlock.graph import calculate_unlocks
from app.schemas import DECLINED
from tests.conftest import FIXTURE_PATH

PE, CD, NE = "potentially_eligible", "cannot_determine", "not_eligible"

STUDENT = {
    "state": "Punjab", "age": 19, "gender": "female", "annual_family_income": 200000, "social_category": "SC",
    "currently_enrolled": True, "course_level": "undergraduate", "occupation": "student",
    "holds_bpl_card": True, "has_disability": False,
}
STUDENT_DOCS = {
    "income_certificate": "missing", "caste_certificate": "missing", "passport_photo": "missing",
    "bank_passbook": "have", "ration_card": "have",
}


def statuses(results):
    return {r.scheme_id.removeprefix("syn_"): r.status for r in results}


def test_student_shared_documents(schemes):
    results = evaluate_all(schemes, STUDENT, STUDENT_DOCS)
    report = calculate_unlocks(results)

    assert statuses(results) == {"a": PE, "b": PE, "c": NE, "d": PE, "e": PE, "f": NE}
    assert [(e.document_id, e.rank, e.required_by, e.sole_blocker_for) for e in report.ranking] == [
        ("income_certificate", 1, ["syn_a", "syn_b", "syn_e"], ["syn_b", "syn_e"]),
        ("caste_certificate", 2, ["syn_a", "syn_d"], ["syn_d"]),
    ]
    assert [(s.document_id, s.newly_ready, s.cumulative_ready) for s in report.plan] == [
        ("income_certificate", ["syn_b", "syn_e"], 2),
        ("caste_certificate", ["syn_a", "syn_d"], 4),
    ]


def test_declined_category_leaves_one_scheme_undetermined(schemes):
    profile = dict(STUDENT, social_category=DECLINED)
    results = evaluate_all(schemes, profile, STUDENT_DOCS)
    report = calculate_unlocks(results)

    assert statuses(results) == {"a": PE, "b": PE, "c": NE, "d": CD, "e": PE, "f": NE}
    assert results[0].documents.possibly_required == ["caste_certificate"]
    assert [p.scheme_id for p in report.pending_info] == ["syn_d"]
    assert [e.document_id for e in report.ranking] == ["income_certificate"]
    assert report.ranking[0].required_by == ["syn_a", "syn_b", "syn_e"]


def test_no_matches_at_all(schemes):
    profile = {
        "state": "Other", "age": 40, "gender": "male", "annual_family_income": 900000, "social_category": "General",
        "currently_enrolled": False, "occupation": "salaried", "holds_bpl_card": False, "has_disability": False,
    }
    results = evaluate_all(schemes, profile, {})
    report = calculate_unlocks(results)

    assert set(statuses(results).values()) == {NE}
    assert report.model_dump() == {"ready_now": [], "ranking": [], "plan": [], "pending_info": []}


def test_ready_now_with_everything_held(schemes):
    profile = dict(STUDENT, has_disability=True)
    docs = {key: "have" for key in (
        "income_certificate", "caste_certificate", "bank_passbook", "ration_card", "disability_certificate",
    )}
    results = evaluate_all(schemes, profile, docs)
    report = calculate_unlocks(results)

    assert statuses(results) == {"a": PE, "b": PE, "c": NE, "d": PE, "e": PE, "f": PE}
    assert report.ready_now == ["syn_a", "syn_b", "syn_d", "syn_e", "syn_f"]
    assert (report.ranking, report.plan) == ([], [])


def test_empty_profile_decides_nothing(schemes):
    results = evaluate_all(schemes, {}, {})
    report = calculate_unlocks(results)

    assert set(statuses(results).values()) == {CD}
    assert len(report.pending_info) == 6
    assert report.plan == []


def test_run_profile_script_prints_the_report(tmp_path, capsys, monkeypatch):
    path = REPO_ROOT / "scripts" / "run_profile.py"
    spec = importlib.util.spec_from_file_location("run_profile", path)
    run_profile = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run_profile)

    profile_file = tmp_path / "citizen.json"
    profile_file.write_text(json.dumps({"profile": STUDENT, "documents": STUDENT_DOCS}), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["run_profile.py", str(profile_file), "--schemes", str(FIXTURE_PATH)])

    run_profile.main()
    output = capsys.readouterr().out

    assert "potentially_eligible" in output
    assert "income_certificate" in output
    assert "₹2,50,000" in output
