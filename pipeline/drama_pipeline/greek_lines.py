"""The committed Greek: one line-level file per play, corpus/greek/<play>.tsv.

The build reads these for a play's Greek; it never runs Diogenes and never
sees the TLG. `python -m drama_pipeline.extract` makes them, on a machine that
has the TLG (HANDOFF-PORTABILITY.md, decision 1). Every play's reference Greek
has one; the other Greek editions (Perseus and OCR'd TEI under sources/) are
read from there and have none.

A file is the printed lines of one play, in printed order (never sorted):

    # work: agamemnon
    # edition: Murray, Aeschyli tragoediae, 2nd ed. (OCT, 1955)
    # columns: n	text
    t	ΑΓΑΜΕΜΝΩΝ
    1	{ΦΥΛΑΞ} θεοὺς μὲν αἰτῶ τῶνδ' ἀπαλλαγὴν πόνων
    208-209	…

`n` is the line's own number as the edition prints it ("1", "141a", "208-209",
"post 410", "t" for the title line). `text` is the line with runs of white
space made one space; each speaker label the edition prints in the line (the
export's <label type="speaker">, which also carries strophe marks) stands in
braces where it stands, `{Χο.}`, `{[στρ. α.}`; the export's ASCII angle
brackets are written ⟨ ⟩, as stage 1 has always shown them. Nothing else is
changed: no NFC. The title line is the title's text alone. The `# edition:`
line is the manifest's `work.greek_edition`: the files name editions, never
the digital source they were read from (John's rule for every public file,
aristotle-reader's decision 3). `extract` holds the export's own source
statement to the manifest's `work.expected_sourcedesc` before it writes, and
that statement goes no further. Stage 1 does the reading: speakers
from strophe marks, lacunae, transpositions, repeated refs, ref fixes, metrical
schemes, hyphens. No markup, no beta code, no Diogenes XML:
pipeline/tests/test_corpus_greek.py holds that line.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import NamedTuple

from lxml import etree

from .config import REPO_ROOT, Manifest

CORPUS_DIR = REPO_ROOT / "corpus" / "greek"
COLUMNS = "# columns: n\ttext"
OPEN, CLOSE = "{", "}"


class Row(NamedTuple):
    n: str      # the line's own number as printed: "1", "141a", "208-209", "post 410", "t"
    text: str   # the line, white space collapsed, speaker labels in braces


def work_name(manifest: Manifest) -> str:
    return manifest.path.stem.removesuffix("-public")


def corpus_path(manifest: Manifest) -> Path:
    return CORPUS_DIR / f"{work_name(manifest)}.tsv"


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _local(el) -> str:
    return etree.QName(el).localname if isinstance(el.tag, str) else ""


_ANGLES = str.maketrans("<>", "⟨⟩")
# The children an exported play line holds (all 44 plays, 2026-11-23): its
# speaker or title label, a page break, a line break, a run of space, and a
# spaced-out word. Anything else is a shape no stage 1 here has met.
_LINE_CHILDREN = frozenset({"label", "pb", "lb", "space", "hi"})


def flatten_line(el) -> str:
    """A play's <l> as one line of the file. The text and every child but a
    speaker label give their text in order, as stage 1 always read them
    (`"".join(child.itertext())`, then the tail); a speaker label gives its
    text, white space collapsed, in braces. Then runs of white space become
    one space, and ASCII angle brackets become ⟨ ⟩."""
    parts = [el.text or ""]
    for child in el:
        if not isinstance(child.tag, str):          # a comment or processing instruction
            parts.append(child.tail or "")
            continue
        if _local(child) == "label" and child.get("type") == "speaker":
            # No space added round the braces: stage 1 drops a strophe mark
            # outright, and the words either side must meet as they did.
            parts.append(f"{OPEN}{_flat(''.join(child.itertext()))}{CLOSE}")
        else:
            parts.append("".join(child.itertext()))
        parts.append(child.tail or "")
    raw = "".join(el.itertext())
    if OPEN in raw or CLOSE in raw:
        # A brace of the edition's own would read back as a label's edge.
        raise ValueError(f"line {el.get('n')!r} prints a brace; the line file keeps braces for labels")
    return _flat("".join(parts)).translate(_ANGLES)


def title_text(el) -> str:
    """The title line (`n="t"`) as stage 1 hashes it: all its text, white
    space collapsed (stage1_greek._line_text)."""
    return _flat("".join(el.itertext()))


def sourcedesc(tree) -> str:
    """The export's <sourceDesc>, as stage1_greek._check_sourcedesc reads it.
    Never written to a line file."""
    return " ".join(_flat("".join(node.itertext())) for node in tree.findall(".//{*}sourceDesc"))


def rows_from_tree(tree, name: str = "<xml>") -> list[Row]:
    """Every <l> of the export's body, in document order.

    Raises where the line file could not say what the XML says, or where the
    export takes a shape no stage 1 of this reader has met: anything in the
    body but its lines, a line inside a line, a child of a line other than
    the five in _LINE_CHILDREN, a label that is neither a speaker's nor the
    title's, a line with no number, a play with no lines."""
    body = tree.find(".//{*}body")
    if body is None:
        raise ValueError(f"{name}: no TEI body")
    if _flat(body.text or ""):
        raise ValueError(f"{name}: text in the body outside a line")
    rows: list[Row] = []
    for el in body:
        if not isinstance(el.tag, str):
            if _flat(el.tail or ""):
                raise ValueError(f"{name}: text in the body outside a line")
            continue
        if _local(el) != "l":
            raise ValueError(f"{name}: a <{_local(el)}> in the body; the export has only lines there")
        if _flat(el.tail or ""):
            raise ValueError(f"{name}: text in the body outside a line")
        n = el.get("n")
        if not n or not n.strip():
            raise ValueError(f"{name}: a line with no number")
        for child in el.iter():
            if child is el or not isinstance(child.tag, str):
                continue
            tag = _local(child)
            if tag == "l":
                raise ValueError(f"{name}: a line inside line {n!r}")
            if child.getparent() is el and tag not in _LINE_CHILDREN:
                raise ValueError(f"{name}: line {n!r} holds a <{tag}>, a shape stage 1 has not met")
            if tag == "label" and child.get("type") not in ("speaker", "head"):
                raise ValueError(f"{name}: line {n!r} holds a label of type {child.get('type')!r}")
            if tag == "label" and child.getparent() is not el:
                raise ValueError(f"{name}: line {n!r} holds a label inside a <{_local(child.getparent())}>")
        rows.append(Row(n, title_text(el) if n == "t" else flatten_line(el)))
    if not rows:
        raise ValueError(f"{name}: the play has no lines")
    return rows


def rows_from_xml(xml_path: Path) -> tuple[list[Row], str]:
    tree = etree.parse(str(xml_path))
    return rows_from_tree(tree, xml_path.name), sourcedesc(tree)


_FIELD_BREAK = re.compile(r"[\t\n\r]")


def format_tsv(rows: list[Row], work: str, edition: str) -> str:
    out = [f"# work: {_flat(work)}", f"# edition: {_flat(edition)}", COLUMNS]
    for row in rows:
        if any(_FIELD_BREAK.search(f) for f in row):
            raise ValueError(f"{work}: a field of line {row.n!r} holds a tab or a line break")
        if row.text != _flat(row.text) or row.n != _flat(row.n) or not row.n:
            raise ValueError(f"{work}: line {row.n!r} is not flat")
        out.append("\t".join(row))
    return "\n".join(out) + "\n"


def parse_tsv(text: str, name: str = "line file") -> tuple[list[Row], str]:
    """(rows, edition) from a line file."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    # Three heading lines and no more: a fourth "# " line would be a place to
    # keep anything at all.
    if len(lines) < 3 or not lines[0].startswith("# work: ") or not lines[1].startswith("# edition: ") \
            or lines[2] != COLUMNS:
        raise ValueError(f"{name}: expected # work, # edition, and then the line {COLUMNS!r}")
    rows = []
    for i, line in enumerate(lines[3:], 4):
        fields = line.split("\t")
        if len(fields) != 2 or "\r" in line:
            raise ValueError(f"{name} line {i}: expected 2 tab-separated fields")
        if not fields[0]:
            raise ValueError(f"{name} line {i}: an empty line number")
        rows.append(Row(*fields))
    if not rows:
        raise ValueError(f"{name}: no lines of text")
    return rows, lines[1][len("# edition: "):]


def load(path: Path) -> tuple[list[Row], str]:
    """A committed line file, or XML of the export's shape (the tests' fixtures)."""
    if path.suffix == ".tsv":
        return parse_tsv(path.read_text(encoding="utf-8"), path.name)
    return rows_from_xml(path)


def split_labels(text: str) -> list[tuple[str, str]]:
    """A line's text as parts in order: ("text", …) and ("label", …)."""
    parts: list[tuple[str, str]] = []
    at = 0
    for m in _LABEL.finditer(text):
        parts.append(("text", text[at:m.start()]))
        parts.append(("label", m.group(1)))
        at = m.end()
    parts.append(("text", text[at:]))
    return parts


# ---- what a line file must never hold --------------------------------------
# The Diogenes XML, the TLG's own beta code, or anything that is not a line of
# Greek. The rule that does the work: every character of a line's text, and
# of a label, is a Greek one (its Unicode name says so: the letters, and the
# Greek marks · ; ʹ) or one of the marks in _MARKS, which are all the others
# the 44 editions print. Beta code writes Greek in Latin letters (mh=nin
# a)/eide), and markup needs Latin names or angle brackets, so neither
# survives, with or without punctuation round the words; nor does a Latin
# letter in another dress (ⓐ, ａ, a combining a). The only Latin a file may
# hold is in a label, whole: the strophe marks Coulon and Dain-Mazon print
# (_LABEL_WORDS) and a stanza number (1. to 12.). An editor's new sign is
# added here by hand, after someone has looked at it.
_MARKS = frozenset(
    " .,'"          # space, full stop, comma, elision
    "-–—"           # hyphen (a word broken over two lines), en dash, em dash
    "[]()⟨⟩«»\"‘’"  # the editors' brackets and quotation marks
    "†"             # the crux
    "⏑⏓×"           # the metrical signs some lyric lines print (stage 1 strips them)
)
_LABEL_WORDS = frozenset({"Str.", "Ant.", "Ep.", "Epod.", "Epode."})
_STANZA = re.compile(r"(?:[1-9]|1[0-2])\.")
_LABEL = re.compile(r"\{([^{}]*)\}")
# A line's number: "1", "141a", "208-209", "289/290", "post 410" (and the
# export's "post1226"), "t" for the title. ASCII digits only.
_NUM = r"[1-9][0-9]{0,3}"
_N = re.compile(rf"{_NUM}(?:[a-f]|[-/]{_NUM})?|post ?{_NUM}|t")
# Markup that needs no Latin letter: a tag's angle bracket, a character
# reference. The export's angle brackets are written ⟨ ⟩, so none is left.
_TAG = re.compile(r"[<>]|&#|&[A-Za-z]")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f\x80-\x9f   ]")
_WORK = re.compile(r"# work: [a-z0-9]+(?:-[a-z0-9]+)*")
# The words of a digital source's own statement, which the edition line must
# not hold: a TLG author and work number "(0085: 005)", the canon's author
# epithets ("Trag.", "Comic."), its dates "(c. 6-5 B.C.)", its "Ed. Murray,
# G." and "Repr. 1960", and the names of the disc and the program.
# Case counts: an edition's own "2nd ed." is not the canon's "Ed. Murray".
_SOURCE_WORDS = re.compile(r"\(\s*\d{4}\s*:\s*\d{3}\s*\)|\b(?:Trag|Comic|Phil|Hist|Lyr|Epic|Tragic)\.|B\.\s?C\.|\bEd\.\s|\bRepr\.|"
                           r"\bTLG\b|Thesaurus\s+Linguae|Diogenes")


def not_greek(text: str) -> list[str]:
    return [ch for ch in text if ch not in _MARKS and not unicodedata.name(ch, "").startswith("GREEK")]


def bad_label(label: str) -> bool:
    if not label or label != _flat(label):
        return True
    return any(not (word in _LABEL_WORDS or _STANZA.fullmatch(word) or not not_greek(word))
               for word in label.split(" "))


def forbidden(text: str) -> list[str]:
    """Problems with a line file's contents; empty when it is clean. Every
    line of the file is examined: the three heading lines, each line number,
    each label, and each line of text. The edition line is free text (an
    editor, a title, a year) and gets the control check, a check against
    markup, and a check against the words of a source description; the corpus
    test holds it to the manifest's own words."""
    problems: list[str] = []
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if len(lines) < 4 or not _WORK.fullmatch(lines[0]) or not lines[1].startswith("# edition: ") \
            or lines[2] != COLUMNS:
        return ["not a line file: it must open with # work, # edition and the # columns line, then lines of text"]
    if "\t" in lines[0] or "\t" in lines[1]:
        return ["not a line file: a tab in a heading line"]
    if _SOURCE_WORDS.search(lines[1]):
        problems.append(f"the edition line holds a source description's words: {lines[1][:100]!r}")
    controls = [line for line in lines if _CONTROL.search(line)]
    if controls:
        problems.append(f"a control character in {len(controls)} lines, first: {controls[0][:80]!r}")
    tags = [line for line in lines[:2] if _TAG.search(line)] + \
           [line for line in lines[3:] if _TAG.search(line.split("\t", 1)[-1])]
    if tags:
        problems.append(f"markup in {len(tags)} lines, first: {tags[0][:80]!r}")
    bad_fields, odd, labels, braces, letters = [], [], [], [], 0
    titles = 0
    for line in lines[3:]:
        fields = line.split("\t")
        if len(fields) != 2 or not _N.fullmatch(fields[0]):
            bad_fields.append(line)
            continue
        n, body = fields
        if n == "t":
            titles += 1
        parts = split_labels(body)
        plain = "".join(v for k, v in parts if k == "text")
        if OPEN in plain or CLOSE in plain or (n == "t" and len(parts) > 1):
            braces.append(line)
            continue
        letters += sum(ch.isalpha() for ch in plain)
        if not_greek(plain):
            odd.append(line)
        if any(bad_label(v) for k, v in parts if k == "label"):
            labels.append(line)
    if bad_fields:
        problems.append(f"a line number that is not one, or the wrong number of fields, in {len(bad_fields)} lines, first: {bad_fields[0][:80]!r}")
    if titles > 1:
        problems.append(f"{titles} title lines; a play has one at most")
    if braces:
        problems.append(f"a brace outside a label, or a label in the title, in {len(braces)} lines, first: {braces[0][:80]!r}")
    if odd:
        problems.append(f"characters that are not Greek in {len(odd)} lines, first: {odd[0][:80]!r}")
    if labels:
        problems.append(f"a label that is not a speaker's or a strophe mark in {len(labels)} lines, first: {labels[0][:80]!r}")
    if not letters:
        problems.append("no letters at all")
    return problems
