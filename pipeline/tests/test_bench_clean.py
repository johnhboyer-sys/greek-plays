from drama_pipeline.bench_clean import (
    _is_greek_running_head,
    _speaker_candidate,
    clean_play,
    greek_ratio,
    locate_play,
    normalize_speakers,
    rejoin_hyphens,
    _strip_trailing_linenum,
    write_clean,
)


LOEB = """
OEDIPUS THE KING
OEDIPUS AT COLONUS
ANTIGONE

LONDON: WILLIAM HEINEMANN

ARGUMENT

Oedipus at Colonus comes here in the volume.

DRAMATIS PERSONAE

OEDIPUS, banished King of Thebes.

OEDIPUS AT COLONUS

OEDIPUS
Child of an old blind sire, Antigone,
What region, say, whose city have we reached?

-ANTIGONE

ARGUMENT

ANTIGONE, daughter of Oedipus, the late king of
Thebes, in defiance of Creon who rules in his stead,
resolves to bury her brother Polyneices.

DRAMATIS PERSONAE

ISMENE and Antigone.
Creon, King of Thebes.
A WarTcHmaNn.
A SECOND MESSENGER,

ANTITONH
Ὦ κοινὸν αὐτάδελφον Ἰσμήνης κάρα,
ap οἶσθ᾽ ὅ τι Ζεὺς τῶν ἀπ᾽ Οἰδίπου κακῶν
ὁποῖον οὐχὶ νῷν ἔτι ζώσαιν τελεῖ;
315

ANTIGONE

ANTIGONE
Ismene, sister of my blood and heart,
See'st thou how Zeus would in our lives ful-
fil the weird of Oedipus, a world of woes!
318

ANTITONH
ἐμοὶ μὲν οὐδεὶς μῦθος, Ἀντιγόνη, φίλων
οὔθ᾽ ἡδὺς οὔτ᾽ ἀλγεινὸς ἵκετ᾽ ἐξ ὅτου
319

ANTIGONE

ISMENE
To me, Antigone, no word of friends
Has come, or glad or grievous.
| GUARD
My lord, I will not say
CHORUS (Str. 1)
Sunbeam, of all that ever dawned upon
(Ant. 1)
Hovering around our city walls he waits,
CREON.
Sirrah, begone whither thou wilt.
EURYDICE.
Ye men of Thebes, I overheard your talk.
SECOND MESSENGER
Sorrows are thine, my lord, and more to come,
END OF VOL. I.
"""


def test_greek_ratio_flags_greek_page():
    assert greek_ratio("Ismene, sister of my blood") < 0.1
    assert greek_ratio("Ὦ κοινὸν αὐτάδελφον Ἰσμήνης κάρα") > 0.3


def test_ajax_greek_running_head_ocr_splits_facing_pages():
    assert _is_greek_running_head("ALAS")


def test_locate_play_skips_toc_and_stops_at_end_of_vol():
    lines = LOEB.splitlines()
    start, end = locate_play(lines, "ANTIGONE")
    assert "ARGUMENT" in lines[start + 1 : start + 20]
    body = "\n".join(lines[start:end])
    assert "Child of an old blind sire" not in body
    assert "END OF VOL" in body


def test_locate_play_does_not_take_running_head_before_next_argument():
    lines = """
AJAX
ARGUMENT
Ajax begins here.
AJAX
The last English page.
ELECTRA
ARGUMENT
Electra begins here.
""".splitlines()
    start, end = locate_play(lines, "AJAX")
    assert lines[start] == "AJAX"
    assert "Ajax begins here." in lines[start:end]
    assert "Electra begins here." not in lines[start:end]


def test_locate_play_accepts_first_running_head_after_cast_when_title_page_is_missing():
    lines = """
ARGUMENT
The argument.
DRAMATIS PERSONAE
Oedipus, an exile.
OEDIPUS AT COLONUS
OEDIPUS
Child of an old blind sire.
ANTIGONE
ARGUMENT
The next play.
""".splitlines()
    start, end = locate_play(lines, "OEDIPUS AT COLONUS")
    assert lines[start] == "OEDIPUS AT COLONUS"
    assert "Child of an old blind sire." in lines[start:end]
    assert "The next play." not in lines[start:end]


def test_hyphen_rejoin():
    assert rejoin_hyphens(["ful-", "fil the weird", "next"]) == [
        "fulfil the weird",
        "next",
    ]


def test_ocr_split_speaker_names_are_repaired():
    assert _speaker_candidate("TECMESS A") == ("TECMESSA", "")
    assert _speaker_candidate("CLY TEMNESTRA") == ("CLYTEMNESTRA", "")
    assert _speaker_candidate("HER ACLES") == ("HERACLES", "")
    assert _speaker_candidate("AGED SFRVANT") == ("AGED SERVANT", "")
    assert _speaker_candidate("DRFIANIRA") == ("DEIANIRA", "")
    assert _speaker_candidate("[SMENE |") == ("ISMENE", "")
    assert _speaker_candidate("UEDIPUS") == ("OEDIPUS", "")
    assert _speaker_candidate("TECMESS.AA") == ("TECMESSA", "")
    assert _speaker_candidate("H¥YLLUS") == ("HYLLUS", "")
    assert _speaker_candidate("OEDIPUS ,") == ("OEDIPUS", "")


def test_ocr_semi_chorus_numbers_are_repaired():
    assert _strip_trailing_linenum("SEMI-CHORUS 2") == "SEMI-CHORUS 2"
    assert _speaker_candidate("SEMI-cHoRUS |") == ("SEMI-CHORUS 1", "")
    assert _speaker_candidate("SEMI-cHORUS 2") == ("SEMI-CHORUS 2", "")


def test_leading_ocr_junk_is_removed_from_speaker_names():
    assert _speaker_candidate("᾿ CHRYSOTHEMIS") == ("CHRYSOTHEMIS", "")
    assert _speaker_candidate("ANTIGONE .") == ("ANTIGONE", "")
    assert _speaker_candidate("7 MESSENGER") == ("MESSENGER", "")
    assert _speaker_candidate("Α TECMESSA") == ("TECMESSA", "")
    assert _speaker_candidate("“OEDIPUS") == ("OEDIPUS", "")
    assert _speaker_candidate("MAS. omit a word") == (None, "MAS. omit a word")


def test_ocr_exit_stubs_and_end_glyphs_are_dropped():
    text, report = clean_play(
        """
AJAX
ARGUMENT
DRAMATIS PERSONAE
Scene: before the tent.
AJAX
AJAX
Speak, and be heard by all assembled here.
| [Hatt AJAX.
The speech continues after the stage direction. [ Hail AJAX.
a,
\\!
END OF VOL. II.
""",
        "AJAX",
    )
    assert "Hatt" not in text
    assert "Hail AJAX" not in text
    assert "\na,\n" not in text
    assert "\\!" not in text
    assert report["speakers_found"] == ["AJAX"]


def test_own_line_speakers_become_name_dot_text():
    lines, speakers, _susp = normalize_speakers(
        [
            "ANTIGONE",
            "Ismene, sister of my blood and heart,",
            "| GUARD",
            "My lord, I will not say",
            "CHORUS (Str. 1)",
            "Sunbeam, of all that ever dawned upon",
            "SECOND MESSENGER",
            "Sorrows are thine, my lord, and more to come,",
        ]
    )
    assert speakers == ["ANTIGONE", "GUARD", "CHORUS", "SECOND MESSENGER"]
    assert lines[0].startswith("ANTIGONE. Ismene, sister")
    assert any(l.startswith("GUARD. My lord") for l in lines)
    assert any(l.startswith("CHORUS. Sunbeam") for l in lines)
    assert any(l.startswith("SECOND MESSENGER. Sorrows") for l in lines)


def test_rogers_short_labels_expand():
    from drama_pipeline import bench_clean as bc

    bc._ACTIVE_SHORT = dict(bc.ROGERS_ABBR["lysistrata"])
    name, rest = bc._speaker_candidate("CA. And so, by Zeus, we are.")
    assert name == "CALONICE"
    assert rest.startswith("And so")
    name, rest = bc._speaker_candidate("LY. Yet though I told them")
    assert name == "LYSISTRATA"
    bc._ACTIVE_SHORT = {}


def test_clean_play_drops_greek_and_keeps_english_cast():
    text, report = clean_play(LOEB, "ANTIGONE")
    assert "Ὦ κοινὸν" not in text
    assert "Child of an old blind sire" not in text
    assert "ANTIGONE. Ismene, sister" in text
    assert "ISMENE. To me, Antigone" in text
    assert "GUARD. My lord" in text
    assert "fulfil the weird" in text
    assert report["pages_dropped"] >= 1
    assert report["pages_kept"] >= 1
    assert "ANTIGONE" in report["speakers_found"]
    assert "GUARD" in report["speakers_found"]
    assert "SECOND MESSENGER" in report["speakers_found"]
    assert "VOR" not in report["speakers_found"]
    assert "B B" not in report["speakers_found"]


def test_write_clean_real_antigone(tmp_path):
    from drama_pipeline.config import REPO_ROOT

    volume = REPO_ROOT / "sources/archive-org/sophocleswitheng01soph.txt"
    dest, report = write_clean(
        volume, "storr", "antigone", "ANTIGONE", out_dir=tmp_path
    )
    text = dest.read_text(encoding="utf-8")
    assert text.splitlines()[0] == "ANTIGONE"
    assert report["pages_kept"] > 20
    assert report["pages_dropped"] > 20
    for name in (
        "ANTIGONE",
        "ISMENE",
        "CHORUS",
        "CREON",
        "GUARD",
        "HAEMON",
        "TEIRESIAS",
        "MESSENGER",
        "EURYDICE",
        "SECOND MESSENGER",
    ):
        assert name in report["speakers_found"], report["speakers_found"]
    assert "ANTIGONE. Ismene, sister" in text
    assert text.count("ANTIGONE.") >= 10
    assert "May I not speak" in text
    assert "VOR." not in text


WAY = """
EURIPIDES
IPHIGENEIA AT AULIS

ARGUMENT

The hosts of Hellas were mustered at Aulis.

DRAMATIS PERSONAE

AGAMEMNON, captain of the host.

Scene: In the Greek camp at Aulis.

IPHIGENEIA AT AULIS

AGAMEMNON
Ancient, before this tent come stand.
OLD SERVANT
I come. What purpose hast thou in hand,
Agamemnon, my king?
END OF VOL. I.

DAUGHTERS OF TROY

ARGUMENT

When Troy was taken by the Greeks.

DRAMATIS PERSONAE

POSEIDON, the God of the Sea.

Scene: The Greek camp.

DAUGHTERS OF TROY

POSEIDON
I come from the Aegean sea's salt depths,
Where Nereids wheel their dances.
HECUBA
O Earth, O city of my fathers,
Now I behold thee in the dust.
"""


def test_locate_way_iphigeneia_and_daughters():
    lines = WAY.splitlines()
    start, end = locate_play(lines, "IPHIGENEIA AT AULIS")
    body = "\n".join(lines[start:end])
    assert "Ancient, before this tent" in body
    assert "When Troy was taken" not in body
    start, end = locate_play(lines, "DAUGHTERS OF TROY")
    body = "\n".join(lines[start:end])
    assert "I come from the Aegean" in body
    assert "Ancient, before this tent" not in body


def test_cyclops_introduction_counts_as_front_matter():
    lines = """
CYCLOPS
INTRODUCTION
The Satyric Drama, of which the Cyclops is the solitary
example extant.
DRAMATIS PERSONAE
SILENUS, an old attendant of Bacchus.
Scene: At the cave.
CYCLOPS
SILENUS
O Bacchus! oh the back-aches that I got
In your cause, when my youthful blood was hot.
""".splitlines()
    start, end = locate_play(lines, "CYCLOPS")
    assert lines[start] == "CYCLOPS"
    body = "\n".join(lines[start:end])
    assert "O Bacchus" in body


def test_ion_missing_title_page_starts_after_cast():
    lines = """
ARGUMENT
The lost was found.
DRAMATIS PERSONAE
HERMES, the messenger.
Scene: At Delphi.
ION
HERMES
Atlas, whose brazen shoulders wear the base
Of heaven, the ancient home of Gods.
HIPPOLYTUS
ARGUMENT
Aphrodite speaks.
""".splitlines()
    start, end = locate_play(lines, "ION")
    body = "\n".join(lines[start:end])
    assert "Atlas, whose brazen shoulders" in body
    assert "Aphrodite speaks" not in body


def test_mixed_case_ocr_speaker_is_folded():
    assert _speaker_candidate("cycLops (looks at bowls)")[0] == "CYCLOPS"
    assert _speaker_candidate("CYCLOPs") == ("CYCLOPS", "")
    assert _speaker_candidate("SILENTUS") == ("SILENUS", "")
    assert _speaker_candidate("Lycus") == ("LYCUS", "")
    assert _speaker_candidate("Lycus (within)") == ("LYCUS", "")
    assert _speaker_candidate("LYcus") == ("LYCUS", "")
    # Wrapped verse starting with a capital is not a speaker.
    assert _speaker_candidate("Ancient, before this tent come stand.")[0] is None
    assert _speaker_candidate("From The City That Stands")[0] is None
    assert _speaker_candidate("I haste")[0] is None
    assert _speaker_candidate("Judgment")[0] is None
    assert _speaker_candidate("DEMOPHON (raising his sta,") == ("DEMOPHON", "")
    assert _speaker_candidate("MACARIA ᾿ Thou dost bid—wisely.")[0] == "MACARIA"


def test_way_verse_keeps_speaker_on_its_own_line():
    text, report = clean_play(WAY, "IPHIGENEIA AT AULIS")
    assert "AGAMEMNON. Ancient, before this tent" in text
    assert "OLD SERVANT. I come. What purpose" in text
    assert "EURIPIDES." not in text
    assert report["speakers_found"] == ["AGAMEMNON", "OLD SERVANT"]
    # A wrapped verse line starting with a capital is not a speaker.
    assert "Agamemnon, my king" in text
    assert "AGAMEMNON, MY KING" not in text


def test_copyright_heading_and_missing_argument_cut_next_play():
    lines = """
PHOENICIAN MAIDENS
ARGUMENT
Oedipus cursed his sons.
DRAMATIS PERSONAE
JOCASTA, wife of Oedipus.
Scene: Thebes.
PHOENICIAN MAIDENS
JOCASTA
To the sun I lift this prayer.
ANTIGONE
O mother, I see a host.
SUPPLIANTS ©
DRAMATIS PERSONAE
AETHRA, mother of Theseus.
Scene: Eleusis.
SUPPLIANTS
AETHRA
Demeter, warder of Eleusisland.
""".splitlines()
    start, end = locate_play(lines, "PHOENICIAN MAIDENS")
    body = "\n".join(lines[start:end])
    assert "To the sun I lift this prayer." in body
    assert "Demeter, warder of Eleusisland." not in body
    start, end = locate_play(lines, "SUPPLIANTS")
    body = "\n".join(lines[start:end])
    assert "Demeter, warder of Eleusisland." in body


def test_catalog_is_not_speakers():
    text, report = clean_play(
        """
CYCLOPS
INTRODUCTION
A satyr play.
DRAMATIS PERSONAE
SILENUS, an old attendant.
Scene: a cave.
CYCLOPS
SILENUS
O Bacchus, the back-aches that I got
In your cause, when my youthful blood was hot.
ODYSSEUS
Odysseus—Isle-king—Ithaca’s my home.
THE LOEB CLASSICAL LIBRARY
VOLUMES ALREADY PUBLISHED
AULUS GELLIUS
AUSONIUS
""",
        "CYCLOPS",
    )
    assert "SILENUS. O Bacchus" in text
    assert "AULUS GELLIUS" not in report["speakers_found"]
    assert "AUSONIUS" not in text


