"""Map printed Greek line refs in an edition to the reference text.

The result maps each edition ref to a reference ref: ``{"<edition ref>": "<tlg ref>"}``.
A value is a single ref (``"113"``, ``"1290"``, ``"12.3"``) or, where one
reference line spans two numbers, a range ``"a-b"`` (``"112-113"``). Keys are
single refs. Only edition lines of 12 or more letters after normalising get a
value; the rest stay out of the map.

Matching runs in print order. A line matches first by exact text, then by
difflib ratio >= 0.85, within 50 reference lines of the expected position, and
never before an earlier match. Lyric colometry differs between editions, so
when no single line matches, the matcher tries up to three edition lines
joined against up to three reference lines joined (either side, or both). Each
edition line in a joined span takes the reference line that holds most of its
text.
"""
from __future__ import annotations

from collections import defaultdict
from difflib import SequenceMatcher
import unicodedata

MIN_LEN = 12
THRESHOLD = 0.85
WINDOW = 50
MAX_JOIN = 3


def normalize(text: str) -> str:
    # U+0345 is the iota subscript. Keep it as an ordinary iota before
    # removing the other combining marks, so adscript and subscript agree.
    decomposed = unicodedata.normalize("NFD", text).replace("ͅ", "ι")
    return "".join(
        ("σ" if ch == "ς" else ch.lower())
        for ch in decomposed
        if unicodedata.category(ch).startswith("L") and ch not in "ʼ᾿᾽"
    )


def _split_span(keys: list[str], ref_keys: list[str], start: int, blocks) -> list[int]:
    """For each edition line of a span, the reference line (offset from
    start) that holds most of its text."""
    e_bounds, pos = [], 0
    for key in keys:
        e_bounds.append((pos, pos + len(key)))
        pos += len(key)
    r_ends, pos = [], 0
    for key in ref_keys:
        pos += len(key)
        r_ends.append(pos)

    def r_index(p: int) -> int:
        for n, end in enumerate(r_ends):
            if p < end:
                return n
        return len(r_ends) - 1

    picks = []
    for lo, hi in e_bounds:
        counts = [0] * len(ref_keys)
        for a, b, size in blocks:
            for k in range(max(lo, a), min(hi, a + size)):
                counts[r_index(b + (k - a))] += 1
        picks.append(max(range(len(counts)), key=lambda n: (counts[n], -n)))
    return picks


def match_lines(edition: list[dict], reference: list[dict]) -> dict[str, str]:
    """Match long lines in print order, first exactly, then near by text,
    then by joining adjacent lines on either side.

    Each search stays within 50 reference lines of the expected position.
    Unmatched lines do not advance the reference cursor.
    """
    ref_keys = [normalize(line["text"]) for line in reference]
    ed_keys = [normalize(line["text"]) for line in edition]
    exact: dict[str, list[int]] = defaultdict(list)
    for index, key in enumerate(ref_keys):
        if len(key) >= MIN_LEN:
            exact[key].append(index)
    result: dict[str, str] = {}
    last = -1
    offset = 0
    index = 0
    while index < len(edition):
        key = ed_keys[index]
        expected = index + offset
        low = max(last + 1, expected - WINDOW, 0)
        high = min(len(reference), expected + WINDOW + 1)
        found = None
        if len(key) >= MIN_LEN:
            choices = [j for j in exact.get(key, []) if low <= j < high]
            if choices:
                found = min(choices, key=lambda j: abs(j - expected))
            else:
                best = THRESHOLD
                for j in range(low, high):
                    candidate = ref_keys[j]
                    if len(candidate) < MIN_LEN:
                        continue
                    ratio = SequenceMatcher(None, key, candidate, autojunk=False).ratio()
                    if ratio >= best:
                        if ratio > best or found is None or abs(j - expected) < abs(found - expected):
                            found, best = j, ratio
        if found is not None:
            result[edition[index]["ref"]] = reference[found]["ref"]
            last = found
            offset = found - index
            index += 1
            continue
        span = _match_span(ed_keys, ref_keys, index, low, high, expected)
        if span is None:
            index += 1
            continue
        k, j, m, picks = span
        for n, pick in zip(range(k), picks):
            if len(ed_keys[index + n]) >= MIN_LEN:
                result[edition[index + n]["ref"]] = reference[j + pick]["ref"]
        last = j + m - 1
        offset = last - (index + k - 1)
        index += k
    return result


def _match_span(ed_keys, ref_keys, index, low, high, expected):
    """Best joined match starting at edition line ``index``: (k, j, m, picks)
    for k edition lines against m reference lines from j, or None."""
    best_score, best = THRESHOLD, None
    for k in range(1, MAX_JOIN + 1):
        if index + k > len(ed_keys):
            break
        span_keys = ed_keys[index:index + k]
        joined = "".join(span_keys)
        if len(joined) < MIN_LEN or not any(len(s) >= MIN_LEN for s in span_keys):
            continue
        for m in range(1, MAX_JOIN + 1):
            if k == 1 and m == 1:
                continue
            for j in range(low, min(high, len(ref_keys) - m + 1)):
                target = "".join(ref_keys[j:j + m])
                if not target:
                    continue
                matcher = SequenceMatcher(None, joined, target, autojunk=False)
                ratio = matcher.ratio()
                if ratio < best_score:
                    continue
                if ratio == best_score and best is not None and abs(j - expected) >= abs(best[1] - expected):
                    continue
                best_score = ratio
                best = (k, j, m, matcher)
    if best is None:
        return None
    k, j, m, matcher = best
    picks = _split_span(ed_keys[index:index + k], ref_keys[j:j + m], j, matcher.get_matching_blocks())
    return k, j, m, picks
