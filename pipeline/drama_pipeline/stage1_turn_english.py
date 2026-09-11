"""Build turn-aligned English for speaker-labelled prose without line numbers.

Gutenberg-style text (Athenian Society 1912; Lindsay 1925) is parsed into
speeches, then paired to the Greek spine's speaker EVENTS — one slot per
antilabe share, not one per segment (P3.4, ``_greek_event_slots``) — by LCS
over canonical names (``turns._lcs_pairs`` + equal-length gap zip). A packed
segment therefore takes one clean pair per share, and its chunk is assembled
from the pieces its shares won — in share order where that agrees with the
English, in English order where the two cross. Residual English is never
dropped: it parks on the nearest segment between the surrounding pairs whose
event set contains its speaker (``residual_grouped``), and otherwise on the
cursor with a per-turn ``speakerMismatch`` (``residual_flagged``) — shown,
flagged when the editions disagree. ``residual_unassigned`` is left for a
speech with no segment to reach at all (stage2 gates it at 0, allowance
``english.max_residual_unassigned``).
A Greek segment with no English gets no chunk — stage2 sees it unmatched.

The report carries two independent quality numbers: ``length_ratio_outliers``
(English/Greek character dispersion, a damage signal) and ``turn_shifts``
(pairs whose English speech is not at the same position in its own same-name
run as the Greek share it paired with — the drift signal, since names now
agree by construction). stage2 gates both. ``pairing_rate`` is per EVENT;
``segment_pairing_rate`` keeps the P3.3 per-segment figure beside it.
"""

from __future__ import annotations

import json
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
    # A speaker's full stop is followed by space or the end of the line.
    # `\.\s*` matched with zero space, so any mid-prose abbreviation became a
    # speaker: Storr philoctetes.txt:830 `O.God!` -> speaker "O" (P2g finding 7).
    r"\.(?=\s|\[|$)\s*"
    r"(?:\[(?P<fn3>\d+)\])?\s*"
    r"(?P<rest>\S.*)?$"
)
_LINDSAY_SPEAKER = re.compile(
    r"^(?:[A-Z]{2,}[A-Z0-9'’\-]*|[0-9]+(?:ST|ND|RD|TH))"
    r"(?:\s+(?:[A-Z]{2,}[A-Z0-9'’\-]*|[0-9]+(?:ST|ND|RD|TH)))*$"
)
_SINGLE_CAP = re.compile(r"[A-ZÀ-Þ]")
# Canonical name for a speech whose printed label is OCR junk: it must never
# equal a Greek roster name, and must not be None (a pairing wildcard).
_OCR_JUNK = "\x00ocr-junk"
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
    """Match ``NAME text`` only when the full caps run is a declared alias.

    The caps run ends before a single-letter capital ("I", "A", "O"): those
    open the speech, they are not part of the name.  Without this,
    ``MYRRHINÉ I could not…`` (pg8688:7539) and ``CHREMYLUS I shall be…``
    (pg8689:13352) build the names "MYRRHINÉ I" / "CHREMYLUS I", fail the
    alias test, and fold into the previous speech (P2g finding 6).  A name
    that BEGINS with a single capital ("A HERALD") keeps it.
    """
    words = line.split()
    first_body = next(
        (i for i, word in enumerate(words) if any(ch.islower() for ch in word)),
        None,
    )
    if first_body is None or first_body == 0:
        return None
    end = first_body
    for i in range(1, first_body):
        if _SINGLE_CAP.fullmatch(words[i]):
            end = i
            break
    name = " ".join(words[:end])
    if name in known_names:
        return name, " ".join(words[end:])
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


def _segment_speaker_events(
    segment: dict, sigla
) -> list[tuple[int, int, str | None, bool]]:
    """``(line, offset, resolved name, mapped)`` for a segment's speaker events.

    A play-line segment is cut only at a LINE-START speaker event, so a
    speaker change part-way through a line (an antilabe, or Seven 1005 where
    the Herald's label sits after an editorial bracket at offset 1) packs two
    or more speakers into one segment.  Every speaker decision therefore has
    to be made per printed line, not per segment (P2h).
    """
    if not isinstance(sigla, _SiglaResolver):
        sigla = _SiglaResolver.from_map(sigla or {})
    events: list[tuple[int, int, str | None, bool]] = []
    for event in segment.get("speakers") or []:
        line = event.get("line")
        if line is None:
            continue
        name, mapped = sigla.resolve(
            event.get("label") or "", _event_ref(segment, event)
        )
        events.append((int(line), int(event.get("offset") or 0), name, bool(mapped)))
    events.sort(key=lambda item: (item[0], item[1]))
    return events


def speaker_at(
    segment: dict,
    line: int,
    sigla,
    *,
    prefer: str | None = None,
    mapped_only: bool = True,
) -> str | None:
    """The speaker of ONE line of a segment: the resolved speaker of the last
    event at or before that line's start.

    Offset-aware: an antilabe line has a start speaker (the last event at or
    before offset 0) and one or more mid-line speakers.  A piece anchored at
    such a line belongs to the speaker whose share of the line the English
    ``<sp>`` names (``prefer``), falling back to the line-start speaker.

    P2i finding 7: on an A–B–A line the English ``<sp>`` that follows the B
    share is the LAST A share, so ``prefer`` matches the last event of that
    name on the line, not the first.
    """
    events = _segment_speaker_events(segment, sigla)
    if prefer is not None:
        for ln, _offset, name, mapped in reversed(events):
            if ln == line and name == prefer and (mapped or not mapped_only):
                return prefer
    start: str | None = None
    for ln, offset, name, mapped in events:
        if ln > line:
            break
        if ln < line or offset == 0:
            start = name if (mapped or not mapped_only) else None
    return start


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
    # Gutenberg marks italics with underscores ("(_to Dionysus_)", 116 such
    # stage notes in the 1912 comedies); the reader has no use for the
    # markup, so the underscores go and the words stay (John, 2026-09-09).
    return _GUTENBERG_ITALICS.sub(r"\1", "\n\n".join(paragraph for paragraph in paragraphs if paragraph))


_GUTENBERG_ITALICS = re.compile(r"_([^_\n]{1,200}?)_")


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

    ``format="verse-own-line"`` is English-only verse (Morshead): speaker
    name on its own line, verse below. Same parser as Lindsay, but the
    source has no ``The Persons of the drama.`` line to auto-detect.
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
    if format == "verse-own-line":
        # First exact title line: a later speaker can share the title
        # (Agamemnon). `_locate_title` would take the last hit.
        hits = [i for i, line in enumerate(lines) if line.strip() == title]
        if not hits:
            raise ValueError(f"play title {title!r} not found")
        title_i = hits[0]
        start = _body_start(lines, title_i, lindsay=True, known_names=known_names)
        speeches, _end_i = _parse_lindsay_speeches(lines, start)
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
    greek_names: list[str | None],
    english_names: list[str | None],
    crossed: dict[int, str | None] | None = None,
    forced: list[tuple[int, int]] | None = None,
) -> list[tuple[int, int]]:
    """Anchors via LCS of named turns, then zip equal-length name-agreeing gaps.

    ``greek_names`` is one entry per Greek speaker SHARE (P3.4,
    ``_greek_event_slots``), so a name here is a single speaker and a pair is
    exact-name. The alternative-name escape the segment-level pairing needed
    (P2h finding 9: a gap turn agreeing with any share of a packed line) is
    gone with the packing it worked around.

    Item 6 (John, 2026-09-09: a real slip is never a one-off): an equal-length
    gap whose sides are all NAMED but do not all agree is zipped too — both
    editions print the same number of speeches between the same two anchors,
    so they correspond by position, and the translator merely gave one to a
    different character (Birds 223–224: Coulon's Euelpides, the 1912 text's
    Pisthetaerus; the old rule left the Greek bare and parked the English on
    Pisthetaerus' next line).  Each disagreeing pair is recorded in
    ``crossed`` (English index -> the Greek slot's speaker) so the emitted
    turn carries the same ``speakerMismatch`` a parked residual would.  A
    gap with an unnamed slot on either side is still never zipped.

    ``forced`` are manifest pins (``english.<slot>.pins``, resolved by
    ``_resolve_pins``): (slot, speech) pairs that hold whatever the names say.
    The LCS then runs separately inside each region between them, so a pin
    re-anchors everything around it — the cure for an exchange where the
    translator swapped two characters' names and name-matching set every
    speech one late (Birds 223–226)."""

    def agrees(i: int, j: int) -> bool:
        # P3.5 finding 2: `turns._names_match` treats None as a WILDCARD, so an
        # unnamed slot (a speakerless lyric continuation) matched any named
        # English speech in an equal-length gap zip — a pair the LCS and the
        # residual walk both refuse. A pair needs two real, equal names.
        g, e = greek_names[i], english_names[j]
        return g is not None and e is not None and g == e

    pinned = sorted(forced or [])
    for (agi, aej), (bgi, bej) in zip(pinned, pinned[1:]):
        if bgi <= agi or bej <= aej:
            raise ValueError(f"pins must run forward in both texts: {(agi, aej)} then {(bgi, bej)}")
    anchors: list[tuple[int, int]] = list(pinned)
    if crossed is not None:
        for gi, ej in pinned:
            if not agrees(gi, ej):
                crossed[ej] = greek_names[gi]
    regions = [(-1, -1)] + pinned + [(len(greek_names), len(english_names))]
    for (agi, aej), (bgi, bej) in zip(regions, regions[1:]):
        g_named = [i for i in range(agi + 1, bgi) if greek_names[i] is not None]
        e_named = [j for j in range(aej + 1, bej) if english_names[j] is not None]
        anchors.extend(
            (g_named[x], e_named[y])
            for x, y in turns_mod._lcs_pairs(
                [greek_names[i] for i in g_named],
                [english_names[j] for j in e_named],
            )
        )
    anchors.sort()
    pairs = list(anchors)
    bounds = [(-1, -1)] + anchors + [(len(greek_names), len(english_names))]
    for (agi, aej), (bgi, bej) in zip(bounds, bounds[1:]):
        sub_g = list(range(agi + 1, bgi))
        sub_e = list(range(aej + 1, bej))
        if not (sub_g and sub_e and len(sub_g) == len(sub_e)):
            continue
        if all(agrees(i, j) for i, j in zip(sub_g, sub_e)):
            pairs.extend(zip(sub_g, sub_e))
        elif all(greek_names[i] is not None for i in sub_g) and all(
            english_names[j] is not None and english_names[j] != _OCR_JUNK for j in sub_e
        ):
            for i, j in zip(sub_g, sub_e):
                pairs.append((i, j))
                if crossed is not None and not agrees(i, j):
                    crossed[j] = greek_names[i]
    pairs.sort()
    out: list[tuple[int, int]] = []
    last_e = -1
    for gi, ej in pairs:
        if ej > last_e:
            out.append((gi, ej))
            last_e = ej
    return out


def _greek_segment_name(segment: dict, sigla: dict) -> str | None:
    """The segment's speaker for pairing: the speaker of its FIRST line at
    offset 0 (the line-level rule), not merely its first speaker event — a
    packed comedy segment used to pair as whichever speaker the antilabe put
    first (P2h finding 9)."""
    events = segment.get("speakers") or []
    if not events:
        return None
    lines = segment.get("lines") or segment.get("greek") or []
    first = next(
        (line.get("n") for line in lines if isinstance(line, dict) and line.get("n") is not None),
        None,
    )
    if first is None:
        return None
    return speaker_at(segment, int(first), sigla, mapped_only=False)


def _greek_event_slots(segments: list[dict], sigla) -> list[dict]:
    """One pairing slot per Greek speaker SHARE, in document order.

    P3.4: a play-line segment is cut only at a LINE-START speaker event, so an
    antilabe packs two or more speakers into ONE segment.  Pairing over
    segments therefore offers a packed segment a single slot, and the English
    speech of its second share can never pair however well it agrees — the
    P3.3 diagnosis found that shape under 45% of the unpaired English (961
    speeches with a free Greek event of their own name inside an
    already-paired segment).  One slot per share lets a packed segment take
    one clean pair per share; the slot remembers ``segment`` (and its ``line``
    / ``offset``), so the emitted chunk is still assembled per segment.

    A segment with no speaker event of its own (a lyric continuation, a
    column break) keeps ONE unnamed slot: pairing treats it as it always did
    (a name wildcard the LCS never anchors) and residual English can still
    park on it, so no segment becomes unreachable.
    """
    slots: list[dict] = []
    for gi, segment in enumerate(segments):
        events = _segment_speaker_events(segment, sigla)
        if not events:
            lines = segment.get("lines") or segment.get("greek") or []
            first = next(
                (
                    line.get("n")
                    for line in lines
                    if isinstance(line, dict) and line.get("n") is not None
                ),
                None,
            )
            slots.append(
                {"segment": gi, "line": first, "offset": 0, "name": None}
            )
            continue
        for line, offset, name, _mapped in events:
            slots.append(
                {"segment": gi, "line": line, "offset": offset, "name": name}
            )
    return slots


def _segment_speaks(segment: dict, sigla) -> set[str]:
    """Every canonical name the segment's own lines carry (primary + shares).

    The residual park window is still segment-scoped (P3.3's rule); an event
    slot inherits its segment's set, so a speech parks CLEAN on a segment
    whose event set contains its name even when the event it would agree with
    is not the slot the cursor stands on.
    """
    return {
        name
        for _ln, _off, name, _mapped in _segment_speaker_events(segment, sigla)
        if name is not None
    }


def _same_name_ordinals(names: list[str | None]) -> list[int | None]:
    """Each entry's 0-based position among the entries of the SAME name."""
    seen: dict[str, int] = {}
    out: list[int | None] = []
    for name in names:
        if name is None:
            out.append(None)
            continue
        out.append(seen.get(name, 0))
        seen[name] = seen.get(name, 0) + 1
    return out


def _assign_speeches(
    n_greek: int,
    pairs: list[tuple[int, int]],
    n_english: int,
    *,
    greek_names: list[str | None] | None = None,
    english_names: list[str | None] | None = None,
    greek_alt: list[set[str]] | None = None,
    greek_segments: list[int] | None = None,
) -> tuple[dict[int, list[int]], int, int, int, dict[int, str | None]]:
    """Map residuals onto Greek speaker slots; gate head residue by slot-0 speaker.

    P3.4: ``n_greek`` and the pair indices are EVENT slots (one per antilabe
    share); ``greek_alt[k]`` is the whole name set of slot k's segment, so the
    clean-park test below is still segment-scoped exactly as P3.3 wrote it.

    Returns ``(assigned, residual_grouped, head_unassigned,
    residual_unassigned, flagged)``, where ``flagged`` maps an English index
    to the speaker of the Greek EVENT it parked on — the per-turn
    ``speakerMismatch`` counterpart.

    P3.3 ruling: a translated speech is SHOWN, flagged when the editions
    disagree, never dropped.  So, after the LCS pairing (which only ever joins
    name-agreeing turns), an unpaired speech is placed in three steps:

    1. it parks on the nearest Greek slot, at or after the slot the last
       English went to and no later than the last share of the segment the
       next paired slot sits on (P3.6), that speaks its canonical name.  The
       window is the previous paired neighbour, the unpaired Greek slots
       between the surrounding pairs, and the next paired neighbour's whole
       line; the search runs forward from the cursor, so document order
       stays monotone.  This is the clean park (``residual_grouped``) — P2i
       finding 5's rule, widened past the single ``last_gi`` it used to test.

       P3.5 findings 4 and 8 make that walk two passes.  The first prefers a
       slot whose OWN event name is the residual's (``name == slot.name``), so
       a later dedicated same-name segment in the window is tried before the
       cursor's own packed segment swallows the speech; that pass also reaches
       BACKWARDS to the first slot of the cursor's own segment, so the second
       share of an antilabe the two editions cross (Frogs 405–406: the Greek
       gives 405 to Xanthias and 406 to Dionysus, the English speaks Dionysus
       first) parks on the share that is really its own.  Reaching a packed
       neighbour never moves document order — the two slots feed the SAME
       chunk — and the cursor never moves back.  The second pass is the P3.3
       rule unchanged: the first slot from the cursor on whose SEGMENT speaks
       the name (primary + the antilabe shares in ``greek_alt``).
    2. otherwise it parks on the cursor segment WITH a per-turn
       ``speakerMismatch {english, greek}`` (``residual_flagged``), exactly
       what the tragedies emit when Perseus' ``<sp>`` and the Greek edition
       name different speakers.  Half of a stichomythia the LCS could not
       reach is a real translated speech and must be readable; the flag says
       whose the Greek edition thinks the lines are.
    3. an unnamed residual (an unattributed continuation, and the OCR sentinel
       a bench scan gives an unreadable label) parks on the cursor unflagged,
       as before: it contradicts nobody.

    ``residual_unassigned`` is therefore reserved for a speech that has no
    Greek segment to reach at all (a spine with no segments); stage2 still
    gates it at 0.

    Head residue — English before the FIRST pair — keeps its own gate: that
    zone is dramatis-personae and front-matter leakage, not dialogue, and it
    attaches to segment 0 only when it names segment 0's speaker.
    """
    assigned: dict[int, list[int]] = {gi: [] for gi in range(n_greek)}
    paired_e = {ej: gi for gi, ej in pairs}
    alt = greek_alt or []
    names = greek_names or []
    cursor: int | None = None
    residual = 0
    head_unassigned = 0
    residual_unassigned = 0
    flagged: dict[int, str | None] = {}

    # `next_pair_gi[ej]` = the Greek SLOT of the next PAIRED English after
    # `ej`; the forward bound of the park window is widened from it to the
    # last slot of that segment below (the end of the play when no pair
    # follows).
    next_pair_gi: list[int | None] = [None] * n_english
    ahead: int | None = None
    for ej in range(n_english - 1, -1, -1):
        next_pair_gi[ej] = ahead
        if ej in paired_e:
            ahead = paired_e[ej]

    # Slot -> segment. Default: every slot its own segment, which is what a
    # caller pairing over segments (and the unit tests) means.
    seg_of = greek_segments or list(range(n_greek))
    # The first slot of each segment: the backward reach of the exact-name
    # pass (a packed neighbour, never another segment).
    seg_first: dict[int, int] = {}
    # The last slot of each segment: the forward bound is widened to it when
    # the next pair sits on an EARLIER share of a packed line, so a residual
    # named for a later share of that same line can reach its own slot
    # (P3.6 finding 1: Birds 666, Hoopoe paired, Peisthetaerus' share behind
    # the bound, parked clean on the Hoopoe slot by the segment fallback).
    seg_last: dict[int, int] = {}
    for gi in range(n_greek):
        seg_key = seg_of[gi] if gi < len(seg_of) else gi
        seg_first.setdefault(seg_key, gi)
        seg_last[seg_key] = gi

    def speaks(gi: int, name: str) -> bool:
        """The segment's own lines carry this speaker (primary or a share)."""
        primary = names[gi] if gi < len(names) else None
        # P2j finding 4: a segment with NO primary is not a wildcard — it
        # speaks nobody, so a named residual never counts as clean here.
        if name == primary:
            return True
        return name in (alt[gi] if gi < len(alt) else set())

    def is_slot(gi: int, name: str) -> bool:
        """This slot's OWN speaker event is that name (P3.5 findings 4, 8)."""
        return gi < len(names) and names[gi] == name

    for ej in range(n_english):
        if ej in paired_e:
            gi = paired_e[ej]
            assigned[gi].append(ej)
            cursor = gi if cursor is None else max(cursor, gi)
            continue
        if cursor is None:
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
        name = (
            english_names[ej]
            if english_names is not None and ej < len(english_names)
            else None
        )
        if name is None or name == _OCR_JUNK:
            assigned[cursor].append(ej)
            residual += 1
            continue
        upper = next_pair_gi[ej]
        upper = n_greek - 1 if upper is None else min(upper, n_greek - 1)
        upper = seg_last.get(seg_of[upper] if upper < len(seg_of) else upper, upper)
        # Pass 1: the slot that IS this speaker, from the head of the cursor's
        # own segment (its packed neighbours) to the forward bound.
        start = seg_first.get(seg_of[cursor] if cursor < len(seg_of) else cursor, cursor)
        target = next(
            (gi for gi in range(min(start, cursor), upper + 1) if is_slot(gi, name)),
            None,
        )
        if target is None:
            # Pass 2: the P3.3 segment-scoped fallback, forward only.
            target = next(
                (gi for gi in range(cursor, upper + 1) if speaks(gi, name)), None
            )
        if target is not None:
            assigned[target].append(ej)
            cursor = max(cursor, target)
            residual += 1
            continue
        assigned[cursor].append(ej)
        # P3.5 finding 7: the flag names the speaker of the EVENT this speech
        # parks on — the share at that (line, offset), not the segment's
        # primary — because that is the Greek the reader is standing in when
        # the turn is emitted at the park.  None when the park is a segment
        # the edition attributes to nobody.
        flagged[ej] = names[cursor] if cursor < len(names) else None
    return assigned, residual, head_unassigned, residual_unassigned, flagged


def _slot_refs(segments: list[dict], slots: list[dict]) -> list[str | None]:
    """The printed line ref of each pairing slot (None for an eventless slot)."""
    out: list[str | None] = []
    for slot in slots:
        seg = segments[slot["segment"]]
        lines = seg.get("lines") or seg.get("greek") or []
        ref = next(
            (line.get("ref") for line in lines if isinstance(line, dict) and line.get("n") == slot["line"]),
            None,
        )
        out.append(str(ref) if ref is not None else None)
    return out


def _resolve_pins(
    pins: list[dict],
    slots: list[dict],
    slot_refs: list[str | None],
    speeches: list[dict],
    work_id: str,
    notes: list[str] | None = None,
) -> list[tuple[int, int]]:
    """Manifest pins -> forced (slot, speech) pairs.

    A pin is ``{greek: "<line ref>", english: "<opening words as printed>",
    run: N}``: the English speech that opens with those words pairs with the
    Greek slot on that line (the share whose speaker is the speech's, else the
    line's first share), and the next N-1 speeches pair with the next N-1
    slots by position.  Fail loud on anything unresolvable — a stale pin
    after a source edit must not silently vanish."""
    forced: list[tuple[int, int]] = []
    used: set[int] = set()
    used_speech: set[int] = set()
    norm = _pin_norm
    normed = [norm(sp["text"]) for sp in speeches]

    def ref_num(r: str | None) -> int | None:
        m = re.match(r"(\d+)", r or "")
        return int(m.group(1)) if m else None

    def matches(words: str) -> list[int]:
        # The quoted words may run past one speech into the next (a reviewer
        # quoting "Aye, that I will. Hand over the money." across two turns):
        # a speech matches when it, joined to the speeches after it, opens
        # with the words.
        out = []
        for j in range(len(speeches)):
            cat = normed[j]
            k = j + 1
            while len(cat) < len(words) and k < len(speeches):
                cat += " " + normed[k]
                k += 1
            if cat.startswith(words):
                out.append(j)
        return out

    # Anchors for the ambiguous case below: every pin that names one speech
    # and a line with a speaker change gives a (slot, speech) point, whatever
    # order the manifest lists the pins in.
    anchors: list[tuple[int, int]] = []
    for pin in pins:
        w = norm(str(pin.get("english", "")))
        r = str(pin.get("greek", "")).strip()
        if not w or not r:
            continue
        js = matches(w)
        ks = [k for k, sr in enumerate(slot_refs) if sr == r]
        if len(js) == 1 and ks:
            # The share the main loop will force: the speaker's own, else
            # the line's first (Grok read of 481c112: ks[0] alone is one
            # slot early on an antilabe line).
            want = speeches[js[0]].get("canonical")
            anchors.append((next((k for k in ks if slots[k]["name"] == want), ks[0]), js[0]))

    for pin in pins:
        ref = str(pin.get("greek", "")).strip()
        words = norm(str(pin.get("english", "")))
        run = int(pin.get("run", 1) or 1)
        if not ref or not words:
            raise ValueError(f"{work_id}: a pin needs both greek and english: {pin!r}")
        # The quoted words may run past one speech into the next (a reviewer
        # quoting "Aye, that I will. Hand over the money." across two turns):
        # a speech matches when it, joined to the speeches after it, opens
        # with the words.
        ejs = matches(words)
        if not ejs:
            raise ValueError(f"{work_id}: pin {words!r} matches 0 speeches")
        gis = [k for k, r in enumerate(slot_refs) if r == ref]
        n = ref_num(ref)
        if not gis and n is not None:
            # The ref names a line with no speaker change on it. If the Greek
            # speech containing that line belongs to the English speech's own
            # speaker, the reviewer meant that speech: snap back to its slot.
            # If it belongs to someone else, the translation has a speech the
            # edition does not (Peace 1227, the arms-dealer's line Coulon
            # gives to Trygaeus): no pin can place it, so fail loud.
            want0 = speeches[ejs[0]].get("canonical") if len(ejs) == 1 else None
            back = [
                (n - ref_num(r), k) for k, r in enumerate(slot_refs)
                if ref_num(r) is not None and 0 < n - ref_num(r) <= 6
            ]
            if back:
                _d, _k = min(back)
                if slots[_k]["name"] == want0:
                    snapped = slot_refs[_k]
                    gis = [k for k, r in enumerate(slot_refs) if r == snapped]
                    if notes is not None:
                        notes.append(f"pin {ref} snapped back to slot {snapped}")
                else:
                    raise ValueError(
                        f"{work_id}: pin {words[:40]!r} on line {ref}: the edition has no "
                        f"speaker change there; that line is {slots[_k]['name']}'s speech "
                        f"(from {slot_refs[_k]}), not {want0}'s -- the translation divides "
                        "the passage differently, and a pin cannot place it"
                    )
        if not gis:
            raise ValueError(f"{work_id}: pin {words!r}: no Greek speaker slot on line {ref}")
        if len(ejs) > 1:
            # A short speech printed more than once ("Dicaeopolis!", Peace's
            # two "What shall we do to her?"): the occurrence nearest where
            # the neighbouring pins put the slot -- interpolated between the
            # anchors either side, one speech per slot beyond a lone anchor,
            # and the play-wide proportion only when no other pin helps
            # (Peace 1337 took the second refrain by proportion, 2026-09-09).
            before = [(g, e) for g, e in anchors if g < gis[0]]
            after = [(g, e) for g, e in anchors if g > gis[0]]
            if before and after:
                g0, e0 = max(before)
                g1, e1 = min(after)
                expect = e0 + (gis[0] - g0) * (e1 - e0) / (g1 - g0)
            elif before:
                g0, e0 = max(before)
                expect = e0 + (gis[0] - g0)
            elif after:
                g1, e1 = min(after)
                expect = e1 - (g1 - gis[0])
            else:
                expect = gis[0] * len(speeches) / max(1, len(slots))
            ej = min(ejs, key=lambda j: abs(j - expect))
            if notes is not None:
                notes.append(f"pin {ref} {words[:30]!r}: {len(ejs)} matches, took speech {ej}")
        else:
            ej = ejs[0]
        want = speeches[ej].get("canonical")
        free = [k for k in gis if k not in used] or gis
        gi = next((k for k in free if slots[k]["name"] == want), free[0])
        # Pins must keep both texts' order. One that crosses an earlier pin
        # (the translation prints the two speeches the other way round, or
        # one review contradicts another) is noted and skipped, not fatal.
        crossing = [(g, e) for g, e in forced if (g < gi) != (e < ej) and g != gi and e != ej]
        if crossing:
            if notes is not None:
                notes.append(f"pin {ref} {words[:30]!r}: crosses the pin at {crossing[0]}, skipped")
            continue
        if gi in used:
            if notes is not None:
                notes.append(f"pin {ref} {words[:30]!r}: slot already pinned, skipped")
            continue
        if ej in used_speech:
            # Two reviews pinned one English speech to two Greek lines. The
            # later pin wins: round two read the build round one produced
            # (2026-09-09), so it is the better-informed ruling. The earlier
            # pair is dropped and its slot freed.
            dropped = [(g, e) for g, e in forced if e == ej]
            forced[:] = [(g, e) for g, e in forced if e != ej]
            for g, _e in dropped:
                used.discard(g)
            if notes is not None:
                notes.append(f"pin {ref} {words[:30]!r}: replaces the earlier pin of that speech at slot(s) {[g for g, _ in dropped]}")
        if run > _RUN_SWAP_WINDOW:
            # A long run is a reviewer describing a stretch paired one late;
            # the anchor fixes the phase and the LCS carries it from there.
            # Held by position it would carry an offset past any speech the
            # translation has and the edition lacks (Grok read of Peace's
            # 27-, 33- and 44-pair runs, 2026-09-09).
            if notes is not None:
                notes.append(f"pin {ref} run {run} capped at {_RUN_SWAP_WINDOW}")
            run = _RUN_SWAP_WINDOW
        for k in range(run):
            if gi + k >= len(slots) or ej + k >= len(speeches):
                raise ValueError(f"{work_id}: pin {words!r} run {run} overruns the play")
            forced.append((gi + k, ej + k))
            used.add(gi + k)
            used_speech.add(ej + k)
    return forced


_RUN_SWAP_WINDOW = 8


def _alignment_with_covered(spine: dict, english: dict) -> dict:
    """The alignment plus the manifest's covered map (the perseus builder's
    own wrapper; imported here, not at module level, because that module
    imports this one)."""
    from .stage1_perseus_play_english import _alignment_with_coverage

    return _alignment_with_coverage(spine, english)


def _resolve_covered(covered: list[dict], segments: list[dict], work_id: str) -> dict[str, str]:
    """``english.<slot>.covered: [{greek: "777", by: "778"}]`` -> the map of
    segment id to the segment whose English holds its translation.  Refs are
    printed line refs of a segment's first line; fail loud on any other."""
    first_ref: dict[str, str] = {}
    for seg in segments:
        lines = seg.get("lines") or seg.get("greek") or []
        ref = next((str(l.get("ref")) for l in lines if isinstance(l, dict) and l.get("ref") is not None), None)
        if ref is not None:
            first_ref.setdefault(ref, seg["id"])
            # A joined lyric ref ("873-875") also answers to its first number.
            head = re.match(r"\d+", ref)
            if head:
                first_ref.setdefault(head.group(0), seg["id"])
    # Every printed ref -> the segment holding it (not only segment openers):
    # exact refs for the declared line (Grok review of fa76916: "368" must not
    # find "368a"), plus a joined ref's first number for its cover.
    containing: dict[str, str] = {}
    containing_head: dict[str, str] = {}
    for seg in segments:
        for l in seg.get("lines") or seg.get("greek") or []:
            if isinstance(l, dict) and l.get("ref") is not None:
                r = str(l["ref"])
                containing.setdefault(r, seg["id"])
                head = re.match(r"\d+", r)
                if head:
                    containing_head.setdefault(head.group(0), seg["id"])
    out: dict[str, str] = {}
    for item in covered:
        greek = str(item.get("greek", "")).strip()
        by = str(item.get("by", "")).strip()
        # A declared line that no longer OPENS a segment (the 40-line cap now
        # meets the English's own speech starts, John, 2026-09-11: Alcestis
        # 368, Seven 367) has nothing to cover: it sits inside a segment whose
        # English is its own, and stage2's strict coverage still names any
        # segment left without English. A line the play lacks is a typo.
        if greek not in first_ref and greek in containing:
            continue
        # The covering block is whichever segment holds `by`, opener or not.
        by_seg = first_ref.get(by) or containing.get(by) or containing_head.get(by)
        if greek not in first_ref or by_seg is None:
            raise ValueError(f"{work_id}: covered {item!r}: no segment opens on line {greek if greek not in first_ref else by}")
        if greek == by:
            raise ValueError(f"{work_id}: covered {item!r}: a segment cannot cover itself")
        if first_ref[greek] != by_seg:
            out[first_ref[greek]] = by_seg
    return out


def _pin_norm(t: str) -> str:
    """Pin matching ignores footnote markers, a leading stage note, and all
    punctuation: "(as Helen) \"These shores[^3.1] are" -> "these shores are"."""
    t = re.sub(r"\[\^[^\]]*\]", " ", t)
    t = re.sub(r"^\s*\([^)]*\)", " ", t)
    t = re.sub(r"[^\w\s]", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()


def _apply_splits(speeches: list[dict], splits: list[dict], work_id: str) -> list[dict]:
    """Manifest splits cut a speech the source runs together where the Greek
    changes speaker: ``{english: "<words the new speech opens with>",
    speaker: "<printed label>"}``.  The words are found in exactly one
    speech (punctuation and footnote markers between them ignored), the
    speech is cut there, and the tail becomes a speech of its own under the
    given label (aliased like any printed label).  Fail loud otherwise.

    A split whose words already open a speech needs no cut; when it carries
    ``greek``, it is returned as a pin of that speech to that line instead
    (reviewers name a split where the source already breaks, 2026-09-09)."""
    pins: list[dict] = []
    for split in splits:
        words = _pin_norm(str(split.get("english", "")))
        label = str(split.get("speaker", "")).strip()
        if not words or not label:
            raise ValueError(f"{work_id}: a split needs english and speaker: {split!r}")
        # Between the words: punctuation, quotes, and footnote markers.
        pat = re.compile(
            r"(?:\[\^[^\]]*\]|\W)*".join(re.escape(w) for w in words.split()), re.IGNORECASE
        )
        hits = [(j, m) for j, sp in enumerate(speeches) for m in [pat.search(sp["text"])] if m]
        if len(hits) != 1:
            raise ValueError(f"{work_id}: split {words!r} matches {len(hits)} speeches (need exactly 1)")
        j, m = hits[0]
        head = speeches[j]["text"][: m.start()].rstrip()
        tail = speeches[j]["text"][m.start():].strip()
        if not head:
            if split.get("greek"):
                pins.append({"greek": split["greek"], "english": split["english"], "run": 1})
                continue
            raise ValueError(f"{work_id}: split {words!r} is already the start of its speech")
        speeches[j]["text"] = head
        speeches.insert(j + 1, {"speaker_printed": label, "text": tail})
    return pins


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
    pins: list[dict] | None = None,
    splits: list[dict] | None = None,
    covered: list[dict] | None = None,
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
    if splits:
        pins = list(pins or []) + _apply_splits(speeches, splits, work_id)

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
        if format == "loeb-ocr":
            # A scanned Loeb comparison slot prints OCR junk as speaker labels
            # ("WOU", "VQL"); those speeches stay in the text UNATTRIBUTED
            # (no colour key) and are reported, rather than failing the play —
            # the bench is a comparison column, not the primary (2026-09-08).
            junk = set(speakers_report["only_in_english"])
            for speech in speeches:
                if speech["canonical"] in junk:
                    # A sentinel, NOT None: `turns._names_match` treats None as
                    # a wildcard that agrees with every Greek speaker, so the
                    # junk speech became a free pairing anchor. Blanking the
                    # printed label drops the turn, so the reader shows the
                    # speech unattributed instead of crediting "WOU" or "VQL"
                    # (P2g finding 8).
                    speech["canonical"] = _OCR_JUNK
                    speech["speaker_printed"] = ""
            e_names = [speech["canonical"] for speech in speeches]
            english_canonical[:] = [n for n in english_canonical if n not in junk]
            speakers_report["unaliased_ocr_speakers"] = sorted(junk)
            speakers_report["only_in_english"] = []
            speakers_report["matches"] = True
        else:
            raise ValueError(f"{work_id}: unaliased English speakers in {play}: {names}")

    segments: list[dict] = list(spine["segments"])
    # P3.4: the pairing runs over speaker EVENTS (one slot per antilabe share),
    # not segments. `slots[k]["segment"]` maps a slot back to the segment whose
    # chunk it feeds; `seg_names` (the old per-segment primary) survives only
    # to report `segment_pairing_rate` beside the event rate.
    slots = _greek_event_slots(segments, sigla)
    slot_names = [slot["name"] for slot in slots]
    seg_names = [_greek_segment_name(seg, sigla) for seg in segments]
    seg_speaks = [_segment_speaks(seg, sigla) for seg in segments]
    # No alt names in the pairing itself: a slot IS one share, so a pair is
    # exact-name by construction. The segment's whole name set rides into
    # `_assign_speeches` instead, where it is the clean-park test (P3.3).
    crossed: dict[int, str | None] = {}
    pin_notes: list[str] = []
    forced = _resolve_pins(pins or [], slots, _slot_refs(segments, slots), speeches, work_id, pin_notes)
    pairs = _pair_turns(slot_names, e_names, crossed=crossed, forced=forced)
    (
        assigned,
        residual_grouped,
        head_unassigned,
        residual_unassigned,
        residual_flags,
    ) = _assign_speeches(
        len(slots),
        pairs,
        len(speeches),
        greek_names=slot_names,
        english_names=e_names,
        greek_alt=[seg_speaks[slot["segment"]] for slot in slots],
        greek_segments=[slot["segment"] for slot in slots],
    )

    # Slot -> segment, then the English each SEGMENT shows: a packed segment's
    # chunk is its shares' pieces concatenated, each keeping its own turn
    # lead-in and offset.  ORDER (P3.5 finding 4): slot (line, offset) order
    # when it agrees with English order — which is every ordinary segment,
    # since pairing is monotone in both — and ENGLISH order when the two
    # cross.  A crossing is real: at Frogs 405–406 the Greek gives the first
    # line to Xanthias and the second to Dionysus while the translation speaks
    # Dionysus first, and each share still parks on its own slot (the walk's
    # exact-name pass).  Emitting slot order there would print the translation
    # backwards, so the English prose keeps its own sequence and the shares
    # inside the chunk are what disagree.
    seg_ejs: list[list[int]] = [[] for _ in segments]
    for k, slot in enumerate(slots):
        for ej in assigned.get(k) or []:
            seg_ejs[slot["segment"]].append(ej)
    for gi, ejs in enumerate(seg_ejs):
        if ejs != sorted(ejs):
            seg_ejs[gi] = sorted(ejs)

    pair_ratios: list[tuple[int, int, float]] = []
    for k, ej in pairs:
        segment = segments[slots[k]["segment"]]
        greek_text = "".join(
            str(line.get("text") or "")
            for line in (segment.get("lines") or segment.get("greek") or [])
            if isinstance(line, dict)
        )
        if greek_text:
            pair_ratios.append(
                (slots[k]["segment"], ej, len(speeches[ej]["text"]) / len(greek_text))
            )
    median_ratio = (
        median(ratio for _gi, _ej, ratio in pair_ratios)
        if pair_ratios
        else None
    )
    # P2g finding 9: this heuristic measures LENGTH DISPERSION, not speaker
    # agreement — it cannot see a same-name off-by-one. It keeps its own key
    # (`speech_mismatches` belongs to perseus-play's real speaker mismatches);
    # `turn_shifts` below is the drift check (P3.4: the same-name ordinal).
    length_ratio_outliers = []
    if median_ratio is not None:
        lower = median_ratio * 0.25
        upper = median_ratio * 4
        length_ratio_outliers = [
            {
                "greek_id": segments[gi]["id"],
                "english_index": ej,
                "ratio": ratio,
            }
            for gi, ej, ratio in pair_ratios
            if ratio < lower or ratio > upper
        ]

    # Event pairing makes the old name check vacuous — a pair joins one Greek
    # share to an English speech of the SAME canonical name by construction —
    # so P3.4 gives `turn_shift` the drift job it could not do before: besides
    # the name, compare each side's position among ITS OWN same-name run. A
    # prologue the two editions distribute differently (Birds redistributes
    # Euelpides/Peisthetaerus) pairs name-for-name at every step while the
    # English sits one Euelpides speech ahead of the Greek — nothing in P3.3
    # could see that. A non-zero ordinal delta is that drift, and it persists
    # for the rest of the play, which is exactly the damage it describes.
    g_ord = _same_name_ordinals(slot_names)
    e_ord = _same_name_ordinals(e_names)
    turn_shifts = [
        {
            "greek_id": segments[slots[k]["segment"]]["id"],
            "english_index": ej,
            "greek_speaker": slot_names[k],
            "english_speaker": e_names[ej],
            "greek_ordinal": g_ord[k],
            "english_ordinal": e_ord[ej],
        }
        for k, ej in pairs
        if slot_names[k] is not None
        and e_names[ej] is not None
        and (e_names[ej] != slot_names[k] or e_ord[ej] != g_ord[k])
    ]
    # Cumulative rate: once the two sides' same-name counts diverge (the Greek
    # splits a line between two speakers where the English has one speech),
    # every later pair of that name inherits the delta, so this reads 0.35–0.74
    # on the eleven comedies and describes structure, not misplacement.
    turn_shift_rate_cumulative = (len(turn_shifts) / len(pairs)) if pairs else 0.0
    # Gated rate (orchestrator ruling 2026-09-08): an ONSET rate, not a count
    # rate. A pair counts only where a drift BEGINS — its same-name ordinal
    # delta differs from the previous pair of that name (the first pair of a
    # name counts when its delta is non-zero); every later pair inherits the
    # offset and counts for nothing. So it measures how often the two editions
    # start disagreeing about position, which is the number that moves when a
    # prologue is paired one turn late, and it stays small (0.026–0.078 on the
    # eleven comedies) however long the play carries an offset afterwards.
    # `new_drifts` is that onset count; the gate is `new_drifts / paired`.
    last_delta: dict[str, int] = {}
    new_drifts = 0
    for k, ej in pairs:
        name = slot_names[k]
        if name is None or e_names[ej] is None or e_ord[ej] is None or g_ord[k] is None:
            continue
        # A pair whose names disagree is a declared crossing (an equal-length
        # gap zipped by position, or a pin): its ordinals belong to two
        # different names, so it opens no drift of its own (item 6, 2026-09-09).
        if e_names[ej] != name:
            continue
        delta = e_ord[ej] - g_ord[k]
        prev = last_delta.get(name)
        if (prev is None and delta != 0) or (prev is not None and delta != prev):
            new_drifts += 1
        last_delta[name] = delta
    turn_shift_rate = (new_drifts / len(pairs)) if pairs else 0.0
    turn_shift_new_drifts = new_drifts

    chunks: list[dict] = []
    for gi, segment in enumerate(segments):
        ejs = seg_ejs[gi]
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
                turn = {
                    "offset": offset,
                    "speaker": speech["canonical"] or printed,
                    "display": printed,
                }
                if ej in residual_flags or ej in crossed:
                    # P3.3: this speech is shown here because it had to be
                    # shown somewhere; the Greek edition gives these lines to
                    # somebody else, and the reader says so.  The flag is on
                    # the TURN, not the chunk — the chunk's other turns are
                    # correctly attributed (P2h finding 3).
                    turn["speakerMismatch"] = {
                        "english": speech["canonical"] or printed,
                        "greek": residual_flags.get(ej, crossed.get(ej)),
                    }
                turns.append(turn)
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

    # No chunk-level `speakerMismatch` here (perseus-play keeps one for
    # pre-P2h compatibility): a flagged residual parks on the CURSOR segment,
    # which has already taken an unflagged turn, so a turn-text chunk whose
    # every turn disagrees cannot arise. The reader reads the per-turn flag.
    chunk_ids = {chunk["id"] for chunk in chunks}
    greek_unpaired = [seg["id"] for seg in segments if seg["id"] not in chunk_ids]
    # The headline rate is now per EVENT: named Greek shares that took a pair
    # over named Greek shares. `segment_pairing_rate` keeps the P3.3 figure
    # (named segments carrying at least one pair) for comparison.
    greek_named = sum(1 for name in slot_names if name is not None)
    paired_named = sum(1 for k, _ej in pairs if slot_names[k] is not None)
    paired_segments = {slots[k]["segment"] for k, _ej in pairs}
    seg_named = sum(1 for name in seg_names if name is not None)
    seg_paired_named = sum(1 for gi in paired_segments if seg_names[gi] is not None)
    total_segments = len(segments)
    english = {
        "work": work_id,
        "source": path.name,
        "translation": translation_id,
        "chunks": chunks,
        "chapters": [],
        # Item 6 (2026-09-09): a Greek speech whose English sits inside the
        # speech attached to a neighbour, declared in the manifest; the
        # reader shows "Translated with the speech above" (stage7 reads it).
        "english_covered_by": _resolve_covered(covered or [], segments, work_id),
    }
    report = {
        "work": work_id,
        "translation": translation_id,
        "speeches_parsed": len(speeches),
        "paired": len(pairs),
        "residual_grouped": residual_grouped,
        "residual_flagged": len(residual_flags),
        "crossed_pairs": len(crossed),
        "pinned_pairs": len(forced),
        "pin_notes": pin_notes,
        "residual_unassigned": residual_unassigned,
        "head_unassigned": head_unassigned,
        "greek_unpaired": len(greek_unpaired),
        "greek_unpaired_ids": greek_unpaired,
        "pairing_rate": (paired_named / greek_named) if greek_named else 0.0,
        "greek_events": len(slots),
        "greek_events_named": greek_named,
        "segment_pairing_rate": (
            (seg_paired_named / seg_named) if seg_named else 0.0
        ),
        "anchor_count": 0,
        "snaps": [],
        "snap_count": 0,
        "length_ratio_outliers": length_ratio_outliers,
        "length_ratio_outlier_count": len(length_ratio_outliers),
        "turn_shifts": turn_shifts,
        "turn_shift_count": len(turn_shifts),
        "turn_shift_rate": turn_shift_rate,
        "turn_shift_new_drifts": turn_shift_new_drifts,
        "turn_shift_rate_cumulative": turn_shift_rate_cumulative,
        "segments_with_chunk": len(chunks),
        "segments_total": total_segments,
        "coverage_ratio": len(chunks) / total_segments if total_segments else 0.0,
        "footnotes": len(footnotes),
        "anomalies": [],
        "speakers": speakers_report,
    }
    return english, footnotes, report


# A sentence starts after . ! ? or … -- not the stop after a lone capital
# initial ("H. W.") or a title ("Mr.", "St.") -- any closing quote or bracket,
# then space or a dash; it opens with a capital, a digit, or a Greek letter
# (the reader's sentenceTicks in shared/lib/speakers.ts reads the same way).
_SENTENCE_START = re.compile(
    r"(?<![\s(][A-Z])(?<!\sMr)(?<!\sMrs)(?<!\sDr)(?<!\sSt)(?<!\sMt)"
    r"[.!?…][\"'’”»)\]]*(?:\s+|[—–]\s*)"
    r"(?=[\"'‘“«(\[]?[A-ZÀ-Þ0-9Ͱ-Ͽἀ-῿])"
)


def _spread_long_speeches(chunks: list[dict], segments: list[dict]) -> list[dict]:
    """A speech-aligned translation's English for a long Greek speech lands on
    the speech's first segment; the Greek segments that continue it (cut at
    the 40-line cap, no speaker change of their own, no chunk of their own)
    stood bare -- Morshead's whole Agamemnon parodos sat beside 40-103 and
    104-257 had nothing (John, 2026-09-11). Spread it: each continuation
    takes the share of the text proportional to its Greek lines, cut at the
    sentence start nearest that point. A continuation that no sentence start
    reaches stays empty, as before."""
    by_id = {c["id"]: c for c in chunks}
    # Each spread chunk's pieces, keyed by the chunk's own id; every other
    # chunk keeps its place in the list (Grok review of b294d29).
    pieces_of: dict[str, list[dict]] = {}
    k = 0
    while k < len(segments):
        seg = segments[k]
        chunk = by_id.get(seg["id"])
        k += 1
        if chunk is None:
            continue
        conts: list[dict] = []
        while k < len(segments) and not segments[k].get("speakers") and segments[k]["id"] not in by_id:
            conts.append(segments[k])
            k += 1
        # Offset-keyed notes or markers would have to be cut with the text;
        # a turn-text chunk carries none, so one that does is left whole.
        if not conts or chunk.get("notes") or chunk.get("markers") or chunk.get("bekker"):
            continue
        out: list[dict] = []
        text = chunk.get("text") or ""
        group = [seg, *conts]
        sizes = [max(1, len(s.get("lines") or s.get("greek") or [])) for s in group]
        total = sum(sizes)
        starts = [m.end() for m in _SENTENCE_START.finditer(text)]
        cuts: list[tuple[dict, int]] = []
        acc = prev = 0
        for i, cont in enumerate(conts):
            acc += sizes[i]
            target = len(text) * acc / total
            cand = [p for p in starts if p > prev]
            if not cand:
                break
            best = min(cand, key=lambda p: abs(p - target))
            cuts.append((cont, best))
            prev = best
        bounds = [0, *[p for _, p in cuts], len(text)]
        owners = [seg, *[c for c, _ in cuts]]
        for idx, owner in enumerate(owners):
            a, b = bounds[idx], bounds[idx + 1]
            piece = text[a:b]
            lead = len(piece) - len(piece.lstrip())
            body = piece.strip()
            if not body:
                continue
            turns = [
                {**t, "offset": max(0, int(t.get("offset") or 0) - a - lead)}
                for t in chunk.get("turns") or []
                if a <= int(t.get("offset") or 0) < b
            ]
            if idx == 0:
                out.append({**chunk, "text": body, "turns": turns})
            else:
                out.append({**chunk, "id": owner["id"], "column": owner["column"],
                            "text": body, "turns": turns, "notes": [], "markers": []})
        pieces_of[chunk["id"]] = out
    result: list[dict] = []
    for c in chunks:
        result.extend(pieces_of.get(c["id"], [c]))
    return result


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


def _aliases_for_slot(speakers: dict, slot: str, translation_id: str | None = None) -> dict:
    if slot == "secondary":
        return speakers.get("english_secondary") or speakers.get("english") or {}
    if slot == "third":
        return (
            speakers.get("english_third")
            or speakers.get("english_secondary")
            or speakers.get("english")
            or {}
        )
    if slot == "overlay" and translation_id:
        return speakers.get(f"english_{translation_id}") or speakers.get("english") or {}
    return speakers.get("english") or {}


def run(
    manifest: Manifest,
    spine: dict,
    slot: str = "primary",
    overlay_entry: dict | None = None,
) -> tuple[Path, Path, Path]:
    english_block = manifest.data.get("english") or {}
    cfg = overlay_entry if overlay_entry is not None else (english_block.get(slot) or {})
    if not cfg:
        raise ValueError(f"{manifest.work_id}: english.{slot} is required for turn-text")
    source_path = SOURCES_DIR / cfg["source"]
    speakers = manifest.data.get("speakers") or {}
    sigla = _SiglaResolver(manifest)
    aliases = _aliases_for_slot(speakers, slot, cfg.get("id"))
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
        pins=cfg.get("pins") or [],
        splits=cfg.get("splits") or [],
        covered=cfg.get("covered") or [],
    )
    # A long speech's English reaches the Greek segments that continue it
    # (John, 2026-09-11, Morshead's Agamemnon parodos).
    english["chunks"] = _spread_long_speeches(english.get("chunks") or [], spine.get("segments") or [])

    out_dir = BUILD_DIR / "stage1"
    out_dir.mkdir(parents=True, exist_ok=True)
    if slot == "secondary":
        english_path = out_dir / "ross_chunks.json"
        alignment_path = out_dir / "secondary_alignment.json"
        report_path = out_dir / "secondary_report.json"
        write_json(english_path, chunks_as_overlay(english))
        write_json(alignment_path, _alignment_with_covered(spine, english))
        write_json(report_path, report)
        return english_path, alignment_path, report_path
    if slot == "third":
        english_path = out_dir / "third_chunks.json"
        alignment_path = out_dir / "third_alignment.json"
        report_path = out_dir / "third_report.json"
        write_json(english_path, chunks_as_overlay(english))
        write_json(alignment_path, _alignment_with_covered(spine, english))
        write_json(report_path, report)
        return english_path, alignment_path, report_path
    if slot == "overlay":
        overlays_path = out_dir / "overlays.json"
        overlays = (
            json.loads(overlays_path.read_text(encoding="utf-8"))
            if overlays_path.exists()
            else {}
        )
        tid = cfg["id"]
        overlays[tid] = chunks_as_overlay(english)
        write_json(overlays_path, overlays)
        alignment_path = out_dir / f"overlay_{tid}_alignment.json"
        report_path = out_dir / f"overlay_{tid}_report.json"
        write_json(alignment_path, _alignment_with_covered(spine, english))
        write_json(report_path, report)
        return overlays_path, alignment_path, report_path
    english_path = out_dir / "english_chunks.json"
    alignment_path = out_dir / "alignment.json"
    report_path = out_dir / "english_report.json"
    write_json(english_path, english)
    write_json(alignment_path, _alignment_with_covered(spine, english))
    write_json(report_path, report)
    write_json(out_dir / "english_footnotes.json", footnotes)
    return english_path, alignment_path, report_path
