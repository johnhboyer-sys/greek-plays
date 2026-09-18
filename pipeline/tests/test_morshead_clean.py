"""E. D. A. Morshead's Aeschylus, Wikisource's proofread transcriptions ->
verse-own-line turn-text (Four Plays of Aeschylus's ProofreadPage markup,
The House of Atreus's <poem> markup)."""

from pathlib import Path

import pytest

from drama_pipeline.morshead_clean import (
    FOUR_PLAYS,
    HOUSE_OF_ATREUS,
    PLAYS,
    convert_four_plays,
    convert_house_of_atreus,
    convert_play,
)
from drama_pipeline.stage1_turn_english import parse_play_speeches


def _parsed(text: str, title: str = "PLAY"):
    speeches, _notes = parse_play_speeches(text, title, format="verse-own-line")
    return speeches


def _speeches(text: str, title: str = "PLAY"):
    return [(s["speaker_printed"], s["text"]) for s in _parsed(text, title)]


SC = '<span class="smallcaps" style="font-variant:small-caps;">{}</span>'


def _prp(index: str, body: str) -> str:
    return (
        f'<div class="prp-pages-output" lang="en" data-mw=\'{{"attrs":{{"index":"x","include":"{index}"}}}}\'>'
        f"{body}</div>"
    )


def _four_plays_page(main_body: str) -> str:
    # Front matter: a title page and a dramatis-personae block, each much
    # smaller than the real play -- convert_four_plays picks the biggest
    # `prp-pages-output` block, so front matter never needs excluding by name.
    front = _prp(
        "1",
        '<div class="wst-center tiInherit"><p><span style="font-size:144%;">THE PLAY</span></p></div>'
        '<div class="wst-block-center"><p>Chorus.<br/>A Messenger.</p></div>',
    )
    main = _prp("2", main_body)
    return f'<html><body><section><div class="mw-parser-output">{front}{main}</div></section></body></html>'


def test_four_plays_cue_verse_direction_and_page_furniture():
    html = _four_plays_page(
        f'<div class="wst-center tiInherit">{SC.format("Chorus")}</div>'
        '<p>Away unto the Grecian land<br/>Hath passed the Persian armament:</p>'
        # An indented reply under a centred cue, unwrapped by any special
        # class ("Layout 2"'s convention) -- must read as verse, not a stray
        # direction (2026-09-15 regression: seven-against-thebes lost 29
        # Chorus turns to exactly this).
        f'<div class="wst-center tiInherit">{SC.format("Eteocles")}</div>'
        '<div style="margin-left:2em"><p>Say on, and I will hear and heed thy words.</p></div>'
        # A cue with its own attached direction.
        f'<div class="wst-center tiInherit">{SC.format("Xerxes")} (holding up a torn robe).</div>'
        "<p>By Xerxes, great Darius' child!</p>"
        # A compound cue Wikisource prints with commas.
        f'<div class="wst-center tiInherit">Antigone, Ismene, and Chorus  (Processional Chant)</div>'
        "<p>Thou wert smitten, in smiting.</p>"
        # A bracketed direction, off on its own line.
        '<div class="wst-right">[Exeunt.</div>'
        # The book's colophon, on the last leaf of its last play.
        '<div class="wst-center tiInherit">Printed by R. &amp; R. Clark, Limited, Edinburgh.</div>'
    )
    out = convert_four_plays(html, "PLAY")
    speeches = _parsed(out.text)
    assert [(s["speaker_printed"], s["text"]) for s in speeches] == [
        ("CHORUS", "Away unto the Grecian land Hath passed the Persian armament:"),
        ("ETEOCLES", "Say on, and I will hear and heed thy words."),
        ("XERXES", "By Xerxes, great Darius' child!"),
        ("ANTIGONE ISMENE AND CHORUS", "Thou wert smitten, in smiting."),
    ]
    assert "_(holding up a torn robe)_" in speeches[2]["shown"]
    assert "_[Exeunt._" in speeches[3]["shown"]
    assert "Printed by" not in out.text
    assert "THE PLAY" not in out.text
    assert "A Messenger" not in out.text  # the front-matter cast list
    assert out.speeches == 4


# B8 (fix-mechanisms brief, 2026-09-17): prometheus-bound review finding 5.
# Wikisource wraps only the word "To" in `<i>`, not the whole "(To NAME)"
# phrase, so the direction never reads as italic and the `<p>`-tag path
# (which has no direction detection at all) printed it as a verse line.
def test_four_plays_p_tag_direction_unitalicised_except_the_word_to():
    # `convert_four_plays` picks the block with the most children; a third,
    # otherwise-irrelevant element keeps this fixture bigger than the
    # front-matter block it is compared against.
    html = _four_plays_page(
        f'<div class="wst-center tiInherit">{SC.format("Chorus")}</div>'
        "<p>For Zeus, defied, is heavy in revenge!<br/>"
        f"(<i>To</i> {SC.format('Prometheus')})<br/>"
        "O deep-devising child of Themis sage,</p>"
        '<div class="wst-right">[Exeunt.</div>'
    )
    out = convert_four_plays(html, "PLAY")
    speeches = _parsed(out.text)
    assert speeches[0]["speaker_printed"] == "CHORUS"
    assert speeches[0]["text"] == (
        "For Zeus, defied, is heavy in revenge! O deep-devising child of Themis sage,"
    )
    assert "(To PROMETHEUS)" not in speeches[0]["text"]
    assert "_(To PROMETHEUS)_" in speeches[0]["shown"]


# The same `<p>`-tag path must also catch an unclosed bracket direction by
# shape alone (persians.txt:137 "[Enter ATOSSA.").
def test_four_plays_p_tag_unclosed_bracket_direction_by_shape_alone():
    # A third, otherwise-irrelevant element keeps this fixture's block
    # bigger than the front-matter block it is compared against.
    html = _four_plays_page(
        f'<div class="wst-center tiInherit">{SC.format("Chorus")}</div>'
        "<p>Or hath the lance-point conquered now?<br/>"
        "[Enter ATOSSA.<br/>"
        "See, yonder comes the mother-queen,</p>"
        '<div class="wst-right">[Exeunt.</div>'
    )
    out = convert_four_plays(html, "PLAY")
    speeches = _parsed(out.text)
    assert speeches[0]["text"] == (
        "Or hath the lance-point conquered now? See, yonder comes the mother-queen,"
    )
    assert "_[Enter ATOSSA._" in speeches[0]["shown"]


def _poem_page(body: str) -> str:
    return f'<html><body><h2>Drama</h2><div class="poem"><p>{body}</p></div></body></html>'


def test_house_of_atreus_cue_direction_and_entrance_sharing_a_cue_s_line():
    html = _poem_page(
        "<i>The Scene is the Palace of Atreus.</i><br/>"
        "<br/>"
        "<b>A Watchman:</b><br/>"
        "<br/>"
        "I pray the gods to quit me of my toils,<br/>"
        "To close the watch I keep, this livelong year.<br/>"
        "<br/>"
        # An entrance direction sharing its line with the cue it introduces.
        "<i>Enter</i> <b>Herald:</b><br/>"
        "<br/>"
        "O land of Argos, fatherland of mine!<br/>"
        "<br/>"
        # A cue with a trailing parenthetical direction on the same line.
        "<b>Athena:</b> (<i>to Orestes</i>)<br/>"
        "<br/>"
        "Answer thou, setting word to match with word.<br/>"
    )
    out = convert_house_of_atreus(html, "PLAY")
    speeches = _parsed(out.text)
    assert [(s["speaker_printed"], s["text"]) for s in speeches] == [
        (
            "WATCHMAN",
            "I pray the gods to quit me of my toils, To close the watch I keep, this livelong year.",
        ),
        ("HERALD", "O land of Argos, fatherland of mine!"),
        ("ATHENA", "Answer thou, setting word to match with word."),
    ]
    assert speeches[0]["directions_before"] == ["The Scene is the Palace of Atreus."]
    assert speeches[1]["directions_before"] == ["Enter."]
    assert "_(to Orestes)_" in speeches[2]["shown"]
    assert out.speeches == 3


SOURCES = Path(__file__).resolve().parents[2] / "sources"


@pytest.mark.parametrize("work_id", sorted(PLAYS))
def test_vendored_text_is_the_converter_output(work_id):
    out = convert_play(work_id)
    _name, title = PLAYS[work_id]
    assert (SOURCES / "bench" / "morshead" / f"{work_id}.txt").read_text(encoding="utf-8") == out.text
    assert len(_speeches(out.text, title)) == out.speeches


def test_four_plays_and_house_of_atreus_partition_every_work_id():
    assert set(FOUR_PLAYS) | set(HOUSE_OF_ATREUS) == set(PLAYS)
    assert not (set(FOUR_PLAYS) & set(HOUSE_OF_ATREUS))


def test_divide_opens_a_speech_before_the_named_line_and_insists_every_cut_fires():
    from drama_pipeline.morshead_clean import _divide

    items = [("cue", "CHORUS"), ("line", "I wail in terror."), ("line", "As a torrent it nears!"), ("para",)]
    assert _divide(items, (("CHORUS", "As a torrent"),)) == [
        ("cue", "CHORUS"),
        ("line", "I wail in terror."),
        ("cue", "CHORUS"),
        ("line", "As a torrent it nears!"),
        ("para",),
    ]
    with pytest.raises(ValueError, match="division not found"):
        _divide(items, (("ISMENE", "Not in the text"),))
