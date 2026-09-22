"""Gilbert Murray's verse (Project Gutenberg text, Wikisource HTML) -> verse-own-line turn-text."""

from pathlib import Path

import pytest

from drama_pipeline.murray_clean import (
    PLAYS,
    _direction_line_closes,
    convert_gutenberg,
    convert_play,
    convert_wikisource,
    read_text,
)
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
    # A strophe/antistrophe label is editorial apparatus, not a stage
    # direction: it must not survive as a rendered direction either (B3,
    # fix-mechanisms brief, 2026-09-17).
    assert "shown" not in speeches[3]


# B4 (fix-mechanisms brief, 2026-09-17): a cue's own bracketed direction
# wraps a turnover onto the next line -- agamemnon.txt:1613-1614,
# "CASSANDRA. [By an effort she regains mastery of herself, and speaks" /
# "directly to the Leader.]" -- and the bracket never closed on the cue's own
# line, so the whole thing fell through as a stray verse line instead of a
# cue plus its direction.
def test_gutenberg_cue_with_bracket_direction_wrapping_a_turnover():
    text = (
        "CHARACTERS IN THE PLAY\n\nCASSANDRA.\n\n\n"
        "THE PLAY\n\n"
        "CHORUS.\n"
        "  Their end I cannot read!\n\n"
        "CASSANDRA. [By an effort she regains mastery of herself, and speaks\n"
        "directly to the Leader.]\n\n"
        "  'Fore God, mine oracle shall no more hide\n"
    )
    out = convert_gutenberg(text, "PLAY", start="THE PLAY", end="NOTES")
    assert "[By an effort" not in out.text.split("\n")[0]
    speeches = _parsed(out.text)
    assert speeches[1]["speaker_printed"] == "CASSANDRA"
    assert speeches[1]["text"] == "'Fore God, mine oracle shall no more hide"
    assert speeches[1]["shown"].startswith(
        "_[By an effort she regains mastery of herself, and speaks directly to the Leader.]_"
    )
    assert "[By an effort" not in speeches[1]["text"]


# G3 (Grok's round-2 read, 2026-09-17): `_CUE_AND_OPEN_BRACKET` did not close
# a lyric label the way the plain `[`-start path already does -- a cue whose
# own bracket opens with a strophe/antistrophe label ("LEADER. [_Strophe._")
# stayed "open" waiting for a closing "]" that never comes; verse on the
# very next physical line, with no blank paragraph break, was swallowed
# into the still-open direction instead of becoming its own speech text.
def test_gutenberg_cue_with_lyric_label_bracket_closes_without_a_blank_line():
    text = (
        "CHARACTERS IN THE PLAY\n\nLEADER.\n\n\n"
        "THE PLAY\n\n"
        "CHORUS.\n"
        "  Their end I cannot read!\n\n"
        "LEADER. [_Strophe._\n"
        "  What is this that evermore,\n"
        "  A cold terror at the door.\n"
    )
    out = convert_gutenberg(text, "PLAY", start="THE PLAY", end="NOTES")
    # murray_clean.py's own job: the label is a complete, closed direction
    # of its own line, not glued onto the verse that follows it.
    assert "LEADER\n_[Strophe._\nWhat is this that evermore," in out.text
    speeches = _parsed(out.text)
    assert speeches[1]["speaker_printed"] == "LEADER"
    # stage1's own B3 rule (2026-09-17) drops the label entirely once it is
    # a properly separated direction -- it must not survive as a cue, verse,
    # or rendered direction in the fully parsed speech.
    assert speeches[1]["text"] == "What is this that evermore, A cold terror at the door."
    assert "shown" not in speeches[1]
    assert "[" not in speeches[1]["text"] and "]" not in speeches[1]["text"]


# B4 (fix-mechanisms brief, 2026-09-17): Project Gutenberg's pg27673
# (oedipus-tyrannus) prints a page-boundary marker, "_[Sidenote: vv. N-N]_",
# that is not verse and not stage business. It must vanish entirely, whether
# it falls between two speeches or in the middle of one.
# B round 3 item 1 (trojan-women 852/462/780/1042, rhesus 1:518 etc.,
# 2026-09-17): a mid-speech aside opens `[` and closes only its own italics
# ("[_Turning upon the Herald._", two balanced underscores) -- Murray's
# Gutenberg editions never print a `]` for this shape at all. Only a literal
# `]` or a blank paragraph line used to close a direction, so this one kept
# accumulating every following verse line (and, at the paragraph's end, the
# next cue) as still-open direction text.
def test_gutenberg_unclosed_bracket_direction_closes_at_its_own_italics():
    text = (
        "CHARACTERS IN THE PLAY\n\nCASSANDRA.\n\n\n"
        "THE PLAY\n\n"
        "CASSANDRA.\n"
        "  With flesh still clean I give them back to thee,\n"
        "[_Turning upon the Herald._\n"
        "Where lies the galley? Whither shall I tread?\n"
        "See that your watch be set, your sail be spread.\n"
    )
    out = convert_gutenberg(text, "PLAY", start="THE PLAY", end="NOTES")
    lines = out.text.splitlines()
    assert "_[Turning upon the Herald._" in lines
    assert "Where lies the galley? Whither shall I tread?" in lines
    assert "See that your watch be set, your sail be spread." in lines
    speeches = _parsed(out.text)
    assert len(speeches) == 1
    assert speeches[0]["speaker_printed"] == "CASSANDRA"
    assert "Where lies the galley" in speeches[0]["text"]
    assert "See that your watch be set" in speeches[0]["text"]
    assert "Turning upon the Herald" not in speeches[0]["text"]


# Same item, the multi-line genuine direction must still work: its italics
# stay unbalanced (an odd run of underscores) until its own last line, so it
# is not cut short by the new rule (rhesus.txt:1317-1319, never touched by
# this brief but the shape the cap must not break).
def test_gutenberg_unclosed_bracket_direction_stays_open_while_its_italics_are_unbalanced():
    text = (
        "CHARACTERS IN THE PLAY\n\nHECTOR.\nRHESUS.\n\n\n"
        "THE PLAY\n\n"
        "HECTOR.\n"
        "  With word of the Argives' counsel.\n"
        "[_Exeunt_ HECTOR _and_ RHESUS _and Attendants. The Guards, who\n"
        "have been below, come forward sleepily from the camp fire,\n"
        "and sit watching by_ HECTOR's _tent_.\n\n"
        "CHORUS.\n"
        "  Say, whose is the watch?\n"
    )
    out = convert_gutenberg(text, "PLAY", start="THE PLAY", end="NOTES")
    lines = out.text.splitlines()
    assert "_[Exeunt HECTOR and RHESUS and Attendants. The Guards, who have been below, come forward sleepily from the camp fire, and sit watching by HECTOR's tent._" in lines
    speeches = _parsed(out.text)
    assert [s["speaker_printed"] for s in speeches] == ["HECTOR", "CHORUS"]
    assert speeches[1]["text"] == "Say, whose is the watch?"


# Same item: a direction whose list of names ends the italics on a plain
# capitalised word with no sentence-final stop of its own until the NEXT
# line ("[_They pray to_ ATHENA, ARTEMIS, _and_" / "APOLLO.",
# oedipus-tyrannus.txt:650-651) must keep that whole list as the direction,
# even though the final name alone would otherwise look like a cue -- Apollo
# never speaks in this play, and an earlier version of this rule that closed
# a direction in front of anything cue-shaped turned "APOLLO." into a
# spurious, textless cue (caught by the pipeline's own `unaliased English
# speakers` gate on a full rebuild, not by a unit test).
def test_gutenberg_unclosed_bracket_direction_list_ending_on_a_name_stays_whole():
    text = (
        "CHARACTERS IN THE PLAY\n\nCHORUS.\n\n\n"
        "THE PLAY\n\n"
        "CHORUS.\n"
        "  Unveil thee, thou dread benediction,\n"
        "[_They pray to_ ATHENA, ARTEMIS, _and_\n"
        "APOLLO.\n"
        "  Zeus-Child that knowest not death, to thee I pray,\n"
    )
    out = convert_gutenberg(text, "PLAY", start="THE PLAY", end="NOTES")
    speeches = _parsed(out.text)
    assert [s["speaker_printed"] for s in speeches] == ["CHORUS"]
    assert speeches[0]["text"] == (
        "Unveil thee, thou dread benediction, "
        "Zeus-Child that knowest not death, to thee I pray,"
    )
    assert "They pray to ATHENA, ARTEMIS, and APOLLO." in speeches[0]["shown"]


# B round 3b item 1 (Grok's read of 5f58b39, build/review/
# review-lane-b-r3-grok-findings.md finding 1, 2026-09-18): round 3's rule
# closed a direction at ANY line ending `.`/`!`/`?`, including the first
# wrap line of a real multi-sentence direction whose italics reopen after a
# name and run on to a second sentence (agamemnon.txt:934, and the same
# shape in alcestis, oedipus-tyrannus, hippolytus x10). The first wrap line
# ends its own clause with a stop, but the reopened italics after
# CLYTEMNESTRA are still unbalanced there, so the direction must not close
# until its true end (a literal `]`).
def test_direction_line_closes_stays_open_past_a_stop_with_reopened_italics():
    direction: list[str] = []
    # "[_As they cease,_ CLYTEMNESTRA _comes...Attendants." -- ends its own
    # clause with a stop, but the italics after CLYTEMNESTRA are unbalanced.
    closed, tail = _direction_line_closes(
        direction,
        "[_As they cease,_ CLYTEMNESTRA _comes from the Palace with Attendants.",
        "She has finished her prayer and sacrifice.",
    )
    assert (closed, tail) == (False, "")
    closed, tail = _direction_line_closes(
        direction,
        "She has finished her prayer and sacrifice.",
        "The Leader approaches her_.]",
    )
    assert (closed, tail) == (False, "")
    closed, tail = _direction_line_closes(direction, "The Leader approaches her_.]", None)
    assert (closed, tail) == (True, "")


def test_gutenberg_multi_sentence_direction_survives_a_stop_on_its_first_wrap_line():
    text = (
        "CHARACTERS IN THE PLAY\n\nLEADER.\nHERALD.\n\n\n"
        "THE PLAY\n\n"
        "LEADER.\n"
        "  As good hath dawned, may good shine on, we pray!\n"
        "[_Enter the_ HERALD, _running. His garments are torn and war-stained.\n"
        "He falls upon his knees and kisses the Earth, and salutes each Altar in\n"
        "turn._]\n\n"
        "HERALD.\n"
        "  Land of my fathers! Argos! Am I here.\n"
    )
    out = convert_gutenberg(text, "PLAY", start="THE PLAY", end="NOTES")
    lines = out.text.splitlines()
    assert (
        "_[Enter the HERALD, running. His garments are torn and war-stained. "
        "He falls upon his knees and kisses the Earth, and salutes each Altar in turn.]_"
    ) in lines
    speeches = _parsed(out.text)
    assert [s["speaker_printed"] for s in speeches] == ["LEADER", "HERALD"]
    assert speeches[0]["text"] == "As good hath dawned, may good shine on, we pray!"
    assert speeches[1]["text"] == "Land of my fathers! Argos! Am I here."
    assert "garments" not in speeches[1]["text"]


# Same finding (item 1): round 3's cap on an unclosed direction counted raw
# Gutenberg wrap lines, not stage-business sentences, so a genuine direction
# running past four 70-character lines (iphigenia-in-tauris's procession,
# bacchae's Agave entrance, alcestis's Heracles entrance) was cut and its
# tail printed as verse. With the cap dropped, a direction runs as many raw
# lines as it needs and still closes on its own literal `]`.
def test_gutenberg_direction_runs_past_four_wraps_to_its_own_close():
    text = (
        "CHARACTERS IN THE PLAY\n\nCHORUS.\nTHOAS.\n\n\n"
        "THE PLAY\n\n"
        "CHORUS.\n"
        "  thou canst read my prayer.\n"
        "[The procession passes out, THOAS and the bystanders\n"
        "veiled; Attendants in front, then\n"
        "IPHIGENIA with the Image, then veiled Soldiers,\n"
        "then ORESTES and PYLADES bound,\n"
        "the bonds held by other veiled Soldiers following\n"
        "them. THOAS goes into the Temple.]\n\n"
        "THOAS.\n"
        "  Farewell.\n"
    )
    out = convert_gutenberg(text, "PLAY", start="THE PLAY", end="NOTES")
    lines = out.text.splitlines()
    assert (
        "_[The procession passes out, THOAS and the bystanders veiled; Attendants in "
        "front, then IPHIGENIA with the Image, then veiled Soldiers, then ORESTES and "
        "PYLADES bound, the bonds held by other veiled Soldiers following them. "
        "THOAS goes into the Temple.]_"
    ) in lines
    speeches = _parsed(out.text)
    assert [s["speaker_printed"] for s in speeches] == ["CHORUS", "THOAS"]
    assert speeches[1]["text"] == "Farewell."
    assert "Temple" not in speeches[1]["text"]


# Same finding: the short mid-speech asides this rule already got right
# (trojan-women's "Turning upon the Herald", B round 3 item 1) must keep
# closing at their own single sentence -- the fix for the multi-sentence
# case must not reopen these into run-ons.
def test_gutenberg_short_aside_still_closes_on_its_own_sentence():
    text = (
        "CHARACTERS IN THE PLAY\n\nCASSANDRA.\n\n\n"
        "THE PLAY\n\n"
        "CASSANDRA.\n"
        "  With flesh still clean I give them back to thee,\n"
        "[_Turning upon the Herald._\n"
        "Where lies the galley? Whither shall I tread?\n"
        "See that your watch be set, your sail be spread.\n"
    )
    out = convert_gutenberg(text, "PLAY", start="THE PLAY", end="NOTES")
    lines = out.text.splitlines()
    assert "_[Turning upon the Herald._" in lines
    speeches = _parsed(out.text)
    assert len(speeches) == 1
    assert speeches[0]["speaker_printed"] == "CASSANDRA"
    assert "Where lies the galley" in speeches[0]["text"]
    assert "See that your watch be set" in speeches[0]["text"]
    assert "Turning upon the Herald" not in speeches[0]["text"]


# B round 3 item 2 (rhesus 23-33, 2026-09-17): a cue's parenthetical aside
# can be followed on the same line by a strophe rubric --
# "CHORUS (_various voices confusedly_).      [_Strophe._" -- which the cue
# matcher did not recognise at all, so no turn boundary opened and the whole
# strophe welded into the previous speech.
def test_gutenberg_cue_with_parenthetical_and_trailing_strophe_label():
    text = (
        "CHARACTERS IN THE PLAY\n\nCHORUS.\n\n\n"
        "THE PLAY\n\n"
        "SOME MAN.\n"
        "  Know nothing?\n\n"
        "CHORUS (_various voices confusedly_).      [_Strophe._\n"
        "  To arms! To arms, Lord Hector!\n"
    )
    out = convert_gutenberg(text, "PLAY", start="THE PLAY", end="NOTES")
    speeches = _parsed(out.text)
    assert [s["speaker_printed"] for s in speeches] == ["SOME MAN", "CHORUS"]
    assert speeches[1]["text"] == "To arms! To arms, Lord Hector!"
    assert "Strophe" not in speeches[1]["text"]
    assert "various voices confusedly" in speeches[1]["shown"]


def test_gutenberg_sidenote_marker_is_dropped_between_speeches():
    text = (
        "CHARACTERS IN THE PLAY\n\nOEDIPUS, _King of Thebes_.\n\n\n"
        "THE PLAY\n\n"
        "OEDIPUS.\n"
        "  My children, latest born to Cadmus old.\n"
        "_[Sidenote: vv. 15-39]_\n\n"
        "CREON.\n"
        "  Good news, for e'en intolerable ills.\n"
    )
    out = convert_gutenberg(text, "PLAY", start="THE PLAY", end="NOTES")
    assert "Sidenote" not in out.text
    speeches = _parsed(out.text)
    assert [(s["speaker_printed"], s["text"]) for s in speeches] == [
        ("OEDIPUS", "My children, latest born to Cadmus old."),
        ("CREON", "Good news, for e'en intolerable ills."),
    ]
    assert not speeches[0].get("directions_before")
    assert not speeches[1].get("directions_before")


def test_gutenberg_sidenote_marker_is_dropped_inside_a_speech():
    text = (
        "CHARACTERS IN THE PLAY\n\nCHORUS.\n\n\n"
        "THE PLAY\n\n"
        "CHORUS.\n"
        "  Yield; consent; think! My Lord, I conjure thee!\n"
        "_[Sidenote: vv. 649-664]_\n"
        "  Kneeling I ask it.\n"
    )
    out = convert_gutenberg(text, "PLAY", start="THE PLAY", end="NOTES")
    assert "Sidenote" not in out.text
    speeches = _parsed(out.text)
    assert speeches == [
        {
            "speaker_printed": "CHORUS",
            "text": "Yield; consent; think! My Lord, I conjure thee! Kneeling I ask it.",
        }
    ]


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
    # The strophe label is editorial apparatus, not a stage direction: it
    # must not survive as a rendered direction either (B3, fix-mechanisms
    # brief, 2026-09-17).
    assert "shown" not in speeches[0]


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


def test_iphigenia_in_tauris_patch_replaces_the_missing_page():
    out = convert_play("iphigenia-in-tauris")
    assert "Sending Completed Page" not in out.text
    assert out.text.count("Where is the priest who does this cruelty?") == 1


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
