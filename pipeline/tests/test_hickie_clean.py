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


# H1 (2026-09-17 round 2 brief, finding 6): Hickie is rendered with
# `footnotes: false` in every one of these five comedies, so a renumbered
# `[N]` marker written into the bench text would resolve to no popup and
# print as a dead bracketed digit -- the call is dropped outright instead.
def test_cue_paren_and_footnote_call_is_stripped_not_renumbered():
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
    assert footnotes == 0
    assert not [line for line in log if line.startswith("uncertain")]
    parsed = _speeches(text)
    assert parsed == [
        ("LYSISTRATA", "Well, we have met at last."),
        ("PRAXAGORA", "I bring news."),
    ]
    assert "[1]" not in text
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
    # must not be dropped as "just a Greek quote" -- registering it (even
    # though nothing renders it, H1) is what keeps the page's own numbering
    # working for whatever definition comes after it, and its call must
    # still resolve (no "uncertain" log line) rather than orphan.
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("LY. A word.[1]", page=0),
        _p("[1] χαῖρε ὦ φίλη γύναι τόδε τὸ ἔργον.", page=0),
        _p("[2] A plain English note.", page=0),
        _p("LY. More.[2]", page=0),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY)
    assert footnotes == 0
    assert "[1]" not in text and "[2]" not in text
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
        ("LYSISTRATA", "Something."),
        ("COMMITTEE-MAN", "New speech."),
    ]
    assert "continuing onto the next page" not in parsed[1][1]
    assert "Part one of a long note continuing onto the next page." not in text


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


# H1 (2026-09-17 round 2 brief, lysistrata finding 1): a Bohn abbreviated
# cue printed in ordinary running-text case (`Lys.`, `Com.`) survived as
# body text of whichever speech was still open instead of opening its own.
# lysistrata.txt:372/375, in shape: "...for there is not more need of
# levers, than of sense and judgment. Lys. By Diana, if in truth..." Uses
# the real corpus abbreviation ("LYS", three letters) rather than
# `_TEST_PLAY`'s own shorter "LY" fixture key.
_LYS_COM_PLAY = _Play(
    title="THE TESTPLAY",
    word="TESTPLAY",
    bench="testplay",
    abbrev={"LYS": "LYSISTRATA", "COM": "COMMITTEE-MAN"},
)


def test_embedded_abbrev_cue_mid_sentence_opens_a_new_speech():
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("COM. Do not force with your levers! For there is not more need of levers, than of sense and judgment. Lys. By Diana, if in truth he shall lay the tip of his hand upon me, he shall weep for it.", page=0),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _LYS_COM_PLAY)
    assert speeches == 2
    assert _speeches(text) == [
        (
            "COMMITTEE-MAN",
            "Do not force with your levers! For there is not more need of levers, than of sense and judgment.",
        ),
        (
            "LYSISTRATA",
            "By Diana, if in truth he shall lay the tip of his hand upon me, he shall weep for it.",
        ),
    ]


# A stray leading period Genie's OCR glued onto the cue itself
# (lysistrata.txt:568, `.Lys. If in the first place...`) must not stop the
# same rule from recognising it as the paragraph's own opening cue.
def test_embedded_abbrev_cue_with_stray_leading_punctuation():
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("COM. Something before.", page=0),
        _p(".Lys. If in the first place we put a stop to people lounging.", page=0),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _LYS_COM_PLAY)
    assert speeches == 2
    assert _speeches(text)[1] == (
        "LYSISTRATA",
        "If in the first place we put a stop to people lounging.",
    )


# H1 (finding 3): a page-foot critical-apparatus block -- editors' surnames
# plus a citation-shaped fragment -- Genie kept as running prose, with no
# leading `[N]` of its own (its call was embedded mid-sentence in the speech
# before it), spliced into the middle of a sentence. It must be dropped
# whole, and the sentence's own two halves stay joined in the open speech.
def test_apparatus_paragraph_dropped_from_the_middle_of_a_sentence():
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("LY. And I invoke thee as our ally, O goddess, if any man burn them", page=0),
        _p(
            "222, 456, 497. Eccles. 295. Cf. Krüger, Gr. Gr. § 54, 8, obs. 7. "
            "Hermann, Vig. n. 255. Enger reads the adverb. Dindorf doubts it.",
            page=0,
        ),
        _p("from below, to bring water along with us!", page=0),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY)
    assert speeches == 1
    assert _speeches(text) == [
        (
            "LYSISTRATA",
            "And I invoke thee as our ally, O goddess, if any man burn them "
            "from below, to bring water along with us!",
        )
    ]
    assert "Krüger" not in text and "Hermann" not in text
    assert any(line.startswith("dropped\tcritical-apparatus") for line in log)


# H1 (finding 5): Genie's OCR keeps only "CHO. OF" bold/upper and prints the
# chorus's own tail in ordinary case (`Wom.`/`Men.`); `_CUE_RE` used to read
# just "CHO" as the cue and leave "OF Wom."/"OF Men." as the speech's first
# words, so the two choruses lost their stable roster colour.
def test_truncated_chorus_tail_cue_keeps_its_roster_name():
    cfg = _Play(
        title="THE TESTPLAY",
        word="TESTPLAY",
        bench="testplay",
        abbrev={"CHO. OF MEN": "CHORUS OF OLD MEN", "CHO. OF WOM": "CHORUS OF OLD WOMEN"},
    )
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("CHO. OF Wom. If you happen to have any soap, I'll provide a bath.", page=0),
        _p("CHO. of Men. O Jupiter! what ever shall we make of these monsters?", page=0),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), cfg)
    assert speeches == 2
    assert _speeches(text) == [
        ("CHORUS OF OLD WOMEN", "If you happen to have any soap, I'll provide a bath."),
        ("CHORUS OF OLD MEN", "O Jupiter! what ever shall we make of these monsters?"),
    ]
    assert "OF Wom." not in text and "of Men." not in text


# H1 addendum: Genie's OCR of "Lys." as "Lrs." (a real corpus instance,
# lysistrata.txt) resolves through the same abbreviated-cue rule once the
# alias is declared, exactly like any other abbreviation.
def test_lrs_ocr_alias_resolves_to_lysistrata():
    assert PLAYS["lysistrata"].abbrev["LRS"] == "LYSISTRATA"
    cfg = _Play(title="THE TESTPLAY", word="TESTPLAY", bench="testplay", abbrev={"LRS": "LYSISTRATA"})
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("Lrs. Come now, since the other matters have been transacted well.", page=0),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), cfg)
    assert _speeches(text) == [
        ("LYSISTRATA", "Come now, since the other matters have been transacted well.")
    ]


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
