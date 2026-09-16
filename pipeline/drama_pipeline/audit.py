"""Per-play audit sheet: `python -m drama_pipeline.audit --work <id>`.

Reads the outputs of the most recent `all --work <id>` (`build/dist/<id>/`
and `build/stage1/*_report.json`) and writes `build/audit/<id>.md`, one
Markdown sheet gathering, per English column, the figures a reviewer needs
to check that column against the Greek: the pipeline's own alignment
reports plus a handful of scans of the built text and the raw bench
sources. `--all` rebuilds and audits every manifest and also writes
`build/audit/INDEX.md`, one row per play with the corpus totals.

These counts are pointers for a reviewer, not verdicts (John, 2026-09-14).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

from .config import BUILD_DIR, REPO_ROOT, SOURCES_DIR, Manifest
from .stage1_turn_english import _SPEAKER_LINE

AUDIT_DIR = BUILD_DIR / "audit"
MANIFESTS_DIR = REPO_ROOT / "manifests"
MAX_ROWS = 40

_FOLD_RE = re.compile(r"[^A-Za-z]")
_MARKER_RE = re.compile(r"\[\^([^\]\s]+)\]")
_DIRECTION_RE = re.compile(r"_[^_\n]+_")
_STAGE_WORD_RE = re.compile(r"^(Enter|Exit|Exeunt|Re-enter|Scene)\b")
_STRAY_NOTE_LINE_RE = re.compile(r"^[1-9]\d*\s[A-Za-z]")
_CAPS_RUN_RE = re.compile(r"[A-Z]{3,}")
_GLUED_DIGIT_RE = re.compile(r"[A-Za-z]\d|\d[A-Za-z]")
_ALLOWED_NON_ASCII = "’‘“”—–…"


def _is_accented_latin(ch: str) -> bool:
    """True for a combining diacritical mark or a Latin letter carrying one
    (`cursèd`, `wingèd`, `Cyllené`, `Phaéthon`): ordinary English verse
    spelling, not scan noise (review finding 9)."""
    category = unicodedata.category(ch)
    if category == "Mn":
        return True
    if category.startswith("L") and "LATIN" in unicodedata.name(ch, ""):
        return True
    return False


def _fold(text: str) -> str:
    return _FOLD_RE.sub("", text).lower()


def _strip_markers(text: str) -> str:
    return _MARKER_RE.sub("", text)


def _ref_range(greek_lines: list[dict]) -> str:
    if not greek_lines:
        return "-"
    first, last = greek_lines[0].get("ref"), greek_lines[-1].get("ref")
    return first if first == last else f"{first}–{last}"


def _table(headers: list[str], rows: list[list[str]], cap: int | None = MAX_ROWS) -> tuple[str, int]:
    """A Markdown table, capped at `cap` rows unless `cap` is None (the
    per-play sheet's sections keep it short this way; the corpus-wide
    INDEX table is never capped — every play gets its row); returns
    (markdown, total)."""
    total = len(rows)
    shown = rows if cap is None else rows[:cap]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    lines.extend("| " + " | ".join(str(c) for c in row) + " |" for row in shown)
    if cap is not None and total > cap:
        lines.append(f"\n_{total} total, first {cap} shown._")
    return "\n".join(lines), total


# --------------------------------------------------------------- loading --

def load_book(dist_dir: Path) -> tuple[list[dict], list[str]]:
    """Concatenate every build/dist/<id>/book-*.json's segments in order."""
    segments: list[dict] = []
    roster: list[str] = []
    for path in sorted(dist_dir.glob("book-*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        segments.extend(data.get("segments") or [])
        for name in data.get("speakerRoster") or []:
            if name not in roster:
                roster.append(name)
    return segments, roster


def load_footnotes(dist_dir: Path) -> dict:
    path = dist_dir / "footnotes.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def columns_for(manifest: Manifest) -> list[dict]:
    """Every configured English column: id, slot, model, source, form."""
    english = manifest.data.get("english") or {}
    registry = (manifest.data.get("registry") or {}).get("translations") or []
    forms = {
        item.get("id"): item.get("form")
        for item in registry
        if isinstance(item, dict)
    }
    cols = []
    for slot in ("primary", "secondary", "third"):
        cfg = english.get(slot) or {}
        if not cfg:
            continue
        cols.append({
            "slot": slot,
            "id": cfg.get("id"),
            "model": cfg.get("model"),
            "source": cfg.get("source"),
            "form": forms.get(cfg.get("id")) or "prose",
        })
    for entry in english.get("overlays") or []:
        cols.append({
            "slot": "overlay",
            "id": entry.get("id"),
            "model": entry.get("model"),
            "source": entry.get("source"),
            "form": forms.get(entry.get("id")) or "prose",
        })
    return cols


def _report_path(stage1_dir: Path, col: dict) -> Path:
    if col["slot"] == "primary":
        return stage1_dir / "english_report.json"
    if col["slot"] == "secondary":
        return stage1_dir / "secondary_report.json"
    if col["slot"] == "third":
        return stage1_dir / "third_report.json"
    return stage1_dir / f"overlay_{col['id']}_report.json"


def load_report(stage1_dir: Path, col: dict, work_id: str) -> dict | None:
    """The column's report, refusing one left over from a different play
    (build/stage1 is single-work scratch; a play with no third slot can
    otherwise inherit the previous play's third_report.json)."""
    path = _report_path(stage1_dir, col)
    if not path.exists():
        return None
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("work") != work_id:
        return None
    return report


def _pieces(seg: dict, col: dict) -> list[dict]:
    if col["slot"] == "primary":
        piece = seg.get("english")
        return [piece] if piece else []
    if col["slot"] == "secondary":
        return seg.get("ross") or []
    if col["slot"] == "third":
        return seg.get("third") or []
    return (seg.get("overlays") or {}).get(col["id"]) or []


def _col_text(seg: dict, col: dict) -> str:
    return "\n\n".join(p.get("text", "") for p in _pieces(seg, col))


def _col_lines(seg: dict, col: dict) -> list[str]:
    lines: list[str] = []
    for p in _pieces(seg, col):
        lines.extend(p.get("text", "").split("\n"))
    return [l for l in lines if l.strip()]


def _greek_chars(seg: dict) -> int:
    return sum(len(l.get("text", "")) for l in seg.get("greek") or [])


# -------------------------------------------------------------- sections --

def section_columns(columns: list[dict], reports: dict[str, dict | None]) -> tuple[str, list[str]]:
    headers = ["Column", "Slot", "Form", "Model", "Source", "Footnotes", "Pairing rate", "Shifted turns", "Unpaired Greek"]
    rows = []
    notes: list[str] = []
    for col in columns:
        cid = col["id"]
        report = reports.get(cid)
        if report is None:
            rows.append([cid, col["slot"], col["form"], col["model"], col["source"], "-", "-", "-", "-"])
            continue
        pairing_rate = report.get("pairing_rate", report.get("coverage_ratio"))
        pairing_str = f"{pairing_rate:.3f}" if isinstance(pairing_rate, (int, float)) else "-"
        shift_count = report.get("turn_shift_count")
        unpaired = report.get("greek_unpaired")
        if unpaired is None:
            total = report.get("segments_total")
            with_chunk = report.get("segments_with_chunk")
            unpaired = (total - with_chunk) if isinstance(total, int) and isinstance(with_chunk, int) else "-"
        rows.append([
            cid, col["slot"], col["form"], col["model"], col["source"],
            report.get("footnotes", 0),
            pairing_str,
            shift_count if shift_count is not None else "-",
            unpaired,
        ])
        # "shifted" counts an ordinal offset per speaker: a run of consecutive
        # turn_shifts entries sharing the same speaker and the same ordinal
        # delta is ONE drift marking every later speech of that speaker, so
        # report where each run starts and how long it runs.
        shifts = report.get("turn_shifts")
        if shifts:
            runs: list[tuple[str, int]] = []
            run_start, run_len, run_key = None, 0, None
            for shift in shifts:
                key = (shift.get("greek_speaker"), shift.get("english_ordinal", 0) - shift.get("greek_ordinal", 0))
                if key == run_key:
                    run_len += 1
                else:
                    if run_start is not None:
                        runs.append((run_start, run_len))
                    run_start, run_len, run_key = shift.get("greek_id"), 1, key
            if run_start is not None:
                runs.append((run_start, run_len))
            run_desc = "; ".join(f"{gid} (×{n})" for gid, n in runs[:10])
            more = f" (+{len(runs) - 10} more runs)" if len(runs) > 10 else ""
            notes.append(f"- **{cid}** shift runs: {run_desc}{more}")
    table, _ = _table(headers, rows)
    return table, notes


def section_bare_greek(columns: list[dict], segments: list[dict]) -> tuple[str, int]:
    headers = ["Segment", "Ref", "Column", "Greek lines", "Column lines/chars", "Reason"]
    rows = []
    for seg in segments:
        greek = seg.get("greek") or []
        if len(greek) < 8:
            continue
        for col in columns:
            if col["slot"] == "primary" and seg.get("englishCoveredBy"):
                continue
            text = _col_text(seg, col)
            if not text:
                rows.append([seg["id"], _ref_range(greek), col["id"], len(greek), 0, "no text"])
                continue
            if col["form"] == "verse":
                n_lines = len(_col_lines(seg, col))
                if n_lines < 0.30 * len(greek):
                    rows.append([seg["id"], _ref_range(greek), col["id"], len(greek), n_lines, "fewer than 30% as many lines"])
            else:
                n_chars = len(text)
                g_chars = _greek_chars(seg)
                if g_chars and n_chars < 0.25 * g_chars:
                    rows.append([seg["id"], _ref_range(greek), col["id"], len(greek), n_chars, "fewer than 25% as many characters"])
    table, total = _table(headers, rows)
    return table, total


def section_overstuffed(columns: list[dict], segments: list[dict]) -> tuple[str, int]:
    headers = ["Segment", "Ref", "Column", "Greek lines", "Column lines/chars", "Reason"]
    rows = []
    for seg in segments:
        greek = seg.get("greek") or []
        if not greek or len(greek) > 3:
            continue
        g_chars = _greek_chars(seg)
        for col in columns:
            text = _col_text(seg, col)
            if not text:
                continue
            n_chars = len(text)
            if col["form"] == "verse":
                n_lines = len(_col_lines(seg, col))
                if n_lines >= 12:
                    rows.append([seg["id"], _ref_range(greek), col["id"], len(greek), n_lines, "12+ lines"])
                    continue
            if g_chars and n_chars >= 4 * g_chars:
                rows.append([seg["id"], _ref_range(greek), col["id"], len(greek), n_chars, "4x the Greek's characters"])
    table, total = _table(headers, rows)
    return table, total


def section_speakers(columns: list[dict], reports: dict[str, dict | None]) -> tuple[str, int]:
    headers = ["Column", "Cues with no roster match", "Roster names with no English speech", "speakerMismatch"]
    rows = []
    total = 0
    for col in columns:
        report = reports.get(col["id"])
        if report is None:
            continue
        speakers = report.get("speakers") or {}
        only_english = speakers.get("only_in_english") or []
        only_greek = speakers.get("only_in_greek") or []
        mismatch = report.get("speech_mismatch_count", report.get("residual_flagged", 0))
        rows.append([col["id"], ", ".join(only_english) or "-", ", ".join(only_greek) or "-", mismatch])
        total += len(only_english) + len(only_greek) + (mismatch or 0)
    table, _ = _table(headers, rows)
    return table, total


def _read_source_lines(col: dict) -> list[str] | None:
    if col["model"] != "turn-text" or not col.get("source"):
        return None
    path = SOURCES_DIR / col["source"]
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8", errors="replace").split("\n")
    except OSError:
        return None


def section_cues_in_speech(columns: list[dict], roster: list[str]) -> tuple[str, int]:
    headers = ["Column", "Line", "Text"]
    rows = []
    roster_folds = {_fold(name) for name in roster if _fold(name)}
    for col in columns:
        lines = _read_source_lines(col)
        if not lines:
            continue
        for i, raw in enumerate(lines, start=1):
            s = raw.strip()
            if not s.endswith(".") or len(s) > 60:
                continue
            body = s[:-1].strip()
            folded = _fold(body)
            if not folded:
                continue
            is_short_fold = len(body) <= 40 and folded in roster_folds
            is_caps_cue = bool(re.match(r"^[A-Z][A-Z .]{1,30}\.$", s)) and any(
                folded in rf or rf in folded for rf in roster_folds
            )
            if not (is_short_fold or is_caps_cue):
                continue
            # A line the model's own parser (`_parse_as_speeches`) already
            # recognises as a standalone speaker cue is a genuine cue, not
            # one embedded inside a speech -- excluded here (review finding
            # 8: nine genuine cues in Alcestis were reported as defects).
            speaker_match = _SPEAKER_LINE.match(s)
            if speaker_match and not (speaker_match.group("rest") or "").strip():
                continue
            rows.append([col["id"], i, s[:80]])
    table, total = _table(headers, rows)
    return table, total


def section_directions(columns: list[dict]) -> tuple[str, int]:
    headers = ["Column", "Directions (_..._)", "Bare stage directions"]
    rows = []
    total = 0
    for col in columns:
        lines = _read_source_lines(col)
        if not lines:
            continue
        text = "\n".join(lines)
        n_directions = len(_DIRECTION_RE.findall(text))
        bare = [
            (i, raw.strip()[:80])
            for i, raw in enumerate(lines, start=1)
            if _STAGE_WORD_RE.match(raw.strip()) and not raw.strip().startswith("_")
        ]
        rows.append([col["id"], n_directions, "; ".join(f"L{i}: {t}" for i, t in bare[:5]) or "-"])
        total += len(bare)
    table, _ = _table(headers, rows)
    return table, total


def section_scan_noise(columns: list[dict]) -> tuple[str, int]:
    headers = ["Column", "Line", "Text", "Reason"]
    rows = []
    for col in columns:
        lines = _read_source_lines(col)
        if not lines:
            continue
        for i, raw in enumerate(lines, start=1):
            s = raw.strip()
            if not s:
                continue
            reason = None
            if ("[" in s and "]" not in s) or "{" in s or s.startswith(". "):
                reason = "bracket-tail turnover"
            elif "®" in s or "†" in s:
                reason = "stray symbol"
            elif _GLUED_DIGIT_RE.search(_strip_markers(s)):
                reason = "digit glued to a word"
            elif any(
                _CAPS_RUN_RE.search(tok) and tok != tok.upper()
                for tok in re.findall(r"[A-Za-z']+", s)
            ):
                reason = "3+ consecutive capitals inside a word"
            elif any(
                ch for ch in s
                if ord(ch) > 127 and ch not in _ALLOWED_NON_ASCII and not _is_accented_latin(ch)
            ):
                reason = "non-Latin glyph"
            if reason:
                rows.append([col["id"], i, s[:80], reason])
    table, total = _table(headers, rows)
    return table, total


def section_footnotes(columns: list[dict], segments: list[dict], footnotes: dict) -> tuple[str, int]:
    headers = ["Item", "Status"]
    rows = []
    markers: set[str] = set()
    for seg in segments:
        for col in columns:
            for piece in _pieces(seg, col):
                markers.update(_MARKER_RE.findall(piece.get("text", "")))
    notes = set(footnotes.keys())
    for m in sorted(markers - notes):
        rows.append([f"marker [^{m}]", "no matching note"])
    for n in sorted(notes - markers):
        rows.append([f"note {n}", "no matching marker"])
    stray_headers = ["Column", "Line", "Text"]
    stray_rows = []
    for seg in segments:
        for col in columns:
            if col["form"] != "verse":
                continue
            for line in _col_lines(seg, col):
                if _STRAY_NOTE_LINE_RE.match(line.strip()):
                    stray_rows.append([col["id"], seg["id"], line.strip()[:80]])
    table, total = _table(headers, rows)
    stray_table, stray_total = _table(stray_headers, stray_rows)
    combined = table + "\n\nNote lines still inside verse:\n\n" + stray_table
    return combined, total + stray_total


def section_verse_shape(columns: list[dict], segments: list[dict]) -> tuple[str, int]:
    long_headers = ["Column", "Segment", "Length"]
    long_rows = []
    dev_headers = ["Segment", "Ref", "Column", "Greek lines", "Column lines", "Diff"]
    dev_rows = []
    for seg in segments:
        greek = seg.get("greek") or []
        for col in columns:
            if col["form"] != "verse":
                continue
            lines = _col_lines(seg, col)
            for line in lines:
                if len(line) > 90:
                    long_rows.append([col["id"], seg["id"], len(line)])
            if greek and lines:
                diff = abs(len(lines) - len(greek)) / len(greek)
                if diff > 0.40:
                    dev_rows.append([seg["id"], _ref_range(greek), col["id"], len(greek), len(lines), f"{diff:.0%}"])
    long_table, long_total = _table(long_headers, long_rows)
    dev_table, dev_total = _table(dev_headers, dev_rows)
    combined = long_table + "\n\nSpeeches whose line count differs from the Greek's by more than 40%:\n\n" + dev_table
    return combined, long_total + dev_total


def section_line_count(columns: list[dict], segments: list[dict]) -> str:
    headers = ["Column", "Form", "Greek total", "Column total", "Ratio"]
    greek_lines = sum(len(seg.get("greek") or []) for seg in segments)
    greek_chars = sum(_greek_chars(seg) for seg in segments)
    rows = [["Greek", "-", greek_lines, "-", "-"]]
    for col in columns:
        if col["form"] == "verse":
            total = sum(len(_col_lines(seg, col)) for seg in segments)
            ratio = f"{total / greek_lines:.2f}" if greek_lines else "-"
            rows.append([col["id"], col["form"], greek_lines, total, ratio])
        else:
            total = sum(len(_col_text(seg, col)) for seg in segments)
            ratio = f"{total / greek_chars:.2f}" if greek_chars else "-"
            rows.append([col["id"], col["form"], greek_chars, total, ratio])
    table, _ = _table(headers, rows)
    return table


# ---------------------------------------------------------------- driver --

def build_sheet(work_id: str, dist_dir: Path, stage1_dir: Path, manifest: Manifest) -> tuple[str, dict[str, int]]:
    columns = columns_for(manifest)
    segments, roster = load_book(dist_dir)
    footnotes = load_footnotes(dist_dir)
    reports = {col["id"]: load_report(stage1_dir, col, work_id) for col in columns}

    columns_table, shift_notes = section_columns(columns, reports)
    bare_table, bare_total = section_bare_greek(columns, segments)
    over_table, over_total = section_overstuffed(columns, segments)
    speakers_table, speakers_total = section_speakers(columns, reports)
    cues_table, cues_total = section_cues_in_speech(columns, roster)
    dirs_table, dirs_total = section_directions(columns)
    scan_table, scan_total = section_scan_noise(columns)
    foot_table, foot_total = section_footnotes(columns, segments, footnotes)
    verse_table, verse_total = section_verse_shape(columns, segments)
    line_table = section_line_count(columns, segments)

    parts = [
        f"# Audit: {work_id}\n",
        "## 1. Columns\n", columns_table,
        ("\n\n" + "\n".join(shift_notes)) if shift_notes else "",
        "\n\n## 2. Bare Greek\n", bare_table,
        "\n\n## 3. Overstuffed\n", over_table,
        "\n\n## 4. Speakers\n", speakers_table,
        "\n\n## 5. Cues inside speech\n", cues_table,
        "\n\n## 6. Directions\n", dirs_table,
        "\n\n## 7. Scan noise\n", scan_table,
        "\n\n## 8. Footnotes\n", foot_table,
        "\n\n## 9. Verse shape\n", verse_table,
        "\n\n## 10. Line count\n",
        "Coarse total, not a coverage check: a ratio near 1.00 can still hide "
        "a page-sized gap offset by excess elsewhere (review finding 9).\n\n",
        line_table,
        "\n",
    ]
    totals = {
        "bare_greek": bare_total,
        "overstuffed": over_total,
        "speakers": speakers_total,
        "cues": cues_total,
        "directions": dirs_total,
        "scan_noise": scan_total,
        "footnotes": foot_total,
        "verse_shape": verse_total,
    }
    return "".join(parts), totals


def _all_work_ids() -> list[str]:
    ids = []
    for path in sorted(MANIFESTS_DIR.glob("*.yaml")):
        if path.name == "authors.yaml" or path.name.endswith("-public.yaml"):
            continue
        ids.append(path.stem)
    return ids


def run_one(work_id: str) -> dict[str, int]:
    manifest = Manifest.for_work(work_id)
    dist_dir = BUILD_DIR / "dist" / work_id
    stage1_dir = BUILD_DIR / "stage1"
    sheet, totals = build_sheet(work_id, dist_dir, stage1_dir, manifest)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    (AUDIT_DIR / f"{work_id}.md").write_text(sheet, encoding="utf-8")
    return totals


def run_all() -> None:
    from . import __main__ as cli

    headers = ["Play", "Bare Greek", "Overstuffed", "Speakers", "Cues", "Directions", "Scan noise", "Footnotes", "Verse shape"]
    index_rows = []
    for work_id in _all_work_ids():
        cli.main(["all", "--work", work_id])
        totals = run_one(work_id)
        index_rows.append([
            work_id, totals["bare_greek"], totals["overstuffed"], totals["speakers"],
            totals["cues"], totals["directions"], totals["scan_noise"], totals["footnotes"],
            totals["verse_shape"],
        ])
    table, _ = _table(headers, index_rows, cap=None)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    (AUDIT_DIR / "INDEX.md").write_text("# Audit index\n\n" + table + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="drama_pipeline.audit")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--work", help="work slug = manifest filename stem")
    group.add_argument("--all", action="store_true", help="rebuild and audit every manifest")
    args = parser.parse_args(argv)
    start = time.monotonic()
    if args.all:
        run_all()
        print(f"audit --all: {time.monotonic() - start:.1f}s")
    else:
        totals = run_one(args.work)
        print(f"audit {args.work}: " + " ".join(f"{k}={v}" for k, v in totals.items()))


if __name__ == "__main__":
    sys.exit(main())
