"""E. D. A. Morshead's Aeschylus, Wikisource's proofread transcriptions ->
verse-own-line turn-text.

Two markup shapes, one book each. *Four Plays of Aeschylus* (1908, validated
by Wikisource's own proofreaders): ProofreadPage `<pages>` transclusion, one
block per front-matter section (title page, argument, dramatis personae) and
one big block for the play itself -- always by far the largest, so front
matter and any trailing footnote reflist (their own tiny blocks) fall away
by picking the block with the most children (`convert_four_plays`). Cues are
small-capitals spans, as in Murray's Wikisource Frogs
(``murray_clean.convert_wikisource``), which this models on and reuses
(`_ws_text`) for text extraction.

*The House of Atreus* (1881 first edition): the whole play sits in one
`<poem>` extension block as a flat, `<br>`-separated run of text -- a cue is
bold ("Aegisthus:"), a stage direction italic; punctuation and page numbers
carry no wrapper at all (`convert_house_of_atreus`). An entrance direction
and the cue it introduces sometimes share one printed line ("Enter Herald:",
"Re-enter Clymemnestra:" -- Agamemnon spells her name that way throughout,
Wikisource's proofread reading, kept as printed).

    python -m drama_pipeline.morshead_clean   # rewrite sources/bench/morshead/*.txt
"""

from __future__ import annotations

import re

import lxml.html

from .config import SOURCES_DIR
from .johnston_clean import Converted, _cue, write_turn_text
from .murray_clean import _fold, _ws_text
from .stage1_common import collapse_ws

# Work id -> (vendored HTML filename, title line written at the top).
FOUR_PLAYS: dict[str, tuple[str, str]] = {
    "persians": ("persians.html", "THE PERSIANS"),
    "prometheus-bound": ("prometheus-bound.html", "PROMETHEUS BOUND"),
    "seven-against-thebes": ("seven-against-thebes.html", "THE SEVEN AGAINST THEBES"),
    "suppliants-aesch": ("suppliants-aesch.html", "THE SUPPLIANT MAIDENS"),
}
HOUSE_OF_ATREUS: dict[str, tuple[str, str]] = {
    "agamemnon": ("agamemnon.html", "AGAMEMNON"),
    "libation-bearers": ("libation-bearers.html", "THE LIBATION-BEARERS"),
    "eumenides": ("eumenides.html", "THE FURIES"),
}
PLAYS: dict[str, tuple[str, str]] = {**FOUR_PLAYS, **HOUSE_OF_ATREUS}

# John, 2026-09-09 (REVIEW-CHECKLIST 8): Morshead prints the parodos, the
# kommos, and the closing lament of Seven against Thebes as long undivided
# blocks, and never labels Ismene; break them where each of Murray's segments
# begins, so every Greek speech has an English anchor. First done by hand in
# the OCR bench (2c22ecc, 75 labels); the same cuts here, applied to the
# Wikisource text by `_divide`: (cue, opening words of the verse line that
# starts the new speech), in play order, each sought after the last. One of
# the 75 is dropped: Murray's division at 1001 falls inside one printed line
# ("And woe! for their pitiful end, who once were our love and our care!").
SEVEN_DIVISIONS: tuple[tuple[str, str], ...] = (
    ('CHORUS', 'As a torrent'),
    ('CHORUS', 'They stream '),
    ('CHORUS', 'They storm t'),
    ('CHORUS', 'O gods high-'),
    ('CHORUS', 'Not here mus'),
    ('CHORUS', 'And now, eve'),
    ('CHORUS', 'Mine eyes fe'),
    ('CHORUS', 'Is thy hand '),
    ('CHORUS', 'Look down up'),
    ('CHORUS', 'And ye, O pr'),
    ('CHORUS', 'Thou too, O '),
    ('CHORUS', 'I mark his w'),
    ('CHORUS', 'That, haled '),
    ('CHORUS', 'Woe, woe for y'),
    ('CHORUS', 'One billow s'),
    ('MESSENGER', 'Did hands me'),
    ('CHORUS', 'A twofold so'),
    ('CHORUS', 'Alas, my sis'),
    ('CHORUS', 'Look up, loo'),
    ('CHORUS', 'Alas! of all'),
    ('ANTIGONE', 'One, proud o'),
    ('CHORUS', 'Alack, on ho'),
    ('ISMENE', 'One strove t'),
    ('CHORUS', 'And lo, the '),
    ('ANTIGONE', 'Each in the l'),
    ('CHORUS', 'Yea, deep an'),
    ('ISMENE', 'Hark, how th'),
    ('CHORUS', 'They strove '),
    ('ANTIGONE', 'Here, by the'),
    ('CHORUS', 'Alas, a pier'),
    ('ISMENE', 'Say we, abov'),
    ('CHORUS', 'Beyond all w'),
    ('ANTIGONE', 'Yea, from on'),
    ('CHORUS', 'Now is their h'),
    ('ISMENE', 'They have th'),
    ('CHORUS', 'Alas, alas! '),
    ('ANTIGONE', 'Thou wert sm'),
    ('ANTIGONE', 'By the spear'),
    ('ANTIGONE', 'Take voice, '),
    ('ANTIGONE', 'Lay the slai'),
    ('ANTIGONE', 'Our soul in '),
    ('ANTIGONE', 'Ah, woe for '),
    ('ISMENE', 'Unbrotherly '),
    ('ANTIGONE', 'And woe for '),
    ('ISMENE', 'The fray tha'),
    ('ANTIGONE', 'The doom of '),
    ('ANTIGONE', 'Ah, twofold '),
    ('ANTIGONE', 'And double t'),
    ('ISMENE', 'As we stand '),
    ('CHORUS', 'O grievous the fate'),
    ('ANTIGONE', 'O dark were '),
    ('ISMENE', 'That exile h'),
    ('ANTIGONE', 'He slew, but'),
    ('ISMENE', 'He struck do'),
    ('ANTIGONE', 'O lineage ac'),
    ('ANTIGONE', 'Alas, for th'),
    ('ANTIGONE', 'And woe! for'),
    ('CHORUS', 'O grievous the f'),
    ('ANTIGONE', 'By proof hav'),
    ('ISMENE', 'At once and '),
    ('ANTIGONE', 'O brothers belov'),
    ('ISMENE', 'Ye came to t'),
    ('ANTIGONE', 'O grievous t'),
    ('ANTIGONE', 'And grievous'),
    ('ANTIGONE', 'To the house'),
    ('ANTIGONE', 'And to me ab'),
    ('ISMENE', 'Ah God! for '),
    ('ANTIGONE', 'O children d'),
    ('ISMENE', 'Who in madne'),
    ('ANTIGONE', 'Shall ye res'),
    ('ISMENE', 'In the place'),
    ('ANTIGONE', 'Alas for the'),
    ('ANTIGONE', 'Prate thou no more'),
    ('CHORUS', 'But we this '),
)

# The book's last leaf, after Prometheus Bound's own final stage direction
# (Four Plays of Aeschylus prints all four plays in one volume; the printer's
# imprint sits where a fifth play would begin).
_COLOPHON = re.compile(r"^Printed by\b")
# A comma before "and" in a compound cue ("Antigone, Ismene, and Chorus")
# would break `_cue`'s speaker grammar; word order is unaffected by dropping it.
_CUE_COMMA = re.compile(r",\s*")
# An entrance direction sharing its printed line with the cue it introduces.
_ENTRANCE = {"Enter", "Re-enter"}
# A bare, unbolded line that still reads as a cue by shape alone (2+ letters,
# all uppercase): Wikisource's own missing-markup slip, not spoken verse.
_BARE_CUE = re.compile(r"^[A-Z][A-Z '\-]+$")
# A bracketed stage direction inside a `<p>` block that Wikisource left
# unitalicised -- only the word "To" or nothing at all sits in an `<i>`, so
# `_ws_text` never sees the whole phrase as a direction (prometheus-bound
# review finding 5, 2026-09-17: "(To PROMETHEUS)", "(Aside)", an unclosed
# "[A pause."). Read by shape alone, regardless of markup; the same three
# shapes the Loeb parser (`stage1_turn_english._DIRECTION_CUE`) already
# recognises, applied at the whole-line level `<p>` text uses.
_PLAIN_DIRECTION_LINE = re.compile(r"^\(To [^)]+\)$|^\(Aside\)$|^\[.+", re.I)
_NOISE = "'’ "  # a stray straight/curly quote and space either side of a run


def read_html(work_id: str) -> str:
    name, _title = PLAYS[work_id]
    return (SOURCES_DIR / "wikisource" / "morshead" / name).read_text(encoding="utf-8")


def _divide(items: list[tuple[str, ...]], divisions: tuple[tuple[str, str], ...]) -> list[tuple[str, ...]]:
    """Open a new speech under ``cue`` before the first verse line, after the
    previous division, that starts with ``opening``; every division must fire."""
    out: list[tuple[str, ...]] = []
    pending = list(divisions)
    for item in items:
        if pending and item[0] == "line" and item[1].startswith(pending[0][1]):
            out.append(("cue", pending.pop(0)[0]))
        out.append(item)
    if pending:
        raise ValueError(f"division not found in the text: {pending[0]!r}")
    return out


def _emit_verse_lines(text: str, items: list[tuple[str, ...]]) -> None:
    """Append ``text``'s lines as ``("line", ...)`` items, except a whole
    line matching `_PLAIN_DIRECTION_LINE`, which is a stage direction the
    source left unitalicised (B8, 2026-09-17) and becomes ``("dir", ...)``
    instead. Shared by the `<p>`-tag path and the indented-reply div path
    ("Layout 2"): a direction can land in either."""
    for line in text.split("\n"):
        line = collapse_ws(line).strip()
        if not line:
            continue
        if _PLAIN_DIRECTION_LINE.match(line):
            items.append(("dir", line))
        else:
            items.append(("line", line))


def convert_four_plays(html: str, title: str, divisions: tuple[tuple[str, str], ...] = ()) -> Converted:
    blocks = lxml.html.fromstring(html).xpath('//div[contains(@class, "prp-pages-output")]')
    root = max(blocks, key=len)  # front matter and a footnote reflist are tiny
    items: list[tuple[str, ...]] = []
    for el in root:
        tag = el.tag.lower() if isinstance(el.tag, str) else ""
        classes = (el.get("class") or "").split()
        if tag not in ("p", "div") or "__nop" in classes or "wst-dhr" in classes:
            continue
        text, italic_head = _ws_text(el)
        if tag == "p":
            _emit_verse_lines(text, items)
            items.append(("para",))
            continue
        flat = collapse_ws(text).strip()
        if not flat:
            continue
        if _COLOPHON.match(flat):
            continue  # Prometheus Bound only: "Printed by R. & R. Clark, Limited, Edinburgh."
        if "wst-center" in classes:
            if el.xpath('.//span[contains(@style, "font-size")]'):
                continue  # the play's title
            name, paren, rest = flat.partition("(")
            name = _CUE_COMMA.sub(" ", name)
            label = len(name.split()) <= 4 and name.strip().endswith(".") or bool(paren)
            if not flat.startswith("[") and (not italic_head or label):
                cue = _cue(_fold(name.strip().rstrip(".").upper()))
                if cue and not cue[1]:
                    items.append(("cue", cue[0]))
                    if paren:
                        items.append(("dir", (paren + rest).strip().rstrip(".")))
                    continue
            items.append(("dir", flat))
            continue
        if flat.startswith(("[", "(")):
            items.append(("dir", flat))
            continue
        # Any other div (wst-dent, wst-right, or a bare margin-left div under a
        # centred cue, "Layout 2"'s indented-response convention): verse.
        _emit_verse_lines(text, items)
        items.append(("para",))
    text_out, written = write_turn_text(title, _divide(items, divisions))
    return Converted(text_out, 0, written)


def _poem_runs(el):
    """(text, style) runs in document order, style "b" / "i" / None; a
    `<br>` yields ("<BR>", None); `<sup>` (a footnote call) is dropped."""

    def walk(node, style):
        if node.text:
            yield node.text, style
        for child in node:
            tag = child.tag.lower() if isinstance(child.tag, str) else ""
            if tag == "br":
                yield "<BR>", None
            elif tag == "sup":
                pass
            elif tag in ("b", "strong"):
                yield from walk(child, "b")
            elif tag in ("i", "em"):
                yield from walk(child, "i")
            else:
                yield from walk(child, style)
            if child.tail:
                yield child.tail, style

    yield from walk(el, None)


def _poem_lines(el):
    line: list[tuple[str, str | None]] = []
    for text, style in _poem_runs(el):
        if text == "<BR>":
            yield line
            line = []
        else:
            line.append((text, style))
    if line:
        yield line


def _joined(runs) -> str:
    return collapse_ws("".join(t for t, _s in runs).replace("​", "").replace("\xa0", " ")).strip()


def _emit_poem_line(runs: list[tuple[str, str | None]], items: list[tuple[str, ...]]) -> None:
    flat = _joined(runs)
    if not flat:
        items.append(("para",))
        return
    bold = [i for i, (t, s) in enumerate(runs) if s == "b" and t.strip()]
    if len(bold) == 1 and _joined([runs[bold[0]]]).endswith(":"):
        bi = bold[0]
        pre = _joined(runs[:bi]).strip(_NOISE)
        raw_name = _joined([runs[bi]]).rstrip(":").strip()
        post = _joined(runs[bi + 1 :])
        if pre in _ENTRANCE:
            items.append(("dir", f"{pre}."))
        elif pre:
            raw_name = collapse_ws(f"{pre} {raw_name}")
        cue = _cue(_fold(raw_name.upper()))
        if not cue or cue[1]:
            raise ValueError(f"poem cue {raw_name!r} did not parse as a speaker")
        items.append(("cue", cue[0]))
        if post.startswith("(") and post.endswith(")"):
            items.append(("dir", post))
        elif post:
            items.append(("line", post))
        return
    italic_text = _joined([(t, s) for t, s in runs if s == "i"])
    plain_text = _joined([(t, s) for t, s in runs if s != "i"]).strip(_NOISE)
    if italic_text and not plain_text:
        items.append(("dir", italic_text))
        return
    if not bold and not italic_text and _BARE_CUE.fullmatch(flat):
        # A cue Wikisource forgot to bold (Eumenides: "OSESTES", plain, no
        # colon, between two Chorus/Orestes exchanges bolded as usual) --
        # real spoken verse is never one bare, all-caps word standing alone
        # on its own line.
        cue = _cue(_fold(flat))
        if cue and not cue[1]:
            items.append(("cue", cue[0]))
            return
    items.append(("line", flat))


def convert_house_of_atreus(html: str, title: str) -> Converted:
    root = lxml.html.fromstring(html).xpath('//div[contains(@class, "poem")]')[0]
    p = root[0]
    items: list[tuple[str, ...]] = []
    for runs in _poem_lines(p):
        _emit_poem_line(runs, items)
    text_out, written = write_turn_text(title, items)
    return Converted(text_out, 0, written)


def convert_play(work_id: str) -> Converted:
    _name, title = PLAYS[work_id]
    html = read_html(work_id)
    if work_id in FOUR_PLAYS:
        divisions = SEVEN_DIVISIONS if work_id == "seven-against-thebes" else ()
        return convert_four_plays(html, title, divisions)
    return convert_house_of_atreus(html, title)


def main() -> int:
    out_dir = SOURCES_DIR / "bench" / "morshead"
    out_dir.mkdir(parents=True, exist_ok=True)
    for work_id in PLAYS:
        result = convert_play(work_id)
        (out_dir / f"{work_id}.txt").write_text(result.text, encoding="utf-8")
        print(f"{work_id}: speeches={result.speeches}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
