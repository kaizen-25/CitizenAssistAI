#!/usr/bin/env python3
"""Print eligibility results and the unlock report for one citizen. Run with the backend venv.

Usage:
  python scripts/run_profile.py citizen.json [--schemes path] [--lang en]

citizen.json: {"profile": {"age": 19, ...}, "documents": {"income_certificate": "missing", ...}}
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.engine.eligibility import evaluate_all  # noqa: E402
from app.engine.explain import localize_report, localize_results  # noqa: E402
from app.schemas import Scheme  # noqa: E402
from app.unlock.graph import calculate_unlocks  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("citizen", type=Path)
    parser.add_argument("--schemes", type=Path, default=ROOT / "backend" / "app" / "data" / "schemes.json")
    parser.add_argument("--lang", default="en", choices=["en", "hi"])
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    citizen = json.loads(args.citizen.read_text(encoding="utf-8"))
    records = json.loads(args.schemes.read_text(encoding="utf-8"))
    schemes = [Scheme.model_validate(record) for record in records]

    results = evaluate_all(schemes, citizen.get("profile", {}), citizen.get("documents", {}))
    for result in localize_results(results, args.lang):
        print(f"\n{result.scheme_id}: {result.status} (document_ready={result.document_ready})")
        for rule in result.rules:
            print(f"  {rule.outcome:<15} {rule.explanation}")
        print(f"  documents: {result.documents.model_dump()}")

    print("\nUnlock report:")
    print(json.dumps(localize_report(calculate_unlocks(results), args.lang).model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
