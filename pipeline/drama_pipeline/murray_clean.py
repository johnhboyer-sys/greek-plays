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
# A cue whose bracketed direction opens on the same line and wraps a
# turnover onto the next: "CASSANDRA. [By an effort she regains mastery of
# herself, and speaks" / "directly to the Leader.]" (agamemnon.txt:1613-1614,
# B4, 2026-09-17). One space, unlike `_CUE_AND_VERSE`'s two.
_CUE_AND_OPEN_BRACKET = re.compile(r"^([A-Z][A-Z' ]+)\.\s\[(?P<rest>.*)$")
# A page's running head left in the text (pg8418 prints "EURIPIDES" mid-speech).
_RUNNING_HEADS = frozenset({"AESCHYLUS", "SOPHOCLES", "EURIPIDES"})
# Project Gutenberg's page-reference marker (pg27673, the only Murray source
# that carries them): "_[Sidenote: vv. 87-99]_", a printer's page-boundary
# note, not verse and not stage business (B4, 2026-09-17). `_NOTE_CALL`
# already drops the plain `[vv. N-N]` form; this is the "Sidenote:"-prefixed
# one, own-line and underscore-wrapped.
_SIDENOTE = re.compile(r"^_?\[Sidenote:[^\]]*\]_?\.?$", re.I)
# A cue's own parenthetical aside can be followed by a metre rubric on the
# same line ("CHORUS (_various voices confusedly_).      [_Strophe._",
# rhesus 23-33, B round 3 item 2, 2026-09-17): the rubric belongs to neither
# the cue nor the verse and is dropped, same as an own-line lyric label (B3).
_CUE_PAREN_AND_RUBRIC = re.compile(r"^([A-Z][A-Z' ]+)\s*(\(.*\))\.\s{2,}(\[.*)$")
# Murray's own Gutenberg convention for a short mid-speech aside never
# prints a `]` at all ("[_Turning upon the Herald._" / "[_Turning furiously
# upon_ HELEN.") -- the direction ends where its own sentence does. But a
# bare sentence-final stop is not enough on its own: a real multi-sentence
# direction's FIRST wrap line often ends a sentence too ("[_As they cease,_
# CLYTEMNESTRA _comes from the Palace with Attendants._ She has finished
# her prayer..." -- agamemnon, B round 3b item 1) while the italics that
# introduced it are still open, or the sentence that ends there is only the
# first of several ("[_The huntsmen have gathered about the altar of_
# ARTEMIS. HIPPOLYTUS _now advances..._]" -- hippolytus, same item). Two
# checks, not one raw ".!?$":
#   1. Italics parity: an odd running count of `_` means the line ends
#      mid-italic-span (the direction's own sentence has not actually
#      finished, whatever punctuation the line happens to end with).
#   2. Even so, a genuine complete aside is followed by real verse -- the
#      next line carries no unclosed `_` of its own. A direction's own
#      continuation line always reopens italics ("HIPPOLYTUS _now
#      advances..."); a poet's mid-verse emphasis word closes on the same
#      line ("_She_ cometh first...") and does not count.
# No line-count cap: a genuine direction (bacchae's Agave entrance,
# iphigenia-in-tauris's procession, alcestis's Heracles entrance) runs as
# many raw lines as it needs and still closes on its own last sentence or
# `]`; nothing in this corpus runs past that without one.
_SENTENCE_END = re.compile(r"[.!?]+['’\"]?_?$")


def _direction_line_closes(direction: list[str], line: str, next_line: str | None) -> tuple[bool, str]:
    """Add `line` to an open `direction` accumulator; report whether it now
    closes, and any text trailing a literal `]` on this line. A direction
    closes at a literal `]` (as before), at a lyric label on its own first
    line, or at a line that ends its own sentence with italics balanced
    (not reopened) and whose next line -- `None` at a blank line or a
    paragraph edge -- carries no unclosed italics of its own."""
    head_, sep, tail = line.partition("]")
    direction.append(head_ + sep)
    if sep:
        return True, tail
    if len(direction) == 1 and _LYRIC_LABEL.match(line):
        return True, ""
    italics_open = sum(seg.count("_") for seg in direction) % 2 == 1
    if not italics_open and _SENTENCE_END.search(line):
        if next_line is None or next_line.count("_") % 2 == 0:
            return True, ""
    return False, ""


def _italic_paragraph(lines: list[str]) -> bool:
    """A paragraph printed wholly in italics except for names in capitals is
    a stage direction with no bracket ("_Enter from the other side_ THANATOS;
    _a crouching black-haired and winged figure ..._", Alcestis): once the
    italic spans and the capitals go, no lowercase letter is left."""
    text = " ".join(lines)
    if not text.startswith("_") or text.count("_") % 2:
        return False
    rest = re.sub(r"_[^_]*_", " ", text)
    # A sung refrain or a gloss is italic too ("_Sorrow, sing sorrow: but
    # good prevail, prevail!_", Agamemnon): a direction names someone in
    # capitals outside the italics.
    if not re.search(r"[A-Z][A-Z'’\-]+", rest):
        return False
    rest = re.sub(r"[A-Z][A-Z'’\-]*", " ", rest)
    return not any(ch.islower() for ch in rest)


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
        if (
            line.startswith("[Illustration")
            or line in _RUNNING_HEADS
            or (line and _STAR_RULE.match(line))
            or _SIDENOTE.match(line)
        ):
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

    skip_to = -1
    for idx, line in enumerate(flat[first:], start=first):
        if idx < skip_to:
            continue
        if line is None:
            close()  # an unclosed bracket ends with its paragraph
            items.append(("para",))
            continue
        if direction is None and line.startswith("_") and not _ITALIC_LINE.match(line):
            # A wholly italic paragraph (capitals for names) is a direction
            # the page prints without brackets (2026-09-14, John).
            end = idx
            while end < len(flat) and flat[end] is not None:
                end += 1
            para_lines = [ln for ln in flat[idx:end] if ln]
            if _italic_paragraph(para_lines):
                items.append(("dir", _plain(" ".join(para_lines))))
                skip_to = end
                continue
        if direction is None and line.startswith("["):
            direction = []
        if direction is not None:
            next_line = flat[idx + 1] if idx + 1 < len(flat) else None
            closed, tail = _direction_line_closes(direction, line, next_line)
            if closed:
                close()
                if tail.strip():
                    items.append(("line", _plain(tail)))
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
        paren_rubric = _CUE_PAREN_AND_RUBRIC.match(_fold(line))
        if paren_rubric and _LYRIC_LABEL.match(paren_rubric.group(3)):
            name = _cue(paren_rubric.group(1).strip())
            if name and not name[1]:
                items.append(("cue", name[0]))
                paren_start = line.find("(")
                paren_end = line.find(")", paren_start) + 1
                items.append(("dir", _plain(line[paren_start:paren_end])))
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
        cue_bracket = _CUE_AND_OPEN_BRACKET.match(line)
        if cue_bracket:
            name = _cue(_fold(cue_bracket.group(1).strip()))
            if name and not name[1]:
                items.append(("cue", name[0]))
                direction = []
                next_line = flat[idx + 1] if idx + 1 < len(flat) else None
                closed, tail = _direction_line_closes(direction, "[" + cue_bracket.group("rest"), next_line)
                if closed:
                    close()
                    if tail.strip():
                        items.append(("line", _plain(tail)))
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
