"""Kosmos Society / CHS Sourcebook play pages -> verse-own-line turn-text.

The Sourcebook prints a Greek line number every fifth line -- ``<sub>5</sub>``,
bold ``5``, ``|5`` or ``[5]``; the CHS Herakles puts it at the end of a verse
line -- and never marks where a speech starts, so these texts pair with the
Greek by speaker turn (``model: turn-text``, ``format: verse-own-line``), not
by line.  The numbers are counted and dropped; bracketed Greek terms
("ordeals [ponoi]") stay as printed.  Footnote calls go, and the play ends
where the notes begin.

    python -m drama_pipeline.kosmos_clean   # rewrite sources/bench/kosmos/*.txt
"""

from __future__ import annotations

import re
import unicodedata
from typing import NamedTuple

import lxml.html

from .config import SOURCES_DIR
from .stage1_common import collapse_ws

# Work id -> the title line written at the top of the text (manifest `play:`).
PLAYS = {
    "seven-against-thebes": "SEVEN AGAINST THEBES",
    "agamemnon": "AGAMEMNON",
    "libation-bearers": "LIBATION BEARERS",
    "eumenides": "EUMENIDES",
    "antigone": "ANTIGONE",
    "oedipus-coloneus": "OEDIPUS AT COLONUS",
    "oedipus-tyrannus": "OEDIPUS TYRANNUS",
    "helen": "HELEN",
    "heracles": "HERAKLES",
    "medea": "MEDEA",
    "trojan-women": "TROJAN WOMEN",
    "bacchae": "BACCHAE",
    "hippolytus": "HIPPOLYTUS",
}

_BLOCK = frozenset(
    {"p", "div", "section", "article", "blockquote", "ul", "ol", "li",
     "h1", "h2", "h3", "h4", "h5", "h6", "table", "tr", "td"}
)
_HEADINGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
_SKIP = frozenset({"script", "style", "noscript", "sup"})
# A link back from a note to its call: only the notes carry these.
_BACKLINK = re.compile(r"^#(?:_ftnref\d|rfn\d|noteref_|sdfootnote\d+anc)")
_MARK = "\x00"
_BOLD_NUMBER = re.compile(r"^\|?\s*\d{1,4}[a-z]?$")
_PIPE_NUMBER = re.compile(r"\|\s*(?:\x00|\d{1,4}[a-z]?\b)")
_BRACKET_NUMBER = re.compile(r"\[\d{1,4}[a-z]?\]")
_LINE_END_NUMBER = re.compile(r"\s\d{1,4}$")
_METRE = re.compile(
    r"^(?:(?:first|second|third)\s+)?"
    r"(?:strophe|antistrophe|epode|mesode|anapa?ests?)(?:\s+\w+)?$",
    re.I,
)
_DATE = re.compile(r"^\d{4}[-.]\d{1,2}[-.]\d{1,2}$")
_NAME = re.compile(r"^[A-Z][A-Za-z .'’\-–—]{0,39}$")
_LABEL_PUNCT = frozenset({"", "[", "]", "–", "—", "-"})


class Converted(NamedTuple):
    text: str  # verse-own-line turn-text
    markers: int  # Greek line numbers dropped
    speeches: int  # speaker cues written


def _walk(el, out: list, bold: bool = False, italic: bool = False) -> None:
    """Flatten ``el`` into text / br / mark / block / backlink / hr tokens."""
    tag = el.tag.lower() if isinstance(el.tag, str) else ""
    if not tag:
        return  # comment; the caller keeps its tail
    href = el.get("href") or ""
    if tag == "a" and href.startswith("#"):
        if _BACKLINK.match(href):
            out.append(("backlink",))
        return  # a footnote call or a back link
    if tag in _SKIP or "noteref" in (el.get("class") or "").split():
        return
    if tag == "br":
        out.append(("br",))
        return
    if tag == "hr":
        out.append(("hr",))
        return
    if tag == "sub" and el.text_content().strip().isdigit():
        out.append(("mark",))
        return
    block = tag in _BLOCK
    if block:
        out.append(("open", el))
    b = bold or tag in ("strong", "b") or "bold" in (el.get("style") or "")
    i = italic or tag in ("em", "i")
    if el.text:
        out.append(("text", el.text, b, i))
    for child in el:
        _walk(child, out, b, i)
        if child.tail:
            out.append(("text", child.tail, b, i))
    if block:
        out.append(("close",))


def _blocks(tokens: list) -> list[tuple[object, list]]:
    """Cut the token stream at every block edge: ``(element, tokens)``."""
    blocks: list[tuple[object, list]] = []
    stack: list = [None]
    current: list = []

    def flush() -> None:
        nonlocal current
        if current:
            blocks.append((stack[-1], current))
        current = []

    for token in tokens:
        if token[0] == "open":
            flush()
            stack.append(token[1])
        elif token[0] == "close":
            flush()
            if len(stack) > 1:
                stack.pop()
        else:
            current.append(token)
    flush()
    return blocks


def _lines(tokens: list, line_end_numbers: bool) -> list[tuple[str, bool, list]]:
    """Split a block at ``<br>``: ``(text with marks as \\x00, italic-only, tokens)``."""
    lines: list[list] = [[]]
    for token in tokens:
        if token[0] == "br":
            lines.append([])
        else:
            lines[-1].append(token)
    out = []
    for toks in lines:
        pieces = []
        italic_only = True
        for token in toks:
            if token[0] == "mark":
                pieces.append(_MARK)
                italic_only = False
            elif token[0] == "text":
                _kind, text, bold, italic = token
                if bold and _BOLD_NUMBER.match(text.strip()):
                    pieces.append(_MARK)
                    italic_only = False
                    continue
                if italic and _METRE.match(text.strip()):
                    continue
                if text.strip() and not italic:
                    italic_only = False
                pieces.append(text)
        line = collapse_ws("".join(pieces)).strip()
        line = _PIPE_NUMBER.sub(_MARK, line)
        line = _BRACKET_NUMBER.sub(_MARK, line)
        if line_end_numbers:
            line = _LINE_END_NUMBER.sub(" " + _MARK, line)
        out.append((line, italic_only, toks))
    return out


def _label(tokens: list) -> tuple[str | None, list]:
    """A leading speaker name: bold (``Attendant [therapōn]`` keeps only the
    name), or italic when it is a bare name alone on its line (Oedipus at
    Colonus prints the Stranger's cue as ``<em>Xenos</em>``, a Greek word)."""
    words: list[str] = []
    bold_seen = italic_seen = False
    rest: list = []
    for k, token in enumerate(tokens):
        if token[0] != "text":
            rest = tokens[k:]
            break
        _kind, text, bold, italic = token
        stripped = text.strip()
        joined = "".join(words)
        in_gloss = "[" in joined and "]" not in joined
        if bold and _BOLD_NUMBER.match(stripped):
            rest = tokens[k:]
            break
        if bold or stripped in _LABEL_PUNCT or (italic and (in_gloss or not bold_seen)):
            words.append(text)
            bold_seen = bold_seen or (bold and bool(stripped))
            italic_seen = italic_seen or (italic and not bold and bool(stripped))
            continue
        rest = tokens[k:]
        break
    raw = re.sub(r"\[[^\]]*\]?", " ", "".join(words))
    name = collapse_ws(raw.replace("–", " ").replace("—", " ")).strip(" .:,;-")
    if not name or not _NAME.match(name) or not any(ch.isalpha() for ch in name):
        return None, tokens
    if not bold_seen:
        alone = bool(rest) and rest[0][0] == "br"
        bare = not re.search(r"[.,;:!?]", "".join(words)) and len(name.split()) <= 2
        if not (italic_seen and alone and bare):
            return None, tokens
    return name, rest


def _cue(name: str) -> str:
    folded = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return collapse_ws(folded).upper()


def _is_end(tokens: list, text: str) -> bool:
    if any(token[0] in ("backlink", "hr") for token in tokens):
        return True
    return text in ("Notes", "Footnotes") or bool(_DATE.match(text)) or text.startswith("Related topics")


def _aligned(el, side: str) -> bool:
    if el is None:
        return False
    style = (el.get("style") or "").replace(" ", "")
    return el.get("align") == side or f"text-align:{side}" in style


def convert(raw_html: str, title: str) -> Converted:
    doc = lxml.html.fromstring(raw_html)
    roots = doc.xpath('//section[@id="main"]') or doc.xpath('//div[contains(@class, "TEI-XML")]')
    if not roots:
        raise ValueError("no Sourcebook text on the page")
    root = roots[0]
    line_end_numbers = root.tag == "div"  # the CHS verse layout
    tokens: list = []
    _walk(root, tokens)

    opening: list[str] = []
    speeches: list[tuple[str, list[tuple[str, str]]]] = []
    markers = 0
    for el, block in _blocks(tokens):
        plain = collapse_ws("".join(t[1] for t in block if t[0] == "text")).strip()
        if speeches and _is_end(block, plain):
            break
        if not plain.strip("_ ") and not any(t[0] == "mark" for t in block):
            continue
        if el is not None and el.tag in _HEADINGS:
            continue  # the play title (Antigone prints it bold)
        name, rest = _label(block)
        if name is not None:
            speeches.append((_cue(name), []))
            block = rest
        lines = _lines(block, line_end_numbers)
        text = collapse_ws(" ".join(line for line, _it, _t in lines))
        markers += text.count(_MARK)
        text = collapse_ws(text.replace(_MARK, " ")).strip()
        if not text:
            continue
        italic_only = all(it or not line for line, it, _t in lines)
        if italic_only and _aligned(el, "right"):
            continue  # a metre label printed on its own line
        if not speeches:
            if italic_only and not _aligned(el, "center"):
                opening.append(text)
            continue
        speeches[-1][1].append(("dir" if italic_only else "para", text.replace("_", " ")))

    out = [title, ""]
    for text in opening:
        out += [f"_{text}_", ""]
    written = 0
    for cue, items in speeches:
        if not any(kind == "para" for kind, _text in items):
            # A cue with no words of its own: its directions still print.
            for _kind, text in items:
                out += [f"_{text}_", ""]
            continue
        out.append(cue)
        written += 1
        for kind, text in items:
            out += [f"_{text}_" if kind == "dir" else text, ""]
    return Converted("\n".join(out).rstrip("\n") + "\n", markers, written)


def main() -> int:
    out_dir = SOURCES_DIR / "bench" / "kosmos"
    out_dir.mkdir(parents=True, exist_ok=True)
    for work_id, title in PLAYS.items():
        raw = (SOURCES_DIR / "kosmos" / f"{work_id}.html").read_text(encoding="utf-8")
        result = convert(raw, title)
        (out_dir / f"{work_id}.txt").write_text(result.text, encoding="utf-8")
        print(f"{work_id}: markers={result.markers} speeches={result.speeches}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
