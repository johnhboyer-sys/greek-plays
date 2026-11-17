"""Speeches: the plays' search unit (John, 2026-11-16: "Count by speech/turn").

A speech runs from one speaker cue to the next. The ported search counts and
pages by "chapter" (Aristotle's unit), so in the plays every speech is a
chapter: offsets.json `chapter_bounds` holds one entry per speech, and
`turn_bounds` the same speeches for the speaker filter and the proximity
editor's "turn" unit.

The cut rule (docs/search-port/units.py): every speaker event in the spine's
`segments[].speakers` starts a speech, at the first token of its line whose
character offset is at or past the event's (a mid-line cue, antilabe, starts
its speech mid-line; the words before it stay with the speaker before). A
segment that opens with no cue (a long speech cut at the line cap) continues
the speech above it. A book's first token starts a speech even with no cue.
A speech whose cue has no Greek token after it in its book (nothing left to
hold) is dropped.

Names. `chapter-pages.ts` finds a chapter by `names.indexOf(chapter)`, so a
name must be unique within its book. A speech is named by the printed ref of
the line its cue stands on ("1287"). When that name is taken -- a second
speech starting on the same printed line (antilabe), or a ref the edition
prints twice (citation.repeated_refs) -- the later speech takes the ref plus
the first of b, c, d ... that is neither taken nor itself a ref some speech
starts on ("1287b", "1287c"). Past z it takes "<ref>.<n>".
"""

from __future__ import annotations

from collections import defaultdict
from string import ascii_lowercase


def build_speeches(
    segments: list[dict],
    spine_segments: list[dict] | None,
    seg_base_offset: list[int],
) -> list[dict]:
    """Every speech of a work, in document order.

    `segments` are stage 3's (lines of tokens with `o`), `spine_segments` the
    spine's (lines with `ref`, events in `speakers`, each with `display` when
    stage 7's canonicalization has run on them), paired by position. Each
    speech: {book, name, start, seg, line, column, ref, offset, label,
    speaker, title, cued, bekker}. `start` is the global token offset of the
    speech's first token; `seg`/`line`/`column`/`ref` place its cue (the
    book's first line for the uncued opening); `speaker` is the display name
    ('' for the dash, which names no one), `title` the heading text.
    """
    if spine_segments is None:
        spine_segments = [{"id": s["id"], "lines": [{} for _ in s["lines"]]} for s in segments]
    if len(spine_segments) != len(segments):
        raise ValueError(f"speeches: {len(spine_segments)} spine segments for {len(segments)} stage3 segments")

    found: list[dict] = []
    book_open: dict[int, dict] = {}
    book_end: dict[int, int] = {}
    token_ref: list[str] = []
    for si, (seg, spine_seg) in enumerate(zip(segments, spine_segments)):
        if spine_seg.get("id", seg["id"]) != seg["id"] or len(spine_seg["lines"]) != len(seg["lines"]):
            raise ValueError(f"speeches: segment {seg['id']} differs between the spine and stage 3")
        book = seg["book"]
        events: dict = defaultdict(list)
        for ev in spine_seg.get("speakers") or []:
            events[ev["line"]].append(ev)
        g = seg_base_offset[si]
        for line, spine_line in zip(seg["lines"], spine_seg["lines"]):
            n = spine_line.get("n", line.get("n"))
            ref = str(spine_line.get("ref") or (n if n is not None else seg["column"]))
            if book not in book_open:
                book_open[book] = {"start": g, "seg": si, "line": n, "column": seg["column"], "ref": ref}
            tokens = line["tokens"]
            # A line number may repeat in a fixture; the events go to the
            # first line that carries it, as units.py maps them.
            for ev in sorted(events.pop(n, []), key=lambda e: e["offset"]):
                k = next((i for i, t in enumerate(tokens) if t.get("o", 0) >= ev["offset"]), len(tokens))
                display = ev["display"] if "display" in ev else ev.get("label")
                found.append({
                    "book": book, "start": g + k, "seg": si, "line": n,
                    "column": seg["column"], "ref": ref, "offset": ev["offset"],
                    "label": ev.get("label"), "speaker": display or "",
                    "title": display or ev.get("label") or "—", "cued": True,
                })
            token_ref.extend([ref] * len(tokens))
            g += len(tokens)
        if events:
            raise ValueError(f"speeches: segment {seg['id']} has a speaker event on no line of its own: {sorted(events)}")
        book_end[book] = g

    by_book: dict[int, list[dict]] = defaultdict(list)
    for sp in found:
        if sp["start"] < book_end[sp["book"]]:
            by_book[sp["book"]].append(sp)
    out: list[dict] = []
    for book, opening in book_open.items():
        speeches = by_book[book]
        if opening["start"] >= book_end[book]:
            continue  # a book with no Greek token holds no speech
        if not speeches or speeches[0]["start"] > opening["start"]:
            speeches.insert(0, {
                "book": book, **opening, "offset": 0, "label": None,
                "speaker": "", "title": "—", "cued": False,
            })
        reserved = {sp["ref"] for sp in speeches}
        used: set[str] = set()
        for i, sp in enumerate(speeches):
            name = sp["ref"]
            if name in used:
                name = next(
                    (sp["ref"] + c for c in ascii_lowercase[1:]
                     if sp["ref"] + c not in used and sp["ref"] + c not in reserved),
                    None,
                )
                k = 2
                while name is None or name in used:
                    name, k = f"{sp['ref']}.{k}", k + 1
            used.add(name)
            sp["name"] = name
            end = (speeches[i + 1]["start"] if i + 1 < len(speeches) else book_end[book]) - 1
            last = token_ref[end] if end >= sp["start"] else sp["ref"]
            sp["bekker"] = sp["ref"] if last == sp["ref"] else f"{sp['ref']}–{last}"
        out.extend(speeches)
    return out


def chapter_bounds(speeches: list[dict]) -> list[dict]:
    """offsets.json `chapter_bounds`, Aristotle's shape. Every bound is exact:
    the speech's first token is known from the cue's character offset."""
    return [{"book": sp["book"], "chapter": sp["name"], "start": sp["start"], "accuracy": "exact"}
            for sp in speeches]


def turn_bounds(speeches: list[dict]) -> list[dict]:
    """offsets.json `turn_bounds`, Plato's shape: the cued speeches only. The
    uncued opening names no one, and a turn there would let an "anyone but"
    speaker filter claim its words; before the first turn the search's
    speakerAt() says null, which fails every filter."""
    return [{"book": sp["book"], "speaker": sp["speaker"], "start": sp["start"], "accuracy": "exact"}
            for sp in speeches if sp["cued"]]
