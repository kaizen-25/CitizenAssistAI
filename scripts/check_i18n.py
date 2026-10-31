#!/usr/bin/env python3
"""List every Hindi string that is missing, or whose {placeholders} differ from the English one."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLACEHOLDER = re.compile(r"\{\w+\}")


def flatten(strings: dict, prefix: str = "") -> dict[str, str]:
    flat = {}
    for key, value in strings.items():
        if key == "_reviewed":
            continue
        if isinstance(value, dict):
            flat.update(flatten(value, f"{prefix}{key}."))
        else:
            flat[f"{prefix}{key}"] = value
    return flat


def compare(en: dict[str, str], hi: dict[str, str], where: str) -> list[str]:
    problems = []
    for key, english in en.items():
        hindi = hi.get(key, "")
        if english and not hindi:
            problems.append(f"{where}: {key} is missing")
        elif sorted(PLACEHOLDER.findall(english)) != sorted(PLACEHOLDER.findall(hindi)):
            problems.append(f"{where}: {key} has mismatched placeholders")
    return problems


def registry_strings(records) -> tuple[dict, dict]:
    en, hi = {}, {}
    for record_id, record in records:
        for name in ("label", "question"):
            if name in record:
                en[f"{record_id}.{name}"] = record[name]["en"]
                hi[f"{record_id}.{name}"] = record[name]["hi"]
        for option in record.get("options") or []:
            en[f"{record_id}.{option['value']}"] = option["label"]["en"]
            hi[f"{record_id}.{option['value']}"] = option["label"]["hi"]
    return en, hi


def read(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    problems = []
    for name in ("frontend/src/i18n", "backend/app/i18n"):
        problems += compare(flatten(read(f"{name}/en.json")), flatten(read(f"{name}/hi.json")), name)
    fields = read("backend/app/data/profile_fields.json")
    documents = read("backend/app/data/documents.json")
    problems += compare(*registry_strings((f["field_id"], f) for f in fields), "profile_fields.json")
    problems += compare(*registry_strings(documents.items()), "documents.json")

    for problem in problems:
        print(problem)
    print(f"{len(problems)} problem(s).")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
