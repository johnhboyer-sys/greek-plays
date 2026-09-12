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
            "<p>CHORUS<br>[To the audience] Alas,<br>for this house.</p>"
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
