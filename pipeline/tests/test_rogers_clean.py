"""B. B. Rogers's Loeb Aristophanes vol. 3 -- History Genie's OCR of the
vendored scan (``aristophanes0003benj_r6k0``) rebuilt into loeb-ocr
turn-text: Lysistrata rides as the ``overlay`` comparison slot,
Thesmophoriazusae/Ecclesiazusae/Wealth as ``third``.
"""

from pathlib import Path

import pytest

from drama_pipeline import genie_text as gt
from drama_pipeline.config import SOURCES_DIR
from drama_pipeline.rogers_clean import (
    GENIE_TEXT,
    PLAYS,
    _Play,
    _convert_body,
    _lift_smallcaps_cues,
    _splice_gaps,
    convert_play,
)
from drama_pipeline.stage1_turn_english import parse_play_speeches


def _p(text: str, italic: bool = False, page: int = 1) -> gt.Paragraph:
    return gt.Paragraph(text=text, italic=italic, page=page)


_TEST_PLAY = _Play(
    title="THE TESTPLAY",
    word="TESTPLAY",
    bench="testplay",
    abbrev={"LY": "LYSISTRATA"},
    compounds={("M", "CH"): "CHORUS"},
)


def _parsed(text: str, title: str = "THE TESTPLAY"):
    return parse_play_speeches(text, title, format="loeb-ocr", verse=True)


def _speeches(text: str, title: str = "THE TESTPLAY"):
    speeches, _notes = _parsed(text, title)
    return [(s["speaker_printed"], s["text"]) for s in speeches]


def test_cue_verse_run_direction_and_footnote():
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("LY. Hail to thee,^a"),
        _p("my oldest friend."),
        _p("Enter Calonice.", italic=True),
        _p("CALONICE. Good day to you."),
        _p("^a Good day indeed."),
        _p("99"),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY)
    assert gaps == []
    assert speeches == 2
    assert footnotes == 1
    assert not [line for line in log if line.startswith("uncertain")]

    parsed, notes = _parsed(text)
    assert [(s["speaker_printed"], s["text"]) for s in parsed] == [
        ("LYSISTRATA", "Hail to thee, [1]\nmy oldest friend."),
        ("CALONICE", "Good day to you."),
    ]
    assert parsed[1]["directions_before"] == ["Enter Calonice."]
    assert notes == {"1": "Good day indeed."}


def test_compound_cue_and_page_number_furniture_dropped():
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("LY. Onward!"),
        _p("42"),  # a bare page number -- furniture, never a speech
        _p("M. CH. We march as one."),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY)
    assert speeches == 2
    assert "42" not in text
    assert _speeches(text) == [
        ("LYSISTRATA", "Onward!"),
        ("CHORUS", "We march as one."),
    ]


def test_greek_paragraph_and_running_head_dropped_mid_play():
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("LY. First half."),
        _p("χαῖρε ὦ φίλη γύναι, τόδε τὸ ἔργον καλόν ἐστιν ἡμῖν"),  # a Greek facing page
        _p("THE TESTPLAY, 10-20"),  # a running head -- not dialogue
        _p("LY. Second half."),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY)
    assert gaps == []
    assert speeches == 2
    assert "χαῖρε" not in text
    assert "TESTPLAY, 10-20" not in text
    assert _speeches(text) == [
        ("LYSISTRATA", "First half."),
        ("LYSISTRATA", "Second half."),
    ]


def test_running_head_jump_opens_a_gap_the_old_bench_fills():
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("LY. Before the gap."),
        _p("THE TESTPLAY, 1-10"),
        _p("LY. Right after."),
        _p("THE TESTPLAY, 20-30"),  # 11-19 has no Genie text at all
        _p("LY. Well after."),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY)
    assert [(lo, hi) for _idx, lo, hi in gaps] == [(11, 19)]
    assert any(line.startswith("gap\t") for line in log)

    old_text = (
        "THE TESTPLAY\n\n"
        "LYSISTRATA. Before the gap.\n\n"
        "LYSISTRATA. Right after.\n\n"
        "CALONICE. The missing middle bit.\n\n"
        "LYSISTRATA. Well after.\n"
    )
    spliced, splice_log = _splice_gaps(text, old_text, gaps, _TEST_PLAY)
    assert any(line.startswith("splice\t") for line in splice_log)
    assert _speeches(spliced) == [
        ("LYSISTRATA", "Before the gap."),
        ("LYSISTRATA", "Right after."),
        ("CALONICE", "The missing middle bit."),
        ("LYSISTRATA", "Well after."),
    ]


def test_splice_refuses_a_span_the_old_bench_itself_never_resolved():
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("LY. Before the gap."),
        _p("THE TESTPLAY, 1-10"),
        _p("LY. Right after."),
        _p("THE TESTPLAY, 20-30"),
        _p("LY. Well after."),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY)
    # The old bench's own text for the gap is bare cues with no words --
    # exactly the collapsed-stichomythia problem this rebuild exists to fix.
    old_text = (
        "THE TESTPLAY\n\n"
        "LYSISTRATA. Before the gap.\n\n"
        "LYSISTRATA. Right after.\n\n"
        "PRAXAGORA. F.W.\nS.W.\n\n"
        "LYSISTRATA. Well after.\n"
    )
    spliced, splice_log = _splice_gaps(text, old_text, gaps, _TEST_PLAY)
    assert not any(line.startswith("splice\t") for line in splice_log)
    assert any(line.startswith("uncertain\t") for line in splice_log)
    assert _speeches(spliced) == [
        ("LYSISTRATA", "Before the gap."),
        ("LYSISTRATA", "Right after."),
        ("LYSISTRATA", "Well after."),
    ]


def test_smallcaps_span_and_table_row_are_speaker_cues():
    # genie_text deletes a <span> and everything inside it. These cues have
    # to be lifted first, or the verse stays in the speech before them.
    raw = (
        '<span style="font-variant:small-caps;">bl.</span>&nbsp; The prospect.\n'
        '<span style="font-variant:small-caps;">bl</span> Just one other thing.\n'
        'A note keeps <span style="font-variant:small-caps;">d</span> the letter.\n'
    )
    lifted = _lift_smallcaps_cues(raw)
    assert lifted.splitlines()[0].startswith("BL. ")
    assert lifted.splitlines()[1].startswith("BL. ")
    assert "small-caps" in lifted.splitlines()[2]

    play = _Play(
        title="THE TESTPLAY",
        word="TESTPLAY",
        bench="testplay",
        abbrev={"LY": "LYSISTRATA", "BL": "BLEPYRUS", "PR": "PRAXAGORA"},
    )
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("LY. Before."),
        _p("| | |"),
        _p("| :--- | :--- |"),
        _p("| BL. | Right. |"),
        _p("| | But what will you do with the desk? |"),
        _p("| PR. | They shall go |"),
        _p("| MN. | τί δ᾽ ἔστιν; |"),
    ]
    text, speeches, _footnotes, _log, gaps = _convert_body(paras, 0, len(paras), play)
    assert gaps == []
    assert "τί" not in text
    assert ":---" not in text
    assert _speeches(text) == [
        ("LYSISTRATA", "Before."),
        ("BLEPYRUS", "Right.\nBut what will you do with the desk?"),
        ("PRAXAGORA", "They shall go"),
    ]
    assert speeches == 3


SOURCES = SOURCES_DIR


@pytest.mark.skipif(
    not GENIE_TEXT.exists(),
    reason="History Genie's OCR text is a machine-local build/ scratch file, not vendored",
)
@pytest.mark.parametrize("work_id", sorted(PLAYS))
def test_vendored_text_is_the_converter_output(work_id):
    out = convert_play(work_id)
    cfg = PLAYS[work_id]
    assert (SOURCES / "bench" / "rogers" / f"{cfg.bench}.txt").read_text(encoding="utf-8") == out.text
    assert len(_speeches(out.text, cfg.title)) == out.speeches
