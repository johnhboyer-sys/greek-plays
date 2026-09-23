"""W. J. Hickie's Bohn Aristophanes, both volumes -- History Genie's OCR of
the vendored scans rebuilt into loeb-ocr turn-text. Vol. II
(``in.ernet.dli.2015.515630``): Lysistrata rides the ``third`` slot,
Thesmophoriazusae/Frogs/Ecclesiazusae/Wealth ride ``secondary``. Vol. I
(``in.ernet.dli.2015.515629``): Acharnians/Knights/Wasps/Peace/Birds all
ride ``secondary``.
"""

from pathlib import Path

import pytest

from drama_pipeline import genie_text as gt
from drama_pipeline.config import SOURCES_DIR
from drama_pipeline.hickie_clean import (
    GENIE_TEXT,
    GENIE_TEXT_I,
    PLAYS,
    _BARE_RANGE_RE,
    _NOTE_CLOSED_RE,
    _PAGE_NUM_RE,
    _Play,
    _collect_footnotes,
    _convert_body,
    _is_cast_heading,
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

# A vol. I play fixture (``genie=GENIE_TEXT_I``): vol. I's own first-entrance
# and cue shapes (H1, 2026-09-22) are gated on this field so that admitting
# them never changes vol. II's already-shipped bench text.
_TEST_PLAY_I = _Play(
    title="THE TESTPLAY",
    word="TESTPLAY",
    bench="testplay",
    genie=GENIE_TEXT_I,
    abbrev={"S S": "SAUSAGE-SELLER", "DEM": "DEMOSTHENES", "COM": "COMMITTEE-MAN"},
    split_cues={"DEM": ("DEMOSTHENES", "DEMUS", "DEMUS.")},
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
    # A cast-list line, even before the play's first cue, is now recognised
    # and logged by `_is_cast_heading` (H2, 2026-09-22), not the generic
    # "pre-speech text" bucket -- see
    # test_cast_heading_mid_speech_is_dropped_not_tailed_on below for the
    # bug this actually fixes (the SAME shape appearing mid-play, once a
    # speech is already open).
    assert any(line.startswith("dropped\tcharacters-present cast heading") for line in log)
    assert any(line.startswith("dropped\tHickie's own Latin") for line in log)


def test_cast_heading_mid_speech_is_dropped_not_tailed_on():
    # H2, 2026-09-22: round 1 only dropped a "characters present" cast
    # heading when it opened the play, before any speech was open yet
    # (the test above). Bohn re-announces who is on stage at a scene
    # change too, mid-play, in the exact same shape -- and THAT occurrence
    # used to fall through to `writer.line` and tail silently onto
    # whatever speech was still open (knights.txt's own "SAUSAGE-SELLER,
    # CLEON, DEMUS."). A single character's name/epithet standing alone,
    # no comma or "AND" at all (thesmophoriazusae.txt's own "FEMALE
    # HERALD."), shares the same shape and must drop the same way.
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("LY. First speech, still open.", page=0),
        _p("LYSISTRATA, CALONICE.", page=0),  # comma-joined roster, re-opens the scene
        _p("COM. New speech.", page=0),
        _p("CALONICE.", page=0),  # a single name/epithet, no comma or "AND"
        _p("LY. Final speech.", page=0),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY)
    assert "LYSISTRATA, CALONICE" not in text
    assert "CALONICE." not in text
    assert speeches == 3
    assert _speeches(text) == [
        ("LYSISTRATA", "First speech, still open."),
        ("COMMITTEE-MAN", "New speech."),
        ("LYSISTRATA", "Final speech."),
    ]
    assert sum(1 for line in log if line.startswith("dropped\tcharacters-present cast heading")) == 2
    # Bohn's own structural "PARABASIS." heading shares this exact shape
    # (all caps, ends in a period) but is NOT a character list --
    # `_is_cast_heading` must not claim it; `_SECTION_LABEL_RE`'s own
    # vol.-I-only rule owns that question instead.
    assert not _is_cast_heading("PARABASIS.")
    assert _is_cast_heading("FEMALE HERALD.")
    assert _is_cast_heading("SAUSAGE-SELLER, CLEON, DEMUS.")


def test_footnote_tail_across_an_intervening_body_page_reattaches_not_leaks():
    # H2, 2026-09-22: the 2026-09-17 fix (see
    # test_footnote_overflow_onto_next_page_before_its_own_heading above)
    # only covers a note running onto the very next page's own running
    # head/body. Bohn can also carry a too-long note past an ENTIRE
    # intervening body page -- with its own running head and real
    # dialogue -- resuming only at the top of THAT page's own footnote
    # block, ahead of its own fresh definitions (knights.txt: p. 99's
    # footnote 8, cut off mid-word "insinu-", resumes only after the
    # whole of p. 100's dialogue, "ate, that he himself is the Pylos...").
    # A genuine Hickie speech spanning a LATER, unrelated page break also
    # opens lowercase -- the discriminator is whether a note was actually
    # left open, not just the lowercase opening, so that speech must stay
    # exactly where it is.
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("LY. Something.[1]", page=1),
        _p("[1] Part one of a long note, cut off mid-", page=1),
        _p("THE TESTPLAY.", page=2),  # a whole intervening body page's own running head
        _p("COM. Real dialogue on the intervening page.", page=2),
        _p("word, orphaned at the top of the next page.", page=3),  # the note's own tail
        _p("LY. A genuine speech, running on", page=3),
        _p("across another, unrelated page break.", page=4),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY)
    assert speeches == 3
    assert any(line.startswith("note-tail") for line in log)
    assert not [line for line in log if line.startswith("uncertain")]
    assert _speeches(text) == [
        ("LYSISTRATA", "Something."),
        ("COMMITTEE-MAN", "Real dialogue on the intervening page."),
        ("LYSISTRATA", "A genuine speech, running on across another, unrelated page break."),
    ]
    assert "orphaned at the top of the next page" not in text


def test_completed_note_does_not_swallow_next_page_dialogue():
    # R3-1 (round 3 brief, blocker, 2026-09-23): `interrupted_key` used to
    # be remembered whenever a running head ended footnote mode, EVEN WHEN
    # the note it interrupted had already finished -- so a lowercase
    # dialogue continuation opening the page after next (a speech simply
    # running on, exactly the shape the test above already protects for a
    # CLEAN reset) could get glued onto an already-complete note purely
    # because it was the last one touched, silently dropping real dialogue
    # (COM's speech loses "continues on the next page.").
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("LY. One.[1]", page=1),
        _p("[1] Complete note.", page=1),
        _p("THE TESTPLAY. 10—20.", page=2),
        _p("COM. A long speech starts here and", page=2),
        _p("continues on the next page.", page=3),
        _p("LY. End.", page=3),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY)
    assert not [line for line in log if line.startswith("note-tail")]
    assert speeches == 3
    assert _speeches(text) == [
        ("LYSISTRATA", "One."),
        ("COMMITTEE-MAN", "A long speech starts here and continues on the next page."),
        ("LYSISTRATA", "End."),
    ]


def test_completed_note_ending_in_a_closer_does_not_swallow_dialogue():
    # Grok's read of round 3 (2026-09-23, finding 2): a note whose last
    # sentence ends inside a bracket or quotation mark ("...(cf. v. 10.)")
    # is just as complete as one ending on the bare period, but a
    # last-character test read it as still open and the R3-1 swallow
    # survived for exactly that shape. Lysistrata's own real tail (note 9,
    # p. 19, head ending `Tyro,"` -- a comma before the quote) must stay
    # open under the stricter test.
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("LY. One.[1]", page=1),
        _p("[1] He stops there (cf. v. 10.)", page=1),
        _p("THE TESTPLAY. 10—20.", page=2),
        _p("COM. A long speech starts here and", page=2),
        _p("continues on the next page.", page=3),
        _p("LY. End.", page=3),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY)
    assert not [line for line in log if line.startswith("note-tail")]
    assert _speeches(text) == [
        ("LYSISTRATA", "One."),
        ("COMMITTEE-MAN", "A long speech starts here and continues on the next page."),
        ("LYSISTRATA", "End."),
    ]
    assert _NOTE_CLOSED_RE.search('the Sophoclean tragedy of Tyro,"') is None
    assert _NOTE_CLOSED_RE.search("ap. Athen. vi. p. 269, F.") is not None


def test_footnote_shaped_lookahead_stops_at_the_page_edge():
    # Grok's read of round 3 (2026-09-23, finding 3): the lookahead that
    # rescues a complete-looking note's tail skipped furniture without
    # checking the page, so a `[N]` definition at the top of the NEXT page
    # could vouch for a dialogue line on this one.
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("LY. One.[1]", page=1),
        _p("[1] Complete note.", page=1),
        _p("THE TESTPLAY. 10—20.", page=2),
        _p("COM. A long speech starts here and", page=2),
        _p("continues on the next page.", page=3),
        _p("308.", page=3),
        _p("B 2", page=3),
        _p("[3] A note on the next page.", page=4),
        _p("LY. End.", page=4),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY)
    assert not [line for line in log if line.startswith("note-tail")]
    assert _speeches(text) == [
        ("LYSISTRATA", "One."),
        ("COMMITTEE-MAN", "A long speech starts here and continues on the next page."),
        ("LYSISTRATA", "End."),
    ]


def test_closed_looking_note_still_gets_a_tail_that_opens_a_note_block():
    # Grok's read of round 3b (2026-09-23, finding 3): the positive side of
    # the R3-1 guard -- a note that reads as complete ("...well explained."
    # is Knights note 6, p. 90, a real one) still gets its tail when that
    # tail is followed, on the same page, by a fresh `[N]` definition. The
    # vendored-bench test locks this only indirectly.
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("LY. Start.[1]", page=1),
        _p("[1] The meaning of the verb is well explained.", page=1),
        _p("THE TESTPLAY. 10—20.", page=2),
        _p("COM. Real dialogue.", page=2),
        _p("by Blomfield in his preface, p. xxv.", page=3),
        _p("[1] Next note.", page=3),
        _p("LY. End.", page=3),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY)
    assert [line for line in log if line.startswith("note-tail")]
    assert "Blomfield" not in text
    assert _speeches(text) == [
        ("LYSISTRATA", "Start."),
        ("COMMITTEE-MAN", "Real dialogue."),
        ("LYSISTRATA", "End."),
    ]
    notes, consumed, _log = _collect_footnotes(paras, 0, len(paras), "TESTPLAY")
    assert notes[1]["1"] == "The meaning of the verb is well explained. by Blomfield in his preface, p. xxv."


def test_bare_range_running_head_also_remembers_interrupted_key():
    # R3-2 (round 3 brief, should-fix, 2026-09-23): the `_BARE_RANGE_RE`
    # branch resets footnote mode the same way a genuine running head does
    # (the three-physical-line heading shape's own range-only paragraph),
    # but only `_is_running_head_line` used to save `interrupted_key` --
    # so a note cut off mid-word right before one never got remembered at
    # all, and its own tail (the SAME shape every real note-tail takes)
    # leaked onto whatever speech was open on the page it resurfaced on.
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("LY. Start.[1]", page=1),
        _p("[1] Long note cut off mid-", page=1),
        _p("10—20.", page=2),
        _p("THE TESTPLAY.", page=2),
        _p("COM. Real dialogue.", page=2),
        _p("word, the tail of the note.", page=3),
        _p("LY. End.", page=3),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY)
    assert any(line.startswith("note-tail") for line in log)
    assert speeches == 3
    assert _speeches(text) == [
        ("LYSISTRATA", "Start."),
        ("COMMITTEE-MAN", "Real dialogue."),
        ("LYSISTRATA", "End."),
    ]
    assert "word, the tail of the note" not in text


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


def test_printers_signature_mark_is_furniture_not_a_dialogue_tail():
    # Round 2 bug A, 2026-09-22: Bohn prints a quire signature ("2 R") on
    # its own line at the foot of a sheet's first page. Frogs p. 308 prints
    # one right after an editor's remark ("VER. 1437—1441, were obelized
    # ...") whose "VER." reads as a cue, so footnote mode ends early; the
    # remark itself is then dropped as apparatus, and the signature fell
    # through the whole cascade onto EURIPIDES's open speech as "2 R".
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("LY. First speech, still open.", page=0),
        _p("[1] A note.", page=0),
        _p(
            "VER. 10—12, were obelized by the Alexandrine critics. In Dindorf's "
            "edition, they are bracketed as doubtful. See Krüger, Gr. Gr. § 51.",
            page=0,
        ),
        _p("2 R", page=0),
        _p("2 THE TESTPLAY. 13—20.", page=1),
        _p("continued over the page.", page=1),
        _p("COM. New speech.", page=1),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY)
    assert "2 R" not in text
    assert speeches == 2
    assert _speeches(text) == [
        ("LYSISTRATA", "First speech, still open. continued over the page."),
        ("COMMITTEE-MAN", "New speech."),
    ]
    # Still furniture when it lands INSIDE a footnote block: never glued
    # onto the open note's own text as a continuation.
    notes, consumed, _log = _collect_footnotes(
        [_p("[1] A note.", page=0), _p("3 R2", page=0), _p("more of the note.", page=0)],
        0,
        3,
        "TESTPLAY",
    )
    assert notes[0]["1"] == "A note. more of the note."
    # R3-3 (round 3 brief, minor, 2026-09-23): vol. I prints the SAME quire
    # signature letter-first ("B 2", "D 2", ... "R 2") rather than
    # digit-first -- the same fake-cue path that let "2 R" leak onto open
    # dialogue above would leak one of these the same way.
    paras_i = [
        _p("THE TESTPLAY", page=0),
        _p("LY. First speech, still open.", page=0),
        _p("[1] A note.", page=0),
        _p(
            "VER. 10—12, were obelized by the Alexandrine critics. In Dindorf's "
            "edition, they are bracketed as doubtful. See Krüger, Gr. Gr. § 51.",
            page=0,
        ),
        _p("H 2", page=0),
        _p("2 THE TESTPLAY. 13—20.", page=1),
        _p("continued over the page.", page=1),
        _p("COM. New speech.", page=1),
    ]
    text_i, speeches_i, _footnotes_i, _log_i, _gaps_i = _convert_body(paras_i, 0, len(paras_i), _TEST_PLAY)
    assert "H 2" not in text_i
    assert speeches_i == 2
    assert _speeches(text_i) == [
        ("LYSISTRATA", "First speech, still open. continued over the page."),
        ("COMMITTEE-MAN", "New speech."),
    ]


def test_page_number_with_a_stray_trailing_period_is_furniture():
    # Round 2 bug B, 2026-09-22: Birds p. 501 prints its page number as
    # "365." (three-physical-line heading: range, title, number), and the
    # whole-string digits test left it on the page as a bare dialogue line.
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("LY. First speech.", page=0),
        _p("10—12.", page=1),
        _p("THE TESTPLAY.", page=1),
        _p("365.", page=1),
        _p("COM. New speech.", page=1),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY)
    assert "365" not in text
    assert speeches == 2
    assert _speeches(text) == [("LYSISTRATA", "First speech."), ("COMMITTEE-MAN", "New speech.")]
    # A bare range still belongs to `_BARE_RANGE_RE` alone, and a dotted
    # page number is not mistaken for one.
    assert _PAGE_NUM_RE.match("10—12.") is None
    assert _BARE_RANGE_RE.match("365.") is None
    assert _PAGE_NUM_RE.match("365..") is None


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


# B round 3 item 3 (Grok's read of Lane B round 2,
# review-lane-b-r2-grok-findings.md, 2026-09-17): `_is_apparatus_paragraph`
# required an editor surname AND a citation-shaped fragment, so a note that
# cites only by bare verse number ("vs. 35"), or one that carries no
# citation fragment at all but opens the paragraph on the editor's own name,
# stayed in the bench as if it were spoken (lysistrata bench 57, 457).
def test_apparatus_paragraph_dropped_for_a_bare_verse_citation_or_an_opening_editor_name():
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("LY. Calonice, my heart is on fire.", page=0),
        _p(
            "Brunck. “This passage has been misunderstood by Brunck, Dindorf, "
            "and Bothe, who think this corresponds to that in vs. 35.” Enger.",
            page=0,
        ),
        _p("COM. And so is mine, alas!", page=0),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY)
    assert speeches == 2
    assert _speeches(text) == [
        ("LYSISTRATA", "Calonice, my heart is on fire."),
        ("COMMITTEE-MAN", "And so is mine, alas!"),
    ]
    assert "Brunck" not in text and "Enger" not in text
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


# B round 3 item 3 (ecclesiazusae finding 2, 2026-09-17): a period between a
# spelled-out cue and its own parenthetical direction used to satisfy
# `_CUE_RE`'s looser shape first, leaving the whole "(...)." sitting in the
# speech text instead of becoming a direction.
def test_cue_with_period_before_its_parenthetical_direction():
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("LY. Onward!", page=0),
        _p("PRAXAGORA. (coming forward out of her hiding-place). I was lying awake.", page=0),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY)
    assert speeches == 2
    assert _speeches(text) == [
        ("LYSISTRATA", "Onward!"),
        ("PRAXAGORA", "I was lying awake."),
    ]
    assert "[coming forward out of her hiding-place]" in text
    assert "(coming forward" not in text


# Same item: a numbered or title-case chorus-role cue followed immediately
# by a parenthetical direction ("1ST WOMAN (entering with a lamp).", "Young
# Woman (looking out from an opposite window)."). `_MIXED_CUE_RE` needs a
# bare "." right after the name, so a name followed by "(" instead never
# matched at all and fell through as a continuation of whatever speech was
# already open.
def test_numbered_and_titlecase_cue_with_parenthetical_direction():
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("LY. Onward!", page=0),
        _p("1ST WOMAN (entering with a lamp). It is time to go.", page=0),
        _p("Young Woman (looking out from an opposite window). I hear you.", page=0),
        _p("1st Old Woman (pointing to the old man). And so do I.", page=0),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY)
    assert speeches == 4
    assert _speeches(text) == [
        ("LYSISTRATA", "Onward!"),
        ("FIRST WOMAN", "It is time to go."),
        ("YOUNG WOMAN", "I hear you."),
        ("FIRST OLD WOMAN", "And so do I."),
    ]
    assert "[entering with a lamp]" in text
    assert "[looking out from an opposite window]" in text
    assert "[pointing to the old man]" in text


def test_normalize_dollar_footnote_and_accented_title_and_br():
    assert _normalize("word${}^3$ more") == "word[3] more"
    assert _normalize("(_aside_)") == "(aside)"
    assert _normalize("THE ECCLÉSIAZUSÆ.") == "THE ECCLESIAZUSÆ."
    assert _normalize("text <br> more") == "text more"


# ---------------------------------------------------------------------------
# Vol. I only (2026-09-22 brief): a first-entrance cue printed on its own
# paragraph, with the speech itself a SEPARATE paragraph (Acharnians's own
# "DICÆOPOLIS (solus)."). Gated on `cfg.genie is GENIE_TEXT_I` so it never
# fires for a vol. II play.
def test_bare_cue_paren_own_paragraph_is_vol_i_only():
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("LYSISTRATA (solus).", page=0),
        _p("Well, we have met at last.", page=0),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY_I)
    assert _speeches(text) == [("LYSISTRATA", "Well, we have met at last.")]
    assert "[solus]" in text


def test_bare_cue_paren_own_paragraph_does_not_fire_for_vol_ii():
    # The SAME shape, on a vol. II (default `genie`) play: falls through to
    # the pre-existing "pre-speech junk" drop, exactly as it did before this
    # fallback was added -- regenerating vol. II must stay byte-identical.
    # (A real cue afterwards keeps `_count_speeches` from choking on a body
    # with no recognised speech at all -- not what this test is about.)
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("LYSISTRATA (solus).", page=0),
        _p("Well, we have met at last.", page=0),
        _p("COM. Something.", page=0),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY)
    assert speeches == 1
    assert "Well, we have met at last." not in text
    assert any(
        line.startswith("dropped\tpre-speech") and "solus" in line for line in log
    )


# A structural section label Genie reads as a markdown heading (never a
# speaker) -- vol. I's own "PARABASIS." (Acharnians, Knights, Wasps, Peace,
# Birds each print one). Dropped as furniture so it can never become a
# phantom speaker via `_BARE_CUE_RE`.
def test_parabasis_section_label_is_dropped_not_a_phantom_cue():
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("COM. Let us strip and follow with our own Anapaests.", page=0),
        _p("PARABASIS.", page=0),
        _p("From the time our instructor first presided.", page=0),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY_I)
    assert _speeches(text) == [
        (
            "COMMITTEE-MAN",
            "Let us strip and follow with our own Anapaests. From the time our instructor first presided.",
        )
    ]
    assert "PARABASIS" not in text


# Knights's own "Dem." collision (H1, 2026-09-22): Bohn reuses the same
# abbreviation for Demosthenes before Demus enters and for Demus himself
# after -- `split_cues` flips the resolution at the marker paragraph.
def test_split_cues_switches_abbreviation_at_the_marker():
    paras = [
        _p("THE TESTPLAY", page=0),
        _p("DEM. Alas for our misfortunes!", page=0),
        _p("DEMUS.", page=0),
        _p("DEM. Who are those that are bawling?", page=0),
    ]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY_I)
    assert _speeches(text) == [
        ("DEMOSTHENES", "Alas for our misfortunes!"),
        ("DEMUS", "Who are those that are bawling?"),
    ]


# A scan without the abbreviation's own internal period ("S S." rather than
# "S. S."), once in Knights (the Cydathenian dog scene's "S. S." elsewhere
# keeps its period): both must resolve to the same roster name.
def test_no_period_variant_of_a_two_letter_abbreviation():
    paras = [_p("THE TESTPLAY", page=0), _p("S S. How completely you imagine!", page=0)]
    text, speeches, footnotes, log, gaps = _convert_body(paras, 0, len(paras), _TEST_PLAY_I)
    assert _speeches(text) == [("SAUSAGE-SELLER", "How completely you imagine!")]


SOURCES = SOURCES_DIR


@pytest.mark.parametrize("work_id", sorted(PLAYS))
def test_vendored_text_is_the_converter_output(work_id):
    cfg = PLAYS[work_id]
    if not cfg.genie.exists():
        # Both volumes are machine-local build/ scratch files, not vendored --
        # a play's OWN volume file (not just `GENIE_TEXT`, vol. II's) decides
        # whether this can run, now that `PLAYS` spans both.
        pytest.skip("History Genie's OCR text is a machine-local build/ scratch file, not vendored")
    out = convert_play(work_id)
    assert (SOURCES / "bench" / "hickie" / f"{cfg.bench}.txt").read_text(encoding="utf-8") == out.text
    assert len(_speeches(out.text, cfg.title)) == out.speeches
