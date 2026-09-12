"""Gilbert Murray's verse translations -> verse-own-line turn-text.

Murray prints no line numbers, so his plays pair with the Greek by speaker
turn (``model: turn-text``, ``format: verse-own-line``).  Ten come as
Project Gutenberg plain text, the Frogs as Wikisource's proofread HTML.
Each play is cut at its own heading and at the start of its notes; stage
directions are kept as ``_..._`` lines, italic marks and illustrations go.

    python -m drama_pipeline.murray_clean   # rewrite sources/bench/murray/*.txt
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import lxml.html

from .config import SOURCES_DIR
from .johnston_clean import _CAST_ENTRY, Converted, _cue, write_turn_text
from .stage1_common import collapse_ws

# Work id -> (source under sources/, title line written at the top (manifest
# `play:`), the heading the play opens after, the line its notes open with).
PLAYS = {
    "agamemnon": ("gutenberg/pg14417.txt", "AGAMEMNON", "THE AGAMEMNON", "NOTES TO THE AGAMEMNON"),
    "oedipus-tyrannus": ("gutenberg/pg27673.txt", "OEDIPUS KING OF THEBES", "OEDIPUS, KING OF THEBES", "NOTES TO"),
    "medea": ("gutenberg/pg35451.txt", "MEDEA", "MEDEA", "NOTES TO MEDEA"),
    "bacchae": ("gutenberg/pg35173.txt", "BACCHAE", "THE BACCHAE", "NOTES ON THE BACCHAE"),
    "trojan-women": ("gutenberg/pg35171.txt", "TROJAN WOMEN", "THE TROJAN WOMEN", "NOTES ON THE TROJAN WOMEN"),
    # pg8418 prints Hippolytus and the Bacchae; no heading between cast and play.
    "hippolytus": ("gutenberg/pg8418.txt", "HIPPOLYTUS", "DRAMATIS PERSONAE", "THE BACCHAE"),
    "iphigenia-in-tauris": ("gutenberg/pg5063.txt", "IPHIGENIA IN TAURIS", "THE IPHIGENIA IN TAURIS", "NOTES TO IPHIGENIA IN TAURIS"),
    "rhesus": ("gutenberg/pg35170.txt", "RHESUS", "RHESUS", "NOTES"),
    "electra-eur": ("gutenberg/pg14322.txt", "ELECTRA", "ELECTRA", "NOTES TO THE ELECTRA"),
    "alcestis": ("gutenberg/pg10523.txt", "ALCESTIS", "ALCESTIS", "NOTES"),
    "frogs": ("wikisource/frogs-murray-1912.html", "FROGS", "", ""),
}

_CHARACTERS = re.compile(r"^\s*(?:CHARACTERS|DRAMATIS PERSONAE)")
# NAME, an optional (direction), optional stops: "CASSANDRA (_whispering_)."
_CUE_LINE = re.compile(r"^([A-Z][A-Z0-9 '’\-]*?)\s*(\(.*\))?\s*\.*$")
# A whole italic line, bracketed or not: "_Some Women._", "(_The dash ..._)".
_ITALIC_LINE = re.compile(r"^\(?_[^_]*_\)?\.?$")
# A note call "[1]", or the Rhesus's Greek verse range "[vv. 11-28]".
_NOTE_CALL = re.compile(r"\s*\[(?:\d+|vv?\.\s*[\d\s\-–,]+)\]")
_STAR_RULE = re.compile(r"^[*\s]+$")  # "* * * * *", a section break
# A cue whose (direction) runs onto the next line: "TALTHYBIUS (_bending over ..."
_OPEN_CUE = re.compile(r"^[A-Z][A-Z' ]+\s*\([^)]*$")
# A lyric label, "[_Strophe_ 1.": its bracket never closes, and the verse
# below it is verse, so the label ends with its line.
_LYRIC_LABEL = re.compile(r"^\[_?(?:Str(?:ophe)?|Antistr(?:ophe)?|Epode|Mesode)(?![a-z])", re.I)
# A cue and its half-line of verse on one line: "HECUBA.      Peace, child."
_CUE_AND_VERSE = re.compile(r"^([A-Z][A-Z' ]+)\.\s{2,}(\S.*)$")
# A page's running head left in the text (pg8418 prints "EURIPIDES" mid-speech).
_RUNNING_HEADS = frozenset({"AESCHYLUS", "SOPHOCLES", "EURIPIDES"})


def read_text(path: Path) -> str:
    """Gutenberg's ``-8`` files are Latin-1; the rest UTF-8."""
    data = Path(path).read_bytes()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def _plain(text: str) -> str:
    """Gutenberg italic marks go: "The_ NURSE _is" -> "The NURSE is"."""
    return collapse_ws(text.replace("_", "")).strip()


def _fold(name: str) -> str:
    """"PLATHANÊ" -> "PLATHANE": the cue reader takes plain capitals only."""
    return "".join(ch for ch in unicodedata.normalize("NFKD", name) if not unicodedata.combining(ch))


def _cue_line(line: str) -> tuple[str, str] | None:
    """``(cue, direction)`` for a Gutenberg speaker line."""
    match = _CUE_LINE.match(_fold(line))
    if not match or any(ch.islower() for ch in match.group(1)):
        return None
    cue = _cue(match.group(1).strip())
    if cue is None or cue[1]:
        return None
    paren = line[line.find("(") :].rstrip(" .") if match.group(2) else ""
    return cue[0], _plain(paren)


def convert_gutenberg(text: str, title: str, *, start: str, end: str) -> Converted:
    lines = text.splitlines()
    cast = next(i for i, line in enumerate(lines) if _CHARACTERS.match(line))
    head = next(i for i in range(cast, len(lines)) if lines[i].strip() == start)
    stop = next(
        (i for i in range(head + 1, len(lines)) if lines[i].strip().startswith((end, "*** END"))),
        len(lines),
    )
    # Stripped lines, None at each blank-line paragraph edge.
    flat: list[str | None] = []
    for raw in lines[head + 1 : stop]:
        line = _NOTE_CALL.sub("", raw).strip()
        if line.startswith("[Illustration") or line in _RUNNING_HEADS or (line and _STAR_RULE.match(line)):
            continue
        if line and flat and flat[-1] and _OPEN_CUE.match(_fold(flat[-1])):
            flat[-1] = f"{flat[-1]} {line}"
        elif line:
            flat.append(line)
        elif flat and flat[-1] is not None:
            flat.append(None)

    def is_speech(k: int) -> bool:
        # The next line after a cue is verse: a direction or scene note that
        # runs on is skipped to its paragraph's end, a one-line one (a lyric
        # label, "[...]", "_..._") and cast entries line by line.
        skipping = False
        for line in flat[k + 1 :]:
            if line is None:
                skipping = False
                continue
            if skipping:
                continue
            if _LYRIC_LABEL.match(line) or _ITALIC_LINE.match(line) or (line.startswith("[") and "]" in line):
                continue
            if line.startswith(("[", "_", "SCENE")):
                skipping = True
                continue
            if _CAST_ENTRY.match(line):
                continue
            return _cue_line(line) is None and any(ch.islower() for ch in line)
        return False

    first = next(k for k, line in enumerate(flat) if line and _cue_line(line) and is_speech(k))

    items: list[tuple[str, ...]] = []
    # Before the first cue only the scene paragraphs count (not a cast list).
    para: list[str] = []
    for line in flat[:first] + [None]:
        if line is not None:
            para.append(line)
            continue
        if para and para[0].startswith(("[", "_", "SCENE")):
            items.append(("dir", _plain(" ".join(para))))
        para = []

    direction: list[str] | None = None

    def close() -> None:
        nonlocal direction
        if direction:
            items.append(("dir", _plain(" ".join(direction))))
        direction = None

    for line in flat[first:]:
        if line is None:
            close()  # an unclosed bracket ends with its paragraph
            items.append(("para",))
            continue
        if direction is None and line.startswith("["):
            direction = []
        if direction is not None:
            head_, sep, tail = line.partition("]")
            direction.append(head_ + sep)
            if sep:
                close()
                if tail.strip():
                    items.append(("line", _plain(tail)))
            elif len(direction) == 1 and _LYRIC_LABEL.match(line):
                close()
            continue
        if _ITALIC_LINE.match(line):
            items.append(("dir", _plain(line)))  # "_Some Women._"
            continue
        cue = _cue_line(line)
        if cue:
            items.append(("cue", cue[0]))
            if cue[1]:
                items.append(("dir", cue[1]))
            continue
        shared = _CUE_AND_VERSE.match(_fold(line))
        if shared and any(ch.islower() for ch in shared.group(2)):
            name = _cue(shared.group(1).strip())
            if name and not name[1]:
                rest = _plain(line[shared.start(2) :])
                items.append(("cue", name[0]))
                # "LEADER.   [_Antistrophe._" carries a lyric label, not verse.
                items.append(("dir" if rest.startswith("[") else "line", rest))
                continue
        items.append(("line", _plain(line)))
    close()
    text_out, written = write_turn_text(title, items)
    return Converted(text_out, 0, written)


def _ws_text(el) -> tuple[str, bool]:
    """Block text with small capitals in capitals; whether any text before
    the first "(" is italic (a centred direction, not a cue)."""
    parts: list[str] = []
    italic_head = False

    def add(text: str, italic: bool) -> None:
        nonlocal italic_head
        if "(" not in "".join(parts) and italic and text.strip():
            italic_head = True
        parts.append(text)

    def walk(node, in_italic: bool, in_upper: bool) -> None:
        tag = node.tag.lower() if isinstance(node.tag, str) else ""
        classes = (node.get("class") or "").split()
        if tag in ("style", "link", "sup") or "pagenum" in classes or "ws-noexport" in classes:
            return
        if tag == "br":
            parts.append("\n")
            return
        up = in_upper or "smallcaps" in classes
        it = in_italic or tag in ("i", "em")
        if node.text:
            add(node.text.upper() if up else node.text, it)
        for child in node:
            walk(child, it, up)
            if child.tail:
                add(child.tail.upper() if up else child.tail, it)

    walk(el, False, False)
    return "".join(parts), italic_head


def convert_wikisource(html: str, title: str) -> Converted:
    root = lxml.html.fromstring(html).xpath('//div[contains(@class, "prp-pages-output")]')[0]
    items: list[tuple[str, ...]] = []
    for el in root:
        tag = el.tag.lower() if isinstance(el.tag, str) else ""
        classes = (el.get("class") or "").split()
        if tag not in ("p", "div") or "__nop" in classes or "wst-dhr" in classes:
            continue
        text, italic_head = _ws_text(el)
        if tag == "p":
            for line in text.split("\n"):
                if line.strip():
                    items.append(("line", collapse_ws(line).strip()))
            items.append(("para",))
            continue
        flat = collapse_ws(text).strip()
        if not flat:
            continue
        if ("wst-dent" in classes or "wst-right" in classes) and not flat.startswith(("[", "(")):
            # An indented lyric (the frogs' song), not a direction.
            for line in text.split("\n"):
                if line.strip():
                    items.append(("line", collapse_ws(line).strip()))
            items.append(("para",))
            continue
        if "wst-center" in classes:
            if el.xpath('.//span[contains(@style, "font-size")]'):
                continue  # the play's title
            name, paren, rest = flat.partition("(")
            # A centred italic sentence is a direction; a short italic label
            # ("Semi-Chorus I.", "Aeschylus and Euripides.") is a cue.
            label = len(name.split()) <= 4 and name.strip().endswith(".") or bool(paren)
            if not flat.startswith("[") and (not italic_head or label):
                cue = _cue(_fold(name.strip().rstrip(".").upper()))
                if cue and not cue[1]:
                    items.append(("cue", cue[0]))
                    if paren:
                        items.append(("dir", (paren + rest).strip().rstrip(".")))
                    continue
        items.append(("dir", flat))  # an indented, right-set or centred direction
    text_out, written = write_turn_text(title, items)
    return Converted(text_out, 0, written)


def convert_play(work_id: str) -> Converted:
    source, title, start, end = PLAYS[work_id]
    raw = read_text(SOURCES_DIR / source)
    if source.endswith(".html"):
        return convert_wikisource(raw, title)
    return convert_gutenberg(raw, title, start=start, end=end)


def main() -> int:
    out_dir = SOURCES_DIR / "bench" / "murray"
    out_dir.mkdir(parents=True, exist_ok=True)
    for work_id in PLAYS:
        result = convert_play(work_id)
        (out_dir / f"{work_id}.txt").write_text(result.text, encoding="utf-8")
        print(f"{work_id}: speeches={result.speeches}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
