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

C1 (2026-09-17 fix-mechanisms brief): "translator drift within ±3" is real
only when there is outside evidence the anchor's own NUMBER, not just its
speaker, is untrustworthy — see :func:`_repairable_anchors`: a literal
inversion in the translation's own ``<l n>`` sequence (Agamemnon's real TEI
prints ``n="1204"`` right before ``n="1203"``), or membership in a run of
three or more consecutive anchors that each independently disagree with the
Greek (Seven 998–1026, Smyth's whole stichomythia one line ahead of the
TLG's).  An anchor that is neither — it keeps its place in the increasing
sequence and stands alone or paired, not in a run of three — simply
disagrees with the Greek about who speaks it (Oedipus Tyrannus 625; Electra
650, 674, 675) and is never moved: it attaches at its own line as an
``attribution_difference`` instead, the same outcome the ±3 search already
produces when it finds nothing.
"""

from __future__ import annotations

import bisect
import html
import json
import re
from pathlib import Path

from lxml import etree

from .config import BUILD_DIR, SOURCES_DIR, Manifest
from .stage1_common import (
    collapse_ws,
    local_name,
    text_excluding_subtrees,
    write_json,
)
from .stage1_english import build_alignment
from .stage1_turn_english import (
    _SiglaResolver,
    _event_ref,
    _segment_speaker_events,
    _speaker_report,
    speaker_at as _line_speaker,
)


# Round 4 item 8: a stage direction reached in the middle of a speech, held
# in the piece text through `collapse_ws` (which would eat the newlines the
# reader's own `_direction_` convention needs) and expanded at the moment the
# text is appended to its chunk.  Two control characters no translation
# contains, so nothing else can be mistaken for one.
_DIRECTION_OPEN = "\x02"
_DIRECTION_CLOSE = "\x03"
_INLINE_DIRECTION = re.compile(
    rf"[ \t]*{_DIRECTION_OPEN}([^{_DIRECTION_CLOSE}]*){_DIRECTION_CLOSE}[ \t]*"
)


def _inline_directions(text: str) -> str:
    """Expand a held mid-speech direction into the reader's own convention:
    `_direction_` alone on its line, which `markStageDirections`
    (shared/lib/speakers.ts) already renders as a `.stage-dir` span in every
    play column, including this one.  Owner ruled 2026-09-21: the reader
    sets a word or two inline in round brackets, a sentence on its own line."""
    return _INLINE_DIRECTION.sub(lambda m: f"\n_{m.group(1)}_\n", text)


_EM_DASH_SPLIT = re.compile(r"(?:(?<=\s)|^)(?=—)")
_LETTERED_ANCHOR = re.compile(r"^(\d+)[a-z]+$")
# A line_fixes VALUE only. ``"<ref>.<k>"`` with k >= 2 names the k-th
# printing of a ref in citation.repeated_refs (segment id ``1:<ref>.<k>``).
# A raw TEI ``<l n>`` is never read as this form.
_REPEATED_SEAT = re.compile(r"^(\d+)\.(\d+)$")
# On the in-memory TEI element only. lxml hands back a fresh Python wrapper
# on each walk, so the element's own id cannot carry this mark.
_LINE_FIX_SEAT = "{http://greek-plays.local/line-fix}seat"
# Every ``<l>`` a line_fixes entry rewrote, whatever number it now carries:
# the translation may print the same number unfixed elsewhere (Seven 971).
_LINE_FIXED = "{http://greek-plays.local/line-fix}fixed"
_LINE_CUTS = "{http://greek-plays.local/line-fix}cuts"
_SKIP_TAGS = frozenset({"gap", "speaker"})


def _repeated_seat(value: str | None) -> tuple[str, int] | None:
    """``("810", 2)`` for a line_fixes value ``"810.2"``. ``None`` otherwise,
    including ``"810.1"`` and a lettered anchor."""
    if not value:
        return None
    match = _REPEATED_SEAT.fullmatch(value)
    if match is None:
        return None
    k = int(match.group(2))
    if k < 2:
        return None
    return match.group(1), k


def _anchor_base(ref: str) -> int:
    """Integer line a numbered anchor counts as. ``810.2`` is line 810."""
    seat = _repeated_seat(ref)
    if seat is not None:
        return int(seat[0])
    lettered = _LETTERED_ANCHOR.fullmatch(ref)
    return int(lettered.group(1) if lettered else ref)


def _numbered_anchor(anchor: str | None) -> bool:
    """True when ``anchor`` has an integer base: a digit, a lettered share,
    or a repeated-ref seat (``810.2``)."""
    if not isinstance(anchor, str) or not anchor:
        return False
    return bool(
        anchor.isdigit()
        or _LETTERED_ANCHOR.fullmatch(anchor)
        or _repeated_seat(anchor)
    )


def _nearest_piece_anchor(anchors: list, index: int):
    """A piece with no anchor of its own (a mid-speech `<stage>` sibling of
    `<l>`, or a paragraph opened before the first line) seats beside its
    nearest NEIGHBOUR in the slice: the next anchored piece if one follows
    (so it prints before that line's own text), else the previous one (so it
    prints after it) — never the slice's first anchor regardless of where in
    the speech the piece actually sits (Sol's integration review, finding 1,
    2026-09-18: Orestes' mid-speech `spoken`/`sung` tags before 1288 and 1291
    both landed on 1286, the speech's first line)."""
    for j in range(index + 1, len(anchors)):
        if anchors[j] is not None:
            return anchors[j]
    for j in range(index - 1, -1, -1):
        if anchors[j] is not None:
            return anchors[j]
    return None


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
        # A line_fixes seat ``"<ref>.<k>"`` is the k-th printing, in the
        # document order this list already records. The returned ref stays
        # the printed line (``810``), so integer callers keep one number
        # while the segment is the distinct printing.
        seat = _repeated_seat(ref)
        if seat is not None:
            base, k = seat
            hits = sorted(self.by_ref.get(base) or [], key=lambda item: item[1])
            if len(hits) < k:
                return None
            segment, _order = hits[k - 1]
            return segment, base
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
    __slots__ = ("pieces", "fixed")

    def __init__(self) -> None:
        self.pieces: list[tuple[str | None, str]] = []
        # Parallel to ``pieces``: the piece's text came from an ``<l>`` a
        # line_fixes entry rewrote.
        self.fixed: list[bool] = []

    def add(self, n: str | None, text: str, fixed: bool = False) -> None:
        if not text:
            return
        fixed = fixed and n is not None
        if self.pieces and self.pieces[-1][0] == n and self.fixed[-1] == fixed:
            prev_n, prev = self.pieces[-1]
            self.pieces[-1] = (prev_n, prev + text)
            return
        self.pieces.append((n, text))
        self.fixed.append(fixed)

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
    head_directions: list[str] | None = None,
) -> list[_Slice]:
    slices: list[_Slice] = []
    current = _Slice()
    line_n_live = True
    seen_text = False
    in_fixed = False

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
        nonlocal seen_text
        if not raw:
            return
        if raw.strip():
            seen_text = True
        if not split:
            current.add(n, raw, in_fixed)
            return
        parts = _EM_DASH_SPLIT.split(raw)
        for i, part in enumerate(parts):
            if not part:
                continue
            if i > 0 and current.has_content:
                flush()
            current.add(slice_n(n), part, in_fixed)

    def walk(node, current_n: str | None = None) -> None:
        nonlocal line_n_live, in_fixed
        tag = local_name(node)
        if tag is None:
            # Comment and processing-instruction nodes have a non-string
            # .tag, so local_name returns None. A comment's own text is
            # dropped, but its .tail is real line text that follows it in
            # document order and must not be lost (Hippolytus review
            # finding 1, 2026-09-17). Processing instructions stay fully
            # skipped, tail included.
            if node.tag is etree.Comment and node.tail:
                handle_text(node.tail, current_n)
            return
        if tag == "stage":
            # C12: a Perseus stage direction.  One that precedes the
            # speech's own words becomes the turn's `directionsBefore`;
            # one reached in the middle of a speech prints inline, on its own
            # line, where the edition prints it (round 4 item 8).
            text = collapse_ws("".join(node.itertext())).strip()
            text = text.replace("_", "").replace(_DIRECTION_OPEN, "").replace(
                _DIRECTION_CLOSE, ""
            )
            if text:
                if seen_text:
                    # Round 4 item 8: a direction the speech has already begun
                    # has no turn to hang `directionsBefore` on, and 375 of
                    # them across 33 plays were counted as lost.  It prints
                    # where the edition prints it, inline, on its own line —
                    # the slot the reader already has for a direction inside a
                    # speech.
                    anomalies.append(
                        {
                            "kind": "stage_direction_inline",
                            "sp": sp_index,
                            "text": text,
                        }
                    )
                    handle_text(
                        f"{_DIRECTION_OPEN}{text}{_DIRECTION_CLOSE}", current_n
                    )
                elif head_directions is not None:
                    head_directions.append(text)
            if node.tail:
                handle_text(node.tail, current_n)
            return
        if tag == "del":
            # C13 (iphigenia-at-aulis finding 1, 2026-09-17): `<del>` is the
            # EDITOR'S deletion -- text the edition prints and brackets, not
            # text that is absent.  Skipping it dropped ten lines of
            # Agamemnon's prologue (IA 105-114) and 140 more passages across
            # the corpus out of the reader's default column, leaving no trace
            # in the build.  The Greek column prints these lines (the hard
            # rule: a deleted line stays printed), so the English prints them
            # too, wrapped in the edition's own mark for deleted text.
            #
            # It is never an `<l>` or an `<sp>` in these files, always an
            # inline run inside one, so there is no turn or chunk to carry a
            # flag: the mark travels with the words, in the chunk `text` every
            # consumer already reads (the pairer's primary bridge, the audit,
            # search, copy-paste). Owner ruled 2026-09-19: square brackets
            # stay; the bracketed spans remain available for styling.
            deleted = collapse_ws(text_excluding_subtrees(node)).strip()
            handle_text("[", current_n)
            if node.text:
                handle_text(node.text, current_n)
            for child in node:
                walk(child, current_n)
            handle_text("]", current_n)
            if deleted:
                anomalies.append(
                    {"kind": "deleted_text_kept", "sp": sp_index, "text": deleted}
                )
            if node.tail:
                handle_text(node.tail, current_n)
            return
        if tag in _SKIP_TAGS:
            if node.tail:
                handle_text(node.tail, current_n)
            return
        if tag == "note":
            marker = text_parser.consume_note(node)
            if marker:
                # The marker belongs to the line it sits in, fixed or not.
                current.add(slice_n(current_n), marker, in_fixed)
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
            # Only an element line_fixes itself rewrote to ``"<ref>.<k>"``.
            authorized_seat = (
                _repeated_seat(raw_n) is not None and node.get(_LINE_FIX_SEAT) == "1"
            )
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
            if not raw_n or (
                not raw_n.isdigit() and lettered is None and not authorized_seat
            ):
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
            outer_fixed, in_fixed = in_fixed, node.get(_LINE_FIXED) == "1"
            if node.get(_LINE_CUTS):
                # The declaration names words in this one numbered line.
                # Keep the source line's head and give each tail its Greek ref.
                start = 0
                in_fixed = True
                for position, ref in json.loads(node.get(_LINE_CUTS)):
                    handle_text(content[start:position], raw_n if start == 0 else previous_ref)
                    start, previous_ref = position, ref
                handle_text(content[start:], previous_ref)
                in_fixed = outer_fixed
                if node.tail:
                    handle_text(node.tail, current_n)
                return
            if node.text:
                handle_text(node.text, raw_n)
            for child in node:
                walk(child, raw_n)
            in_fixed = outer_fixed
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


def _out_of_order_anchors(jobs: list[dict]) -> set[int]:
    """Job POSITIONS involved in a literal inversion of the translation's
    OWN ``<l n>`` sequence: two numbered anchors, adjacent in document
    order, where the later one is a LOWER number than the one before it
    (Agamemnon's real Perseus TEI prints ``n="1204"`` immediately before
    ``n="1203"``).  A translation is always typeset in increasing printed
    order; a drop like this is a transcription/TEI artifact, not an
    editorial fact (C1 condition A — see :func:`_repairable_anchors`).

    G3 (Grok's read of round 1): the number read here is the one the TEI
    PRINTED (``raw_n``), never C4's remapped one.  A declared rotation
    always ends in a numeric drop once remapped, so reading the remapped
    number let every successful remap manufacture its own repair evidence
    and pull the rotation's wrap line off the seat the remap had just given
    it.
    """
    broken: set[int] = set()
    prev: int | None = None
    prev_pos: int | None = None
    for pos, job in enumerate(jobs):
        n = job.get("raw_n")
        if n is None:
            continue
        if prev is not None and n < prev:
            broken.add(pos)
            broken.add(prev_pos)
        prev, prev_pos = n, pos
    return broken


def _mismatching_anchors(jobs: list[dict], index: _SpeechIndex) -> dict[int, bool]:
    """Which anchors disagree with the Greek about their own speaker,
    computed independently of repair so :func:`_repairable_anchors` can find
    a RUN of them.  Only single-speech (not multi-span) digit anchors with an
    exact Greek ref of their own are checked — the same test
    :func:`_resolve_slice_anchor` itself applies.

    G2 (Grok's read of round 1): keyed by JOB POSITION, not by the integer
    base.  An antilabe's two halves share a base (``328`` and ``328a``), so
    an int key let the second half's verdict overwrite the first's and the
    run counter then scored both halves with one bit.
    """
    result: dict[int, bool] = {}
    for pos, job in enumerate(jobs):
        n = job.get("n")
        anchor = job.get("anchor")
        speaker = job.get("canonical")
        if n is None or anchor is None or not speaker or job.get("multi_span"):
            continue
        hit = index.segment_for_anchor(anchor)
        if hit is None:
            continue
        segment, ref = hit
        greek_speaker = index.share_speaker(segment, n, anchor, prefer=speaker)
        result[pos] = greek_speaker is not None and speaker != greek_speaker
    return result


# Perseus numbers a prose translation every fifth line, so two anchors up to
# five lines apart are adjacent lines of the translation and a drift running
# through both is one run (Agamemnon's exodos: Smyth anchors 1660, 1662,
# 1665, 1666, ...).  A wider gap means the translation has its own text in
# between that does NOT disagree, and the disagreements on either side are
# independent (G1).
_RUN_MAX_LINE_GAP = 5


def _repairable_anchors(jobs: list[dict], index: _SpeechIndex) -> set[int]:
    """Anchors :func:`_resolve_slice_anchor` may hand to
    ``nearest_matching_speech`` (C1): a line carrying its own ``n`` inside
    the play's numbering is not drift, and repair is only safe when there is
    outside evidence the NUMBER itself, not just the speaker, is untrustworthy.
    Two such signs, both drawn from real corpus instances:

    A. a literal inversion in the translation's own ``<l n>`` sequence
       (:func:`_out_of_order_anchors` — Agamemnon 1203/1204, a scanned TEI
       with the two lines' numbers swapped).
    B. membership in a RUN of three or more consecutive anchors that each
       independently disagree with the Greek about their speaker (Seven
       998–1026: Smyth's whole stichomythia runs one line ahead of the
       TLG's, so 999 through 1004 mismatch in a row).

    A run of exactly two (Electra 674/675: two adjacent lines whose speakers
    the editions simply swap, in perfectly ordinary printed order) is
    neither of these — two lines can coincidentally look swapped, three
    cannot — and stays a plain, in-place ``attribution_difference``.
    """
    repairable = _out_of_order_anchors(jobs)
    mismatch = _mismatching_anchors(jobs, index)
    numbered = [pos for pos, job in enumerate(jobs) if job.get("n") is not None]
    run: list[int] = []
    for pos in numbered:
        # G1: a RUN is successive numbered jobs whose own line numbers
        # advance by no more than one anchor step, each scored by its OWN
        # mismatch bit.  Counting bare positions let three disagreements ten
        # lines apart — three independent attribution differences, with the
        # translation's own unnumbered text between them — pass as a run.
        if mismatch.get(pos) and (
            not run or 0 <= jobs[pos]["n"] - jobs[run[-1]]["n"] <= _RUN_MAX_LINE_GAP
        ):
            run.append(pos)
            continue
        if len(run) >= 3:
            repairable.update(run)
        run = [pos] if mismatch.get(pos) else []
    if len(run) >= 3:
        repairable.update(run)
    repairable.update(_crowded_seat_anchors(jobs, index, mismatch))
    return repairable


def _crowded_seat_anchors(
    jobs: list[dict], index: _SpeechIndex, mismatch: dict[int, bool]
) -> set[int]:
    """S3 (the 2026-09-17 bare-segment sweep): the lone disagreeing anchor
    that may still be repaired.

    C1's rule — an anchor whose number names a real Greek line is not drift
    — is right whenever the anchor's number and the Greek's number denote
    the same verse, and it is what keeps Oedipus Tyrannus 625 on its own
    line.  It is wrong when the translation's numbering has slipped by a
    line, and the sweep found two real cases a run of three could never
    catch: Hecuba's anchor 709 (the Chorus's question, which Coleridge
    numbers one ahead of Diggle's 708) and Persians' 1076 (the Chorus's
    closing line, which Smyth numbers one ahead of 1077).

    What tells those apart from OT 625 is not how long the disagreement runs
    but what else is sitting on the seat.  In each, the Greek segment the
    anchor's own number resolves to ALREADY holds the English of a different
    line number that the Greek agrees with: two English LINES have landed on
    one Greek seat, and a translation does not number two lines for one
    verse.  OT 625's only co-occupant is 625a — the second half of its own
    line, which is what an antilabe is and implies no slip at all.  So the
    co-occupant must be a different SOURCE LINE, which is not the same
    thing as a different number (Sol review of 6e8a9d6, finding 2): a
    translator may number the halves of one Greek line 625 and 626 rather
    than 625/625a, and then the bases differ while the source line is one.
    What says so is the line itself — two anchors on ONE printed ref whose
    line carries TWO SPEAKER SHARES are that antilabe's two halves,
    however they are numbered, and imply no slip.  Anything else is
    evidence: a co-occupant on another of the seat's printed refs (Smyth's
    Persians 1075 and 1076, two refs in one Greek speech), or two English
    lines on a single-speaker ref (Diggle's Hecuba 709-710).

    And a LONE move must fill a hole: the same-speaker speech the repair
    would reach must hold no English anchor of its own, so it never
    displaces a neighbour that is already correct.  (Hecuba 708 and Persians
    1077 are both bare; Creon's 624, the seat OT 625 used to be dragged to,
    is bare too — which is exactly why the first clause has to do the work.)

    A crowded seat is also the SEED of a run.  Where the slip lasts several
    lines every anchor in it is displaced, and each in turn frees the seat
    the next one needs, so the run is repaired together and the
    hole-filling test cannot be applied to its members one at a time
    (Suppliants 1159-1160: Coleridge numbers the whole close of the kommos
    one ahead, and his 1161 lands on the tail of the same Greek seat as his
    1160 — the crowding — while 1:1158 stands empty).  The run is the
    maximal stretch of mismatching anchors around the seed whose own line
    numbers advance by at most one, the same shape Rule B counts.
    """
    def agrees(job: dict) -> bool:
        # Read per job, not from ``mismatch``: a piece of a multi-span
        # speech is excluded there (it is never itself repaired) but it is
        # just as good evidence that the seat is already occupied by its
        # own, correctly attributed English — Smyth's Persians 1075 shares
        # a ``<sp>`` with 1074b and so is multi-span.
        anchor, n, speaker = job.get("anchor"), job.get("n"), job.get("canonical")
        if anchor is None or n is None or not speaker:
            return False
        hit = index.segment_for_anchor(anchor)
        if hit is None:
            return False
        greek = index.share_speaker(hit[0], n, anchor, prefer=speaker)
        return greek is not None and greek == speaker

    seats: dict[str, list[int]] = {}
    seat_ref: dict[int, str] = {}
    for pos, job in enumerate(jobs):
        anchor = job.get("anchor")
        if anchor is None:
            continue
        hit = index.segment_for_anchor(anchor)
        if hit is not None:
            seats.setdefault(hit[0]["id"], []).append(pos)
            seat_ref[pos] = hit[1]
    anchored = set(seats)

    numbered = [pos for pos, job in enumerate(jobs) if job.get("n") is not None]
    order = {pos: i for i, pos in enumerate(numbered)}

    def run_around(pos: int) -> list[int]:
        """The stretch of mismatching anchors around ``pos`` whose own line
        numbers advance by at most one (Rule B's own shape)."""
        i = order[pos]
        lo = i
        while lo > 0:
            prev, cur = numbered[lo - 1], numbered[lo]
            if (
                not mismatch.get(prev)
                or not 0 <= jobs[cur]["n"] - jobs[prev]["n"] <= _RUN_MAX_LINE_GAP
            ):
                break
            lo -= 1
        hi = i
        while hi + 1 < len(numbered):
            cur, nxt = numbered[hi], numbered[hi + 1]
            if (
                not mismatch.get(nxt)
                or not 0 <= jobs[nxt]["n"] - jobs[cur]["n"] <= _RUN_MAX_LINE_GAP
            ):
                break
            hi += 1
        return numbered[lo : hi + 1]

    movable: set[int] = set()
    for pos, job in enumerate(jobs):
        if not mismatch.get(pos):
            continue
        anchor, n, speaker = job.get("anchor"), job.get("n"), job.get("canonical")
        hit = index.segment_for_anchor(anchor) if anchor is not None else None
        if hit is None or n is None or not speaker:
            continue
        shares = len([s for s in index.line_shares(hit[0], n) if s is not None])
        settled = any(
            jobs[other].get("n") != n
            and (seat_ref.get(other) != seat_ref.get(pos) or shares < 2)
            and agrees(jobs[other])
            for other in seats.get(hit[0]["id"], ())
        )
        if not settled:
            continue
        run = run_around(pos)
        if len(run) == 1:
            repaired = index.nearest_matching_speech(n, speaker)
            if repaired is None or repaired[0]["id"] in anchored:
                continue
        movable.update(run)
    return movable


_REPEAT_MIN_CHARS = 15


def _repeat_lettered_positions(jobs: list[dict]) -> set[int]:
    """C2 (fix-mechanisms brief round 2, eumenides #5): an edition may
    reprint a refrain verbatim as a lettered "ephymnion" repeat (Murray's
    Eumenides ``372a``/``375a``, word for word his own ``372``/``375``),
    with no separate Greek line to hold the second copy.  Attaching it the
    ordinary way (its base digit IS a real ref) just writes the segment's
    own sentence a second time.  The signal that distinguishes a repeat
    from a genuine antilabe answering half (Electra's ``1221a``, which says
    something NEW) is textual: a repeat's own piece text is the SAME
    sentence, verbatim, as the base number's earlier, plain occurrence —
    an antilabe half never is.  Short interjections ("Ah!") are exempted
    (``_REPEAT_MIN_CHARS``) since two different speeches coincidentally
    sharing one exclamation is not evidence of a reprint.

    Returns positions into ``jobs`` (by list index) to skip outright: no
    text, no turn, no tick — exactly as a stage direction contributes
    nothing to the dialogue it repeats.
    """
    plain_text_by_base: dict[int, str] = {}
    skip: set[int] = set()
    for pos, job in enumerate(jobs):
        n = job.get("n")
        anchor = job.get("anchor")
        if n is None or anchor is None:
            continue
        text = collapse_ws(job.get("text") or "").strip().casefold()
        if _LETTERED_ANCHOR.fullmatch(anchor) is None:
            plain_text_by_base.setdefault(n, text)
            continue
        prior = plain_text_by_base.get(n)
        if prior and len(prior) >= _REPEAT_MIN_CHARS and prior == text:
            skip.add(pos)
    return skip


def _small_piece_runs(jobs: list[dict]) -> list[list[int]]:
    """Positions into ``jobs`` for each maximal run (length >= 2) of
    consecutive jobs that are each the ONLY piece of a non-multi-span
    English speech — candidates for the antilabe share realignment of
    :func:`_antilabe_reassignments` (C6)."""
    counts: dict[int, int] = {}
    for job in jobs:
        counts[job["sp_index"]] = counts.get(job["sp_index"], 0) + 1
    runs: list[list[int]] = []
    current: list[int] = []
    for pos, job in enumerate(jobs):
        is_small = counts[job["sp_index"]] == 1 and not job.get("multi_span")
        if is_small:
            current.append(pos)
        else:
            if len(current) >= 2:
                runs.append(current)
            current = []
    if len(current) >= 2:
        runs.append(current)
    return runs


def _segment_event_shares(
    index: _SpeechIndex, segment: dict
) -> list[tuple[int, str | None]]:
    """(printed_line, speaker) for each REAL speaker event of a segment, in
    document order — excludes a printed line that merely inherits the
    previous event (a continuation), which is not a separate antilabe
    share."""
    line_n = index.line_n.get(segment["id"]) or {}
    internal_to_printed: dict[int, int] = {}
    for printed, internal in line_n.items():
        internal_to_printed.setdefault(internal, printed)
    out: list[tuple[int, str | None]] = []
    from .stage1_turn_english import _segment_speaker_events

    for internal_line, _offset, name, mapped in _segment_speaker_events(
        segment, index.sigla
    ):
        printed = internal_to_printed.get(internal_line)
        if printed is None:
            continue
        out.append((printed, name if mapped else None))
    return out


def _antilabe_pool(
    jobs: list[dict], sub: list[int], index: _SpeechIndex
) -> list[tuple[dict, int, str | None]] | None:
    """The ordered (segment, printed_line, speaker) shares ``sub``'s own
    members' raw anchors name, each multi-share segment counted once, in
    document order.  ``None`` when nothing in ``sub`` names a multi-share
    segment at all — no antilabe evidence to act on."""
    seen: dict[str, dict] = {}
    for pos in sub:
        anchor = jobs[pos].get("anchor")
        hit = index.segment_for_anchor(anchor) if anchor is not None else None
        if hit is None:
            continue
        segment, _ref = hit
        seen.setdefault(segment["id"], segment)
    ordered = sorted(seen.values(), key=lambda seg: index.order[seg["id"]])
    pool: list[tuple[dict, int, str | None]] = []
    has_multi = False
    for segment in ordered:
        shares = _segment_event_shares(index, segment)
        if len(shares) < 2:
            continue
        has_multi = True
        for printed_line, speaker in shares:
            pool.append((segment, printed_line, speaker))
    return pool if has_multi else None


def _antilabe_walk_matches(
    jobs: list[dict],
    sub: list[int],
    pool: list[tuple[dict, int, str | None]],
) -> bool:
    for pos, (_segment, _printed_line, speaker) in zip(sub, pool):
        if jobs[pos].get("canonical") != speaker:
            return False
    return True


def _position_is_movable(jobs: list[dict], pos: int, index: _SpeechIndex) -> bool:
    """Whether ``jobs[pos]`` may ever be reassigned by the antilabe walk at
    all.  An orphan (no Greek ref of its own) always may — it has nowhere
    else to go.  A piece whose naive target is a MULTI-share segment also
    may: which of that segment's shares it really represents is exactly
    the ambiguity :func:`_SpeechIndex.share_speaker`'s "does this speaker
    appear ANYWHERE on the line" check can paper over, so an unflagged
    piece there is not proof of correctness.  A piece whose naive target
    is a SINGLE-share segment has no such ambiguity — there is only one
    share to be — so it is movable only when it is actually WRONG there
    (a real speaker mismatch): Electra's "840" naively lands on Chorus's
    own single-share continuation while the piece itself is Electra's, a
    real, flagged mismatch.  Without a mismatch, a single-share target is
    provably already correct and must never be pulled into a neighbour's
    antilabe by coincidence of counting (Alcestis 388/389, each its own
    unambiguous single-share line, dragged toward 390/391's real antilabe;
    Bacchae 1185/1188, dragged toward 1182's already-complete one)."""
    job = jobs[pos]
    anchor = job.get("anchor")
    if anchor is None:
        return True
    hit = index.segment_for_anchor(anchor)
    if hit is None:
        return True
    segment, _ref = hit
    if len(segment.get("speakers") or []) >= 2:
        return True
    n = job.get("n")
    speaker = job.get("canonical")
    if not speaker or n is None:
        return False
    greek_speaker = index.share_speaker(segment, n, anchor, prefer=speaker)
    return greek_speaker is not None and speaker != greek_speaker


def _antilabe_window_has_cross_segment_evidence(
    jobs: list[dict], sub: list[int], index: _SpeechIndex
) -> bool:
    """Whether ``sub``'s own members' naive anchors, between them, name at
    least TWO DISTINCT multi-share Greek segments — proof this is a
    genuine cross-segment antilabe lag (Jebb's numbers running a half-line
    ahead so the lag visibly crosses from one packed line into the next),
    not a coincidence.

    A window can satisfy the plain piece-count-equals-pool-size and
    per-position speaker checks by sheer accident: three speakers who
    happen to alternate A-B-A across three consecutive, already-correct,
    single-share one-line exchanges (Electra 1499-1501, each a plain digit
    with its own unambiguous ref); or a lettered anchor that ALREADY
    resolves correctly on its own being dragged, along with two unrelated
    neighbours, into a coincidental rewalk of a segment it already
    completes by itself (Bacchae 1184b/1185/1188, where 1182/1182b/1184/
    1184b already exhaust that segment's own three real shares with no
    defect at all). Neither case moves anything ACROSS a segment boundary
    — the tell every genuine lagged run shares. A segment named only via
    an orphan (no anchor of its own at all) does not count toward this
    total; the orphan is evidence something is missing, not of where it
    truly measures against.
    """
    targets: set[str] = set()
    for pos in sub:
        anchor = jobs[pos].get("anchor")
        if anchor is None:
            continue
        hit = index.segment_for_anchor(anchor)
        if hit is None:
            continue
        segment, _ref = hit
        if len(segment.get("speakers") or []) >= 2:
            targets.add(segment["id"])
    return len(targets) >= 2


def _one_to_one_transposition_bases(
    blocks: list[dict] | None,
    printed_refs: list[str] | None,
    jobs: list[dict],
) -> list[set[int]]:
    """Line numbers of each declared transposition stretch whose English
    anchors already correspond one-to-one with the stretch's printed lines.

    The same guard :func:`_transposition_anchor_remap` uses before it will
    re-key: the distinct base numbers of the anchors inside the stretch's
    numeric range are exactly the stretch's own refs, one for one — none
    missing, none doubled. A lettered share (``1185`` beside ``1185a``, or
    two halves both rewritten onto ``1185``) is one base, not a second
    line. On such a stretch the anchors are already the right refs, and
    the English (numeric order) and the Greek (printed order) differ in
    position only because the edition transposed the lines. A
    document-position walk through that difference swaps lines that were
    already seated (Heracles 1185–1188: Diggle prints 1187, 1188, 1186,
    1185, and the walk exchanges 1185 with 1186).
    """
    if not blocks or not printed_refs:
        return []
    stretches, _anomalies = _transposition_printed_stretches(blocks, printed_refs)
    english_bases: set[int] = set()
    for job in jobs:
        anchor = job.get("anchor")
        if _numbered_anchor(anchor):
            english_bases.add(_anchor_base(anchor))
    settled: list[set[int]] = []
    for span, _forced in stretches:
        span_refs = [printed_refs[p] for p in span]
        printed_bases = [_anchor_base(_ref_root(ref)) for ref in span_refs]
        if len(set(printed_bases)) != len(printed_bases):
            continue
        lo, hi = min(printed_bases), max(printed_bases)
        observed = {base for base in english_bases if lo <= base <= hi}
        if observed != set(printed_bases):
            continue
        settled.append(set(printed_bases))
    return settled


def _window_overlaps_settled_transposition(
    jobs: list[dict], sub: list[int], settled: list[set[int]]
) -> bool:
    """Whether any piece in ``sub`` carries an anchor whose base is a line
    of a stretch :func:`_one_to_one_transposition_bases` has settled."""
    if not settled:
        return False
    for pos in sub:
        anchor = jobs[pos].get("anchor")
        if not _numbered_anchor(anchor):
            continue
        base = _anchor_base(anchor)
        if any(base in bases for bases in settled):
            return True
    return False


def _antilabe_reassignments(
    jobs: list[dict],
    index: _SpeechIndex,
    transpositions: list[dict] | None = None,
    printed_refs: list[str] | None = None,
) -> dict[int, tuple[dict, int]]:
    """C6 (fix-mechanisms brief round 2, electra-soph #2/#3/#12): a run of
    short antilabe speeches, matched by DOCUMENT POSITION against the
    Greek's own speaker events — the same order both editions transcribe
    the exchange in.  An edition may pack two or more speaker "shares" onto
    ONE printed Greek line while the English translation's own ``<l n>``
    increments once per SHARE, so the translation's numbers run a
    half-line ahead of (or behind) the Greek's the moment a line is
    packed; any English half whose own number then lands on no Greek ref
    at all is dropped outright by the ordinary per-anchor resolution
    (Jebb's Electra: 828, 829, 843, 844, 857, 867).  Numbers cannot fix
    this — position can.

    A broad run often holds more than one antilabe stretch, plus perfectly
    ordinary dialogue between and around them (Electra's kommos runs
    827-831, then correct dialogue at 836/840, then another lagged stretch
    at 841-845; the recognition run holds a whole stichomythia, a broken
    stretch, and an already-correct antilabe run, all as one chain of
    single-line speeches).  So every contiguous sub-window of a broad run
    is a candidate, not just a trim off its two ends: each is checked for
    the same three things — its own piece count matches the pool of real
    Greek events its members name, every member's own speaker agrees with
    the share the walk assigns it, and at least one member's ORDINARY,
    un-overridden resolution is provably broken (dropped outright, or
    disagreeing with the Greek about its speaker).  That last check is
    what keeps three merely-adjacent, already-correct one-line exchanges
    (Electra 1499-1501) from being "fixed" by sheer coincidence of
    alternating speakers.  A fourth keeps the walk out of a declared
    transposition whose anchors are already one-to-one with the stretch's
    printed lines (:func:`_one_to_one_transposition_bases`): there the
    position gap is the edition's own order, not a numbering lag, and
    walking it swaps lines that already name the right ref (Heracles
    1185/1186).  Windows are applied longest first, then earliest, and
    never overlap one already taken.

    Returns ``{job position: (segment, printed_line)}`` overrides for the
    positions a matching window resolves; every other job is untouched.

    ``transpositions`` and ``printed_refs`` are the citation rows and the
    spine's printed ref list already in hand at the call. The walk does
    not read the manifest itself.
    """
    overrides: dict[int, tuple[dict, int]] = {}
    settled = _one_to_one_transposition_bases(transpositions, printed_refs, jobs)
    for run in _small_piece_runs(jobs):
        total = len(run)
        candidates: list[list[int]] = []
        for start in range(total):
            for end in range(start + 2, total + 1):
                sub = run[start:end]
                if not all(_position_is_movable(jobs, pos, index) for pos in sub):
                    continue
                pool = _antilabe_pool(jobs, sub, index)
                if (
                    pool is not None
                    and len(pool) == len(sub)
                    and _antilabe_walk_matches(jobs, sub, pool)
                    and _antilabe_window_has_cross_segment_evidence(jobs, sub, index)
                    and not _window_overlaps_settled_transposition(
                        jobs, sub, settled
                    )
                ):
                    candidates.append(sub)
        candidates.sort(key=lambda sub: (-len(sub), sub[0]))
        claimed: set[int] = set()
        for sub in candidates:
            if claimed.intersection(sub):
                continue
            pool = _antilabe_pool(jobs, sub, index)
            assert pool is not None
            for pos, (segment, printed_line, _speaker) in zip(sub, pool):
                overrides[pos] = (segment, printed_line)
            claimed.update(sub)
    return overrides


def _multi_span_tail_redirects(
    jobs: list[dict], index: _SpeechIndex
) -> set[tuple[int, int]]:
    """C7 (fix-mechanisms brief round 2, prometheus-bound #4): a multi-span
    ``<sp>``'s LAST anchored piece sometimes lands, by an exact ref match,
    on the Greek segment the VERY NEXT ``<sp>`` also owns — the English
    edition's own line count runs a beat ahead of the Greek's real speech
    boundary for one line, so the tail of THIS speech and the head of the
    NEXT one collide on one segment (Prometheus Bound 189–195, 279–330,
    332–335, 335–340: every case opens the target segment with the
    outgoing speaker's tail before the incoming speaker's own, correctly
    anchored, turn).  When that collision holds — the piece disagrees with
    the segment's Greek speaker, the piece BEFORE it in the same speech
    agrees with it, and the speech AFTER it starts on that very same
    segment — the tail piece is not a real turn of its own: it belongs
    with the rest of its own speech, one segment back, not with the
    segment its raw number happens to name.

    A genuine multi-span attribution difference (Seven's Herald 1030,
    landing alone with no following speech on the same segment) has no
    colliding successor and is untouched: :func:`_resolve_slice_anchor`
    still flags it in place, as P2j intends.

    Returns ``{(sp_index, n)}`` pairs identifying the tail pieces to
    redirect onto their own speech's PREVIOUS segment instead of their own
    anchor's.
    """
    by_sp: dict[int, list[dict]] = {}
    for job in jobs:
        if job.get("n") is not None:
            by_sp.setdefault(job["sp_index"], []).append(job)
    redirects: set[tuple[int, int]] = set()
    for sp_index, pieces in by_sp.items():
        if len(pieces) < 2:
            continue
        last, prev = pieces[-1], pieces[-2]
        if not last.get("multi_span"):
            continue
        speaker = last.get("canonical")
        if not speaker or speaker != prev.get("canonical"):
            continue
        last_hit = index.segment_for_anchor(last["anchor"])
        prev_hit = index.segment_for_anchor(prev["anchor"])
        if last_hit is None or prev_hit is None:
            continue
        last_seg, _ = last_hit
        prev_seg, _ = prev_hit
        if last_seg["id"] == prev_seg["id"]:
            continue
        last_speaker = index.share_speaker(
            last_seg, last["n"], last["anchor"], prefer=speaker
        )
        if last_speaker is None or last_speaker == speaker:
            continue  # no mismatch -- a legitimate new segment for this speech
        prev_speaker = index.share_speaker(
            prev_seg, prev["n"], prev["anchor"], prefer=speaker
        )
        if prev_speaker != speaker:
            continue  # the "established" piece isn't clean either
        next_pieces = by_sp.get(sp_index + 1)
        if not next_pieces:
            continue
        next_hit = index.segment_for_anchor(next_pieces[0]["anchor"])
        if next_hit is None or next_hit[0]["id"] != last_seg["id"]:
            continue
        redirects.add((sp_index, last["n"]))
    return redirects


_TERMINAL_PUNCTUATION = ".!?…"
# Quotes and brackets an edition closes AFTER the stop, plus the Greek colon.
_TRAILING_MARKS = "\"'’”)]»· "


def _runs_line_for_line(
    jobs: list[dict], index: _SpeechIndex, sp_index: int, n: int, segment: dict
) -> bool:
    """Is this speech's head numbered the very NEXT printed line after the
    last line the PREVIOUS English speech numbered inside ``segment``?

    That is the shape of a translation running line for line with the Greek
    (Coleridge's Hecuba has her 159 and gives 160 to the semi-chorus), and
    where it holds, the head's own number is as trustworthy as any other
    anchor's.  Where the previous speech left printed lines of its own
    unnumbered before this one — its last anchor is two or more lines back,
    or it never anchored in this segment at all — the translation's
    lineation has already parted from the edition's and the number carries
    no such weight.  A head sharing one line with the previous speech (an
    antilabe half, Trachiniae 879a/879b) is not line-for-line either.
    """
    printed = index.printed.get(segment["id"]) or []
    previous = max((j["sp_index"] for j in jobs if j["sp_index"] < sp_index), default=None)
    if previous is None or n not in printed:
        return False
    lines = [
        j["n"]
        for j in jobs
        if j["sp_index"] == previous
        and j.get("anchor") is not None
        and j.get("n") in printed
        and (index.segment_for_anchor(j["anchor"]) or (None,))[0] is not None
        and index.segment_for_anchor(j["anchor"])[0]["id"] == segment["id"]
    ]
    if not lines:
        return False
    return printed.index(n) == printed.index(max(lines)) + 1


def _reads_as_a_continuation(text: str) -> bool:
    """Does this piece read as part of a sentence rather than a whole one?

    True when it begins mid-sentence (its first letter is lowercase) or ends
    without terminal punctuation — the two ways a translator's line shows on
    the page that the sentence runs on past it.
    """
    body = (text or "").strip()
    if not body:
        return False
    first = next((ch for ch in body if ch.isalpha()), "")
    if first and first.islower():
        return True
    return body.rstrip(_TRAILING_MARKS)[-1:] not in ("",) + tuple(
        _TERMINAL_PUNCTUATION
    )


def _multi_span_head_redirects(
    jobs: list[dict], index: _SpeechIndex
) -> dict[tuple[int, int], tuple[str, str]]:
    """C9 (Lane C round 3; trachiniae findings 3, 4, 6): the mirror of
    :func:`_multi_span_tail_redirects`.

    Jebb and Dain-Mazon part company by a line at a speech boundary, so a
    speech's FIRST ``<l n>`` names a line the PREVIOUS Greek speech prints
    while every later anchor of the same ``<sp>`` sits correctly in the next.
    The Old Man's 1017 then printed at the end of Heracles's speech and
    Hyllus's segment opened mid-sentence ("more than mine."); the Chorus's
    881b did the same inside the Nurse's one-line 881, and 879b inside hers
    again at 879.  A speech's own opening clause is not a turn in the
    previous speaker's speech: it belongs at the head of its own turn, with
    the rest of the ``<sp>``.

    The conditions mirror C7's: the head piece disagrees with the Greek
    speaker of the segment its number names, and the NEXT piece of the same
    speech agrees with its own segment.  That layout alone is not enough
    (Sol review of 6e8a9d6, finding 3): it is also exactly what a plain
    attribution difference looks like where the translator gives the
    previous speaker's last line to the incoming one.  Coleridge's Trojan
    Women ``n="160"``, "The rower's hand is busy?", renders Greek 160,
    the second line of Hecuba's couplet — Perseus's own note in the file
    says the line was reassigned in the translation — and moving it took
    Greek 160's only English off Greek 160.

    The extra condition is asked for only where the head's own number is
    worth something, which :func:`_runs_line_for_line` decides: when the
    previous English speech numbered the line immediately before this one
    inside the same Greek speech, the translation is running line for line
    there, and a head that is a whole sentence stays where its number puts
    it, flagged (Trojan Women 160 and 183, Iphigenia in Tauris 116 — all
    three verified against the Greek).  It may still move if its own text
    says it is a continuation: it begins mid-sentence, or ends without
    terminal punctuation, the way a split sentence reads on the page
    ("Speak," / "woman, with what end…"; "As for me" / "whose hair is
    white with age").  Where the previous speech's numbering has already
    parted from the edition's — it left printed lines unnumbered, or the
    two share one line — the number proves nothing and the layout decides
    as before (Oedipus at Colonus 148, Philoctetes 1115 and 1162,
    Persians 1074, Hippolytus 1313, all verified to belong in the speech
    they are moved to).

    Known cost, measured: Ajax 231.  Jebb numbers the Chorus's last piece
    230 and renders 230-232 in it, so the test reads that stretch as line
    for line when it is not, and Tecmessa's opening — which translates
    Greek 233-234 — now stays at the end of the Chorus's block, flagged.
    (The round-3b brief's third signal, the PREVIOUS speech's last piece
    ending unterminated, is deliberately not used: it is evidence about
    that speech's own text, and the one place in the corpus where it would
    fire is Trojan Women 160, where Hecuba's line ends on a dash and the
    move is wrong.)

    The third condition — that the head really is
    sitting inside the PREVIOUS speech's block rather than opening a Greek
    speech of its own — is checked at commit time against the segment that
    speech actually landed on, because the previous speech may itself have
    been moved there by a drift repair (Trojan Women 274, where Coleridge's
    whole exchange from 270 runs a line behind and Talthybius's answer is
    repaired onto 1:274 just before Hecuba's head arrives).

    Returns ``{(sp_index, n): (head segment id, target segment id)}``.
    """
    by_sp: dict[int, list[dict]] = {}
    for job in jobs:
        if job.get("n") is not None and job.get("anchor") is not None:
            by_sp.setdefault(job["sp_index"], []).append(job)
    redirects: dict[tuple[int, int], str] = {}
    for sp_index, pieces in by_sp.items():
        if len(pieces) < 2:
            continue
        head, nxt = pieces[0], pieces[1]
        speaker = head.get("canonical")
        if not speaker or speaker != nxt.get("canonical"):
            continue
        head_hit_early = index.segment_for_anchor(head["anchor"])
        if (
            head_hit_early is not None
            and _runs_line_for_line(jobs, index, sp_index, head["n"], head_hit_early[0])
            and not _reads_as_a_continuation(head.get("text") or "")
        ):
            continue
        head_hit = index.segment_for_anchor(head["anchor"])
        next_hit = index.segment_for_anchor(nxt["anchor"])
        if head_hit is None or next_hit is None:
            continue
        head_seg, next_seg = head_hit[0], next_hit[0]
        if head_seg["id"] == next_seg["id"]:
            continue
        if index.order[next_seg["id"]] <= index.order[head_seg["id"]]:
            continue
        head_speaker = index.share_speaker(
            head_seg, head["n"], head["anchor"], prefer=speaker
        )
        if head_speaker is None or head_speaker == speaker:
            continue  # the head opens a Greek speech of its own; leave it
        next_speaker = index.share_speaker(
            next_seg, nxt["n"], nxt["anchor"], prefer=speaker
        )
        if next_speaker != speaker:
            continue  # the rest of the speech is not cleanly seated either
        redirects[(sp_index, head["n"])] = (head_seg["id"], next_seg["id"])
    return redirects


_UNPRINTED_REF_WINDOW = 3


def _unprinted_ref_seat(
    n: int, speaker: str | None, index: _SpeechIndex
) -> tuple[dict, int] | None:
    """C15 (andromache finding 5, 2026-09-17): the seat for an English line
    whose number the Greek edition does not print.

    Coleridge numbers the Chorus's answer at Andromache 1203; Diggle prints
    no 1203, so the anchor resolved to nothing and the line was dropped —
    fourteen lines across eleven plays, each of them translated text the
    reader never saw.  A number the edition does not print is still a
    number: the line sits between the printed lines that bracket it, and
    the translation's own neighbours say which ones.  So the seat is the
    nearest printed line within a few lines of the number, preferring one
    the Greek gives to this very speaker — every corpus instance has a
    printed neighbour one line away, and the speaker preference is what
    separates the two candidates either side of it (Oedipus Tyrannus 650 is
    Oedipus's and belongs at 651, not at the Chorus's 649).

    Far outside that window there is no neighbour to speak of: Helen's TEI
    numbers one line ``5563``, a typo for 563, and a typo belongs in
    `english.<slot>.line_fixes` (C16), not seated by guesswork at the end
    of the play.  ``None`` then, and the piece keeps its old
    ``unmatched_anchor`` report.

    Round 5, Grok's nit on d348247: two candidates that agree with the
    speaker at the same delta (both one line away, neither preferred by
    speaker) break the tie toward the LOWER line number — the opposite of
    ``_nearest_line``'s snap-forward convention.  No corpus instance reaches
    this exact tie today (every real one is settled by delta or by speaker
    agreement first); the round-4 acceptance test already pins the lower-line
    seat (``1:5``'s unprinted ``7`` files under ``6``, not ``8``), so this
    keeps that verified behaviour rather than flip a convention with no real
    instance to check the flip against.  A genuine corpus tie should get a
    philological read (lineation is Opus's call) before this changes."""
    candidates: list[tuple[int, int, int]] = []
    for delta in range(1, _UNPRINTED_REF_WINDOW + 1):
        for line in (n - delta, n + delta):
            if not index.on_spine(line):
                continue
            hit = index.segment_for_line(line)
            if hit is None:
                continue
            segment, _ref = hit
            agrees = (
                speaker is not None
                and index.speaker_at(segment, line, prefer=speaker) == speaker
            )
            candidates.append((0 if agrees else 1, delta, line))
    if not candidates:
        return None
    _agrees, _delta, line = min(candidates)
    hit = index.segment_for_line(line)
    assert hit is not None
    return hit[0], line


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
    repairable: bool = False,
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
            # C1: a line carrying its own n inside the play's numbering is
            # not drift — only an anchor with outside evidence that its own
            # NUMBER is untrustworthy (see _repairable_anchors) may be
            # repaired onto a nearby same-speaker speech.  Everything else
            # that disagrees with the Greek about its speaker is a real
            # attribution difference and stays put, flagged, below.
            if not multi_span and repairable:
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


_PERSEUS_LINE_NOTE = re.compile(r"^l+\.\s*(\d+)$")


def _between_speech_directions(translation) -> dict[int, list[str]]:
    """C12: Perseus ``<stage>`` elements that sit BETWEEN speeches (a direct
    part of the division rather than of an ``<sp>``) belong before the next
    speech — "Odysseus enters with his attendants." before his own turn.
    Returns ``{sp_index: [direction, ...]}`` for the speech each precedes,
    numbered as :func:`parse_translation` numbers them."""
    out: dict[int, list[str]] = {}
    pending: list[str] = []
    sp_index = 0
    for el in translation.iter():
        tag = local_name(el)
        if tag == "sp":
            sp_index += 1
            if pending:
                out[sp_index] = pending
                pending = []
            continue
        if tag != "stage":
            continue
        if any(local_name(a) == "sp" for a in el.iterancestors()):
            continue
        text = collapse_ws("".join(el.itertext())).strip()
        if text:
            pending.append(text)
    return out


def _perseus_note_anchors(
    translation, aliases: dict[str, str], index: _SpeechIndex
) -> dict[tuple[int, str], str]:
    """C11 (Lane C round 3; suppliants-aesch finding 3): honour a
    ``<note resp="perseus">l. N</note>`` inside an ``<l>`` as that line's
    real anchor.

    Smyth's ``<l n>`` follows one edition's numbering of the Herald scene and
    the spine's another; the Perseus encoders wrote the answer into the text
    as a note, and the converter dropped it with every other non-Smyth note,
    so 905-910 held the neighbouring turn's words in all three columns.

    The note is honoured only where it settles a contest: the spine must give
    the ``<l>``'s OWN number to a different speaker and give the note's
    number to this very speaker.  Suppliants has seven such notes and the
    three at 207-210 name lines whose own slots already agree with their
    speaker — the build is right there — so those are left alone (the
    review's own "gate on agreement rather than applying blindly").

    Returns ``{(sp_index, raw anchor): note anchor}``.
    """
    out: dict[tuple[int, str], str] = {}
    for sp_index, speech in enumerate(translation.findall(".//{*}sp"), start=1):
        el = speech.find("./{*}speaker")
        printed = collapse_ws("".join(el.itertext())).strip() if el is not None else ""
        speaker = _canonical_english(printed, aliases)
        if not speaker:
            continue
        for line in speech.iter("{*}l"):
            raw = line.get("n") or ""
            if not raw.isdigit():
                continue
            target: int | None = None
            for note in line.iter("{*}note"):
                if note.get("resp") != "perseus":
                    continue
                match = _PERSEUS_LINE_NOTE.match(
                    collapse_ws("".join(note.itertext())).strip()
                )
                if match:
                    target = int(match.group(1))
            if target is None or target == int(raw):
                continue
            own = index.segment_for_line(int(raw))
            hit = index.segment_for_line(target)
            if own is None or hit is None:
                continue
            if index.speaker_at(own[0], int(raw), prefer=speaker) == speaker:
                continue  # the line's own number is not contested
            if index.speaker_at(hit[0], target, prefer=speaker) != speaker:
                continue  # the note's number does not belong to this speaker
            out[(sp_index, raw)] = str(target)
    return out


def _ref_order_key(ref: str) -> tuple[int, int, str] | None:
    from .scheme import play_line_order_key

    try:
        return play_line_order_key(ref)
    except (ValueError, TypeError):
        return None


def _transposition_printed_stretches(
    blocks: list[dict], printed_refs: list[str]
) -> tuple[list[tuple[list[int], bool]], list[dict]]:
    """The document-position stretches the declared rows disorder.

    A ``citation.transpositions`` row records that the run ``start``-``end``
    is printed AFTER the higher-numbered ``before`` — the block-derivation
    in ``stage1_greek._derive_play_line_transposed_blocks`` writes it that
    way.  The stretch the row disorders therefore begins at the first ref
    printed out of numeric turn (everything from ``end``+1 through
    ``before``, which the edition prints early) and ends at ``end``.  That
    is read off the spine's own printed sequence rather than reconstructed
    by arithmetic on the bounds, so a lettered or hyphenated bound (Bacchae
    ``148b``/``1448a``, Orestes ``1488b``, Rhesus ``678-679``) is an
    ordinary ref like any other instead of an ``int()`` that fails silently
    (G4).

    Rows whose stretches overlap describe ONE permutation and are merged:
    Seven's ``{984,992,before:993}`` and ``{983,983,before:993}`` are the
    single printed rotation 993, 984-992, 983, not two rotations to fold
    into one dict, last write winning (G4).

    Returns the merged stretches — each a list of document positions with
    the flag saying whether a row declared ``english_keyed: printed`` over
    it — and the rows that yielded none, each with its reason.
    """
    anomalies: list[dict] = []
    positions: dict[str, list[int]] = {}
    for i, ref in enumerate(printed_refs):
        positions.setdefault(ref, []).append(i)

    stretches: list[tuple[list[int], bool]] = []
    for block in blocks:
        row = {
            "start": block.get("start"),
            "end": block.get("end"),
            "before": block.get("before"),
        }
        forced = block.get("english_keyed") == "printed"
        starts = positions.get(row["start"] or "")
        ends = positions.get(row["end"] or "")
        end_key = _ref_order_key(row["end"]) if isinstance(row["end"], str) else None
        if not starts or not ends or end_key is None:
            anomalies.append(
                {
                    "kind": "transposition_remap_skipped",
                    "reason": "bound_off_spine",
                    "block": row,
                }
            )
            continue
        first = starts[0]
        last = next((p for p in ends if p >= first), None)
        if last is None:
            anomalies.append(
                {
                    "kind": "transposition_remap_skipped",
                    "reason": "bound_off_spine",
                    "block": row,
                }
            )
            continue
        head = first
        while head > 0:
            key = _ref_order_key(printed_refs[head - 1])
            if key is None or key <= end_key:
                break
            head -= 1
        span = list(range(head, last + 1))
        if not any(printed_refs[p] == row["before"] for p in span):
            # The row's own "before" anchor is not among the refs printed
            # early in this stretch, so the row does not describe a simple
            # rotation of one contiguous printed run (Bacchae's 847-1392
            # row, whose `before` 1448a sits 700 lines earlier).
            anomalies.append(
                {
                    "kind": "transposition_remap_skipped",
                    "reason": "before_outside_printed_stretch",
                    "block": row,
                }
            )
            continue
        stretches.append((span, forced))

    stretches.sort(key=lambda item: (item[0][0], item[0][-1]))
    merged: list[tuple[list[int], bool]] = []
    for span, forced in stretches:
        if merged and span[0] <= merged[-1][0][-1]:
            prev, prev_forced = merged[-1]
            if prev_forced != forced:
                # Grok's read of 134dbe0: the merge used to OR the flag, so
                # one declaring row forced printed keying over rows that never
                # asked for it.  Number keying is the default and printed the
                # exception; a merged stretch whose rows disagree is a
                # manifest the author has to settle, not a silent promotion.
                raise ValueError(
                    "citation.transpositions: overlapping rows over one "
                    f"printed stretch (positions {min(prev[0], span[0])}-"
                    f"{max(prev[-1], span[-1])}) disagree about english_keyed "
                    "— declare it on every row of the stretch or on none"
                )
            merged[-1] = (
                list(range(min(prev[0], span[0]), max(prev[-1], span[-1]) + 1)),
                forced,
            )
            continue
        merged.append((span, forced))
    return merged, anomalies


def _printed_keying_disagreements(
    index: _SpeechIndex,
    english_speakers: dict[int, str | None],
    pairs: list[tuple[int, int]],
) -> int:
    """How many of ``pairs`` (English base → Greek ref number) put an
    English speech on a Greek line the edition gives to somebody else."""
    bad = 0
    for base, target in pairs:
        speaker = english_speakers.get(base)
        if not speaker:
            continue
        hit = index.segment_for_anchor(str(target))
        if hit is None:
            continue
        segment, _ref = hit
        greek = index.share_speaker(segment, target, str(target), prefer=speaker)
        if greek is not None and greek != speaker:
            bad += 1
    return bad


def _transposition_anchor_remap(
    blocks: list[dict],
    printed_refs: list[str],
    english_bases: set[int],
    index: _SpeechIndex | None = None,
    english_speakers: dict[int, str | None] | None = None,
) -> tuple[dict[int, int], list[dict]]:
    """C4/S1: map a translation's own line number, inside a printed stretch
    a ``citation.transpositions`` row disorders, to the Greek ref that
    occupies the SAME printed position in the edition.

    Perseus's own ``<l n>`` always runs in plain ascending numeric order —
    it is not itself transposed, whichever edition backs the Greek spine.
    Oedipus at Colonus declares ``{start: "328", end: "328", before:
    "330"}``: printed order for 328-330 is 329, 330, 328, so Jebb's own
    328th/329th/330th anchors (numbered 328, 329, 330, in that order) must
    seat at Greek refs 329, 330, 328 respectively — the ref at the SAME
    printed position, not the ref with the same digits.

    S1 (the bare-segment data sweep, 2026-09-17): that premise holds only
    when the translation really does print one line per printed Greek line
    across the stretch.  Coleridge's Andromache gives the couplet 70+71 a
    single ``<l n="70">``, so the stretch's four printed refs (73, 70, 71,
    72) carry three anchors; remapping anyway sends ``n="70"`` to ref 73,
    invents a numeric drop that satisfies Rule A, and the repair cascades
    onto an already-filled neighbour.  So the map is built only when the
    distinct base numbers of the translation's anchors inside the stretch's
    numeric range are EXACTLY the stretch's own refs, one for one.
    Otherwise the anchors keep their numbers and the skip is reported.

    A declared row means one of two things, and which one is a per-play data
    call the Greek's own speaker attributions are only EVIDENCE for.  Either
    the two editions NUMBER the same verses differently, and then the
    translation's nth line in the stretch is the edition's nth printed line
    (OC 328-330: Jebb renumbers his transposed verse, Dain-Mazon keeps the
    vulgate's number).  Or both number the verses alike and only the printed
    ORDER differs, and then the anchor's own number is already right (Hecuba
    758/759, Iphigenia at Aulis 653-665, Iphigenia in Tauris 1050/1051,
    Phoenician Women 1747-1749, Rhesus 334-338 — in each, re-keying by
    printed position moves every line onto a speech the edition gives to the
    other character).

    The numbers are the default, and printed position has to earn the
    stretch: the remap fires only where it scores STRICTLY FEWER speaker
    disagreements than leaving the anchors alone.  A TIE — a stichomythia
    whose characters alternate the same way under either keying, so the
    attributions cannot tell the readings apart — stands down too (Sol
    review of 6e8a9d6, finding 1).  The corpus is 14 tie stretches where the
    content says the numbers are right (hippolytus 104-107, where Coleridge's
    ``n="104"`` translates Greek 104, and 13 more) against one where printed
    position is right and verified (OC 328-330), so guessing on a tie loses
    fourteen times to win once.

    A row may instead DECLARE the reading, with ``english_keyed: printed``,
    and then it is honoured whatever the speaker count says — a verified
    manifest declaration outranks an inference from the attributions (the
    same precedence a hand-written ``speakers.overrides`` entry has over the
    synthesized one).  Only the one-for-one anchor guard above still applies
    to a declared row: where the translation does not print one line per
    printed Greek line, position keying has nothing to mean.
    """
    stretches, anomalies = _transposition_printed_stretches(blocks, printed_refs)
    remap: dict[int, int] = {}
    for span, forced in stretches:
        span_refs = [printed_refs[p] for p in span]
        printed_bases = [_anchor_base(_ref_root(ref)) for ref in span_refs]
        detail = {
            "kind": "transposition_remap_skipped",
            "printed": span_refs,
        }
        if len(set(printed_bases)) != len(printed_bases):
            anomalies.append({**detail, "reason": "printed_stretch_repeats_a_number"})
            continue
        numeric_bases = sorted(printed_bases)
        lo, hi = numeric_bases[0], numeric_bases[-1]
        observed = {base for base in english_bases if lo <= base <= hi}
        if observed != set(numeric_bases):
            anomalies.append(
                {
                    **detail,
                    "reason": "anchors_not_one_per_printed_line",
                    "expected": numeric_bases,
                    "observed": sorted(observed),
                }
            )
            continue
        pairs = [
            (numeric, printed)
            for numeric, printed in zip(numeric_bases, printed_bases)
            if numeric != printed
        ]
        if not pairs:
            continue  # the permutation moves no number: nothing to key either way
        if not forced:
            if index is None or not english_speakers:
                anomalies.append({**detail, "reason": "printed_keying_unevidenced"})
                continue
            by_number = _printed_keying_disagreements(
                index, english_speakers, [(base, base) for base, _ in pairs]
            )
            by_printed = _printed_keying_disagreements(index, english_speakers, pairs)
            if by_printed >= by_number:
                anomalies.append(
                    {
                        **detail,
                        "reason": (
                            "printed_keying_contradicted_by_greek_speakers"
                            if by_printed > by_number
                            else "printed_keying_not_favoured_by_greek_speakers"
                        ),
                        "disagreements": {"by_number": by_number, "by_printed": by_printed},
                    }
                )
                continue
        remap.update(dict(pairs))
    return remap, anomalies


def _ref_root(ref: str) -> str:
    """The plain number a printed ref is keyed by (``709-710`` → ``709``,
    ``post 42`` → ``42``, ``148b`` → ``148b``)."""
    if ref.startswith("post ") and ref[5:].isdigit():
        return ref[5:]
    if "-" in ref:
        head = ref.split("-", 1)[0]
        if head.isdigit():
            return head
    return ref


def _remap_anchor(anchor: str, remap: dict[int, int]) -> str:
    """Apply :func:`_transposition_anchor_remap` to one raw anchor string,
    preserving a lettered anchor's own share suffix (``329a`` -> ``330a``
    when 329 remaps to 330).

    A repeated-ref seat (``810.2``) is left as written. Its base counts as
    810 wherever a stretch does arithmetic, but the k-th printing is the
    seat the line_fix named and a rotation must not move it onto another
    ref's printing."""
    if not remap or _repeated_seat(anchor) is not None:
        return anchor
    lettered = _LETTERED_ANCHOR.fullmatch(anchor)
    if lettered:
        base = int(lettered.group(1))
        if base not in remap:
            return anchor
        return f"{remap[base]}{anchor[len(lettered.group(1)):]}"
    if anchor.isdigit():
        base = int(anchor)
        return str(remap.get(base, base))
    return anchor


def _apply_line_fixes(
    translation,
    line_fixes: dict | None,
    work_id: str,
    index: _SpeechIndex,
    repeated_refs: dict | None,
) -> None:
    """C16 (iphigenia-in-tauris finding 5, 2026-09-17): rewrite a TEI line
    number the translation mistypes, before anything reads it.

    Perseus files Thoas's 1188 under ``n="188"``, and the bare number filed
    it a thousand lines early, at the end of the Chorus's parodos, with a
    Thoas turn inside the Chorus's ode; the manifest then declared `1:1188`
    a gap, recording the bug as a hole.  ``english.<slot>.line_fixes:
    {"188": "1188"}`` is the per-play declaration that this is a typo, and
    it is applied to the parsed tree so every later reader — the anchor
    pre-scan the transposition remap works from, the slices, the Perseus
    line notes — sees one number.  A key that matches no line, or more than
    one, is itself a typo and raises.

    A value ``"<ref>.<k>"`` (k >= 2) names the k-th printing of a ref in
    ``citation.repeated_refs``, the segment the build already calls
    ``1:<ref>.<k>``.  Those elements are marked with a private attribute,
    because lxml's Python identity is not stable across walks, and the
    walker accepts the form only on a marked element: a raw TEI ``<l n>``
    of the same shape stays a non-numeric anchor.  A value whose ref is not
    declared, or which asks for a printing the spine does not have, raises
    naming ``line_fixes`` and the value — a stale fix must not drop the
    sentence.

    Each rewritten element is marked ``_LINE_FIXED``: the placement of that
    line is the manifest's own reading of the Greek, which no speaker
    heuristic may move (Seven 996-1004)."""
    if not line_fixes:
        return
    if not isinstance(line_fixes, dict):
        raise ValueError(f"{work_id}: english line_fixes must be a map of TEI n -> n")
    wanted = {str(k): str(v) for k, v in line_fixes.items()}
    hits: dict[str, int] = {key: 0 for key in wanted}
    for line in list(translation.iter("{*}l")):
        raw = line.get("n")
        if raw in wanted:
            hits[raw] += 1
            line.set("n", wanted[raw])
            line.set(_LINE_FIXED, "1")
            if _repeated_seat(wanted[raw]) is not None:
                line.set(_LINE_FIX_SEAT, "1")
    wrong = {key: count for key, count in hits.items() if count != 1}
    if wrong:
        raise ValueError(
            f"{work_id}: english line_fixes {wrong!r} — each key must name "
            "exactly one <l n> in the translation"
        )
    declared = {str(k): int(v) for k, v in (repeated_refs or {}).items()}
    for line in list(translation.iter("{*}l")):
        if line.get(_LINE_FIX_SEAT) != "1":
            continue
        raw = line.get("n") or ""
        seat = _repeated_seat(raw)
        if seat is None:
            continue
        ref, k = seat
        if ref not in declared:
            raise ValueError(
                f"{work_id}: english line_fixes value {raw!r} names printing "
                f"{k} of ref {ref!r}, which is not declared in "
                "citation.repeated_refs"
            )
        printed = len(index.by_ref.get(ref) or [])
        have = min(printed, declared[ref])
        if have < k:
            raise ValueError(
                f"{work_id}: english line_fixes value {raw!r} names printing "
                f"{k} of ref {ref!r}, but only {have} printing(s) exist"
            )


_ANCHOR_WINDOW = 3          # lines either side of the mapped line an anchor may move
_ANCHOR_SPEAKER_COST = 10.0
_ANCHOR_MOVE_COST = 1.0
_ANCHOR_SHARE_COST = 2.0     # a speech opens on a line where its speaker only speaks the second half
_ANCHOR_BACK_COST = 3.0      # an anchor seated before the one ahead of it (a transposed stretch)


def _apply_anchor_map(
    translation,
    mapping: dict[str, str],
    inferred: set[str],
    target_order: list[str],
    source_id: str,
    index: "_SpeechIndex",
    aliases: dict[str, str],
) -> dict:
    """Rewrite each ``<l n>`` from the count of ``source_id``'s Greek to this
    spine's count (``english.<slot>.anchor_map``; see ``anchor_map.py``).

    The text gives each anchor a line (its ``mapped`` line). Perseus numbers
    its English by its own lines, though, which agree with the source Greek's
    count in some stretches and drift from it in others (an English speech of
    two lines over one Greek line shifts every number after it). So each
    anchor may sit up to ``_ANCHOR_WINDOW`` lines from its mapped line, where
    that seats its speaker on a line the speaker speaks: the anchors, in
    document order, take the seats of least cost, and seating one before the
    one ahead of it costs too. Moving from the mapped line costs a little, and a seat the
    English speaker does not speak costs much, so an anchor stays on its
    mapped line unless its speaker forces it off. An anchor the text gives no
    line for keeps its own number, is listed under ``unmatched``, and seats
    where that number is a line of this spine. A line
    ``line_fixes`` already rewrote stays as the manifest put it. Returns the
    report block."""
    from .anchor_map import remap_anchor

    target_refs = set(target_order)
    position = {ref: i for i, ref in reversed(list(enumerate(target_order)))}
    counts = {"anchors": 0, "direct": 0, "inferred": 0, "moved": 0, "kept": 0,
              "off_mapped_line": 0, "present_before": 0, "present_after": 0}
    unmatched: list[str] = []
    moved: list[dict] = []
    speaker_cache: dict[tuple[str, str | None], str | None] = {}

    def speaker(ref: str, prefer: str | None) -> str | None:
        key = (ref, prefer)
        if key not in speaker_cache:
            found = index.segment_for_anchor(ref)
            who = None
            if found is not None:
                segment, printed = found
                number = _anchor_base(printed)
                who = index.speaker_at(segment, number, prefer=prefer)
                # A segment with no speaker event goes on with the speech before it.
                at = index.order[segment["id"]]
                while who is None and at > 0:
                    at -= 1
                    before = index.segments[at]
                    printed_lines = index.printed.get(before["id"]) or []
                    if printed_lines:
                        who = index.speaker_at(before, printed_lines[-1], prefer=prefer)
            speaker_cache[key] = who
        return speaker_cache[key]

    seats: list[dict] = []
    for speech in translation.iter("{*}sp"):
        label = speech.find("./{*}speaker")
        name = collapse_ws("".join(label.itertext())).strip() if label is not None else ""
        canonical = _canonical_english(name, aliases)
        opens = True
        for line in speech.iter("{*}l"):
            raw = line.get("n") or ""
            if not (raw.isdigit() or _LETTERED_ANCHOR.fullmatch(raw)) or line.get(_LINE_FIXED) == "1":
                continue
            if raw.isdigit() and int(raw) == 0:
                continue
            opening, opens = opens, False
            counts["anchors"] += 1
            counts["present_before"] += raw in target_refs
            mapped = remap_anchor(raw, mapping, target_refs)
            if mapped is None or mapped not in position:
                unmatched.append(raw)
                counts["present_after"] += raw in target_refs
                if raw in position:     # keeps its number, and still bounds its neighbours
                    seats.append({"line": line, "raw": raw, "mapped": raw, "speaker": canonical, "opens": opening, "fixed": True})
                continue
            counts["inferred" if raw in inferred else "direct"] += 1
            seats.append({"line": line, "raw": raw, "mapped": mapped, "speaker": canonical, "opens": opening})

    # Least-cost seating, anchors in document order, seats never going back.
    last = len(target_order) - 1
    table: list[dict[int, tuple[float, int | None]]] = []
    for seat in seats:
        base = position[seat["mapped"]]
        options: dict[int, float] = {}
        reach = 0 if seat.get("fixed") else _ANCHOR_WINDOW
        for at in range(max(0, base - reach), min(last, base + reach) + 1):
            cost = 0.0 if at == base else _ANCHOR_MOVE_COST + 0.5 * abs(at - base)
            if seat["speaker"] and speaker(target_order[at], seat["speaker"]) != seat["speaker"]:
                cost += _ANCHOR_SPEAKER_COST
            elif seat["speaker"] and seat["opens"] and speaker(target_order[at], None) != seat["speaker"]:
                cost += _ANCHOR_SHARE_COST
            options[at] = cost
        row: dict[int, tuple[float, int | None]] = {}
        previous = table[-1] if table else None
        for at, cost in options.items():
            if previous is None:
                row[at] = (cost, None)
                continue
            best = min(
                ((total + (0.0 if before <= at else _ANCHOR_BACK_COST), before) for before, (total, _) in previous.items()),
                key=lambda item: (item[0], -item[1]),
            )
            row[at] = (cost + best[0], best[1])
        table.append(row)
    chosen: list[int] = []
    if table:
        at = min(table[-1], key=lambda k: (table[-1][k][0], abs(k - position[seats[-1]["mapped"]])))
        chosen.append(at)
        for row in reversed(table[1:]):
            at = row[at][1]
            chosen.append(at)
        chosen.reverse()
    for seat, at in zip(seats, chosen):
        if seat.get("fixed"):
            continue
        new = target_order[at]
        counts["off_mapped_line"] += new != seat["mapped"]
        counts["present_after"] += new in target_refs
        if new == seat["raw"]:
            counts["kept"] += 1
            continue
        counts["moved"] += 1
        moved.append({"from": seat["raw"], "to": new})
        seat["line"].set("n", new)
    return {
        "source_edition": source_id,
        **counts,
        "unmatched": unmatched,
        "moved_anchors": moved,
    }


def _anchor_map_from(manifest: Manifest, cfg: dict, spine: dict) -> tuple[dict, set, list, str]:
    """The map ``cfg["anchor_map"]`` declares, built from the named edition's
    Greek against this edition's spine."""
    from . import stage1_tei_greek
    from .anchor_map import build_anchor_map

    source_id = cfg["anchor_map"]
    view = (getattr(manifest, "anchor_editions", None) or {}).get(source_id)
    if view is None:
        raise ValueError(f"{manifest.work_id}: anchor_map {source_id!r} names no declared Greek edition")
    source_spine = stage1_tei_greek.parse_spine(
        SOURCES_DIR / view.data["work"]["greek_source"]["path"], view
    )

    def lines(sp: dict) -> list[dict]:
        return [line for seg in sp["segments"] for line in seg["lines"]]

    target = lines(spine)
    mapping, inferred = build_anchor_map(lines(source_spine), target)
    order = []
    for line in target:
        order.append(line["ref"])
        order += [part["ref"] for part in line.get("parts") or []]
    return mapping, inferred, order, source_id


def _apply_cuts(translation, cuts: list[dict] | None, work_id: str, index: _SpeechIndex) -> None:
    """Mark exact, unique words within one numbered TEI line for a new Greek seat."""
    if not cuts:
        return
    if not isinstance(cuts, list):
        raise ValueError(f"{work_id}: english.primary.cuts must be a list")
    lines = list(translation.iter("{*}l"))
    by_line: dict[int, list[tuple[int, str]]] = {}
    for cut in cuts:
        ref = str(cut.get("greek", "")) if isinstance(cut, dict) else ""
        words = str(cut.get("english", "")) if isinstance(cut, dict) else ""
        hits = [
            (i, _line_plain_text(line).find(words))
            for i, line in enumerate(lines)
            if words and line.get("n") and _line_plain_text(line).count(words)
        ]
        if (not _numbered_anchor(ref) or index.segment_for_anchor(ref) is None
                or sum(_line_plain_text(lines[i]).count(words) for i, _ in hits) != 1):
            raise ValueError(f"{work_id}: stale english.primary.cuts ref {ref!r}, words {words!r}: expected exactly one match in a numbered <l> and a usable Greek ref")
        i, position = hits[0]
        # The cut path slices the line's plain text; a note or milestone
        # inside it would be dropped, so a marked-up line is refused.
        if any(isinstance(child.tag, str) for child in lines[i]):
            raise ValueError(f"{work_id}: english.primary.cuts ref {ref!r}: <l n={lines[i].get('n')!r}> carries markup, which a cut would drop")
        by_line.setdefault(i, []).append((position, ref))
    for i, entries in by_line.items():
        entries.sort()
        if len({position for position, _ in entries}) != len(entries):
            raise ValueError(f"{work_id}: overlapping english.primary.cuts in <l n={lines[i].get('n')!r}>")
        lines[i].set(_LINE_CUTS, json.dumps(entries))


def parse_translation(
    xml_path: Path,
    spine: dict,
    *,
    work_id: str,
    translation_id: str,
    sigla: dict | None = None,
    english_aliases: dict[str, str] | None = None,
    covered_decl: list[dict] | None = None,
    transpositions: list[dict] | None = None,
    line_fixes: dict | None = None,
    cuts: list[dict] | None = None,
    repeated_refs: dict | None = None,
    anchor_map: tuple[dict, set, list, str] | None = None,
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
    _apply_line_fixes(translation, line_fixes, work_id, index, repeated_refs)
    anchor_map_report = _apply_anchor_map(translation, *anchor_map, index, aliases) if anchor_map else None
    _apply_cuts(translation, cuts, work_id, index)
    cut_refs = {str(c["greek"]) for c in (cuts or [])}
    cut_refs.update(
        line.get("n") for line in translation.iter("{*}l") if line.get(_LINE_CUTS)
    )
    chunks_by_id: dict[str, dict] = {}
    footnotes: dict[str, str] = {}
    snaps: list[dict] = []
    mismatches: list[dict] = []
    anomalies: list[dict] = []
    # S1/G4: the remap is decided against the spine's own printed order and
    # against every anchor the translation prints, so both have to be in
    # hand before the first speech is sliced.
    printed_refs = [
        line["ref"]
        for segment in index.segments
        for line in (segment.get("lines") or [])
        if isinstance(line.get("ref"), str)
    ]
    english_bases: set[int] = set()
    english_speakers: dict[int, str | None] = {}
    for speech in translation.findall(".//{*}sp"):
        el = speech.find("./{*}speaker")
        name = collapse_ws("".join(el.itertext())).strip() if el is not None else ""
        canonical_name = _canonical_english(name, aliases)
        for line in speech.iter("{*}l"):
            raw = line.get("n") or ""
            authorized_seat = (
                line.get(_LINE_FIX_SEAT) == "1" and _repeated_seat(raw) is not None
            )
            if raw.isdigit() or _LETTERED_ANCHOR.fullmatch(raw) or authorized_seat:
                base = _anchor_base(raw)
                english_bases.add(base)
                english_speakers.setdefault(base, canonical_name)
    anchor_remap, remap_anomalies = _transposition_anchor_remap(
        transpositions or [],
        printed_refs,
        english_bases,
        index,
        english_speakers,
    )
    anomalies.extend(remap_anomalies)
    note_anchors = _perseus_note_anchors(translation, aliases, index)
    between_directions = _between_speech_directions(translation)
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
        tick: bool = True,
    ) -> dict | None:
        chunk = ensure_chunk(segment)
        text = _inline_directions(text)
        if chunk["text"] and not (
            chunk["text"].endswith("\n") or text.startswith("\n")
        ):
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
        if tick:
            chunk["bekker"].append({"n": tick_n, "offset": offset, "real": True})
        chunk["text"] += text
        return turn

    jobs: list[dict] = []
    directions_pending: dict[int, list[str]] = {}
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
        own_tick=True,
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
            tick=own_tick,
        )
        if job["printed"] and not already:
            turns_emitted[turn_key] = turn
        # C12: the directions that precede this speech go on its FIRST turn.
        if turn is not None and directions_pending.get(job["sp_index"]):
            turn["directionsBefore"] = directions_pending.pop(job["sp_index"])
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
        head_directions = list(between_directions.get(sp_index) or [])
        slices = _iter_speech_slices(
            speech,
            split=split,
            text_parser=text_parser,
            anomalies=anomalies,
            sp_index=sp_index,
            printed=printed,
            head_directions=head_directions,
        )
        if head_directions:
            directions_pending[sp_index] = head_directions
        # G3: the number the TEI PRINTED, kept per piece before C4 rewrites
        # it, so Rule A's inversion test reads the translation's own
        # sequence and not the rotation the remap just performed.
        raw_anchors = [[anchor for anchor, _part in sl.pieces] for sl in slices]
        if note_anchors:
            # C11: a `<note resp="perseus">l. N</note>` that settles a
            # contested line names this piece's real Greek seat.
            for sl in slices:
                sl.pieces = [
                    (
                        note_anchors.get((sp_index, piece_anchor), piece_anchor)
                        if piece_anchor is not None
                        else piece_anchor,
                        piece_text,
                    )
                    for piece_anchor, piece_text in sl.pieces
                ]
        if anchor_remap:
            # C4: re-key every anchor in this speech before anything reads
            # it — multi-span detection, the job's own tick, and the Greek
            # lookup all have to agree on the SAME (remapped) ref.
            for sl in slices:
                sl.pieces = [
                    (
                        _remap_anchor(piece_anchor, anchor_remap)
                        if piece_anchor is not None
                        else piece_anchor,
                        piece_text,
                    )
                    for piece_anchor, piece_text in sl.pieces
                ]
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
        for slice_index, sl in enumerate(slices):
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
            piece_ns = [pn for pn, _pt in sl.pieces]
            for piece_index, (piece_n, piece_text) in enumerate(sl.pieces):
                piece = collapse_ws(piece_text).strip()
                if not piece:
                    continue
                raw_piece = raw_anchors[slice_index][piece_index]
                raw_source = raw_piece if raw_piece is not None else (
                    _nearest_piece_anchor(raw_anchors[slice_index], piece_index)
                )
                # A piece with no anchor of its own seats beside its nearest
                # NEIGHBOUR in the slice, not the slice's first anchor: one
                # before the first `<l n>` (a paragraph opened mid-line)
                # takes the next line's number, no tick, so the reader
                # interpolates (Agamemnon 8 sat at 10; John, 2026-09-12); a
                # mid-speech `<stage>` between two `<l>` siblings likewise
                # takes the FOLLOWING line's number and prints before its
                # text, and one after the speech's last `<l>` takes the
                # PRECEDING line's number and prints after it (Sol's
                # integration review, finding 1, 2026-09-18).
                resolved_anchor = (
                    piece_n
                    if piece_n is not None
                    else _nearest_piece_anchor(piece_ns, piece_index)
                )
                jobs.append(
                    {
                        "n": _anchor_base(resolved_anchor),
                        "raw_n": _anchor_base(raw_source) if raw_source else None,
                        "line_fixed": sl.fixed[piece_index],
                        "anchor": resolved_anchor,
                        "own_tick": piece_n is not None,
                        "text": piece,
                        "printed": printed,
                        "canonical": canonical,
                        "speech_anchors": speech_anchors,
                        "sp_index": sp_index,
                        "speakerless": not printed,
                        "multi_span": multi_span,
                    }
                )

    anchored_segments = {
        hit[0]["id"]
        for hit in (
            index.segment_for_anchor(job["anchor"])
            for job in jobs
            if job.get("anchor") is not None
        )
        if hit is not None
    }
    repairable_anchors = _repairable_anchors(jobs, index)
    repeat_positions = _repeat_lettered_positions(jobs)
    antilabe_overrides = _antilabe_reassignments(
        jobs, index, transpositions=transpositions, printed_refs=printed_refs
    )
    tail_redirects = _multi_span_tail_redirects(jobs, index)
    head_redirects = _multi_span_head_redirects(jobs, index)
    prev_assigned: dict[int, str] = {}
    last_commit: tuple[int, str] | None = None
    for pos, job in enumerate(jobs):
        n = job["n"]
        # An explicit ``<ref>.<k>`` seat stays on the printing it names.
        # Repair, antilabe reassignment, and the head/tail redirects all
        # move a piece by its integer, which would collapse 810.2 onto 810.
        explicit_seat = _repeated_seat(job.get("anchor") or "") is not None
        # A line a line_fixes entry seats stays there too: the speaker
        # repair and the antilabe walk would move it by speaker, and the fix
        # already read the Greek (Seven 996-1004, where Smyth gives each line
        # to the other sister).
        fixed_seat = explicit_seat or job.get("line_fixed", False)
        if n is not None:
            anchor_count += 1
        if pos in repeat_positions:
            # C2: a lettered anchor whose own text is a verbatim printed
            # repeat of its base's earlier occurrence (Eumenides 372a/375a)
            # contributes nothing new -- skip it exactly as a stage
            # direction is skipped, rather than write the sentence twice.
            continue
        if pos in antilabe_overrides and not fixed_seat:
            # C6: position, not number, decided this piece's home.
            segment, printed_line = antilabe_overrides[pos]
            commit_job(job, segment, printed_line)
            prev_assigned[job["sp_index"]] = job["assigned"]
            continue
        head_redirect = head_redirects.get((job["sp_index"], n)) if n is not None else None
        if (
            head_redirect is not None
            and not explicit_seat
            and not (job.get("line_fixed") and job["anchor"] in cut_refs)
            and last_commit is not None
            and last_commit[0] < job["sp_index"]
            and last_commit[1] == head_redirect[0]
        ):
            # C9/C10: this piece opens its own speech; its number merely
            # lands inside the block the previous speech has just filled.
            # Seat it at the head of the segment the rest of the speech
            # occupies.
            target = index.by_id[head_redirect[1]]
            printed = index.printed.get(target["id"]) or []
            commit_job(job, target, printed[0] if printed else n)
            prev_assigned[job["sp_index"]] = job["assigned"]
            last_commit = (job["sp_index"], job["assigned"])
            continue
        if (
            n is not None
            and not explicit_seat
            and not (job.get("line_fixed") and job["anchor"] in cut_refs)
            and (job["sp_index"], n) in tail_redirects
        ):
            # C7: this piece is the tail of its OWN speech, displaced onto
            # the next speech's segment by a one-line collision; it belongs
            # with the rest of its own speech, one segment back.
            prev_id = prev_assigned.get(job["sp_index"])
            if prev_id is not None:
                commit_job(job, index.by_id[prev_id], n, add_turn=False, own_tick=False)
                prev_assigned[job["sp_index"]] = prev_id
                last_commit = (job["sp_index"], job["assigned"])
                continue
        if n is None:
            prev_id = prev_assigned.get(job["sp_index"])
            if prev_id is None:
                anomalies.append(
                    {"kind": "nless_slice_unattached", "sp": job["sp_index"]}
                )
                continue
            prev_order = index.order[prev_id]
            nxt = prev_order
            if job["speakerless"] and prev_order + 1 < len(index.segments):
                # A speakerless <sp> is split at each para milestone so
                # Agamemnon's packed elders (1348-1371), the Eumenides
                # Furies' short strophic units and Seven's sisters' kommos
                # each take the next Greek speech in turn.  C9 (trachiniae
                # finding 5): a paragraph may take that next speech only if
                # the next speech has no English of its own.  Heracles's
                # dying speech is one speakerless <sp> with paragraph breaks
                # inside <l n="1080"> and <l n="1105">, and the Chorus's
                # couplet after it carries its own <l n="1112"> — so those
                # two blocks were flushed into the Chorus's turn and his own
                # speech was left spliced.  A paragraph is part of the
                # speech it is printed in unless there is an empty Greek
                # speech waiting for it.
                if index.segments[prev_order + 1]["id"] not in anchored_segments:
                    nxt = prev_order + 1
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
            # The segment's first line is a true start only for a piece that
            # opens the chunk; mid-chunk it ran backwards (Agamemnon 1@1081).
            opens = not (chunks_by_id.get(segment["id"]) or {}).get("text")
            commit_job(job, segment, tick_n, snap=snap, own_tick=opens)
            prev_assigned[job["sp_index"]] = segment["id"]
            last_commit = (job["sp_index"], job["assigned"])
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
            repairable=pos in repairable_anchors and not fixed_seat,
        )
        if result is None:
            seat = _unprinted_ref_seat(n, job["canonical"], index)
            if seat is None:
                anomalies.append(
                    {
                        "kind": "unmatched_anchor",
                        "sp": job["sp_index"],
                        "n_raw": job["anchor"],
                    }
                )
                continue
            # C15: the edition does not print this number, so the piece takes
            # no tick of its own unless it opens the chunk -- it must not
            # claim a line the Greek never printed.
            segment, seat_line = seat
            opens = not (chunks_by_id.get(segment["id"]) or {}).get("text")
            anomalies.append(
                {
                    "kind": "unprinted_ref",
                    "sp": job["sp_index"],
                    "n_raw": job["anchor"],
                    "attached_to": segment["id"],
                    "ref": index.closest_ref(segment, seat_line),
                }
            )
            commit_job(job, segment, seat_line, own_tick=opens)
            prev_assigned[job["sp_index"]] = job["assigned"]
            last_commit = (job["sp_index"], job["assigned"])
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
            own_tick=job["own_tick"],
        )
        prev_assigned[job["sp_index"]] = job["assigned"]
        last_commit = (job["sp_index"], job["assigned"])

    chunks = [
        chunks_by_id[segment["id"]]
        for segment in spine["segments"]
        if segment["id"] in chunks_by_id
    ]
    for chunk in chunks:
        # Item 8: a chunk whose last piece is a stage direction ends on the
        # newline that closes the direction's own line; trim it, and keep any
        # offset that pointed past the new end inside the text.
        trimmed = chunk["text"].rstrip()
        if trimmed != chunk["text"]:
            chunk["text"] = trimmed
            for mark in chunk["bekker"]:
                mark["offset"] = min(mark["offset"], len(trimmed))
            for turn in chunk["turns"]:
                turn["offset"] = min(turn["offset"], len(trimmed))
        # Round 5 finding 1: a mid-speech `<stage>` between `<l>` siblings now
        # seats beside the FOLLOWING line and can open its chunk, leaving the
        # newline that opens the direction's own line with nothing before
        # it; trim that leading newline the same way the trailing one above
        # is trimmed, shifting every offset back by what was removed.
        leading = chunk["text"].lstrip("\n")
        if leading != chunk["text"]:
            removed = len(chunk["text"]) - len(leading)
            chunk["text"] = leading
            for mark in chunk["bekker"]:
                mark["offset"] = max(0, mark["offset"] - removed)
            for turn in chunk["turns"]:
                turn["offset"] = max(0, turn["offset"] - removed)
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
    if anchor_map_report is not None:
        report["anchor_map"] = anchor_map_report
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


def _repeated_ref_counts(manifest: Manifest) -> dict[str, int]:
    """``citation.repeated_refs`` for book 1, as ``{ref: count}``."""
    decl = ((manifest.data.get("citation") or {}).get("repeated_refs") or {}).get("1") or []
    out: dict[str, int] = {}
    if not isinstance(decl, list):
        return out
    for entry in decl:
        if isinstance(entry, dict) and entry.get("ref") is not None:
            out[str(entry["ref"])] = int(entry.get("count") or 0)
    return out


def run(manifest: Manifest, spine: dict, slot: str = "primary") -> tuple[Path, Path, Path]:
    from .text_fixes import apply_text_fixes
    cfg = ((manifest.data.get("english") or {}).get(slot) or {})
    if not cfg:
        raise ValueError(f"{manifest.work_id}: english.{slot} is required for perseus-play")
    xml_path = SOURCES_DIR / cfg["source"]
    speakers = manifest.data.get("speakers") or {}
    # Resolve Greek speakers through stage7's own rules (overrides included,
    # plus C3's numbered-siglum overrides synthesized from this spine).
    sigla = _SiglaResolver(manifest, spine)
    if slot == "secondary":
        aliases = speakers.get("english_secondary") or speakers.get("english") or {}
    else:
        aliases = speakers.get("english") or {}
    anchor_map = _anchor_map_from(manifest, cfg, spine) if cfg.get("anchor_map") else None
    english, footnotes, report = parse_translation(
        xml_path,
        spine,
        work_id=manifest.work_id,
        covered_decl=cfg.get("covered") or [],
        translation_id=cfg["id"],
        sigla=sigla,
        english_aliases=aliases,
        line_fixes=cfg.get("line_fixes"),
        cuts=cfg.get("cuts"),
        transpositions=((manifest.data.get("citation") or {}).get("transpositions") or {}).get("1") or [],
        repeated_refs=_repeated_ref_counts(manifest),
        anchor_map=anchor_map,
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

    apply_text_fixes(english, footnotes, cfg.get("text_fixes"), manifest.work_id, slot)

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
    if anchor_map:
        write_json(out_dir / "anchor_map.json", anchor_map[0])
    return english_path, alignment_path, report_path
