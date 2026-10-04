import pytest

from drama_pipeline.bench_clean_verse import (
    clean_genie_html,
    clean_play,
    clean_play_prose,
    collapse_spaces,
    expand_prose_speaker,
    locate_play,
    parse_dramatis,
    speaker_from_line,
    write_clean,
    write_clean_genie_html,
)
from drama_pipeline.stage1_turn_english import _split_lindsay_speaker_line, parse_play_speeches


MORSHEAD = """
PREFACE
Some front matter about the trilogy.

THE AGAMEMNON OF AESCHYLUS

DRAMATIS PERSONAE

A Watchman.
Chorus.
Clytemnestra.

The Scene is the Palace of Atreus at Mycenae.

AGAMEMNON

A Watchman

I  PRAY  the  gods  to  quit  me  of  my  toils,
To  close  the  watch  I  keep,  this  livelong  year ;

4

AGAMEMNON

And if at whiles, for the lost balm of sleep,
I medicine my soul with melody
Of trill or song — anon to tears I turn,

[A beacon-light is seen reddening
the distant sky.

Fire of the night, that brings my spirit day,

[Exit. The chorus of old men enter.

AGAMEMNON

5

Chorus

Ten livelong years have rolled away,
Since the twin lords of sceptred sway,

Clytemnestra

As saith the adage, From the womb of Night
Spring forth, with promise fair, the young child Light.

Enter Herald

O land of Argos, fatherland of mine !
To thee at last, beneath the tenth year's sun,

Agamemnon

Then, if thou wilt, let some one stoop to loose
Swiftly these sandals, slaves beneath my foot :

Cassandra

Apollo, Apollo !

Voice of Agamemnon

O I am sped — a deep, a mortal blow.

One of the Chorus

'Tis best, I judge, aloud for aid to call,

Leader of the Chorus

I read one will from many a diverse word,

TEgisthus

This word from thee, this word from one who rows

HiGISTHUS

Lo ! I too am standing ready, hand on hilt for death

THE LIBATION-BEARERS

DRAMATIS PERSONAE

Orestes.
Chorus of Captive Women.

THE LIBATION-BEARERS

Orestes

Lord of the shades and patron of the realm
That erst my father swayed, list now my prayer,
"""


def test_collapse_djvu_spaces():
    assert collapse_spaces("I  PRAY  the  gods") == "I PRAY the gods"


def test_locate_cuts_at_next_play_and_skips_toc():
    lines = MORSHEAD.splitlines()
    start, end = locate_play(lines, "AGAMEMNON")
    body = "\n".join(lines[start:end])
    assert "I  PRAY  the  gods" in body
    assert "Lord of the shades" not in body
    assert "PREFACE" not in body or start > 0


def test_watchman_article_stripped_and_emitted_caps():
    assert speaker_from_line("A Watchman") == "WATCHMAN"
    assert speaker_from_line("The King of Argos") == "KING OF ARGOS"
    assert speaker_from_line("The Herald") == "HERALD"
    assert speaker_from_line("Enter Herald") == "HERALD"


def test_aegisthus_ocr_variants():
    assert speaker_from_line("TEgisthus") == "AEGISTHUS"
    assert speaker_from_line("HiGISTHUS") == "AEGISTHUS"
    assert speaker_from_line("iEGISTHUS") == "AEGISTHUS"
    assert speaker_from_line("^Egisthus") == "AEGISTHUS"
    assert speaker_from_line("jEGISTHUS") == "AEGISTHUS"
    assert speaker_from_line("/Egisthus") == "AEGISTHUS"
    assert speaker_from_line("Voice of ^Egisthus") == "VOICE OF AEGISTHUS"


def test_io_ocr_ell_for_i():
    assert speaker_from_line("lo") == "IO"
    assert speaker_from_line("Id") == "IO"
    assert speaker_from_line("Io") == "IO"
    assert speaker_from_line("IO") is None  # page 10, not the character


def test_ocr_page_numbers_and_signatures_are_dropped():
    from drama_pipeline.bench_clean_verse import _is_page_number, _is_signature

    assert _is_page_number("IIS")
    assert _is_page_number("IOO")
    assert _is_page_number("IOI")
    assert _is_signature("US")
    text, _report = clean_play(
        """
THE SEVEN AGAINST THEBES
DRAMATIS PERSONAE
Eteocles.
The Scene is Thebes.
THE SEVEN AGAINST THEBES
Eteocles
Clansmen of Cadmus, at the signal given
By time and season must the ruler speak.
IIS
Chorus
O woe, O woe, for the city's doom.
""",
        "THE SEVEN AGAINST THEBES",
    )
    assert "\nIIS\n" not in text
    speeches, _notes = parse_play_speeches(
        text, "THE SEVEN AGAINST THEBES", format="verse-own-line"
    )
    assert "IIS" not in [s["speaker_printed"] for s in speeches]


def test_lowercase_verse_wrap_is_not_a_speaker():
    assert speaker_from_line("strength,") is None
    assert speaker_from_line("slave ! —") is None
    assert speaker_from_line("Pylades,") == "PYLADES"


def test_stage_directions_are_not_speakers():
    assert speaker_from_line("[A beacon-light is seen reddening") is None
    assert speaker_from_line("[Exit. The chorus of old men enter.") is None
    assert speaker_from_line("{Enter Atossa.") is None
    assert speaker_from_line("( To Prometheus)") is None
    assert speaker_from_line("{To lo)") is None
    assert speaker_from_line("[Exeunt omnes.") is None


def test_strength_parenthetical_stripped():
    assert speaker_from_line("Strength {To Prometheus)") == "STRENGTH"
    assert speaker_from_line("Slave ( from within)") == "SLAVE"


def test_oceanus_and_prometheus_ocr():
    assert speaker_from_line("Ocean US") == "OCEANUS"
    assert speaker_from_line("Oceaxus") == "OCEANUS"
    assert speaker_from_line("PROiNIETHEUS") == "PROMETHEUS"
    assert speaker_from_line("Prometheu.s") == "PROMETHEUS"
    assert speaker_from_line("Promf:theus") == "PROMETHEUS"


def test_combined_seven_heading():
    assert speaker_from_line("Antigone, Ismkne, and Chorus") == (
        "ANTIGONE ISMENE AND CHORUS"
    )


def test_clean_play_drops_heads_pages_stage_keeps_verse():
    text, report = clean_play(MORSHEAD, "AGAMEMNON")
    assert text.splitlines()[0] == "AGAMEMNON"
    assert report["speakers_found"][0] == "WATCHMAN"
    assert report["speakers_found"][1] == "CHORUS"
    assert "WATCHMAN" in report["speakers_found"]
    assert "CHORUS" in report["speakers_found"]
    assert "CLYTEMNESTRA" in report["speakers_found"]
    assert "HERALD" in report["speakers_found"]
    assert "AGAMEMNON" in report["speakers_found"]
    assert "CASSANDRA" in report["speakers_found"]
    assert "VOICE OF AGAMEMNON" in report["speakers_found"]
    assert "ONE OF THE CHORUS" in report["speakers_found"]
    assert "LEADER OF THE CHORUS" in report["speakers_found"]
    assert "AEGISTHUS" in report["speakers_found"]
    assert "I PRAY the gods to quit me of my toils," in text
    assert "Ten livelong years have rolled away," in text
    assert "O land of Argos, fatherland of mine !" in text
    assert "PREFACE" not in text
    assert "DRAMATIS" not in text
    assert "beacon-light" not in text
    assert "\n4\n" not in text
    # Running-head AGAMEMNON (all caps, between verse) is dropped;
    # the character remains as a speaker event.
    assert "Lord of the shades" not in text
    speeches, notes = parse_play_speeches(text, "AGAMEMNON", format="verse-own-line")
    assert notes == {}
    printed = [s["speaker_printed"] for s in speeches]
    assert printed[0] == "WATCHMAN"
    assert "HERALD" in printed
    assert "AEGISTHUS" in printed
    assert not any(name.startswith("THE ") for name in printed)


def test_hyphen_rejoin_across_page_break():
    text, _report = clean_play(
        """
AGAMEMNON
DRAMATIS PERSONAE
A Watchman.
AGAMEMNON
A Watchman
I medicine my soul with mel-
ody of trill or song.
Chorus
Ten livelong years have rolled away,
""",
        "AGAMEMNON",
    )
    assert "melody of trill or song." in text
    assert "mel-\nody" not in text


def test_appendix_stops_play():
    text, _report = clean_play(
        """
THE LIBATION-BEARERS
DRAMATIS PERSONAE
Orestes.
THE LIBATION-BEARERS
Orestes
Lord of the shades and patron of the realm
That erst my father swayed.
Chorus
Most loyal of all sons unto thy sire,
APPENDIX
A note about corruptions in the Greek text of this play.
THE FURIES
DRAMATIS PERSONAE
The Pythian Priestess.
""",
        "THE LIBATION-BEARERS",
    )
    assert "Lord of the shades" in text
    assert "corruptions in the Greek" not in text
    assert "Pythian" not in text


def test_skips_dramatis_and_scene_before_body():
    text, report = clean_play(
        """
THE PERSIANS
ARGUMENT
Xerxes went forth against Hellas.
DRAMATIS PERSONAE
Chorus of Persian Elders.
Atossa, Widow of Darius and Mother of Xerxes.
A Messenger.
The Scene is laid at the Palace of Susa.
THE PERSIANS
Chorus
Away unto the Grecian land
Hath passed the Persian armament :
Atossa
Therefore come I forth to you, from chambers decked
""",
        "THE PERSIANS",
    )
    assert report["speakers_found"][0] == "CHORUS"
    assert "CHORUS OF PERSIAN ELDERS" not in report["speakers_found"]
    assert "Widow of Darius" not in text
    assert "Away unto the Grecian land" in text


def test_wrapped_stage_direction_is_dropped():
    text, report = clean_play(
        """
THE LIBATION-BEARERS
DRAMATIS PERSONAE
Orestes.
The Scene is the Tomb of Agamemnon.
THE LIBATION-BEARERS
Orestes
Lord of the shades and patron of the realm
That erst my father swayed, list now my prayer.
[Exeunt Pylades and Orestes ; enter the Chorus
bearing vessels for libation ; they pace slowly
towards the tomb of
Agamemnon.

Chorus
Forth from the royal halls by high command
I bear libations for the dead.
""",
        "THE LIBATION-BEARERS",
    )
    assert "AGAMEMNON" not in report["speakers_found"]
    assert "tomb of" not in text
    assert "Forth from the royal halls" in text


def test_footnote_lines_dropped():
    text, _report = clean_play(
        """
AGAMEMNON
DRAMATIS PERSONAE
Chorus.
AGAMEMNON
Chorus
Unsoothed by tears or spilth of wine
Poured forth too late, the wrath divine.
1 The flameless shrine appears to be a metaphor for
an altar without fire.
Clytemnestra
Hear then again, and plainly — Troy is ours !
""",
        "AGAMEMNON",
    )
    assert "flameless shrine appears" not in text
    assert "Troy is ours" in text


def test_verse_own_line_format_without_persons_heading():
    text = """AGAMEMNON

WATCHMAN
I pray the gods to quit me of my toils,
To close the watch I keep, this livelong year.

CHORUS
Ten livelong years have rolled away,
Since the twin lords of sceptred sway.
"""
    speeches, notes = parse_play_speeches(text, "AGAMEMNON", format="verse-own-line")
    assert notes == {}
    assert [s["speaker_printed"] for s in speeches] == ["WATCHMAN", "CHORUS"]
    assert speeches[0]["text"].startswith("I pray the gods")
    assert "Ten livelong years" in speeches[1]["text"]


def test_write_clean_real_agamemnon(tmp_path):
    from drama_pipeline.config import REPO_ROOT

    volume = REPO_ROOT / "sources/archive-org/houseofatreusbei00aesc.txt"
    dest, report = write_clean(
        volume, "morshead", "agamemnon", "AGAMEMNON", out_dir=tmp_path
    )
    text = dest.read_text(encoding="utf-8")
    assert text.splitlines()[0] == "AGAMEMNON"
    for name in (
        "WATCHMAN",
        "CHORUS",
        "CLYTEMNESTRA",
        "HERALD",
        "AGAMEMNON",
        "CASSANDRA",
        "AEGISTHUS",
    ):
        assert name in report["speakers_found"], report["speakers_found"]
    assert report["lines_kept"] > 200
    assert "I PRAY the gods" in text or "I pray the gods" in text.lower()
    speeches, _notes = parse_play_speeches(text, "AGAMEMNON", format="verse-own-line")
    assert speeches[0]["speaker_printed"] == "WATCHMAN"
    assert len(speeches) > 40


HICKIE = """
THE ACHARNIANS.

DRAMATIS PERSONÆ.

DICÆOPOLIS.
HERALD.
AMPHITHEUS.
CHORUS OF ACHARNIANS.
EURIPIDES.

Scene.—The Pnyx.

THE ARGUMENT.

This Comedy takes its name from the natives of Acharnae, who
constitute the Chorus. It was brought out in January.

THE ACHARNIANS.

Dicæopolis (solus).

How many things truly have I been vexed at in my heart;
and with how few have I been pleased.

4 THE ACHARNIANS. 27—55.

Her. Advance to the front; advance, that ye may be
within the consecrated line.

Amp. Has any one spoken yet?

' See Kruger's Greek Gram. § 69.

Dic. Mr. Prytanes, you wrong the assembly in order-
ing the peace to be discussed.

Cuo. We will never hearken to you.

END OF THE ACHARNIANS.

THE KNIGHTS.

DRAMATIS PERSONÆ.

DEMOS.
SAUSAGE-SELLER.
"""


def test_prose_inline_expands_dramatis_abbreviations():
    names = parse_dramatis(HICKIE.splitlines(), "THE ACHARNIANS")
    assert "DICAEOPOLIS" in names
    assert "HERALD" in names
    from drama_pipeline.bench_clean_verse import _abbr_table

    table = _abbr_table(names)
    assert expand_prose_speaker("Dic", names, table) == "DICAEOPOLIS"
    assert expand_prose_speaker("Her", names, table) == "HERALD"
    assert expand_prose_speaker("Amp", names, table) == "AMPHITHEUS"
    assert expand_prose_speaker("Cuo", names, table) == "CHORUS OF ACHARNIANS"


def test_prose_inline_chorus_or_men_women():
    names = [
        "LYSISTRATA",
        "CALONICE",
        "CHORUS OF OLD MEN",
        "CHORUS OF OLD WOMEN",
    ]
    from drama_pipeline.bench_clean_verse import _abbr_table

    table = _abbr_table(names)
    assert expand_prose_speaker("Cuo", names, table, which="Men") == "CHORUS OF OLD MEN"
    assert expand_prose_speaker("CHo", names, table, which="Wom") == "CHORUS OF OLD WOMEN"
    assert expand_prose_speaker("Caton", names, table) == "CALONICE"


def test_prose_inline_emits_gutenberg_name_dot_text():
    cleaned, report = clean_play_prose(HICKIE, "THE ACHARNIANS", next_title="THE KNIGHTS")
    assert cleaned.splitlines()[0] == "THE ACHARNIANS"
    assert "This Comedy takes its name" not in cleaned
    assert "See Kruger" not in cleaned
    assert "27—55" not in cleaned
    assert "SAUSAGE-SELLER" not in cleaned
    speeches, notes = parse_play_speeches(cleaned, "THE ACHARNIANS")
    assert notes == {}
    printed = [s["speaker_printed"] for s in speeches]
    assert printed[0] == "DICAEOPOLIS"
    assert "HERALD" in printed
    assert "AMPHITHEUS" in printed
    assert "CHORUS" in printed
    assert "ordering the peace" in " ".join(s["text"] for s in speeches)
    assert report["speaker_events"] >= 4


def test_prose_inline_dramatis_strips_descriptions():
    text = """
THE KNIGHTS.

DRAMATIS PERSON.

DEMUS, an old citizen of Athens.
DEMOSTHENES, i
NICIAS, Slaves of Demus.
SAUSAGE-SELLER (afterwards Agoracritus).
CHORUS OF KNIGHTS.

THE ARGUMENT.

A plot summary that must not become a speaker name.

THE KNIGHTS.

Dem. Alas! alas! for our misfortunes, alas!
Nic. Miserable, like you.
Sau. I will sell sausages in the agora.
Cuo. Strike the villain, and troubler of the Knights.
END OF THE KNIGHTS.

THE CLOUDS.

DRAMATIS PERSON.

STREPSIADES.
"""
    names = parse_dramatis(text.splitlines(), "THE KNIGHTS")
    assert "DEMUS" in names
    assert "DEMOSTHENES" in names
    assert "NICIAS" in names
    assert "SAUSAGE SELLER" in names
    assert "AGORACRITUS" in names
    assert all("OLD CITIZEN" not in n for n in names)
    cleaned, report = clean_play_prose(text, "THE KNIGHTS", next_title="THE CLOUDS")
    speeches, _notes = parse_play_speeches(cleaned, "THE KNIGHTS")
    printed = [s["speaker_printed"] for s in speeches]
    assert printed[0] == "DEMOSTHENES"
    assert "NICIAS" in printed
    assert "SAUSAGE SELLER" in printed
    assert "CHORUS" in printed
    assert "STREPSIADES" not in printed


def test_prose_inline_sausage_seller_ss_and_demus():
    text = """
THE KNIGHTS.

DRAMATIS PERSON.

DEMUS.
DEMOSTHENES.
SAUSAGE-SELLER.
CHORUS OF KNIGHTS.

THE ARGUMENT.

Plot.

THE KNIGHTS.

Dem. Alas for our misfortunes.
S. S. O father, by Jupiter, pray come forth.
Deuvs.
Dem. Who are those that are bawling?
END OF THE KNIGHTS.

THE CLOUDS.

DRAMATIS PERSON.

STREPSIADES.
"""
    cleaned, report = clean_play_prose(text, "THE KNIGHTS", next_title="THE CLOUDS")
    speeches, _notes = parse_play_speeches(cleaned, "THE KNIGHTS")
    printed = [s["speaker_printed"] for s in speeches]
    assert "SAUSAGE SELLER" in printed
    assert "DEMUS" in printed
    assert printed[-1] == "DEMUS"


def test_prose_inline_play_title_character_stays_in_dramatis():
    text = """
LYSISTRATA.

DRAMATIS PERSONE.

LYSISTRATA.
CALONICE.
CHORUS OF OLD MEN.
CHORUS OF OLD WOMEN.

THE ARGUMENT.

A plot.

LYSISTRATA.

Lys. Well! if one had summoned them to the temple of
Bacchus, it would not even have been possible to pass.
Caton. And you too, Lysistrata! Why are you troubled?
Cuo. or Men. This affair has come unexpected for us.
CHo. or Wom. Why do you insult us?
END OF THE LYSISTRATA.

THE THESMOPHORIAZUSAE.

DRAMATIS PERSON Z.

MNESILOCHUS.
"""
    names = parse_dramatis(text.splitlines(), "LYSISTRATA")
    assert "LYSISTRATA" in names
    assert "CALONICE" in names
    cleaned, report = clean_play_prose(
        text, "LYSISTRATA", next_title="THE THESMOPHORIAZUSAE"
    )
    speeches, _notes = parse_play_speeches(cleaned, "LYSISTRATA")
    printed = [s["speaker_printed"] for s in speeches]
    assert printed[0] == "LYSISTRATA"
    assert "CALONICE" in printed
    assert "CHORUS OF OLD MEN" in printed
    assert "CHORUS OF OLD WOMEN" in printed


def test_prose_inline_write_clean(tmp_path):
    src = tmp_path / "vol.txt"
    src.write_text(HICKIE, encoding="utf-8")
    dest, report = write_clean(
        src,
        "hickie",
        "acharnians",
        "THE ACHARNIANS",
        next_title="THE KNIGHTS",
        out_dir=tmp_path,
        layout="prose-inline",
    )
    text = dest.read_text(encoding="utf-8")
    assert text.startswith("THE ACHARNIANS")
    assert "DICAEOPOLIS." in text
    assert report["speakers_found"][0] == "DICAEOPOLIS"


# Genie OCR HTML (Arrowsmith): paragraph index 0 is <p class="p1">THE PLAY</p>,
# so "SCENE:" is index 3 and the fully-italic "That's it." aside is index 8.
GENIE_HTML = """
<p class="p1">THE PLAY</p>
<p class="p1"><i>Characters of the Play</i></p>
<p class="p1">SPEAKERONE, a fellow</p>
<p class="p1">SCENE: <i>A street.</i></p>
<p class="p1">SPEAKERONE</p>
<p class="p1">Line one, with <i>real</i> emphasis and a note.*</p>
<p class="p1"><i>Turning to go.</i></p>
<p class="p1">SPEAKERTWO</p>
<p class="p1"><i>That's it.</i></p>
<p class="p1">$\\qquad\\qquad$ Right you are.</p>
<p class="p1">\xa0\xa0\xa0\xa0trailing half of the line.</p>
<p class="p1">11</p>
<p class="p1">Aristophanes, and William Arrowsmith. <i>The Play</i>.</p>
<p class="p1">E-book, Ann Arbor, MI: University of Michigan Press, 1962.</p>
<p class="p1">Downloaded on behalf of Unknown Institution</p>
<p class="p1">---</p>
<p class="p1">SPEAKERONE</p>
<p class="p1">Final line.</p>
<p class="p1"><i>Notes</i></p>
<p class="p1"><i>page</i> 11. Some annotation.</p>
"""


def test_genie_html_marks_stage_directions_keeps_overrides():
    # John, 2026-09-12: keep Arrowsmith's stage directions, each on its own
    # `_..._` line where he prints it, so the parser can tell them from speech.
    speakers = frozenset({"SPEAKERONE", "SPEAKERTWO"})
    cleaned, report = clean_genie_html(
        GENIE_HTML, "THE PLAY", speakers, dialogue_overrides=frozenset({8})
    )
    assert cleaned.startswith("THE PLAY\n\n")
    lines = cleaned.splitlines()
    assert lines.index("_Turning to go._") == lines.index("Line one, with real emphasis and a note.") + 1
    assert "That's it." in lines  # overridden: dialogue, not narration
    assert "note." in cleaned and "*" not in cleaned  # footnote asterisk stripped
    assert "$" not in cleaned and "qquad" not in cleaned  # LaTeX indent stripped
    assert "Right you are." in cleaned
    assert "trailing half of the line." in cleaned  # nbsp indent stripped
    assert "Aristophanes, and William Arrowsmith" not in cleaned  # footer stripped
    assert "11" not in cleaned.splitlines()  # page number stripped
    assert "Some annotation" not in cleaned  # Notes end matter excluded
    assert report["stage_directions_kept"] == 1
    assert report["dialogue_overrides_used"] == 1
    assert report["speakers_found"] == ["SPEAKERONE", "SPEAKERTWO"]


def test_genie_html_folds_shouted_caps_line_so_it_is_not_read_as_a_speaker():
    # A bare all-caps line with no punctuation (Arrowsmith shouts a phrase
    # in caps for emphasis) is exactly what the shared verse-own-line reader
    # takes for a speaker cue; the cleaner must fold it into a neighbouring
    # line rather than emit it standalone.
    html = """
<p class="p1">THE PLAY</p>
<p class="p1"><i>Characters of the Play</i></p>
<p class="p1">SCENE: <i>A street.</i></p>
<p class="p1">SPEAKERONE</p>
<p class="p1">Gentlemen, hear this:</p>
<p class="p1">YOUR ATTENTION</p>
<p class="p1">PLEASE.</p>
<p class="p1">That is all.</p>
<p class="p1"><i>Notes</i></p>
"""
    speakers = frozenset({"SPEAKERONE"})
    cleaned, _report = clean_genie_html(html, "THE PLAY", speakers)
    lines = [ln for ln in cleaned.splitlines() if ln]
    assert lines == [
        "THE PLAY",
        "SPEAKERONE",
        "Gentlemen, hear this: YOUR ATTENTION PLEASE.",
        "That is all.",
    ]
    speeches, _notes = parse_play_speeches(cleaned, "THE PLAY", format="verse-own-line")
    assert [s["speaker_printed"] for s in speeches] == ["SPEAKERONE"]


def test_genie_html_speaker_relabels_by_occurrence():
    # Arrowsmith reuses one printed label for two Greek roles a manifest
    # tells apart only by occurrence (Birds' "MESSENGER" cue covers First
    # Messenger, the Herald, and a plain Messenger); the cleaner must retag
    # the chosen occurrences without touching the roster check itself.
    html = """
<p class="p1">THE PLAY</p>
<p class="p1"><i>Characters of the Play</i></p>
<p class="p1">SCENE: <i>A street.</i></p>
<p class="p1">MESSENGER</p>
<p class="p1">First report.</p>
<p class="p1">MESSENGER</p>
<p class="p1">Second report.</p>
<p class="p1"><i>Notes</i></p>
"""
    speakers = frozenset({"MESSENGER"})
    cleaned, report = clean_genie_html(
        html, "THE PLAY", speakers, speaker_relabels={5: "HERALD"}
    )
    lines = [ln for ln in cleaned.splitlines() if ln]
    assert lines == ["THE PLAY", "MESSENGER", "First report.", "HERALD", "Second report."]
    assert report["speakers_found"] == ["MESSENGER", "HERALD"]


def test_genie_html_without_override_marks_ambiguous_line_as_direction():
    speakers = frozenset({"SPEAKERONE", "SPEAKERTWO"})
    cleaned, report = clean_genie_html(GENIE_HTML, "THE PLAY", speakers)
    assert "That's it." not in cleaned.splitlines()
    assert "_That's it._" in cleaned.splitlines()
    assert report["stage_directions_kept"] == 2
    assert report["dialogue_overrides_used"] == 0


def test_genie_html_strips_note_mark_before_matching_speaker_cue():
    # Codex review finding 1 (2026-09-11): a speaker cue carrying a footnote
    # asterisk (`CHORUS*`) is not `in speakers` verbatim, so name matching
    # missed it and it fell through to become dialogue under the previous
    # speaker instead of opening its own speech.
    html = """
<p class="p1">THE PLAY</p>
<p class="p1"><i>Characters of the Play</i></p>
<p class="p1">SCENE: <i>A street.</i></p>
<p class="p1">SPEAKERONE</p>
<p class="p1">First line.</p>
<p class="p1">CHORUS*</p>
<p class="p1">Second line.</p>
<p class="p1"><i>Notes</i></p>
"""
    speakers = frozenset({"SPEAKERONE", "CHORUS"})
    cleaned, _report = clean_genie_html(html, "THE PLAY", speakers)
    lines = [ln for ln in cleaned.splitlines() if ln]
    assert lines == ["THE PLAY", "SPEAKERONE", "First line.", "CHORUS", "Second line."]
    speeches, _notes = parse_play_speeches(cleaned, "THE PLAY", format="verse-own-line")
    assert [s["speaker_printed"] for s in speeches] == ["SPEAKERONE", "CHORUS"]


def test_genie_html_strips_hspace_prefix_before_matching_speaker_cue():
    # Codex re-review finding 2 (2026-09-11): Clouds' printed-rhetoric scene
    # (genie-clouds.html ~2697-2724) indents lines with `$\hspace{Nem}$`
    # rather than `$\qquad...$`, which the old regex did not cover. Left
    # in place, `$\hspace{4em}$ SOKRATES` is not `in speakers` verbatim, so
    # the cue falls through as raw dialogue -- hiding both the speaker
    # change and the six turns that follow, and shifting the third column
    # (Greek 1105-1130 got no English; 1:1131 got the speech for 1105-1106;
    # 1:1150 showed the raw spacing command as if it were dialogue).
    html = """
<p class="p1">THE PLAY</p>
<p class="p1"><i>Characters of the Play</i></p>
<p class="p1">SCENE: <i>A street.</i></p>
<p class="p1">SPEAKERONE</p>
<p class="p1">$\\hspace{18em}$ Well, let them.</p>
<p class="p1">$\\hspace{4em}$ SPEAKERTWO</p>
<p class="p1">$\\hspace{13em}$ Ah, greetings.</p>
<p class="p1"><i>Notes</i></p>
"""
    speakers = frozenset({"SPEAKERONE", "SPEAKERTWO"})
    cleaned, _report = clean_genie_html(html, "THE PLAY", speakers)
    assert "\\hspace" not in cleaned and "$" not in cleaned
    lines = [ln for ln in cleaned.splitlines() if ln]
    assert lines == [
        "THE PLAY",
        "SPEAKERONE",
        "Well, let them.",
        "SPEAKERTWO",
        "Ah, greetings.",
    ]
    speeches, _notes = parse_play_speeches(cleaned, "THE PLAY", format="verse-own-line")
    assert [s["speaker_printed"] for s in speeches] == ["SPEAKERONE", "SPEAKERTWO"]


def test_genie_html_drops_footer_ocr_variants():
    # Codex review finding 4 (2026-09-11): the footer check only matched an
    # exact prefix, so OCR variants (no comma, a stray page number inserted
    # mid-line, an "Edited by" recasting) survived as dialogue.
    html = """
<p class="p1">THE PLAY</p>
<p class="p1"><i>Characters of the Play</i></p>
<p class="p1">SCENE: <i>A street.</i></p>
<p class="p1">SPEAKERONE</p>
<p class="p1">First line.</p>
<p class="p1">Aristophanes and William Arrowsmith. <i>The Play</i>.</p>
<p class="p1">Aristophanes, 34 William Arrowsmith. <i>The Play</i>.</p>
<p class="p1">Aristophanes, The Play. Edited by William Arrowsmith. The Play.</p>
<p class="p1">E-book, Ann Arbor, MI: University of Michigan Press, 1962.</p>
<p class="p1">Second line.</p>
<p class="p1"><i>Notes</i></p>
"""
    speakers = frozenset({"SPEAKERONE"})
    cleaned, _report = clean_genie_html(html, "THE PLAY", speakers)
    assert "Arrowsmith" not in cleaned
    assert "Ann Arbor" not in cleaned
    lines = [ln for ln in cleaned.splitlines() if ln]
    assert lines == ["THE PLAY", "SPEAKERONE", "First line.", "Second line."]


def test_genie_html_drops_stage_direction_split_across_partial_italics():
    # Codex review finding 3 (2026-09-11): a stage direction whose italics
    # cover only part of the paragraph ("Exit ... From the other side
    # enters ...," dressed in a magnificent uniform.) is not fully italic,
    # so the default "fully-italic paragraphs only" rule keeps it as
    # dialogue. `stage_direction_overrides` force-drops the whole paragraph
    # by index regardless of how much of it is marked up in italics.
    html = """
<p class="p1">THE PLAY</p>
<p class="p1"><i>Characters of the Play</i></p>
<p class="p1">SCENE: <i>A street.</i></p>
<p class="p1">SPEAKERONE</p>
<p class="p1">First line.</p>
<p class="p1"><i>Exit Speakerone. From the other side enters an Inspector,</i> dressed in a magnificent uniform.</p>
<p class="p1">Second line.</p>
<p class="p1"><i>Notes</i></p>
"""
    speakers = frozenset({"SPEAKERONE"})
    cleaned, report = clean_genie_html(
        html, "THE PLAY", speakers, stage_direction_overrides=frozenset({5})
    )
    lines = [ln for ln in cleaned.splitlines() if ln]
    assert lines == [
        "THE PLAY",
        "SPEAKERONE",
        "First line.",
        "_Exit Speakerone. From the other side enters an Inspector, dressed in a magnificent uniform._",
        "Second line.",
    ]
    assert report["stage_directions_kept"] == 1


def test_genie_html_fully_italic_ignores_a_trailing_note_mark():
    # Codex review finding 3 (2026-09-11), the other half: a note mark
    # sitting just OUTSIDE the italic span ("<i>In the high tragic
    # manner.</i>*") makes the paragraph fail the "fully italic" test by a
    # single stray "*", so the stage direction survives as dialogue.
    html = """
<p class="p1">THE PLAY</p>
<p class="p1"><i>Characters of the Play</i></p>
<p class="p1">SCENE: <i>A street.</i></p>
<p class="p1">SPEAKERONE</p>
<p class="p1">First line.</p>
<p class="p1"><i>In the high tragic manner.</i>*</p>
<p class="p1">Second line.</p>
<p class="p1"><i>Notes</i></p>
"""
    speakers = frozenset({"SPEAKERONE"})
    cleaned, report = clean_genie_html(html, "THE PLAY", speakers)
    lines = [ln for ln in cleaned.splitlines() if ln]
    assert lines == ["THE PLAY", "SPEAKERONE", "First line.", "_In the high tragic manner._", "Second line."]
    assert report["stage_directions_kept"] == 1


def test_genie_html_direction_does_not_change_how_a_caps_line_folds():
    # A shouted caps line still folds into the verse before it when a stage
    # direction sits between them, so the speech text is what it was when
    # directions were dropped; the direction follows the joined line.
    html = """
<p class="p1">THE PLAY</p>
<p class="p1"><i>Characters of the Play</i></p>
<p class="p1">SCENE: <i>A street.</i></p>
<p class="p1">SPEAKERONE</p>
<p class="p1">Gentlemen, hear this:</p>
<p class="p1"><i>He shouts.</i></p>
<p class="p1">YOUR ATTENTION</p>
<p class="p1">That is all.</p>
<p class="p1"><i>Notes</i></p>
"""
    cleaned, _report = clean_genie_html(html, "THE PLAY", frozenset({"SPEAKERONE"}))
    lines = [ln for ln in cleaned.splitlines() if ln]
    assert lines == [
        "THE PLAY",
        "SPEAKERONE",
        "Gentlemen, hear this: YOUR ATTENTION",
        "_He shouts._",
        "That is all.",
    ]


# What the cleaner dropped as stage direction before 2026-09-12 (its own
# `stage_directions_dropped` report on build/arrowsmith/genie-*.html): the
# sung-dialogue overrides are already out of these counts.
ARROWSMITH_DIRECTIONS_DROPPED = {"clouds": 212, "birds": 149}


def test_real_arrowsmith_files_keep_every_stage_direction():
    from drama_pipeline.config import REPO_ROOT
    import drama_pipeline.bench_clean_verse as bcv

    if not all(
        (REPO_ROOT / "build" / "arrowsmith" / f"genie-{play}.html").exists()
        for play in ("clouds", "birds")
    ):
        pytest.skip("Arrowsmith's Genie HTML is a machine-local build/ scratch file, not vendored")
    for play, title in (("clouds", "THE CLOUDS"), ("birds", "THE BIRDS")):
        html = (REPO_ROOT / "build" / "arrowsmith" / f"genie-{play}.html").read_text(
            encoding="utf-8", errors="replace"
        )
        cleaned, report = clean_genie_html(
            html,
            title,
            bcv.GENIE_ROSTERS[play],
            dialogue_overrides=bcv.GENIE_DIALOGUE_OVERRIDES.get(play, frozenset()),
            speaker_relabels=bcv.GENIE_SPEAKER_RELABELS.get(play, {}),
            stage_direction_overrides=bcv.GENIE_STAGE_DIRECTION_OVERRIDES.get(play, frozenset()),
        )
        text = (REPO_ROOT / "sources" / "bench" / "arrowsmith" / f"{play}.txt").read_text(
            encoding="utf-8"
        )
        assert cleaned == text, f"{play}: cleaned file does not reproduce"
        marked = [ln for ln in text.splitlines() if ln.startswith("_") and ln.endswith("_")]
        assert len(marked) == report["stage_directions_kept"] == ARROWSMITH_DIRECTIONS_DROPPED[play]


def test_clean_genie_html_real_clouds_keeps_the_mocking_songs_2814_line():
    # Codex review finding 2 (2026-09-11): the Clouds override review
    # missed paragraph 2814 -- a single sung dialogue line ("He went to
    # school with Sokrates") inside the run 2812-2821, the Chorus's mocking
    # song -- so it dropped as an unreviewed stage direction. A gap in an
    # otherwise-contiguous override run is exactly the shape of the miss.
    from drama_pipeline.config import REPO_ROOT
    import drama_pipeline.bench_clean_verse as bcv

    html_path = REPO_ROOT / "build" / "arrowsmith" / "genie-clouds.html"
    if not html_path.exists():
        pytest.skip("Arrowsmith's Genie HTML is a machine-local build/ scratch file, not vendored")
    html_text = html_path.read_text(encoding="utf-8")
    cleaned, _report = clean_genie_html(
        html_text,
        "THE CLOUDS",
        bcv.GENIE_ROSTERS["clouds"],
        dialogue_overrides=bcv.GENIE_DIALOGUE_OVERRIDES["clouds"],
        speaker_relabels=bcv.GENIE_SPEAKER_RELABELS.get("clouds", {}),
    )
    assert "He went to school with Sokrates" in cleaned


def test_real_arrowsmith_files_every_speaker_cue_becomes_a_speech():
    # The coverage check finding 6 was missing: `_body_start` can lock onto
    # a LATER speaker cue and silently drop every genuine speech before it
    # (six of them, in Clouds), with no count anywhere catching the loss.
    # A speaker cue in the cleaned file (own-line, matched the same way the
    # parser matches one) must equal the number of speeches the parser
    # actually returns -- any gap means some cue's speech never made it in.
    from drama_pipeline.config import REPO_ROOT

    for play, title in (("clouds", "THE CLOUDS"), ("birds", "THE BIRDS")):
        text = (REPO_ROOT / "sources" / "bench" / "arrowsmith" / f"{play}.txt").read_text(
            encoding="utf-8"
        )
        cue_count = sum(
            1 for line in text.splitlines() if _split_lindsay_speaker_line(line) is not None
        )
        speeches, _notes = parse_play_speeches(text, title, format="verse-own-line")
        assert len(speeches) == cue_count, f"{play}: {len(speeches)} speeches, {cue_count} cues"


def test_write_clean_genie_html(tmp_path):
    html_path = tmp_path / "genie-play.html"
    html_path.write_text(GENIE_HTML, encoding="utf-8")
    import drama_pipeline.bench_clean_verse as bcv

    bcv.GENIE_ROSTERS["play"] = frozenset({"SPEAKERONE", "SPEAKERTWO"})
    bcv.GENIE_DIALOGUE_OVERRIDES["play"] = frozenset({8})
    dest, report = write_clean_genie_html(
        html_path, "arrowsmith", "play", "THE PLAY", out_dir=tmp_path
    )
    text = dest.read_text(encoding="utf-8")
    assert text.startswith("THE PLAY")
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="verse-own-line")
    printed = [s["speaker_printed"] for s in speeches]
    assert printed == ["SPEAKERONE", "SPEAKERTWO", "SPEAKERONE"]
