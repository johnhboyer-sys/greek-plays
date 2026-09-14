"""Gilbert Murray's verse (Project Gutenberg text, Wikisource HTML) -> verse-own-line turn-text."""

from pathlib import Path

import pytest

from drama_pipeline.murray_clean import PLAYS, convert_gutenberg, convert_play, convert_wikisource, read_text
from drama_pipeline.stage1_turn_english import parse_play_speeches


def _parsed(text: str, title: str = "PLAY"):
    speeches, _notes = parse_play_speeches(text, title, format="verse-own-line")
    return speeches


def _speeches(text: str, title: str = "PLAY"):
    return [(s["speaker_printed"], s["text"]) for s in _parsed(text, title)]


GUTENBERG = """\
*** START OF THE PROJECT GUTENBERG EBOOK ***

                                  MEDEA

                         CHARACTERS OF THE PLAY

MEDEA, _daughter of Aietes_.
NURSE _of Medea_.
A MESSENGER.

CHORUS of Corinthian Women, with their LEADER.




                 MEDEA


_The Scene represents the front of_ MEDEA'S _House in Corinth.
    The_ NURSE _is discovered alone_.


                 NURSE.

  Would God no Argo e'er had winged the seas
  To Colchis through the _blue_ Symplegades:
    But now, the world is angry.

[_The_ CHILDREN _and their_ ATTENDANT
_come in_.]

ATTENDANT (_to the Nurse_).

  Thou ancient treasure of my lady's room.

CHORUS.

(_The dash marks a new speaker._)

_Some Women._
  I heard a voice and a moan.

ELDER B. [vv. 1348-49]
  Summon all the citizens! [vv. 1350-52]

* * * * *

[Illustration]

MEDEA (_within_)
  Ah, woe is me!

[_Exeunt._

NOTES TO MEDEA

P. 1, l. 1. A note.
"""


def test_gutenberg_play_between_its_heading_and_its_notes():
    out = convert_gutenberg(GUTENBERG, "PLAY", start="MEDEA", end="NOTES TO MEDEA")
    speeches = _parsed(out.text)
    assert [(s["speaker_printed"], s["text"]) for s in speeches] == [
        ("NURSE", "Would God no Argo e'er had winged the seas To Colchis through the blue Symplegades: But now, the world is angry."),
        ("ATTENDANT", "Thou ancient treasure of my lady's room."),
        ("CHORUS", "I heard a voice and a moan."),
        ("ELDER-B", "Summon all the citizens!"),
        ("MEDEA", "Ah, woe is me!"),
    ]
    assert speeches[0]["directions_before"] == [
        "The Scene represents the front of MEDEA'S House in Corinth. The NURSE is discovered alone."
    ]
    assert speeches[1]["directions_before"] == ["[The CHILDREN and their ATTENDANT come in.]"]
    assert "_(to the Nurse)_" in speeches[1]["shown"]
    # Two direction lines running on print as one direction.
    assert "_(The dash marks a new speaker.) Some Women._" in speeches[2]["shown"]
    assert "_(within)_" in speeches[4]["shown"]
    # An unclosed bracket ends with its paragraph; the notes never come in.
    assert "_[Exeunt._" in speeches[4]["shown"]
    assert "A note" not in out.text and "Illustration" not in out.text
    assert out.speeches == 5


def test_gutenberg_wrapped_cue_direction_and_a_cue_sharing_a_verse_line():
    # The Trojan Women (pg35171) prints both.
    text = (
        "CHARACTERS IN THE PLAY\n\nHECUBA, _Queen of Troy_.\n\n\n"
        "THE TROJAN WOMEN\n\n"
        "FIFTH WOMAN.\n"
        "    How have they cast me, and to whom\n"
        "    A bondmaid?\n"
        "HECUBA.      Peace, child: wait thy doom.\n\n"
        "TALTHYBIUS (_bending over_ ANDROMACHE _and gradually taking the Child\n"
        "from her_).\n\n"
        "  Come, child: let be.\n\n"
        "LEADER.   [_Antistrophe._\n"
        "  O Troy, my Troy!\n"
    )
    out = convert_gutenberg(text, "PLAY", start="THE TROJAN WOMEN", end="NOTES")
    speeches = _parsed(out.text)
    assert [(s["speaker_printed"], s["text"]) for s in speeches] == [
        ("FIFTH WOMAN", "How have they cast me, and to whom A bondmaid?"),
        ("HECUBA", "Peace, child: wait thy doom."),
        ("TALTHYBIUS", "Come, child: let be."),
        ("LEADER", "O Troy, my Troy!"),
    ]
    assert "_(bending over ANDROMACHE and gradually taking the Child from her)_" in speeches[2]["shown"]
    assert "_[Antistrophe._" in speeches[3]["shown"]


def test_gutenberg_lyric_label_does_not_swallow_the_verse_below_it():
    # "[_Strophe_ 1." never closes its bracket (Trojan Women, parodos).
    text = (
        "CHARACTERS IN THE PLAY\n\nHECUBA, _Queen of Troy_.\n\n\n"
        "THE TROJAN WOMEN\n\n"
        "[_The Women steal\n    out severally, startled and afraid._\n\n"
        "                   FIRST WOMAN.\n"
        "                                               [_Strophe_ 1.\n"
        "    How say'st thou? Whither moves thy cry,\n"
        "      Thy bitter cry?\n"
    )
    out = convert_gutenberg(text, "PLAY", start="THE TROJAN WOMEN", end="NOTES")
    speeches = _parsed(out.text)
    assert [(s["speaker_printed"], s["text"]) for s in speeches] == [
        ("FIRST WOMAN", "How say'st thou? Whither moves thy cry, Thy bitter cry?"),
    ]
    assert speeches[0]["directions_before"] == ["[The Women steal out severally, startled and afraid."]
    assert "_[Strophe 1._" in speeches[0]["shown"]


def test_gutenberg_cast_list_in_capitals_before_the_first_cue():
    # Hippolytus (pg8418): no heading between the cast list and the play, and
    # cues are indented capitals with no stop.
    text = (
        "DRAMATIS PERSONAE\n\n"
        "   THE GODDESS APHRODITE\n"
        "   THESEUS, _King of Athens_\n"
        "   THE NURSE OF PHAEDRA\n"
        "   A CHORUS OF TROZENIAN WOMEN, WITH THEIR LEADER\n\n"
        "_The scene is laid in Trozen._\n\n\n"
        "    APHRODITE\n"
        "  Great among men, and not unnamed am I.\n\n"
        "EURIPIDES\n"
        "  The Cyprian, in God's inmost halls.\n\n"
        "    HUNTSMAN (_approaching the Statue and kneeling_)\n"
        "  Hail, O my Queen!\n\n"
        "THE BACCHAE\n\n"
        "    DIONYSUS\n"
        "  Behold, God's Son is come.\n"
    )
    out = convert_gutenberg(text, "PLAY", start="DRAMATIS PERSONAE", end="THE BACCHAE")
    assert _speeches(out.text) == [
        # The running head goes; the blank line printed before it stays.
        ("APHRODITE", "Great among men, and not unnamed am I.\n\nThe Cyprian, in God's inmost halls."),
        ("HUNTSMAN", "Hail, O my Queen!"),
    ]


def test_gutenberg_without_underscores_keeps_its_brackets_and_capitals():
    # Iphigenia in Tauris (pg5063) prints no italics.
    text = (
        "CHARACTERS OF THE PLAY\n\nTHOAS, King of Tauris.\n\n\n"
        "THE IPHIGENIA IN TAURIS\n\n"
        "[The Scene shows a great Temple. IPHIGENIA\ncomes out from the Temple.]\n\n"
        "IPHIGENIA.\n\nChild of the man of torment and of pride.\n\n"
        "IPHIGENIA (WITH SUDDEN IMPULSE).\n\nListen!\n"
    )
    out = convert_gutenberg(text, "PLAY", start="THE IPHIGENIA IN TAURIS", end="NOTES")
    speeches = _parsed(out.text)
    assert [(s["speaker_printed"], s["text"]) for s in speeches] == [
        ("IPHIGENIA", "Child of the man of torment and of pride."),
        ("IPHIGENIA", "Listen!"),
    ]
    assert speeches[0]["directions_before"] == ["[The Scene shows a great Temple. IPHIGENIA comes out from the Temple.]"]
    assert "_(WITH SUDDEN IMPULSE)_" in speeches[1]["shown"]


def _ws(body: str) -> str:
    return (
        '<div class="mw-parser-output"><div class="ws-noexport">header</div>'
        f'<div class="prp-pages-output" lang="en">{body}</div></div>'
    )


SC = '<span class="smallcaps" style="font-variant:small-caps;">{}</span>'


def test_wikisource_cues_directions_and_page_numbers():
    html = _ws(
        '<div class="wst-center tiInherit"><p><span style="font-size:144%;">THE FROGS</span></p></div>'
        f'<div class="wst-hanging-indent"><i>Enter</i> {SC.format("Dionysus")}<i>, disguised</i>.</div>'
        f'<div class="wst-center tiInherit"><p>{SC.format("Xanthias")}<br />(<i>looking round</i>).</p></div>'
        "<p>Sir, shall I say one of the regular things<br />"
        '<span class="pagenum ws-pagenum" data-page-number="4"><span class="pagenum-inner">&#8203;</span></span>'
        "That people always laugh at?</p><p><br /></p>"
        f'<div class="wst-right"><p>[{SC.format("Dionysus")} <i>shrugs</i>.</p></div>'
        f'<div class="wst-center tiInherit"><p>{SC.format("Dionysus")}.</p></div>'
        '<p><span class="wst-gap __gap" style="display:inline-block"></span>Say what you like.</p>'
        f'<div class="wst-center tiInherit"><p>{SC.format("Frogs")}.</p></div>'
        '<div class="wst-dent" style="margin-left:4em;"><p>Brekekekex co-äx.<br />Co-äx!</p></div>'
        '<div class="wst-center tiInherit"><p><i>Semi-Chorus I.</i></p></div>'
        "<p>Now go.</p>"
        f'<div class="wst-center tiInherit"><p>{SC.format("Aeschylus")} <i>and</i> {SC.format("Euripides")}.</p></div>'
        "<p>Farewell.</p>"
        '<div class="wst-center tiInherit"><p><i>The door opens again. Enter</i> '
        f'{SC.format("Euripides")}<i>, and others.</i></p></div>'
        '<hr class="wst-rule" />'
    )
    out = convert_wikisource(html, "PLAY")
    speeches = _parsed(out.text)
    assert [(s["speaker_printed"], s["text"]) for s in speeches] == [
        ("XANTHIAS", "Sir, shall I say one of the regular things That people always laugh at?"),
        ("DIONYSUS", "Say what you like."),
        # An indented lyric is verse, not a direction.
        ("FROGS", "Brekekekex co-äx. Co-äx!"),
        ("SEMI-CHORUS-I", "Now go."),
        ("AESCHYLUS AND EURIPIDES", "Farewell."),
    ]
    assert speeches[0]["directions_before"] == ["Enter DIONYSUS, disguised."]
    assert "_(looking round)_" in speeches[0]["shown"]
    assert speeches[1]["directions_before"] == ["[DIONYSUS shrugs."]
    assert "_The door opens again. Enter EURIPIDES, and others._" in speeches[4]["shown"]
    assert out.speeches == 5


def test_read_text_takes_utf8_else_latin1(tmp_path):
    utf = tmp_path / "a.txt"
    utf.write_bytes("Semelê".encode("utf-8"))
    lat = tmp_path / "b.txt"
    lat.write_bytes("Semelê".encode("latin-1"))
    assert read_text(utf) == read_text(lat) == "Semelê"


SOURCES = Path(__file__).resolve().parents[2] / "sources"


@pytest.mark.parametrize("work_id", sorted(PLAYS))
def test_vendored_text_is_the_converter_output(work_id):
    out = convert_play(work_id)
    title = PLAYS[work_id][1]
    assert (SOURCES / "bench" / "murray" / f"{work_id}.txt").read_text(encoding="utf-8") == out.text
    # Every cue the converter wrote reads back as one speech.
    assert len(_speeches(out.text, title)) == out.speeches


def test_gutenberg_italic_paragraph_without_brackets_is_a_direction():
    text = """\
*** START OF THE PROJECT GUTENBERG EBOOK ***

                         CHARACTERS OF THE PLAY

APOLLO.
THANATOS.


                 ALCESTIS


                 APOLLO.

  He hath watched, and cometh at the fall of fate.

_Enter from the other side_ THANATOS; _a crouching black-haired and
winged figure, carrying a drawn sword. He starts in revulsion on
seeing_ APOLLO.

                 THANATOS.

  Aha! _Thou_ here?
_Sorrow, sing sorrow: but good prevail, prevail_!

NOTES
"""
    out = convert_gutenberg(text, "PLAY", start="ALCESTIS", end="NOTES")
    speeches = _parsed(out.text)
    assert [s["speaker_printed"] for s in speeches] == ["APOLLO", "THANATOS"]
    assert speeches[1]["directions_before"] == [
        "Enter from the other side THANATOS; a crouching black-haired and winged figure, carrying a drawn sword. He starts in revulsion on seeing APOLLO."
    ]
    assert "Enter from the other side" not in speeches[0]["text"]
    # A verse line that merely opens with an italic word stays verse, and so
    # does a wholly italic refrain that names no one in capitals.
    assert speeches[1]["text"] == "Aha! Thou here? Sorrow, sing sorrow: but good prevail, prevail!"
