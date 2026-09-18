"""Ian Johnston's play pages (johnstonia, VIU) -> verse-own-line turn-text.

Johnston numbers every tenth line of his English ("10") and every tenth
Greek line in brackets ("[10]"), both mid-speech, never at a speech start,
so these texts pair with the Greek by speaker turn (``model: turn-text``,
``format: verse-own-line``), not by line.  Both numbers are counted and
dropped, footnote calls go, stage directions (in square brackets) are kept
as ``_[...]_`` lines, and the play ends where the notes begin.

    python -m drama_pipeline.johnston_clean   # rewrite sources/bench/johnston/*.txt
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

import lxml.html

from .config import SOURCES_DIR
from .stage1_common import collapse_ws
from .stage1_turn_english import _lindsay_speaker

# Work id -> the title line written at the top of the text (manifest `play:`).
PLAYS = {
    "agamemnon": "AGAMEMNON",
    "libation-bearers": "LIBATION BEARERS",
    "eumenides": "EUMENIDES",
    "persians": "PERSIANS",
    "prometheus-bound": "PROMETHEUS BOUND",
    "seven-against-thebes": "SEVEN AGAINST THEBES",
    "suppliants-aesch": "SUPPLIANT WOMEN",
    "ajax": "AJAX",
    "antigone": "ANTIGONE",
    "oedipus-tyrannus": "OEDIPUS THE KING",
    "oedipus-coloneus": "OEDIPUS AT COLONUS",
    "philoctetes": "PHILOCTETES",
    "electra-eur": "ELECTRA",
    "hippolytus": "HIPPOLYTUS",
    "medea": "MEDEA",
    "orestes": "ORESTES",
    "bacchae": "BACCHAE",
    "birds": "BIRDS",
    "clouds": "CLOUDS",
    "frogs": "FROGS",
    "knights": "KNIGHTS",
    "lysistrata": "LYSISTRATA",
    "peace": "PEACE",
}

_BLOCK = frozenset(
    {"p", "div", "blockquote", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table", "tr", "td"}
)
_SKIP = frozenset({"script", "style", "head", "title", "sup"})
_GREEK_NUMBER = re.compile(r"\[\s*\d{1,4}[a-z]?\s*\]")
_END_NUMBER = re.compile(r"(?:^|\s)\d{1,4}[a-z]?$")
_CUE = re.compile(
    r"^([A-Z][A-Z0-9'’\-]*(?:\s+(?:and\s+)?[A-Z0-9][A-Z0-9'’\-]*)*)[:.]?\s*(\[.*)?$"
)
# A title-case return cue ("Xerxes", "Chorus"): same shape as `_CUE` but each
# word may carry lowercase letters after its capital. Only tried when `_CUE`
# fails, and only trusted (see `_cue`) when the name was already spoken in
# full capitals earlier in the same play -- otherwise an ordinary one-word
# line of verse ("Enough.") would be misread as a return cue, since every
# English sentence starts with a capital letter too.
_CUE_LOOSE = re.compile(
    r"^([A-Za-z][A-Za-z0-9'’\-]*(?:\s+(?:and\s+)?[A-Za-z0-9][A-Za-z0-9'’\-]*)*)[:.]?\s*(\[.*)?$"
)
_CAST_ENTRY = re.compile(r"^[^a-z:,]{2,}[:,]")
_END = frozenset({"ENDNOTES", "NOTES", "FOOTNOTES", "EPILOGUE"})
_NUMBER_WORDS = {
    "1": "ONE", "2": "TWO", "3": "THREE", "4": "FOUR", "5": "FIVE", "6": "SIX",
    "7": "SEVEN", "8": "EIGHT", "9": "NINE", "10": "TEN", "11": "ELEVEN", "12": "TWELVE",
}


class Converted(NamedTuple):
    text: str  # verse-own-line turn-text
    markers: int  # line numbers dropped (English and Greek)
    speeches: int  # speaker cues written


def read_page(path: Path) -> str:
    """The 2022 Bacchae page is UTF-8; the Word pages on web.viu.ca are Windows-1252."""
    data = Path(path).read_bytes()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1252")


def _walk(el, out: list, italic: bool = False, upper: bool = False) -> None:
    """Flatten ``el`` into text / br / open / close tokens."""
    tag = el.tag.lower() if isinstance(el.tag, str) else ""
    if not tag or tag in _SKIP:
        # A skipped element (a footnote marker's own `<sup>`, most often)
        # can still carry the SOURCE's own line break for the verse line it
        # interrupts -- johnston/antigone.htm's note-8 marker sits in a
        # `<sup>` between "...in the city." and "I'd trust...", with the
        # `<br>` INSIDE that `<sup>`; dropping the whole element dropped the
        # break too and welded the two lines with no space between them
        # (J1, 2026-09-17 round 2 brief: "city.I'd trust...",
        # johnston/antigone.txt:1126). Keep any nested `<br>`, same as the
        # footnote-link special case just below; drop everything else.
        if tag:
            out.extend(("br",) for _br in el.iter("br"))
        return
    if tag == "a" and "#" in (el.get("href") or ""):
        # A footnote call ("#n1", "birds.htm#note45"): its text goes, a line
        # break inside it stays.
        out.extend(("br",) for _br in el.iter("br"))
        return
    if tag == "br":
        out.append(("br",))
        return
    block = tag in _BLOCK
    if block:
        out.append(("open",))
    it = italic or tag in ("i", "em")
    up = upper or "text-transform:uppercase" in (el.get("style") or "").replace(" ", "")
    if el.text:
        out.append(("text", el.text.upper() if up else el.text, it))
    for child in el:
        _walk(child, out, it, up)
        if child.tail:
            out.append(("text", child.tail.upper() if up else child.tail, it))
    if block:
        out.append(("close",))


def _lines(tokens: list) -> list[tuple[str, bool] | None]:
    """Printed lines as ``(text, italic)``, ``None`` at each paragraph edge.

    ``italic`` is true when the line carries any italicized text. Johnston
    sets stage directions in italics; dialogue he has himself restored or
    supplied after a manuscript gap is bracketed but printed in the same
    plain verse font as the rest of the line (see ``convert``)."""
    out: list[tuple[str, bool] | None] = []
    current: list[str] = []
    italic: list[bool] = []

    def flush() -> None:
        text = collapse_ws("".join(current)).strip()
        out.append((text, any(italic)))
        current.clear()
        italic.clear()

    for token in tokens:
        if token[0] == "text":
            current.append(token[1])
            if token[1].strip():
                italic.append(token[2])
        elif token[0] == "br":
            flush()
        else:
            flush()
            out.append(None)
    flush()
    return out


def _strip_numbers(line: str) -> tuple[str, int]:
    line, n = _GREEK_NUMBER.subn(" ", line)
    line = collapse_ws(line).strip()
    if not (line.isdigit() or any(ch.islower() for ch in line)):
        return line, n  # a cue keeps its number ("CHORUS MEMBER 1")
    while match := _END_NUMBER.search(line):
        line = line[: match.start()].rstrip()
        n += 1
    return line, n


def _cue(
    line: str, known: set[str] | None = None, para_initial: bool = False
) -> tuple[str, str, bool] | None:
    """``(cue, rest, loose)`` for a speaker line; ``rest`` opens a stage
    direction and ``loose`` marks a title-case match the caller must not
    trust unless real speech follows it (see ``convert``).

    ``known`` is the set of cues already spoken (in full capitals) earlier in
    this same play, and ``para_initial`` says whether ``line`` opens its own
    ``<p>``: together they are what let a later title-case return cue
    ("Xerxes", "Chorus") through ``_CUE_LOOSE`` without also swallowing a
    character's own name where it ends someone else's sentence mid-paragraph
    ("Menelaus" in Orestes, "Danaus." in Suppliant Women) or an ordinary
    one-word line of verse -- so a loose match needs both, and the caller
    must also check ``is_speech`` before trusting it."""
    stripped = line.rstrip(" |")  # Agamemnon prints "WATCHMAN |"
    match = _CUE.match(stripped)
    loose = match is None
    if loose:
        match = _CUE_LOOSE.match(stripped)
    if not match or sum(ch.isalpha() for ch in match.group(1)) < 2:
        return None
    words = match.group(1).upper().split()  # "HIPPOLYTUS and ATTENDANTS"
    if words[0] in ("A", "AN", "THE") and len(words) > 1:
        words = words[1:]  # the cue reader takes "THE ..." for a title
    joined: list[str] = []
    for word in words:
        word = _NUMBER_WORDS.get(word, word)
        if len(word) == 1 and joined:
            joined[-1] += f"-{word}"  # "WOMAN C": the cue reader wants two letters
        else:
            joined.append(word)
    words = joined
    cue = " ".join(words)
    if loose and (not para_initial or cue not in (known or ())):
        return None
    if _lindsay_speaker(cue) != cue:
        raise ValueError(f"speaker cue {line!r} cannot be written as a verse-own-line cue")
    return cue, (match.group(2) or ""), loose


def _is_end(line: str) -> bool:
    return line.upper() in _END or line.startswith(("[Back to", "Page loads on", "Notes to"))


def _opens_direction(line: str, italic: bool) -> bool:
    """A ``[``-led line is a stage direction, not restored dialogue.

    Johnston sets stage directions in italics. He also brackets dialogue he
    has himself restored or supplied after a manuscript gap, but prints it in
    the same plain (non-italic) verse font as the rest of the speech; those
    lines must stay in the turn-text as ordinary verse, brackets and all,
    rather than being read as a direction. A bracketed line with no lowercase
    letters at all (an ellipsis marking an untranslated gap, "[. . . .]") is
    not restored dialogue either way, so it still opens a direction."""
    return italic or not any(ch.islower() for ch in line)


def convert(raw_html: str, title: str) -> Converted:
    doc = lxml.html.fromstring(raw_html)
    tokens: list = []
    _walk(doc, tokens)
    lines: list[str | None] = []
    italics: list[bool] = []
    markers = 0
    for item in _lines(tokens):
        if item is None:
            lines.append(None)
            italics.append(False)
            continue
        line, italic = item
        # An unlinked footnote call ("death.*"); the verse has no asterisks.
        line, n = _strip_numbers(line.replace("*", ""))
        markers += n
        lines.append(line)
        italics.append(italic)

    heads = [i for i, line in enumerate(lines) if line and line.casefold() == "dramatis personae"]
    if not heads:
        raise ValueError("no Dramatis Personae heading")

    # Cues already spoken in full capitals, in document order -- what lets a
    # later title-case return cue ("Xerxes", "Chorus") through `_cue` without
    # also swallowing an ordinary one-word line of verse.
    known_cues: set[str] = set()

    def is_para_initial(k: int) -> bool:
        # `lines[k]` opens its `<p>` when nothing but paragraph-boundary
        # `None`s and empty flush artifacts ("") separate it from the last
        # real content -- a `<p>` open/close pair around a genuine speech
        # break shows up as `[..., None, "", None, ...]` in `lines`. A name
        # that merely ends the previous speaker's sentence ("Menelaus" in
        # Orestes, "Danaus." in Suppliant Women) sits mid-paragraph instead,
        # a plain `<br>` away from real text, and fails this check.
        for prev in reversed(lines[:k]):
            if prev is None:
                return True
            if prev:
                return False
        return True

    def is_speech(k: int) -> bool:
        # The next printed line after a cue, directions, scene notes and
        # cast-list entries ("AEACUS: a gatekeeper") skipped, is verse.
        for j in range(k + 1, len(lines)):
            line = lines[j]
            if not line or line.startswith(("[", "Scene")) or _CAST_ENTRY.match(line):
                continue
            return (
                _cue(line, known_cues, is_para_initial(j)) is None
                and any(ch.islower() for ch in line)
            )
        return False

    start = next(
        (
            k
            for k in range(heads[0] + 1, len(lines))
            if lines[k] and _cue(lines[k], known_cues, is_para_initial(k)) and is_speech(k)
        ),
        None,
    )
    if start is None:
        raise ValueError("no speeches after the Dramatis Personae")

    # ("cue", name) / ("dir", text) / ("line", text) / ("para",)
    items: list[tuple[str, ...]] = []
    direction: list[str] | None = None

    def close_direction() -> None:
        nonlocal direction
        assert direction is not None
        items.append(("dir", collapse_ws(" ".join(direction)).replace("_", " ")))
        direction = None

    def add_direction(text: str) -> None:
        # Text after a closing bracket is verse again. Birds closes two
        # directions with "}", a typo for "]".
        assert direction is not None
        ends = [i for i in (text.find("]"), text.find("}")) if i >= 0]
        if not ends:
            direction.append(text)
            return
        direction.append(text[: min(ends)] + "]")
        close_direction()
        tail = text[min(ends) + 1 :]
        if tail.strip():
            items.append(("line", tail.strip()))

    for k in range(heads[0] + 1, len(lines)):
        line = lines[k]
        if line is None:
            items.append(("para",))
            continue
        if not line:
            continue
        if direction is not None:
            if italics[k] or not any(ch.isalpha() for ch in line):
                add_direction(line)
                continue
            # Johnston's directions are italic: a plain line after one whose
            # bracket he never closed (Birds, "[advancing towards Pisthetairos
            # and Euelpides") is the speech again.
            direction[-1] = direction[-1].rstrip() + "]"
            close_direction()
        if k >= start and _is_end(line):
            break
        if line.startswith("[") and _opens_direction(line, italics[k]):
            direction = []
            add_direction(line)
            continue
        if k < start:
            continue  # the cast list and scene notes
        cue = _cue(line, known_cues, is_para_initial(k))
        if cue and (not cue[2] or is_speech(k)):
            known_cues.add(cue[0])
            items.append(("cue", cue[0]))
            if cue[1]:
                direction = []
                add_direction(cue[1])
            continue
        items.append(("line", line.replace("_", " ")))

    text, written = write_turn_text(title, items)
    return Converted(text, markers, written)


def write_turn_text(title: str, items: list[tuple[str, ...]]) -> tuple[str, int]:
    """``("cue", name)`` / ``("dir", text)`` / ``("line", text)`` / ``("para",)``
    items -> verse-own-line turn-text and the number of cues written."""
    out = [title, ""]
    speeches: list[tuple[str, list[tuple[str, ...]]]] = []
    for item in items:
        if item[0] == "cue":
            speeches.append((item[1], []))
        elif speeches:
            speeches[-1][1].append(item)
        elif item[0] == "dir":
            out += [f"_{item[1]}_", ""]
    written = 0
    for cue, body in speeches:
        if not any(kind == "line" for kind, *_rest in body):
            # A cue with no words of its own: its directions still print.
            for kind, *rest in body:
                if kind == "dir":
                    out += [f"_{rest[0]}_", ""]
            continue
        out.append(cue)
        written += 1
        for kind, *rest in body:
            if kind == "line":
                out.append(rest[0])
            elif kind == "dir":
                out.append(f"_{rest[0]}_")
            elif out[-1] != "":
                out.append("")
        if out[-1] != "":
            out.append("")
    return "\n".join(out).rstrip("\n") + "\n", written


def main() -> int:
    out_dir = SOURCES_DIR / "bench" / "johnston"
    out_dir.mkdir(parents=True, exist_ok=True)
    for work_id, title in PLAYS.items():
        result = convert(read_page(SOURCES_DIR / "johnston" / f"{work_id}.htm"), title)
        (out_dir / f"{work_id}.txt").write_text(result.text, encoding="utf-8")
        print(f"{work_id}: markers={result.markers} speeches={result.speeches}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
