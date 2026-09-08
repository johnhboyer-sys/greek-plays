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
from statistics import median

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
    r"(?P<rest>\S.*)?$"
)
_LINDSAY_SPEAKER = re.compile(
    r"^(?:[A-Z]{2,}[A-Z0-9'’\-]*|[0-9]+(?:ST|ND|RD|TH))"
    r"(?:\s+(?:[A-Z]{2,}[A-Z0-9'’\-]*|[0-9]+(?:ST|ND|RD|TH)))*$"
)
_NOTE_START = re.compile(r"^\[(\d+)\]\s*(.*)$")
_FN_MARK = re.compile(r"\[(\d+)\]")
_PG_END = re.compile(r"^\*\*\*\s*END OF|End of the Project Gutenberg")
_COMEDY_TITLES = {
    "THE ACHARNIANS",
    "THE KNIGHTS",
    "THE CLOUDS",
    "THE WASPS",
    "PEACE",
    "THE BIRDS",
    "LYSISTRATA",
    "THE THESMOPHORIAZUSAE",
    "THE FROGS",
    "THE ECCLESIAZUSAE",
    "PLUTUS",
}


def _sanitize_note_raw(raw: str) -> str:
    """Footnote marker labels must not contain ``-`` (reader regex is ``\\w``)."""
    return raw.replace("-", "_")


def _canonical_english(printed: str, aliases: dict[str, str]) -> str | None:
    if not printed:
        return None
    if printed in aliases:
        return aliases[printed]
    return printed


def _periodless_speaker(
    line: str, known_names: set[str]
) -> tuple[str, str] | None:
    """Match ``NAME text`` only when the full caps run is a declared alias."""
    words = line.split()
    first_body = next(
        (i for i, word in enumerate(words) if any(ch.islower() for ch in word)),
        None,
    )
    if first_body is None or first_body == 0:
        return None
    name = " ".join(words[:first_body])
    if name in known_names:
        return name, " ".join(words[first_body:])
    return None


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
    if _PG_END.match(s) or s.startswith("FINIS") or s.startswith("END OF VOL"):
        return True
    if s in ("Footnotes:", "FOOTNOTES:"):
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


_LINDSAY_STAGE = re.compile(r"\s+(\([^)]*\))$")


def _split_lindsay_speaker_line(line: str) -> tuple[str, str] | None:
    """Own-line Lindsay speaker: NAME, optional ``(_stage_)``, optional period.

    Only one trailing period is a speaker mark. Ellipsis (``O....``) is verse.
    """
    s = line.strip()
    if not s or s in _DRAMATIS_HEADS or s.startswith("The Persons of the drama"):
        return None
    if s in {"INTRODUCTION", "INDEX", "CONTENTS"} or s.startswith("THE "):
        return None
    if s.endswith("."):
        s = s[:-1]
    stage = ""
    staged = _LINDSAY_STAGE.search(s)
    if staged:
        stage = staged.group(1)
        s = s[: staged.start()].rstrip()
    if not s or not _LINDSAY_SPEAKER.fullmatch(s):
        return None
    return s, stage


def _lindsay_speaker(line: str) -> str | None:
    split = _split_lindsay_speaker_line(line)
    return None if split is None else split[0]


def _looks_like_speech_body(s: str) -> bool:
    """Verse/prose, not a dramatis-personae stub ('Stratyllis, etc.')."""
    if not s or s.startswith("_") or s.startswith("SCENE"):
        return False
    words = s.split()
    return (len(words) >= 5 or len(s) >= 40) and any(ch.islower() for ch in s)


def _body_start(
    lines: list[str], title_i: int, lindsay: bool, known_names: set[str]
) -> int:
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
        else:
            match = _SPEAKER_LINE.match(raw)
            if match and match.group("rest"):
                return i
        if _is_play_end(raw) or _is_gutenberg_end_line(raw):
            break
        i += 1
    raise ValueError("no speeches found after play title")


def _is_gutenberg_end_line(line: str) -> bool:
    return bool(_PG_END.match(line.strip()))


def _join_parts(parts: list[str]) -> str:
    paragraphs: list[str] = []
    buf: list[str] = []
    for part in parts:
        if part:
            buf.append(part)
        elif buf:
            paragraphs.append(collapse_ws(" ".join(buf)).strip())
            buf = []
    if buf:
        paragraphs.append(collapse_ws(" ".join(buf)).strip())
    return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)


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
            s == "INTRODUCTION"
            or s.startswith("INDEX")
            or (s in _COMEDY_TITLES and s != title)
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


def _parse_as_speeches(
    lines: list[str], start: int, known_names: set[str]
) -> tuple[list[dict], int]:
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
        periodless = None if m else _periodless_speaker(raw, known_names)
        if m or periodless:
            flush()
            speaker = m.group("name").strip() if m else periodless[0]
            parts = []
            if m:
                for mark in (m.group("fn1"), m.group("fn2"), m.group("fn3")):
                    if mark:
                        parts.append(f"[{mark}]")
                if m.group("stage"):
                    parts.append(m.group("stage"))
                if m.group("rest"):
                    parts.append(m.group("rest"))
            else:
                parts.append(periodless[1])
        elif speaker:
            if s:
                parts.append(s)
            elif parts and parts[-1] != "":
                parts.append("")
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
        split = _split_lindsay_speaker_line(raw)
        if split:
            # Own-line speaker: NAME, optional (_stage_), optional period.
            name, stage = split
            flush()
            speaker = name
            parts = [stage] if stage else []
            i += 1
            continue
        if speaker:
            if s:
                parts.append(s)
            elif parts and parts[-1] != "":
                parts.append("")
        i += 1
    flush()
    return speeches, end_i


def parse_play_speeches(
    text: str,
    title: str,
    *,
    format: str = "gutenberg",
    known_names: set[str] | None = None,
    line_fixes: dict[int | str, str] | None = None,
) -> tuple[list[dict], dict[str, str]]:
    """Split one play into ``{speaker_printed, text}`` speeches + notes.

    ``format="loeb-ocr"`` is the bench cleaner output: ``NAME. text`` lines,
    no Gutenberg footnotes block. Own-line caps names are already folded by
    ``bench_clean``.
    """
    lines = text.splitlines()
    for raw_line_no, replacement in (line_fixes or {}).items():
        line_no = int(raw_line_no)
        if line_no < 1 or line_no > len(lines):
            raise ValueError(
                f"line fix {line_no} is outside the {len(lines)}-line source"
            )
        lines[line_no - 1] = replacement
    known_names = known_names or set()
    title_i = _locate_title(lines, title)
    if format == "loeb-ocr":
        start = _body_start(lines, title_i, lindsay=False, known_names=known_names)
        speeches, _end_i = _parse_as_speeches(lines, start, known_names)
        return speeches, {}
    dp = _dramatis_index_after(lines, title_i)
    dp_line = lines[dp].strip() if dp is not None else ""
    lindsay = dp_line.startswith("The Persons of the drama")
    start = _body_start(lines, title_i, lindsay, known_names)
    if lindsay:
        speeches, end_i = _parse_lindsay_speeches(lines, start)
    else:
        speeches, end_i = _parse_as_speeches(lines, start, known_names)
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
    n_greek: int,
    pairs: list[tuple[int, int]],
    n_english: int,
    *,
    greek_names: list[str | None] | None = None,
    english_names: list[str | None] | None = None,
) -> tuple[dict[int, list[int]], int, int]:
    """Map residuals to a prior pair; gate head residue by segment-0 speaker."""
    assigned: dict[int, list[int]] = {gi: [] for gi in range(n_greek)}
    paired_e = {ej: gi for gi, ej in pairs}
    last_gi: int | None = None
    residual = 0
    head_unassigned = 0
    for ej in range(n_english):
        if ej in paired_e:
            gi = paired_e[ej]
            assigned[gi].append(ej)
            last_gi = gi
            continue
        if last_gi is None:
            head_matches = (
                n_greek > 0
                and greek_names is not None
                and english_names is not None
                and len(greek_names) > 0
                and len(english_names) > ej
                and english_names[ej] is not None
                and english_names[ej] == greek_names[0]
            )
            if head_matches:
                assigned[0].append(ej)
                residual += 1
            else:
                head_unassigned += 1
            continue
        assigned[last_gi].append(ej)
        residual += 1
    return assigned, residual, head_unassigned


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
    format: str = "gutenberg",
    line_fixes: dict[int | str, str] | None = None,
) -> tuple[dict, dict[str, str], dict]:
    """Parse one turn-text source and cut it on the Greek segments."""
    text = path.read_text(encoding="utf-8")
    if not isinstance(sigla, _SiglaResolver):
        sigla = _SiglaResolver.from_map(sigla or {})
    aliases = english_aliases or {}
    speeches, notes_by_n = parse_play_speeches(
        text,
        play,
        format=format,
        known_names=set(aliases),
        line_fixes=line_fixes,
    )

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

    speakers_report = _speaker_report(
        spine, sigla, english_canonical, english_printed
    )
    if speakers_report["only_in_english"]:
        names = ", ".join(speakers_report["only_in_english"])
        raise ValueError(f"{work_id}: unaliased English speakers in {play}: {names}")

    segments: list[dict] = list(spine["segments"])
    g_names = [_greek_segment_name(seg, sigla) for seg in segments]
    pairs = _pair_turns(g_names, e_names)
    assigned, residual_grouped, head_unassigned = _assign_speeches(
        len(segments),
        pairs,
        len(speeches),
        greek_names=g_names,
        english_names=e_names,
    )

    pair_ratios: list[tuple[int, int, float]] = []
    for gi, ej in pairs:
        greek_text = "".join(
            str(line.get("text") or "")
            for line in (segments[gi].get("lines") or segments[gi].get("greek") or [])
            if isinstance(line, dict)
        )
        if greek_text:
            pair_ratios.append((gi, ej, len(speeches[ej]["text"]) / len(greek_text)))
    median_ratio = (
        median(ratio for _gi, _ej, ratio in pair_ratios)
        if pair_ratios
        else None
    )
    speech_mismatches = []
    if median_ratio is not None:
        lower = median_ratio * 0.25
        upper = median_ratio * 4
        speech_mismatches = [
            {
                "greek_id": segments[gi]["id"],
                "english_index": ej,
                "ratio": ratio,
            }
            for gi, ej, ratio in pair_ratios
            if ratio < lower or ratio > upper
        ]

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
        "head_unassigned": head_unassigned,
        "greek_unpaired": len(greek_unpaired),
        "greek_unpaired_ids": greek_unpaired,
        "pairing_rate": (paired_named / greek_named) if greek_named else 0.0,
        "anchor_count": 0,
        "snaps": [],
        "snap_count": 0,
        "speech_mismatches": speech_mismatches,
        "speech_mismatch_count": len(speech_mismatches),
        "segments_with_chunk": len(chunks),
        "segments_total": total_segments,
        "coverage_ratio": len(chunks) / total_segments if total_segments else 0.0,
        "footnotes": len(footnotes),
        "anomalies": [],
        "speakers": speakers_report,
    }
    return english, footnotes, report


def chunks_as_overlay(english: dict) -> dict[str, list[dict]]:
    """Turn-text chunks → the overlay dict stage7 reads from ``ross_chunks.json``.

    OverlayPiece has no ``turns``; speaker names are prefixed into ``text``
    so compare mode still shows who is speaking.
    """
    out: dict[str, list[dict]] = {}
    for chunk in english.get("chunks") or []:
        text = chunk.get("text") or ""
        turns = chunk.get("turns") or []
        for turn in reversed(turns):
            name = turn.get("display") or turn.get("speaker") or ""
            if not name:
                continue
            off = int(turn.get("offset") or 0)
            off = max(0, min(off, len(text)))
            text = text[:off] + f"{name}. " + text[off:]
        out[chunk["id"]] = [
            {
                "chapter": str(chunk.get("column") or "1"),
                "text": text,
                "cont": False,
            }
        ]
    return out


def run(manifest: Manifest, spine: dict, slot: str = "primary") -> tuple[Path, Path, Path]:
    cfg = ((manifest.data.get("english") or {}).get(slot) or {})
    if not cfg:
        raise ValueError(f"{manifest.work_id}: english.{slot} is required for turn-text")
    source_path = SOURCES_DIR / cfg["source"]
    speakers = manifest.data.get("speakers") or {}
    sigla = _SiglaResolver(manifest)
    if slot == "secondary":
        aliases = speakers.get("english_secondary") or speakers.get("english") or {}
    else:
        aliases = speakers.get("english") or {}
    play = cfg.get("play")
    if not play:
        raise ValueError(f"{manifest.work_id}: english.{slot}.play is required for turn-text")
    english, footnotes, report = parse_translation(
        source_path,
        spine,
        work_id=manifest.work_id,
        translation_id=cfg["id"],
        play=play,
        sigla=sigla,
        english_aliases=aliases,
        footnotes_enabled=bool(cfg.get("footnotes", slot == "primary")),
        format=cfg.get("format") or "gutenberg",
        line_fixes=cfg.get("line_fixes") or {},
    )

    out_dir = BUILD_DIR / "stage1"
    out_dir.mkdir(parents=True, exist_ok=True)
    if slot == "secondary":
        english_path = out_dir / "ross_chunks.json"
        alignment_path = out_dir / "secondary_alignment.json"
        report_path = out_dir / "secondary_report.json"
        write_json(english_path, chunks_as_overlay(english))
        write_json(alignment_path, build_alignment(spine, english))
        write_json(report_path, report)
        return english_path, alignment_path, report_path
    english_path = out_dir / "english_chunks.json"
    alignment_path = out_dir / "alignment.json"
    report_path = out_dir / "english_report.json"
    write_json(english_path, english)
    write_json(alignment_path, build_alignment(spine, english))
    write_json(report_path, report)
    write_json(out_dir / "english_footnotes.json", footnotes)
    return english_path, alignment_path, report_path
