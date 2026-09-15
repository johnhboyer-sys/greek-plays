"""genie_text.paragraphs on a small inline fixture of Genie's markdown .txt."""

from drama_pipeline.genie_text import Paragraph, is_greek_paragraph, paragraphs


FIXTURE = """\
# AJAX

**ATHENA**
Son of Laertes, ever on the prowl&nbsp;&nbsp;10
To seize some coign of vantage 'gainst thy foes,

6

---

ΑΙΑΣ

ΑΘΗΝΑ
Ἀεί μέν, ὦ παῖ <span style="float: right;">10</span>

7

---

AJAX

*Enter* ODYSSEUS, *scanning the sand.*

ODYSSEUS
Of Sisyphus,¹ let not this ill fame cling
Cozening the Fates: the Sisters promised me$^2$

Footnotes:
[1] Odysseus, reputed son of Sisyphus, not Laertes.
[2] A gloss on the ransom.
"""

# Way vol. 4's page shape (seen 2026-09-15): &emsp; indents, bare $\quad$/
# $\qquad$ spacing macros, <small>...</small> and <p align="center">...</p>
# cues, and $^{1}$/<sup>1</sup> footnote calls.
WAY_FIXTURE = """\
# ALCESTIS

<p align="center">APOLLO</p>
Fear not: fair words and justice are with me.

<small>HANDMAID</small>
She liveth, and is dead : both mayst thou say.

&emsp;&emsp;Though ye voyage all seas,
$\\quad$Ye shall light on no lands,
$\\qquad\\qquad$(Ant.)

Of lifeless food: $^{1}$ take Orpheus for thy king:

$^{1}$ Abstinence from animal food.

<sup>1</sup> A gloss on the name.
"""


def test_page_index_increments_on_bare_dash_separator():
    paras = paragraphs_from_text(FIXTURE)
    pages = {p.page for p in paras}
    assert pages == {0, 1, 2}


def test_heading_and_bold_cue_markup_stripped():
    paras = paragraphs_from_text(FIXTURE)
    assert paras[0].text == "AJAX"
    assert paras[1].text == "ATHENA"


def test_nbsp_indent_and_span_marginal_number_stripped():
    paras = paragraphs_from_text(FIXTURE)
    line = next(p for p in paras if p.text.startswith("Son of Laertes"))
    assert line.text == "Son of Laertes, ever on the prowl 10"
    greek_line = next(p for p in paras if p.text.startswith("Ἀεί"))
    assert "<span" not in greek_line.text
    assert "10" not in greek_line.text or greek_line.text.endswith("10")


def test_whole_line_italic_run_is_a_direction():
    paras = paragraphs_from_text(FIXTURE)
    direction = next(p for p in paras if "Enter" in p.text)
    assert direction.italic is True
    assert direction.text == "Enter ODYSSEUS, scanning the sand."


def test_footnote_calls_normalised_to_bracket_markers():
    paras = paragraphs_from_text(FIXTURE)
    sisyphus = next(p for p in paras if p.text.startswith("Of Sisyphus"))
    assert sisyphus.text == "Of Sisyphus,[1] let not this ill fame cling"
    ransom = next(p for p in paras if p.text.startswith("Cozening"))
    assert ransom.text == "Cozening the Fates: the Sisters promised me[2]"


def test_footnotes_block_kept_as_plain_paragraphs():
    paras = paragraphs_from_text(FIXTURE)
    assert any(p.text == "Footnotes:" for p in paras)
    assert any(p.text.startswith("[1] Odysseus") for p in paras)


def test_is_greek_paragraph():
    assert is_greek_paragraph("Ἀεί μέν, ὦ παῖ Λαρτίου") is True
    assert is_greek_paragraph("Son of Laertes, ever on the prowl") is False
    assert is_greek_paragraph("6") is False


def test_way_vol4_p_align_and_small_cue_tags_stripped():
    paras = paragraphs_from_text(WAY_FIXTURE)
    assert any(p.text == "APOLLO" for p in paras)
    assert any(p.text == "HANDMAID" for p in paras)
    assert not any("<p" in p.text or "<small" in p.text for p in paras)


def test_way_vol4_emsp_and_quad_macros_stripped():
    paras = paragraphs_from_text(WAY_FIXTURE)
    line = next(p for p in paras if p.text.startswith("Though ye voyage"))
    assert line.text == "Though ye voyage all seas,"
    line2 = next(p for p in paras if "no lands" in p.text)
    assert line2.text == "Ye shall light on no lands,"
    line3 = next(p for p in paras if "(Ant.)" in p.text)
    assert line3.text == "(Ant.)"
    assert "\\quad" not in line3.text and "$" not in line3.text


def test_way_vol4_footnote_calls_normalised():
    paras = paragraphs_from_text(WAY_FIXTURE)
    food = next(p for p in paras if p.text.startswith("Of lifeless food"))
    assert food.text == "Of lifeless food: [1] take Orpheus for thy king:"
    gloss = next(p for p in paras if "gloss on the name" in p.text)
    assert gloss.text == "[1] A gloss on the name."


def paragraphs_from_text(text: str) -> list[Paragraph]:
    """paragraphs() reads a path; write the fixture to a tmp file per call."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "fixture.txt"
        path.write_text(text, encoding="utf-8")
        return paragraphs(path)
