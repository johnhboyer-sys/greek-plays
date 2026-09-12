"""Kosmos Society / CHS Sourcebook HTML -> verse-own-line turn-text."""

from pathlib import Path

import pytest

from drama_pipeline.kosmos_clean import PLAYS, convert
from drama_pipeline.stage1_turn_english import parse_play_speeches


def _page(body: str) -> str:
    return (
        "<html><body><header><p><strong>Menu</strong></p></header>"
        f'<section id="main" class="articleContent contentMain">{body}</section>'
        "</body></html>"
    )


def _speeches(text: str, title: str = "PLAY"):
    speeches, _notes = parse_play_speeches(text, title, format="verse-own-line")
    return [(s["speaker_printed"], s["text"]) for s in speeches]


def test_sub_and_bold_markers_are_counted_and_stripped():
    out = convert(
        _page(
            '<h2>Agamemnon</h2><p style="text-align: center">Translated by Someone</p>'
            "<p><strong>Watchman</strong><br />"
            '<span><sub><span style="font-size: xx-small">1</span></sub></span>'
            "<span> I ask for release from these ordeals [</span><em>ponoi</em><span>] of mine,</span>"
            " <strong>5</strong> bringers of winter.</p>"
        ),
        "PLAY",
    )
    assert out.markers == 2
    assert _speeches(out.text) == [
        ("WATCHMAN", "I ask for release from these ordeals [ponoi] of mine, bringers of winter.")
    ]


def test_pipe_markers_in_every_printed_form():
    out = convert(
        _page(
            "<p><b>Nurse<br /></b>furnish oars |<b>5</b> for the hands |<b>10 </b>of men.</p>"
            "<p><b>Attendant<br />|85 </b>And who of mortals is not?</p>"
            "<p><b>|225 </b>But it is on me. Nothing |1345 amiss.</p>"
        ),
        "PLAY",
    )
    assert out.markers == 5
    assert _speeches(out.text) == [
        ("NURSE", "furnish oars for the hands of men."),
        ("ATTENDANT", "And who of mortals is not?\n\nBut it is on me. Nothing amiss."),
    ]


def test_bracketed_numbers_are_markers_bracketed_words_stay():
    out = convert(
        _page(
            "<p><strong>Poseidon</strong><br />with exact measurement [5] set towers"
            " [from <em>dikē</em>] of Kadmos [i.e., Thebes] about [10a] this land.</p>"
        ),
        "PLAY",
    )
    assert out.markers == 2
    assert _speeches(out.text) == [
        ("POSEIDON", "with exact measurement set towers [from dikē] of Kadmos [i.e., Thebes] about this land.")
    ]


def test_footnote_calls_and_label_glosses_are_dropped():
    out = convert(
        _page(
            '<p><a name="rfn1"></a> <strong>Pythia</strong><strong><a href="#fn1"><sup>1</sup></a></strong><br />'
            "I give honor to Earth.<strong><a href=\"#fn2\"><sup>2</sup></a></strong></p>"
            "<p><strong>Attendant [</strong><em>therapōn</em><strong>]</strong><br />Lord, listen.</p>"
            '<p><strong>Hecuba</strong><strong><a href="#_ftn1" name="_ftnref1"><sup>[1]</sup></a></strong><br />Ah me.</p>'
            "<p><strong>Second Half</strong>&#8211;<strong>Chorus<br /></strong>We will go.</p>"
        ),
        "PLAY",
    )
    assert out.markers == 0
    assert _speeches(out.text) == [
        ("PYTHIA", "I give honor to Earth."),
        ("ATTENDANT", "Lord, listen."),
        ("HECUBA", "Ah me."),
        ("SECOND HALF CHORUS", "We will go."),
    ]


def test_directions_kept_metre_labels_dropped():
    out = convert(
        _page(
            "<p><em>Upon the roof of the palace.</em></p>"
            "<p><strong>Watchman</strong><br />First words.</p>"
            "<p><em>He sees a flash of light.</em></p>"
            "<p>Oh welcome, light.</p>"
            "<p><em>He descends.</em></p>"
            "<p><strong>Chorus</strong></p>"
            '<p align="right"><em>anapests</em></p>'
            "<p>This is the tenth year.</p>"
        ),
        "PLAY",
    )
    speeches, _ = parse_play_speeches(out.text, "PLAY", format="verse-own-line")
    assert [s["speaker_printed"] for s in speeches] == ["WATCHMAN", "CHORUS"]
    assert speeches[0]["text"] == "First words.\n\nOh welcome, light."
    assert speeches[0]["directions_before"] == ["Upon the roof of the palace."]
    assert speeches[0]["shown"] == "First words.\n_He sees a flash of light._\nOh welcome, light."
    assert speeches[1]["directions_before"] == ["He descends."]
    assert speeches[1]["text"] == "This is the tenth year."
    assert "anapests" not in out.text


@pytest.mark.parametrize(
    "notes",
    [
        '<p><strong>Notes</strong></p><p><a name="fn1"></a>[<a href="#rfn1"> back </a>] 1. A note.</p>',
        '<p><a href="#_ftnref1" name="_ftn1"><sup>[1]</sup></a> A note.</p>',
        '<div><hr align="left" /><div id="ftn1"><p><a href="#_ftnref1" name="_ftn1">[1]</a> A note.</p></div></div>',
        '<h4 class="western">Notes</h4><p>A note.</p>',
        '<div id="sdfootnote1"><p><a class="sdfootnotesym" href="#sdfootnote1anc">1</a>A note.</p></div>',
        '<p><span style="font-size: small">2020-07-17</span></p><p>Related topics</p>',
    ],
)
def test_play_ends_before_the_notes(notes):
    out = convert(_page(f"<p><strong>Chorus</strong><br />Last words.</p>{notes}"), "PLAY")
    assert _speeches(out.text) == [("CHORUS", "Last words.")]
    assert "note" not in out.text.casefold()


def test_an_italic_name_alone_on_its_line_is_a_speaker():
    # Oedipus at Colonus prints the Stranger's cue as <em>Xenos</em>, a Greek word.
    out = convert(
        _page(
            "<p><strong>Oedipus </strong><br />Who are you?</p>"
            "<p><em>Xenos</em><br />Now, before you inquire [<em>historeîn</em>], leave this seat.</p>"
            "<p><em>Xenos </em><br />Ground inviolable.</p>"
        ),
        "PLAY",
    )
    assert _speeches(out.text) == [
        ("OEDIPUS", "Who are you?"),
        ("XENOS", "Now, before you inquire [historeîn], leave this seat."),
        ("XENOS", "Ground inviolable."),
    ]


def test_italic_lines_that_are_not_bare_names_are_not_speakers():
    out = convert(
        _page(
            "<p><strong>Chorus</strong><br />First.</p>"
            "<p><em>He descends.</em><br />Oh welcome.</p>"
            "<p><em>epode</em><br />Behold these boys!</p>"
            "<p><em>A </em>Xenos<em> enters.</em></p>"
        ),
        "PLAY",
    )
    speeches, _ = parse_play_speeches(out.text, "PLAY", format="verse-own-line")
    assert [s["speaker_printed"] for s in speeches] == ["CHORUS"]


def test_a_bold_title_heading_is_not_a_speaker():
    # Antigone prints its title as <h2><strong>Antigone</strong></h2>, then the credit.
    out = convert(
        _page(
            '<h2 style="text-align: center"><strong>Antigone</strong></h2>'
            '<p style="text-align: center">Translation of R. C. Jebb</p>'
            "<p><strong>Antigone<br /></strong>Ismene, my sister.</p>"
        ),
        "PLAY",
    )
    assert _speeches(out.text) == [("ANTIGONE", "Ismene, my sister.")]


def test_underscore_rule_line_is_skipped():
    out = convert(_page("<p><strong>Chorus</strong><br />End.</p><p>__</p>"), "PLAY")
    assert _speeches(out.text) == [("CHORUS", "End.")]


def test_chs_verse_numbers_at_line_end():
    page = (
        '<html><body><div class="TEI-XML"><div class="copy">'
        '<div class="Paragraph">Translated by Robert Potter</div>'
        '<div class="Paragraph"><em>Introduction</em>: the story so far.</div>'
        '<div class="Paragraph"><div class="inlineCitation"><strong>Amphitryon</strong><br />'
        "crop of sown men grew, of which race [<em>genos</em>] only a few 5<br />"
        'raised by the Cyclopes:<span class="noteref"> [<a href="#n.1">1</a>] </span> <a name="noteref_n.1"></a> exiled<br />'
        "<em>epode</em><br />"
        "Behold these boys! 130<br />"
        "their father's spirit.</div></div>"
        '<h2>Footnotes</h2><div class="ftNote"><div class="Paragraph">1. A note.</div></div>'
        "</div></div></body></html>"
    )
    out = convert(page, "PLAY")
    assert out.markers == 2
    assert _speeches(out.text) == [
        (
            "AMPHITRYON",
            "crop of sown men grew, of which race [genos] only a few raised by the Cyclopes: exiled "
            "Behold these boys! their father's spirit.",
        )
    ]


def test_output_has_title_line_and_speaker_count():
    out = convert(_page("<p><strong>Kassandra</strong><br />Otototoi.</p>"), "AGAMEMNON")
    assert out.text.splitlines()[0] == "AGAMEMNON"
    assert out.speeches == 1


SOURCES = Path(__file__).resolve().parents[2] / "sources"


@pytest.mark.parametrize("work_id", sorted(PLAYS))
def test_vendored_text_is_the_converter_output(work_id):
    raw = (SOURCES / "kosmos" / f"{work_id}.html").read_text(encoding="utf-8")
    out = convert(raw, PLAYS[work_id])
    assert (SOURCES / "bench" / "kosmos" / f"{work_id}.txt").read_text(encoding="utf-8") == out.text
    # Every speaker cue the converter wrote reads back as one speech: no
    # line of dialogue is mistaken for a cue, none is lost.
    assert len(_speeches(out.text, PLAYS[work_id])) == out.speeches
