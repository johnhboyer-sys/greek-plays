"""W. J. Hickie's Bohn Aristophanes vol. II -- History Genie's OCR of the
vendored scan (``in.ernet.dli.2015.515630``) rebuilt into loeb-ocr turn-text:
Lysistrata rides the ``third`` slot, Thesmophoriazusae/Frogs/Ecclesiazusae/
Wealth ride ``secondary``.
"""

from pathlib import Path

import pytest

from drama_pipeline import genie_text as gt
from drama_pipeline.config import SOURCES_DIR
from drama_pipeline.hickie_clean import (
    GENIE_TEXT,
    PLAYS,
    _Play,
    _convert_body,
    _normalize,
    convert_play,
)
from drama_pipeline.stage1_turn_english import parse_play_speeches


def _p(text: str, italic: bool = False, page: int = 1) -> gt.Paragraph:
    return gt.Paragraph(text=text, italic=italic, page=page)


_TEST_PLAY = _Play(
    title="THE TESTPLAY",
    word="TESTPLAY",
    bench="testplay",
    abbrev={"LY": "LYSISTRATA", "COM": "COMMITTEE-MAN"},
    drop_exact=("Non traducta linea.",),
)


def _parsed(text: str, title: str = "THE TESTPLAY"):
    return parse_play_speeches(text, title, format="loeb-ocr", verse=False)


def _speeches(text: str, title: str = "THE TESTPLAY"):
    speeches, _notes = _parsed(text, title)
    return [(s["speaker_printed"], s["text"]) for s in speeches]


def test_cue_paren_and_footnote_call_resolved_same_page():
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("[SCENE—a house.]", page=0),
        _p("LY. Well, we have met at last.[1]", page=0),
        _p("PRAXAGORA (coming out of the house). I bring news.", page=0),
        _p("[1] A footnote of some length.", page=0),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY)
    assert gaps == []
    assert speeches == 2
    assert footnotes == 1
    assert not [line for line in log if line.startswith("uncertain")]
    parsed = _speeches(text)
    assert parsed == [
        ("LYSISTRATA", "Well, we have met at last.[1]"),
        ("PRAXAGORA", "I bring news."),
    ]
    assert "[coming out of the house]" in text


def test_mixed_case_ordinal_cue_and_cyrillic_smallcaps_homoglyphs():
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("LY. Onward!", page=0),
        _p("2nd Old Wom. I follow.", page=0),
        _p("Young Man. So do I.", page=0),
        _p("Сно. Behold, we march.", page=0),  # Cyrillic С/н/о homoglyphs for "CHO."
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY)
    assert speeches == 4
    assert _speeches(text) == [
        ("LYSISTRATA", "Onward!"),
        ("SECOND OLD WOMAN", "I follow."),
        ("YOUNG MAN", "So do I."),
        ("CHO", "Behold, we march."),
    ]


def test_footnote_definition_that_is_mostly_greek_is_still_registered():
    # A genuinely short definition, almost entirely a quoted Greek phrase,
    # must not be dropped as "just a Greek quote" -- it is still a real
    # footnote, and dropping it silently also swallows the page's own
    # numbering for whatever definition comes after it.
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("LY. A word.[1]", page=0),
        _p("[1] χαῖρε ὦ φίλη γύναι τόδε τὸ ἔργον.", page=0),
        _p("[2] A plain English note.", page=0),
        _p("LY. More.[2]", page=0),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY)
    assert footnotes == 2
    assert not [line for line in log if line.startswith("uncertain")]


def test_footnote_overflow_onto_next_page_before_its_own_heading():
    # A note too long for its own page runs on, uninterrupted, into the top
    # of the next one -- before that page's own running head or a real cue
    # ever appears. A plain page-boundary reset would leave this line as an
    # unattributed continuation of whatever speech follows.
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("LY. Something.[1]", page=1),
        _p("[1] Part one of a long note", page=1),
        _p("continuing onto the next page.", page=2),
        _p("COM. New speech.", page=2),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY)
    assert speeches == 2
    assert not [line for line in log if line.startswith("uncertain")]
    parsed = _speeches(text)
    assert parsed == [
        ("LYSISTRATA", "Something.[1]"),
        ("COMMITTEE-MAN", "New speech."),
    ]
    assert "continuing onto the next page" not in parsed[1][1]
    assert "Part one of a long note continuing onto the next page." in text


def test_pipe_table_running_head_and_reversed_range_recognised():
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("LY. Before,"),
        _p("20—10. | THE TESTPLAY. | 99"),  # reversed range, pipe-delimited
        _p("continuing right after,"),
        _p("--- | --- | ---"),  # the pipe table's own separator row
        _p("still going."),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY)
    assert gaps == []
    assert "20" not in text
    assert "---" not in text
    assert speeches == 1  # the furniture never breaks the one open speech
    assert _speeches(text) == [("LYSISTRATA", "Before, continuing right after, still going.")]


def test_dropped_bare_pre_speech_and_drop_exact_latin_substitution():
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("[SCENE—a house.]", page=0),
        _p("LYSISTRATA, CALONICE.", page=0),  # a cast-list line before the first cue
        _p("LY. First words.", page=0),
        _p("Non traducta linea.", page=0),  # declared drop_exact
        _p("LY. More words.", page=0),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY)
    assert "LYSISTRATA, CALONICE" not in text
    assert "Non traducta linea" not in text
    assert any(line.startswith("dropped\tpre-speech") for line in log)
    assert any(line.startswith("dropped\tHickie's own Latin") for line in log)


def test_normalize_dollar_footnote_and_accented_title_and_br():
    assert _normalize("word${}^3$ more") == "word[3] more"
    assert _normalize("(_aside_)") == "(aside)"
    assert _normalize("THE ECCLÉSIAZUSÆ.") == "THE ECCLESIAZUSÆ."
    assert _normalize("text <br> more") == "text more"


SOURCES = SOURCES_DIR


@pytest.mark.skipif(
    not GENIE_TEXT.exists(),
    reason="History Genie's OCR text is a machine-local build/ scratch file, not vendored",
)
@pytest.mark.parametrize("work_id", sorted(PLAYS))
def test_vendored_text_is_the_converter_output(work_id):
    out = convert_play(work_id)
    cfg = PLAYS[work_id]
    assert (SOURCES / "bench" / "hickie" / f"{cfg.bench}.txt").read_text(encoding="utf-8") == out.text
    assert len(_speeches(out.text, cfg.title)) == out.speeches
