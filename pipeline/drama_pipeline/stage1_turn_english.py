"""Build turn-aligned English for speaker-labelled prose without line numbers.

Gutenberg-style text (Athenian Society 1912; Lindsay 1925) is parsed into
speeches, then paired to the Greek spine's speaker sequence by LCS over
canonical names (``turns._lcs_pairs`` + equal-length gap zip). Residual
English is grouped onto the preceding paired segment so no speech is dropped.
A Greek segment with no English gets no chunk — stage2 sees it unmatched.
"""

from __future__ import annotations

import re
from pathlib import Path

from .config import BUILD_DIR, SOURCES_DIR, Manifest
from .stage1_common import collapse_ws, write_json
from .stage1_english import build_alignment
from . import turns as turns_mod


_DRAMATIS_HEADS = ("DRAMATIS PERSONAE", "The Persons of the drama.")
_SPEAKER_LINE = re.compile(
    r"^(?P<name>[A-ZÀ-Þ][A-ZÀ-Þ0-9'’\-]*(?:[ ,]+(?:AND[ ,]+)?[A-ZÀ-Þ][A-ZÀ-Þ0-9'’\-]*)*)"
    r"(?:\[(?P<fn1>\d+)\])?"
    r"(?:\s+(?P<stage>\([^)]*\)))?"
    r"(?:\[(?P<fn2>\d+)\])?"
    r"\.\s*"
    r"(?:\[(?P<fn3>\d+)\])?\s*"
    r"(?P<rest>\S.*)$"
)
_LINDSAY_SPEAKER = re.compile(
    r"^(?:[A-Z][A-Z0-9'’\-]*|[0-9]+(?:ST|ND|RD|TH))"
    r"(?:\s+(?:[A-Z][A-Z0-9'’\-]*|[0-9]+(?:ST|ND|RD|TH)))*$"
)
_NOTE_START = re.compile(r"^\[(\d+)\]\s*(.*)$")
_FN_MARK = re.compile(r"\[(\d+)\]")
_PG_END = re.compile(r"^\*\*\*\s*END OF|End of the Project Gutenberg")


def _sanitize_note_raw(raw: str) -> str:
    """Footnote marker labels must not contain ``-`` (reader regex is ``\\w``)."""
    return raw.replace("-", "_")


def _canonical_english(printed: str, aliases: dict[str, str]) -> str | None:
    if not printed:
        return None
    if printed in aliases:
        return aliases[printed]
    return printed


class _SiglaResolver:
    """Greek label -> canonical display, resolved EXACTLY as stage7 does
    (`_norm_siglum` folds the three Greek-numeral prime codepoints, brackets
    and the trailing dot; `speakers.overrides` re-assign an abbreviation from a
    printed ref onward). The builder must agree with stage7 or the English
    names it pairs against are not the roster the reader colours by (P3,
    2026-09-07: `ΟΙ. Αʹ` with U+0374 missed a map key typed with U+02B9 and
    the slaves of Knights fell out of the roster)."""

    def __init__(self, manifest: Manifest):
        from . import stage7_emit as s7
        speakers = manifest.data.get("speakers") or {}
        sigla = speakers.get("sigla") or {}
        self.sigla_norm = {s7._norm_siglum(k): v for k, v in sigla.items()}
        self.overrides = s7._load_speaker_overrides(manifest)
        self._display = s7._play_line_display

    @classmethod
    def from_map(cls, sigla: dict) -> "_SiglaResolver":
        """A resolver over a bare sigla map (tests, callers without a manifest)."""
        from . import stage7_emit as s7
        obj = cls.__new__(cls)
        obj.sigla_norm = {s7._norm_siglum(k): v for k, v in (sigla or {}).items()}
        obj.overrides = []
        obj._display = s7._play_line_display
        return obj

    def resolve(self, label: str, ref: str | None) -> tuple[str | None, bool]:
        return self._display(label, self.sigla_norm, self.overrides, ref)


def _event_ref(segment: dict, event: dict) -> str | None:
    n = event.get("line")
    for line in segment.get("lines") or segment.get("greek") or []:
        if isinstance(line, dict) and line.get("n") == n:
            return line.get("ref")
    return None


def _speaker_report(
    spine: dict, sigla: dict, english_canonical: list[str], english_printed: list[str]
) -> dict:
    if not isinstance(sigla, _SiglaResolver):
        sigla = _SiglaResolver.from_map(sigla or {})
    greek_roster: list[str] = []
    seen: set[str] = set()
    for segment in spine["segments"]:
        for event in segment.get("speakers", []):
            display, mapped = sigla.resolve(event["label"], _event_ref(segment, event))
            if mapped and display is not None and display not in seen:
                seen.add(display)
                greek_roster.append(display)
    eng_set = set(english_canonical)
    greek_set = set(greek_roster)
    return {
        "english_displays": english_printed,
        "english_canonical": english_canonical,
        "greek_roster": greek_roster,
        "only_in_english": sorted(eng_set - greek_set),
        "only_in_greek": sorted(greek_set - eng_set),
        "matches": eng_set <= greek_set,
    }


def _is_star_rule(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    compact = s.replace(" ", "").replace("\t", "")
    return compact.startswith("*****") or (
        s.count("*") >= 3 and all(ch in "* \t" for ch in s)
    )


def _is_play_end(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if _PG_END.match(s) or s.startswith("FINIS") or s in ("Footnotes:", "FOOTNOTES:"):
        return True
    return False


def _star_ends_play(lines: list[str], i: int) -> bool:
    for j in range(i + 1, min(len(lines), i + 8)):
        s = lines[j].strip()
        if not s:
            continue
        return s.startswith("FINIS") or s in ("Footnotes:", "FOOTNOTES:") or s == "INTRODUCTION"
    return False


def _dramatis_index_after(lines: list[str], title_i: int, window: int = 20) -> int | None:
    for j in range(title_i + 1, min(len(lines), title_i + 1 + window)):
        s = lines[j].strip()
        if s in _DRAMATIS_HEADS or s.startswith("The Persons of the drama"):
            return j
        if s == "INTRODUCTION" or _SPEAKER_LINE.match(lines[j]):
            return None
    return None


def _locate_title(lines: list[str], title: str) -> int:
    hits = [i for i, line in enumerate(lines) if line.strip() == title]
    if not hits:
        raise ValueError(f"play title {title!r} not found")
    with_dp = [i for i in hits if _dramatis_index_after(lines, i) is not None]
    return with_dp[-1] if with_dp else hits[-1]


def _lindsay_speaker(line: str) -> str | None:
    s = line.strip().rstrip(".")
    if not s or s in _DRAMATIS_HEADS or s.startswith("The Persons of the drama"):
        return None
    if s in {"INTRODUCTION", "INDEX", "CONTENTS"} or s.startswith("THE "):
        return None
    if not _LINDSAY_SPEAKER.fullmatch(s):
        return None
    return s


def _looks_like_speech_body(s: str) -> bool:
    """Verse/prose, not a dramatis-personae stub ('Stratyllis, etc.')."""
    if not s or s.startswith("_") or s.startswith("SCENE"):
        return False
    words = s.split()
    return (len(words) >= 5 or len(s) >= 40) and any(ch.islower() for ch in s)


def _body_start(lines: list[str], title_i: int, lindsay: bool) -> int:
    dp = _dramatis_index_after(lines, title_i)
    i = (dp + 1) if dp is not None else title_i + 1
    while i < len(lines):
        raw = lines[i]
        if lindsay:
            name = _lindsay_speaker(raw)
            if name:
                nxt = next(
                    (lines[j].strip() for j in range(i + 1, len(lines)) if lines[j].strip()),
                    "",
                )
                if nxt and _lindsay_speaker(nxt) is None and _looks_like_speech_body(nxt):
                    return i
        elif _SPEAKER_LINE.match(raw):
            return i
        if _is_play_end(raw) or _is_gutenberg_end_line(raw):
            break
        i += 1
    raise ValueError("no speeches found after play title")


def _is_gutenberg_end_line(line: str) -> bool:
    return bool(_PG_END.match(line.strip()))


def _join_parts(parts: list[str]) -> str:
    return collapse_ws(" ".join(p for p in parts if p)).strip()


def _parse_notes(lines: list[str], from_i: int, title: str) -> dict[str, str]:
    notes: dict[str, str] = {}
    i = from_i
    while i < len(lines):
        s = lines[i].strip()
        if s in ("Footnotes:", "FOOTNOTES:"):
            i += 1
            break
        if _is_gutenberg_end_line(lines[i]) or s == "INTRODUCTION":
            return notes
        i += 1
    else:
        return notes

    current: str | None = None
    buf: list[str] = []

    def flush() -> None:
        if current is not None:
            notes[current] = collapse_ws(" ".join(buf)).strip()

    while i < len(lines):
        s = lines[i].strip()
        if (
            s in ("INTRODUCTION", "DRAMATIS PERSONAE")
            or s.startswith("The Persons of the drama")
            or s.startswith("FINIS")
            or s == title
            or _is_gutenberg_end_line(lines[i])
        ):
            break
        m = _NOTE_START.match(s)
        if m:
            flush()
            current = m.group(1)
            buf = [m.group(2)]
        elif current is not None and s and not _is_star_rule(s):
            buf.append(s)
        i += 1
    flush()
    return notes


def _parse_as_speeches(lines: list[str], start: int) -> tuple[list[dict], int]:
    speeches: list[dict] = []
    parts: list[str] = []
    speaker = ""
    i = start
    end_i = len(lines)

    def flush() -> None:
        text = _join_parts(parts)
        if speaker and text:
            speeches.append({"speaker_printed": speaker, "text": text})

    while i < len(lines):
        raw = lines[i]
        s = raw.strip()
        if _is_star_rule(s):
            if _star_ends_play(lines, i):
                end_i = i
                break
            i += 1
            continue
        if _is_play_end(s) or _is_gutenberg_end_line(raw):
            end_i = i
            break
        m = _SPEAKER_LINE.match(raw)
        if m:
            flush()
            speaker = m.group("name").strip()
            parts = []
            for mark in (m.group("fn1"), m.group("fn2"), m.group("fn3")):
                if mark:
                    parts.append(f"[{mark}]")
            if m.group("stage"):
                parts.append(m.group("stage"))
            parts.append(m.group("rest"))
        elif speaker:
            if s:
                parts.append(s)
        i += 1
    flush()
    return speeches, end_i


def _parse_lindsay_speeches(lines: list[str], start: int) -> tuple[list[dict], int]:
    speeches: list[dict] = []
    parts: list[str] = []
    speaker = ""
    i = start
    end_i = len(lines)

    def flush() -> None:
        text = _join_parts(parts)
        if speaker and text:
            speeches.append({"speaker_printed": speaker, "text": text})

    while i < len(lines):
        raw = lines[i]
        s = raw.strip()
        if _is_star_rule(s):
            if _star_ends_play(lines, i):
                end_i = i
                break
            i += 1
            continue
        if _is_play_end(s) or _is_gutenberg_end_line(raw):
            end_i = i
            break
        name = _lindsay_speaker(raw)
        if name and (s.endswith(".") or raw.strip() == name or raw.strip() == name + "."):
            # Own-line speaker: the line is only the name (optional period).
            only_name = raw.strip() in {name, name + "."}
            if only_name:
                flush()
                speaker = name
                parts = []
                i += 1
                continue
        if speaker and s:
            parts.append(s)
        i += 1
    flush()
    return speeches, end_i


def parse_play_speeches(text: str, title: str) -> tuple[list[dict], dict[str, str]]:
    """Split one Gutenberg play into ``{speaker_printed, text}`` speeches + notes."""
    lines = text.splitlines()
    title_i = _locate_title(lines, title)
    dp = _dramatis_index_after(lines, title_i)
    dp_line = lines[dp].strip() if dp is not None else ""
    lindsay = dp_line.startswith("The Persons of the drama")
    start = _body_start(lines, title_i, lindsay)
    if lindsay:
        speeches, end_i = _parse_lindsay_speeches(lines, start)
    else:
        speeches, end_i = _parse_as_speeches(lines, start)
    notes = _parse_notes(lines, end_i, title)
    return speeches, notes


def _rewrite_footnotes(
    text: str,
    notes_by_n: dict[str, str],
    footnotes: dict[str, str],
    seq: int,
    *,
    enabled: bool,
) -> tuple[str, int]:
    if not enabled:
        return text, seq

    def repl(match: re.Match[str]) -> str:
        nonlocal seq
        seq += 1
        raw = _sanitize_note_raw(match.group(1))
        label = f"{seq}.{raw}"
        note = notes_by_n.get(match.group(1), "")
        if note:
            footnotes[label] = note
        return f"[^{label}]"

    return _FN_MARK.sub(repl, text), seq


def _pair_turns(
    greek_names: list[str | None], english_names: list[str | None]
) -> list[tuple[int, int]]:
    """Anchors via LCS of named turns, then zip equal-length name-agreeing gaps."""
    g_named = [i for i, name in enumerate(greek_names) if name is not None]
    e_named = [j for j, name in enumerate(english_names) if name is not None]
    anchors = [
        (g_named[x], e_named[y])
        for x, y in turns_mod._lcs_pairs(
            [greek_names[i] for i in g_named],
            [english_names[j] for j in e_named],
        )
    ]
    pairs = list(anchors)
    bounds = [(-1, -1)] + anchors + [(len(greek_names), len(english_names))]
    for (agi, aej), (bgi, bej) in zip(bounds, bounds[1:]):
        sub_g = list(range(agi + 1, bgi))
        sub_e = list(range(aej + 1, bej))
        if (
            sub_g
            and sub_e
            and len(sub_g) == len(sub_e)
            and all(
                turns_mod._names_match(greek_names[i], english_names[j])
                for i, j in zip(sub_g, sub_e)
            )
        ):
            pairs.extend(zip(sub_g, sub_e))
    pairs.sort()
    out: list[tuple[int, int]] = []
    last_e = -1
    for gi, ej in pairs:
        if ej > last_e:
            out.append((gi, ej))
            last_e = ej
    return out


def _greek_segment_name(segment: dict, sigla: dict) -> str | None:
    events = segment.get("speakers") or []
    if not events:
        return None
    name, _mapped = sigla.resolve(events[0].get("label") or "", _event_ref(segment, events[0]))
    return name


def _assign_speeches(
    n_greek: int, pairs: list[tuple[int, int]], n_english: int
) -> tuple[dict[int, list[int]], int]:
    """Map each English speech onto a Greek segment. Residuals → preceding pair."""
    assigned: dict[int, list[int]] = {gi: [] for gi in range(n_greek)}
    paired_e = {ej: gi for gi, ej in pairs}
    last_gi: int | None = None
    first_gi = pairs[0][0] if pairs else (0 if n_greek else None)
    residual = 0
    for ej in range(n_english):
        if ej in paired_e:
            gi = paired_e[ej]
            assigned[gi].append(ej)
            last_gi = gi
            continue
        gi = last_gi if last_gi is not None else first_gi
        if gi is None:
            continue
        assigned[gi].append(ej)
        residual += 1
    return assigned, residual


def parse_translation(
    path: Path,
    spine: dict,
    *,
    work_id: str,
    translation_id: str,
    play: str,
    sigla: dict | None = None,
    english_aliases: dict[str, str] | None = None,
    footnotes_enabled: bool = True,
) -> tuple[dict, dict[str, str], dict]:
    """Parse one turn-text source and cut it on the Greek segments."""
    text = path.read_text(encoding="utf-8")
    if not isinstance(sigla, _SiglaResolver):
        sigla = _SiglaResolver.from_map(sigla or {})
    aliases = english_aliases or {}
    speeches, notes_by_n = parse_play_speeches(text, play)

    footnotes: dict[str, str] = {}
    seq = 0
    english_canonical: list[str] = []
    english_printed: list[str] = []
    display_seen: set[str] = set()
    e_names: list[str | None] = []
    for speech in speeches:
        printed = speech["speaker_printed"]
        canonical = _canonical_english(printed, aliases)
        speech["canonical"] = canonical
        rewritten, seq = _rewrite_footnotes(
            speech["text"], notes_by_n, footnotes, seq, enabled=footnotes_enabled
        )
        speech["text"] = rewritten
        e_names.append(canonical)
        if printed and printed not in display_seen:
            display_seen.add(printed)
            english_printed.append(printed)
            if canonical:
                english_canonical.append(canonical)

    segments: list[dict] = list(spine["segments"])
    g_names = [_greek_segment_name(seg, sigla) for seg in segments]
    pairs = _pair_turns(g_names, e_names)
    assigned, residual_grouped = _assign_speeches(len(segments), pairs, len(speeches))

    chunks: list[dict] = []
    for gi, segment in enumerate(segments):
        ejs = assigned.get(gi) or []
        if not ejs:
            continue
        texts: list[str] = []
        turns: list[dict] = []
        for ej in ejs:
            speech = speeches[ej]
            piece = speech["text"]
            if not piece:
                continue
            offset = len("\n\n".join(texts) + ("\n\n" if texts else ""))
            printed = speech["speaker_printed"]
            if printed:
                turns.append(
                    {
                        "offset": offset,
                        "speaker": speech["canonical"] or printed,
                        "display": printed,
                    }
                )
            texts.append(piece)
        if not texts:
            continue
        chunks.append(
            {
                "id": segment["id"],
                "book": segment["book"],
                "column": segment["column"],
                "text": "\n\n".join(texts),
                "notes": [],
                "markers": [],
                "bekker": [],
                "turns": turns,
                "approximate": True,
            }
        )

    chunk_ids = {chunk["id"] for chunk in chunks}
    greek_unpaired = [seg["id"] for seg in segments if seg["id"] not in chunk_ids]
    greek_named = sum(1 for name in g_names if name is not None)
    paired_named = sum(1 for gi, _ej in pairs if g_names[gi] is not None)
    total_segments = len(segments)
    english = {
        "work": work_id,
        "source": path.name,
        "translation": translation_id,
        "chunks": chunks,
        "chapters": [],
    }
    report = {
        "work": work_id,
        "translation": translation_id,
        "speeches_parsed": len(speeches),
        "paired": len(pairs),
        "residual_grouped": residual_grouped,
        "greek_unpaired": len(greek_unpaired),
        "greek_unpaired_ids": greek_unpaired,
        "pairing_rate": (paired_named / greek_named) if greek_named else 0.0,
        "anchor_count": 0,
        "snaps": [],
        "snap_count": 0,
        "speech_mismatches": [],
        "speech_mismatch_count": 0,
        "segments_with_chunk": len(chunks),
        "segments_total": total_segments,
        "coverage_ratio": len(chunks) / total_segments if total_segments else 0.0,
        "footnotes": len(footnotes),
        "anomalies": [],
        "speakers": _speaker_report(spine, sigla, english_canonical, english_printed),
    }
    return english, footnotes, report


def run(manifest: Manifest, spine: dict) -> tuple[Path, Path, Path]:
    primary = ((manifest.data.get("english") or {}).get("primary") or {})
    source_path = SOURCES_DIR / primary["source"]
    speakers = manifest.data.get("speakers") or {}
    sigla = _SiglaResolver(manifest)
    aliases = speakers.get("english") or {}
    play = primary.get("play")
    if not play:
        raise ValueError(f"{manifest.work_id}: english.primary.play is required for turn-text")
    english, footnotes, report = parse_translation(
        source_path,
        spine,
        work_id=manifest.work_id,
        translation_id=primary["id"],
        play=play,
        sigla=sigla,
        english_aliases=aliases,
        footnotes_enabled=bool(primary.get("footnotes", True)),
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
