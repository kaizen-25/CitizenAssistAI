from app.schemas import DocumentBuckets, ResultSource, SchemeResult
from app.unlock.graph import calculate_unlocks


def result(scheme_id, missing=(), unsure=(), status="potentially_eligible", unknown=()):
    return SchemeResult(
        scheme_id=scheme_id,
        name=scheme_id,
        department="d",
        status=status,
        rules=[],
        unknown_fields=list(unknown),
        documents=DocumentBuckets(missing=list(missing), unsure=list(unsure)),
        document_ready=status == "potentially_eligible" and not missing and not unsure,
        source=ResultSource(url="u", title="t", retrieved_on="2026-11-01"),
    )


def five_schemes():
    income, caste = "income_certificate", "caste_certificate"
    return [
        result("a", [income]),
        result("b", [income, caste]),
        result("c", [income]),
        result("d", [caste]),
        result("e", [income]),
    ]


def ranks(report):
    return {entry.document_id: entry.rank for entry in report.ranking}


def steps(report):
    return [(s.step, s.document_id, s.newly_ready, s.cumulative_ready) for s in report.plan]


def test_five_scheme_ranking_matches_the_spec():
    income, caste = calculate_unlocks(five_schemes()).ranking

    assert (income.document_id, income.rank, income.required_by, income.sole_blocker_for) == (
        "income_certificate", 1, ["a", "b", "c", "e"], ["a", "c", "e"],
    )
    assert (caste.document_id, caste.rank, caste.required_by, caste.sole_blocker_for) == (
        "caste_certificate", 2, ["b", "d"], ["d"],
    )


def test_five_scheme_plan_matches_the_spec():
    assert steps(calculate_unlocks(five_schemes())) == [
        (1, "income_certificate", ["a", "c", "e"], 3),
        (2, "caste_certificate", ["b", "d"], 5),
    ]


def test_ready_schemes_are_listed_and_not_counted():
    report = calculate_unlocks([result("ready"), result("a", ["x"])])

    assert report.ready_now == ["ready"]
    assert report.ranking[0].required_by == ["a"]
    assert steps(report) == [(1, "x", ["a"], 1)]


def test_cannot_determine_is_excluded_from_all_counts():
    report = calculate_unlocks([
        result("a", ["x"]),
        result("pending", ["x", "y"], status="cannot_determine", unknown=["social_category"]),
    ])

    assert report.ranking[0].required_by == ["a"]
    assert [entry.document_id for entry in report.ranking] == ["x"]
    assert steps(report) == [(1, "x", ["a"], 1)]


def test_cannot_determine_goes_to_pending_info():
    report = calculate_unlocks([result("pending", ["x"], ["y"], status="cannot_determine", unknown=["age"])])

    assert report.pending_info[0].model_dump() == {"scheme_id": "pending", "unknown_fields": ["age"], "missing_documents": ["x", "y"]}


def test_not_eligible_is_ignored_everywhere():
    report = calculate_unlocks([result("no", ["x"], status="not_eligible")])

    assert (report.ready_now, report.ranking, report.plan, report.pending_info) == ([], [], [], [])


def test_unsure_documents_block_like_missing_ones():
    report = calculate_unlocks([result("a", unsure=["x"])])

    assert report.ranking[0].sole_blocker_for == ["a"]
    assert steps(report) == [(1, "x", ["a"], 1)]


def test_documents_tying_on_both_counts_share_a_rank():
    report = calculate_unlocks([result("a", ["x"]), result("b", ["y"]), result("c", ["z", "w"]), result("d", ["z", "w"])])

    assert ranks(report) == {"w": 1, "z": 1, "x": 3, "y": 3}


def test_required_by_ties_break_on_sole_blocker_count():
    report = calculate_unlocks([result("a", ["x"]), result("b", ["x", "y"]), result("c", ["y", "z"])])

    assert ranks(report) == {"x": 1, "y": 2, "z": 3}


def test_plan_makes_a_progress_step_when_no_document_completes_a_scheme():
    report = calculate_unlocks([result("a", ["x", "y"]), result("b", ["x", "z"])])

    assert steps(report) == [
        (1, "x", [], 0),
        (2, "y", ["a"], 1),
        (3, "z", ["b"], 2),
    ]


def test_plan_prefers_most_newly_ready_over_largest_required_by():
    # y is required by more schemes, but x alone finishes two.
    report = calculate_unlocks([
        result("a", ["x"]),
        result("b", ["x"]),
        result("c", ["y", "z"]),
        result("d", ["y", "w"]),
        result("e", ["y", "v"]),
    ])

    assert report.plan[0].document_id == "x"
    assert report.plan[0].newly_ready == ["a", "b"]


def test_plan_tie_breaks_on_required_by_then_document_id():
    report = calculate_unlocks([result("a", ["x"]), result("b", ["y"]), result("c", ["y", "z"])])

    assert [step.document_id for step in report.plan] == ["y", "x", "z"]


def test_plan_stops_when_every_candidate_is_ready():
    report = calculate_unlocks(five_schemes())

    assert report.plan[-1].cumulative_ready == 5
    assert len(report.plan) == 2


def test_plan_leaves_no_candidate_behind():
    results = [result("a", ["p", "q", "r"]), result("b", ["q", "s"]), result("c", ["r", "s", "t"]), result("d", ["u"])]
    report = calculate_unlocks(results)

    assert sorted(s for step in report.plan for s in step.newly_ready) == ["a", "b", "c", "d"]


def test_no_results_gives_an_empty_report():
    assert calculate_unlocks([]).model_dump() == {"ready_now": [], "ranking": [], "plan": [], "pending_info": []}
