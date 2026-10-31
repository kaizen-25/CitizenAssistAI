#!/usr/bin/env python3
"""Validate scheme data against SPEC §3.4. Standard library only, so it runs on any Python.

Usage:
  python scripts/validate_data.py                      # checks backend/app/data/schemes.json
  python scripts/validate_data.py --file draft.json    # checks one record or a list of records
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "backend" / "app" / "data"

OPERATORS = {"eq", "neq", "gt", "gte", "lt", "lte", "in", "not_in"}
ORDERING_OPERATORS = {"gt", "gte", "lt", "lte"}
LIST_OPERATORS = {"in", "not_in"}
RULE_KINDS = {"hard", "manual_check"}
MAX_EXCERPT_WORDS = 30

CHECKS = {
    "rule_fields": "Every rule field exists in profile_fields.json",
    "operators": "Every operator is valid",
    "value_types": "Every value matches its field type",
    "document_ids": "Every document_id exists in documents.json",
    "source_url": "Every scheme has a source.url",
    "application_url": "Every non-offline scheme has an application_url",
    "source_excerpts": "Every rule has a non-empty source_excerpt",
    "unique_ids": "scheme_id and rule_id values are unique",
    "verified_by": "verified_by is set when status is verified",
}


def value_matches_field(value, field: dict) -> bool:
    field_type = field["type"]
    if field_type == "boolean":
        return isinstance(value, bool)
    if field_type == "enum":
        return value in [option["value"] for option in field.get("options") or []]
    if isinstance(value, bool):
        return False
    if field_type == "integer" and not isinstance(value, int):
        return False
    if field_type == "number" and not isinstance(value, (int, float)):
        return False
    low, high = field.get("min"), field.get("max")
    return (low is None or value >= low) and (high is None or value <= high)


def check_comparison(comparison: dict, where: str, fields: dict, errors: dict) -> None:
    """Check the field, operator and value of a rule or an applies_if condition."""
    field_id = comparison.get("field")
    operator = comparison.get("operator")
    value = comparison.get("value")

    field = fields.get(field_id)
    if field is None:
        errors["rule_fields"].append(f"{where}: unregistered field {field_id!r}")
    if operator not in OPERATORS:
        errors["operators"].append(f"{where}: invalid operator {operator!r}")
        return
    if field is None:
        return

    if operator in ORDERING_OPERATORS and field["type"] not in ("number", "integer"):
        errors["operators"].append(f"{where}: {operator} needs a numeric field, {field_id} is {field['type']}")
    if operator in LIST_OPERATORS:
        if not isinstance(value, list) or not value:
            errors["value_types"].append(f"{where}: {operator} needs a non-empty list")
            return
        values = value
    else:
        values = [value]
    for item in values:
        if not value_matches_field(item, field):
            errors["value_types"].append(f"{where}: {item!r} does not fit {field_id} ({field['type']})")


def validate_scheme(scheme: dict, fields: dict, documents: dict, seen: Counter, errors: dict, warnings: list) -> None:
    scheme_id = scheme.get("scheme_id") or "<missing scheme_id>"
    seen[scheme_id] += 1

    for index, rule in enumerate(scheme.get("rules", [])):
        rule_id = rule.get("rule_id") or f"{scheme_id}.rules[{index}]"
        where = f"{scheme_id}/{rule_id}"
        seen[rule_id] += 1

        kind = rule.get("kind")
        if kind not in RULE_KINDS:
            errors["operators"].append(f"{where}: invalid kind {kind!r}")
        # A manual_check is never evaluated and often has no profile field, e.g. "attendance >= 75%".
        if kind != "manual_check" or rule.get("field") is not None:
            check_comparison(rule, where, fields, errors)
        if rule.get("applies_if"):
            check_comparison(rule["applies_if"], f"{where}/applies_if", fields, errors)

        excerpt = (rule.get("source_excerpt") or "").strip()
        if not excerpt:
            errors["source_excerpts"].append(f"{where}: empty source_excerpt")
        elif len(excerpt.split()) > MAX_EXCERPT_WORDS:
            warnings.append(f"{where}: source_excerpt is over {MAX_EXCERPT_WORDS} words")

    for entry in scheme.get("documents", []):
        document_id = entry.get("document_id")
        where = f"{scheme_id}/documents/{document_id}"
        if document_id not in documents:
            errors["document_ids"].append(f"{where}: unknown document_id")
        if entry.get("applies_if"):
            check_comparison(entry["applies_if"], f"{where}/applies_if", fields, errors)

    if not (scheme.get("source") or {}).get("url"):
        errors["source_url"].append(f"{scheme_id}: missing source.url")
    if not scheme.get("application_url") and scheme.get("application_mode") != ["offline"]:
        errors["application_url"].append(f"{scheme_id}: missing application_url")

    verification = scheme.get("verification") or {}
    if verification.get("status") == "verified" and not verification.get("verified_by"):
        errors["verified_by"].append(f"{scheme_id}: verified without verified_by")


def validate(schemes: list, fields: list, documents: dict) -> tuple[dict, list]:
    """Return (errors keyed by check, warnings). A check passed if its error list is empty."""
    errors: dict[str, list[str]] = {check: [] for check in CHECKS}
    warnings: list[str] = []
    field_index = {field["field_id"]: field for field in fields}
    seen: Counter = Counter()

    for scheme in schemes:
        validate_scheme(scheme, field_index, documents, seen, errors, warnings)

    for identifier, count in seen.items():
        if count > 1:
            errors["unique_ids"].append(f"{identifier}: used {count} times")
    return errors, warnings


def verified_counts(schemes: list) -> Counter:
    return Counter(
        scheme.get("category", "<none>")
        for scheme in schemes
        if (scheme.get("verification") or {}).get("status") == "verified"
    )


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def print_report(schemes: list, errors: dict, warnings: list) -> None:
    width = max(len(text) for text in CHECKS.values())
    print(f"{'Check'.ljust(width)}  Result")
    print(f"{'-' * width}  ------")
    for check, text in CHECKS.items():
        print(f"{text.ljust(width)}  {'FAIL' if errors[check] else 'PASS'}")
        for error in errors[check]:
            print(f"    - {error}")

    for warning in warnings:
        print(f"WARNING: {warning}")

    counts = verified_counts(schemes)
    print(f"\nRecords checked: {len(schemes)}")
    print(f"Verified records: {sum(counts.values())}")
    for category, count in sorted(counts.items()):
        print(f"  {category}: {count}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", type=Path, default=DATA_DIR / "schemes.json", help="scheme record(s) to check")
    args = parser.parse_args()

    records = read_json(args.file)
    schemes = records if isinstance(records, list) else [records]
    fields = read_json(DATA_DIR / "profile_fields.json")
    documents = read_json(DATA_DIR / "documents.json")

    errors, warnings = validate(schemes, fields, documents)
    print_report(schemes, errors, warnings)
    return 1 if any(errors.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
