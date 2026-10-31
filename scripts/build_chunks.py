#!/usr/bin/env python3
"""Build backend/app/data/chunks.jsonl from verified schemes and their sources (SPEC §7.4). Run with the backend venv."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from structure_scheme import ROOT, read_source  # noqa: E402
from validate_data import DATA_DIR, read_json  # noqa: E402

CHUNK_WORDS = 400
OVERLAP_WORDS = 50


def chunk_words(text: str, size: int = CHUNK_WORDS, overlap: int = OVERLAP_WORDS) -> list[str]:
    words = text.split()
    if not words:
        return []
    step = size - overlap
    return [" ".join(words[start:start + size]) for start in range(0, max(len(words) - overlap, 1), step)]


def render_scheme(scheme: dict) -> str:
    lines = [
        scheme["name"]["en"], f"Department: {scheme['department']}", scheme["summary"], f"Benefits: {scheme['benefits']}",
        *[rule["source_excerpt"] for rule in scheme["rules"]],
        *scheme.get("unmapped_conditions", []),
    ]
    return "\n".join(lines)


def build(schemes: list[dict], read=read_source, root: Path = ROOT) -> list[dict]:
    chunks = []
    seen_files = set()
    for scheme in schemes:
        if scheme["verification"]["status"] != "verified":
            continue
        texts = [render_scheme(scheme)]
        file = scheme["source"].get("file")
        if file and file not in seen_files and (root / file).exists():
            seen_files.add(file)
            texts.append(read(root / file))
        pieces = [piece for text in texts for piece in chunk_words(text)]
        chunks += [
            {
                "chunk_id": f"{scheme['scheme_id']}_c{index}",
                "scheme_id": scheme["scheme_id"],
                "source_url": scheme["source"]["url"],
                "source_title": scheme["source"]["title"],
                "text": piece,
            }
            for index, piece in enumerate(pieces)
        ]
    return chunks


def main() -> int:
    chunks = build(read_json(DATA_DIR / "schemes.json"))
    path = DATA_DIR / "chunks.jsonl"
    path.write_text("".join(json.dumps(chunk, ensure_ascii=False) + "\n" for chunk in chunks), encoding="utf-8")
    print(f"Wrote {len(chunks)} chunks to {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
