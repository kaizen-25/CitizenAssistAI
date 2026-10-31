#!/usr/bin/env python3
"""Draft ONE unverified scheme record from an official source. Run with the backend venv.

Usage:
  python scripts/structure_scheme.py sources/edu_001.pdf --id edu_001 [--url URL] [--title TITLE] [--timeout 120]
      [--focus "scheme name"] [--start "text to begin reading from"]

The LLM only structures the text. Code then rejects anything it cannot trace back to that text:
an excerpt that is not verbatim, a number missing from its excerpt, an unregistered field, or a
URL that is not literally in the source. Rejected items go to `_review_notes`.
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_data import DATA_DIR, check_comparison, read_json  # noqa: E402

DRAFTS_DIR = DATA_DIR / "drafts"
MANIFEST = ROOT / "sources" / "manifest.json"
MAX_SOURCE_CHARS = 40000
LAKH = 100000

SYSTEM_PROMPT = """You structure one official Indian government scheme document into JSON.
Use ONLY the supplied source text. Never use outside knowledge, and never guess.
- source_excerpt must be copied word for word from the source, at most 30 words.
- Create a hard rule only when the condition maps exactly onto a listed profile field.
- Use kind "manual_check" with empty field and operator for a real criterion that no field can express.
- Anything ambiguous goes in unmapped_conditions, copied from the source.
- value_json and applies_if_value_json hold JSON: 250000, true, "Punjab" or ["SC","ST"]. Use empty strings when unused.
- For a state scheme, add a hard rule on the state field only if the source says so.
- application_url must appear literally in the source, otherwise use an empty string.
- A value on an enum field must be one of that field's listed options."""

DRAFT_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "level": {"type": "string", "enum": ["central", "state"]},
        "state": {"type": "string"},
        "category": {"type": "string", "enum": ["education", "social_welfare"]},
        "department": {"type": "string"},
        "summary": {"type": "string"},
        "benefits": {"type": "string"},
        "rules": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": ["hard", "manual_check"]},
                    "field": {"type": "string"},
                    "operator": {"type": "string"},
                    "value_json": {"type": "string"},
                    "applies_if_field": {"type": "string"},
                    "applies_if_operator": {"type": "string"},
                    "applies_if_value_json": {"type": "string"},
                    "source_excerpt": {"type": "string"},
                },
                "required": ["kind", "source_excerpt"],
            },
        },
        "documents": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string"},
                    "source_text": {"type": "string"},
                    "requirement": {"type": "string", "enum": ["mandatory", "optional"]},
                    "applies_if_field": {"type": "string"},
                    "applies_if_operator": {"type": "string"},
                    "applies_if_value_json": {"type": "string"},
                },
                "required": ["source_text", "requirement"],
            },
        },
        "unmapped_conditions": {"type": "array", "items": {"type": "string"}},
        "application_url": {"type": "string"},
        "application_mode": {"type": "array", "items": {"type": "string", "enum": ["online", "offline"]}},
    },
    "required": ["name", "level", "category", "department", "summary", "benefits", "rules", "documents"],
}


class _TextExtractor(HTMLParser):
    SKIPPED = {"script", "style", "noscript", "template"}

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.links: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIPPED:
            self.skip_depth += 1
        href = dict(attrs).get("href")
        if tag == "a" and href and href.startswith("http"):
            self.links.append(href)

    def handle_endtag(self, tag):
        if tag in self.SKIPPED and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data):
        if not self.skip_depth:
            self.parts.append(data)


def read_source(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader

        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    text = path.read_text(encoding="utf-8", errors="replace")
    if suffix in (".html", ".htm"):
        extractor = _TextExtractor()
        extractor.feed(text)
        return "\n".join([" ".join(extractor.parts), *extractor.links])
    return text


def normalize(text: str) -> str:
    return " ".join(text.split()).casefold()


def is_verbatim(excerpt: str, source_text: str) -> bool:
    return bool(excerpt.strip()) and normalize(excerpt) in normalize(source_text)


def number_in_text(value: float, text: str) -> bool:
    """True if the number is written in the text as digits, or in lakh or thousand form."""
    plain = normalize(text).replace(",", "")
    forms = [f"{value:g}" if value < 1e6 else str(int(value))]
    if value >= LAKH:
        lakhs = f"{value / LAKH:g}"
        forms += [f"{lakhs}\\s*(?:lakhs?|lacs?)", f"{value / LAKH:.2f}\\s*(?:lakhs?|lacs?)"]
    if value >= 1000 and value % 1000 == 0:
        forms.append(f"{value / 1000:g}\\s*(?:thousand|k\\b)")
    return any(re.search(rf"(?<!\d)(?<!\d\.){form.replace('.', chr(92) + '.')}(?![\d])", plain) for form in forms)


def _parse_value(value_json: str):
    return json.loads(value_json)


def _condition(raw: dict) -> dict | None:
    if not raw.get("applies_if_field"):
        return None
    return {
        "field": raw["applies_if_field"],
        "operator": raw.get("applies_if_operator"),
        "value": _parse_value(raw.get("applies_if_value_json") or "null"),
    }


def _problems(comparison: dict, fields: dict) -> list[str]:
    errors = {"rule_fields": [], "operators": [], "value_types": []}
    check_comparison(comparison, "rule", fields, errors)
    return [error for found in errors.values() for error in found]


def _hard_rule_problem(raw: dict, excerpt: str, fields: dict) -> tuple[dict | None, str | None]:
    """Return (rule fields, None) or (None, why it was rejected)."""
    try:
        comparison = {"field": raw.get("field"), "operator": raw.get("operator"), "value": _parse_value(raw.get("value_json") or "null")}
        condition = _condition(raw)
    except ValueError:
        return None, "value is not valid JSON"

    problems = _problems(comparison, fields) + (_problems(condition, fields) if condition else [])
    if problems:
        return None, "; ".join(problems)

    values = comparison["value"] if isinstance(comparison["value"], list) else [comparison["value"]]
    for value in values:
        if isinstance(value, (int, float)) and not isinstance(value, bool) and not number_in_text(value, excerpt):
            return None, f"number {value} is not in its excerpt"
    return {**comparison, "applies_if": condition}, None


def _clean_rules(raw_rules: list, scheme_id: str, source_text: str, fields: dict) -> tuple[list, list, list]:
    rules, unmapped, notes = [], [], []
    for raw in raw_rules:
        excerpt = (raw.get("source_excerpt") or "").strip()
        if not is_verbatim(excerpt, source_text):
            notes.append(f"Rejected rule, excerpt not verbatim: {excerpt!r}")
            continue

        rule_id = f"{scheme_id}_r{len(rules) + 1}"
        if raw.get("kind") == "manual_check":
            rules.append({"rule_id": rule_id, "kind": "manual_check", "source_excerpt": excerpt})
            continue

        comparison, problem = _hard_rule_problem(raw, excerpt, fields)
        if problem:
            notes.append(f"Moved to unmapped_conditions ({problem}): {excerpt!r}")
            unmapped.append(excerpt)
            continue
        rules.append({"rule_id": rule_id, **comparison, "kind": "hard", "source_excerpt": excerpt})
    return rules, unmapped, notes


def _clean_documents(raw_documents: list, source_text: str, fields: dict, documents: dict) -> tuple[list, list, list]:
    cleaned, unmapped, notes = [], [], []
    seen = set()
    for raw in raw_documents:
        text = (raw.get("source_text") or "").strip()
        document_id = raw.get("document_id")
        if document_id not in documents:
            notes.append(f"Unmapped document, no matching document_id: {text!r}")
            if is_verbatim(text, source_text):
                unmapped.append(f"Document: {text}")
            continue
        if not is_verbatim(text, source_text):
            notes.append(f"Rejected document {document_id}, text not verbatim: {text!r}")
            continue
        if document_id in seen:
            continue

        try:
            condition = _condition(raw)
        except ValueError:
            condition = {"field": None, "operator": None, "value": None}
        if condition and _problems(condition, fields):
            notes.append(f"Moved document to unmapped_conditions, bad condition: {text!r}")
            unmapped.append(f"Document: {text}")
            continue

        seen.add(document_id)
        cleaned.append({"document_id": document_id, "requirement": raw.get("requirement", "mandatory"), "applies_if": condition})
    return cleaned, unmapped, notes


def sanitize_draft(raw: dict, source_text: str, scheme_id: str, source: dict, fields: dict, documents: dict) -> dict:
    rules, unmapped, notes = _clean_rules(raw.get("rules", []), scheme_id, source_text, fields)
    docs, doc_unmapped, doc_notes = _clean_documents(raw.get("documents", []), source_text, fields, documents)
    notes += doc_notes

    kept_conditions = []
    for condition in raw.get("unmapped_conditions", []):
        if is_verbatim(condition, source_text):
            kept_conditions.append(condition.strip())
        else:
            notes.append(f"Rejected unmapped condition, not verbatim: {condition!r}")

    url = (raw.get("application_url") or "").strip()
    if url and url not in source_text:
        notes.append(f"Rejected application_url, not in source: {url!r}")
        url = ""

    level = raw.get("level")
    if level == "state" and not any(rule.get("field") == "state" for rule in rules):
        notes.append("State scheme has no hard rule on state (SPEC §14.8).")

    return {
        "scheme_id": scheme_id,
        "name": {"en": raw.get("name", "")},
        "level": level,
        "state": raw.get("state") or None,
        "category": raw.get("category"),
        "department": raw.get("department", ""),
        "summary": raw.get("summary", ""),
        "benefits": raw.get("benefits", ""),
        "rules": rules,
        "documents": docs,
        "unmapped_conditions": kept_conditions + unmapped + doc_unmapped,
        "application_url": url or None,
        "application_mode": raw.get("application_mode", []),
        "source": source,
        "verification": {"status": "unverified", "verified_by": None, "verified_on": None},
        "_review_notes": notes,
    }


def build_user_prompt(source_text: str, fields: list, documents: dict, focus: str = "", start: str = "") -> str:
    offset = normalize_offset(source_text, start)
    field_lines = [
        f"- {f['field_id']} ({f['type']}"
        + (f", unit {f['unit']}" if f.get("unit") else "")
        + (f", options {[o['value'] for o in f['options']]}" if f.get("options") else "")
        + ")"
        for f in fields
    ]
    document_lines = [f"- {doc_id}: {doc['label']['en']}" for doc_id, doc in documents.items()]
    return "\n".join([
        "Profile fields:", *field_lines,
        "", "Operators: eq neq gt gte lt lte in not_in",
        "", "Document ids:", *document_lines,
        *(["", f"This document covers several schemes. Structure ONLY this one: {focus}"] if focus else []),
        "", "Source text:", source_text[offset:offset + MAX_SOURCE_CHARS],
    ])


def normalize_offset(source_text: str, start: str) -> int:
    """Where the prompt's slice begins. Long documents can be read from a section heading."""
    return max(source_text.find(start), 0) if start else 0


def manifest_entry(file: Path) -> dict:
    if not MANIFEST.exists():
        return {}
    relative = file.resolve().relative_to(ROOT).as_posix() if file.resolve().is_relative_to(ROOT) else file.name
    return next((e for e in read_json(MANIFEST) if e.get("file") == relative), {})


def main() -> int:
    from app.llm.provider import complete_json

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file", type=Path)
    parser.add_argument("--id", required=True, dest="scheme_id")
    parser.add_argument("--url")
    parser.add_argument("--title")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--focus", default="", help="the one scheme to structure when a document covers several")
    parser.add_argument("--start", default="", help="begin reading a long document from this text")
    args = parser.parse_args()

    entry = manifest_entry(args.file)
    url = args.url or entry.get("url")
    if not url:
        return print("A source URL is required: pass --url or add the file to sources/manifest.json.") or 1

    source_text = read_source(args.file)
    if not source_text.strip():
        return print(f"No text could be read from {args.file}. It may be a scanned PDF.") or 1

    fields = read_json(DATA_DIR / "profile_fields.json")
    documents = read_json(DATA_DIR / "documents.json")
    raw = complete_json(SYSTEM_PROMPT, build_user_prompt(source_text, fields, documents, args.focus, args.start), DRAFT_SCHEMA, timeout=args.timeout)
    if raw is None:
        return print("No LLM response. Check LLM_PROVIDER and that a provider is reachable.") or 1

    source = {
        "url": url,
        "title": args.title or entry.get("title", ""),
        "published": None,
        "retrieved_on": entry.get("retrieved_on", date.today().isoformat()),
        "file": entry.get("file") or args.file.as_posix(),
    }
    draft = sanitize_draft(raw, source_text, args.scheme_id, source, {f["field_id"]: f for f in fields}, documents)

    DRAFTS_DIR.mkdir(exist_ok=True)
    path = DRAFTS_DIR / f"{args.scheme_id}.json"
    path.write_text(json.dumps(draft, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Draft written to {path}")
    for note in draft["_review_notes"]:
        print(f"NOTE: {note}")
    return subprocess.run([sys.executable, str(Path(__file__).parent / "validate_data.py"), "--file", str(path)]).returncode


if __name__ == "__main__":
    sys.exit(main())
