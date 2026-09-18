"""Ian Johnston's play pages (johnstonia, VIU) -> verse-own-line turn-text."""

from pathlib import Path

import pytest

from drama_pipeline.johnston_clean import PLAYS, convert, read_page
from drama_pipeline.stage1_turn_english import parse_play_speeches


def _page(body: str) -> str:
    return (
        "<html><body><p>Aeschylus</p><p>Dramatis Personae</p>"
        "<p>NURSE: a servant of Medea<br>Tutor: a slave</p>"
        f"{body}</body></html>"
    )


def _parsed(text: str, title: str = "PLAY"):
    speeches, _notes = parse_play_speeches(text, title, format="verse-own-line")
    return speeches


def _speeches(text: str, title: str = "PLAY"):
    return [(s["speaker_printed"], s["text"]) for s in _parsed(text, title)]


def test_word_page_cue_first_line_and_number_markers():
    out = convert(
        _page(
            "<p><span style='text-transform:uppercase'>Nurse</span><br>"
            "O how I wish<b><sup><a href='#n1'>1</a></sup></b><br>"
            "had never sailed away <span style='font-size:10.0pt'>10</span><br>"
            "to the towers [10]<br>"
            "of Iolcus, 100 [80]<br>"
            "<span style='font-size:10.0pt'>50</span></p>"
        ),
        "PLAY",
    )
    assert out.markers == 5
    assert _speeches(out.text) == [
        ("NURSE", "O how I wish had never sailed away to the towers of Iolcus,")
    ]


def test_cue_closing_a_paragraph_opens_the_next_one():
    # The 2022 Bacchae page ends a paragraph with the cue.
    out = convert(
        _page(
            "<p><em>[Scene: Thebes, outside the palace.]</em><br><br>DIONYSUS</p>"
            "<p>I have arrived here.<strong><a href='#n1'>(1)</a></strong><br>"
            "In Thebes.&nbsp;&nbsp;&nbsp;<span> 10</span></p>"
        ),
        "PLAY",
    )
    speeches = _parsed(out.text)
    assert [(s["speaker_printed"], s["text"]) for s in speeches] == [
        ("DIONYSUS", "I have arrived here. In Thebes.")
    ]
    assert speeches[0]["directions_before"] == ["[Scene: Thebes, outside the palace.]"]


def test_a_capitals_line_in_the_cast_list_is_not_a_cue():
    out = convert(
        _page(
            "<p>CITIZENS OF THEBES</p>"
            "<p><i>[Enter Eteocles.]</i></p>"
            "<p>ETEOCLES<br>You citizens of Cadmus.</p>"
        ),
        "PLAY",
    )
    assert _speeches(out.text) == [("ETEOCLES", "You citizens of Cadmus.")]


def test_capitals_cast_list_without_colons_is_skipped():
    # Frogs and Seven list some of the cast in bare capitals.
    out = convert(
        _page(
            "<p>CHORUS OF FROGS<br>CHORUS OF INITIATES: worshippers<br>AEACUS: a gatekeeper</p>"
            "<p>SERVANT<br>FIRST HOSTESS (PANDOKEUTRIA)</p>"
            "<p>SPEAR MAKER<br>BOY, a son of Lamachus</p>"
            "<p>CITIZENS OF THEBES<br>SOLDIERS: including the champions.</p>"
            "<p>SECOND HERALD</p><p>Scene: A rugged wilderness.</p>"
            "<p><i>[Enter Xanthias.]</i></p>"
            "<p>XANTHIAS<br>Look, master, an audience!</p>"
        ),
        "PLAY",
    )
    assert _speeches(out.text) == [("XANTHIAS", "Look, master, an audience!")]


def test_directions_stay_out_of_the_speech_text():
    out = convert(
        _page(
            "<p>CLYTAEMNESTRA <i>[pulling Aegisthus<br>towards the doors]</i><br>"
            "Leave them their yelping.</p>"
            "<p><i>[They go in.</i><br><i>The doors close.]</i></p>"
            "<p>CHORUS<br><i>[To the audience]</i> Alas,<br>for this house.</p>"
        ),
        "PLAY",
    )
    speeches = _parsed(out.text)
    assert [(s["speaker_printed"], s["text"]) for s in speeches] == [
        ("CLYTAEMNESTRA", "Leave them their yelping."),
        ("CHORUS", "Alas, for this house."),
    ]
    assert "_[pulling Aegisthus towards the doors]_" in speeches[0]["shown"]
    assert speeches[1]["directions_before"] == ["[They go in. The doors close.]"]
    assert "_[To the audience]_" in speeches[1]["shown"]


def test_footnote_calls_linking_to_the_page_go_with_their_line_breaks_kept():
    out = convert(
        _page(
            "<p>EUELPIDES<br>I could use cords of linen."
            "<a href='aristophanes/birds.htm#note45'><span>*</span></a><br>"
            "No more.<a href='#n2'>2<br></a>Then go.*</p>"
        ),
        "PLAY",
    )
    assert "No more.\nThen go." in out.text
    assert _speeches(out.text) == [("EUELPIDES", "I could use cords of linen. No more. Then go.")]


# J1 (2026-09-17 round 2 brief): a footnote marker's own `<sup>` (skipped --
# Johnston's superscript numbering, not text) can carry the SOURCE's own
# `<br>` line break for the verse line it interrupts. johnston/antigone.htm
# note 8 sits in a `<sup>` between "...in the city." and "I'd trust...",
# with the `<br>` INSIDE that skipped `<sup>`; dropping the whole element
# dropped the break too, welding the two lines with no space between them
# (johnston/antigone.txt:1126, "city.I'd trust such a man to govern wisely").
def test_footnote_marker_sup_does_not_swallow_its_own_line_break():
    out = convert(
        _page(
            "<p>CHORUS<br>"
            "The man who acts well with his household<br>"
            "will be found a just man in the city.</span>"
            "<b><sup><span><a href='#n8'>8</a><br>\n</span></sup></b>"
            "<span>I'd trust such a man to govern wisely<br>"
            "or to be content with someone ruling him.</p>"
        ),
        "PLAY",
    )
    assert "city.I'd" not in out.text
    assert _speeches(out.text) == [
        (
            "CHORUS",
            "The man who acts well with his household will be found a just man "
            "in the city. I'd trust such a man to govern wisely or to be content "
            "with someone ruling him.",
        )
    ]


def test_restored_dialogue_in_plain_brackets_stays_verse_not_a_direction():
    # Johnston brackets dialogue he has himself restored or supplied after a
    # manuscript gap, but -- unlike his stage directions -- prints it in the
    # same plain (non-italic) verse font as the rest of the speech (e.g. his
    # Suppliant Women note 9: "There is apparently a line missing here. The
    # words in square brackets have been provided to maintain the logic of
    # the conversation"). The converter used to treat every "[" the same way
    # and read this restored dialogue as a stage direction.
    out = convert(
        _page(
            "<p>CHORUS<br>Look over here well.<br>"
            "[Look over here—<br>there is a symbol drawn, some form of bird.]</p>"
        ),
        "PLAY",
    )
    speeches = _parsed(out.text)
    assert speeches[0].get("directions_before") is None
    assert "_[Look over here" not in out.text
    assert speeches[0]["text"] == (
        "Look over here well. [Look over here— there is a symbol drawn, some form of bird.]"
    )


def test_an_unclosed_restoration_bracket_does_not_swallow_the_next_speaker():
    # Ian Johnston's Bacchae page brackets Agave's speech at line 1244 as
    # restored ("At this point, there is a major gap in the manuscript. The
    # text here is reconstructed...") but never closes the bracket; the next
    # "]" in the page belongs to an unrelated, later, italicized stage
    # direction. The old code read a "[" as always opening a direction and
    # accumulated every line -- Cadmus's whole intervening speech and cue
    # included -- until that unrelated "]", silently dropping Cadmus's cue
    # and merging his lines into Agave's.
    out = convert(
        _page(
            "<p>AGAVE<br>"
            "[From being your royal and honoured daughter,<br>"
            "the mother of a king, I'm now transformed.<br>"
            "Father, give me your permission now<br>"
            "to lay out here the body of my son.</p>"
            "<p>CADMUS<br>"
            "That's no easy task to undertake.<br>"
            "But if you think you can endure the work,<br>"
            "then, my child, begin the appropriate rites.</p>"
            "<p>AGAVE<br><i>[removing Pentheus's limbs]</i><br>"
            "Alas, for my poor son, my only child.</p>"
        ),
        "PLAY",
    )
    speeches = _parsed(out.text)
    assert [(s["speaker_printed"], s["text"]) for s in speeches] == [
        (
            "AGAVE",
            "[From being your royal and honoured daughter, the mother of a "
            "king, I'm now transformed. Father, give me your permission now "
            "to lay out here the body of my son.",
        ),
        (
            "CADMUS",
            "That's no easy task to undertake. But if you think you can "
            "endure the work, then, my child, begin the appropriate rites.",
        ),
        ("AGAVE", "Alas, for my poor son, my only child."),
    ]
    assert "_[removing Pentheus's limbs]_" in speeches[2]["shown"]


def test_a_brace_typed_for_a_bracket_still_closes_a_direction():
    # Johnston's Birds closes two italic directions with "}" (Birds 1102,
    # "[to Euelpides}"); the converter read on to the next "]" and swallowed
    # the dialogue between as a stage direction.
    out = convert(
        _page(
            "<p>PISTHETAIROS<br><i>[to Euelpides}</i> I think they're easing off.<br>"
            "Let's retreat.</p>"
            "<p>EUELPIDES<br>Agreed.</p>"
            "<p>CHORUS<br><i>[to all]</i><br>Now.</p>"
        ),
        "PLAY",
    )
    assert _speeches(out.text) == [
        ("PISTHETAIROS", "I think they're easing off. Let's retreat."),
        ("EUELPIDES", "Agreed."),
        ("CHORUS", "Now."),
    ]
    assert "[to Euelpides]" in out.text


def test_an_unclosed_italic_direction_ends_where_the_italics_end():
    # Birds: "<i>[advancing towards Pisthetairos and Euelpides<br></i>" never
    # closes its bracket; the chorus's song follows in plain type, and the
    # converter used to swallow it, and every speech after it, as a direction.
    out = convert(
        _page(
            "<p>CHORUS<br><i>[advancing towards them<br></i>On, on, let's attack.<br>"
            "Break them in the crush.</p>"
            "<p>PISTHETAIROS<br>We're done for.</p>"
        ),
        "PLAY",
    )
    assert _speeches(out.text) == [
        ("CHORUS", "On, on, let's attack. Break them in the crush."),
        ("PISTHETAIROS", "We're done for."),
    ]
    assert "[advancing towards them]" in out.text


def test_an_italic_line_without_brackets_is_speech():
    out = convert(_page("<p>HERMES<br><i>Io, Io!</i><br>Come here.</p>"), "PLAY")
    assert _speeches(out.text) == [("HERMES", "Io, Io! Come here.")]


@pytest.mark.parametrize(
    "tail",
    [
        "<p>ENDNOTES</p><p>1 A note.</p>",
        "<p>Epilogue</p><p>The trilogy is lost.</p>",
        "<p>[Back to johnstonia Home Page]</p><p>Page loads</p>",
        "<p>Notes to Lysistrata</p><p>*Pan was a god. [Back to Text]</p>",
    ],
)
def test_the_play_ends_before_notes_and_site_links(tail):
    out = convert(_page(f"<p>CHORUS<br>We go.</p>{tail}"), "PLAY")
    assert _speeches(out.text) == [("CHORUS", "We go.")]


def test_cue_labels_the_parser_cannot_read_are_respelled():
    out = convert(
        _page(
            "<p>WATCHMAN |<br>Zero.</p>"
            "<p>CHORUS MEMBER 1<br>One.</p>"
            "<p>A SECOND HOOPOE<br>Two.</p>"
            "<p>WOMAN C<br>Three.</p>"
            "<p>LEADER OF WOMEN’S CHORUS<br>Four.</p>"
            "<p>AESCHYLUS and EURIPIDES<br>Five.</p>"
        ),
        "PLAY",
    )
    assert _speeches(out.text) == [
        ("WATCHMAN", "Zero."),
        ("CHORUS MEMBER ONE", "One."),
        ("SECOND HOOPOE", "Two."),
        ("WOMAN-C", "Three."),
        ("LEADER OF WOMEN’S CHORUS", "Four."),
        ("AESCHYLUS AND EURIPIDES", "Five."),
    ]


def test_a_title_case_return_cue_is_recognised_when_already_seen():
    # Persians and Seven Against Thebes print a later return cue in title
    # case ("Xerxes", "Chorus", "Antigone") instead of full capitals; _CUE
    # required full capitals, so the bare line collapsed into the speech
    # above it and printed as verse inside the wrong speaker's turn
    # (persians findings #2/#3, 2026-09-15).
    out = convert(
        _page(
            "<p>CHORUS<br>Away unto the Grecian land.</p>"
            "<p>XERXES<br>Woe is me.</p>"
            "<p>Chorus<br>So small a remnant from so many!</p>"
        ),
        "PLAY",
    )
    assert _speeches(out.text) == [
        ("CHORUS", "Away unto the Grecian land."),
        ("XERXES", "Woe is me."),
        ("CHORUS", "So small a remnant from so many!"),
    ]


def test_a_title_case_line_that_is_no_cue_yet_stays_verse():
    # The guard for the fix above: a one-word line of verse that happens to
    # start with a capital letter (every English sentence does) must not be
    # mistaken for a return cue just because it is title case. Only a name
    # already spoken in full capitals earlier in the play qualifies.
    out = convert(_page("<p>WATCHMAN<br>Zero.</p>"), "PLAY")
    assert _speeches(out.text) == [("WATCHMAN", "Zero.")]


def test_a_colon_punctuated_cue_is_recognised():
    # Frogs and Ajax print some Johnston cues with a trailing colon instead
    # of the cue standing alone on its line ("CHORUS:", "AESCHYLUS:",
    # "AESCHYLUS and EURIPIDES: [...]"); _CUE required the name to be the
    # whole line with nothing after it, so these speeches folded into the
    # one above and the Greek they render showed an empty column (frogs
    # finding #2, ajax finding #6, 2026-09-15).
    out = convert(
        _page(
            "<p>DIONYSUS<br>Come here, then.</p>"
            "<p>CHORUS:<br>Clever men like these take pains.</p>"
            "<p>AESCHYLUS and EURIPIDES: <i>[each one holding a scale pan]</i><br>"
            "We are ready.</p>"
        ),
        "PLAY",
    )
    speeches = _parsed(out.text)
    assert [(s["speaker_printed"], s["text"]) for s in speeches] == [
        ("DIONYSUS", "Come here, then."),
        ("CHORUS", "Clever men like these take pains."),
        ("AESCHYLUS AND EURIPIDES", "We are ready."),
    ]
    assert "_[each one holding a scale pan]_" in speeches[2]["shown"]


def test_a_digit_named_cue_with_a_colon_is_recognised():
    # Ajax's Johnston text prints "CHORAL GROUP 2 LEADER:" in the search
    # scene: a cue that already carries a digit also failed once a trailing
    # colon was added (ajax finding #6, 2026-09-15).
    out = convert(
        _page("<p>CHORAL GROUP 2 LEADER:<br>We've searched everywhere.</p>"),
        "PLAY",
    )
    assert _speeches(out.text) == [
        ("CHORAL GROUP TWO LEADER", "We've searched everywhere.")
    ]


def test_output_has_title_line_and_speaker_count():
    out = convert(_page("<p>CASSANDRA<br>Otototoi.</p>"), "AGAMEMNON")
    assert out.text.splitlines()[0] == "AGAMEMNON"
    assert out.speeches == 1


def test_read_page_takes_utf8_else_windows_1252(tmp_path):
    utf = tmp_path / "a.htm"
    utf.write_bytes("<p>Jason’s</p>".encode("utf-8"))
    cp = tmp_path / "b.htm"
    cp.write_bytes("<p>Jason’s</p>".encode("cp1252"))
    assert read_page(utf) == read_page(cp) == "<p>Jason’s</p>"


SOURCES = Path(__file__).resolve().parents[2] / "sources"


@pytest.mark.parametrize("work_id", sorted(PLAYS))
def test_vendored_text_is_the_converter_output(work_id):
    out = convert(read_page(SOURCES / "johnston" / f"{work_id}.htm"), PLAYS[work_id])
    assert (SOURCES / "bench" / "johnston" / f"{work_id}.txt").read_text(encoding="utf-8") == out.text
    # Every cue the converter wrote reads back as one speech.
    assert len(_speeches(out.text, PLAYS[work_id])) == out.speeches
