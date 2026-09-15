r"""Read History Genie's markdown-flavoured OCR of a Loeb volume.

Genie exports each scanned volume as one ``.txt`` per Internet Archive item
(``build/genie/<item>.txt``, John's second, independent OCR pass used to
check the Storr/Way bench text against ABBYY -- see
``build/review/fix-genie-loeb-brief.md``). The delivered format (seen
2026-09-15) is markdown-flavoured and already carries the printed formatting:

- ``---`` alone on a line separates pages; each page opens with a page
  number and running head (``# AJAX`` / ``AJAX`` / ``ΑΙΑΣ`` / ``AIAS``,
  sometimes ``<center>...</center>``).
- Speaker cues print as ``**NAME**`` or plain ``NAME`` alone on a line.
- Stage directions are ``*italic*`` runs, often inside ``[...]``.
- Footnote calls are ``¹`` (a bare superscript digit), ``$^1$``/``$^{1}$``,
  or ``<sup>1</sup>`` (Way vol. 4, seen 2026-09-15).
- Verse indents and marginal Greek line numbers are ``&nbsp;`` runs, the
  numbers sometimes wrapped in ``<span style="float: right;">10</span>``.
  Way vol. 4 also uses ``&emsp;`` runs for the same indents, and renders
  some indentation and strophe/antistrophe spacing as bare LaTeX macros,
  ``$\quad$``/``$\qquad$``, with no wrapping tag.
- Way vol. 4 marks a few cues/notes with ``<small>...</small>`` or
  ``<p align="center">...</p>`` instead of ``**bold**``/``<center>``.

This module turns one page-delimited paragraph stream into cleaned,
plain-text lines -- markdown/``&nbsp;``/``&emsp;``/``<span>``/``<small>``/
``<p>``/``$\quad$`` noise stripped, footnote calls normalised to ``[n]`` --
annotated with an italic flag and a page index, so a caller can drop Greek
pages (mostly Greek letters) and align what is left to a bench file.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

_GREEK_RE = re.compile(r"[Ͱ-Ͽἀ-῿]")
_LETTER_RE = re.compile(r"[^\W\d_]", re.UNICODE)

_SPAN_RE = re.compile(r"<span[^>]*>(.*?)</span>", re.S | re.I)
_CENTER_RE = re.compile(r"</?center>", re.I)
_SMALL_RE = re.compile(r"</?small>", re.I)
_P_TAG_RE = re.compile(r"</?p[^>]*>", re.I)
_HEADING_RE = re.compile(r"^#{1,6}\s*")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RUN_RE = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
_ITALIC_WHOLE_RE = re.compile(r"\A\*([^*].*[^*]|[^*])\*\Z")
# Way vol. 4's page shape: footnote calls as $^1$ or $^{1}$, and occasional
# $\quad$/$\qquad$ LaTeX spacing macros standing in for indentation (the
# Sophocles vol. 2 shape used &nbsp; runs for the same purpose instead).
_DOLLAR_FOOTNOTE_RE = re.compile(r"\$\^\{?(\d+)\}?\$")
_QUAD_RE = re.compile(r"\$(?:\\q{1,2}uad)+\$")
_SUP_TAG_RE = re.compile(r"<sup>(\d+)</sup>", re.I)
_SUPERSCRIPT_RUN_RE = re.compile(r"[¹²³⁰-⁹]+")


@dataclass(frozen=True)
class Paragraph:
    """One non-blank line of Genie's ``.txt``, cleaned.

    ``text`` has markdown emphasis, ``&nbsp;``/``<span>`` noise and footnote
    superscripts (``$^1$`` or a bare superscript digit) normalised away or
    to ``[n]``. ``italic`` is true when the whole line was one ``*...*``
    run (a stage direction). ``page`` is the 0-based index of the
    ``---``-delimited page the line came from.
    """

    text: str
    italic: bool
    page: int


def _superscript_to_plain(match: "re.Match[str]") -> str:
    digits = "".join(unicodedata.normalize("NFKC", ch) for ch in match.group(0))
    return f"[{digits}]"


def _clean_line(line: str) -> tuple[str, bool]:
    line = _SPAN_RE.sub("", line)
    line = line.replace("\xa0", " ").replace("&nbsp;", " ").replace("&emsp;", " ")
    line = _CENTER_RE.sub("", line)
    line = _SMALL_RE.sub("", line)
    line = _P_TAG_RE.sub("", line)
    line = _HEADING_RE.sub("", line)
    line = _QUAD_RE.sub(" ", line)
    line = _SUP_TAG_RE.sub(lambda m: f"[{m.group(1)}]", line)
    line = _DOLLAR_FOOTNOTE_RE.sub(lambda m: f"[{m.group(1)}]", line)
    line = _SUPERSCRIPT_RUN_RE.sub(_superscript_to_plain, line)
    stripped = line.strip()
    italic = False
    whole = _ITALIC_WHOLE_RE.match(stripped)
    if whole:
        italic = True
        stripped = whole.group(1).strip()
    stripped = _BOLD_RE.sub(r"\1", stripped)
    stripped = _ITALIC_RUN_RE.sub(r"\1", stripped)
    stripped = re.sub(r" {2,}", " ", stripped).strip()
    return stripped, italic


def paragraphs(path: str | Path) -> list[Paragraph]:
    """Split Genie's ``.txt`` into cleaned, page-indexed paragraphs.

    Blank lines and bare ``---`` page-break markers are dropped; every
    remaining line becomes one :class:`Paragraph`. A page with a mix of
    Greek and English (a running head printed in both) still comes back as
    plain paragraphs -- dropping Greek content is the caller's job, via
    :func:`is_greek_paragraph`, since only the caller knows how strict to
    be for a given play.
    """
    raw = Path(path).read_text(encoding="utf-8")
    out: list[Paragraph] = []
    page = 0
    for raw_line in raw.splitlines():
        if raw_line.strip() == "---":
            page += 1
            continue
        if not raw_line.strip():
            continue
        text, italic = _clean_line(raw_line)
        if text:
            out.append(Paragraph(text=text, italic=italic, page=page))
    return out


def is_greek_paragraph(text: str) -> bool:
    """True when the line's letters are mostly Greek (a facing Greek page)."""
    letters = _LETTER_RE.findall(text)
    if not letters:
        return False
    greek = sum(1 for ch in letters if _GREEK_RE.match(ch))
    return greek > len(letters) / 2
