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
from .stage1_turn_english import (
    _SPEAKER_LINE,
    _is_gutenberg_end_line,
    _is_play_end,
    _dramatis_index_after,
    _locate_title,
)

AUDIT_DIR = BUILD_DIR / "audit"
MANIFESTS_DIR = REPO_ROOT / "manifests"
MAX_ROWS = 40

_FOLD_RE = re.compile(r"[^A-Za-z]")
_MARKER_RE = re.compile(r"\[\^([^\]\s]+)\]")
_DIRECTION_RE = re.compile(r"_[^_\n]+_")
_STAGE_WORD_RE = re.compile(r"^(Enter|Exit|Exeunt|Re-enter|Scene)\b")
# D7 (suppliants-eur review, 2026-09-17): a genuine leftover footnote
# note-line opens a real sentence, capitalised; Way's own verse regularly
# opens a line with the pronoun "I" mis-scanned as the digit "1", always
# followed by a lowercase word ("1 faint", "1 will", "1 had") -- requiring
# an upper-case letter after the digit tells the two apart.
_STRAY_NOTE_LINE_RE = re.compile(r"^[1-9]\d*\s[A-Z]")
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
            "play": cfg.get("play"),
            "form": forms.get(cfg.get("id")) or "prose",
        })
    for entry in english.get("overlays") or []:
        cols.append({
            "slot": "overlay",
            "id": entry.get("id"),
            "model": entry.get("model"),
            "source": entry.get("source"),
            "play": entry.get("play"),
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

def _shift_onsets(shifts: list[dict]) -> list[tuple[str, int]]:
    """Group `turn_shifts` entries by the speaker whose same-name ordinal
    diverges from the Greek, counting a shift only where THAT SPEAKER's
    own delta changes from its own last value -- not every time the raw
    pair sequence happens to repeat a (speaker, delta) key back to back.

    A lost turn permanently offsets a speaker's same-name ordinal count,
    so every later turn of that speaker keeps appearing in `turn_shifts`
    even once the pairing itself has resynced content-wise (prometheus-
    bound review, 2026-09-17: "the offset never returns to zero, so every
    later Prometheus and Chorus turn is counted as shifted even though
    the text realigns"). The old grouping walked the raw pair sequence
    and broke the run the instant a DIFFERENT speaker's shift entry came
    between two of this speaker's -- so an alternating stichomythia
    reported one row per turn (59 "runs" for 103 shifted turns) instead
    of the one incident per speaker it actually is. Tracking each
    speaker's own last delta, independent of interleaving, collapses
    that back to one run per speaker per onset.

    A name mismatch (the English speaker recorded on the pair differs
    from the Greek one) is a different defect, already surfaced by
    `section_speakers`'s speakerMismatch count -- excluded here so it is
    not double-counted as an ordinal drift.

    Returns `(first_greek_id, run_length)` pairs in first-seen order.
    """
    runs: list[list] = []  # [greek_id, length], mutated in place
    last_delta: dict[str, int] = {}
    last_run_idx: dict[str, int] = {}
    for shift in shifts:
        name = shift.get("greek_speaker")
        english_speaker = shift.get("english_speaker", name)
        if name is None or english_speaker != name:
            continue
        delta = shift.get("english_ordinal", 0) - shift.get("greek_ordinal", 0)
        if last_delta.get(name) == delta and name in last_run_idx:
            runs[last_run_idx[name]][1] += 1
        else:
            last_run_idx[name] = len(runs)
            runs.append([shift.get("greek_id"), 1])
        last_delta[name] = delta
    return [(gid, n) for gid, n in runs]


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
        shifts = report.get("turn_shifts")
        if shifts is not None:
            # Onset count (D3): how many times a speaker's ordinal offset
            # actually changed, not how many later turns kept carrying it.
            runs = _shift_onsets(shifts)
            shift_count = len(runs)
        else:
            runs = []
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
        # "Shifted turns" counts an onset per speaker (D3): one drift is one
        # speaker's ordinal offset changing value, not every later speech of
        # that speaker still carrying it -- report where each onset starts
        # and how long the offset it opened persists.
        if runs:
            run_desc = "; ".join(f"{gid} (×{n})" for gid, n in runs[:10])
            more = f" (+{len(runs) - 10} more runs)" if len(runs) > 10 else ""
            notes.append(f"- **{cid}** shift runs: {run_desc}{more}")
    table, _ = _table(headers, rows)
    return table, notes


_BARE_TEXT_MIN_GREEK = 1  # a wholly empty column is bare at any Greek content
_BARE_RATIO_MIN_GREEK = 8  # the 30%/25% ratio checks need the longer segment


def section_bare_greek(columns: list[dict], segments: list[dict]) -> tuple[str, int]:
    headers = ["Segment", "Ref", "Column", "Greek lines", "Column lines/chars", "Reason"]
    rows = []
    for seg in segments:
        greek = seg.get("greek") or []
        if len(greek) < _BARE_TEXT_MIN_GREEK:
            continue
        for col in columns:
            if col["slot"] == "primary" and seg.get("englishCoveredBy"):
                continue
            text = _col_text(seg, col)
            if not text:
                # A wholly empty column is bare regardless of segment length
                # (Ajax review finding B, 2026-09-16: three one-line Storr
                # cells with no `ross` text were missed by the 8-line floor).
                rows.append([seg["id"], _ref_range(greek), col["id"], len(greek), 0, "no text"])
                continue
            if len(greek) < _BARE_RATIO_MIN_GREEK:
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


def _built_speaker_mismatch(segments: list[dict], col: dict) -> tuple[int, int]:
    """(flagged turns, segments carrying at least one) for `col`, counted
    from the built `turn.speakerMismatch` objects themselves rather than a
    stage1-side estimate (wasps review finding 7, 2026-09-17: the report's
    `speech_mismatch_count` read 6 where the build actually carries 59
    flagged turns across 53 segments -- the report field is a bench-side
    guess and the build is the fact)."""
    turns = 0
    segs_with = 0
    for seg in segments:
        seg_flagged = False
        for piece in _pieces(seg, col):
            for turn in piece.get("turns") or []:
                if turn.get("speakerMismatch"):
                    turns += 1
                    seg_flagged = True
        if seg_flagged:
            segs_with += 1
    return turns, segs_with


def section_speakers(columns: list[dict], segments: list[dict], reports: dict[str, dict | None]) -> tuple[str, int]:
    headers = ["Column", "Cues with no roster match", "Roster names with no English speech", "speakerMismatch (segments)"]
    rows = []
    total = 0
    for col in columns:
        report = reports.get(col["id"])
        if report is None:
            continue
        speakers = report.get("speakers") or {}
        only_english = speakers.get("only_in_english") or []
        only_greek = speakers.get("only_in_greek") or []
        mismatch, mismatch_segs = _built_speaker_mismatch(segments, col)
        mismatch_str = f"{mismatch} ({mismatch_segs} segs)" if mismatch else 0
        rows.append([col["id"], ", ".join(only_english) or "-", ", ".join(only_greek) or "-", mismatch_str])
        total += len(only_english) + len(only_greek) + mismatch
    table, _ = _table(headers, rows)
    return table, total


def _play_span(lines: list[str], play: str) -> tuple[int, int] | None:
    """The `[start, end)` line range `parse_play_speeches` would read for
    `play` -- so a raw-source scan does not wander into a different play
    sharing the same Gutenberg volume (`gutenberg/pg8688.txt` and
    `pg8689.txt` hold the eleven comedies between them; clouds review
    finding, 2026-09-17: untrimmed §7
    scan-noise rows for the athenian-society primary were another play's
    text, footnote bodies three plays over, or the trailing PG licence)."""
    try:
        start = _locate_title(lines, play)
    except ValueError:
        return None
    # Only a dramatis-anchored title marks a play inside a shared volume.
    # On a verse-own-line bench the title is also a speaker cue (Johnston's
    # `AJAX` 44 times), and `_locate_title` would take the last hit and
    # keep only the tail of the file (Grok read, 2026-09-17).
    if _dramatis_index_after(lines, start) is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if _is_play_end(lines[j].strip()) or _is_gutenberg_end_line(lines[j]):
            end = j
            break
    return start, end


def _read_source_lines(col: dict) -> list[str] | None:
    if col["model"] != "turn-text" or not col.get("source"):
        return None
    path = SOURCES_DIR / col["source"]
    if not path.exists():
        return None
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
    except OSError:
        return None
    play = col.get("play")
    span = _play_span(lines, play) if play else None
    if span is None:
        return lines
    start, end = span
    # Blank out everything outside this play's own span rather than
    # slicing, so the line numbers every section reports stay the file's
    # own (a reviewer greps the bench file at that number) -- only a
    # single-play bench file's `start` is ever non-trivial to begin with;
    # every per-play file already opens on (or right next to) its title.
    return [""] * start + lines[start:end] + [""] * (len(lines) - end)


# A capitalized cue name immediately followed by an unclosed bracket tail
# (a metrical or stage label glued onto the name: Murray's "LEADER.
# [Strophe."), rather than the speech itself -- the real line of dialogue
# is the NEXT source line, so neither the whole-line roster-fold check
# below nor the all-caps-cue check recognises this as a cue at all
# (oedipus-tyrannus review finding 6, 2026-09-17; the same line is already
# reported as scan noise, "bracket-tail turnover", by section 7, but not as
# a cue).
_BRACKET_TAIL_CUE_RE = re.compile(r"^([A-ZÀ-Þ][A-Za-zÀ-Þ'’]{1,24})\.\s*\[[^\]]*$")

# A roster name embedded mid-line, immediately after a sentence's own end
# punctuation and immediately before a capitalized word -- a second speech
# run on from the first with no cue period of its own (oedipus-tyrannus
# review finding 5, 2026-09-17: Kosmos's own paragraph break was lost, so
# "...Will you never come to an end [telos]? Teiresias You find fault..."
# buries Teiresias's reply inside Oedipus's speech). Anchoring on `.?!`
# rather than on any non-space character keeps this from matching a name
# used in ordinary English mid-sentence -- a vocative ("O Teiresias, hear
# me") has a comma, not a full stop, before it, and a stage direction's own
# possessive ("Enter Orestes' Nurse") has an apostrophe, not one either
# (libation-bearers spot-check, 2026-09-17).
_MIDLINE_NAME_RE = re.compile(r"(?<=[.?!])\s([A-ZÀ-Þ][a-zà-ÿ'’]+)(?=\s[A-ZÀ-Þ])")


def _roster_allcaps_pattern(roster: list[str]) -> re.Pattern | None:
    names = sorted({name.strip() for name in roster if name and name.strip()}, key=len, reverse=True)
    if not names:
        return None
    alts = "|".join(re.escape(name.upper()) for name in names)
    return re.compile(rf"(?<![A-Za-z])(?:{alts})(?![A-Za-z])[.:]")


def _built_cue_hits(segments: list[dict], columns: list[dict], roster: list[str]) -> list[list]:
    """A roster name printed in ALL CAPS as its own cue token, buried
    inside a column's built text rather than sitting at that text's own
    head, is a cue the pairer never turned into a `turns` entry -- it
    prints as plain verse or prose instead of opening a new speech (ion
    review finding 11, 2026-09-17: an antilabe half-line's second speaker
    prints as a bare cue token mid-block, 58 lines across ~40 segments;
    libation-bearers finding 11 and IT findings 7/9/15 are the same
    shape). `section_cues_in_speech`'s scan above reads the raw BENCH
    source, which cannot see a cue the build itself failed to lift out --
    this reads the built column text instead, per column per segment."""
    pattern = _roster_allcaps_pattern(roster)
    if pattern is None:
        return []
    rows: list[list] = []
    for seg in segments:
        for col in columns:
            text = _col_text(seg, col)
            if not text:
                continue
            for m in pattern.finditer(text):
                if m.start() == 0:
                    continue  # the column's own opening cue, not a buried one
                snippet = text[max(0, m.start() - 20):m.end() + 40].replace("\n", " / ")
                rows.append([col["id"], seg["id"], snippet.strip()[:80], "roster cue buried in the built text"])
    return rows


def section_cues_in_speech(
    columns: list[dict], roster: list[str], segments: list[dict] | None = None
) -> tuple[str, int]:
    headers = ["Column", "Line", "Text", "Reason"]
    rows: list[list] = []
    rows.extend(_built_cue_hits(segments or [], columns, roster))
    roster_folds = {_fold(name) for name in roster if _fold(name)}
    for col in columns:
        lines = _read_source_lines(col)
        if not lines:
            continue
        last_cue: tuple[str, int, str] | None = None  # (name, line, text)
        for i, raw in enumerate(lines, start=1):
            s = raw.strip()
            if not s:
                continue
            speaker_match = _SPEAKER_LINE.match(s)
            cue_name = speaker_match.group("name").strip() if speaker_match else None

            # A cue that repeats the immediately preceding cue's own name,
            # with no other speaker's cue in between, prints one speaker's
            # two speeches as if the second answered the first (Storr's
            # "CREON." greets himself: the Loeb gives the first speech to
            # Oedipus -- finding 2).
            if cue_name and last_cue and cue_name == last_cue[0]:
                rows.append([col["id"], last_cue[1], last_cue[2], f"cue repeated at line {i}"])
                rows.append([col["id"], i, s[:80], f"repeats the cue at line {last_cue[1]}"])
                last_cue = (cue_name, i, s[:80])
                continue
            if cue_name:
                last_cue = (cue_name, i, s[:80])

            if len(s) <= 70:
                tail = _BRACKET_TAIL_CUE_RE.match(s)
                if tail:
                    rows.append([col["id"], i, s[:80], "cue name carries an unclosed bracket tail"])
                    continue

            if s.endswith(".") and len(s) <= 60:
                body = s[:-1].strip()
                folded = _fold(body)
                if folded:
                    is_short_fold = len(body) <= 40 and folded in roster_folds
                    is_caps_cue = bool(re.match(r"^[A-Z][A-Z .]{1,30}\.$", s)) and any(
                        folded in rf or rf in folded for rf in roster_folds
                    )
                    # A bare cue the model's own parser (`_parse_as_speeches`)
                    # already recognises as a standalone speaker cue -- name
                    # alone, its speech continuing on later lines -- is a
                    # genuine cue, not one embedded inside a speech --
                    # excluded here (review finding 8: nine genuine cues in
                    # Alcestis were reported as defects).
                    is_bare_standalone_cue = bool(speaker_match) and not (
                        speaker_match.group("rest") or ""
                    ).strip()
                    if (is_short_fold or is_caps_cue) and not is_bare_standalone_cue:
                        rows.append([col["id"], i, s[:80], "roster name alone on the line"])
                        continue

            for m in _MIDLINE_NAME_RE.finditer(s):
                if _fold(m.group(1)) in roster_folds:
                    rows.append([col["id"], i, s[:80], "roster name mid-line before a capital"])
                    break
    table, total = _table(headers, rows)
    return table, total


def _built_direction_count(segments: list[dict], col: dict) -> int:
    """Directions the loeb-ocr turn-english path lifted onto the built
    pieces (`directionsBefore`, commit 7db48a2) -- these never appear as
    `_..._` markup in the raw bench source, so the source-text scan below
    counts none of them (Ajax review finding B, 2026-09-16)."""
    count = 0
    for seg in segments:
        for piece in _pieces(seg, col):
            count += len(piece.get("directionsBefore") or [])
            for turn in piece.get("turns") or []:
                count += len(turn.get("directionsBefore") or [])
    return count


def section_directions(columns: list[dict], segments: list[dict]) -> tuple[str, int]:
    headers = ["Column", "Directions (source _..._)", "Directions (built)", "Bare stage directions"]
    rows = []
    total = 0
    for col in columns:
        lines = _read_source_lines(col)
        n_built = _built_direction_count(segments, col)
        if not lines and not n_built:
            continue
        n_source = len(_DIRECTION_RE.findall("\n".join(lines))) if lines else 0
        bare = [
            (i, raw.strip()[:80])
            for i, raw in enumerate(lines, start=1)
            if _STAGE_WORD_RE.match(raw.strip()) and not raw.strip().startswith("_")
        ] if lines else []
        rows.append([col["id"], n_source, n_built, "; ".join(f"L{i}: {t}" for i, t in bare[:5]) or "-"])
        total += len(bare)
    table, _ = _table(headers, rows)
    return table, total


# D6 (2026-09-17): a handful of OCR-fragment shapes the reviews found
# surviving into the built column text, none of which the checks above
# catch -- a rubric label left standing alone (phoenician-women's
# "(Str)"/"(Ant.)"), a torn cue with a leading quote and a space before an
# all-caps remnant ("' AAD"), a bare quoted word-fragment with nothing
# else on the line ('"Yee'), and a short line ending in an unmatched
# closing bracket with no opener anywhere on it ("et)").
_RUBRIC_RE = re.compile(r"^\(?(?:strophe|antistrophe|str|ant)\.?\s*\d*\.?\)?$", re.IGNORECASE)
_QUOTE_CAPS_FRAGMENT_RE = re.compile(r"^['\"’]\s+[A-Z]{2,8}$")
_QUOTE_LEAD_WORD_RE = re.compile(r"^['\"’][A-Z][a-z]{1,6}$")
_TRAILING_BRACKET_NO_OPEN_RE = re.compile(r"[)\]]$")
_STRAY_SYMBOL_CHARS = "®†«»~|*"


def _scan_noise_reason(s: str) -> str | None:
    """One reason string for a line of scan noise, or None -- shared by
    the raw-source scan and the built-column scan below (D6) so both read
    the same rules."""
    if not s:
        return None
    if (
        ("[" in s and "]" not in s) or "{" in s or s.startswith(". ")
        or _QUOTE_CAPS_FRAGMENT_RE.match(s)
    ):
        return "bracket-tail turnover"
    if (
        len(s) <= 10 and _TRAILING_BRACKET_NO_OPEN_RE.search(s)
        and "(" not in s and "[" not in s
    ):
        return "bracket-tail turnover"
    if _RUBRIC_RE.match(s):
        return "strophe/antistrophe rubric"
    if any(ch in s for ch in _STRAY_SYMBOL_CHARS):
        return "stray symbol"
    if _GLUED_DIGIT_RE.search(_strip_markers(s)):
        return "digit glued to a word"
    if any(
        _CAPS_RUN_RE.search(tok) and tok != tok.upper()
        for tok in re.findall(r"[A-Za-z']+", s)
    ):
        return "3+ consecutive capitals inside a word"
    if any(
        ch for ch in s
        if ord(ch) > 127 and ch not in _ALLOWED_NON_ASCII and not _is_accented_latin(ch)
    ):
        return "non-Latin glyph"
    if _QUOTE_LEAD_WORD_RE.match(s):
        return "OCR quote fragment"
    return None


def _built_scan_noise_hits(segments: list[dict], columns: list[dict]) -> list[list]:
    """Scan-noise fragments visible only in the BUILT column text, not the
    raw bench (D6: phoenician-women review, 2026-09-17, "35 survive into
    the built Way column" against 27 the old bench-only scan listed;
    rhesus's closing scanner garbage is the same shape). A line the
    converter reformatted, merged, or (for a multi-play Gutenberg volume)
    trimmed out of the bench span can still carry noise once it lands in
    the built json -- this reads what the reader actually shows."""
    rows: list[list] = []
    for seg in segments:
        for col in columns:
            for line in _col_lines(seg, col):
                s = line.strip()
                reason = _scan_noise_reason(s)
                if reason:
                    rows.append([col["id"], seg["id"], s[:80], reason])
    return rows


def section_scan_noise(columns: list[dict], segments: list[dict] | None = None) -> tuple[str, int]:
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
            reason = _scan_noise_reason(s)
            if reason:
                rows.append([col["id"], i, s[:80], reason])
    rows.extend(_built_scan_noise_hits(segments or [], columns))
    table, total = _table(headers, rows)
    return table, total


def _empty_columns(segments: list[dict], columns: list[dict]) -> list[str]:
    """Column ids with zero built pieces across the whole play -- a
    manifest slot marked `private: true` that some build excludes
    entirely is the known case (wealth/lysistrata/thesmophoriazusae
    reviews, 2026-09-17: Rogers absent from every segment while his own
    footnotes.json entries survive, reading as 92-155 "no matching
    marker" rows with nothing to tell a reviewer why), but any column
    that ends up contributing no text qualifies."""
    return [col["id"] for col in columns if not any(_pieces(seg, col) for seg in segments)]


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
    empty_cols = _empty_columns(segments, columns)
    header = (
        f"_Column(s) with no built text in this play (a private "
        f"comparison slot most likely; excluded from the reader): "
        f"{', '.join(empty_cols)}. An orphan note/marker below may "
        f"belong to one of them rather than describe a real mismatch._\n\n"
    ) if empty_cols else ""
    combined = header + table + "\n\nNote lines still inside verse:\n\n" + stray_table
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
    speakers_table, speakers_total = section_speakers(columns, segments, reports)
    cues_table, cues_total = section_cues_in_speech(columns, roster, segments)
    dirs_table, dirs_total = section_directions(columns, segments)
    scan_table, scan_total = section_scan_noise(columns, segments)
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
