"""Checked, reader-facing corrections for one English translation slot."""

from __future__ import annotations


def apply_text_fixes(english: dict, footnotes: dict, fixes: list | None,
                     manifest: str, slot: str) -> None:
    """Change final chunk and footnote text, requiring one hit per fix."""
    if not fixes:
        return

    def strings(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "text" and isinstance(item, str):
                    yield value, key
                elif key in ("directions", "directionsBefore") and isinstance(item, list):
                    for index, direction in enumerate(item):
                        if isinstance(direction, str):
                            yield item, index
                        elif isinstance(direction, (dict, list)):
                            yield from strings(direction)
                elif isinstance(item, (dict, list)):
                    yield from strings(item)
        elif isinstance(value, list):
            for item in value:
                yield from strings(item)

    targets = list(strings(english))
    targets += [(footnotes, key) for key, value in footnotes.items()
                if isinstance(value, str)]
    for fix in fixes:
        find, replace = fix["find"], fix["replace"]
        if not find or find == replace:
            raise ValueError(f"{manifest}: english.{slot} text_fixes invalid find {find!r}")
        hits = sum(obj[key].count(find) for obj, key in targets)
        if hits != 1:
            raise ValueError(
                f"{manifest}: english.{slot} text_fixes find {find!r} "
                f"occurred {hits} times (expected once)"
            )
        for obj, key in targets:
            if find in obj[key]:
                old = obj[key]
                start = old.index(find)
                # The context in `find` is unchanged on either side of the
                # actual edit. Keep positions used by stage7's turn labels,
                # ticks, and note calls aligned with the new string.
                prefix = 0
                while prefix < min(len(find), len(replace)) and find[prefix] == replace[prefix]:
                    prefix += 1
                suffix = 0
                while (suffix < len(find) - prefix
                       and suffix < len(replace) - prefix
                       and find[-suffix - 1] == replace[-suffix - 1]):
                    suffix += 1
                edit_start = start + prefix
                edit_end = start + len(find) - suffix
                delta = len(replace) - len(find)
                if key == "text" and isinstance(obj, dict):
                    for field in ("turns", "notes", "markers", "bekker"):
                        for item in obj.get(field) or []:
                            if not isinstance(item, dict) or not isinstance(item.get("offset"), int):
                                continue
                            offset = item["offset"]
                            if edit_start < offset < edit_end:
                                raise ValueError(
                                    f"{manifest}: english.{slot} text_fixes find {find!r} "
                                    "crosses a text offset"
                                )
                            if offset >= edit_end:
                                item["offset"] = offset + delta
                obj[key] = old.replace(find, replace, 1)
                break
