"""A work's Greek as one running text, for the search page's running-text mode.

Ported from the Aristotle reader (pipeline/aristotle_pipeline/running_text.py,
main 3fd7197). Stage 6 writes search/running.json:

  {"v": 1, "token_count": N, "text": "..."}

`text` is every stage3 token of the work in document order, each as its Beta
Code letters (lowercase, the search indexes' letters) with its diacritics
kept after each letter in one fixed order, and between two tokens the
punctuation the page prints there, including before the first token and after
the last. The two never share a character:

  token  a-z  '  ( ) / \\ = | +     (letters, elision, Beta Code marks)
  gap    space , . ; : " -          (: is the raised dot, " every quote mark)

so the n-th run of token characters IS global token n: the offset map back to
segment, line and token is offsets.json, which counts the same tokens in the
same order. Editorial sigla ([ ] < > † *) and parentheses (which Beta Code
spends on breathings) are not text and are left out.

One difference from Aristotle: the plays' stage 3 keeps each token's exact
place in its line (`o`, with text[o:o+len(t)] == t, stage3_tokenize's
contract), so build_running_text cuts the printed line at those places
rather than re-tokenizing it with stage 3's cleaning rules. The gaps are the
printed text between tokens; check_alignment is Aristotle's, unchanged.
"""

from __future__ import annotations

import re
import unicodedata

from .beta import _APOSTROPHES, _BASE, _MARKS

TOKEN_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz'()/\\=|+")
GAP_CHARS = frozenset(' ,.;:"-')

# The order a letter's marks are written in, whatever order they arrived in:
# breathing, diaeresis, accent, iota subscript (ἔ e)/, ΐ i+/, ᾗ h(=|).
_MARK_RANK = {")": 0, "(": 0, "+": 1, "/": 2, "\\": 2, "=": 2, "|": 3}

_GAP_MAP = {
    ",": ",", ".": ".", ";": ";", ";": ";",
    "·": ":", "·": ":", ":": ":",
    '"': '"', "“": '"', "”": '"', "‘": '"', "’": '"',
    "«": '"', "»": '"', "'": '"', "᾽": '"', "ʼ": '"',
    "—": "-", "–": "-", "-": "-",
}


def token_beta(surface: str) -> str:
    """A token's Beta Code with its marks, each letter's marks in _MARK_RANK
    order. Grave stays grave: this is the text as printed, not a lookup key."""
    units: list[list[str]] = []
    for ch in unicodedata.normalize("NFD", surface):
        if ch in _APOSTROPHES:
            units.append(["'"])
            continue
        low = ch.lower()
        if low in _BASE:
            units.append([_BASE[low]])
        elif "a" <= low <= "z":  # a Beta Code letter is its own fold, as in greekFold
            units.append([low])
        elif ch in _MARKS and units and units[-1][0] != "'":
            if _MARKS[ch]:
                units[-1].append(_MARKS[ch])
        # Sigla the plays' surface keeps (<ν>, †) have no token characters:
        # they drop out inside the token and never become a gap, which would
        # split one stage3 token into two.
    out = "".join(u[0] + "".join(sorted(u[1:], key=_MARK_RANK.__getitem__)) for u in units)
    if not any(c.isalpha() for c in out):
        raise ValueError(f"running text: token {surface!r} has no Greek letter")
    return out


def spells_a_letter(surface: str) -> bool:
    """Whether a token has a run of its own in the running text."""
    try:
        token_beta(surface)
    except ValueError:
        return False
    return True


def gap_text(raw: str) -> str:
    """The punctuation between two words as the running text keeps it: every
    space run one space, sigla and parentheses gone."""
    kept = "".join(" " if ch.isspace() else _GAP_MAP.get(ch, "") for ch in raw)
    return re.sub(r" {2,}", " ", kept)


def build_running_text(segments: list[dict], spine: dict) -> str:
    """The work's running text from stage3's segments and the spine's lines.
    Raises if a token does not stand in its line where stage 3 says it does,
    since every token after a slip would then be cited and marked wrongly."""
    work = spine["work"]
    if [s["id"] for s in segments] != [s["id"] for s in spine["segments"]]:
        raise ValueError(f"running text: {work}: segment order differs from stage3 at global token 0")
    parts: list[str] = []
    gap = ""
    global_token = 0
    for seg, printed_seg in zip(segments, spine["segments"]):
        # Pair lines by position as stage3 and stage7 do, never by number.
        if len(seg["lines"]) != len(printed_seg["lines"]):
            raise ValueError(
                f"running text: {work}: {seg['id']} line count differs from stage3 "
                f"at global token {global_token}"
            )
        for line, printed in zip(seg["lines"], printed_seg["lines"]):
            ref = f"{seg['id']} line {line.get('n')}{line.get('sub', '')}"
            text = printed["text"]
            gap += " "
            pos = 0
            for tok in line["tokens"]:
                o, t = tok["o"], tok["t"]
                if o < pos or text[o:o + len(t)] != t:
                    raise ValueError(
                        f"running text: {work}: {ref} token {t!r} is not at offset {o} "
                        f"of its line, global token {global_token}"
                    )
                gap += text[pos:o]
                mapped_gap = gap_text(gap)
                # Keep the printed work edges, without the line separator
                # added above or outer whitespace. Inner gaps still separate
                # tokens even when all their printed marks were sigla.
                parts.append((mapped_gap or " ") if global_token else mapped_gap)
                try:
                    parts.append(token_beta(t))
                except ValueError as err:
                    raise ValueError(
                        f"running text: {work}: {ref} global token {global_token}: {err}"
                    ) from err
                global_token += 1
                gap = ""
                pos = o + len(t)
            gap += text[pos:]
    parts.append(gap_text(gap))
    return "".join(parts).strip(" ")


def token_spans(text: str) -> list[tuple[int, int]]:
    """Each token's [start, end) in the running text: its runs of token
    characters, in order. The n-th span is global token n."""
    spans: list[tuple[int, int]] = []
    start = -1
    for i, ch in enumerate(text):
        if ch in TOKEN_CHARS:
            if start < 0:
                start = i
        elif ch in GAP_CHARS:
            if start >= 0:
                spans.append((start, i))
                start = -1
        else:
            raise ValueError(f"running text: unexpected character {ch!r} at {i}")
    if start >= 0:
        spans.append((start, len(text)))
    return spans


def check_alignment(work: str, text: str, segments: list[dict], token_count: int) -> None:
    """Raise on the first token that disagrees with the offsets source.

    Counts alone cannot detect a shifted or swapped token. Compare every run
    too; report the zero-based global token the client would cite wrongly.
    """
    try:
        spans = token_spans(text)
    except ValueError as err:
        raise ValueError(f"running text: {work}: {err}") from err
    if token_count == 0 or not spans:
        raise ValueError(
            f"running text: {work}: cannot check alignment at global token 0: "
            f"{len(spans)} runs, offsets token_count {token_count}"
        )
    expected = [(seg["id"], line, tok)
                for seg in segments for line in seg["lines"] for tok in line["tokens"]]
    for i in range(max(len(spans), len(expected), token_count)):
        actual = text[slice(*spans[i])] if i < len(spans) else None
        source = token_beta(expected[i][2]["t"]) if i < len(expected) else None
        if actual != source or i >= token_count or i >= len(expected):
            where = (f"{expected[i][0]} line {expected[i][1]['n']}"
                     f"{expected[i][1].get('sub', '')} {expected[i][2]['t']!r}"
                     if i < len(expected) else "<end of stage3>")
            raise ValueError(
                f"running text: {work}: first divergence at global token {i} ({where}): "
                f"run {actual!r}, expected {source!r}; {len(spans)} runs, "
                f"{len(expected)} stage3 tokens, offsets token_count {token_count}"
            )
