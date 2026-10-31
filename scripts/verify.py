#!/usr/bin/env python3
"""Show a draft beside its source and publish it into schemes.json. Run with the backend venv.

Usage:
  python scripts/verify.py edu_001 --by initials        # tick each rule interactively
  python scripts/verify.py edu_001 --by claude --yes    # publish after reading the printed review
  python scripts/verify.py edu_001                      # print the review only
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from structure_scheme import DRAFTS_DIR, ROOT, is_verbatim, read_source  # noqa: E402
from validate_data import DATA_DIR, read_json, validate  # noqa: E402


def blockers(draft: dict, source_text: str, schemes: list, fields: list, documents: dict) -> list[str]:
    """Reasons this draft may not be published. Empty means it may."""
    found = []
    if not draft.get("rules"):
        found.append("the draft has no rules")
    for rule in draft.get("rules", []):
        if not is_verbatim(rule.get("source_excerpt", ""), source_text):
            found.append(f"{rule.get('rule_id')}: excerpt is not in the source file")
    if any(s["scheme_id"] == draft["scheme_id"] for s in schemes):
        found.append(f"{draft['scheme_id']} is already in schemes.json")

    public = {key: value for key, value in draft.items() if not key.startswith("_")}
    errors, _ = validate([*schemes, public], fields, documents)
    found += [error for group in errors.values() for error in group]
    return found


def publish(draft: dict, by: str, schemes_path: Path, on: str) -> dict:
    record = {key: value for key, value in draft.items() if not key.startswith("_")}
    record["verification"] = {"status": "verified", "verified_by": by, "verified_on": on}
    schemes = read_json(schemes_path)
    schemes.append(record)
    schemes_path.write_text(json.dumps(schemes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return record


def print_review(draft: dict, source_text: str) -> None:
    print(f"{draft['scheme_id']}: {draft['name']['en']}")
    print(f"Department: {draft['department']}")
    print(f"Source: {draft['source']['url']} ({draft['source'].get('file')})")
    print(f"Apply: {draft.get('application_url')} {draft.get('application_mode')}")
    print(f"\nSummary: {draft['summary']}\nBenefits: {draft['benefits']}\n\nRules:")
    for rule in draft["rules"]:
        found = "in source" if is_verbatim(rule["source_excerpt"], source_text) else "NOT IN SOURCE"
        condition = rule.get("applies_if")
        when = f"  if {condition['field']} {condition['operator']} {condition['value']}" if condition else ""
        check = "manual check" if rule["kind"] == "manual_check" else f"{rule['field']} {rule['operator']} {rule['value']}"
        print(f"  {rule['rule_id']}: {check}{when}\n      [{found}] {rule['source_excerpt']}")
    print("\nDocuments:")
    for document in draft["documents"]:
        condition = document.get("applies_if")
        print(f"  {document['document_id']} ({document['requirement']})" + (f" if {condition}" if condition else ""))
    print("\nUnmapped conditions:")
    for condition in draft["unmapped_conditions"]:
        print(f"  {condition}")
    if draft.get("_review_notes"):
        print("\nReview notes:")
        for note in draft["_review_notes"]:
            print(f"  {note}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scheme_id")
    parser.add_argument("--by", help="who verified this record, written into verified_by")
    parser.add_argument("--yes", action="store_true", help="publish without per-rule prompts")
    args = parser.parse_args()

    path = DRAFTS_DIR / f"{args.scheme_id}.json"
    draft = read_json(path)
    source_text = read_source(ROOT / draft["source"]["file"])
    print_review(draft, source_text)
    if not args.by:
        return 0

    schemes_path = DATA_DIR / "schemes.json"
    found = blockers(
        draft, source_text, read_json(schemes_path),
        read_json(DATA_DIR / "profile_fields.json"), read_json(DATA_DIR / "documents.json"),
    )
    if found:
        print("\nNot published:")
        for reason in found:
            print(f"  {reason}")
        return 1

    if not args.yes:
        for rule in draft["rules"]:
            if input(f"Does the source justify {rule['rule_id']}? [y/N] ").strip().lower() != "y":
                print("Not published.")
                return 1

    publish(draft, args.by, schemes_path, date.today().isoformat())
    path.unlink()
    print(f"\nPublished {args.scheme_id} to schemes.json, verified by {args.by}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
