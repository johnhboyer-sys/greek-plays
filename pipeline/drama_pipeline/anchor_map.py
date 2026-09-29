"""Re-key a translation's line anchors from one Greek edition's count to another's.

Perseus prints an English translation's ``<l n>`` anchors in the count of its
own Greek text (Storr's, for Jebb's Sophocles). An edition that counts
differently (Jebb's own Greek) has no line, or the wrong one, at some of
those numbers. ``build_anchor_map`` finds, for each line of the source
edition, the line of the target edition that holds the same text, by the
concordance matcher; ``remap_anchor`` then turns one printed anchor into the
target's number. Nothing here is written by hand.

A source line the matcher leaves out (a short line, a lyric split another way)
takes the offset both of its matched neighbours share: when the line before and
the line after it sit the same number of lines apart in the two editions, so
does it. Where they disagree it stays unmapped and its anchor keeps its
number.
"""
from __future__ import annotations

import re

from .concordance import match_lines

_ANCHOR = re.compile(r"(\d+)([a-z]*)")
_REF = re.compile(r"\d+[a-z]*")


def build_anchor_map(
    source: list[dict], target: list[dict]
) -> tuple[dict[str, str], set[str]]:
    """Map each source ref to the target ref holding the same text.

    Returns ``(mapping, inferred)``: ``inferred`` is the refs mapped by the
    shared-offset rule rather than by a text match.
    """
    direct = {
        ref: value
        for ref, value in match_lines(source, target).items()
        if _REF.fullmatch(value)
    }
    target_pos: dict[str, int] = {}
    for index, line in enumerate(target):
        target_pos.setdefault(line["ref"], index)
    matched: list[tuple[int, int]] = []
    for index, line in enumerate(source):
        j = target_pos.get(direct.get(line["ref"], ""))
        if j is not None:
            matched.append((index, j))
    mapping = dict(direct)
    inferred: set[str] = set()
    cursor = 0
    for index, line in enumerate(source):
        ref = line["ref"]
        if ref in mapping:
            continue
        while cursor < len(matched) and matched[cursor][0] < index:
            cursor += 1
        if cursor == 0 or cursor >= len(matched):
            continue
        (a, ja), (b, jb) = matched[cursor - 1], matched[cursor]
        if ja - a != jb - b:
            continue
        j = index + (ja - a)
        if 0 <= j < len(target):
            mapping[ref] = target[j]["ref"]
            inferred.add(ref)
    return mapping, inferred


def remap_anchor(anchor: str, mapping: dict[str, str], target_refs: set[str]) -> str | None:
    """The target's number for one printed anchor, or None when the text gives none.

    A lettered anchor (``148b``, a share of a divided line) maps its whole
    ref if the source has a line of that name, else its base line; it keeps
    the letter only where the target has a line or share of that name.
    """
    found = _ANCHOR.fullmatch(anchor)
    if found is None:
        return None
    if anchor in mapping:
        return mapping[anchor]
    base, letter = found.groups()
    if not letter or base not in mapping:
        return None
    target = mapping[base]
    lettered = target + letter
    return lettered if lettered in target_refs else target
