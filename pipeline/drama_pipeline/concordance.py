"""Map printed Greek line refs in an edition to the reference text."""
from __future__ import annotations

from collections import defaultdict
from difflib import SequenceMatcher
import unicodedata


def normalize(text: str) -> str:
    # U+0345 is the iota subscript. Keep it as an ordinary iota before
    # removing the other combining marks, so adscript and subscript agree.
    decomposed = unicodedata.normalize("NFD", text).replace("\u0345", "ι")
    return "".join(
        ("σ" if ch == "ς" else ch.lower())
        for ch in decomposed
        if unicodedata.category(ch).startswith("L") and ch not in "ʼ᾿᾽"
    )


def match_lines(edition: list[dict], reference: list[dict]) -> dict[str, str]:
    """Match long lines in print order, first exactly, then near by text.

    Each search stays within 50 reference lines of the expected position.
    Unmatched lines do not advance the reference cursor.
    """
    ref_keys = [normalize(line["text"]) for line in reference]
    exact: dict[str, list[int]] = defaultdict(list)
    for index, key in enumerate(ref_keys):
        if len(key) >= 12:
            exact[key].append(index)
    result: dict[str, str] = {}
    last = -1
    offset = 0
    for index, line in enumerate(edition):
        key = normalize(line["text"])
        if len(key) < 12:
            continue
        expected = index + offset
        low = max(last + 1, expected - 50, 0)
        high = min(len(reference), expected + 51)
        choices = [j for j in exact.get(key, []) if low <= j < high]
        if choices:
            found = min(choices, key=lambda j: abs(j - expected))
        else:
            found = None
            best = 0.85
            for j in range(low, high):
                candidate = ref_keys[j]
                if len(candidate) < 12:
                    continue
                ratio = SequenceMatcher(None, key, candidate, autojunk=False).ratio()
                if ratio >= best:
                    if ratio > best or found is None or abs(j - expected) < abs(found - expected):
                        found, best = j, ratio
        if found is not None:
            result[line["ref"]] = reference[found]["ref"]
            last = found
            offset = found - index
    return result
