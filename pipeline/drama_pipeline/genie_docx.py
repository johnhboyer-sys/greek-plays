"""Read History Genie's ``.docx`` export of a Loeb volume.

John saves Genie's second, independent OCR pass as one ``.docx`` per
Internet Archive item (``build/genie/<item>.docx``; a ``.txt`` usually sits
beside it, see ``genie_text.py`` and ``build/review/fix-genie-loeb-brief.md``).
The ``.txt`` is markdown-flavoured and is the primary input; this module is
the fallback for when the ``.txt`` loses something the caller needs (a run
missing from the ``.txt`` export, or the ``.txt`` truncated before the end
of the volume).

The ``.docx`` carries formatting as real run properties rather than
markdown: italics as ``<w:i/>``, bold as ``<w:b/>``, small capitals as
``<w:smallCaps/>``, footnote calls as ``<w:vertAlign w:val="superscript"/>``,
and a page break as ``<w:br w:type="page"/>`` or a
``<w:lastRenderedPageBreak/>`` marker. Standard library only
(``zipfile`` + ``xml.etree``), per the brief.

This reader turns each run's formatting into the same markdown-style
markup ``genie_text.py`` already knows how to strip (``**bold**``,
``*italic*``, small caps wrapped the same as bold since the bench has no
separate small-caps convention, ``$^n$`` for a footnote call), then hands
each assembled paragraph line to ``genie_text._clean_line`` so both readers
produce the identical :class:`~genie_text.Paragraph` shape from the same
cleaning logic.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from .genie_text import Paragraph, _clean_line

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _run_text(run: ET.Element) -> str:
    parts: list[str] = []
    for node in run.iter():
        tag = node.tag
        if tag == f"{_W}t":
            parts.append(node.text or "")
        elif tag == f"{_W}tab":
            parts.append("\t")
    return "".join(parts)


def _markup_run(run: ET.Element) -> str:
    """Render one ``w:r`` run as markdown-style text (bold/italic/footnote)."""
    text = _run_text(run)
    if not text:
        return ""
    rpr = run.find(f"{_W}rPr")
    if rpr is None:
        return text
    vert_align = rpr.find(f"{_W}vertAlign")
    if vert_align is not None and vert_align.get(f"{_W}val") == "superscript":
        return f"$^{text}$"
    bold = rpr.find(f"{_W}b") is not None
    italic = rpr.find(f"{_W}i") is not None
    small_caps = rpr.find(f"{_W}smallCaps") is not None
    if bold or small_caps:
        return f"**{text}**"
    if italic:
        return f"*{text}*"
    return text


def _has_page_break(para: ET.Element) -> bool:
    for node in para.iter():
        if node.tag == f"{_W}lastRenderedPageBreak":
            return True
        if node.tag == f"{_W}br" and node.get(f"{_W}type") == "page":
            return True
    return False


def paragraphs(path: str | Path) -> list[Paragraph]:
    """Split Genie's ``.docx`` body into cleaned, page-indexed paragraphs.

    Mirrors :func:`genie_text.paragraphs`: blank lines are dropped, markdown
    emphasis and footnote markup are stripped (via the same
    ``_clean_line``), and ``italic`` is true only when a whole paragraph is
    one italic (or small-caps) run -- inline emphasis mid-paragraph is
    flattened to plain text, matching ``genie_text.py``'s behaviour on the
    ``.txt``.
    """
    with zipfile.ZipFile(path) as archive:
        xml_bytes = archive.read("word/document.xml")
    root = ET.fromstring(xml_bytes)
    body = root.find(f"{_W}body")
    if body is None:
        return []

    out: list[Paragraph] = []
    page = 0
    for para in body.iter(f"{_W}p"):
        if _has_page_break(para):
            page += 1
        raw_line = "".join(_markup_run(run) for run in para.iter(f"{_W}r"))
        if not raw_line.strip():
            continue
        text, italic = _clean_line(raw_line)
        if text:
            out.append(Paragraph(text=text, italic=italic, page=page))
    return out
