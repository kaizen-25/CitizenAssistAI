import copy
import importlib.util
import json
import subprocess
import sys
from typing import get_args

import pytest

from app.config import DATA_DIR, REPO_ROOT
from app.schemas import Operator
from tests.test_schemas import SPEC_EXAMPLE

SCRIPT = REPO_ROOT / "scripts" / "validate_data.py"

spec = importlib.util.spec_from_file_location("validate_data", SCRIPT)
validate_data = importlib.util.module_from_spec(spec)
sys.modules["validate_data"] = validate_data
spec.loader.exec_module(validate_data)

FIELDS = json.loads((DATA_DIR / "profile_fields.json").read_text(encoding="utf-8"))
DOCUMENTS = json.loads((DATA_DIR / "documents.json").read_text(encoding="utf-8"))


def failed_checks(*schemes):
    errors, _ = validate_data.validate(list(schemes), FIELDS, DOCUMENTS)
    return {check for check, found in errors.items() if found}


@pytest.fixture
def scheme():
    return copy.deepcopy(SPEC_EXAMPLE)


def test_valid_scheme_passes(scheme):
    assert failed_checks(scheme) == set()


def test_operator_list_matches_api_models():
    assert validate_data.OPERATORS == set(get_args(Operator))


def test_unregistered_rule_field_fails(scheme):
    scheme["rules"][0]["field"] = "shoe_size"
    assert failed_checks(scheme) == {"rule_fields"}


def test_unregistered_applies_if_field_fails(scheme):
    scheme["rules"][1]["applies_if"]["field"] = "shoe_size"
    assert failed_checks(scheme) == {"rule_fields"}


def test_invalid_operator_fails(scheme):
    scheme["rules"][0]["operator"] = "approximately"
    assert failed_checks(scheme) == {"operators"}


def test_ordering_operator_on_enum_fails(scheme):
    scheme["rules"][1].update(operator="gte", value="undergraduate")
    assert failed_checks(scheme) == {"operators"}


@pytest.mark.parametrize(
    "field, operator, value",
    [
        ("annual_family_income", "lte", "2.5 lakh"),
        ("annual_family_income", "lte", True),
        ("annual_family_income", "lte", -1),
        ("age", "gte", 18.5),
        ("currently_enrolled", "eq", "yes"),
        ("social_category", "eq", "Unlisted"),
        ("social_category", "in", "SC"),
        ("social_category", "in", []),
        ("social_category", "not_in", ["SC", "Unlisted"]),
    ],
)
def test_value_of_wrong_type_fails(scheme, field, operator, value):
    scheme["rules"][0].update(field=field, operator=operator, value=value)
    assert failed_checks(scheme) == {"value_types"}


def test_unknown_document_id_fails(scheme):
    scheme["documents"][0]["document_id"] = "library_card"
    assert failed_checks(scheme) == {"document_ids"}


def test_document_applies_if_is_checked(scheme):
    scheme["documents"][1]["applies_if"]["value"] = ["Unlisted"]
    assert failed_checks(scheme) == {"value_types"}


def test_missing_source_url_fails(scheme):
    scheme["source"]["url"] = ""
    assert failed_checks(scheme) == {"source_url"}


def test_missing_application_url_fails(scheme):
    scheme["application_url"] = None
    assert failed_checks(scheme) == {"application_url"}


def test_empty_excerpt_on_hard_rule_fails(scheme):
    scheme["rules"][0]["source_excerpt"] = "   "
    assert failed_checks(scheme) == {"source_excerpts"}


def test_duplicate_scheme_ids_fail(scheme):
    other = copy.deepcopy(scheme)
    for index, rule in enumerate(other["rules"]):
        rule["rule_id"] = f"other_{index}"
    assert failed_checks(scheme, other) == {"unique_ids"}


def test_duplicate_rule_ids_fail(scheme):
    scheme["rules"][1]["rule_id"] = scheme["rules"][0]["rule_id"]
    assert failed_checks(scheme) == {"unique_ids"}


def test_verified_without_verifier_fails(scheme):
    scheme["verification"]["verified_by"] = None
    assert failed_checks(scheme) == {"verified_by"}


def test_unverified_without_verifier_passes(scheme):
    scheme["verification"] = {"status": "unverified", "verified_by": None, "verified_on": None}
    assert failed_checks(scheme) == set()


def test_manual_check_without_field_passes_but_needs_excerpt(scheme):
    scheme["rules"].append({"rule_id": "syn_a_r3", "kind": "manual_check", "source_excerpt": "attendance of 75%"})
    assert failed_checks(scheme) == set()

    scheme["rules"][-1]["source_excerpt"] = ""
    assert failed_checks(scheme) == {"source_excerpts"}


def test_long_excerpt_warns_without_failing(scheme):
    scheme["rules"][0]["source_excerpt"] = "word " * 31
    errors, warnings = validate_data.validate([scheme], FIELDS, DOCUMENTS)
    assert not any(errors.values())
    assert len(warnings) == 1


def run_cli(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, encoding="utf-8")


def test_cli_passes_on_repo_data():
    result = run_cli()
    assert result.returncode == 0, result.stdout
    assert "Verified records: 0" in result.stdout


def test_cli_exits_nonzero_for_bad_draft_and_counts_categories(scheme, tmp_path):
    scheme["rules"][0]["field"] = "shoe_size"
    draft = tmp_path / "draft.json"
    draft.write_text(json.dumps(scheme), encoding="utf-8")

    result = run_cli("--file", str(draft))

    assert result.returncode == 1
    assert "shoe_size" in result.stdout
    assert "education: 1" in result.stdout
