"""Build line-anchored Perseus English for ``play-line`` drama spines.

Each positive ``<l n>`` inside the TEI translation is a real anchor.  The
Greek spine owns both the segment cuts and the set of valid printed refs, so
an English block is snapped to the nearest plain-numbered Greek ref when its
own number is absent.  Output stays sparse: only segments that receive prose
get an English chunk.
"""

from __future__ import annotations

import bisect
import html
from pathlib import Path

from lxml import etree

from .config import BUILD_DIR, SOURCES_DIR, Manifest
from .stage1_common import collapse_ws, local_name, write_json
from .stage1_english import build_alignment


def _nearest_line(valid_sorted: list[int], n: int) -> int:
    """Return the nearest valid line, snapping forward on a tie."""
    if not valid_sorted:
        raise ValueError("play-line English needs at least one numbered Greek ref")
    idx = bisect.bisect_left(valid_sorted, n)
    if idx == 0:
        return valid_sorted[0]
    if idx == len(valid_sorted):
        return valid_sorted[-1]
    before, after = valid_sorted[idx - 1], valid_sorted[idx]
    return before if n - before < after - n else after


def _note_html(el) -> str:
    """Render a small, safe HTML subset from a trusted Perseus TEI note."""
    tags = {
        "bibl": "cite",
        "foreign": "i",
        "gloss": "i",
        "q": "q",
        "quote": "q",
        "title": "cite",
    }

    def render(node, root: bool = False) -> str:
        pieces = [html.escape(node.text or "")]
        for child in node:
            tag = local_name(child) or ""
            inner = render(child)
            html_tag = (
                "strong" if child.get("rend") == "strong" else "em"
            ) if tag == "hi" else tags.get(tag)
            pieces.append(f"<{html_tag}>{inner}</{html_tag}>" if html_tag else inner)
            pieces.append(html.escape(child.tail or ""))
        value = "".join(pieces)
        return collapse_ws(value).strip() if root else value

    return render(el, root=True)


class _LineText:
    def __init__(self, footnotes: dict[str, str], anomalies: list[dict]):
        self.footnotes = footnotes
        self.anomalies = anomalies
        self.note_seq = 0

    def extract(self, line) -> str:
        parts: list[str] = []

        def walk(node, root: bool = False) -> None:
            if node.text:
                parts.append(node.text)
            for child in node:
                tag = local_name(child)
                if tag == "del":
                    if child.tail:
                        parts.append(child.tail)
                    continue
                if tag == "note":
                    if child.get("resp") == "Smyth":
                        self.note_seq += 1
                        raw = collapse_ws(child.get("n") or "").strip() or f"n{self.note_seq}"
                        label = f"{self.note_seq}.{raw}"
                        parts.append(f"[^{label}]")
                        self.footnotes[label] = _note_html(child)
                    else:
                        self.anomalies.append(
                            {"kind": "note_skipped_non_smyth", "resp": child.get("resp")}
                        )
                    if child.tail:
                        parts.append(child.tail)
                    continue
                walk(child)
                if child.tail:
                    parts.append(child.tail)

        walk(line, root=True)
        return collapse_ws("".join(parts)).strip()


def _spine_index(spine: dict) -> tuple[dict[int, dict], list[dict], list[int]]:
    exact: dict[int, dict] = {}
    refs: list[dict] = []
    valid_numbers: set[int] = set()

    for order, segment in enumerate(spine["segments"]):
        for line in segment["lines"]:
            ref = line.get("ref")
            if isinstance(ref, str) and ref.isdigit():
                n = int(ref)
                exact[n] = segment
                refs.append(
                    {"start": n, "end": n, "ref": ref, "segment": segment, "order": order}
                )
                valid_numbers.add(n)
            elif isinstance(ref, str) and ref[:-1].isdigit() and ref[-1:].isalpha():
                n = int(ref[:-1])
                refs.append(
                    {"start": n, "end": n, "ref": ref, "segment": segment, "order": order}
                )
                valid_numbers.add(n)
            elif isinstance(ref, str) and "-" in ref:
                start, end = ref.split("-", 1)
                if start.isdigit() and end.isdigit():
                    refs.append(
                        {
                            "start": int(start),
                            "end": int(end),
                            "ref": ref,
                            "segment": segment,
                            "order": order,
                        }
                    )
                    valid_numbers.update(range(int(start), int(end) + 1))
    if not refs:
        raise ValueError("play-line English needs at least one numbered Greek ref")
    return exact, refs, sorted(valid_numbers)


def _resolve_anchor(
    exact: dict[int, dict], refs: list[dict], valid_numbers: list[int], n: int
) -> tuple[int, str, dict]:
    if n in exact:
        return n, str(n), exact[n]
    snapped = _nearest_line(valid_numbers, n)
    candidates = [item for item in refs if item["start"] <= snapped <= item["end"]]
    target = min(
        candidates,
        key=lambda item: (item["ref"] != str(snapped), item["order"]),
    )
    return snapped, target["ref"], target["segment"]


def _speaker_report(spine: dict, sigla: dict, english_displays: list[str]) -> dict:
    """Compare source speaker text with the mapped Greek roster, without remapping."""
    from . import turns as turns_mod

    greek_roster: list[str] = []
    seen: set[str] = set()
    for segment in spine["segments"]:
        for event in segment.get("speakers", []):
            display, mapped = turns_mod.greek_speaker(event["label"], sigla)
            if mapped and display is not None and display not in seen:
                seen.add(display)
                greek_roster.append(display)

    eng_set = set(english_displays)
    greek_set = set(greek_roster)
    return {
        "english_displays": english_displays,
        "greek_roster": greek_roster,
        "only_in_english": sorted(eng_set - greek_set),
        "only_in_greek": sorted(greek_set - eng_set),
        "matches": eng_set == greek_set,
    }


def parse_translation(
    xml_path: Path,
    spine: dict,
    *,
    work_id: str,
    translation_id: str,
    sigla: dict | None = None,
) -> tuple[dict, dict[str, str], dict]:
    """Parse one ``perseus-play`` TEI and cut it on the Greek segments."""
    tree = etree.parse(str(xml_path))
    translation = tree.find('.//{*}div[@type="translation"]')
    if translation is None:
        raise ValueError(f"no div type='translation' in {xml_path}")

    exact_lines, spine_refs, valid_numbers = _spine_index(spine)
    chunks_by_id: dict[str, dict] = {}
    footnotes: dict[str, str] = {}
    snaps: list[dict] = []
    anomalies: list[dict] = []
    text_parser = _LineText(footnotes, anomalies)
    anchor_count = 0
    english_displays: list[str] = []
    display_seen: set[str] = set()

    for sp_index, speech in enumerate(translation.findall('.//{*}sp'), start=1):
        speaker_el = speech.find('./{*}speaker')
        speaker = (
            collapse_ws("".join(speaker_el.itertext())).strip()
            if speaker_el is not None
            else ""
        )
        if speaker and speaker not in display_seen:
            display_seen.add(speaker)
            english_displays.append(speaker)
        turn_added = False

        for line in speech.findall('.//{*}l'):
            raw_n = line.get("n")
            if raw_n == "0":
                continue
            if not raw_n or not raw_n.isdigit():
                anomalies.append(
                    {"kind": "non_numeric_anchor", "sp": sp_index, "n_raw": raw_n}
                )
                continue
            n = int(raw_n)
            if n <= 0:
                continue
            anchor_count += 1
            tick_n, snapped_ref, segment = _resolve_anchor(
                exact_lines, spine_refs, valid_numbers, n
            )
            if n not in exact_lines:
                snaps.append(
                    {
                        "n_raw": n,
                        "snapped_to": snapped_ref,
                        "segment": segment["id"],
                    }
                )

            text = text_parser.extract(line)
            if not text:
                anomalies.append(
                    {"kind": "empty_anchor", "sp": sp_index, "n_raw": n}
                )
                continue

            chunk = chunks_by_id.get(segment["id"])
            if chunk is None:
                chunk = {
                    "id": segment["id"],
                    "book": segment["book"],
                    "column": segment["column"],
                    "text": "",
                    "notes": [],
                    "markers": [],
                    "bekker": [],
                    "turns": [],
                }
                chunks_by_id[segment["id"]] = chunk

            if chunk["text"]:
                chunk["text"] += " "
            offset = len(chunk["text"])
            if not turn_added:
                if speaker:
                    chunk["turns"].append(
                        {"offset": offset, "speaker": speaker, "display": speaker}
                    )
                else:
                    anomalies.append(
                        {"kind": "missing_speaker", "sp": sp_index, "n_raw": n}
                    )
                turn_added = True
            chunk["bekker"].append({"n": tick_n, "offset": offset, "real": True})
            chunk["text"] += text

    chunks = [
        chunks_by_id[segment["id"]]
        for segment in spine["segments"]
        if segment["id"] in chunks_by_id
    ]
    english = {
        "work": work_id,
        "source": xml_path.name,
        "translation": translation_id,
        "chunks": chunks,
        "chapters": [],
    }
    total_segments = len(spine["segments"])
    report = {
        "work": work_id,
        "translation": translation_id,
        "anchor_count": anchor_count,
        "snaps": snaps,
        "snap_count": len(snaps),
        "segments_with_chunk": len(chunks),
        "segments_total": total_segments,
        "coverage_ratio": len(chunks) / total_segments if total_segments else 0.0,
        "footnotes": len(footnotes),
        "anomalies": anomalies,
        "speakers": _speaker_report(spine, sigla or {}, english_displays),
    }
    return english, footnotes, report


def run(manifest: Manifest, spine: dict) -> tuple[Path, Path, Path]:
    primary = ((manifest.data.get("english") or {}).get("primary") or {})
    xml_path = SOURCES_DIR / primary["source"]
    sigla = ((manifest.data.get("speakers") or {}).get("sigla") or {})
    english, footnotes, report = parse_translation(
        xml_path,
        spine,
        work_id=manifest.work_id,
        translation_id=primary["id"],
        sigla=sigla,
    )

    out_dir = BUILD_DIR / "stage1"
    out_dir.mkdir(parents=True, exist_ok=True)
    english_path = out_dir / "english_chunks.json"
    alignment_path = out_dir / "alignment.json"
    report_path = out_dir / "english_report.json"
    write_json(english_path, english)
    write_json(alignment_path, build_alignment(spine, english))
    write_json(report_path, report)
    write_json(out_dir / "english_footnotes.json", footnotes)
    return english_path, alignment_path, report_path
