"""Declared corrections to single English margin numbers.

`english.<slot>.tick_fixes` (or an edition's `alignment.<id>.tick_fixes`) is
a list of `{column, shown, nth?, n?, at?, label?, note?}`: in the English
beside Greek segment `column`, the `nth` (1-based, default the only) tick
showing `shown` is renumbered to `n`, moved to the start of the words `at`,
and/or given `label`, the lettered line it names ("1575b") where the segment
prints more than one lettered line of that number.
A fix that matches no tick, or whose `at` does not occur exactly once in
that English, fails the build rather than going stale silently.
"""

import re


def apply_tick_fixes(english: dict, fixes: list[dict] | None, work_id: str) -> None:
    by_column = {chunk["column"]: chunk for chunk in english.get("chunks") or []}
    for fix in fixes or []:
        where = f"{work_id}: tick_fixes {fix}"
        if not {"n", "at", "label"} & set(fix):
            raise ValueError(f"{where}: nothing to do (no n, at or label)")
        chunk = by_column.get(str(fix["column"]))
        if chunk is None:
            raise ValueError(f"{where}: no English beside segment {fix['column']}")
        ticks = [t for t in chunk.get("bekker") or [] if t["n"] == int(fix["shown"])]
        nth = fix.get("nth")
        if nth is None and len(ticks) != 1:
            raise ValueError(f"{where}: matches no single tick ({len(ticks)} found)")
        if nth is not None and not 1 <= nth <= len(ticks):
            raise ValueError(f"{where}: matches no tick number {nth} ({len(ticks)} found)")
        tick = ticks[(nth or 1) - 1]
        if "at" in fix:
            count = chunk["text"].count(fix["at"])
            if count != 1:
                raise ValueError(f"{where}: at occurs {count} times")
            tick["offset"] = chunk["text"].index(fix["at"])
        if "n" in fix:
            tick["n"] = int(fix["n"])
        if "label" in fix:
            if not re.fullmatch(rf"{tick['n']}[a-z]", str(fix["label"])):
                raise ValueError(f"{where}: label is not a lettered line {tick['n']}")
            tick["label"] = str(fix["label"])
        chunk["bekker"].sort(key=lambda t: t["offset"])
