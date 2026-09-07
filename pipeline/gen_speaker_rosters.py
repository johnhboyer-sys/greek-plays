#!/usr/bin/env python3
"""Harvest play-line speaker sigla and maintain manifest roster blocks.

The built book is preferred because it shows exactly what stage7 emits. The
single-work stage1 spine is a fallback when its ``work`` id matches. Pass
``--spine`` for a raw Greek export and ``--perseus`` for a Perseus English TEI
to propose displays by first-appearance alignment. Report mode is the default;
``--write`` replaces only a supported top-level ``speakers:`` block, so comments
elsewhere in the manifest remain byte-for-byte intact.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from collections import Counter
from pathlib import Path

import yaml
from lxml import etree


ROOT = Path(__file__).resolve().parents[1]

_SPEAKERS_BLOCK = re.compile(r"(?ms)^speakers:\s*\n.*?(?=^\S|\Z)")
_BOOKS_HEADING = re.compile(r"(?m)^books:\s*$")
_TOP_LEVEL_SPEAKERS = re.compile(r"(?m)^speakers\s*:")
_SUPPORTED_SPEAKERS_HEADING = re.compile(r"^speakers:\s*$")
# Same prefixes stage1 uses to keep strophe markers out of the speaker stream
# (stage1_greek._PLAY_LINE_STROPHE_RE) -- "ἐπῳδός" listed before "ἐπῳδ" for
# Persians' spelled-out epode marker (see that module for why).
_STROPHE_RE = re.compile(
    r"^\[?(στρ|ἀντ|ἐπῳδός|ἐπῳδ|μεσῳδ|ἐφυμν|ἐφ|Str|Ant|Ep|Epode)\b"
)


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


def _local(tag) -> str:
    if isinstance(tag, str):
        return etree.QName(tag).localname
    return ""


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def _first_appearances(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _letters(label: str) -> str:
    return "".join(ch for ch in label if ch.isalpha()).casefold()


def _is_caps_form(label: str) -> bool:
    letters = [ch for ch in label if ch.isalpha()]
    return bool(letters) and all(ch.isupper() for ch in letters)


def _caps_matches_siglum(caps: str, siglum: str) -> bool:
    caps_letters = _letters(caps)
    sig_letters = _letters(siglum)
    return bool(caps_letters and sig_letters) and caps_letters.startswith(sig_letters)


def labels_from_book_json(path: Path) -> tuple[list[str], dict[str, str]]:
    """Ordered ``segments[].speakers[].label`` plus first emitted displays."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    labels: list[str] = []
    displays: dict[str, str] = {}
    for label, display in _event_rows(doc):
        labels.append(label)
        if isinstance(display, str) and display:
            displays.setdefault(label, display)
    return labels, displays


def labels_from_spine_xml(path: Path) -> list[str]:
    """Ordered ``<label type="speaker">`` text; strophe markers dropped."""
    tree = etree.parse(str(path))
    labels: list[str] = []
    for el in tree.iter():
        if _local(el.tag) != "label" or el.get("type") != "speaker":
            continue
        text = re.sub(r"\s+", " ", "".join(el.itertext())).strip()
        if not text or _STROPHE_RE.match(text):
            continue
        labels.append(text)
    return labels


def speakers_from_perseus(path: Path) -> list[str]:
    """Ordered ``<speaker>`` names from a Perseus English TEI file."""
    tree = etree.parse(str(path))
    names: list[str] = []
    for el in tree.iter():
        if _local(el.tag) != "speaker":
            continue
        name = re.sub(r"\s+", " ", "".join(el.itertext())).strip()
        if name:
            names.append(name)
    return names


def _group_labels(distinct: list[str]) -> list[list[str]]:
    """Collapse full-caps first appearances with matching abbreviated sigla."""
    caps = [label for label in distinct if _is_caps_form(label)]
    owner: dict[str, str] = {}
    for label in distinct:
        if _is_caps_form(label):
            owner[label] = label
            continue
        match = next((cap for cap in caps if _caps_matches_siglum(cap, label)), None)
        owner[label] = match if match is not None else label
    groups: list[list[str]] = []
    index: dict[str, int] = {}
    for label in distinct:
        key = owner[label]
        if key not in index:
            index[key] = len(groups)
            groups.append([])
        groups[index[key]].append(label)
    return groups


def align_perseus(
    greek_labels: list[str],
    perseus_names: list[str],
) -> tuple[dict[str, str], list[str], list[str]]:
    """Zip first-appearance Greek groups to first-appearance Perseus names.

    Returns ``(mapping, leftover_greek, leftover_perseus)``. Never invents a
    name: leftovers stay residue for manual review.
    """
    greek_distinct = _first_appearances([lab for lab in greek_labels if lab != "—"])
    perseus_distinct = _first_appearances([name for name in perseus_names if name])
    groups = _group_labels(greek_distinct)
    n = min(len(groups), len(perseus_distinct))
    mapping: dict[str, str] = {}
    for i in range(n):
        display = perseus_distinct[i]
        for label in groups[i]:
            mapping[label] = display
    leftover_greek = [label for group in groups[n:] for label in group]
    leftover_perseus = perseus_distinct[n:]
    return mapping, leftover_greek, leftover_perseus


def harvest(
    work_id: str,
    *,
    spine: Path | None = None,
) -> tuple[Counter[str], dict[str, str], str | None]:
    """Return counts, emitted display hints, and the artifact used."""
    if spine is not None:
        labels = labels_from_spine_xml(spine)
        return Counter(labels), {}, _rel(spine)

    book = ROOT / "build" / "dist" / work_id / "book-01.json"
    if book.exists():
        labels, displays = labels_from_book_json(book)
        return Counter(labels), displays, _rel(book)

    spine_path = ROOT / "build" / "stage1" / "greek_spine.json"
    if spine_path.exists():
        doc = json.loads(spine_path.read_text(encoding="utf-8"))
        if doc.get("work") == work_id:
            labels: list[str] = []
            displays: dict[str, str] = {}
            for label, display in _event_rows(doc):
                labels.append(label)
                if isinstance(display, str) and display:
                    displays.setdefault(label, display)
            return Counter(labels), displays, _rel(spine_path)
    return Counter(), {}, None


def propose(
    observed: Counter[str],
    emitted: dict[str, str],
    declared: dict,
    perseus: dict[str, str] | None = None,
) -> tuple[dict[str, str | None], list[str]]:
    """Build an ordered proposal and list labels that need human names."""
    order = list(observed)
    for source in (declared, perseus or {}):
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
        elif perseus and label in perseus:
            proposal[label] = perseus[label]
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


def _top_level_speakers_hits(text: str) -> list[str]:
    hits = []
    for line in text.splitlines():
        if line.startswith((" ", "\t")):
            continue
        if _TOP_LEVEL_SPEAKERS.match(line):
            hits.append(line)
    return hits


def _load_mapping(text: str, *, origin: str) -> dict:
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"{origin}: not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{origin}: expected a YAML mapping at the top level")
    return data


def _require_single_speakers(text: str, data: dict, *, origin: str) -> None:
    n_text = len(_top_level_speakers_hits(text))
    n_parsed = 1 if "speakers" in data else 0
    if n_text != 1 or n_parsed != 1:
        raise ValueError(
            f"{origin}: need exactly one top-level speakers key "
            f"(text {n_text}, parsed {n_parsed})"
        )


def _assert_other_keys_equal(original: dict, proposed: dict, *, origin: str) -> None:
    for key, value in original.items():
        if key == "speakers":
            continue
        if key not in proposed or proposed[key] != value:
            raise ValueError(f"{origin}: top-level key {key!r} did not round-trip")
    for key in proposed:
        if key == "speakers":
            continue
        if key not in original:
            raise ValueError(f"{origin}: unexpected top-level key {key!r}")


def _atomic_write(path: Path, text: str) -> None:
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def write_block(path: Path, roster: dict[str, str | None]) -> None:
    text = path.read_text(encoding="utf-8")
    original = _load_mapping(text, origin=path.name)
    hits = _top_level_speakers_hits(text)
    if len(hits) > 1:
        raise ValueError(f"{path.name}: duplicate top-level speakers key")
    yaml_has = "speakers" in original
    if yaml_has and not hits:
        raise ValueError(
            f"{path.name}: unsupported speakers form (parsed speakers key "
            "has no top-level 'speakers:' line)"
        )
    if hits and not yaml_has:
        raise ValueError(f"{path.name}: unsupported speakers form (unparsed top-level key)")
    if hits:
        heading = hits[0]
        if _SUPPORTED_SPEAKERS_HEADING.match(heading) is None:
            raise ValueError(
                f"{path.name}: unsupported speakers form {heading!r}; "
                "expected a block heading 'speakers:' "
                "(comment-on-same-line and inline mappings are refused)"
            )
        if _SPEAKERS_BLOCK.search(text) is None:
            raise ValueError(f"{path.name}: unsupported speakers form; cannot isolate the block")
        updated = _SPEAKERS_BLOCK.sub(render_block(roster), text, count=1)
    elif _BOOKS_HEADING.search(text):
        updated = _BOOKS_HEADING.sub(render_block(roster) + "books:", text, count=1)
    else:
        raise ValueError(f"{path.name}: cannot place speakers block; no books heading")

    proposed = _load_mapping(updated, origin=f"{path.name} (proposed)")
    _require_single_speakers(updated, proposed, origin=f"{path.name} (proposed)")
    _assert_other_keys_equal(original, proposed, origin=path.name)
    _atomic_write(path, updated)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="rewrite manifest speakers blocks")
    parser.add_argument(
        "--perseus",
        type=Path,
        help="Perseus English TEI XML whose <speaker> names seed display proposals",
    )
    parser.add_argument(
        "--spine",
        type=Path,
        help="Raw Greek export XML; harvest <label type='speaker'> instead of book-01.json",
    )
    args = parser.parse_args(argv)
    if args.perseus is not None and not args.perseus.is_file():
        raise SystemExit(f"--perseus not found: {args.perseus}")
    if args.spine is not None and not args.spine.is_file():
        raise SystemExit(f"--spine not found: {args.spine}")
    perseus_names = speakers_from_perseus(args.perseus) if args.perseus is not None else None
    failed = False
    for path, data in _play_line_manifests():
        work_id = data["work"]["id"]
        declared = ((data.get("speakers") or {}).get("sigla") or {})
        observed, emitted, source = harvest(work_id, spine=args.spine)
        perseus_map = None
        leftover_english: list[str] = []
        if perseus_names is not None:
            perseus_map, _, leftover_english = align_perseus(list(observed), perseus_names)
        roster, unresolved = propose(observed, emitted, declared, perseus_map)
        print(f"{work_id}: {sum(observed.values())} events from {source or 'no build artifact'}")
        for label in observed:
            display = roster.get(label)
            suggestion = display if display is not None else ("unattributed" if label == "—" else "TODO")
            print(f"  {label!r}: {observed[label]} -> {suggestion}")
        if leftover_english:
            print(
                "  unmatched Perseus names: "
                + ", ".join(repr(name) for name in leftover_english)
            )
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
