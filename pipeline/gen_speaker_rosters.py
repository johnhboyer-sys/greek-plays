#!/usr/bin/env python3
"""Harvest play-line speaker sigla and maintain manifest roster blocks.

The built book is preferred because it shows exactly what stage7 emits. The
single-work stage1 spine is a fallback when its ``work`` id matches. Report
mode is the default; ``--write`` replaces only each top-level ``speakers:``
block, so comments elsewhere in the manifest remain byte-for-byte intact.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]

# Curated starter proposals. Unknown plays still get a useful harvest report,
# but --write refuses to put guessed character names into a manifest.
CURATED: dict[str, dict[str, str | None]] = {
    "agamemnon": {
        "ΦΥΛΑΞ": "Watchman",
        "ΧΟΡΟΣ": "Chorus",
        "Χο.": "Chorus",
        "ΚΛΥΤΑΙΜΗΣΤΡΑ": "Clytaemestra",
        "Κλ.": "Clytaemestra",
        "ΚΗΡΥΞ": "Herald",
        "Κη.": "Herald",
        "ΑΓΑΜΕΜΝΩΝ": "Agamemnon",
        "Αγ.": "Agamemnon",
        "ΚΑΣΣΑΝΔΡΑ": "Cassandra",
        "Κα.": "Cassandra",
        "ΑΙΓΙΣΘΟΣ": "Aegisthus",
        "Αι.": "Aegisthus",
        **{f"{n}.": f"Elder {n}" for n in range(1, 13)},
        "—": None,
    },
}

_SPEAKERS_BLOCK = re.compile(r"(?ms)^speakers:\n.*?(?=^\S|\Z)")
_BOOKS_HEADING = re.compile(r"(?m)^books:\s*$")


def _play_line_manifests() -> list[tuple[Path, dict]]:
    manifests = []
    for path in sorted((ROOT / "manifests").glob("*.yaml")):
        if path.name == "authors.yaml":
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and (data.get("citation") or {}).get("scheme") == "play-line":
            manifests.append((path, data))
    return manifests


def _event_rows(doc: dict):
    for segment in doc.get("segments", []):
        for event in segment.get("speakers", []):
            label = event.get("label")
            if isinstance(label, str) and label:
                yield label, event.get("display")


def harvest(work_id: str) -> tuple[Counter[str], dict[str, str], str | None]:
    """Return counts, emitted display hints, and the artifact used."""
    counts: Counter[str] = Counter()
    displays: dict[str, str] = {}
    book = ROOT / "build" / "dist" / work_id / "book-01.json"
    if book.exists():
        doc = json.loads(book.read_text(encoding="utf-8"))
        for label, display in _event_rows(doc):
            counts[label] += 1
            if isinstance(display, str) and display:
                displays.setdefault(label, display)
        return counts, displays, str(book.relative_to(ROOT))

    spine_path = ROOT / "build" / "stage1" / "greek_spine.json"
    if spine_path.exists():
        doc = json.loads(spine_path.read_text(encoding="utf-8"))
        if doc.get("work") == work_id:
            for label, display in _event_rows(doc):
                counts[label] += 1
                if isinstance(display, str) and display:
                    displays.setdefault(label, display)
            return counts, displays, str(spine_path.relative_to(ROOT))
    return counts, displays, None


def propose(
    work_id: str,
    observed: Counter[str],
    emitted: dict[str, str],
    declared: dict,
) -> tuple[dict[str, str | None], list[str]]:
    """Build an ordered proposal and list labels that need human names."""
    known = CURATED.get(work_id, {})
    order = list(observed)
    for source in (declared, known):
        for label in source:
            if label not in order:
                order.append(label)
    if "—" not in order:
        order.append("—")

    proposal: dict[str, str | None] = {}
    unresolved = []
    for label in order:
        if label == "—":
            proposal[label] = None
        elif isinstance(declared.get(label), str) and declared[label]:
            proposal[label] = declared[label]
        elif label in known:
            proposal[label] = known[label]
        elif label in emitted:
            proposal[label] = emitted[label]
        else:
            unresolved.append(label)
    return proposal, unresolved


def render_block(roster: dict[str, str | None]) -> str:
    lines = [
        "speakers:",
        "  # Greek edition siglum -> canonical English display name.",
        "  sigla:",
    ]
    for label, display in roster.items():
        key = json.dumps(label, ensure_ascii=False)
        value = "null" if display is None else json.dumps(display, ensure_ascii=False)
        lines.append(f"    {key}: {value}")
    return "\n".join(lines) + "\n\n"


def write_block(path: Path, roster: dict[str, str | None]) -> None:
    text = path.read_text(encoding="utf-8")
    block = render_block(roster)
    if _SPEAKERS_BLOCK.search(text):
        updated = _SPEAKERS_BLOCK.sub(block, text, count=1)
    elif _BOOKS_HEADING.search(text):
        updated = _BOOKS_HEADING.sub(block + "books:", text, count=1)
    else:
        raise ValueError(f"{path.name}: cannot place speakers block; no books heading")
    path.write_text(updated, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="rewrite manifest speakers blocks")
    args = parser.parse_args(argv)
    failed = False
    for path, data in _play_line_manifests():
        work_id = data["work"]["id"]
        declared = ((data.get("speakers") or {}).get("sigla") or {})
        observed, emitted, source = harvest(work_id)
        roster, unresolved = propose(work_id, observed, emitted, declared)
        print(f"{work_id}: {sum(observed.values())} events from {source or 'no build artifact'}")
        for label in observed:
            display = roster.get(label)
            suggestion = display if display is not None else ("unattributed" if label == "—" else "TODO")
            print(f"  {label!r}: {observed[label]} -> {suggestion}")
        if unresolved:
            failed = True
            print(f"  unresolved: {', '.join(repr(label) for label in unresolved)}")
            if args.write:
                print("  not written: resolve every canonical display first")
        elif args.write:
            write_block(path, roster)
            print(f"  wrote {path.relative_to(ROOT)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
