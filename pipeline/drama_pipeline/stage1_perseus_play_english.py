"""Build line-anchored Perseus English for ``play-line`` drama spines.

The TEI is parsed into speeches (``<sp>``), then into slices.  A speakerless
speech, or one that contains ``<milestone unit="para"/>``, is split at each
para milestone and at a leading em-dash so packed elders (Ag. 1348–1371)
become one slice per utterance.

P2c line-owner rule: a slice whose ``<l n>`` sits on the spine attaches to
the Greek segment that owns that printed number, even when the English
speaker differs from the Greek speaker — but only when the same English
``<sp>`` has anchors in more than one Greek segment (the translator ran
several Greek speeches together).  Each of those segments gets its own
chunk carrying the English speech's turn ``{offset:0, speaker, display}``.
An anchor absent from the spine still snaps only onto another line of the
same English speech.  A single-speech ``<sp>`` whose only ``<l n>`` sits
inside a different speaker's Greek speech still reattaches to the nearest
matching-speaker speech within ±3 lines (Cassandra/Chorus Ag. 1077).

P2e continuation coverage: a Greek segment that sits inside an English
speech's attached line span (or between a single attached anchor and the
next English owner) and has no piece of its own is marked
``english_covered_by`` pointing at the segment that holds the translator's
block.  The marker does not copy text and does not claim speaker identity.

P2f attribution difference: when that ±3 same-speaker search finds
nothing, the piece attaches to the Greek speech that prints the line
(the line owner) and the chunk is marked ``speakerMismatch``
``{english, greek}`` so the text is shown and the edition disagreement
is visible.  Translator drift (a same-speaker Greek speech within ±3)
still reattaches there without the flag.

P2g: Greek speakers resolve through ``_SiglaResolver`` (stage7's
``_norm_siglum`` + ``speakers.overrides``), continuation coverage never
crosses speakers, and the repaired attachment ticks a line the target
segment itself prints.

P2h: a segment is cut only at a LINE-START speaker event, so an antilabe
packs two or more speakers into one segment; every speaker decision is
therefore made per printed line (``_SpeechIndex.speaker_at``), never per
segment set.  The owner check, the repair search (which may target only a
line the speaker actually speaks), the tick and continuation coverage all
use it; claims are ``(segment, speaker)`` pairs.

P2i: the drift repair measures its distance against the speaker's OWN
printed lines and will not move a piece into a speech the speaker owns
less than half of, so a packed span no longer swallows a neighbour's
one-liner.  Every anchor whose printed line is on the spine attaches: when
the printed line's speaker differs from the English speaker and the repair
finds nothing, the piece stays on the speech that prints it and the TURN
carries ``speakerMismatch {english, greek}`` — showing the translation
beside the Greek it translates, marked as disputed, beats withholding it
(orchestrator ruling, 2026-09-08).  A lettered anchor (``1630b``) names its
share of an antilabe line, so Coleridge's Helen 1630–1640 reads against
Diggle's ``Θε.β`` instead of the line-start king.
"""

from __future__ import annotations

import bisect
import html
import re
from pathlib import Path

from lxml import etree

from .config import BUILD_DIR, SOURCES_DIR, Manifest
from .stage1_common import collapse_ws, local_name, write_json
from .stage1_english import build_alignment
from .stage1_turn_english import (
    _SiglaResolver,
    _event_ref,
    _segment_speaker_events,
    _speaker_report,
    speaker_at as _line_speaker,
)


_EM_DASH_SPLIT = re.compile(r"(?:(?<=\s)|^)(?=—)")
_LETTERED_ANCHOR = re.compile(r"^(\d+)[a-z]+$")
_SKIP_TAGS = frozenset({"del", "stage", "gap", "speaker"})


def _anchor_base(ref: str) -> int:
    lettered = _LETTERED_ANCHOR.fullmatch(ref)
    return int(lettered.group(1) if lettered else ref)


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


def _sanitize_note_raw(raw: str) -> str:
    """Footnote marker labels must not contain ``-`` (reader regex is ``\\w``)."""
    return raw.replace("-", "_")


class _LineText:
    def __init__(self, footnotes: dict[str, str], anomalies: list[dict]):
        self.footnotes = footnotes
        self.anomalies = anomalies
        self.note_seq = 0

    def consume_note(self, child) -> str:
        if child.get("resp") == "Smyth":
            self.note_seq += 1
            raw = collapse_ws(child.get("n") or "").strip() or f"n{self.note_seq}"
            label = f"{self.note_seq}.{_sanitize_note_raw(raw)}"
            self.footnotes[label] = _note_html(child)
            return f"[^{label}]"
        self.anomalies.append(
            {"kind": "note_skipped_non_smyth", "resp": child.get("resp")}
        )
        return ""


def _ref_line_numbers(ref: str) -> set[int]:
    """Integer line numbers covered by a printed play-line ref."""
    if ref.isdigit():
        return {int(ref)}
    if ref.startswith("post ") and ref[5:].isdigit():
        return {int(ref[5:])}
    lettered = _LETTERED_ANCHOR.fullmatch(ref)
    if lettered:
        return {int(lettered.group(1))}
    if "-" in ref:
        start, end = ref.split("-", 1)
        if start.isdigit() and end.isdigit():
            return set(range(int(start), int(end) + 1))
    return set()


class _SpeechIndex:
    """Greek segments as speeches, with the line numbers each one covers.

    Speakers resolve EXACTLY as stage7 resolves them (``_SiglaResolver`` =
    ``_norm_siglum`` + ``speakers.overrides`` by printed ref): an abbreviation
    the edition re-assigns part-way through (Helen's ``Θε.`` → Theoclymenus
    from 1165) must read as the character stage7 colours, or every line after
    the override scores a false speaker mismatch (P2g finding 2).  A segment
    may map SEVERAL speakers (Seven 1:1004 packs Ismene 1004 and the Herald
    from the antilabe at 1005), so the SET only says "this segment contains
    that speaker".  Every decision about one printed line — who owns it, what
    a repair may target, what a chunk's mismatch names — goes through
    :meth:`speaker_at`, the resolved speaker of the last event at or before
    that line (P2h findings 2, 4, 6, 7, 8).
    """

    def __init__(self, spine: dict, sigla):
        if not isinstance(sigla, _SiglaResolver):
            sigla = _SiglaResolver.from_map(sigla or {})

        self.sigla = sigla
        self.line_n: dict[str, dict[int, int]] = {}
        self.printed: dict[str, list[int]] = {}
        self.segments: list[dict] = list(spine["segments"])
        self.by_id = {seg["id"]: seg for seg in self.segments}
        self.order = {seg["id"]: i for i, seg in enumerate(self.segments)}
        self.span: dict[str, set[int]] = {}
        self.covering: dict[int, list[tuple[dict, str, int]]] = {}
        self.by_ref: dict[str, list[tuple[dict, int]]] = {}
        self.speakers_of: dict[str, set[str]] = {}
        self.valid_numbers: set[int] = set()

        for order, segment in enumerate(self.segments):
            numbers: set[int] = set()
            names: list[str] = []
            for event in segment.get("speakers") or []:
                name, mapped = sigla.resolve(
                    event.get("label") or "", _event_ref(segment, event)
                )
                if mapped and name is not None and name not in names:
                    names.append(name)
            self.speakers_of[segment["id"]] = set(names)
            line_n: dict[int, int] = {}
            for line in segment.get("lines") or []:
                ref = line.get("ref")
                if not isinstance(ref, str):
                    continue
                covered = _ref_line_numbers(ref)
                numbers.update(covered)
                self.by_ref.setdefault(ref, []).append((segment, order))
                for n in covered:
                    self.covering.setdefault(n, []).append((segment, ref, order))
                    if line.get("n") is not None:
                        line_n.setdefault(n, int(line["n"]))
            self.line_n[segment["id"]] = line_n
            self.printed[segment["id"]] = sorted(line_n)
            self.span[segment["id"]] = numbers
            self.valid_numbers.update(numbers)

        if not self.valid_numbers:
            raise ValueError("play-line English needs at least one numbered Greek ref")

    def on_spine(self, n: int) -> bool:
        return n in self.covering

    def speaker_at(
        self, segment: dict, n: int, prefer: str | None = None
    ) -> str | None:
        """The resolved speaker of PRINTED line ``n`` inside ``segment``.

        Offset-aware (see ``stage1_turn_english.speaker_at``): the line's
        start speaker is the last event at or before its offset 0, and a
        mid-line event (an antilabe) adds a second speaker to the same line.
        When the English ``<sp>`` names one of the line's speakers, the piece
        belongs to that share of the line.  ``n`` outside the segment falls
        back to the nearest line the segment does print.
        """
        mapping = self.line_n.get(segment["id"]) or {}
        if not mapping:
            return None
        line = mapping.get(n)
        if line is None:
            nearest = min(mapping, key=lambda printed: (abs(printed - n), printed))
            line = mapping[nearest]
        return _line_speaker(segment, line, self.sigla, prefer=prefer)

    def speaker_lines(self, segment: dict, speaker: str) -> list[int]:
        """The segment's printed lines that ``speaker`` actually speaks."""
        return [
            n
            for n in self.printed.get(segment["id"]) or []
            if self.speaker_at(segment, n, prefer=speaker) == speaker
        ]

    def line_shares(self, segment: dict, n: int) -> list[str | None]:
        """The shares of PRINTED line ``n``, in offset order.

        The first entry is the line's start speaker (the last event at or
        before offset 0, inherited from an earlier line when the line opens
        no speech); each further entry is one mid-line event.  A lettered
        English anchor names a share by position — Coleridge's Helen
        ``1630b`` is the second share of 1630, Diggle's ``Θε.β`` (P2i
        finding 3).  ``n`` the segment does not print has no shares.
        """
        mapping = self.line_n.get(segment["id"]) or {}
        line = mapping.get(n)
        if line is None:
            return []
        start: str | None = None
        mid: list[str | None] = []
        for ln, offset, name, mapped in _segment_speaker_events(segment, self.sigla):
            if ln > line:
                break
            resolved = name if mapped else None
            if ln < line or offset == 0:
                start = resolved
            else:
                mid.append(resolved)
        return [start] + mid

    def share_speaker(
        self, segment: dict, n: int, anchor: str, prefer: str | None = None
    ) -> str | None:
        """The Greek speaker a piece anchored at ``anchor`` belongs to.

        A share the English speaker actually speaks always wins: the Greek
        line may open with the tail of the previous speech (Alcestis 1119
        starts in Admetus's hands), so the letters need not line up with the
        shares one for one.  Only when the English speaker owns no share of
        the line does the letter decide which share the piece disagrees
        with — Coleridge's Helen ``1630b`` is the second share, Diggle's
        ``Θε.β`` (Second Servant), not the line-start king.  Only a letter
        past ``a`` names a share: a plain ``1270a`` is the spine's own
        printed ref, not a second half.
        """
        resolved = self.speaker_at(segment, n, prefer=prefer)
        if prefer is not None and resolved == prefer:
            return resolved
        lettered = _LETTERED_ANCHOR.fullmatch(anchor or "")
        if lettered is not None:
            suffix = (anchor or "")[len(lettered.group(1)) :]
            index = ord(suffix[0]) - ord("a")
            shares = self.line_shares(segment, n) if index > 0 else []
            if 0 <= index < len(shares) and shares[index] is not None:
                return shares[index]
        return resolved

    def segment_for_line(self, n: int) -> tuple[dict, str] | None:
        hits = self.covering.get(n)
        if not hits:
            return None
        # Prefer a ref that prints as this number, then document order.
        segment, ref, _order = min(
            hits,
            key=lambda item: (item[1] != str(n), item[2]),
        )
        return segment, ref

    def segment_for_anchor(self, ref: str) -> tuple[dict, str] | None:
        exact = self.by_ref.get(ref)
        if exact:
            segment, _order = min(exact, key=lambda item: item[1])
            return segment, ref
        match = _LETTERED_ANCHOR.fullmatch(ref)
        if match:
            return self.segment_for_line(int(match.group(1)))
        if ref.isdigit():
            return self.segment_for_line(int(ref))
        return None

    def closest_ref(self, segment: dict, n: int) -> str:
        best: tuple[int, int, str] | None = None
        for line in segment.get("lines") or []:
            ref = line.get("ref")
            if not isinstance(ref, str):
                continue
            numbers = _ref_line_numbers(ref)
            if not numbers:
                continue
            distance = min(abs(n - line_n) for line_n in numbers)
            candidate = (distance, 0 if ref == str(n) else 1, ref)
            if best is None or candidate < best:
                best = candidate
        return best[2] if best else str(n)

    def nearest_matching_speech(
        self,
        n: int,
        speaker: str,
        window: int = 3,
        claimed: set[tuple[str, str]] | None = None,
    ) -> tuple[dict, int] | None:
        """Nearest segment in which ``speaker`` actually SPEAKS A LINE, within
        ±window of n; returns it with the line to tick.

        A segment that merely carries the speaker's name somewhere in a packed
        antilabe span is not a target unless one of its lines is that
        speaker's (P2h finding 6: Ismene 1003 was being ticked onto the
        Herald's 22-line block).  The tick is the nearest such line, EARLIER
        on a tie, matching the earlier-speech preference (finding 8).

        P2i finding 1: the distance is measured against the speaker's OWN
        printed lines, not the candidate's whole span — a 22-line block whose
        rim the speaker happens to speak is no nearer than it really is — and
        candidates are ranked ``(distance, foreign lines, document order)``,
        so a same-speaker one-liner beats a packed span at equal distance.  A
        candidate the speaker owns less than half of is not a repair target at
        all: drift repair moves a piece to another speech of that character's,
        never into the middle of somebody else's (Seven ``1:1004``, where
        Ismene owns 1004 and the Herald 1005–1025).  That piece stays on the
        speech that prints its line, flagged (finding 2).

        ``claimed`` holds ``(segment id, speaker)`` pairs, so one speaker's
        drift repair no longer locks a whole segment against another's
        (P2h finding 4).  It blocks only a repair that MOVES the piece: a
        segment that itself prints line ``n`` is never claimed away from it.
        """
        claimed = claimed or set()
        best: tuple[int, int, int, dict, int] | None = None
        for segment in self.segments:
            sid = segment["id"]
            if speaker not in (self.speakers_of.get(sid) or set()):
                continue
            own = self.speaker_lines(segment, speaker)
            if not own:
                continue
            foreign = len(self.printed.get(sid) or []) - len(own)
            if foreign > len(own):
                continue
            distance = min(abs(n - line) for line in own)
            if distance > window:
                continue
            if distance and (sid, speaker) in claimed:
                continue
            tick = min(own, key=lambda line: (abs(n - line), line))
            # Equal distance: the earlier speech (Ag. 1204 Chorus → 1203, not 1205).
            candidate = (distance, foreign, self.order[sid], segment, tick)
            if best is None or candidate < best:
                best = candidate
        if best is None:
            return None
        return best[3], best[4]


def _is_lacuna_segment(segment: dict) -> bool:
    """Empty ``role: lacuna`` placeholder — never continuation-covered."""
    lines = segment.get("lines") or []
    return bool(lines) and all(
        line.get("role") == "lacuna" and not str(line.get("text") or "").strip()
        for line in lines
    )


def _continuation_covered_by(
    index: _SpeechIndex,
    chunks_by_id: dict[str, dict],
    jobs: list[dict],
    skip_ids: set[str] | None = None,
) -> dict[str, str]:
    """Map unmatched Greek segments to the segment that holds their English.

    An English ``<sp>`` whose attached anchors span ``[min_n, max_n]`` covers
    every Greek segment whose printed integers all lie in that span and that
    has no chunk of its own.  A single-anchor speech covers the same way out
    to the next attached English anchor when its Greek owner ends before that
    next owner's speech begins.  Lacunae, declared gaps (``skip_ids``), and
    segments that carry their own English ``<l n>`` stay unmarked.  The
    marker means "the translator's block that contains this line is attached
    at ``<id>``".

    P2g finding 4: coverage never crosses speakers.  A segment is marked only
    when its resolved speaker set intersects the covering segment's, so the
    Herald's Seven 1042/1044 can no longer be declared covered by Antigone's
    1026 block.  A cross-speaker hole is a real hole: it must be attached, or
    declared in ``english.gaps`` like any other.

    P2h finding 7: the test is the ENGLISH speech's canonical speaker, not the
    covering segment's whole speaker set — a packed covering segment would
    otherwise lend its second speaker's name to segments the translator's
    block never covers.  P2i finding 4: on the covered side the test is every
    printed LINE of the candidate, not its speaker set.
    """
    skip_ids = skip_ids or set()
    chunked = set(chunks_by_id)
    lacuna_ids = {seg["id"] for seg in index.segments if _is_lacuna_segment(seg)}
    anchor_ns = {job["n"] for job in jobs if job.get("n") is not None}
    attached_by_speech: dict[int, list[tuple[int, str]]] = {}
    speech_speaker: dict[int, str | None] = {}
    for job in jobs:
        assigned = job.get("assigned")
        n = job.get("n")
        if assigned is None or n is None:
            continue
        attached_by_speech.setdefault(job["sp_index"], []).append((n, assigned))
        speech_speaker.setdefault(job["sp_index"], job.get("canonical"))

    covered: dict[str, str] = {}

    def mark_span(
        n_i: int, n_j: int, seg_i: str, seg_j: str, cover_speaker: str | None
    ) -> None:
        if seg_i not in index.order or seg_j not in index.order:
            return
        lo, hi = (n_i, n_j) if n_i <= n_j else (n_j, n_i)
        start, end = index.order[seg_i], index.order[seg_j]
        if start > end:
            start, end = end, start
        if cover_speaker is None:
            return
        for segment in index.segments[start + 1 : end]:
            sid = segment["id"]
            if (
                sid in chunked
                or sid in skip_ids
                or sid in lacuna_ids
                or sid in covered
            ):
                continue
            # P2i finding 4: the COVERED side is per line too.  Every printed
            # line of the candidate must be the covering English speaker's;
            # a segment that hands a line to somebody else part-way through
            # is a real hole, not a continuation of this block.
            printed = index.printed.get(sid) or []
            if not printed:
                continue
            if any(
                index.speaker_at(segment, line, prefer=cover_speaker) != cover_speaker
                for line in printed
            ):
                continue
            numbers = index.span.get(sid) or set()
            if not numbers:
                continue
            if not all(lo <= n <= hi for n in numbers):
                continue
            if numbers & anchor_ns:
                continue
            covered[sid] = seg_i

    for sp_index, items in attached_by_speech.items():
        for (n_i, seg_i), (n_j, seg_j) in zip(items, items[1:]):
            mark_span(n_i, n_j, seg_i, seg_j, speech_speaker.get(sp_index))

    flat: list[tuple[int, int, str]] = []
    for sp_index in sorted(attached_by_speech):
        for n, seg_id in attached_by_speech[sp_index]:
            flat.append((sp_index, n, seg_id))
    speech_counts = {sp: len(items) for sp, items in attached_by_speech.items()}
    for i, (sp_i, n_i, seg_i) in enumerate(flat):
        if speech_counts[sp_i] != 1 or i + 1 >= len(flat):
            continue
        _sp_j, n_j, seg_j = flat[i + 1]
        owner_nums = index.span.get(seg_i) or set()
        next_nums = index.span.get(seg_j) or set()
        if not owner_nums or not next_nums:
            continue
        if max(owner_nums) >= min(next_nums):
            continue
        mark_span(n_i, n_j, seg_i, seg_j, speech_speaker.get(sp_i))

    return covered


def _alignment_with_coverage(spine: dict, english: dict) -> dict:
    """``build_alignment`` plus the parallel ``english_covered_by`` map."""
    alignment = build_alignment(spine, english)
    covered = english.get("english_covered_by") or {}
    alignment["english_covered_by"] = covered
    for pair in alignment["pairs"]:
        cover = covered.get(pair["segment"])
        if cover and pair["english"] is None:
            pair["englishCoveredBy"] = cover
    return alignment


def _canonical_english(printed: str, aliases: dict[str, str]) -> str | None:
    if not printed:
        return None
    if printed in aliases:
        return aliases[printed]
    return printed


def _has_para_milestone(speech) -> bool:
    return any(
        local_name(el) == "milestone" and el.get("unit") == "para"
        for el in speech.iter()
        if isinstance(el.tag, str)
    )


class _Slice:
    __slots__ = ("pieces",)

    def __init__(self) -> None:
        self.pieces: list[tuple[str | None, str]] = []

    def add(self, n: str | None, text: str) -> None:
        if not text:
            return
        if self.pieces and self.pieces[-1][0] == n:
            prev_n, prev = self.pieces[-1]
            self.pieces[-1] = (prev_n, prev + text)
            return
        self.pieces.append((n, text))

    @property
    def has_content(self) -> bool:
        return any(part.strip() for _n, part in self.pieces)

    def first_anchor(self) -> str | None:
        for anchor, _part in self.pieces:
            if anchor is not None:
                return anchor
        return None

    def text(self) -> str:
        return collapse_ws("".join(part for _n, part in self.pieces)).strip()


def _line_plain_text(node) -> str:
    return collapse_ws("".join(node.itertext())).strip()


def _is_speaker_label(text: str, printed: str) -> bool:
    def fold(value: str) -> str:
        return re.sub(r"[^\w\s]", "", collapse_ws(value), flags=re.UNICODE).strip().casefold()

    a, b = fold(text), fold(printed)
    return bool(a) and bool(b) and a == b


def _iter_speech_slices(
    speech,
    *,
    split: bool,
    text_parser: _LineText,
    anomalies: list[dict],
    sp_index: int,
    printed: str = "",
) -> list[_Slice]:
    slices: list[_Slice] = []
    current = _Slice()
    line_n_live = True

    def flush() -> None:
        nonlocal current, line_n_live
        if current.has_content:
            slices.append(current)
        current = _Slice()
        if split:
            line_n_live = False

    def slice_n(n: str | None) -> str | None:
        return n if (n is not None and line_n_live) else None

    def handle_text(raw: str | None, n: str | None) -> None:
        if not raw:
            return
        if not split:
            current.add(n, raw)
            return
        parts = _EM_DASH_SPLIT.split(raw)
        for i, part in enumerate(parts):
            if not part:
                continue
            if i > 0 and current.has_content:
                flush()
            current.add(slice_n(n), part)

    def walk(node, current_n: str | None = None) -> None:
        nonlocal line_n_live
        tag = local_name(node)
        if tag is None:
            return
        if tag in _SKIP_TAGS:
            if node.tail:
                handle_text(node.tail, current_n)
            return
        if tag == "note":
            marker = text_parser.consume_note(node)
            if marker:
                current.add(slice_n(current_n), marker)
            if node.tail:
                handle_text(node.tail, current_n)
            return
        if tag == "milestone" and node.get("unit") == "para" and split:
            flush()
            if node.tail:
                handle_text(node.tail, current_n)
            return
        if tag == "l":
            raw_n = node.get("n")
            content = _line_plain_text(node)
            lettered = _LETTERED_ANCHOR.fullmatch(raw_n or "")
            # Astra lane C, F8: n="0" is display-only when it repeats the
            # speaker label; any other nonempty n="0" (or n<=0) is loss.
            zero_n = raw_n == "0" or (
                bool(raw_n) and raw_n.isdigit() and int(raw_n) == 0
            )
            if zero_n:
                if content and not _is_speaker_label(content, printed):
                    anomalies.append(
                        {"kind": "zero_n_content", "sp": sp_index, "n_raw": raw_n}
                    )
                if node.tail:
                    handle_text(node.tail, current_n)
                return
            if not raw_n or (not raw_n.isdigit() and lettered is None):
                if content:
                    anomalies.append(
                        {"kind": "non_numeric_anchor", "sp": sp_index, "n_raw": raw_n}
                    )
                if node.tail:
                    handle_text(node.tail, current_n)
                return
            n = _anchor_base(raw_n)
            if n <= 0:
                if content and not _is_speaker_label(content, printed):
                    anomalies.append(
                        {"kind": "zero_n_content", "sp": sp_index, "n_raw": raw_n}
                    )
                if node.tail:
                    handle_text(node.tail, current_n)
                return
            line_n_live = True
            if node.text:
                handle_text(node.text, raw_n)
            for child in node:
                walk(child, raw_n)
            if node.tail:
                handle_text(node.tail, current_n)
            return
        if node.text:
            handle_text(node.text, current_n)
        for child in node:
            walk(child, current_n)
        if node.tail:
            handle_text(node.tail, current_n)

    walk(speech)
    flush()
    return slices


def _speakers_row(work_id: str, n: int | None, ref: str, printed: str, speaker: str | None, greek: str | None) -> dict:
    return {
        "play": work_id,
        "english_line": n,
        "greek_ref": ref,
        "english_speaker": printed or speaker or "",
        "greek_speaker": greek or "",
    }


def _resolve_slice_anchor(
    n: int,
    *,
    anchor: str,
    speaker: str | None,
    speech_anchors: list[str],
    multi_span: bool,
    index: _SpeechIndex,
    work_id: str,
    printed: str,
    claimed: set[tuple[str, str]] | None = None,
) -> dict | None:
    """Attach one English line number to a Greek segment, or return None."""
    claimed = claimed or set()
    hit = index.segment_for_anchor(anchor)
    if hit is not None:
        segment, ref = hit
        # P2h finding 2: the owner is the speaker of the PRINTED LINE, not the
        # segment's speaker set — a packed antilabe segment would otherwise
        # accept any of its speakers' English anywhere in the span.
        # P2i finding 3: a lettered anchor names its SHARE of that line.
        greek_speaker = index.share_speaker(segment, n, anchor, prefer=speaker)
        if speaker and greek_speaker is not None and speaker != greek_speaker:
            mismatch = _speakers_row(work_id, n, ref, printed, speaker, greek_speaker)
            if not multi_span:
                repaired = index.nearest_matching_speech(n, speaker, claimed=claimed)
                if repaired is not None:
                    target, tick = repaired
                    # P2g finding 10: the marker must name a line the TARGET
                    # segment prints, not the English n of the neighbour the
                    # piece was taken from.
                    target_ref = index.closest_ref(target, tick)
                    mismatch["attached_to"] = target["id"]
                    mismatch["attached_ref"] = target_ref
                    mismatch["attached_speaker"] = index.speaker_at(
                        target, tick, prefer=speaker
                    )
                    mismatch["kind"] = "speaker_repair"
                    return {
                        "attached": True,
                        "tick": tick,
                        "ref": target_ref,
                        "segment": target,
                        "snap": None,
                        "mismatch": mismatch,
                    }
                # P2f/P2i finding 2: no same-speaker Greek speech within ±3 —
                # this is an attribution difference (the two editions give the
                # line to different characters).  Attach to the speech that
                # PRINTS the line and flag the turn with the speaker of that
                # printed line, whether or not the English speaker appears
                # elsewhere in the segment: showing the translation beside the
                # Greek it translates, marked as disputed, beats withholding
                # it (orchestrator ruling, 2026-09-08).
                mismatch["attached_to"] = segment["id"]
                mismatch["attached_ref"] = ref
                mismatch["attached_speaker"] = greek_speaker
                mismatch["kind"] = "attribution_difference"
                return {
                    "attached": True,
                    "tick": n,
                    "ref": ref,
                    "segment": segment,
                    "snap": None,
                    "mismatch": mismatch,
                    "speaker_mismatch": {
                        "english": speaker,
                        "greek": greek_speaker,
                    },
                }
            # P2j finding 1: a multi-span speech (one <sp> whose anchors reach
            # several Greek speeches) disagrees with the printed line's
            # speaker exactly as a singleton does -- Seven's Herald 1030
            # owner-attaches onto Antigone's 1:1026 -- so its turn carries the
            # same flag.  Only the repair search stays withheld: a piece of a
            # spanning speech belongs beside the Greek its own anchor names.
            mismatch["attached_to"] = segment["id"]
            mismatch["attached_ref"] = ref
            mismatch["attached_speaker"] = greek_speaker
            mismatch["kind"] = "attribution_difference"
            return {
                "attached": True,
                "tick": n,
                "ref": ref,
                "segment": segment,
                "snap": None,
                "mismatch": mismatch,
                "speaker_mismatch": {
                    "english": speaker,
                    "greek": greek_speaker,
                },
            }
        else:
            mismatch = None
        return {
            "attached": True,
            "tick": n,
            "ref": ref,
            "segment": segment,
            "snap": None,
            "mismatch": mismatch,
        }

    own_hits = [
        other
        for other in speech_anchors
        if other != anchor and index.segment_for_anchor(other) is not None
    ]
    if not own_hits:
        return None
    span_numbers: set[int] = set()
    for other in own_hits:
        hit = index.segment_for_anchor(other)
        if hit is None:
            continue
        own_seg, _ref = hit
        if speaker:
            greek = index.speakers_of.get(own_seg["id"]) or set()
            if greek and speaker not in greek:
                continue
        span_numbers.update(index.span.get(own_seg["id"]) or set())
    if not span_numbers:
        return None
    snapped = _nearest_line(sorted(span_numbers), n)
    snapped_hit = index.segment_for_line(snapped)
    if snapped_hit is None:
        return None
    segment, ref = snapped_hit
    if speaker and (index.speakers_of.get(segment["id"]) or set()):
        # P2h finding 2: snap onto a line this speaker actually speaks.
        own_lines = index.speaker_lines(segment, speaker)
        if not own_lines:
            return None
        if index.speaker_at(segment, snapped, prefer=speaker) != speaker:
            snapped = min(own_lines, key=lambda line: (abs(snapped - line), line))
            ref = index.closest_ref(segment, snapped)
    snap = _speakers_row(
        work_id, n, ref, printed, speaker, index.speaker_at(segment, snapped, prefer=speaker)
    )
    snap["snapped_to"] = ref
    snap["segment"] = segment["id"]
    return {
        "attached": True,
        "tick": snapped,
        "ref": ref,
        "segment": segment,
        "snap": snap,
        "mismatch": None,
    }


def parse_translation(
    xml_path: Path,
    spine: dict,
    *,
    work_id: str,
    translation_id: str,
    sigla: dict | None = None,
    english_aliases: dict[str, str] | None = None,
    covered_decl: list[dict] | None = None,
) -> tuple[dict, dict[str, str], dict]:
    """Parse one ``perseus-play`` TEI and cut it on the Greek segments."""
    tree = etree.parse(str(xml_path))
    translation = tree.find('.//{*}div[@type="translation"]')
    if translation is None:
        raise ValueError(f"no div type='translation' in {xml_path}")

    if not isinstance(sigla, _SiglaResolver):
        sigla = _SiglaResolver.from_map(sigla or {})
    aliases = english_aliases or {}
    index = _SpeechIndex(spine, sigla)
    chunks_by_id: dict[str, dict] = {}
    footnotes: dict[str, str] = {}
    snaps: list[dict] = []
    mismatches: list[dict] = []
    anomalies: list[dict] = []
    text_parser = _LineText(footnotes, anomalies)
    anchor_count = 0
    english_canonical: list[str] = []
    english_printed: list[str] = []
    display_seen: set[str] = set()

    def ensure_chunk(segment: dict) -> dict:
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
        return chunk

    def append_text(
        segment: dict,
        text: str,
        tick_n: int,
        *,
        printed: str,
        canonical: str | None,
        add_turn: bool,
    ) -> dict | None:
        chunk = ensure_chunk(segment)
        if chunk["text"]:
            chunk["text"] += " "
        offset = len(chunk["text"])
        turn = None
        if add_turn and printed:
            turn = {
                "offset": offset,
                "speaker": canonical or printed,
                "display": printed,
            }
            chunk["turns"].append(turn)
        chunk["bekker"].append({"n": tick_n, "offset": offset, "real": True})
        chunk["text"] += text
        return turn

    jobs: list[dict] = []
    claimed: set[tuple[str, str]] = set()
    turns_emitted: dict[tuple[int, str, str], dict | None] = {}
    attribution_differences: list[dict] = []

    def commit_job(
        job,
        segment,
        tick,
        *,
        snap=None,
        mismatch=None,
        add_turn=True,
        speaker_mismatch=None,
    ) -> None:
        if mismatch:
            mismatches.append(mismatch)
        if snap:
            snaps.append(snap)
        turn_key = (job["sp_index"], job["printed"], segment["id"])
        already = turn_key in turns_emitted
        turn = append_text(
            segment,
            job["text"],
            tick,
            printed=job["printed"],
            canonical=job["canonical"],
            add_turn=add_turn and bool(job["printed"]) and not already,
        )
        if job["printed"] and not already:
            turns_emitted[turn_key] = turn
        if speaker_mismatch:
            # P2h finding 3: the disagreement belongs to the English TURN, not
            # to the whole chunk — a packed chunk's other turns are correctly
            # attributed and must not be underlined with this one's quarrel.
            turn = turns_emitted.get(turn_key) or turn
            if turn is not None:
                turn.setdefault("speakerMismatch", speaker_mismatch)
            attribution_differences.append(
                {
                    "greek_id": segment["id"],
                    "line": job["n"],
                    "english_speaker": speaker_mismatch["english"],
                    "greek_speaker": speaker_mismatch["greek"],
                }
            )
        if job["canonical"]:
            # Claims are (segment, speaker) pairs: one speaker's repair no
            # longer locks the segment against another's (P2h finding 4).
            claimed.add((segment["id"], job["canonical"]))
        job["assigned"] = segment["id"]

    for sp_index, speech in enumerate(translation.findall(".//{*}sp"), start=1):
        speaker_el = speech.find("./{*}speaker")
        printed = (
            collapse_ws("".join(speaker_el.itertext())).strip()
            if speaker_el is not None
            else ""
        )
        canonical = _canonical_english(printed, aliases)
        if printed and printed not in display_seen:
            display_seen.add(printed)
            english_printed.append(printed)
            if canonical:
                english_canonical.append(canonical)
        split = (not printed) or _has_para_milestone(speech)
        slices = _iter_speech_slices(
            speech,
            split=split,
            text_parser=text_parser,
            anomalies=anomalies,
            sp_index=sp_index,
            printed=printed,
        )
        speech_anchors = [
            anchor
            for sl in slices
            for anchor, _part in sl.pieces
            if anchor is not None
        ]
        owner_ids = set()
        for anchor in speech_anchors:
            owned = index.segment_for_anchor(anchor)
            if owned is not None:
                owner_ids.add(owned[0]["id"])
        multi_span = len(owner_ids) > 1
        for sl in slices:
            anchor = sl.first_anchor()
            if anchor is None:
                text = sl.text()
                if not text:
                    continue
                jobs.append(
                    {
                        "n": None,
                        "anchor": None,
                        "text": text,
                        "printed": printed,
                        "canonical": canonical,
                        "speech_anchors": speech_anchors,
                        "sp_index": sp_index,
                        "speakerless": not printed,
                        "multi_span": multi_span,
                    }
                )
                continue
            for piece_n, piece_text in sl.pieces:
                piece = collapse_ws(piece_text).strip()
                if not piece:
                    continue
                jobs.append(
                    {
                        "n": _anchor_base(piece_n or anchor),
                        "anchor": piece_n if piece_n is not None else anchor,
                        "text": piece,
                        "printed": printed,
                        "canonical": canonical,
                        "speech_anchors": speech_anchors,
                        "sp_index": sp_index,
                        "speakerless": not printed,
                        "multi_span": multi_span,
                    }
                )

    prev_assigned: dict[int, str] = {}
    for job in jobs:
        n = job["n"]
        if n is not None:
            anchor_count += 1
        if n is None:
            prev_id = prev_assigned.get(job["sp_index"])
            if prev_id is None:
                anomalies.append(
                    {"kind": "nless_slice_unattached", "sp": job["sp_index"]}
                )
                continue
            prev_order = index.order[prev_id]
            nxt = prev_order + 1 if job["speakerless"] else prev_order
            if nxt < 0 or nxt >= len(index.segments):
                anomalies.append(
                    {"kind": "nless_slice_unattached", "sp": job["sp_index"]}
                )
                continue
            segment = index.segments[nxt]
            numbers = index.span.get(segment["id"]) or set()
            if not numbers:
                anomalies.append(
                    {"kind": "nless_slice_unattached", "sp": job["sp_index"]}
                )
                continue
            tick_n = min(numbers)
            ref = index.closest_ref(segment, tick_n)
            snap = {
                **_speakers_row(
                    work_id,
                    None,
                    ref,
                    job["printed"],
                    job["canonical"],
                    # P2i finding 6: the speaker of the TICK LINE, never the
                    # segment's joined speaker set ("Ismene / Herald").
                    index.speaker_at(segment, tick_n, prefer=job["canonical"]),
                ),
                "snapped_to": ref,
                "segment": segment["id"],
                "kind": "nless_para",
            }
            commit_job(job, segment, tick_n, snap=snap)
            prev_assigned[job["sp_index"]] = segment["id"]
            continue
        result = _resolve_slice_anchor(
            n,
            anchor=job["anchor"],
            speaker=job["canonical"],
            speech_anchors=job["speech_anchors"],
            multi_span=job["multi_span"],
            index=index,
            work_id=work_id,
            printed=job["printed"],
            claimed=claimed,
        )
        if result is None:
            anomalies.append(
                {
                    "kind": "unmatched_anchor",
                    "sp": job["sp_index"],
                    "n_raw": job["anchor"],
                }
            )
            continue
        # P2i finding 2/8: every anchor whose printed line is on the spine
        # now attaches (flagged when the editions disagree), so a resolved
        # anchor is never handed back unattached.
        commit_job(
            job,
            result["segment"],
            result["tick"],
            snap=result.get("snap"),
            mismatch=result.get("mismatch"),
            speaker_mismatch=result.get("speaker_mismatch"),
        )
        prev_assigned[job["sp_index"]] = job["assigned"]

    chunks = [
        chunks_by_id[segment["id"]]
        for segment in spine["segments"]
        if segment["id"] in chunks_by_id
    ]
    for chunk in chunks:
        # Compatibility: the chunk-level flag survives only for a chunk whose
        # EVERY turn disagrees (the ordinary one-turn attribution difference).
        turns = chunk.get("turns") or []
        if turns and all(turn.get("speakerMismatch") for turn in turns):
            chunk["speakerMismatch"] = turns[0]["speakerMismatch"]
    covered = _continuation_covered_by(index, chunks_by_id, jobs)
    # REVIEW-CHECKLIST 7 (2026-09-09): a hole the span rule cannot prove but
    # a reviewer has confirmed sits inside a neighbour's block is declared in
    # the manifest (english.<slot>.covered: [{greek, by}]) and shows in the
    # reader as "Translated with the speech above"; the declaration wins
    # over the computed map for its segment.
    from .stage1_turn_english import _owning_covered, _resolve_covered

    covered.update(_resolve_covered(covered_decl or [], spine["segments"], work_id))
    covered = _owning_covered(covered, set(chunks_by_id), work_id)
    english = {
        "work": work_id,
        "source": xml_path.name,
        "translation": translation_id,
        "chunks": chunks,
        "chapters": [],
        "english_covered_by": covered,
    }
    total_segments = len(spine["segments"])
    report = {
        "work": work_id,
        "translation": translation_id,
        "anchor_count": anchor_count,
        "snaps": snaps,
        "snap_count": len(snaps),
        "speech_mismatches": mismatches,
        "speech_mismatch_count": len(mismatches),
        "unresolved_mismatch_count": sum(
            1 for item in mismatches if not item.get("attached_to")
        ),
        "attribution_differences": attribution_differences,
        "attribution_difference_count": len(attribution_differences),
        "segments_with_chunk": len(chunks),
        "segments_total": total_segments,
        "coverage_ratio": len(chunks) / total_segments if total_segments else 0.0,
        "covered_by_count": len(covered),
        "footnotes": len(footnotes),
        "anomalies": anomalies,
        "speakers": _speaker_report(
            spine, sigla, english_canonical, english_printed
        ),
    }
    return english, footnotes, report


def _chunks_as_overlay(english: dict) -> dict[str, list[dict]]:
    """Perseus-play chunks → the overlay dict stage7 reads from ``ross_chunks.json``."""
    out: dict[str, list[dict]] = {}
    for chunk in english.get("chunks") or []:
        text = chunk.get("text") or ""
        turns = chunk.get("turns") or []
        for turn in reversed(turns):
            name = (turn.get("display") or turn.get("speaker") or "").rstrip(".")
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
        raise ValueError(f"{manifest.work_id}: english.{slot} is required for perseus-play")
    xml_path = SOURCES_DIR / cfg["source"]
    speakers = manifest.data.get("speakers") or {}
    # Resolve Greek speakers through stage7's own rules (overrides included).
    sigla = _SiglaResolver(manifest)
    if slot == "secondary":
        aliases = speakers.get("english_secondary") or speakers.get("english") or {}
    else:
        aliases = speakers.get("english") or {}
    english, footnotes, report = parse_translation(
        xml_path,
        spine,
        work_id=manifest.work_id,
        covered_decl=cfg.get("covered") or [],
        translation_id=cfg["id"],
        sigla=sigla,
        english_aliases=aliases,
    )
    from .stage2_validate import _play_line_english_gap_ids

    gap_ids = _play_line_english_gap_ids(manifest, spine["segments"])
    if gap_ids:
        covered = {
            sid: cover
            for sid, cover in (english.get("english_covered_by") or {}).items()
            if sid not in gap_ids
        }
        english["english_covered_by"] = covered
        report["covered_by_count"] = len(covered)

    out_dir = BUILD_DIR / "stage1"
    out_dir.mkdir(parents=True, exist_ok=True)
    alignment = _alignment_with_coverage(spine, english)
    if slot == "secondary":
        english_path = out_dir / "ross_chunks.json"
        alignment_path = out_dir / "secondary_alignment.json"
        report_path = out_dir / "secondary_report.json"
        write_json(english_path, _chunks_as_overlay(english))
        write_json(alignment_path, alignment)
        write_json(report_path, report)
        return english_path, alignment_path, report_path
    english_path = out_dir / "english_chunks.json"
    alignment_path = out_dir / "alignment.json"
    report_path = out_dir / "english_report.json"
    write_json(english_path, english)
    write_json(alignment_path, alignment)
    write_json(report_path, report)
    write_json(out_dir / "english_footnotes.json", footnotes)
    return english_path, alignment_path, report_path
