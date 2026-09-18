"""Stage 2: validation of the Stage 1 spine, chunks, and alignment.

Checks:
  1. Column completeness and monotonic order across 1094a-1181b.
  2. Line-number gaps inside columns (book-boundary gaps are expected and
     verified against the manifest; anything else is flagged).
  3. Alignment coverage in both directions.
  4. Greek/English length-ratio outliers (> 1.5 SD from the mean ratio).
  5. Proper-name spot check: names that should co-occur in the same column
     in both languages.
  6. Sigla/character inventory of the Greek text: every non-Greek,
     non-expected character with counts and sample locations.

Emits build/stage2/validation_report.json and .md (human-readable).
"""

from __future__ import annotations

import json
import hashlib
import math
import re
import statistics
import unicodedata
from collections import defaultdict
from pathlib import Path

from . import scheme as scheme_mod
from .config import BUILD_DIR, Manifest, SOURCES_DIR, private_translation_ids
from .refs import column_key, column_range, ref_key
from .stage3_tokenize import _SPINE_FILENAMES

def _base(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()

# Characters we expect in Bywater's text besides Greek letters.
EXPECTED_NON_GREEK = set(" .,·;'’ʼ—-()[]")


def _is_greek_letter(ch: str) -> bool:
    if not ch.isalpha():
        return False
    try:
        return "GREEK" in unicodedata.name(ch)
    except ValueError:
        return False


def _omit_declared_segment_ids(manifest: Manifest, segments: list[dict]) -> set[str]:
    """Segment ids whose column carries a `kind: "omit"` disposition in the
    manifest's own `citation.kind_overrides` (John's ruling 2026-07-23:
    "where she has no greek, we leave out" -- design note
    docs/freeman-wave-design.md §1(b)). `stage1_freeman_english.build_english`
    skips these columns entirely (no English chunk emitted), so
    `build_alignment` correctly reports them unmatched -- this derives the
    alignment allowance from that SAME declaration rather than a parallel,
    hand-maintained list, so a manifest that adds/removes an omit ruling
    never needs a second edit here to keep stage2 in sync."""
    overrides = (manifest.data.get("citation") or {}).get("kind_overrides")
    if not isinstance(overrides, dict):
        return set()
    omit_columns = {
        col for col, decl in overrides.items()
        if isinstance(decl, dict) and decl.get("kind") == "omit"
    }
    if not omit_columns:
        return set()
    return {seg["id"] for seg in segments if seg["column"] in omit_columns}


def _summary_suppressed_segment_ids(manifest: Manifest, segments: list[dict]) -> set[str]:
    """Segment ids named in the manifest's own `english.summary_suppressed`
    (John's ruling 2026-07-29: a Freeman précis already covered by a
    translated context-english source-passage span ships no Freeman English
    chunk at all -- see stage1_freeman_english.py gate 5).
    `stage1_freeman_english.build_english` skips these columns entirely, so
    `build_alignment` correctly reports them unmatched -- this derives the
    alignment allowance from that SAME declaration, same posture as
    `_omit_declared_segment_ids` above, rather than a second hand-maintained
    list."""
    suppressed = (manifest.data.get("english") or {}).get("summary_suppressed")
    if not isinstance(suppressed, list) or not suppressed:
        return set()
    columns = set(suppressed)
    return {seg["id"] for seg in segments if seg["column"] in columns}


def _play_line_lacuna_segment_ids(segments: list[dict]) -> set[str]:
    """Segments made only of empty lacuna placeholder lines (Diggle's
    empty-bracket ``post N`` lines): no translation can cover them, so they
    never need a declared gap (sweep 2026-09-07: Cyclops post 146,
    Heraclidae post 110, Helen's two at post 1226, and a dozen more).
    A line that carries ``role: lacuna`` but also has text is not a hole.
    """
    out: set[str] = set()
    for seg in segments:
        lines = seg.get("lines") or []
        if lines and all(
            line.get("role") == "lacuna" and not str(line.get("text") or "").strip()
            for line in lines
        ):
            out.add(seg["id"])
    return out


def _play_line_twin_segment_ids(segments: list[dict]) -> set[str]:
    """Repeated-ref second copies (``1:803.2``) and lettered twins
    (Bacchae 843a/843b, Medea 1270a) that share an integer line number with
    another segment. A Perseus ``<l n>`` can attach to only one owner per
    integer, so these never need a declared gap."""
    from .stage1_perseus_play_english import _ref_line_numbers

    ids = {seg["id"] for seg in segments}

    def is_copy(seg_id: str) -> bool:
        if "." not in seg_id:
            return False
        base, suffix = seg_id.rsplit(".", 1)
        return suffix.isdigit() and int(suffix) >= 2 and base in ids

    def is_lettered(ref: str) -> bool:
        return len(ref) > 1 and ref[:-1].isdigit() and ref[-1:].isalpha()

    covering: dict[int, list[tuple[dict, str, int]]] = {}
    for order, seg in enumerate(segments):
        seen_n: set[int] = set()
        for line in seg.get("lines") or []:
            ref = line.get("ref")
            if not isinstance(ref, str):
                continue
            for n in _ref_line_numbers(ref):
                if n in seen_n:
                    continue
                seen_n.add(n)
                covering.setdefault(n, []).append((seg, ref, order))

    twins: set[str] = set()
    for seg in segments:
        if is_copy(seg["id"]):
            twins.add(seg["id"])
    for n, hits in covering.items():
        unique = {seg["id"] for seg, _ref, _order in hits}
        if len(unique) < 2:
            continue
        preferred, _ref, _order = min(
            hits, key=lambda item: (item[1] != str(n), item[2])
        )
        for seg, ref, _order in hits:
            if seg["id"] == preferred["id"]:
                continue
            if is_copy(seg["id"]) or is_lettered(ref):
                twins.add(seg["id"])
    return twins


def _play_line_english_source(manifest: Manifest) -> Path | None:
    raw = ((manifest.data.get("english") or {}).get("primary") or {}).get("source")
    if not raw:
        return None
    path = Path(raw)
    if path.is_file():
        return path
    vendored = SOURCES_DIR / str(raw)
    return vendored if vendored.is_file() else None


def _play_line_nonempty_translation_ns(source: Path | None) -> set[str] | None:
    """Printed ``<l n>`` values in the translation TEI that carry text.

    ``None`` means the source could not be read (fail closed for lettered
    twins). An empty set means the TEI was read and had no nonempty lines.
    """
    if source is None or not source.is_file():
        return None
    try:
        from lxml import etree

        tree = etree.parse(str(source))
    except (OSError, etree.LxmlError):
        return None
    translation = tree.find('.//{*}div[@type="translation"]')
    root = translation if translation is not None else tree.getroot()
    found: set[str] = set()
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        if el.tag.rsplit("}", 1)[-1] != "l":
            continue
        n = el.get("n")
        if not n:
            continue
        if "".join(el.itertext()).strip():
            found.add(n)
    return found


def _play_line_allowed_twin_ids(manifest: Manifest, segments: list[dict]) -> set[str]:
    """Twins that may stay unmatched without a declared gap.

    Numeric ``.2`` copies always pass. A lettered twin passes only when the
    source TEI has been read and has no nonempty exact ``<l n>`` for that ref.
    """
    twins = _play_line_twin_segment_ids(segments)
    ids = {seg["id"] for seg in segments}
    by_id = {seg["id"]: seg for seg in segments}

    def is_copy(seg_id: str) -> bool:
        if "." not in seg_id:
            return False
        base, suffix = seg_id.rsplit(".", 1)
        return suffix.isdigit() and int(suffix) >= 2 and base in ids

    def is_lettered(ref: str) -> bool:
        return len(ref) > 1 and ref[:-1].isdigit() and ref[-1:].isalpha()

    translated_ns = _play_line_nonempty_translation_ns(
        _play_line_english_source(manifest)
    )
    allowed: set[str] = set()
    for sid in twins:
        if is_copy(sid):
            allowed.add(sid)
            continue
        seg = by_id.get(sid)
        if seg is None:
            continue
        lettered_refs = [
            line.get("ref")
            for line in seg.get("lines") or []
            if isinstance(line.get("ref"), str) and is_lettered(line["ref"])
        ]
        if not lettered_refs:
            allowed.add(sid)
            continue
        if translated_ns is None:
            continue
        if any(ref in translated_ns for ref in lettered_refs):
            continue
        allowed.add(sid)
    return allowed


def _play_line_english_gap_ids(manifest: Manifest, segments: list[dict]) -> set[str]:
    """Segment ids declared in ``english.gaps`` (ids or printed linerefs)."""
    declared = (manifest.data.get("english") or {}).get("gaps")
    if not isinstance(declared, list) or not declared:
        return set()
    by_id = {seg["id"] for seg in segments}
    by_ref: dict[str, str] = {}
    for seg in segments:
        for line in seg.get("lines") or []:
            ref = line.get("ref")
            if isinstance(ref, str) and ref:
                by_ref.setdefault(ref, seg["id"])
    allowed: set[str] = set()
    for item in declared:
        if item is None:
            continue
        token = str(item).strip()
        if not token:
            continue
        if token in by_id:
            allowed.add(token)
            continue
        if token in by_ref:
            allowed.add(by_ref[token])
            continue
        # A bare printed number that a range/suffix line covers.
        if token.isdigit():
            n = int(token)
            for seg in segments:
                for line in seg.get("lines") or []:
                    ref = line.get("ref")
                    if not isinstance(ref, str):
                        continue
                    if ref == token or ref.startswith("post ") and ref[5:] == token:
                        allowed.add(seg["id"])
                        break
                    if "-" in ref:
                        start, end = ref.split("-", 1)
                        if start.isdigit() and end.isdigit() and int(start) <= n <= int(end):
                            allowed.add(seg["id"])
                            break
                    if len(ref) > 1 and ref[:-1] == token and ref[-1:].isalpha():
                        allowed.add(seg["id"])
                        break
            continue
        allowed.add(token)
    return allowed


def _stage1_english_report(
    work_id: str, filename: str = "english_report.json"
) -> tuple[dict | None, str | None]:
    """The stage1 English report for THIS work, or an explicit error string.

    ``build/stage1`` is single-work scratch: a report left by the previous play
    must never authorise this one (Opus review 2026-09-07 item 6), and a
    missing or unreadable report must not silently open a gate (P2g finding
    11) -- both return an error the caller turns into ``ok: False``.
    """
    path = BUILD_DIR / "stage1" / filename
    label = (
        "English report"
        if filename == "english_report.json"
        else f"report {filename}"
    )
    if not path.exists():
        return None, f"no stage1 {label} at {path}"
    try:
        data = json.loads(path.read_text())
    except (ValueError, OSError) as exc:
        return None, f"unreadable stage1 {label} {path}: {exc}"
    if not isinstance(data, dict) or data.get("work") != work_id:
        got = data.get("work") if isinstance(data, dict) else None
        return None, (
            f"stage1 {label} is for {got!r}, not {work_id!r} "
            "(build/stage1 is single-work scratch)"
        )
    return data, None


# Stage-1 anomaly kinds that each mean one English piece reached no chunk.
_ATTACHMENT_LOSS_KINDS = (
    "unmatched_anchor",
    "nless_slice_unattached",
    "attribution_hole",
    "non_numeric_anchor",  # Astra lane C, F8
    "zero_n_content",  # Astra lane C, F8
)


def _attachment_loss_check(manifest: Manifest) -> dict:
    """Gate the perseus-play attachment loss (P2g finding 3).

    An English piece the builder could not attach to any Greek speech is
    translated text the reader never sees; before P2f a play could delete 113
    speeches and still print PASS. ``english.max_unresolved_mismatches``
    (default 0) is the allowance.

    P2h finding 5: P2f zeroed ``unresolved_mismatch_count`` (everything
    on-spine attaches), and the dropped text moved into ``anomalies``. The
    gate counts those kinds too — ``unmatched_anchor`` (an anchor on no
    Greek speech), ``nless_slice_unattached`` (a para slice with nowhere to
    go) and ``attribution_hole`` are each one English piece the reader never
    sees.  P2i retired the builder's only hole (an attribution difference is
    now an attached, flagged turn) and with it the dead
    ``speech_mismatch_unattached`` anomaly; ``attribution_hole`` stays in the
    tuple so a future hole is gated the moment it appears.
    """
    english_cfg = manifest.data.get("english") or {}
    max_unresolved = int(english_cfg.get("max_unresolved_mismatches", 0))
    data, error = _stage1_english_report(manifest.work_id)
    check = {
        "unresolved": None,
        "max_unresolved": max_unresolved,
        "mismatches": None,
        "attribution_differences": None,
        "error": error,
        "ok": error is None,
    }
    if data is None:
        return check
    anomalies = [a for a in (data.get("anomalies") or []) if isinstance(a, dict)]
    by_kind = {
        kind: sum(1 for a in anomalies if a.get("kind") == kind)
        for kind in _ATTACHMENT_LOSS_KINDS
    }
    unresolved = int(data.get("unresolved_mismatch_count") or 0) + sum(by_kind.values())
    check["dropped"] = by_kind
    if unresolved > max_unresolved:
        error = (
            f"{unresolved} English piece(s) attached to no Greek speech "
            f"(maximum {max_unresolved}): that text is dropped from the reader"
        )
    check.update(
        {
            "unresolved": unresolved,
            "mismatches": int(data.get("speech_mismatch_count") or 0),
            "attribution_differences": int(
                data.get("attribution_difference_count") or 0
            ),
            "error": error,
            "ok": error is None,
        }
    )
    return check


def _pick_turn_text_threshold(slot_entry: dict, english_cfg: dict, key: str, default):
    if isinstance(slot_entry, dict) and slot_entry.get(key) is not None:
        return slot_entry[key], f"english slot {key}"
    if english_cfg.get(key) is not None:
        return english_cfg[key], f"english.{key}"
    return default, f"english.{key}"


def _public_turn_text_comparison_slots(
    manifest: Manifest,
) -> list[tuple[str, dict, str]]:
    """Public (non-private) secondary/third/overlay turn-text slots (Astra lane C, F1)."""
    private_ids = private_translation_ids(manifest.data)
    english = manifest.data.get("english") or {}
    out: list[tuple[str, dict, str]] = []
    for slot, filename in (
        ("secondary", "secondary_report.json"),
        ("third", "third_report.json"),
    ):
        entry = english.get(slot)
        if not isinstance(entry, dict) or entry.get("model") != "turn-text":
            continue
        if entry.get("private") or entry.get("id") in private_ids:
            continue
        out.append((slot, entry, filename))
    for item in english.get("overlays") or []:
        if not isinstance(item, dict) or item.get("model") != "turn-text":
            continue
        if item.get("private") or item.get("id") in private_ids:
            continue
        tid = item.get("id") or ""
        out.append((f"overlay:{tid}", item, f"overlay_{tid}_report.json"))
    return out


def _turn_text_quality_checks(
    *,
    work_id: str,
    english_cfg: dict,
    slot_entry: dict,
    slot: str,
    filename: str,
    key_suffix: str,
) -> dict[str, dict]:
    """Pairing/shift/ratio/residual/head gates for one turn-text report."""
    floor = float(
        _pick_turn_text_threshold(slot_entry, english_cfg, "min_pairing_rate", 0.85)[0]
        or 0.85
    )
    max_ratio_rate = float(
        _pick_turn_text_threshold(slot_entry, english_cfg, "max_mismatch_rate", 0.25)[0]
    )
    max_shift_rate = float(
        _pick_turn_text_threshold(slot_entry, english_cfg, "max_turn_shift_rate", 0.10)[0]
    )
    max_residual = int(
        _pick_turn_text_threshold(slot_entry, english_cfg, "max_residual_unassigned", 0)[0]
    )
    max_low_confidence = float(
        _pick_turn_text_threshold(slot_entry, english_cfg, "max_low_confidence_rate", 0.08)[0]
    )
    max_bare_run = int(
        _pick_turn_text_threshold(slot_entry, english_cfg, "max_bare_run_events", 12)[0]
    )
    if isinstance(slot_entry, dict) and slot_entry.get("head_front_matter") is not None:
        declared_head = int(slot_entry["head_front_matter"])
        head_key = f"english.{slot}.head_front_matter"
    elif english_cfg.get("head_front_matter") is not None:
        declared_head = int(english_cfg["head_front_matter"])
        head_key = "english.head_front_matter"
    else:
        declared_head = 0
        head_key = f"english.{slot}.head_front_matter"
    slot_label = "" if slot == "primary" else f"{slot} "
    data, read_error = _stage1_english_report(work_id, filename)
    rate = None
    ratio_check = {
        "count": None,
        "paired": None,
        "rate": None,
        "max_rate": max_ratio_rate,
        "error": read_error,
        "ok": read_error is None,
    }
    shift_check = {
        "count": None,
        "paired": None,
        "rate": None,
        "max_rate": max_shift_rate,
        "error": read_error,
        "ok": read_error is None,
    }
    residual_check = {
        "count": None,
        "max_count": max_residual,
        "error": read_error,
        "ok": read_error is None,
    }
    head_check = {
        "count": None,
        "declared": declared_head,
        "error": read_error,
        "ok": read_error is None,
    }
    low_conf_check = {
        "rate": None,
        "count": None,
        "max_rate": max_low_confidence,
        "error": read_error,
        "ok": read_error is None,
    }
    bare_run_check = {
        "count": None,
        "max_count": max_bare_run,
        "runs": None,
        "error": read_error,
        "ok": read_error is None,
    }
    if data is not None:
        try:
            rate = float(data.get("pairing_rate"))
        except (ValueError, TypeError):
            rate = None
        paired = int(data.get("paired") or 0)
        ratio_count = int(data.get("length_ratio_outlier_count") or 0)
        ratio_rate = (
            ratio_count / paired if paired else (1.0 if ratio_count else 0.0)
        )
        ratio_error = None
        if ratio_rate > max_ratio_rate:
            ratio_error = (
                f"{slot_label}turn-text length-ratio outlier rate {ratio_rate:.3f} "
                f"exceeds maximum {max_ratio_rate:.3f} "
                f"({ratio_count}/{paired} paired speeches)"
            )
        ratio_check = {
            "count": ratio_count,
            "paired": paired,
            "rate": ratio_rate,
            "max_rate": max_ratio_rate,
            "error": ratio_error,
            "ok": ratio_error is None,
        }
        shift_count = int(data.get("turn_shift_count") or 0)
        raw_rate = data.get("turn_shift_rate")
        new_drifts = data.get("turn_shift_new_drifts")
        if raw_rate is None:
            new_drifts = shift_count
            shift_rate = (
                shift_count / paired if paired else (1.0 if shift_count else 0.0)
            )
        else:
            shift_rate = float(raw_rate)
            new_drifts = shift_count if new_drifts is None else int(new_drifts)
        shift_error = None
        if shift_rate > max_shift_rate:
            shift_error = (
                f"{slot_label}turn-text turn-shift rate {shift_rate:.3f} exceeds maximum "
                f"{max_shift_rate:.3f} ({new_drifts}/{paired} pairs OPEN a new "
                "same-name position drift; cumulative shifts "
                f"{shift_count})"
            )
        shift_check = {
            "count": shift_count,
            "new_drifts": new_drifts,
            "paired": paired,
            "rate": shift_rate,
            "max_rate": max_shift_rate,
            "error": shift_error,
            "ok": shift_error is None,
        }
        residual_unassigned = int(data.get("residual_unassigned") or 0)
        residual_error = None
        if residual_unassigned > max_residual:
            residual_error = (
                f"{slot_label}{residual_unassigned} residual English speech(es) parked "
                f"on no Greek speech (maximum {max_residual}): that text "
                "is dropped from the reader"
            )
        residual_check = {
            "count": residual_unassigned,
            "max_count": max_residual,
            "error": residual_error,
            "ok": residual_error is None,
        }
        # Astra lane C, F3: an opening English speech dropped before the first
        # pair is reader-visible loss unless the manifest names the exact
        # front-matter count.
        head_unassigned = int(data.get("head_unassigned") or 0)
        head_error = None
        if head_unassigned != declared_head:
            head_error = (
                f"{slot_label}{head_unassigned} English opening speech(es) dropped "
                f"before the first pair (declared {head_key}={declared_head}): "
                "that text is dropped from the reader"
            )
        head_check = {
            "count": head_unassigned,
            "declared": declared_head,
            "error": head_error,
            "ok": head_error is None,
        }
        # Turn-pairing design 2026-09-15 section 7: the DP's own confidence
        # signal (margin) and its loud holes (a Greek stretch the DP left
        # bare rather than sliding the rest of the play).
        low_conf_rate = data.get("low_confidence_rate")
        low_conf_pairs = int(data.get("low_confidence_pairs") or 0)
        low_conf_error = None
        if low_conf_rate is not None and low_conf_rate > max_low_confidence:
            low_conf_error = (
                f"{slot_label}turn-text low-confidence pairing rate {low_conf_rate:.3f} "
                f"exceeds maximum {max_low_confidence:.3f} ({low_conf_pairs}/{paired} "
                "pairs whose margin over the next-best match is thin)"
            )
        low_conf_check = {
            "rate": low_conf_rate,
            "count": low_conf_pairs,
            "max_rate": max_low_confidence,
            "error": low_conf_error,
            # Round 2 task 3: WARN, never fail the build, until a later
            # per-play pass declares `known_gaps` and turns this into a real
            # gate -- "ok" stays true so `report["ok"]` never sees it.
            "warn": low_conf_error is not None,
            "ok": True,
        }
        known_gaps = (
            slot_entry.get("known_gaps") if isinstance(slot_entry, dict) else None
        ) or []
        runs = data.get("greek_skip_runs") or []
        undeclared_events = sum(
            int(r.get("events") or 0)
            for r in runs
            if not r.get("covered") and not _gap_declared(r, known_gaps)
        )
        bare_error = None
        if undeclared_events > max_bare_run:
            spans = ", ".join(
                f"{r.get('start_ref')}–{r.get('end_ref')}"
                for r in runs
                if not r.get("covered") and not _gap_declared(r, known_gaps)
            )
            bare_error = (
                f"{slot_label}{undeclared_events} Greek event(s) left bare in an "
                f"undeclared skip run (maximum {max_bare_run}): {spans} -- declare "
                f"each under english.{slot}.known_gaps or restore the missing text"
            )
        bare_run_check = {
            "count": undeclared_events,
            "max_count": max_bare_run,
            "runs": runs,
            "error": bare_error,
            # Round 2 task 3: WARN, never fail the build (see low_conf_check
            # above) -- a later per-play pass declares `known_gaps` and turns
            # this into a real gate.
            "warn": bare_error is not None,
            "ok": True,
        }
    floor_error = read_error
    if data is not None:
        if rate is None:
            floor_error = (
                f"{slot_label}turn-text stage-1 report carries no pairing_rate: "
                f"the {floor:.3f} floor cannot be checked"
            )
        elif rate < floor:
            floor_error = (
                f"{slot_label}turn-text pairing rate {rate:.3f} is below the floor "
                f"{floor:.3f} (english.min_pairing_rate): too much of the "
                "Greek carries no English of its own"
            )
    floor_check = {
        "rate": rate,
        "floor": floor,
        "error": floor_error,
        "ok": floor_error is None,
    }
    suffix = key_suffix
    return {
        f"turn_text_length_ratio{suffix}": ratio_check,
        f"turn_text_turn_shift{suffix}": shift_check,
        f"turn_text_residual_unassigned{suffix}": residual_check,
        f"turn_text_head_unassigned{suffix}": head_check,
        f"turn_text_pairing_floor{suffix}": floor_check,
        f"turn_text_low_confidence{suffix}": low_conf_check,
        f"turn_text_bare_run{suffix}": bare_run_check,
    }


def _gap_declared(run: dict, known_gaps: list) -> bool:
    """Is a ``greek_skip_runs`` entry covered by a manifest-declared
    ``english.<slot>.known_gaps: [{from, to, note}]`` span (turn-pairing
    design 2026-09-15, section 3.5)?"""

    def num(ref) -> int | None:
        m = re.match(r"(\d+)", str(ref or ""))
        return int(m.group(1)) if m else None

    lo, hi = num(run.get("start_ref")), num(run.get("end_ref"))
    if lo is None or hi is None:
        return False
    for gap in known_gaps:
        if not isinstance(gap, dict):
            continue
        glo, ghi = num(gap.get("from")), num(gap.get("to"))
        if glo is not None and ghi is not None and glo <= lo and hi <= ghi:
            return True
    return False


# --- A3: a comparison column that is simply blank ---------------------------
#
# A turn-text column that has no text for a Greek speech AND no
# `englishCoveredBy` note prints as a silent blank: the reader cannot tell
# whether the translator dropped the lines, or the builder lost them. It is
# how Birds 1:302, 1:907, 1:908 and 1:417 and Clouds 1:1112 reach the page.
# Nothing else on the sheet sees it -- `turn_text_bare_run` counts EVENTS off
# the stage-1 report and stops at the primary's own coverage, and
# `strict_coverage` runs for one slot only.
#
# It is a WARNING (John decides whether it fails the build): a comparison
# bench legitimately omits passages, and until each column's omissions are
# declared the count is a reading list, not a gate.
_BLANK_COLUMN_FILES = {
    "primary": ("english_chunks.json", "alignment.json"),
    "secondary": ("ross_chunks.json", "secondary_alignment.json"),
    "third": ("third_chunks.json", "third_alignment.json"),
}


def _column_chunk_ids(path: Path, translation_id: str | None) -> set[str] | None:
    """The segment ids a stage-1 column file actually carries text for."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    if isinstance(data, dict) and "chunks" in data:
        rows = {c["id"]: c for c in data["chunks"] if isinstance(c, dict)}
    else:
        if translation_id is not None:
            data = (data or {}).get(translation_id) or {}
        rows = {
            sid: (pieces[0] if isinstance(pieces, list) and pieces else {})
            for sid, pieces in (data or {}).items()
        }
    return {sid for sid, row in rows.items() if (row or {}).get("text")}


def _turn_text_columns(manifest: Manifest) -> list[tuple[str, Path, Path, str | None]]:
    """(label, chunk file, alignment file, overlay id) per turn-text column."""
    stage1 = BUILD_DIR / "stage1"
    english = manifest.data.get("english") or {}
    out: list[tuple[str, Path, Path, str | None]] = []
    primary = english.get("primary") or {}
    if primary.get("model") == "turn-text":
        chunks, align = _BLANK_COLUMN_FILES["primary"]
        out.append(("primary", stage1 / chunks, stage1 / align, None))
    for slot, entry, _filename in _public_turn_text_comparison_slots(manifest):
        if slot.startswith("overlay:"):
            tid = slot.split(":", 1)[1]
            out.append(
                (slot, stage1 / "overlays.json",
                 stage1 / f"overlay_{tid}_alignment.json", tid)
            )
            continue
        chunks, align = _BLANK_COLUMN_FILES[slot]
        out.append((slot, stage1 / chunks, stage1 / align, None))
    return out


def blank_column_segments(
    columns: list[tuple[str, set[str] | None, set[str]]],
    speaking: list[str],
) -> dict[str, list[str]]:
    """Per column, the speaking segments it leaves blank with no note.

    ``columns`` is ``(label, ids with text, ids with a coveredBy note)``; a
    column whose file could not be read (``None``) is skipped rather than
    reported blank everywhere.
    """
    out: dict[str, list[str]] = {}
    for label, has_text, covered in columns:
        if has_text is None:
            continue
        blanks = [sid for sid in speaking if sid not in has_text and sid not in covered]
        if blanks:
            out[label] = blanks
    return out


def _blank_column_check(manifest: Manifest, segments: list[dict]) -> dict:
    # A lacuna placeholder often carries the speaker the editor conjectures
    # for the lost lines, but it is not a Greek speech and no column should
    # hold anything beside it (`stage1_turn_english.is_lacuna_segment`).
    holes = _play_line_lacuna_segment_ids(segments)
    speaking = [
        seg["id"] for seg in segments if seg.get("speakers") and seg["id"] not in holes
    ]
    columns = []
    for label, chunk_path, align_path, tid in _turn_text_columns(manifest):
        covered: set[str] = set()
        if align_path.exists():
            try:
                covered = set(
                    (json.loads(align_path.read_text(encoding="utf-8")) or {}).get(
                        "english_covered_by"
                    )
                    or {}
                )
            except (ValueError, OSError):
                covered = set()
        columns.append((label, _column_chunk_ids(chunk_path, tid), covered))
    blanks = blank_column_segments(columns, speaking)
    total = sum(len(v) for v in blanks.values())
    warning = None
    if total:
        listed = "; ".join(
            f"{label}: {len(ids)} ({', '.join(ids[:12])}{' ...' if len(ids) > 12 else ''})"
            for label, ids in blanks.items()
        )
        warning = (
            f"{total} Greek speech(es) sit beside a blank turn-text column with no "
            f"englishCoveredBy note -- {listed}; restore the text, or declare the "
            "omission so the reader is told"
        )
    return {
        "count": total,
        "columns": blanks,
        "error": warning,
        "warn": warning is not None,
        "ok": True,
    }


# --- R7: a Greek roster speaker no English cue in a column resolves to ------
#
# Suppliants' Greek names Danaids, Egyptians and Handmaidens; Morshead's only
# chorus cues are CHORUS and SEMI-CHORUS (both `Chorus`) and Johnston's are
# CHORUS and HANDMAIDENS, so nothing a reader can see says that a whole
# stretch of the play is being paired with no speaker evidence at all. It is
# not necessarily a defect -- a translator who prints SEMI-CHORUS where the
# edition prints ΘΕΡΑΠΑΙΝΑΙ is making his own choice, and an `english_
# overrides` entry or an alias is the remedy when it matters -- so this lists
# the names per column and warns. The stage-1 report already computes it
# (`speakers.only_in_greek`); this is where a reviewer sees it.
def _slot_report(manifest: Manifest, filename: str) -> list[dict]:
    """A turn-text slot's ``unenglished_events`` (R10), or ``[]``."""
    path = BUILD_DIR / "stage1" / filename
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8")) or {}
    except (ValueError, OSError):
        return []
    events = data.get("unenglished_events")
    return list(events) if isinstance(events, list) else []


# --- R8: a declaration the build contradicts -------------------------------
#
# `english.gaps` says "the translation omits this line", and `strict_coverage`
# treats every entry as an allowance. Nine of Peace's eleven entries have
# English in the built book -- 517, 439, 441, 484, 488, 489, 490, 499 and 1063
# are all present, and only 468 is truly bare -- so the gate ran green over a
# declaration list that was almost entirely false, and it masked two real
# displacements. A dead declaration is worse than none: it is an allowance for
# damage nobody is looking at. Warned rather than failed, because the remedy is
# a manifest edit and the list is John's to re-derive.
def _dead_gap_check(
    manifest: Manifest, segments: list[dict], unmatched: list[str],
    covered_ids: list[str],
) -> dict:
    declared = _play_line_english_gap_ids(manifest, segments)
    if not declared:
        return {"count": 0, "with_english": [], "also_covered": [], "ok": True}
    first_ref = {
        seg["id"]: next(
            (l.get("ref") for l in (seg.get("lines") or []) if l.get("ref")), None
        )
        for seg in segments
    }
    with_english = sorted(declared - set(unmatched))
    also_covered = sorted(declared & set(covered_ids))
    dead = sorted(set(with_english) | set(also_covered))
    warning = None
    if dead:
        named = ", ".join(str(first_ref.get(s) or s) for s in dead[:25])
        warning = (
            f"{len(dead)} english.gaps declaration(s) the build contradicts: "
            f"{named}{' ...' if len(dead) > 25 else ''} -- each has English of "
            "its own, or is declared covered as well; re-derive the list, "
            "because strict_coverage is allowing these segments on a false "
            "declaration"
        )
    return {
        "count": len(dead),
        "with_english": with_english,
        "also_covered": also_covered,
        "error": warning,
        "warn": warning is not None,
        "ok": True,
    }


def _unmapped_speaker_check(manifest: Manifest) -> dict:
    stage1 = BUILD_DIR / "stage1"
    english = manifest.data.get("english") or {}
    files: list[tuple[str, str]] = []
    if (english.get("primary") or {}).get("model") == "turn-text":
        files.append(("primary", "english_report.json"))
    for slot, _entry, filename in _public_turn_text_comparison_slots(manifest):
        files.append((slot, filename))
    columns: dict[str, list[str]] = {}
    for label, filename in files:
        path = stage1 / filename
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8")) or {}
        except (ValueError, OSError):
            continue
        names = ((data.get("speakers") or {}).get("only_in_greek")) or []
        if names:
            columns[label] = list(names)
    total = sum(len(v) for v in columns.values())
    warning = None
    if total:
        listed = "; ".join(
            f"{label}: {', '.join(names)}" for label, names in columns.items()
        )
        warning = (
            f"{total} Greek roster speaker(s) that no English cue resolves to -- "
            f"{listed}; their turns are paired with no speaker evidence, so check "
            "the alias map or english_overrides for each column"
        )
    return {
        "count": total,
        "columns": columns,
        "error": warning,
        "warn": warning is not None,
        "ok": True,
    }


def _dead_primary_covered_declarations(
    manifest: Manifest, segments: list[dict], chunk_ids: set[str]
) -> list[dict]:
    """A declared ``english.primary.covered`` entry whose Greek segment now
    carries its OWN English chunk (C1, 2026-09-17 fix-mechanisms brief): the
    drift-repair fix stops moving a line that names its own ref onto a
    neighbour, so a ``covered`` entry written to mask that old displacement
    (oedipus-tyrannus's ``{greek: "625", by: "624"}``, electra-eur's
    ``{greek: "650", by: "post 651"}``) no longer describes what the build
    does.  Reported for the orchestrator to drop, or replace with whatever
    the segment it displaced now needs (oedipus-tyrannus 624 -> 623) --
    never failed here, since a stale declaration is harmless (stage7 never
    emits ``englishCoveredBy`` next to a real chunk) and dropping it is a
    manifest/data change outside this file's blast radius."""
    declared = ((manifest.data.get("english") or {}).get("primary") or {}).get("covered") or []
    first_ref: dict[str, str] = {}
    for seg in segments:
        lines = seg.get("lines") or seg.get("greek") or []
        ref = next(
            (str(l.get("ref")) for l in lines if isinstance(l, dict) and l.get("ref") is not None),
            None,
        )
        if ref is not None:
            first_ref.setdefault(ref, seg["id"])
    dead = []
    for item in declared:
        if not isinstance(item, dict):
            continue
        greek = str(item.get("greek", "")).strip()
        sid = first_ref.get(greek)
        if sid and sid in chunk_ids:
            dead.append({"greek": greek, "by": item.get("by"), "segment": sid})
    return dead


def validate(manifest: Manifest, spine: dict, english: dict, alignment: dict) -> dict:
    report: dict = {"checks": {}}
    segments = spine["segments"]
    # Dispatch structural rules on the citation scheme instead of ad-hoc string
    # tests. "observed" schemes (busse, stephanus) carry irregular, per-work
    # column spans whose page numbers are not globally unique and whose interior
    # pages are not guaranteed to hold every section letter, so their expected
    # column set is the OBSERVED spine, never a rectangular page x side range;
    # editorial line-number gaps on those schemes are demoted (not failures).
    sch = scheme_mod.for_manifest(manifest)
    observed = sch.validation_mode == "observed"

    # --- 1. column completeness + monotonicity --------------------------
    seen_cols: list[str] = []
    for seg in segments:
        if seg["column"] not in seen_cols:
            seen_cols.append(seg["column"])
    expected = list(seen_cols) if observed else column_range(
        manifest.first_column, manifest.last_column, sch.range_sides)
    missing = sorted(set(expected) - set(seen_cols), key=lambda c: column_key(c, sch))
    extra = sorted(set(seen_cols) - set(expected), key=lambda c: column_key(c, sch))
    keys = [column_key(c, sch) for c in seen_cols]
    monotonic = all(a <= b for a, b in zip(keys, keys[1:]))
    # verse-line (Lucretius' DRN) is DELIBERATELY non-monotonic in document
    # order — editors reprint transposed blocks under their original line
    # numbers (design memo §3.3), so document order != citation order by
    # design, not defect. stage1_latin's own parse-time gate
    # (`_derive_transposed_blocks` vs. the manifest's declared
    # `citation.transpositions`) is the real drift tripwire for this;
    # citation-order monotonicity is instead asserted post-sort, against the
    # emitted dist data, by preflight's verse-line gate. `monotonic` is still
    # reported here for information, just not gated on.
    report["checks"]["columns"] = {
        "expected": len(expected),
        "found": len(seen_cols),
        "missing": missing,
        "extra": extra,
        "monotonic": monotonic,
        "ok": not missing and not extra and (monotonic or sch.verse_line_scheme or sch.play_line_scheme),
    }

    # --- 1b. section-token order (observed schemes only) ----------------
    # The spine's columns must be STRICTLY increasing in ref order (17e before
    # 18a). Missing letters within a page or skipped pages are legal (works
    # start/end mid-page; interior pages need not carry every letter) and are
    # reported as info, honouring manifest-declared `expected_section_gaps`.
    # Skipped for a dk (Diels-Kranz) scheme: its column_key is a 3-tuple
    # (series, number, suffix), not the 2-tuple (page, letter) this
    # page/letter-contiguity check is shaped for, and dk's numbering has
    # real, EXPECTED non-contiguous gaps throughout (declared deletions like
    # B84/B109, not just at page boundaries) — the section_spine count+sha256
    # fingerprint immediately below (1c) is dk's actual completeness+order
    # gate (memo gate 2).
    # Skipped for verse-line the same way dk is skipped just below (and for
    # the same reason): this check assumes a (page, letter)-axis grammar —
    # verse-line's second component is a richer (number, suffix)/range
    # lineref with EXPECTED non-contiguous jumps (the transposed blocks
    # above), not a defect this page/letter-contiguity check is shaped to
    # describe.
    # `declared_gaps` is manifest data, not scheme-shaped, and is also needed
    # by the section_spine diagnostic below (1c) for fragment/verse-line
    # schemes (dk's "real, EXPECTED non-contiguous gaps" the comment above
    # describes) -- so it is computed unconditionally, unlike `letter_ix`
    # (below), which only makes sense for a genuine letter-axis scheme.
    declared_gaps = {
        (g["after"], g["next"])
        for g in manifest.data.get("expected_section_gaps", [])
        if isinstance(g, dict) and {"after", "next"} <= g.keys()
    }
    if observed and not sch.fragment_scheme and not sch.verse_line_scheme and not sch.play_line_scheme:
        letter_ix = {ch: i for i, ch in enumerate(sch.section_letters)}
        strictly_increasing = all(a < b for a, b in zip(keys, keys[1:]))
        section_gaps: list[dict] = []
        for (c_prev, k_prev), (c_next, k_next) in zip(
            zip(seen_cols, keys), zip(seen_cols[1:], keys[1:])
        ):
            (p0, l0), (p1, l1) = k_prev, k_next
            if sch.numeric_section:
                # book-section: sections are consecutive integers within a book
                # ("4.9" -> "4.10"), and any section starts the next book.
                contiguous = (p0 == p1 and l1 == l0 + 1) or (p1 == p0 + 1)
            else:
                contiguous = (
                    (p0 == p1 and letter_ix.get(l1, -99) == letter_ix.get(l0, -1) + 1)
                    or (p1 == p0 + 1)  # advancing to the next page is normal
                )
            if not contiguous:
                section_gaps.append({
                    "after": c_prev,
                    "next": c_next,
                    "expected": (c_prev, c_next) in declared_gaps,
                })
        report["checks"]["section_order"] = {
            "strictly_increasing": strictly_increasing,
            "gaps": section_gaps,  # informational
            "ok": strictly_increasing,
        }

    # --- 1c. immutable observed-section baseline -----------------------
    # Stephanus exports are irregular, so a rectangular range cannot establish
    # completeness.  Instead, compare the ordered section-token spine with the
    # verified per-work manifest fingerprint captured from stage 1.
    if sch.has_sections:
        baseline = manifest.data.get("section_spine") or {}
        expected_count = baseline.get("count")
        expected_sha256 = baseline.get("sha256")
        got_count = len(seen_cols)
        got_sha256 = hashlib.sha256(",".join(seen_cols).encode("utf-8")).hexdigest()
        count_ok = isinstance(expected_count, int) and got_count == expected_count
        hash_ok = (
            isinstance(expected_sha256, str)
            and len(expected_sha256) == 64
            and got_sha256 == expected_sha256.lower()
        )
        first_ok = bool(seen_cols) and seen_cols[0] == manifest.first_column
        last_ok = bool(seen_cols) and seen_cols[-1] == manifest.last_column

        first_diverging = None
        if not count_ok:
            # A digest-only baseline intentionally does not duplicate the full
            # token list. Pinpoint the first structurally suspicious observed
            # token: an undeclared within-page jump (the common deletion case),
            # or the first/last token when the boundary itself moved.
            if not first_ok and seen_cols:
                first_diverging = {"index": 0, "token": seen_cols[0]}
            else:
                for i, ((prev, pkey), (nxt, nkey)) in enumerate(
                    zip(zip(seen_cols, keys), zip(seen_cols[1:], keys[1:])), 1
                ):
                    if sch.numeric_section or sch.fragment_scheme:
                        # dk's column_key is a (series, number, suffix) triple
                        # (refs.py's column_key) — no letter axis, so its
                        # second component is already an int, same as
                        # numeric_section's, and the int-jump comparison below
                        # is meaningful for it too. `letter_ix` (built above
                        # only for genuine letter schemes) is never populated
                        # for dk, so this branch must not fall to the `else`.
                        same_page_jump = pkey[0] == nkey[0] and nkey[1] > pkey[1] + 1
                    else:
                        same_page_jump = (
                            pkey[0] == nkey[0]
                            and letter_ix.get(nkey[1], -99) > letter_ix.get(pkey[1], -1) + 1
                        )
                    if same_page_jump and (prev, nxt) not in declared_gaps:
                        first_diverging = {"index": i, "token": nxt, "after": prev}
                        break
                if first_diverging is None and seen_cols:
                    i = min(got_count, expected_count or got_count) - 1
                    first_diverging = {"index": max(i, 0), "token": seen_cols[max(i, 0)]}

        report["checks"]["section_spine"] = {
            "expected": {"count": expected_count, "sha256": expected_sha256},
            "got": {"count": got_count, "sha256": got_sha256},
            "count_match": count_ok,
            "hash_match": hash_ok,
            "first_column": {"expected": manifest.first_column,
                             "got": seen_cols[0] if seen_cols else None,
                             "ok": first_ok},
            "last_column": {"expected": manifest.last_column,
                            "got": seen_cols[-1] if seen_cols else None,
                            "ok": last_ok},
            "first_diverging_token": first_diverging,
            "ok": count_ok and hash_ok and first_ok and last_ok,
        }

    # --- 1d. book partition (section schemes) ---------------------------
    # The declared books MUST partition the observed spine: ordered and
    # non-overlapping by (page, letter), and every observed section falls in
    # exactly one book. A section outside every declared range is an ERROR (the
    # book table is missing coverage); a section claimed by two ranges means the
    # ranges overlap. Bekker/busse books are handled by the line-gap check.
    if sch.has_sections:
        from .refs import column_prefix_key

        ranges = [
            (b["n"], column_prefix_key(b["start"], sch), column_prefix_key(b["end"], sch))
            for b in manifest.books
        ]
        within = all(s <= e for _, s, e in ranges)
        ordered = all(a[2] < b[1] for a, b in zip(ranges, ranges[1:]))
        outside: list[str] = []
        overlapping: list[str] = []
        for col in seen_cols:
            k = column_prefix_key(col, sch)
            hits = [n for n, s, e in ranges if s <= k <= e]
            if not hits:
                outside.append(col)
            elif len(hits) > 1:
                overlapping.append(col)
        report["checks"]["book_partition"] = {
            "books": len(ranges),
            "ordered_non_overlapping": within and ordered,
            "sections_outside_any_book": outside,
            "sections_in_multiple_books": overlapping,
            "ok": within and ordered and not outside and not overlapping,
        }

    # --- 2. line-number gaps ---------------------------------------------
    # Expected gaps: between one book's end and the next book's start when
    # they share a column (Bekker numbering skips the heading lines). Only
    # line-bearing schemes declare book boundaries with a line number; section
    # schemes (stephanus) bound books by a page+letter column and demote all
    # intra-column line gaps below, so their book table is skipped here.
    expected_gaps = set()
    books = manifest.books
    if not observed:
        for prev, nxt in zip(books, books[1:]):
            e_page, e_side, e_line = ref_key(prev["end"])
            s_page, s_side, s_line = ref_key(nxt["start"])
            if (e_page, e_side) == (s_page, s_side):
                expected_gaps.add((f"{e_page}{e_side}", e_line, s_line))
    # Edition quirks declared in the manifest (e.g. a repeated line number).
    for g in manifest.data.get("expected_line_gaps", []):
        expected_gaps.add((g["column"], g["after"], g["next"]))
    gaps = []
    lines_by_col: dict[str, list[int]] = defaultdict(list)
    for seg in segments:
        lines_by_col[seg["column"]].extend(l["n"] for l in seg["lines"])
    for col, nums in lines_by_col.items():
        for a, b in zip(nums, nums[1:]):
            if b != a + 1:
                entry = {
                    "column": col,
                    "after_line": a,
                    "next_line": b,
                    "expected": (col, a, b) in expected_gaps,
                }
                gaps.append(entry)
    # observed schemes: line numbers are editorial (busse per-page numbering with
    # section headings dropped; stephanus lines restart per section and are not
    # user-facing citation targets), so intra-column line-number gaps are demoted
    # to non-failing warnings rather than treated as spine defects.
    if observed:
        for g in gaps:
            g["expected"] = True
    unexpected_gaps = [g for g in gaps if not g["expected"]]
    report["checks"]["line_gaps"] = {
        "gaps": gaps,
        "unexpected": unexpected_gaps,
        "ok": not unexpected_gaps,
    }

    # --- 3. alignment coverage -------------------------------------------
    # P2e: a segment whose English sits on an earlier speech (continuation
    # coverage) is not a hole. englishCoveredBy on the pair, or the parallel
    # english_covered_by map, both count as covered.
    # P2f: an attribution-difference attachment is a real chunk (the English
    # speaker disagrees with the Greek line owner, flagged speakerMismatch
    # on the chunk). It pairs here like any other chunk and is not unmatched.
    # P2g finding 4: coverage is an ALLOWANCE, not a silent deletion. A covered
    # segment stays in `unmatched_segments` (and in `covered_ids`) and is
    # allowed by reason; a hole that is neither attached nor covered still has
    # to be named in `english.gaps`.
    covered_by = alignment.get("english_covered_by") or {}
    covered_ids = sorted(
        set(covered_by)
        | {p["segment"] for p in alignment["pairs"] if p.get("englishCoveredBy")}
    )
    unmatched = [
        p["segment"] for p in alignment["pairs"] if p["english"] is None
    ]
    # Columns the English TEI demonstrably cannot cover (Perseus omitted a Bekker
    # page milestone, or assigns a book-straddling column to a single book) are
    # declared in the manifest so they're surfaced but don't fail the build.
    allowed = set(manifest.data.get("alignment_allow_unmatched", []))
    primary_model = (
        ((manifest.data.get("english") or {}).get("primary") or {}).get("model")
    )
    if sch.play_line_scheme and primary_model == "perseus-play":
        # perseus-play is sparse by design, but a hole is only legal when the
        # manifest names it in english.gaps (segment ids or printed refs) --
        # or when the translator's own block, attached to another segment,
        # demonstrably contains it (continuation coverage).
        allowed.update(_play_line_english_gap_ids(manifest, segments))
        allowed.update(_play_line_lacuna_segment_ids(segments))
        allowed.update(_play_line_allowed_twin_ids(manifest, segments))
        allowed.update(covered_ids)
        report["checks"]["attachment_loss"] = _attachment_loss_check(manifest)
        dead_covered = _dead_primary_covered_declarations(
            manifest, segments, {c["id"] for c in english.get("chunks") or []}
        )
        report["checks"]["primary_dead_covered"] = {
            "dead": dead_covered,
            # Informational only (C1): a stale declaration is harmless at
            # emission time, so this never fails or warns the build -- it
            # just names what the orchestrator should drop from the manifest.
            "ok": True,
        }
    if sch.play_line_scheme and primary_model == "turn-text":
        # turn-text (P3, the 1912 comedies): the English has no line numbers,
        # so speeches pair by speaker turn and residue is grouped onto the
        # previous paired speech — never dropped. The honest contract is a
        # pairing-rate floor the manifest declares (default 0.85, plan P3
        # acceptance), read from the builder's own report and gated on its own
        # by `checks.turn_text_pairing_floor` (P3.5 finding 3); every unpaired
        # Greek speech is an expected, labelled ("by speech")
        # hole whether the floor holds or not. Since P3.4 the report's
        # `pairing_rate` is per Greek speaker EVENT (one slot per antilabe
        # share), which is what this floor now reads; the old per-segment
        # figure rides beside it as `segment_pairing_rate` and is not gated.
        english_cfg = manifest.data.get("english") or {}
        report["checks"].update(
            _turn_text_quality_checks(
                work_id=manifest.work_id,
                english_cfg=english_cfg,
                slot_entry=english_cfg.get("primary") or {},
                slot="primary",
                filename="english_report.json",
                key_suffix="",
            )
        )
        allowed.update(unmatched)
        allowed.update(_play_line_english_gap_ids(manifest, segments))
        allowed.update(_play_line_lacuna_segment_ids(segments))
        # Item 6 (John, 2026-09-09: "all English matched to Greek, or flag
        # that there is no Greek for the English"): with
        # english.strict_coverage, every Greek speech that carries no English
        # of its own must be declared -- in english.gaps (the translation
        # omits it) or english.<slot>.covered (its English sits in the
        # neighbouring speech) -- or the build fails naming it.
        if english_cfg.get("strict_coverage"):
            declared = (
                _play_line_english_gap_ids(manifest, segments)
                | set(covered_ids)
                | _play_line_lacuna_segment_ids(segments)
            )
            speaking = {seg["id"] for seg in segments if seg.get("speakers")}
            holes = [sid for sid in unmatched if sid in speaking and sid not in declared]
            first_ref = {
                seg["id"]: next((l.get("ref") for l in (seg.get("lines") or []) if l.get("ref")), None)
                for seg in segments
            }
            strict_error = None
            if holes:
                named = ", ".join(str(first_ref.get(s) or s) for s in holes[:25])
                strict_error = (
                    f"{len(holes)} Greek speech(es) carry no English and are not "
                    f"declared: {named}{' ...' if len(holes) > 25 else ''} -- pin the "
                    "English, or declare each under english.gaps (omitted) or "
                    "english.primary.covered (translated with a neighbour)"
                )
            # R10 (acharnians finding 5): the same question asked per Greek
            # SPEECH. `unmatched` is a segment list, so a packed comedy line
            # whose two shares the translator renders as one turn leaves the
            # second share with no English and nothing to declare it -- the
            # reader gets one English block against a line the Greek divides
            # between two speakers. Warned, not gated: turning it into a
            # failure would fail eleven comedies on undeclared shares before
            # anybody has ruled on them, and the declarations are John's.
            slot_holes = [
                event
                for event in (_slot_report(manifest, "english_report.json") or [])
                if event.get("segment") not in declared
            ]
            slot_warning = None
            if slot_holes:
                named = ", ".join(
                    f"{e.get('ref')} ({e.get('speaker')})" for e in slot_holes[:25]
                )
                slot_warning = (
                    f"{len(slot_holes)} Greek speech(es) inside a segment that HAS "
                    f"English carry none of their own and are not declared: {named}"
                    f"{' ...' if len(slot_holes) > 25 else ''}"
                )
            report["checks"]["turn_text_strict_coverage"] = {
                "count": len(holes),
                "holes": holes,
                "slot_holes": slot_holes,
                "slot_warning": slot_warning,
                "error": strict_error,
                "warn": strict_error is None and slot_warning is not None,
                "ok": strict_error is None,
            }
    if sch.play_line_scheme:
        # Astra lane C, F1: public comparison turn-text reports use the same
        # quality floors as primary (slot key, then english.*, then defaults).
        english_cfg = manifest.data.get("english") or {}
        for slot, entry, filename in _public_turn_text_comparison_slots(manifest):
            suffix = "_" + slot.replace(":", "_")
            report["checks"].update(
                _turn_text_quality_checks(
                    work_id=manifest.work_id,
                    english_cfg=english_cfg,
                    slot_entry=entry,
                    slot=slot,
                    filename=filename,
                    key_suffix=suffix,
                )
            )
        report["checks"]["turn_text_blank_columns"] = _blank_column_check(
            manifest, segments
        )
        report["checks"]["turn_text_unmapped_speakers"] = _unmapped_speaker_check(
            manifest
        )
        report["checks"]["english_dead_gaps"] = _dead_gap_check(
            manifest, segments, unmatched, covered_ids
        )
    # A column the manifest's own citation.kind_overrides declares `omit`
    # is ALSO a legitimate unmatched column (see _omit_declared_segment_ids)
    # -- derived from the SAME declaration stage1 already enforces, not a
    # second hand-maintained allowance list.
    allowed |= _omit_declared_segment_ids(manifest, segments)
    allowed |= _summary_suppressed_segment_ids(manifest, segments)
    unexpected_unmatched = [s for s in unmatched if s not in allowed]
    # A book-boundary edition mismatch is symmetric: the English TEI places a
    # book division a column off from the Greek, leaving both an unpaired Greek
    # segment and an unpaired English chunk. The allowance covers either side.
    unexpected_english_only = [s for s in alignment["english_only"] if s not in allowed]
    report["checks"]["alignment"] = {
        "pairs": len(alignment["pairs"]),
        "unmatched_segments": unmatched,
        "covered_ids": covered_ids,
        "allowed_unmatched": sorted(allowed & (set(unmatched) | set(alignment["english_only"]))),
        "unexpected_unmatched": unexpected_unmatched,
        "english_only": alignment["english_only"],
        "unexpected_english_only": unexpected_english_only,
        "ok": not unexpected_unmatched and not unexpected_english_only,
    }

    # --- 4. length-ratio gate ----------------------------------------------
    # A chapter whose English/Greek character ratio falls far outside the healthy
    # spread signals extraction damage: a truncated chapter reads far too short, a
    # footnote/apparatus-contaminated one far too long. The bound is derived from
    # the healthy body of the distribution using robust statistics (median + MAD
    # of the log-ratio), which resist the very outliers being hunted — so a
    # handful of damaged chapters cannot inflate the spread and hide themselves.
    # When the manifest opts in via `length_ratio_gate` this is a HARD gate with a
    # named-chapter message; otherwise it stays informational, so a work whose
    # ratio profile has not been vetted is never failed silently. `exempt` columns
    # (genuinely terse chapters, cross-validated by eye) are dropped from BOTH the
    # statistics and the pass/fail test.
    eng_by_id = {c["id"]: c for c in english["chunks"]}
    gate_cfg = manifest.data.get("length_ratio_gate")
    exempt = set((gate_cfg or {}).get("exempt", []))
    max_z = float((gate_cfg or {}).get("max_robust_z", 6.0))
    ratios = []
    for seg in segments:
        eng = eng_by_id.get(seg["id"])
        if eng is None:
            continue
        glen = sum(len(l["text"]) for l in seg["lines"])
        elen = len(eng["text"])
        if glen and elen:
            ratios.append({"column": seg["column"], "ratio": elen / glen,
                           "greek_chars": glen, "english_chars": elen})
    logs = [math.log(r["ratio"]) for r in ratios if r["column"] not in exempt]
    # No paired English yet (e.g. a stephanus work whose English walker runs in a
    # separate pass) → nothing to compare; report an empty, passing check.
    if len(logs) < 2:
        report["checks"]["length_ratio"] = {
            "median": 0.0, "robust_sd": 0.0, "max_robust_z": max_z,
            "enforced": bool(gate_cfg), "exempt": sorted(exempt),
            "outliers": [], "failures": [], "ok": True,
        }
    else:
        med = statistics.median(logs)
        mad = statistics.median([abs(x - med) for x in logs])
        # robust SD from the MAD; fall back to plain SD if the MAD collapses
        # (near-identical ratios) so the z-score never divides by zero.
        robust_sd = 1.4826 * mad or statistics.pstdev(logs) or 1.0
        scored = []
        for r in ratios:
            z = (math.log(r["ratio"]) - med) / robust_sd
            scored.append({**r, "ratio": round(r["ratio"], 3), "robust_z": round(z, 2)})
        outliers = sorted((s for s in scored if abs(s["robust_z"]) > 3.5),
                          key=lambda s: -abs(s["robust_z"]))
        failures = [s for s in scored
                    if abs(s["robust_z"]) > max_z and s["column"] not in exempt]
        report["checks"]["length_ratio"] = {
            "median": round(math.exp(med), 3),
            "robust_sd": round(robust_sd, 4),
            "max_robust_z": max_z,
            "enforced": bool(gate_cfg),
            "exempt": sorted(exempt),
            "outliers": outliers,
            "failures": failures,
            "ok": (not failures) if gate_cfg else True,
        }

    # --- 5. proper-name spot check ------------------------------------------
    greek_text_by_col: dict[str, str] = defaultdict(str)
    eng_text_by_col: dict[str, str] = defaultdict(str)
    for seg in segments:
        greek_text_by_col[seg["column"]] += " ".join(l["text"] for l in seg["lines"])
    for c in english["chunks"]:
        eng_text_by_col[c["column"]] += c["text"]
    greek_base_by_col = {c: _base(t) for c, t in greek_text_by_col.items()}
    proper_names = [tuple(p) for p in manifest.data.get("proper_names", [])]
    name_results = []
    for grc, eng_name in proper_names:
        grc_cols = {c for c, t in greek_base_by_col.items() if grc in t}
        eng_cols = {c for c, t in eng_text_by_col.items() if eng_name in t}
        # English chunk boundaries sit exactly at milestones, but a sentence
        # begun late in one column is often translated as overflowing the
        # boundary; allow +/- one column of slack.
        def near(col, others):
            i = expected.index(col)
            window = set(expected[max(0, i - 1) : i + 2])
            return bool(window & others)

        only_greek = sorted(c for c in grc_cols if not near(c, eng_cols))
        only_english = sorted(c for c in eng_cols if not near(c, grc_cols))
        name_results.append(
            {
                "greek": grc,
                "english": eng_name,
                "greek_columns": len(grc_cols),
                "english_columns": len(eng_cols),
                "greek_without_english": only_greek,
                "english_without_greek": only_english,
            }
        )
    report["checks"]["proper_names"] = {
        "names": name_results,
        "ok": all(
            not n["greek_without_english"] and not n["english_without_greek"]
            for n in name_results
        ),
    }

    # --- 6. sigla / character inventory ------------------------------------
    inventory: dict[str, dict] = {}
    for seg in segments:
        for line in seg["lines"]:
            for ch in line["text"]:
                if _is_greek_letter(ch) or ch in EXPECTED_NON_GREEK:
                    continue
                entry = inventory.setdefault(
                    ch,
                    {
                        "char": ch,
                        "name": unicodedata.name(ch, "UNKNOWN"),
                        "count": 0,
                        "samples": [],
                    },
                )
                entry["count"] += 1
                if len(entry["samples"]) < 5:
                    entry["samples"].append(
                        {"ref": f"{seg['column']}{line['n']}", "text": line["text"][:80]}
                    )
    report["checks"]["sigla"] = {
        "characters": sorted(inventory.values(), key=lambda e: -e["count"]),
        "ok": True,  # informational
    }

    report["ok"] = all(c.get("ok") for c in report["checks"].values())
    return report


def _to_markdown(report: dict) -> str:
    c = report["checks"]
    lines = ["# Stage 2 validation report", ""]
    lines.append(f"Overall: {'PASS' if report['ok'] else 'FAIL'}")
    cols = c["columns"]
    lines += [
        "",
        "## Columns",
        f"- {cols['found']}/{cols['expected']} columns, monotonic: {cols['monotonic']}",
        f"- missing: {cols['missing'] or 'none'}; extra: {cols['extra'] or 'none'}",
        "",
        "## Line gaps",
        f"- {len(c['line_gaps']['gaps'])} gaps, "
        f"{len(c['line_gaps']['unexpected'])} unexpected",
    ]
    for g in c["line_gaps"]["gaps"]:
        marker = "expected (book boundary)" if g["expected"] else "**UNEXPECTED**"
        lines.append(
            f"  - {g['column']}: {g['after_line']} -> {g['next_line']} ({marker})"
        )
    if "section_order" in c:
        so = c["section_order"]
        lines += [
            "",
            "## Section order (observed scheme)",
            f"- strictly increasing: {so['strictly_increasing']}; "
            f"{len(so['gaps'])} section gaps (info)",
        ]
        for g in so["gaps"]:
            tag = "declared" if g["expected"] else "gap"
            lines.append(f"  - {g['after']} -> {g['next']} ({tag})")
    if "section_spine" in c:
        ss = c["section_spine"]
        lines += [
            "",
            "## Section spine baseline",
            f"- count: expected {ss['expected']['count']}, got {ss['got']['count']}; "
            f"sha256: expected {ss['expected']['sha256']}, got {ss['got']['sha256']}",
            f"- span: {ss['first_column']['got']}..{ss['last_column']['got']} "
            f"(expected {ss['first_column']['expected']}..{ss['last_column']['expected']})",
        ]
        if ss["first_diverging_token"]:
            lines.append(f"- first diverging token: {ss['first_diverging_token']}")
    if "book_partition" in c:
        bp = c["book_partition"]
        lines += [
            "",
            "## Book partition (section scheme)",
            f"- {bp['books']} books, ordered & non-overlapping: "
            f"{bp['ordered_non_overlapping']}",
            f"- sections outside any book: "
            f"{bp['sections_outside_any_book'] or 'none'}",
            f"- sections in multiple books: "
            f"{bp['sections_in_multiple_books'] or 'none'}",
        ]
    a = c["alignment"]
    lines += [
        "",
        "## Alignment",
        f"- {a['pairs']} pairs; unmatched segments: {a['unmatched_segments'] or 'none'}; "
        f"english-only: {a['english_only'] or 'none'}",
        f"- continuation-covered: {a.get('covered_ids') or 'none'}",
    ]
    if "attachment_loss" in c:
        al = c["attachment_loss"]
        lines += [
            "",
            "## English attachment loss",
            f"- unresolved {al['unresolved'] if al['unresolved'] is not None else 'unavailable'}; "
            f"maximum {al['max_unresolved']}; attribution differences "
            f"{al['attribution_differences'] if al['attribution_differences'] is not None else 'unavailable'}",
        ]
        if al["error"]:
            lines.append(f"- **FAIL:** {al['error']}")
    for key, heading in (
        ("turn_text_length_ratio", "## Turn-text length-ratio outliers"),
        ("turn_text_turn_shift", "## Turn-text speaker shifts"),
    ):
        if key not in c:
            continue
        tm = c[key]
        lines += [
            "",
            heading,
            f"- rate {tm['rate'] if tm['rate'] is not None else 'unavailable'}; "
            f"maximum {tm['max_rate']}; count {tm['count'] if tm['count'] is not None else 'unavailable'}",
        ]
        if tm["error"]:
            lines.append(f"- **FAIL:** {tm['error']}")
    if "turn_text_residual_unassigned" in c:
        ru = c["turn_text_residual_unassigned"]
        lines += [
            "",
            "## Turn-text residual English left unassigned",
            f"- count {ru['count'] if ru['count'] is not None else 'unavailable'}; "
            f"maximum {ru['max_count']}",
        ]
        if ru["error"]:
            lines.append(f"- **FAIL:** {ru['error']}")
    if "turn_text_head_unassigned" in c:
        hu = c["turn_text_head_unassigned"]
        lines += [
            "",
            "## Turn-text opening English dropped as front matter",
            f"- count {hu['count'] if hu['count'] is not None else 'unavailable'}; "
            f"declared {hu.get('declared')}",
        ]
        if hu["error"]:
            lines.append(f"- **FAIL:** {hu['error']}")
    for key, check in c.items():
        if not key.startswith("turn_text_") or key in {
            "turn_text_length_ratio",
            "turn_text_turn_shift",
            "turn_text_residual_unassigned",
            "turn_text_head_unassigned",
            "turn_text_pairing_floor",
            "turn_text_strict_coverage",
        }:
            continue
        if not isinstance(check, dict):
            continue
        lines += ["", f"## {key.replace('_', ' ').strip()}"]
        if check.get("warn"):
            lines.append(f"- **WARN:** {check['error']}")
        elif check.get("error"):
            lines.append(f"- **FAIL:** {check['error']}")
        elif check.get("ok") is True:
            lines.append("- ok")
    lines += [
        "",
        "## Length ratios (english chars / greek chars)",
        f"- median {c['length_ratio']['median']}, robust sd(log) "
        f"{c['length_ratio']['robust_sd']}, "
        f"gate {'ENFORCED' if c['length_ratio']['enforced'] else 'informational'} "
        f"at |robust z| > {c['length_ratio']['max_robust_z']}"
        + (f", exempt {c['length_ratio']['exempt']}" if c['length_ratio']['exempt'] else ""),
    ]
    fails = c["length_ratio"].get("failures", [])
    if fails:
        lines.append(f"- **{len(fails)} FAILING chapter(s)** (extraction damage):")
        for o in fails:
            lines.append(
                f"  - **{o['column']}**: ratio {o['ratio']} (robust z {o['robust_z']}; "
                f"grc {o['greek_chars']}, eng {o['english_chars']})"
            )
    lines.append(f"- {len(c['length_ratio']['outliers'])} outlier(s) beyond 3.5 robust SD:")
    for o in c["length_ratio"]["outliers"][:15]:
        lines.append(
            f"  - {o['column']}: ratio {o['ratio']} (robust z {o['robust_z']}; "
            f"grc {o['greek_chars']}, eng {o['english_chars']})"
        )
    lines += ["", "## Proper names"]
    for n in c["proper_names"]["names"]:
        status = (
            "ok"
            if not n["greek_without_english"] and not n["english_without_greek"]
            else f"grc-only {n['greek_without_english']} eng-only {n['english_without_greek']}"
        )
        lines.append(
            f"- {n['greek']} / {n['english']}: grc in {n['greek_columns']} cols, "
            f"eng in {n['english_columns']} cols — {status}"
        )
    lines += ["", "## Non-Greek character inventory"]
    for e in c["sigla"]["characters"]:
        sample = e["samples"][0]["ref"] if e["samples"] else ""
        lines.append(
            f"- U+{ord(e['char']):04X} {e['char']!r} {e['name']} x{e['count']} "
            f"(e.g. {sample})"
        )
    return "\n".join(lines) + "\n"


def run(manifest: Manifest) -> Path:
    stage1 = BUILD_DIR / "stage1"
    # Per-language spine filename (shared with stage3/stage7 via the same
    # mapping — see stage3_tokenize._SPINE_FILENAMES's doc).
    spine_file = _SPINE_FILENAMES[manifest.language]
    spine = json.loads((stage1 / spine_file).read_text(encoding="utf-8"))
    # The English side may not be built yet (a stephanus work whose Stephanus TEI
    # walker runs as a separate pass). Validate the Greek spine alone in that case.
    eng_path = stage1 / "english_chunks.json"
    align_path = stage1 / "alignment.json"
    english = (json.loads(eng_path.read_text(encoding="utf-8"))
               if eng_path.exists() else {"chunks": []})
    alignment = (json.loads(align_path.read_text(encoding="utf-8"))
                 if align_path.exists() else {"pairs": [], "english_only": []})
    report = validate(manifest, spine, english, alignment)
    out_dir = BUILD_DIR / "stage2"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "validation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    md_path = out_dir / "validation_report.md"
    md_path.write_text(_to_markdown(report), encoding="utf-8")
    return md_path
