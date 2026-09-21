import json
import time
from pathlib import Path

import pytest

from drama_pipeline.config import Manifest, SOURCES_DIR
from drama_pipeline.stage1_english import build_alignment
from drama_pipeline.stage1_turn_english import (
    _assign_speeches,
    _apply_english_overrides,
    _split_lindsay_speaker_line,
    parse_play_speeches,
    parse_translation,
)


def test_english_override_switches_at_match_and_not_before():
    speeches = [
        {"speaker_printed": "MESSENGER", "text": "Earlier words.", "canonical": "Servant"},
        {"speaker_printed": "MESSENGER", "text": "(aside) Go to work on the courtship of another woman.", "canonical": "Servant"},
        {"speaker_printed": "MESSENGER", "text": "Later words.", "canonical": "Servant"},
    ]
    _apply_english_overrides(speeches, [{"slot": "third", "cue": "MESSENGER", "from_text": "Go to work on the courtship of another woman", "display": "Messenger"}], "test-play", "third")
    assert [speech["canonical"] for speech in speeches] == ["Servant", "Messenger", "Messenger"]


def test_english_override_can_switch_the_same_cue_again():
    speeches = [
        {"speaker_printed": "MESSENGER", "text": "First report.", "canonical": "One"},
        {"speaker_printed": "MESSENGER", "text": "Second report.", "canonical": "One"},
        {"speaker_printed": "MESSENGER", "text": "Afterward.", "canonical": "One"},
        # A repeated anchor: the first entry already fired and must not fire again.
        {"speaker_printed": "MESSENGER", "text": "First report, once more.", "canonical": "One"},
    ]
    _apply_english_overrides(speeches, [
        {"slot": "third", "cue": "MESSENGER", "from_text": "First report", "display": "Two"},
        {"slot": "third", "cue": "MESSENGER", "from_text": "Second report", "display": "Three"},
    ], "test-play", "third")
    assert [speech["canonical"] for speech in speeches] == ["Two", "Three", "Three", "Three"]


def test_english_canonical_names_keeps_both_names_of_a_switched_cue():
    from drama_pipeline.stage1_turn_english import _english_canonical_names
    speeches = [
        {"speaker_printed": "MESSENGER", "text": "a", "canonical": "Messenger"},
        {"speaker_printed": "CHORUS", "text": "b", "canonical": "Chorus"},
        {"speaker_printed": "MESSENGER", "text": "c", "canonical": "Second Messenger"},
        {"speaker_printed": "MESSENGER", "text": "d", "canonical": "Second Messenger"},
    ]
    assert _english_canonical_names(speeches) == ["Messenger", "Chorus", "Second Messenger"]


def test_english_override_without_match_raises():
    speeches = [{"speaker_printed": "MESSENGER", "text": "Here.", "canonical": "Messenger"}]
    with pytest.raises(RuntimeError, match="test-play.*MESSENGER.*Missing"):
        _apply_english_overrides(speeches, [{"slot": "third", "cue": "MESSENGER", "from_text": "Missing words", "display": "Second Messenger"}], "test-play", "third")


FIXTURES = Path(__file__).parent / "fixtures" / "turn_english"

ALIASES = {
    "DICAEOPOLIS": "Dicaeopolis",
    "DEMOSTHENES AND NICIAS": "Demosthenes and Nicias",
    "HERALD": "Herald",
    "CHORUS": "Chorus",
    "LAMACHUS": "Lamachus",
}
SIGLA = {
    "Δι.": "Dicaeopolis",
    "Δη.Νι.": "Demosthenes and Nicias",
    "Κη.": "Herald",
    "Χο.": "Chorus",
    "Αγγ.": "Messenger",
    "Λα.": "Lamachus",
}

COMEDIES = [
    "acharnians",
    "knights",
    "clouds",
    "wasps",
    "peace",
    "birds",
    "lysistrata",
    "thesmophoriazusae",
    "frogs",
    "ecclesiazusae",
    "wealth",
]

# Printed opening speaker of each Athenian Society play, in COMEDIES order.
FIRST_SPEAKERS = [
    "DICAEOPOLIS",
    "DEMOSTHENES",
    "STREPSIADES",
    "SOSIAS",
    "FIRST SERVANT",
    "EUELPIDES",
    "LYSISTRATA",
    "MNESILOCHUS",
    "XANTHIAS",
    "PRAXAGORA",
    "CARIO",
]


def _manifest_speeches(work: str) -> tuple[list[dict], dict[str, str]]:
    manifest = Manifest.for_work(work)
    cfg = manifest.data["english"]["primary"]
    aliases = manifest.data["speakers"]["english"]
    text = (SOURCES_DIR / cfg["source"]).read_text(encoding="utf-8")
    return parse_play_speeches(
        text,
        cfg["play"],
        known_names=set(aliases),
        line_fixes=cfg.get("line_fixes") or {},
    )


def _antigone_spine() -> dict:
    labels = ["ΑΝ.", "ΙΣ.", "Χο.", "ΚΡ."]
    return {
        "work": "antigone",
        "segments": [
            {
                "id": f"1:{n}",
                "book": 1,
                "column": "1",
                "lines": [{"n": n, "ref": str(n), "text": "Greek sample text"}],
                "speakers": [{"line": n, "offset": 0, "label": label}],
            }
            for n, label in enumerate(labels, 1)
        ],
    }


def _parse():
    spine = json.loads((FIXTURES / "spine.json").read_text(encoding="utf-8"))
    return parse_translation(
        FIXTURES / "play.txt",
        spine,
        work_id="test-play",
        translation_id="athenian-society",
        play="THE ACHARNIANS",
        sigla=SIGLA,
        english_aliases=ALIASES,
        footnotes_enabled=True,
    )


def test_speech_parsing_wraps_and_uses_last_title():
    text = (FIXTURES / "play.txt").read_text(encoding="utf-8")
    speeches, notes = parse_play_speeches(text, "THE ACHARNIANS")
    assert len(speeches) == 6
    assert speeches[0]["speaker_printed"] == "DICAEOPOLIS"
    assert "gnawed at my heart and how few" in speeches[0]["text"]
    assert speeches[1]["speaker_printed"] == "DEMOSTHENES AND NICIAS"
    assert all("must not be ingested" not in s["text"] for s in speeches)
    assert all(s["speaker_printed"] != "FAKE" for s in speeches)
    assert notes["5"].startswith("A name invented")


def test_alias_and_sigla_canonicalisation():
    english, _footnotes, report = _parse()
    first = english["chunks"][0]
    assert first["turns"][0]["speaker"] == "Dicaeopolis"
    assert first["turns"][0]["display"] == "DICAEOPOLIS"
    speakers = report["speakers"]
    assert "Dicaeopolis" in speakers["english_canonical"]
    assert "Dicaeopolis" in speakers["greek_roster"]
    assert speakers["only_in_english"] == []


def test_a_foreign_residual_is_shown_flagged_not_dropped():
    """P3.3: the extra Dicaeopolis speech is not any segment's in its window —
    so it is SHOWN carrying the disagreement, never dropped (it used to be
    counted as `residual_unassigned` and reach no chunk at all).

    R12 moved WHERE: it used to be appended to the Herald's chunk, the slot
    the English before it went to, and it is shown on the CHORUS's segment
    instead -- the next paired English's own, which is the Greek just before
    the anchor this speech precedes. The old park printed a speech against
    Greek behind the one it translates, which is how Way's IT parodos read a
    speech ahead for 85 lines."""
    english, _footnotes, report = _parse()
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert "1:40" not in by_id
    assert by_id["1:20"]["text"] == "The assembly is open."
    chorus = by_id["1:30"]
    assert chorus["text"].startswith("An extra speech the Greek does not split.")
    assert "We are the old men" in chorus["text"]
    assert [turn["speaker"] for turn in chorus["turns"]] == ["Dicaeopolis", "Chorus"]
    assert chorus["turns"][0]["speakerMismatch"] == {
        "english": "Dicaeopolis",
        "greek": "Chorus",
    }
    assert "speakerMismatch" not in chorus["turns"][1]
    # Not every turn of the chunk disagrees, so the pre-P2h chunk-level
    # compatibility flag stays off.
    assert "speakerMismatch" not in chorus
    assert report["residual_flagged"] == 1
    assert report["residual_unassigned"] == 0
    assert [chunk["id"] for chunk in english["chunks"]] == [
        "1:1",
        "1:10",
        "1:20",
        "1:30",
        "1:50",
    ]


def test_unmatched_greek_is_unmatched_in_alignment():
    english, _footnotes, _report = _parse()
    spine = json.loads((FIXTURES / "spine.json").read_text(encoding="utf-8"))
    alignment = build_alignment(spine, english)
    unmatched = [p["segment"] for p in alignment["pairs"] if p["english"] is None]
    assert unmatched == ["1:40"]
    assert alignment["english_only"] == []


def test_footnote_label_shape():
    english, footnotes, report = _parse()
    assert list(footnotes) == ["1.5"]
    assert "-" not in next(iter(footnotes))
    assert "[^1.5]" in english["chunks"][0]["text"]
    assert "[5]" not in english["chunks"][0]["text"]
    assert footnotes["1.5"].startswith("A name invented")
    assert report["footnotes"] == 1


def test_report_numbers():
    _english, _footnotes, report = _parse()
    assert report["speeches_parsed"] == 6
    assert report["paired"] == 5
    assert report["residual_grouped"] == 0
    assert report["residual_flagged"] == 1
    assert report["residual_unassigned"] == 0
    assert report["head_unassigned"] == 0
    assert report["greek_unpaired"] == 1
    assert report["greek_unpaired_ids"] == ["1:40"]
    assert report["pairing_rate"] == 5 / 6
    assert report["segments_with_chunk"] == 5
    assert report["segments_total"] == 6
    assert report["coverage_ratio"] == 5 / 6
    assert all(chunk.get("approximate") is True for chunk in _english["chunks"])


def test_sigla_resolver_folds_numeral_primes_and_applies_overrides(tmp_path):
    from drama_pipeline.config import Manifest
    from drama_pipeline import stage1_turn_english as m
    man = Manifest({"work": {"id": "k"}, "speakers": {
        "sigla": {"\u039f\u0399. \u0391\u02b9": "First Slave", "\u0391\u0399.": "Aeacus", "\u2014": None},
        "overrides": [{"siglum": "\u0391\u0399.", "from": "830", "display": "Aeschylus"}]}}, tmp_path / "k.yaml")
    r = m._SiglaResolver(man)
    assert r.resolve("\u039f\u0399. \u0391\u0374", "12") == ("First Slave", True)   # export prime U+0374 vs key U+02B9
    assert r.resolve("\u0391\u0399.", "500") == ("Aeacus", True)
    assert r.resolve("\u0391\u0399.", "900") == ("Aeschylus", True)
    assert r.resolve("\u2014", "5") == (None, True)


def test_speaker_line_accepts_accented_capitals():
    """The 1912 Lysistrata prints CALONICÉ. and MYRRHINÉ. (72 speeches
    between them); an ASCII-only name class merged them into the previous
    speech and the play paired at 0.75."""
    from drama_pipeline.stage1_turn_english import _SPEAKER_LINE
    assert _SPEAKER_LINE.match("CALONICÉ. Why, what is the matter?").group("name") == "CALONICÉ"
    assert _SPEAKER_LINE.match("MYRRHINÉ (_aside_). Not now.").group("name") == "MYRRHINÉ"


def test_real_lysistrata_periodless_alias_names_start_speeches():
    speeches, _notes = _manifest_speeches("lysistrata")
    found = [
        speech["speaker_printed"]
        for speech in speeches
        if speech["text"].startswith(
            ("How so--not the same thing?", "You?", "Yes, just we.")
        )
    ]
    assert found == ["LYSISTRATA", "MAGISTRATE", "LYSISTRATA"]


def test_periodless_name_must_be_a_declared_alias():
    text = """TEST PLAY

ALPHA. One.

UNKNOWN This stays in Alpha's speech.

BETA Two.
FINIS
"""
    speeches, _notes = parse_play_speeches(
        text, "TEST PLAY", known_names={"ALPHA", "BETA"}
    )
    assert [speech["speaker_printed"] for speech in speeches] == ["ALPHA", "BETA"]
    assert "UNKNOWN This stays" in speeches[0]["text"]


def test_real_own_line_labels_start_speeches():
    lysistrata, _notes = _manifest_speeches("lysistrata")
    cinesias = [
        speech for speech in lysistrata
        if speech["speaker_printed"] == "CINESIAS"
        and "handling his tool" in speech["text"]
    ]
    assert len(cinesias) == 1
    assert cinesias[0]["text"].endswith("there!")

    frogs, _notes = _manifest_speeches("frogs")
    dionysus = [
        speech for speech in frogs
        if speech["speaker_printed"] == "DIONYSUS"
        and "should you not be beaten" in speech["text"]
    ]
    assert len(dionysus) == 1
    assert dionysus[0]["text"].startswith("(to Xanthias)\n\nBut why")


def test_real_notes_stop_at_index_and_next_play_title():
    _clouds, clouds_notes = _manifest_speeches("clouds")
    assert "INDEX" not in next(reversed(clouds_notes.values()))

    _knights, knights_notes = _manifest_speeches("knights")
    assert not next(reversed(knights_notes.values())).endswith("THE ACHARNIANS")

    _frogs, frogs_notes = _manifest_speeches("frogs")
    frogs_ns = {int(n) for n in frogs_notes}
    assert {n for n in range(446, 544)} <= frogs_ns
    assert sum(1 for n in frogs_ns if 446 <= n <= 543) == 98

    _eccl, eccl_notes = _manifest_speeches("ecclesiazusae")
    eccl_ns = {int(n) for n in eccl_notes}
    assert {n for n in range(665, 736)} <= eccl_ns
    assert sum(1 for n in eccl_ns if 665 <= n <= 735) == 71


# B7 addendum (fix-mechanisms brief, 2026-09-17): Project Gutenberg's
# `[Greek: ...]` and `[Symbol: ...]` markup -- a word its plain-text edition
# could not set in Greek type or as a symbol -- printed raw in the footnote
# popup instead of the transliteration or description it wraps. Knights
# review finding 5: footnote 1 is on the play's first line.
def test_gutenberg_footnote_translit_and_symbol_markup_is_unwrapped():
    knights, knights_notes = _manifest_speeches("knights")
    assert "[Greek:" not in "".join(knights_notes.values())
    assert "[Symbol:" not in "".join(knights_notes.values())
    assert "Paphlag_on" in knights_notes["5"]
    assert "Letter 'san'" in knights_notes["80"]


def test_unaliased_english_speakers_fail_with_play_and_name(tmp_path):
    path = tmp_path / "play.txt"
    path.write_text("TEST PLAY\nKNOWN. Yes.\nSTRANGER. No.\nFINIS\n", encoding="utf-8")
    spine = {
        "work": "test",
        "segments": [{
            "id": "1:1", "book": 1, "column": "1",
            "lines": [{"n": 1, "ref": "1", "text": "Greek"}],
            "speakers": [{"line": 1, "offset": 0, "label": "Κ."}],
        }],
    }
    with pytest.raises(ValueError, match=r"TEST PLAY: STRANGER"):
        parse_translation(
            path,
            spine,
            work_id="test",
            translation_id="test",
            play="TEST PLAY",
            sigla={"Κ.": "Known"},
            english_aliases={"KNOWN": "Known"},
            footnotes_enabled=False,
        )


def test_all_comedy_alias_tables_cover_real_english_speakers():
    for work, first in zip(COMEDIES, FIRST_SPEAKERS, strict=True):
        manifest = Manifest.for_work(work)
        cfg = manifest.data["english"]["primary"]
        speakers = manifest.data["speakers"]
        aliases = speakers["english"]
        roster = {display for display in speakers["sigla"].values() if display}
        speeches, _notes = parse_play_speeches(
            (SOURCES_DIR / cfg["source"]).read_text(encoding="utf-8"),
            cfg["play"],
            known_names=set(aliases),
            line_fixes=cfg.get("line_fixes") or {},
        )
        assert speeches[0]["speaker_printed"] == first, work
        for speech in speeches:
            printed = speech["speaker_printed"]
            assert printed in aliases, (work, printed)
            assert aliases[printed] in roster, (work, printed, aliases[printed])
            text = speech["text"]
            assert "DRAMATIS" not in text, work
            assert "costumed as Wasps" not in text, work
            assert "attending AGATHON" not in text, work


def test_wasps_and_thesmo_cast_list_lines_are_not_speeches():
    pg8689 = (SOURCES_DIR / "gutenberg/pg8689.txt").read_text(encoding="utf-8").splitlines()
    assert pg8689[178] == "CHORUS OF ELDERS, costumed as Wasps."
    assert pg8689[8687] == "CHORUS attending AGATHON."
    assert pg8689[8693].startswith("CHORUS OF THESMOPHORIAZUSAE")

    wasps, _notes = _manifest_speeches("wasps")
    assert wasps[0]["speaker_printed"] == "SOSIAS"
    assert all("costumed as Wasps" not in speech["text"] for speech in wasps)
    assert all(speech["speaker_printed"] != "CHORUS OF ELDERS" for speech in wasps)

    thesmo, _notes = _manifest_speeches("thesmophoriazusae")
    assert thesmo[0]["speaker_printed"] == "MNESILOCHUS"
    assert all("attending AGATHON" not in speech["text"] for speech in thesmo)
    assert all(
        not speech["text"].startswith("attending AGATHON")
        and "women keeping the Feast of Demeter" not in speech["text"]
        for speech in thesmo
    )


def test_lysistrata_chorus_of_athenians_is_its_own_speech():
    """The closing ode is the Athenian chorus's, not Lysistrata's: with
    `CHORUS OF ATHENIANS` declared in speakers.english the periodless rule
    starts a new speech there (P2g finding 12)."""
    pg8688 = (SOURCES_DIR / "gutenberg/pg8688.txt").read_text(encoding="utf-8").splitlines()
    assert pg8688[9150].startswith("CHORUS OF ATHENIANS Appear")

    speeches, _notes = _manifest_speeches("lysistrata")
    preceding = [
        speech
        for speech in speeches
        if speech["speaker_printed"] == "LYSISTRATA"
        and "All is for the best" in speech["text"]
    ]
    assert len(preceding) == 1
    assert "Appear, appear, dancers" not in preceding[0]["text"]
    ode = [
        speech
        for speech in speeches
        if speech["speaker_printed"] == "CHORUS OF ATHENIANS"
    ]
    assert len(ode) == 1
    assert ode[0]["text"].startswith("Appear, appear, dancers")
    assert all(
        not speech["text"].startswith("OF ATHENIANS Appear") for speech in speeches
    )


def test_speech_length_ratio_outlier_is_reported(tmp_path):
    path = tmp_path / "play.txt"
    long_text = "x" * 100
    path.write_text(
        f"TEST PLAY\nALPHA. abcdefghij\nBETA. abcdefghij\nGAMMA. {long_text}\nFINIS\n",
        encoding="utf-8",
    )
    labels = [("Α.", "Alpha"), ("Β.", "Beta"), ("Γ.", "Gamma")]
    spine = {
        "work": "test",
        "segments": [
            {
                "id": f"1:{n}", "book": 1, "column": "1",
                "lines": [{"n": n, "ref": str(n), "text": "abcdefghij"}],
                "speakers": [{"line": n, "offset": 0, "label": label}],
            }
            for n, (label, _display) in enumerate(labels, 1)
        ],
    }
    _english, _footnotes, report = parse_translation(
        path,
        spine,
        work_id="test",
        translation_id="test",
        play="TEST PLAY",
        sigla=dict(labels),
        english_aliases={"ALPHA": "Alpha", "BETA": "Beta", "GAMMA": "Gamma"},
        footnotes_enabled=False,
    )
    # The heuristic measures LENGTH, so it keeps a length name; the key
    # `speech_mismatches` belongs to perseus-play's real speaker mismatches.
    assert report["length_ratio_outliers"] == [
        {"greek_id": "1:3", "english_index": 2, "ratio": 10.0}
    ]
    assert report["length_ratio_outlier_count"] == 1
    assert "speech_mismatches" not in report
    assert report["turn_shifts"] == []
    assert report["turn_shift_count"] == 0
    assert report["turn_shift_rate"] == 0.0


def test_head_residue_attaches_only_when_speaker_matches():
    """English BEFORE the first pair keeps its own gate: that zone is the
    dramatis personae and the front matter, not dialogue, so it is not swept
    onto segment 0 by the never-drop rule."""
    assigned, residual, head_unassigned, unassigned, flags = _assign_speeches(
        4, [(3, 2)], 3
    )
    assert assigned[0] == []
    assert assigned[3] == [2]
    assert residual == 0
    assert head_unassigned == 2
    assert unassigned == 0
    assert flags == {}

    matched, matched_residual, matched_head, _un, _f = _assign_speeches(
        4,
        [(3, 2)],
        3,
        greek_names=["Sosias", "X", "Y", "Z"],
        english_names=["Sosias", "Sosias", "Z"],
    )
    assert matched[0] == [0, 1]
    assert matched[3] == [2]
    assert matched_residual == 2
    assert matched_head == 0

    skipped, skipped_residual, skipped_head, _un2, _f2 = _assign_speeches(
        4,
        [(3, 2)],
        3,
        greek_names=["Sosias", "X", "Y", "Z"],
        english_names=["Chorus", "Chorus", "Z"],
    )
    assert skipped[0] == []
    assert skipped[3] == [2]
    assert skipped_residual == 0
    assert skipped_head == 2


def test_residual_on_a_segment_that_speaker_never_speaks_is_flagged():
    """P3.3, Frogs-shaped: Dionysus and Xanthias alternate, the English runs
    two Dionysus speeches together, and the trailing one reaches no segment of
    his.  It is shown on the segment the pairing landed on, flagged with the
    disagreement — it used to be dropped (P2i finding 5)."""
    greek = ["Dionysus", "Xanthias", "Dionysus", "Xanthias"]
    english = ["Dionysus", "Xanthias", "Dionysus", "Xanthias", "Dionysus"]
    # English 4 (Dionysus) has no pair; the cursor is the Xanthias segment 3
    # and no segment after it is Dionysus', so it parks there flagged.
    assigned, residual, head, unassigned, flags = _assign_speeches(
        4,
        [(0, 0), (1, 1), (2, 2), (3, 3)],
        5,
        greek_names=greek,
        english_names=english,
    )
    assert assigned[3] == [3, 4]
    assert residual == 0
    assert head == 0
    assert unassigned == 0
    assert flags == {4: "Xanthias"}

    # A name the segment's own lines carry (an antilabe share) parks CLEAN,
    # and so does an unnamed continuation.
    parked, parked_residual, _head, parked_unassigned, parked_flags = _assign_speeches(
        4,
        [(0, 0), (1, 1), (2, 2), (3, 3)],
        6,
        greek_names=greek,
        english_names=english + [None],
        greek_alt=[set(), set(), set(), {"Dionysus"}],
    )
    assert parked[3] == [3, 4, 5]
    assert parked_residual == 2
    assert parked_unassigned == 0
    assert parked_flags == {}


def test_residual_walks_forward_to_the_segment_that_speaks_it():
    """P3.3 step 1, the stichomythia case the LCS drops: the Greek packs
    A-B-A-B into segments the pairing skipped, so the unpaired English walks
    FORWARD — over the unpaired segments between the surrounding pairs, up to
    and including the next paired one — to the nearest segment whose lines
    carry its speaker, and never backwards (document order stays monotone)."""
    greek = ["Alpha", "Beta", "Alpha", "Beta", "Alpha"]
    # Only the first and last agree, so segments 1-3 sit between the pairs.
    assigned, residual, _head, unassigned, flags = _assign_speeches(
        5,
        [(0, 0), (4, 3)],
        4,
        greek_names=greek,
        english_names=["Alpha", "Beta", "Alpha", "Alpha"],
    )
    assert assigned[1] == [1]  # Beta walks to the Beta segment
    assert assigned[2] == [2]  # the next Alpha to the Alpha segment after it
    assert assigned[4] == [3]
    assert residual == 2
    assert unassigned == 0
    assert flags == {}

    # Monotone: a residual never walks BACK to a namesake segment behind the
    # cursor — Alpha's segment 0 is already past, so the unpaired Alpha is
    # flagged on the Beta segment instead of jumping backwards in the text.
    back, back_residual, _h, back_unassigned, back_flags = _assign_speeches(
        2,
        [(1, 0)],
        2,
        greek_names=["Alpha", "Beta"],
        english_names=["Beta", "Alpha"],
    )
    assert back[0] == []
    assert back[1] == [0, 1]
    assert back_residual == 0
    assert back_unassigned == 0
    assert back_flags == {1: "Beta"}


def test_named_residual_on_a_speakerless_lyric_is_flagged_not_dropped():
    """P2j finding 4 under the P3.3 ruling: the ode carries no speaker at all,
    so it is still not a wildcard — a named residual does not count as CLEAN
    there.  But it is no longer dropped: with nowhere better in the window it
    parks on the ode flagged, and the flag names the ode's speaker (None: the
    edition attributes those lines to nobody)."""
    from drama_pipeline.stage1_turn_english import _OCR_JUNK

    greek = ["Dionysus", None]  # segment 1 is the unattributed ode
    pairs = [(0, 0), (1, 1)]
    assigned, residual, head, unassigned, flags = _assign_speeches(
        2,
        pairs,
        3,
        greek_names=greek,
        english_names=["Dionysus", "Chorus", "Dionysus"],
    )
    assert assigned[1] == [1, 2]
    assert residual == 0
    assert head == 0
    assert unassigned == 0
    assert flags == {2: None}

    parked, parked_residual, _head, parked_unassigned, parked_flags = _assign_speeches(
        2,
        pairs,
        4,
        greek_names=greek,
        english_names=["Dionysus", "Chorus", None, _OCR_JUNK],
    )
    assert parked[1] == [1, 2, 3]
    assert parked_residual == 2
    assert parked_unassigned == 0
    assert parked_flags == {}


def test_head_residue_unassigned_is_reported(tmp_path):
    """P3.4 note: the play now closes with a REAL Chorus speech.

    The fixture used to be ``CHORUS junk / ALPHA opening`` against a single
    packed segment, where the segment offered exactly one pairing slot
    (Alpha).  Pairing over shares offers two — Alpha at offset 0 and the
    Chorus share at offset 1 — and ``[Chorus, Alpha]`` against
    ``[Alpha, Chorus]`` has two longest common subsequences of length one, so
    the junk could pair on a tie.  The trailing real Chorus speech makes the
    intended reading the unique longest one and leaves the rule this test is
    about — head English attaches to the first slot only when it names that
    slot's speaker — the only thing being measured.
    """
    path = tmp_path / "play.txt"
    path.write_text(
        "TEST PLAY\nCHORUS. Cast-list junk.\nALPHA. Real opening.\n"
        "CHORUS. Real chorus.\nFINIS\n",
        encoding="utf-8",
    )
    spine = {
        "work": "test",
        "segments": [
            {
                "id": "1:1", "book": 1, "column": "1",
                "lines": [{"n": 1, "ref": "1", "text": "Greek alpha"}],
                "speakers": [
                    {"line": 1, "offset": 0, "label": "Α."},
                    {"line": 1, "offset": 1, "label": "Χο."},
                ],
            },
        ],
    }
    english, _footnotes, report = parse_translation(
        path,
        spine,
        work_id="test",
        translation_id="test",
        play="TEST PLAY",
        sigla={"Α.": "Alpha", "Χο.": "Chorus"},
        english_aliases={"CHORUS": "Chorus", "ALPHA": "Alpha"},
        footnotes_enabled=False,
    )
    assert report["head_unassigned"] == 1
    assert report["paired"] == 2
    assert [chunk["id"] for chunk in english["chunks"]] == ["1:1"]
    assert "Cast-list junk" not in english["chunks"][0]["text"]
    assert english["chunks"][0]["turns"][0]["speaker"] == "Alpha"
    # Both shares of the packed line pair, and the segment's chunk carries
    # them in share order.
    assert english["chunks"][0]["turns"][1]["speaker"] == "Chorus"


def test_quality_numbers_are_surfaced_in_the_stage1_summary():
    from drama_pipeline import __main__ as cli

    main_src = Path(cli.__file__).read_text(encoding="utf-8")
    assert "ratio_outliers={report['length_ratio_outlier_count']}" in main_src
    # P3.5 finding 6: the summary prints the GATED number (the onset rate and
    # its count) beside the cumulative shift count, each clearly labelled.
    assert "shift_cum={report['turn_shift_count']}" in main_src
    assert "new_drifts={report['turn_shift_new_drifts']}" in main_src
    assert "shift_rate={report['turn_shift_rate']:.3f}" in main_src
    assert "flagged={report['residual_flagged']}" in main_src
    assert "seg_rate={report['segment_pairing_rate']:.3f}" in main_src
    assert "head_unassigned={report['head_unassigned']}" in main_src
    assert "unresolved={report['unresolved_mismatch_count']}" in main_src
    assert "covered={report['covered_by_count']}" in main_src


def _turn_text_manifest(**english) -> Manifest:
    data = {
        "work": {"id": "test-play", "title": "Test", "author": "aristophanes"},
        "citation": {"scheme": "play-line"},
        "books": [{"n": 1, "start": "1", "end": "3"}],
        "english": {
            "primary": {"id": "as", "name": "AS", "model": "turn-text"},
            "gaps": [],
            **english,
        },
        "proper_names": [],
    }
    return Manifest(data, Path("test-play.yaml"))


def _stage2_with_report(
    monkeypatch,
    tmp_path,
    report: dict,
    manifest: Manifest,
    unmatched_ids: tuple[str, ...] = (),
    slot_reports: dict | None = None,
):
    from drama_pipeline import stage2_validate as s2

    stage1 = tmp_path / "stage1"
    stage1.mkdir(exist_ok=True, parents=True)
    if report is not None:
        (stage1 / "english_report.json").write_text(
            json.dumps(report), encoding="utf-8"
        )
    for name, data in (slot_reports or {}).items():
        (stage1 / name).write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(s2, "BUILD_DIR", tmp_path)
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": f"1:{n}",
                "book": 1,
                "column": "1",
                "lines": [{"n": n, "ref": str(n), "text": "Greek sample text"}],
                "speakers": [{"line": n, "offset": 0, "label": "Χο."}],
            }
            for n in (1, 2, 3)
        ],
    }
    english = {
        "chunks": [
            {"id": f"1:{n}", "column": "1", "text": "English sample text here."}
            for n in (1, 2, 3)
            if f"1:{n}" not in unmatched_ids
        ]
    }
    alignment = {
        "pairs": [
            {
                "segment": f"1:{n}",
                "english": None if f"1:{n}" in unmatched_ids else f"1:{n}",
            }
            for n in (1, 2, 3)
        ],
        "english_only": [],
    }
    return s2.validate(manifest, spine, english, alignment)


def test_stage2_gates_length_ratio_and_turn_shift_separately(tmp_path, monkeypatch):
    base = {
        "work": "test-play",
        "pairing_rate": 0.99,
        "paired": 100,
        "length_ratio_outlier_count": 10,
        "turn_shift_count": 2,
        "turn_shift_rate": 0.02,
    }
    ok = _stage2_with_report(monkeypatch, tmp_path, base, _turn_text_manifest())
    assert ok["checks"]["turn_text_length_ratio"]["ok"] is True
    assert ok["checks"]["turn_text_turn_shift"]["ok"] is True
    assert "turn_text_mismatches" not in ok["checks"]

    shifted = _stage2_with_report(
        monkeypatch,
        tmp_path,
        {**base, "turn_shift_count": 12, "turn_shift_rate": 0.12},
        _turn_text_manifest(),
    )
    shift = shifted["checks"]["turn_text_turn_shift"]
    assert shift["ok"] is False
    # Default gate is 0.10 on the NEW-drift rate (P3.4 ruling).
    assert "turn-shift rate 0.120 exceeds maximum 0.100" in shift["error"]
    # The length gate is untouched at 0.25 and still passes.
    assert shifted["checks"]["turn_text_length_ratio"]["ok"] is True
    assert shifted["ok"] is False

    allowed = _stage2_with_report(
        monkeypatch,
        tmp_path,
        {**base, "turn_shift_count": 9, "turn_shift_rate": 0.09},
        _turn_text_manifest(max_turn_shift_rate=0.1),
    )
    assert allowed["checks"]["turn_text_turn_shift"]["ok"] is True

    long_ratio = _stage2_with_report(
        monkeypatch,
        tmp_path,
        {**base, "length_ratio_outlier_count": 30},
        _turn_text_manifest(),
    )
    assert long_ratio["checks"]["turn_text_length_ratio"]["ok"] is False
    assert (
        "length-ratio outlier rate 0.300"
        in long_ratio["checks"]["turn_text_length_ratio"]["error"]
    )


def test_stage2_reads_a_zero_shift_rate_as_a_value_and_quotes_the_gated_count(
    tmp_path, monkeypatch
):
    """P3.5 finding 1: `float(x or fallback)` read a reported 0.0 as missing.

    The gated number is the ONSET rate (`turn_shift_rate`, pairs where a
    same-name drift begins).  A perfectly aligned play reports 0.0 for it
    beside a large cumulative `turn_shift_count`, and the old `or` swapped the
    honest 0.0 for the cumulative rate — 0.35–0.74 in the comedies — failing
    the cleanest play in the corpus.  The error text quotes the gated count
    too, not the cumulative one.
    """
    base = {
        "work": "test-play",
        "pairing_rate": 0.99,
        "paired": 100,
        "length_ratio_outlier_count": 10,
    }
    clean = _stage2_with_report(
        monkeypatch,
        tmp_path,
        {**base, "turn_shift_count": 62, "turn_shift_rate": 0.0, "turn_shift_new_drifts": 0},
        _turn_text_manifest(),
    )
    shift = clean["checks"]["turn_text_turn_shift"]
    assert shift["ok"] is True
    assert shift["rate"] == 0.0
    assert (shift["new_drifts"], shift["count"]) == (0, 62)

    over = _stage2_with_report(
        monkeypatch,
        tmp_path,
        {
            **base,
            "turn_shift_count": 62,
            "turn_shift_rate": 0.12,
            "turn_shift_new_drifts": 12,
        },
        _turn_text_manifest(),
    )
    error = over["checks"]["turn_text_turn_shift"]["error"]
    assert "turn-shift rate 0.120 exceeds maximum 0.100" in error
    # The gated count, with the cumulative one named as what it is.
    assert "12/100 pairs OPEN a new same-name position drift" in error
    assert "cumulative shifts 62" in error

    # A pre-P3.4 report has no onset rate at all: fall back to the cumulative
    # rate, which is never smaller — fails closed.
    old = _stage2_with_report(
        monkeypatch,
        tmp_path,
        {**base, "turn_shift_count": 62},
        _turn_text_manifest(),
    )
    assert old["checks"]["turn_text_turn_shift"]["ok"] is False
    assert old["checks"]["turn_text_turn_shift"]["new_drifts"] == 62


def test_stage2_pairing_floor_is_its_own_check_and_keeps_the_hole_allowance(
    tmp_path, monkeypatch
):
    """P3.5 finding 3.

    The floor used to be a silent switch: below it the unmatched allowance was
    skipped, so every Greek hole in the play failed `alignment` and the one
    number that had really moved was buried.  It is now its own check, naming
    the rate and the floor, and the holes stay expected either way (turn-text
    English carries no line numbers — the holes are the model, not damage).
    """
    base = {
        "work": "test-play",
        "paired": 100,
        "length_ratio_outlier_count": 10,
        "turn_shift_count": 2,
        "turn_shift_rate": 0.02,
        "turn_shift_new_drifts": 2,
    }
    low = _stage2_with_report(
        monkeypatch,
        tmp_path,
        {**base, "pairing_rate": 0.80},
        _turn_text_manifest(),
        unmatched_ids=("1:2",),
    )
    floor = low["checks"]["turn_text_pairing_floor"]
    assert floor["ok"] is False
    assert floor["rate"] == 0.80 and floor["floor"] == 0.85
    assert "pairing rate 0.800 is below the floor 0.850" in floor["error"]
    assert low["ok"] is False
    # The hole is still an expected hole: alignment does not double-fail.
    assert low["checks"]["alignment"]["ok"] is True
    assert low["checks"]["alignment"]["allowed_unmatched"] == ["1:2"]

    # A manifest may declare its own floor (a structural reason, commented).
    declared = _stage2_with_report(
        monkeypatch,
        tmp_path,
        {**base, "pairing_rate": 0.855},
        _turn_text_manifest(min_pairing_rate=0.80),
        unmatched_ids=("1:2",),
    )
    assert declared["checks"]["turn_text_pairing_floor"]["ok"] is True
    assert declared["checks"]["alignment"]["ok"] is True

    # P3.6 finding 4: exactly the floor passes (`rate < floor` fails)...
    exact = _stage2_with_report(
        monkeypatch,
        tmp_path,
        {**base, "pairing_rate": 0.85},
        _turn_text_manifest(),
        unmatched_ids=("1:2",),
    )
    assert exact["checks"]["turn_text_pairing_floor"]["ok"] is True
    # ...and a report with no rate at all fails closed.
    no_rate = _stage2_with_report(
        monkeypatch,
        tmp_path,
        {k: v for k, v in base.items() if k != "pairing_rate"},
        _turn_text_manifest(),
        unmatched_ids=("1:2",),
    )
    assert no_rate["checks"]["turn_text_pairing_floor"]["ok"] is False
    assert "carries no pairing_rate" in no_rate["checks"]["turn_text_pairing_floor"]["error"]

    # Fails closed with no report of this play's own.
    foreign = _stage2_with_report(
        monkeypatch,
        tmp_path,
        {"work": "frogs", "pairing_rate": 0.99, "paired": 10},
        _turn_text_manifest(),
    )
    assert foreign["checks"]["turn_text_pairing_floor"]["ok"] is False
    assert "not 'test-play'" in foreign["checks"]["turn_text_pairing_floor"]["error"]


def test_thesmophoriazusae_declares_its_pairing_floor_at_the_default():
    """P3.6 finding 2: 0.855 measured (432/505), declared AT 0.85 so three
    more lost pairs fail loudly — not 0.80, which was 25 pairs of slack."""
    manifest = Manifest.for_work("thesmophoriazusae")
    assert manifest.data["english"]["min_pairing_rate"] == 0.85


def test_stage2_gates_residual_english_that_reached_no_chunk(tmp_path, monkeypatch):
    """P2j finding 3: a residual the builder refused to park is English the
    reader never sees — the turn-text twin of `attachment_loss`.  Default 0;
    a play declares `english.max_residual_unassigned` to allow its own."""
    base = {
        "work": "test-play",
        "pairing_rate": 0.99,
        "paired": 100,
        "length_ratio_outlier_count": 10,
        "turn_shift_count": 2,
        "turn_shift_rate": 0.02,
    }
    clean = _stage2_with_report(
        monkeypatch, tmp_path, {**base, "residual_unassigned": 0}, _turn_text_manifest()
    )
    assert clean["checks"]["turn_text_residual_unassigned"]["ok"] is True

    lost = _stage2_with_report(
        monkeypatch, tmp_path, {**base, "residual_unassigned": 7}, _turn_text_manifest()
    )
    check = lost["checks"]["turn_text_residual_unassigned"]
    assert check["ok"] is False
    assert check["count"] == 7
    assert "7 residual English speech(es) parked on no Greek speech" in check["error"]
    assert lost["ok"] is False

    allowed = _stage2_with_report(
        monkeypatch,
        tmp_path,
        {**base, "residual_unassigned": 7},
        _turn_text_manifest(max_residual_unassigned=7),
    )
    assert allowed["checks"]["turn_text_residual_unassigned"]["ok"] is True

    # Fails closed on a report that belongs to another play.
    foreign = _stage2_with_report(
        monkeypatch,
        tmp_path,
        {"work": "frogs", "pairing_rate": 0.99, "paired": 10},
        _turn_text_manifest(),
    )
    stale = foreign["checks"]["turn_text_residual_unassigned"]
    assert stale["ok"] is False
    assert "not 'test-play'" in stale["error"]


def test_stage2_turn_text_checks_fail_closed_without_this_works_report(
    tmp_path, monkeypatch
):
    """A missing report, or one left by the previous play, must not open the
    gate (P2g finding 11)."""
    foreign = _stage2_with_report(
        monkeypatch,
        tmp_path,
        {"work": "frogs", "pairing_rate": 0.99, "paired": 10},
        _turn_text_manifest(),
    )
    for key in (
        "turn_text_length_ratio",
        "turn_text_turn_shift",
        "turn_text_residual_unassigned",
        "turn_text_head_unassigned",
        "turn_text_pairing_floor",
    ):
        assert foreign["checks"][key]["ok"] is False
        assert "not 'test-play'" in foreign["checks"][key]["error"]
    assert foreign["ok"] is False

    missing = _stage2_with_report(
        monkeypatch, tmp_path / "empty", None, _turn_text_manifest()
    )
    for key in (
        "turn_text_length_ratio",
        "turn_text_turn_shift",
        "turn_text_residual_unassigned",
        "turn_text_head_unassigned",
        "turn_text_pairing_floor",
    ):
        assert missing["checks"][key]["ok"] is False
        assert "no stage1 English report" in missing["checks"][key]["error"]


def test_stage2_gates_public_comparison_turn_text_reports(tmp_path, monkeypatch):
    """Astra lane C, F1: public secondary/third/overlay reports use the slot floor."""
    base = {
        "work": "test-play",
        "pairing_rate": 0.99,
        "paired": 100,
        "length_ratio_outlier_count": 10,
        "turn_shift_count": 2,
        "turn_shift_rate": 0.02,
        "turn_shift_new_drifts": 2,
        "residual_unassigned": 0,
        "head_unassigned": 0,
        "unresolved_mismatch_count": 0,
    }
    data = {
        "work": {"id": "test-play", "title": "Test", "author": "aeschylus"},
        "citation": {"scheme": "play-line"},
        "books": [{"n": 1, "start": "1", "end": "3"}],
        "english": {
            "primary": {"id": "smyth", "name": "Smyth", "model": "perseus-play"},
            "secondary": {
                "id": "morshead",
                "name": "Morshead",
                "model": "turn-text",
            },
            "min_pairing_rate": 0.60,
            "gaps": [],
        },
        "proper_names": [],
    }
    manifest = Manifest(data, Path("test-play.yaml"))
    low = _stage2_with_report(
        monkeypatch,
        tmp_path,
        base,
        manifest,
        slot_reports={"secondary_report.json": {**base, "pairing_rate": 0.50}},
    )
    floor = low["checks"]["turn_text_pairing_floor_secondary"]
    assert floor["ok"] is False
    assert floor["rate"] == 0.50 and floor["floor"] == 0.60
    assert "secondary turn-text pairing rate 0.500 is below the floor 0.600" in floor["error"]
    assert low["ok"] is False

    ok = _stage2_with_report(
        monkeypatch,
        tmp_path,
        base,
        manifest,
        slot_reports={"secondary_report.json": {**base, "pairing_rate": 0.62}},
    )
    assert ok["checks"]["turn_text_pairing_floor_secondary"]["ok"] is True

    private_data = {
        "work": {"id": "test-play", "title": "Test", "author": "aeschylus"},
        "citation": {"scheme": "play-line"},
        "books": [{"n": 1, "start": "1", "end": "3"}],
        "english": {
            "primary": {"id": "smyth", "name": "Smyth", "model": "perseus-play"},
            "secondary": {
                "id": "morshead",
                "name": "Morshead",
                "model": "turn-text",
                "private": True,
            },
            "min_pairing_rate": 0.60,
            "gaps": [],
        },
        "proper_names": [],
    }
    private_manifest = Manifest(private_data, Path("test-play.yaml"))
    skipped = _stage2_with_report(
        monkeypatch,
        tmp_path,
        base,
        private_manifest,
        slot_reports={"secondary_report.json": {**base, "pairing_rate": 0.10}},
    )
    assert "turn_text_pairing_floor_secondary" not in skipped["checks"]
    assert skipped["ok"] is True


def test_stage2_gates_head_unassigned_unless_declared_front_matter(
    tmp_path, monkeypatch
):
    """Astra lane C, F3: opening English dropped before the first pair is gated."""
    base = {
        "work": "test-play",
        "pairing_rate": 0.99,
        "paired": 100,
        "length_ratio_outlier_count": 10,
        "turn_shift_count": 2,
        "turn_shift_rate": 0.02,
        "residual_unassigned": 0,
    }
    lost = _stage2_with_report(
        monkeypatch, tmp_path, {**base, "head_unassigned": 1}, _turn_text_manifest()
    )
    check = lost["checks"]["turn_text_head_unassigned"]
    assert check["ok"] is False
    assert check["count"] == 1
    assert "english.primary.head_front_matter=0" in check["error"]
    assert lost["ok"] is False

    allowed = _stage2_with_report(
        monkeypatch,
        tmp_path,
        {**base, "head_unassigned": 1},
        _turn_text_manifest(head_front_matter=1),
    )
    assert allowed["checks"]["turn_text_head_unassigned"]["ok"] is True

    stale = _stage2_with_report(
        monkeypatch,
        tmp_path,
        {**base, "head_unassigned": 1},
        _turn_text_manifest(head_front_matter=2),
    )
    assert stale["checks"]["turn_text_head_unassigned"]["ok"] is False
    assert "english.head_front_matter=2" in stale["checks"]["turn_text_head_unassigned"]["error"]


def test_manifest_line_fix_repairs_peace_speaker():
    speeches, _notes = _manifest_speeches("peace")
    fixed = [
        speech for speech in speeches
        if speech["speaker_printed"] == "SON OF CLEONYMUS"
        and speech["text"].startswith('"But I saved my life."')
    ]
    assert len(fixed) == 1


def test_blank_source_line_preserves_paragraph_and_turn_offset(tmp_path):
    path = tmp_path / "play.txt"
    path.write_text(
        "TEST PLAY\nALPHA. First paragraph.\n\nSecond paragraph.\n"
        "ALT. Extra speech.\nBETA. Last speech.\nFINIS\n",
        encoding="utf-8",
    )
    spine = {
        "work": "test",
        "segments": [
            {
                "id": "1:1", "book": 1, "column": "1",
                "lines": [{"n": 1, "ref": "1", "text": "Greek one"}],
                "speakers": [{"line": 1, "offset": 0, "label": "Α."}],
            },
            {
                "id": "1:2", "book": 1, "column": "1",
                "lines": [{"n": 2, "ref": "2", "text": "Greek two"}],
                "speakers": [{"line": 2, "offset": 0, "label": "Β."}],
            },
        ],
    }
    english, _footnotes, _report = parse_translation(
        path,
        spine,
        work_id="test",
        translation_id="test",
        play="TEST PLAY",
        sigla={"Α.": "Alpha", "Β.": "Beta"},
        english_aliases={"ALPHA": "Alpha", "ALT": "Alpha", "BETA": "Beta"},
        footnotes_enabled=False,
    )
    first = english["chunks"][0]
    first_speech = "First paragraph.\n\nSecond paragraph."
    assert first["text"] == first_speech + "\n\nExtra speech."
    assert first["turns"][1]["offset"] == len(first_speech) + 2


def test_real_knights_speech_count_and_edge_speakers():
    speeches, _notes = _manifest_speeches("knights")
    assert len(speeches) == 540
    assert speeches[0]["speaker_printed"] == "DEMOSTHENES"
    assert speeches[-1]["speaker_printed"] == "DEMOS"


def test_verse_own_line_format_parses_without_persons_heading():
    text = """AGAMEMNON

WATCHMAN
I pray the gods to quit me of my toils,
To close the watch I keep, this livelong year.

CHORUS
Ten livelong years have rolled away.
"""
    speeches, notes = parse_play_speeches(text, "AGAMEMNON", format="verse-own-line")
    assert notes == {}
    assert [s["speaker_printed"] for s in speeches] == ["WATCHMAN", "CHORUS"]
    assert speeches[0]["text"].startswith("I pray the gods")


# B3 (fix-mechanisms brief, 2026-09-17): Murray's Gutenberg text prints a
# strophe/antistrophe label as editorial apparatus, not spoken text and not
# stage business. It must vanish entirely -- not become a cue, not survive
# as verse, and not become a rendered direction either (agamemnon.txt:1290,
# 1310, 1329, 1348).
def test_verse_own_line_mid_line_strophe_label_is_dropped():
    text = """AGAMEMNON

CHORUS
What is this that evermore, [Strophe 1.
A cold terror at the door
"""
    speeches, _notes = parse_play_speeches(text, "AGAMEMNON", format="verse-own-line", verse=True)
    assert speeches == [
        {
            "speaker_printed": "CHORUS",
            "text": "What is this that evermore,\nA cold terror at the door",
        }
    ]
    assert "Strophe" not in speeches[0]["text"]


def test_verse_own_line_own_line_antistrophe_label_is_dropped_not_a_direction():
    text = """AGAMEMNON

CHORUS
The long galleys took the brine

_[Antistrophe 1._
And in harbour, mine own eye
"""
    speeches, _notes = parse_play_speeches(text, "AGAMEMNON", format="verse-own-line")
    assert speeches == [
        {
            "speaker_printed": "CHORUS",
            "text": "The long galleys took the brine\n\nAnd in harbour, mine own eye",
        }
    ]
    assert "shown" not in speeches[0]
    assert "Antistrophe" not in (speeches[0].get("shown") or "")


def test_verse_own_line_bare_strophe_and_epode_labels_are_dropped():
    text = "AGAMEMNON\n\nCHORUS\nYet that lyreless music hidden\n\n_[Strophe 2._\nWhispers still words of ill,\n\n_[Epode._\nThe Soul unbidden.\n"
    speeches, _notes = parse_play_speeches(text, "AGAMEMNON", format="verse-own-line")
    text_out = speeches[0]["text"]
    assert "Strophe" not in text_out and "Epode" not in text_out
    assert "shown" not in speeches[0]


# B5 (fix-mechanisms brief, 2026-09-17): Johnston's source sometimes prints a
# cue sharing its line with spoken text, `NAME: text`, instead of the usual
# own-line form -- birds.txt:2905 "FIRST MESSENGER: Then, by god, the ducks,
# with slings attached" -- and the own-line-only cue reader missed it,
# folding the speech into the block above and leaving the Greek bare.
def test_verse_own_line_mid_line_colon_cue_is_recognised():
    text = (
        "THE PLAY\n\n"
        "PISTHETAIROS\n"
        "Is there anything we can't do with our feet?\n\n"
        "FIRST MESSENGER: Then, by god, the ducks, with slings attached\n"
        "around their waists, set up the bricks.\n\n"
        "PISTHETAIROS\n"
        "Why should we hire wage labour any more?\n"
    )
    speeches, _notes = parse_play_speeches(
        text,
        "THE PLAY",
        format="verse-own-line",
        known_names={"FIRST MESSENGER", "PISTHETAIROS"},
        verse=True,
    )
    assert speeches[1] == {
        "speaker_printed": "FIRST MESSENGER",
        "text": "Then, by god, the ducks, with slings attached\naround their waists, set up the bricks.",
    }
    assert speeches[2]["speaker_printed"] == "PISTHETAIROS"


# Without a `known_names` entry for the capitalised phrase, the mid-line
# form must never fire -- guarding against an ordinary capitalised aside
# ("NOTE: see above") being mistaken for a cue.
def test_verse_own_line_mid_line_colon_cue_requires_a_known_name():
    text = "THE PLAY\n\nCHORUS\nAs the old proverb goes, NOTE: this changes nothing.\n"
    speeches, _notes = parse_play_speeches(
        text, "THE PLAY", format="verse-own-line", known_names={"CHORUS"}
    )
    assert speeches == [
        {
            "speaker_printed": "CHORUS",
            "text": "As the old proverb goes, NOTE: this changes nothing.",
        }
    ]


# A direction can carry a roster name of its own right after a period --
# oedipus-coloneus.txt:2577 `_[Enter POLYNEICES. He greets ANTIGONE and
# ISMENE first.]_` -- and must never be cut apart looking for an embedded
# cue; a direction is never itself a speaker turn.
def test_verse_own_line_embedded_cue_split_does_not_touch_a_direction_line():
    text = (
        "THE PLAY\n\n"
        "ANTIGONE\n"
        "Here is my father's home.\n\n"
        "_[Enter POLYNEICES. He greets ANTIGONE and ISMENE first.]_\n\n"
        "POLYNEICES\n"
        "My sisters, well beloved.\n"
    )
    speeches, _notes = parse_play_speeches(
        text,
        "THE PLAY",
        format="verse-own-line",
        known_names={"ANTIGONE", "ISMENE", "POLYNEICES"},
    )
    assert speeches[1]["speaker_printed"] == "POLYNEICES"
    assert speeches[1]["directions_before"] == [
        "[Enter POLYNEICES. He greets ANTIGONE and ISMENE first.]"
    ]


# B5 addendum (2026-09-17, electra-eur review finding 3): Murray's Gutenberg
# kommoi run several speakers' half-lines together on one physical line,
# cue and all -- electra-eur.txt:2873 "ORESTES. No more to see thee!
# ELECTRA. Nor thy breath" -- so six Greek turns collapsed into one Murray
# turn and nine segments went bare. The rule guards on a known name exactly
# as the colon form does; Murray's separator is a period.
def test_verse_own_line_run_on_kommos_line_splits_at_each_embedded_cue():
    text = (
        "THE PLAY\n\n"
        "ORESTES\n"
        "Stand thou beside me.\n\n"
        "ORESTES. No more to see thee! ELECTRA. Nor thy breath\n"
        "Be near my face! ORESTES. Ah, so it ends.\n"
    )
    speeches, _notes = parse_play_speeches(
        text, "THE PLAY", format="verse-own-line", known_names={"ORESTES", "ELECTRA"}, verse=True
    )
    assert [(s["speaker_printed"], s["text"]) for s in speeches] == [
        ("ORESTES", "Stand thou beside me."),
        ("ORESTES", "No more to see thee!"),
        ("ELECTRA", "Nor thy breath\nBe near my face!"),
        ("ORESTES", "Ah, so it ends."),
    ]


def test_lindsay_speaker_line_rejects_long_lines_without_hanging():
    # Reproduces a catastrophic-backtracking hang in `_LINDSAY_SPEAKER`: a
    # long, almost-all-caps line that fails to match only at the very end
    # (Arrowsmith's Birds bench text has an all-caps mock-legal decree like
    # this) used to make `.fullmatch()` take minutes. A real speaker cue is
    # always a short name, so a long line short-circuits before the regex.
    long_decree = (
        "BE IT HEREBY PROVIDED THAT IF ANY CLOUD- CUCKOOLANDER SHALL "
        "WILFULLY INJURE OR WRONG ANY CITIZEN OF ATHENS—"
    )
    assert len(long_decree) > 64
    assert _split_lindsay_speaker_line(long_decree) is None
    # Short genuine speaker cues are unaffected.
    assert _split_lindsay_speaker_line("STREPSIADES") == ("STREPSIADES", "")
    assert _split_lindsay_speaker_line("MYRRHINE (_above_)") == ("MYRRHINE", "(_above_)")


# H2 (2026-09-17 round 2 brief, lysistrata finding 2): Lindsay's own generic
# chorus cue only italicises "Chorus of", leaving the group name in ordinary
# ALL CAPS -- `_LINDSAY_SPEAKER`'s ALL-CAPS-only charset cannot match the
# underscores or the lowercase "horus of", so the cue read as body text and
# both parodoi collapsed into a two-line reply (pg7700.txt:1126).
def test_lindsay_chorus_of_cue_with_italic_markers_wrapping_part_of_the_name():
    # The resolved name is the bare group ("WOMEN"/"OLD MEN"), matching the
    # manifest's existing `english_secondary` alias for Lindsay's other
    # bare-group cues -- no manifest change needed to recognise it.
    assert _split_lindsay_speaker_line("_Chorus of_ WOMEN.") == ("WOMEN", "")
    assert _split_lindsay_speaker_line("_Chorus of_ OLD MEN.") == ("OLD MEN", "")


# The SAME opening shape also introduces a stage direction, with more
# italic text after the group name (pg7700.txt:1053) -- that one must stay
# a direction, never a speaker cue, so the pattern only fires when the
# group name is the very last thing on the line.
def test_lindsay_chorus_of_direction_with_trailing_text_is_not_a_cue():
    assert _split_lindsay_speaker_line(
        "_Chorus of_ OLD MEN _enter to attack the captured Acropolis_."
    ) is None


def test_lindsay_speaker_line_rejects_malformed_parens_without_hanging():
    # Codex re-review finding 1 (2026-09-11): moving the length guard AFTER
    # `_LINDSAY_STAGE.search()` left that regex free to backtrack
    # quadratically on a line stuffed with unmatched "(" -- there is no
    # closing ")" anywhere for `[^)]*\)` to land on, so the engine retries
    # the match from every "(" position before giving up. Both shapes below
    # took over 2s pre-fix (`dea35ea` rejected each in under 0.1 ms); the
    # total-length guard now runs before any regex, so each must return
    # promptly regardless of what floods the line.
    malformed = [
        "CHORUS" + " (" * 100000,
        "CHORUS" + " " * 100000 + "(",
    ]
    for line in malformed:
        t0 = time.monotonic()
        result = _split_lindsay_speaker_line(line)
        elapsed = time.monotonic() - t0
        assert result is None
        assert elapsed < 1.0, f"took {elapsed:.3f}s: {line[:20]!r}..."


def test_verse_own_line_body_start_accepts_a_short_interjection_and_a_caps_shout():
    # Codex review finding 6 (2026-09-11): `_body_start`'s speech-body check
    # requires >=5 words or >=40 chars AND a lowercase letter, so it skips
    # past a genuine one-word interjection ("Yaaaahhuuuuu.") and a shouted
    # all-caps line (Arrowsmith writes some dialogue in solid caps -- see
    # `test_genie_html_folds_shouted_caps_line...`) and locks onto a LATER
    # speech instead. There is no dramatis-personae list in this format to
    # guard against (the docstring: verse-own-line has none to auto-detect),
    # so any real line right after the title is body text.
    text = """THE CLOUDS

STREPSIADES
Yaaaahhuuuuu.
Great Zeus Almighty, what an endless monster of a night it's been!

PHEIDIPPIDES
PHILO,
YOU FOULED ME! KEEP IN YOUR OWN LANE!

STREPSIADES
That's it.
That's the horsey blight that has blasted me dead.
"""
    speeches, _notes = parse_play_speeches(text, "THE CLOUDS", format="verse-own-line")
    assert speeches[0]["speaker_printed"] == "STREPSIADES"
    assert speeches[0]["text"].startswith("Yaaaahhuuuuu.")
    assert [s["speaker_printed"] for s in speeches] == [
        "STREPSIADES",
        "PHEIDIPPIDES",
        "STREPSIADES",
    ]


def test_lindsay_speaker_line_bounds_only_the_name_not_the_stage_direction():
    # Codex review finding 5 (2026-09-11): the length guard counted the
    # parenthetical direction too, so a genuine cue with a long stage
    # direction (over 64 chars in all) was rejected. Only the NAME needs
    # bounding against the hang above; the direction is already split off
    # by `_LINDSAY_STAGE` by the time the guard runs.
    cue = "CHORUS (_turning to the audience and raising both hands toward the sky_)."
    assert len(cue) > 64
    assert _split_lindsay_speaker_line(cue) == (
        "CHORUS",
        "(_turning to the audience and raising both hands toward the sky_)",
    )


def test_lindsay_own_line_speakers_keep_optional_period_path():
    text = """LYSISTRATA
The Persons of the drama.

Scene: Athens.

LYSISTRATA
This is the first speech in the play.

CALONICE.
This is the second speech in the play.

MYRRHINE (_above_)
This is the third speech in the play.

FINIS
"""
    speeches, notes = parse_play_speeches(text, "LYSISTRATA")
    assert speeches == [
        {
            "speaker_printed": "LYSISTRATA",
            "text": "This is the first speech in the play.",
        },
        {
            "speaker_printed": "CALONICE",
            "text": "This is the second speech in the play.",
        },
        {
            "speaker_printed": "MYRRHINE",
            "text": "(above) This is the third speech in the play.",
        },
    ]
    assert notes == {}


def test_real_lindsay_lysistrata_speech_count_and_edge_speakers():
    text = (SOURCES_DIR / "gutenberg/pg7700.txt").read_text(encoding="utf-8")
    speeches, notes = parse_play_speeches(text, "LYSISTRATA")
    assert notes == {}
    # H2 (2026-09-17 round 2): `_Chorus of_ WOMEN.` (pg7700.txt:1126) now
    # opens its own speech instead of reading as the tail of whichever turn
    # was still open -- one more speech than the pre-fix count encoded.
    assert len(speeches) == 538
    assert speeches[0]["speaker_printed"] == "LYSISTRATA"
    assert speeches[-1]["speaker_printed"] == "SPARTANS"
    printed = {speech["speaker_printed"] for speech in speeches}
    assert "MYRRHINE" in printed
    assert "STRATYLLIS" in printed
    assert "O" not in printed
    assert "WOMEN" in printed
    groaning = [
        speech
        for speech in speeches
        if speech["speaker_printed"] == "CINESIAS" and "O...." in speech["text"]
    ]
    assert len(groaning) == 1
    staged = [
        speech
        for speech in speeches
        if speech["speaker_printed"] == "MYRRHINE"
        and speech["text"].startswith("(above)")
    ]
    assert len(staged) == 1


LOEB_OCR = """ANTIGONE

ANTIGONE. Ismene, sister of my blood and heart,
See'st thou how Zeus would in our lives fulfil
the weird of Oedipus.

ISMENE. To me, Antigone, no word of friends
has come.

CHORUS. Sunbeam, of all that ever dawned upon
our seven-gated Thebes.

CREON. Sirrah, begone.
END OF VOL. I.
"""


def test_loeb_ocr_format_parses_name_dot_text(tmp_path):
    path = tmp_path / "antigone.txt"
    path.write_text(LOEB_OCR, encoding="utf-8")
    spine = _antigone_spine()
    english, footnotes, report = parse_translation(
        path,
        spine,
        work_id="antigone",
        translation_id="storr",
        play="ANTIGONE",
        sigla={"ΑΝ.": "Antigone", "ΙΣ.": "Ismene", "Χο.": "Chorus", "ΚΡ.": "Creon"},
        english_aliases={
            "ANTIGONE": "Antigone",
            "ISMENE": "Ismene",
            "CHORUS": "Chorus",
            "CREON": "Creon",
        },
        footnotes_enabled=False,
        format="loeb-ocr",
    )
    printed = [t["display"] for c in english["chunks"] for t in c.get("turns") or []]
    assert printed[:4] == ["ANTIGONE", "ISMENE", "CHORUS", "CREON"]
    assert footnotes == {}
    assert "END OF VOL" not in english["chunks"][-1]["text"]
    assert report["speeches_parsed"] == 4


# Way's Loeb footnotes as popups (John, 2026-09-14): loeb-ocr notes are
# moved out of the verse into a `Footnotes:` block (`[k] text` per note,
# mirroring the Gutenberg `_parse_notes` shape) and a `[k]` marker is left
# in the verse at the word each note glosses.
LOEB_OCR_WITH_FOOTNOTES = """ANTIGONE

ANTIGONE. Ismene, sister of my blood and heart,
See'st thou how Zeus would in our lives fulfil
the weird[1] of Oedipus.

ISMENE. To me, Antigone, no word of friends
has come.

CHORUS. Sunbeam[2], of all that ever dawned upon
our seven-gated Thebes.

CREON. Sirrah, begone.

Footnotes:
[1] i.e. destined fate.
[2] Addressed to the rising sun.
"""


def test_loeb_ocr_footnotes_block_parsed_into_notes_and_markers(tmp_path):
    """Before the 2026-09-14 fix, ``format="loeb-ocr"`` never called
    ``_parse_notes`` -- ``parse_play_speeches`` always returned ``{}`` for
    notes, and ``_parse_as_speeches`` had no stopping condition for a
    ``Footnotes:`` line, so the block's raw text (the ``Footnotes:`` header
    and every ``[k] ...`` line) was swallowed into Creon's speech instead of
    ending it there. This must fail on that code: ``notes`` was empty, and
    the note bodies were part of a speech's text."""
    speeches, notes = parse_play_speeches(LOEB_OCR_WITH_FOOTNOTES, "ANTIGONE", format="loeb-ocr")
    assert notes == {
        "1": "i.e. destined fate.",
        "2": "Addressed to the rising sun.",
    }
    assert len(speeches) == 4
    assert speeches[-1]["speaker_printed"] == "CREON"
    assert speeches[-1]["text"] == "Sirrah, begone."
    for speech in speeches:
        assert "Footnotes:" not in speech["text"]
        assert "destined fate" not in speech["text"]
        assert "rising sun" not in speech["text"]


def test_loeb_ocr_footnote_marker_glued_before_punctuation_becomes_popup(tmp_path):
    """A ``[k]`` marker glued directly onto a word, with no space before the
    punctuation that follows it (Way's own style once the OCR remnant of his
    superscript is removed, e.g. ``heifer-maid[1] !``), must survive
    ``_rewrite_footnotes`` as ``[^seq.k]`` in the same place, and the note
    text must reach the ``footnotes`` map keyed by that same label."""
    path = tmp_path / "antigone.txt"
    path.write_text(LOEB_OCR_WITH_FOOTNOTES, encoding="utf-8")
    english, footnotes, _report = parse_translation(
        path,
        _antigone_spine(),
        work_id="antigone",
        translation_id="way",
        play="ANTIGONE",
        sigla={"ΑΝ.": "Antigone", "ΙΣ.": "Ismene", "Χο.": "Chorus", "ΚΡ.": "Creon"},
        english_aliases={
            "ANTIGONE": "Antigone",
            "ISMENE": "Ismene",
            "CHORUS": "Chorus",
            "CREON": "Creon",
        },
        footnotes_enabled=True,
        format="loeb-ocr",
    )
    all_text = " ".join(c["text"] for c in english["chunks"])
    assert "the weird[^1.1] of Oedipus" in all_text
    assert "Sunbeam[^2.2], of all" in all_text
    assert footnotes == {
        "1.1": "i.e. destined fate.",
        "2.2": "Addressed to the rising sun.",
    }


# Sol review finding 4 (2026-09-16): `_parse_as_speeches` (the loeb-ocr model
# path) had no direction handling at all, so a restored stage direction on a
# line of its own -- `[Enter TECMESSA.]`, `_Flights of birds are seen
# approaching._` -- was swallowed into whichever speech was still open,
# becoming spoken verse. Both the Storr bracket form and the Way underscore
# form must now read as a direction and land on the *next* speech's
# `directions_before`, never inside any speech's text.
LOEB_OCR_DIRECTIONS = """THE PLAY

[The scene opens.]
ANTIGONE. Ismene, sister of my blood.
_She turns slowly._
See'st thou how Zeus would fulfil.
[Ismene enters.]

ISMENE. To me no word of friends has come.

CHORUS. Sunbeam of all that dawned.
"""


def test_loeb_ocr_directions_are_not_swallowed_into_speech_text():
    speeches, _notes = parse_play_speeches(LOEB_OCR_DIRECTIONS, "THE PLAY", format="loeb-ocr")
    assert speeches == [
        {
            "speaker_printed": "ANTIGONE",
            "text": "Ismene, sister of my blood. See'st thou how Zeus would fulfil.",
            "directions_before": ["The scene opens."],
        },
        {
            "speaker_printed": "ISMENE",
            "text": "To me no word of friends has come.",
            # Both the mid-speech underscore direction and the one after
            # Antigone's last line defer to the next speech, in order.
            "directions_before": ["She turns slowly.", "Ismene enters."],
        },
        {"speaker_printed": "CHORUS", "text": "Sunbeam of all that dawned."},
    ]
    for speech in speeches:
        assert "scene opens" not in speech["text"]
        assert "turns slowly" not in speech["text"]
        assert "Ismene enters" not in speech["text"]


def test_loeb_ocr_bracket_direction_keeps_trailing_period_off_the_next_speech():
    # Ajax bench form: `[Exeunt.]` (period inside the brackets).
    text = "THE PLAY\n\nCHORUS. Ready am I.\n[Exeunt.]\n\nAJAX. The slayer standeth.\n"
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr")
    assert speeches[0] == {"speaker_printed": "CHORUS", "text": "Ready am I."}
    assert speeches[1] == {
        "speaker_printed": "AJAX",
        "text": "The slayer standeth.",
        "directions_before": ["Exeunt."],
    }


# Codex merge-gate finding 2 (2026-09-16): a stage direction that opens a
# verse line in brackets, with the spoken words following it on the same
# line, kept printing as speech -- Way's Andromache 660, `[To attendant]
# Lead the way faster!` -- because `_loeb_direction` only read a direction
# that filled the whole line. The leading bracket must now split off, the
# cue attaching to the open speech's `shown` and the words riding on as its
# next verse line.
def test_loeb_ocr_leading_bracket_direction_splits_off_the_verse_line():
    text = (
        "THE PLAY\n\n"
        "PELEUS. Menelaus, hold! Press not where justice bars.\n"
        "[To attendant] Lead the way faster!\n"
    )
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert speeches == [
        {
            "speaker_printed": "PELEUS",
            "text": "Menelaus, hold! Press not where justice bars.\nLead the way faster!",
            "shown": "Menelaus, hold! Press not where justice bars.\n_To attendant_\nLead the way faster!",
        }
    ]


# Sol re-check finding 6 (2026-09-16): a leading bracketed direction on the
# *cue* line itself -- way/heraclidae.txt:348, `CHORUS. [To HERALD] Depart
# thou :--touch thou not this man,` -- was never split at all. The cue
# branch appended the speaker-line regex's whole `rest` group straight into
# `parts`, so `[To HERALD]` rode into the spoken text; only a *continuation*
# line got `_split_leading_direction`/`_split_trailing_direction`.
def test_loeb_ocr_leading_bracket_direction_on_the_cue_line_splits_off():
    text = (
        "THE PLAY\n\n"
        "CHORUS. [To HERALD] Depart thou :—touch thou not this man,\n"
        "O king.\n"
    )
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert speeches == [
        {
            "speaker_printed": "CHORUS",
            "text": "Depart thou :—touch thou not this man,\nO king.",
            "shown": "_To HERALD_\nDepart thou :—touch thou not this man,\nO king.",
        }
    ]
    assert "[To HERALD]" not in speeches[0]["text"]


# The Loeb habit is to never close the bracket at all -- Cyclops 538,
# `... make your host good\ncheer. [Begins to drive the crew in.` -- so the
# trailing form must split on an unclosed bracket too. At the very end of a
# speech (nothing follows on the same or a later line) it rides forward as
# the next speech's `directions_before`, exactly like a whole-line direction.
def test_loeb_ocr_trailing_bracket_direction_rides_to_next_speech():
    text = (
        "THE PLAY\n\n"
        "CHORUS. Ready am I,\n"
        "and glad of cheer. [Begins to drive the crew in.\n\n"
        "ODYSSEUS. And perils of the sea, only to run.\n"
    )
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert speeches == [
        {"speaker_printed": "CHORUS", "text": "Ready am I,\nand glad of cheer."},
        {
            "speaker_printed": "ODYSSEUS",
            "text": "And perils of the sea, only to run.",
            "directions_before": ["Begins to drive the crew in."],
        },
    ]


def test_loeb_ocr_trailing_bracket_direction_may_close():
    # oedipus-coloneus.txt:710 form, bracket closed but no trailing period:
    # `... is of no account. [Exit ISMENE.`. Bench text never closes it, but
    # the split must accept either.
    text = "THE PLAY\n\nISMENE. I go, and thou must guard our father.\nToil is of no account. [Exit ISMENE.]\n\nCHORUS. Ill is it, stranger.\n"
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert speeches[0]["text"] == "I go, and thou must guard our father.\nToil is of no account."
    assert speeches[1] == {
        "speaker_printed": "CHORUS",
        "text": "Ill is it, stranger.",
        "directions_before": ["Exit ISMENE."],
    }


# B6 (fix-mechanisms brief, 2026-09-17): a Loeb volume prints its editorial
# appendix -- fragments, textual notes -- after the play's last verse line,
# under an "APPENDIX" heading; the parser read straight through it into the
# Chorus's closing turn (way/bacchae.txt:1823).
def test_loeb_ocr_stops_at_the_appendix_heading():
    text = (
        "THE PLAY\n\n"
        "CHORUS. O the works of the Gods—in manifold wise they reveal them.\n\n"
        'APPENDIX TO THE "BACCHANALS."\n\n'
        "A few fragments, given below, of the lost close of the play.\n"
    )
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert speeches == [
        {
            "speaker_printed": "CHORUS",
            "text": "O the works of the Gods—in manifold wise they reveal them.",
        }
    ]
    assert "APPENDIX" not in speeches[0]["text"]
    assert "fragments" not in speeches[0]["text"]


# B1 (fix-mechanisms brief, 2026-09-17): a Loeb verse line too long for the
# printed column wraps, and its tail was never rejoined -- it survived into
# the build as a whole line of its own. A Loeb verse line always opens with a
# capital (or an opening quote/bracket ahead of one; confirmed against
# storr/antigone.txt:391-432 and way/bacchae.txt), so a line that opens
# lowercase instead is the wrapped tail of the line above it. Antigone's Ode
# to Man (storr/antigone.txt:391-432): "Many wonders there be, but naught
# more wondrous" / "than man :" must rejoin as one line.
def test_loeb_ocr_hanging_turnover_without_bracket_rejoins_the_wrapped_line():
    text = (
        "THE PLAY\n\n"
        "CHORUS. Many wonders there be, but naught more wondrous\n"
        "than man :\n"
        "Over the surging sea, with a whitening south wind\n"
        "wan,\n"
    )
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert speeches == [
        {
            "speaker_printed": "CHORUS",
            "text": (
                "Many wonders there be, but naught more wondrous than man :\n"
                "Over the surging sea, with a whitening south wind wan,"
            ),
        }
    ]


# oedipus-tyrannus.txt:426-427, a second instance of the same shape, with two
# wraps in one speech.
def test_loeb_ocr_hanging_turnover_rejoins_across_several_wraps():
    text = (
        "THE PLAY\n\n"
        "OEDIPUS. Will nothing loose thy tongue? Can nothing melt\n"
        "thee,\n"
        "Nor breed compassion? Thou dost still hold back.\n"
        "the secret.\n"
    )
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert speeches == [
        {
            "speaker_printed": "OEDIPUS",
            "text": (
                "Will nothing loose thy tongue? Can nothing melt thee,\n"
                "Nor breed compassion? Thou dost still hold back. the secret."
            ),
        }
    ]


# A legitimate mid-speech line never opens lowercase in these Loeb benches
# (confirmed against the corpus), so the rejoin rule must not need a length
# heuristic to tell a real short verse line from a tail -- but it must leave
# an ordinary, capitalised short line alone.
def test_loeb_ocr_short_capitalised_line_is_not_treated_as_a_turnover():
    text = "THE PLAY\n\nCHORUS. Ah me!\nWoe is me.\n"
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert speeches == [
        {"speaker_printed": "CHORUS", "text": "Ah me!\nWoe is me."}
    ]


# G2 (Grok's round-2 read, 2026-09-17): Rule A also glued a 1-3 letter OCR
# orphan onto the end of an already-complete sentence -- "one"
# (storr/antigone.txt:170), "to"/"a" (storr/electra-soph.txt:1211,1331) --
# none of them a genuine turnover. A candidate under four characters is
# never merged, whatever the length of the line before it.
def test_loeb_ocr_short_orphan_after_a_finished_sentence_is_not_merged():
    text = (
        "THE PLAY\n\n"
        "CHORUS. And with a river always at its edge of ample flowing water.\n"
        "one\n"
        "More lines follow the orphan.\n"
    )
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert speeches == [
        {
            "speaker_printed": "CHORUS",
            "text": (
                "And with a river always at its edge of ample flowing water.\n"
                "one\n"
                "More lines follow the orphan."
            ),
        }
    ]


# Bacchae's shape (finding 4, 2026-09-17) is a *different* turnover: the
# Loeb column set a short line's overflow to the right of the *next*,
# unrelated line, so the OCR glues an unclosed `[...` tail onto the end of
# the line ABOVE the one it continues. way/bacchae.txt:78-79: "...to my
# painless toil [with greeting." / "For the Clamour-king, hailing the
# Bacchanals' God" reads correctly only when "with greeting." moves onto the
# end of the second line -- "hailing the Bacchanals' God with greeting."
def test_loeb_ocr_bracket_tail_moves_to_the_following_line():
    text = (
        "THE PLAY\n\n"
        "CHORUS. From Asian soil\n"
        "Far over the hallowed ridges of Tmolus fleeting,\n"
        "To the task that I love do I speed, to my painless toil [with greeting.\n"
        "For the Clamour-king, hailing the Bacchanals' God\n"
    )
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert speeches == [
        {
            "speaker_printed": "CHORUS",
            "text": (
                "From Asian soil\n"
                "Far over the hallowed ridges of Tmolus fleeting,\n"
                "To the task that I love do I speed, to my painless toil\n"
                "For the Clamour-king, hailing the Bacchanals' God with greeting."
            ),
        }
    ]
    assert "[with greeting" not in speeches[0]["text"]


# A recognised direction cue in a trailing bracket (`Enter`/`Exit`/`To `/...)
# is `_split_trailing_direction`'s, not the bracket-tail turnover's -- the
# two must not collide.
def test_loeb_ocr_bracket_tail_does_not_swallow_a_real_trailing_direction():
    text = (
        "THE PLAY\n\n"
        "CHORUS. Ready am I,\n"
        "and glad of cheer. [Begins to drive the crew in.\n\n"
        "ODYSSEUS. And perils of the sea, only to run.\n"
    )
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert speeches[0] == {"speaker_printed": "CHORUS", "text": "Ready am I,\nand glad of cheer."}
    assert speeches[1]["directions_before"] == ["Begins to drive the crew in."]


# G1 (round 2, Grok finding 1, 2026-09-17): a wrap-tail line (Rule A) can
# itself carry a Rule B trailing bracket tail meant for the line after it.
# Rule A used to run first and swallow the whole line -- bracket and all --
# before Rule B ever peeled the tail off (way/cyclops.txt:60-62: "...
# bedraggled" / "with the dew. [rascal! Shoo!" / "Here goes a stone ...
# wilful"). The tail must move to the end of the following line and the
# raw `[` must not survive into the joined verse.
def test_loeb_ocr_wrap_tail_line_also_carrying_a_bracket_tail_peels_it_first():
    text = (
        "THE PLAY\n\n"
        "CHORUS. A bedraggled and drenched and thoroughly dishevelled goat,\n"
        "with the dew. [rascal! Shoo!\n"
        "Here goes a stone at the most wilful goat of the herd.\n"
    )
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert speeches == [
        {
            "speaker_printed": "CHORUS",
            "text": (
                "A bedraggled and drenched and thoroughly dishevelled goat, with the dew.\n"
                "Here goes a stone at the most wilful goat of the herd. rascal! Shoo!"
            ),
        }
    ]
    assert "[" not in speeches[0]["text"]


# Guard against the real false-positive risk (grep of every Way/Storr bench
# file, 2026-09-16): Storr's Sophocles verse also uses a bare parenthesis for
# a rhetorical aside inside the line itself, not a stage direction --
# electra-soph.txt:57, `(So let thy tale run) at the Pythian games.` A
# leading/trailing bracket only reads as a direction for a recognised cue
# (`To ...`, `Aside`, `Enter`/`Exit`/`Exeunt`, `Begins`); an ordinary
# parenthetical remark must stay exactly where it was printed.
def test_loeb_ocr_leading_parenthetical_aside_is_not_a_direction():
    text = (
        "THE PLAY\n\n"
        "ORESTES. Say thou hast perished at the Pythian games,\n"
        "(So let thy tale run) at the Pythian games.\n"
    )
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert speeches == [
        {
            "speaker_printed": "ORESTES",
            "text": "Say thou hast perished at the Pythian games,\n(So let thy tale run) at the Pythian games.",
        }
    ]


# B2 (fix-mechanisms brief, 2026-09-17): Way cues the god's off-stage
# utterances in mixed case with a parenthetical location -- `Dionysus
# (within).` -- instead of the usual all-caps `NAME.`, so `_SPEAKER_LINE`
# never saw a cue and the lines were swallowed into the surrounding Chorus
# speech (way/bacchae.txt:675, 689, 704).
def test_loeb_ocr_offstage_mixed_case_cue_is_recognised():
    text = (
        "THE PLAY\n\n"
        "CHORUS. Spread fatness on every hand.\n"
        "Dionysus (within).\n"
        "What ho! Give heed to my voice, give heed !\n"
        "\n"
        "CHORUS. What cry was it?\n"
    )
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert speeches[0] == {"speaker_printed": "CHORUS", "text": "Spread fatness on every hand."}
    assert speeches[1] == {
        "speaker_printed": "DIONYSUS",
        "text": "What ho! Give heed to my voice, give heed !",
    }
    assert speeches[2]["speaker_printed"] == "CHORUS"


# The OCR sometimes glues a stray ". " onto the front of the cue
# (way/bacchae.txt:675: ". Dionysus (within).") and sometimes drops the
# trailing period (:689: "Dionysus (within)"); both must still read as a cue.
def test_loeb_ocr_offstage_cue_tolerates_stray_leading_dot_and_missing_period():
    text = (
        "THE PLAY\n\n"
        "CHORUS. Our Lord!\n"
        ". Dionysus (within).\n"
        "Earth-floor, sway to and fro!\n"
        "\n"
        "CHORUS. Ha, swiftly shall fall!\n"
        "Dionysus (within)\n"
        "Kindle the torch.\n"
    )
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert speeches[1] == {"speaker_printed": "DIONYSUS", "text": "Earth-floor, sway to and fro!"}
    assert speeches[3] == {"speaker_printed": "DIONYSUS", "text": "Kindle the torch."}


# B2 addendum (2026-09-17, oedipus-coloneus review finding 3): Storr's OCR
# sometimes writes the cue as `NAME :` (a space then a colon) instead of
# `NAME.`, alone on its own line -- oedipus-coloneus.txt:82 `STRANGER :`,
# :763 `CHORUS :` -- and the whole speech that follows was folded into the
# turn above.
def test_loeb_ocr_space_colon_cue_is_recognised():
    text = (
        "THE PLAY\n\n"
        "OEDIPUS. How call you then the place wherein we bide?\n"
        "STRANGER :\n"
        "Whate’er I know thou too shalt know ; the place\n"
        "Is all to great Poseidon consecrate.\n"
    )
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert speeches[0]["speaker_printed"] == "OEDIPUS"
    assert speeches[1] == {
        "speaker_printed": "STRANGER",
        "text": "Whate’er I know thou too shalt know ; the place\nIs all to great Poseidon consecrate.",
    }


def test_loeb_ocr_space_colon_cue_second_instance():
    text = "THE PLAY\n\nOEDIPUS. Too true.\nCHORUS :\nOh horror!\n\nOEDIPUS. Horrors from the deep.\n"
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert speeches[1] == {"speaker_printed": "CHORUS", "text": "Oh horror!"}


# H4 (2026-09-17 round 2 brief, helen finding 5): a Way cue whose OCR
# slipped one letter to lowercase at the very end, its own stage direction
# on the SAME line and no terminating period at all -- the speech starts on
# the next physical line (way/helen.txt:1902-1903). `_SPEAKER_LINE`'s name
# charset is ALL-CAPS only and always needs a "."/" :" terminator, so this
# used to glue onto the end of the previous speaker's turn.
def test_loeb_ocr_case_slip_cue_with_stage_direction_and_no_period():
    text = (
        "THE PLAY\n\n"
        "HELEN. Now bid one give a ship wherein to bear\n"
        "The gifts, that so thy kindness may be full.\n"
        "THEOCLYMENUs (to attendant)\n"
        "Of fifty oars, and rowers therewithal.\n"
        "\n"
        "HELEN. The rites who ordereth, shall not he command ?\n"
    )
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert speeches[1] == {
        "speaker_printed": "THEOCLYMENUS",
        "text": "Of fifty oars, and rowers therewithal.",
        "shown": "_to attendant_\nOf fifty oars, and rowers therewithal.",
    }
    assert speeches[2]["speaker_printed"] == "HELEN"


# B round 3 item 4 (suppliants-eur finding 5, 2026-09-17): a Loeb cue whose
# own line ends in a comma instead of the usual period or " :"
# ("SECOND MOTHER,", bare on its own line) was not recognised as a cue at
# all, and its speech welded onto the previous speaker's turn.
def test_loeb_ocr_comma_terminated_cue_is_recognised():
    text = (
        "THE PLAY\n\n"
        "SECOND CHILD. They are gone! No sons hast thou any more.\n"
        "SECOND MOTHER,\n"
        "They crumbled to ashes mid flame as they lay,\n"
        "And to Hades now have they winged their way.\n"
        "\n"
        "THIRD CHILD. O my father.\n"
    )
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert speeches[0]["speaker_printed"] == "SECOND CHILD"
    assert speeches[1] == {
        "speaker_printed": "SECOND MOTHER",
        "text": "They crumbled to ashes mid flame as they lay,\nAnd to Hades now have they winged their way.",
    }
    assert speeches[2]["speaker_printed"] == "THIRD CHILD"


# B round 3 item 4 (heracles finding 6, 2026-09-17): a Loeb ode's own
# editorial rubric -- a Roman-numeral list heading ("I. The Nemean Lion")
# or a short strophe/antistrophe tag ("- (Ant, 3)") -- printed mid-speech,
# between stanzas, used to survive into the built verse as if it were
# translated text.
def test_loeb_ocr_ode_rubric_dropped_between_stanzas():
    text = (
        "THE PLAY\n\n"
        "CHORUS. The Lay of the Labours of Hercules\n"
        "Hard on the pean triumphant-ringing.\n"
        "I. The Nemean Lion\n"
        "In Zeus' glen first, in the Lion's lair,\n"
        "II. The Centaurs\n"
        "Then on the mountain-haunters raining.\n"
        "- (Ant, 3)\n"
        "As maids of Delos chant the paean's holy strain.\n"
    )
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert len(speeches) == 1
    assert speeches[0]["speaker_printed"] == "CHORUS"
    text_out = speeches[0]["text"]
    assert "Nemean Lion" not in text_out
    assert "Centaurs" not in text_out
    assert "(Ant, 3)" not in text_out
    assert text_out == (
        "The Lay of the Labours of Hercules\n"
        "Hard on the pean triumphant-ringing.\n"
        "In Zeus' glen first, in the Lion's lair,\n"
        "Then on the mountain-haunters raining.\n"
        "As maids of Delos chant the paean's holy strain."
    )


# B round 3 item 4 (phoenician-women finding 8, 2026-09-17): the same
# rubric, embedded at the END of an otherwise real verse line instead of
# alone on its own -- "...Cadmus speeding (Str)", "...Cithaeron (Ant.)",
# "...light (Mesode)", "...shield-array (Ani, 2)" ("Ani" the OCR's own slip
# for "Ant") -- must be stripped, keeping the line's real text.
def test_loeb_ocr_trailing_ode_rubric_is_stripped_from_a_real_verse_line():
    text = (
        "THE PLAY\n\n"
        "CHORUS. To this land from Phoenicia Cadmus speeding (Str)\n"
        "Gorges mysterious of frondage, Cithaeron (Ant.)\n"
        "Hail, rock that flashest a splendour of light (Mesode)\n"
        "Round the town a shield-array (Ani, 2)\n"
    )
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert len(speeches) == 1
    text_out = speeches[0]["text"]
    assert "(Str)" not in text_out and "(Ant.)" not in text_out
    assert "(Mesode)" not in text_out and "(Ani, 2)" not in text_out
    assert text_out == (
        "To this land from Phoenicia Cadmus speeding\n"
        "Gorges mysterious of frondage, Cithaeron\n"
        "Hail, rock that flashest a splendour of light\n"
        "Round the town a shield-array"
    )


# Same item: a lone OCR guillemet, alone on its own line
# (phoenician-women.txt:1757), is pure scan noise with no text to salvage.
def test_loeb_ocr_lone_guillemet_line_is_dropped():
    text = (
        "THE PLAY\n\n"
        "CHORUS. With spears they lunged: yet crouched behind their shields,\n"
        "»\n"
        "That so the steel might bootless glance aside.\n"
    )
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert len(speeches) == 1
    assert "»" not in speeches[0]["text"]
    assert speeches[0]["text"] == (
        "With spears they lunged: yet crouched behind their shields,\n"
        "That so the steel might bootless glance aside."
    )


# B round 3 item 4 (cyclops finding 4, 2026-09-17): a bracketed stage
# direction spanning two lines, whose first line names a speaking character
# rather than opening with one of the stock direction verbs
# ("[SILENUS comes out of cave, artistically made up as victim /
# of assault and battery.]") -- `_UNCLOSED_DIRECTION` only recognises an
# unclosed "[" when it opens on a verb, so this fell through as two raw
# verse lines instead of becoming a direction.
def test_loeb_ocr_two_line_bracket_direction_opening_on_a_known_name():
    text = (
        "THE PLAY\n\n"
        "SILENUS. Here in my caves and with plaited withs about.\n"
        "[SILENUS comes out of cave, artistically made up as victim\n"
        "of assault and battery.]\n"
        "\n"
        "SILENUS. Oh! oh! They've pummelled me into a fever!\n"
    )
    speeches, _notes = parse_play_speeches(
        text, "THE PLAY", format="loeb-ocr", verse=True, known_names={"SILENUS"}
    )
    assert len(speeches) == 2
    assert speeches[0]["text"] == "Here in my caves and with plaited withs about."
    assert "SILENUS comes out" not in speeches[0]["text"]
    assert speeches[1]["directions_before"] == [
        "SILENUS comes out of cave, artistically made up as victim of assault and battery."
    ]
    assert speeches[1]["text"] == "Oh! oh! They've pummelled me into a fever!"


# Same item: an unclosed "[" that never closes within the line cap (Way's
# Cyclops has several genuine run-on verse fragments shaped like this) must
# not be swallowed as a direction just because its first word happens to be
# a known character's name -- a real "]" must actually turn up nearby.
def test_loeb_ocr_bracket_opening_on_a_name_but_never_closing_is_left_alone():
    text = (
        "THE PLAY\n\n"
        "SILENUS. Watch well.\n"
        "[CYCLOPS shows corner of skin, an old wound gapes\n"
        "beneath the rags he wears, and never a bracket comes\n"
        "to close it, line after line after line running on\n"
        "well past the cap this rule allows before it gives up\n"
        "\n"
        "CYCLOPS. What ails you now?\n"
    )
    speeches, _notes = parse_play_speeches(
        text, "THE PLAY", format="loeb-ocr", verse=True, known_names={"SILENUS", "CYCLOPS"}
    )
    assert speeches[0]["speaker_printed"] == "SILENUS"
    assert "CYCLOPS shows corner of skin" in speeches[0]["text"]
    assert not speeches[0].get("directions_before")


# B round 3 item 5 (phoenician-women finding 1, 2026-09-17): a cue-less
# block that follows an "_Enter NAME._" direction used to weld onto the
# previous speaker's turn instead of opening NAME's own -- the whole
# parodos glued into the Old Servant's nine-line speech.
def test_loeb_ocr_cueless_block_after_enter_direction_opens_the_entrants_turn():
    text = (
        "THE PLAY\n\n"
        "OLD SERVANT. Daughter, pass in, and 'neath the roofs abide.\n"
        "\n"
        "_Exeunt OLD SERVANT and ANTIGONE._\n"
        "\n"
        "_Enter CHORUS._\n"
        "\n"
        "Afar from the tides against Tyre's walls swelling,\n"
        "For Loxias chosen an offering,\n"
    )
    speeches, _notes = parse_play_speeches(
        text, "THE PLAY", format="loeb-ocr", verse=True, known_names={"OLD SERVANT", "CHORUS"}
    )
    assert [s["speaker_printed"] for s in speeches] == ["OLD SERVANT", "CHORUS"]
    assert speeches[1]["text"] == (
        "Afar from the tides against Tyre's walls swelling,\nFor Loxias chosen an offering,"
    )
    assert speeches[1]["directions_before"] == [
        "Exeunt OLD SERVANT and ANTIGONE.",
        "Enter CHORUS.",
    ]


# Same item: "Enter X and Y" names two entrants and cannot say which one
# opens the next cue-less block, so it is left alone (welds as before)
# rather than guessed.
def test_loeb_ocr_enter_two_names_is_not_treated_as_an_implicit_cue():
    text = (
        "THE PLAY\n\n"
        "OLD SERVANT. Daughter, pass in, and 'neath the roofs abide.\n"
        "\n"
        "_Enter CHORUS and ATTENDANTS._\n"
        "\n"
        "Afar from the tides against Tyre's walls swelling,\n"
    )
    speeches, _notes = parse_play_speeches(
        text, "THE PLAY", format="loeb-ocr", verse=True, known_names={"OLD SERVANT", "CHORUS"}
    )
    assert len(speeches) == 1
    assert speeches[0]["speaker_printed"] == "OLD SERVANT"
    assert "Afar from the tides" in speeches[0]["text"]


# B round 3b item 2 (Grok's read of 5f58b39, review-lane-b-r3-grok-findings.md
# finding 3, 2026-09-18): the parser has no Greek, so `implicit_entrant`
# cannot tell an entrance that truly opens the entrant's own turn from one
# that doesn't -- it just guesses from the English. `parse_translation` DOES
# have the Greek, and now settles the guess with a trial alignment: the
# split stands only if the speech it created lands on a genuine Greek
# speaker event of the same name; otherwise it is folded back onto the
# speech before it. way/alcestis.txt:41 ("_Enter DEATH._" mid-Apollo's own
# speech, Death's real cue several lines later) is the shape that must be
# rejected.
def test_loeb_ocr_implicit_entrant_stays_with_the_current_speaker_when_the_greek_disagrees(tmp_path):
    path = tmp_path / "play.txt"
    path.write_text(
        "THE PLAY\n\n"
        "APOLLO. Go forth of yonder hall's beloved roof, I lest pollution taint "
        "me in their house.\n"
        "\n"
        "_Enter DEATH._\n"
        "\n"
        "Lo, yonder Death; I see him nigh at hand, priest of the dead, who comes "
        "to hale her down to Hades halls.\n"
        "\n"
        "DEATH. Ha, thou at the palace! Wilt not make room?\n",
        encoding="utf-8",
    )
    spine = {
        "work": "test",
        "segments": [
            {
                "id": "1:1", "book": 1, "column": "1",
                "lines": [{"n": 1, "ref": "1", "text": (
                    "apollo greek words here about the palace and the woman who "
                    "must die today for her husband"
                )}],
                "speakers": [{"line": 1, "offset": 0, "label": "Α."}],
            },
            {
                "id": "1:2", "book": 1, "column": "1",
                "lines": [{"n": 2, "ref": "2", "text": "death greek words short reply"}],
                "speakers": [{"line": 2, "offset": 0, "label": "Θ."}],
            },
        ],
    }
    english, _footnotes, _report = parse_translation(
        path, spine, work_id="test", translation_id="test", play="THE PLAY",
        sigla={"Α.": "Apollo", "Θ.": "Death"},
        english_aliases={"APOLLO": "Apollo", "DEATH": "Death"},
        footnotes_enabled=False, format="loeb-ocr", verse=True,
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert [turn["speaker"] for turn in by_id["1:1"]["turns"]] == ["Apollo"]
    assert "Lo, yonder Death" in by_id["1:1"]["text"]
    assert [turn["speaker"] for turn in by_id["1:2"]["turns"]] == ["Death"]
    assert by_id["1:2"]["text"] == "Ha, thou at the palace! Wilt not make room?"


# Same item: medea.txt:1029 ("_Enter NURSE._" mid-Medea's own speech; NURSE
# never gets a cue of her own again) is the same shape -- NURSE has no
# genuine Greek speaker event to land on at all, so the whole block stays
# Medea's.
def test_loeb_ocr_implicit_entrant_with_no_matching_greek_speaker_at_all(tmp_path):
    path = tmp_path / "play.txt"
    path.write_text(
        "THE PLAY\n\n"
        "MEDEA. So be it: wasted are all hindering words of mine against my "
        "husband's cruel and bitter heart.\n"
        "But ho!\n"
        "\n"
        "_Enter NURSE._\n"
        "\n"
        "go thou and Jason bring to me, thou whom I use for every deed of "
        "trust and loyal service.\n"
        "\n"
        "CHORUS. O happy the race in the ages olden of Erechtheus, the seed "
        "of the blest Gods' line.\n",
        encoding="utf-8",
    )
    spine = {
        "work": "test",
        "segments": [
            {
                "id": "1:1", "book": 1, "column": "1",
                "lines": [{"n": 1, "ref": "1", "text": (
                    "medea greek words about her husband cruel heart and the "
                    "nurse she will send on an errand"
                )}],
                "speakers": [{"line": 1, "offset": 0, "label": "Μη."}],
            },
            {
                "id": "1:2", "book": 1, "column": "1",
                "lines": [{"n": 2, "ref": "2", "text": (
                    "chorus greek words about erechtheus and the golden race"
                )}],
                "speakers": [{"line": 2, "offset": 0, "label": "Χο."}],
            },
        ],
    }
    english, _footnotes, _report = parse_translation(
        path, spine, work_id="test", translation_id="test", play="THE PLAY",
        sigla={"Μη.": "Medea", "Χο.": "Chorus"},
        english_aliases={"MEDEA": "Medea", "CHORUS": "Chorus", "NURSE": "Nurse"},
        footnotes_enabled=False, format="loeb-ocr", verse=True,
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert [turn["speaker"] for turn in by_id["1:1"]["turns"]] == ["Medea"]
    assert "go thou and Jason bring to me" in by_id["1:1"]["text"]
    assert [turn["speaker"] for turn in by_id["1:2"]["turns"]] == ["Chorus"]


# Same item, the accepting case: phoenician-women's parodos really is
# CHORUS's own turn -- an "Exeunt" of the previous speakers clears the stage
# right before "Enter CHORUS.", and the Greek has a genuine CHORUS speaker
# event waiting for it. The split must stand.
def test_loeb_ocr_implicit_entrant_accepted_when_the_greek_agrees(tmp_path):
    path = tmp_path / "play.txt"
    path.write_text(
        "THE PLAY\n\n"
        "OLD SERVANT. Daughter, pass in, and 'neath the roofs abide, for "
        "scandal-loving still is womankind.\n"
        "\n"
        "_Exeunt OLD SERVANT and ANTIGONE._\n"
        "\n"
        "_Enter CHORUS._\n"
        "\n"
        "Afar from the tides against Tyre's walls swelling, for Loxias "
        "chosen an offering, from the Isle of Phoenicia I came.\n",
        encoding="utf-8",
    )
    spine = {
        "work": "test",
        "segments": [
            {
                "id": "1:1", "book": 1, "column": "1",
                "lines": [{"n": 1, "ref": "1", "text": (
                    "old servant greek words about the daughter and the roof "
                    "and womankind"
                )}],
                "speakers": [{"line": 1, "offset": 0, "label": "Πρ."}],
            },
            {
                "id": "1:2", "book": 1, "column": "1",
                "lines": [{"n": 2, "ref": "2", "text": (
                    "chorus greek parodos about tyre and phoenicia and loxias"
                )}],
                "speakers": [{"line": 2, "offset": 0, "label": "Χο."}],
            },
        ],
    }
    english, _footnotes, _report = parse_translation(
        path, spine, work_id="test", translation_id="test", play="THE PLAY",
        sigla={"Πρ.": "Old Servant", "Χο.": "Chorus"},
        english_aliases={"OLD SERVANT": "Old Servant", "CHORUS": "Chorus"},
        footnotes_enabled=False, format="loeb-ocr", verse=True,
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert [turn["speaker"] for turn in by_id["1:1"]["turns"]] == ["Old Servant"]
    assert [turn["speaker"] for turn in by_id["1:2"]["turns"]] == ["Chorus"]
    assert by_id["1:2"]["text"].startswith("Afar from the tides")


def test_b4_a_pin_after_a_rejected_implicit_entrant_lands_on_its_speech(tmp_path):
    """B4. `forced = _resolve_pins(...)` runs before the implicit-entrant
    fold. The fold deletes the rejected speech and rebuilds the English
    nodes, but the real alignment still receives the pre-fold indices, so a
    pin on a LATER speech names the speech after the one it quoted.

    No loeb-ocr slot in the corpus has `pins:` today. This bench is the
    alcestis shape (an Enter the Greek rejects) plus a pin on the speech
    after the folded one, and a further speech so the stale index is a real
    speech rather than an index past the end.
    """
    path = tmp_path / "play.txt"
    path.write_text(
        "THE PLAY\n\n"
        "APOLLO. Go forth of yonder hall's beloved roof, lest pollution taint "
        "me in their house.\n"
        "\n"
        "_Enter NURSE._\n"
        "\n"
        "Lo, yonder I see the servant standing by the door.\n"
        "\n"
        "DEATH. Ha, thou at the palace! Wilt not make room?\n"
        "\n"
        "CHORUS. O happy the race in the ages olden of Erechtheus.\n",
        encoding="utf-8",
    )
    spine = {
        "work": "test",
        "segments": [
            {
                "id": "1:1", "book": 1, "column": "1",
                "lines": [{"n": 1, "ref": "1", "text": (
                    "apollo greek words here about the palace and the woman"
                )}],
                "speakers": [{"line": 1, "offset": 0, "label": "Α."}],
            },
            {
                "id": "1:2", "book": 1, "column": "1",
                "lines": [{"n": 2, "ref": "2", "text": "death greek words short reply"}],
                "speakers": [{"line": 2, "offset": 0, "label": "Θ."}],
            },
            {
                "id": "1:3", "book": 1, "column": "1",
                "lines": [{"n": 3, "ref": "3", "text": (
                    "chorus greek words about erechtheus and the golden race"
                )}],
                "speakers": [{"line": 3, "offset": 0, "label": "Χο."}],
            },
        ],
    }
    english, _footnotes, _report = parse_translation(
        path, spine, work_id="test", translation_id="test", play="THE PLAY",
        sigla={"Α.": "Apollo", "Θ.": "Death", "Χο.": "Chorus"},
        english_aliases={
            "APOLLO": "Apollo", "DEATH": "Death", "NURSE": "Nurse",
            "CHORUS": "Chorus",
        },
        footnotes_enabled=False, format="loeb-ocr", verse=True,
        pins=[{"greek": "2", "english": "Ha, thou at the palace"}],
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert "Lo, yonder I see the servant" in by_id["1:1"]["text"]
    assert by_id["1:2"]["text"].startswith("Ha, thou at the palace")
    assert "O happy the race" not in by_id["1:2"]["text"]
    assert by_id["1:3"]["text"].startswith("O happy the race")


def test_b4_a_pin_on_a_rejected_implicit_entrant_is_loud(tmp_path):
    """Sol's read of B4 (2026-09-21): the fold used to drop, without a word,
    a pin whose own speech it deleted. A pin that holds the cue-less block
    after `_Enter NURSE._` to a line the Greek gives Death is rejected by the
    Greek and folded into Apollo; the pin then names nothing, and says so."""
    path = tmp_path / "play.txt"
    path.write_text(
        "THE PLAY\n\n"
        "APOLLO. Go forth of yonder hall's beloved roof, lest pollution taint "
        "me in their house.\n"
        "\n"
        "_Enter NURSE._\n"
        "\n"
        "Lo, yonder I see the servant standing by the door.\n"
        "\n"
        "DEATH. Ha, thou at the palace! Wilt not make room?\n",
        encoding="utf-8",
    )
    spine = {
        "work": "test",
        "segments": [
            {
                "id": "1:1", "book": 1, "column": "1",
                "lines": [{"n": 1, "ref": "1", "text": (
                    "apollo greek words here about the palace and the woman"
                )}],
                "speakers": [{"line": 1, "offset": 0, "label": "Α."}],
            },
            {
                "id": "1:2", "book": 1, "column": "1",
                "lines": [{"n": 2, "ref": "2", "text": "death greek words short reply"}],
                "speakers": [{"line": 2, "offset": 0, "label": "Θ."}],
            },
        ],
    }
    with pytest.raises(ValueError, match="folded"):
        parse_translation(
            path, spine, work_id="test", translation_id="test", play="THE PLAY",
            sigla={"Α.": "Apollo", "Θ.": "Death"},
            english_aliases={"APOLLO": "Apollo", "DEATH": "Death", "NURSE": "Nurse"},
            footnotes_enabled=False, format="loeb-ocr", verse=True,
            pins=[{"greek": "2", "english": "Lo, yonder I see the servant"}],
        )


# B round 3 item 4 (philoctetes finding 5, 2026-09-17): a Loeb editorial
# note citing the lines a cut passage omits, printed as if it were verse
# ("' The omitted lines are:", storr/philoctetes.txt:1808, followed by the
# omitted lines themselves) -- the only instance of this exact shape in the
# corpus. Dropped, continuation and all, up to the next blank line or cue.
def test_loeb_ocr_omitted_lines_editorial_note_is_dropped():
    text = (
        "THE PLAY\n\n"
        "NEOPTOLEMUS. Why should a man feel fear who helps his friends?\n"
        "' The omitted lines are:\n"
        "Who judged Odysseus of thy father's arms\n"
        "More worthy than the hapless Ajax.\n"
        "\n"
        "PHILOCTETES. Help for the sons of Atreus, or for me?\n"
    )
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert [s["speaker_printed"] for s in speeches] == ["NEOPTOLEMUS", "PHILOCTETES"]
    assert speeches[0]["text"] == "Why should a man feel fear who helps his friends?"
    assert "omitted" not in speeches[0]["text"].lower()
    assert "Odysseus" not in speeches[0]["text"]


# A stage direction printed on a line of its own with no closing bracket at
# all -- Way's Andromache 556, `[Exit, led by MENELAUS.` -- still printed as
# speech: `_loeb_direction` required a closing `]`. Read now as a direction
# whenever the line opens with a recognised cue (2026-09-16).
def test_loeb_ocr_unclosed_whole_line_bracket_direction_is_read_as_a_direction():
    text = (
        "THE PLAY\n\n"
        "ANDROMACHE. Boast not herein :—thine hour shall haply come.\n"
        "[Exit, led by MENELAUS.\n\n"
        "CHORUS. Never rival brides blessed marriage-estate.\n"
    )
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert speeches == [
        {"speaker_printed": "ANDROMACHE", "text": "Boast not herein :—thine hour shall haply come."},
        {
            "speaker_printed": "CHORUS",
            "text": "Never rival brides blessed marriage-estate.",
            "directions_before": ["Exit, led by MENELAUS."],
        },
    ]
    for speech in speeches:
        assert "Exit, led by MENELAUS" not in speech["text"]


# The same unclosed-bracket habit also covers "Re-enter"/"Re-enters" -- added
# to `_DIRECTION_CUE` alongside this fix.
def test_loeb_ocr_unclosed_whole_line_bracket_recognises_re_enter():
    text = "THE PLAY\n\nISMENE. I go.\n[Re-enter ISMENE.\n\nCHORUS. Ill is it, stranger.\n"
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert speeches[1] == {
        "speaker_printed": "CHORUS",
        "text": "Ill is it, stranger.",
        "directions_before": ["Re-enter ISMENE."],
    }


# A run-on unclosed bracket with no recognised cue stays speech -- Way's
# Cyclops 218, `[Shows corner of skin.`, where "Shows" is not a direction
# cue; a bare unclosed-`[` test would wrongly cut real speech text.
def test_loeb_ocr_unclosed_whole_line_bracket_with_no_cue_stays_speech():
    text = (
        "THE PLAY\n\n"
        "ODYSSEUS. Old man, it's in this very skin—behold !\n"
        "[Shows corner of skin.\n\n"
        "SILENUS. That !—why there's not a toothful in't, I swear !\n"
    )
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert speeches[0] == {
        "speaker_printed": "ODYSSEUS",
        "text": "Old man, it's in this very skin—behold !\n[Shows corner of skin.",
    }
    assert "directions_before" not in speeches[1]


# Same fix, the verse-own-line path (`_parse_lindsay_speeches`): the own-line
# direction check only read `_..._`, so an unclosed `[...` on its own line
# also printed as speech there.
def test_verse_own_line_unclosed_whole_line_bracket_direction_is_read_as_a_direction():
    text = (
        "THE PLAY\n\n"
        "ANDROMACHE\n"
        "Boast not herein :—thine hour shall haply come.\n"
        "[Exit, led by MENELAUS.\n\n"
        "CHORUS\n"
        "Never rival brides blessed marriage-estate.\n"
    )
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="verse-own-line")
    assert speeches == [
        {"speaker_printed": "ANDROMACHE", "text": "Boast not herein :—thine hour shall haply come."},
        {
            "speaker_printed": "CHORUS",
            "text": "Never rival brides blessed marriage-estate.",
            "directions_before": ["Exit, led by MENELAUS."],
        },
    ]


def test_verse_own_line_unclosed_whole_line_bracket_with_no_cue_stays_speech():
    text = "THE PLAY\n\nODYSSEUS\nOld man, it's in this very skin.\n[Shows corner of skin.\n\nSILENUS\nThat!\n"
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="verse-own-line")
    assert speeches[0] == {
        "speaker_printed": "ODYSSEUS",
        "text": "Old man, it's in this very skin. [Shows corner of skin.",
    }
    assert "directions_before" not in speeches[1]


def test_lindsay_format_keeps_an_unclosed_bracketed_line_as_speech():
    # The comedy (Lindsay) format is `directions=False`: unlike verse-own-line
    # it never reads an own-line direction at all, closed or unclosed.
    text = (
        "LYSISTRATA\nThe Persons of the drama.\n\n"
        "LYSISTRATA\nHear me now, O women of the mighty city.\n[Exit LYSISTRATA.\n"
    )
    speeches, _notes = parse_play_speeches(text, "LYSISTRATA")
    assert speeches[0] == {
        "speaker_printed": "LYSISTRATA",
        "text": "Hear me now, O women of the mighty city. [Exit LYSISTRATA.",
    }


def test_chunks_as_overlay_prefixes_speakers():
    from drama_pipeline.stage1_turn_english import chunks_as_overlay

    first, second = "Ismene, sister.", "To me, Antigone."
    joined = first + "\n\n" + second
    overlay = chunks_as_overlay(
        {
            "chunks": [
                {
                    "id": "1:1",
                    "column": "1",
                    "text": joined,
                    "turns": [
                        {"offset": 0, "speaker": "Antigone", "display": "ANTIGONE"},
                        {"offset": len(first) + 2, "speaker": "Ismene", "display": "ISMENE"},
                    ],
                }
            ]
        }
    )
    piece = overlay["1:1"][0]
    assert piece["cont"] is False
    assert piece["chapter"] == "1"
    assert piece["text"].startswith("ANTIGONE. Ismene, sister.")
    assert "ISMENE. To me, Antigone." in piece["text"]


# Arrowsmith's stage directions (John, 2026-09-12): the cleaner writes each
# printed line of one as `_..._`; a direction between two speeches is carried
# as the next speech's `directions_before`, one inside a speech in `shown`.
DIRECTIONS = """THE PLAY

_The scene opens._
ANTIGONE
Ismene, sister of my blood.
_She turns_
_slowly._
See'st thou how Zeus would fulfil.
_Ismene enters._

ISMENE
To me no word of friends has come.

CHORUS
Sunbeam of all that dawned.

CREON
Sirrah, begone.
_Exit Creon._
"""


def _without_directions(text: str) -> str:
    return "\n".join(ln for ln in text.splitlines() if not (ln.startswith("_") and ln.endswith("_"))) + "\n"


def test_verse_own_line_separates_stage_directions_from_speech():
    speeches, _notes = parse_play_speeches(DIRECTIONS, "THE PLAY", format="verse-own-line")
    assert speeches == [
        {
            "speaker_printed": "ANTIGONE",
            "text": "Ismene, sister of my blood. See'st thou how Zeus would fulfil.",
            "directions_before": ["The scene opens."],
            "shown": "Ismene, sister of my blood.\n_She turns slowly._\nSee'st thou how Zeus would fulfil.",
        },
        {
            "speaker_printed": "ISMENE",
            "text": "To me no word of friends has come.",
            "directions_before": ["Ismene enters."],
        },
        {"speaker_printed": "CHORUS", "text": "Sunbeam of all that dawned."},
        # After the last speech there is no next one: the direction stays inline.
        {"speaker_printed": "CREON", "text": "Sirrah, begone.", "shown": "Sirrah, begone.\n_Exit Creon._"},
    ]
    # Speech text is what it was before directions were kept.
    plain, _notes = parse_play_speeches(_without_directions(DIRECTIONS), "THE PLAY", format="verse-own-line")
    assert [s["text"] for s in speeches] == [s["text"] for s in plain]


def test_verse_own_line_first_speech_may_open_with_a_direction():
    # Clouds: Pheidippides' first speech opens "_Waking up crossly._"; the
    # first-speech search must look past it, or it skips two speeches.
    text = "THE PLAY\n\nANTIGONE\n_Waking up._\nSister.\n\nISMENE\nTo me.\n"
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="verse-own-line")
    assert [s["speaker_printed"] for s in speeches] == ["ANTIGONE", "ISMENE"]
    assert speeches[0]["shown"] == "_Waking up._\nSister."


# Codex merge-gate finding 2 (2026-09-16): the verse-own-line path only read
# a direction on a line of its own (`_..._`); a leading/trailing bracket
# direction sharing a verse line with spoken text must split the same way
# the loeb-ocr path now does, using the format's existing `inline`/`shown`
# machinery -- gated on `directions=True` (verse-own-line only), so the
# Lindsay comedy format is untouched.
def test_verse_own_line_leading_bracket_direction_splits_off_the_verse_line():
    text = "THE PLAY\n\nPELEUS\nMenelaus, hold!\n[To attendant] Lead the way faster!\n"
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="verse-own-line")
    assert speeches == [
        {
            "speaker_printed": "PELEUS",
            "text": "Menelaus, hold! Lead the way faster!",
            "shown": "Menelaus, hold!\n_To attendant_\nLead the way faster!",
        }
    ]


def test_verse_own_line_trailing_bracket_direction_rides_to_next_speech():
    text = (
        "THE PLAY\n\n"
        "HERMIONE\n"
        "So far as in me lies, ye are saved. [Enters the palace.\n\n"
        "ELECTRA\n"
        "Ho ye, armed friends within.\n"
    )
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="verse-own-line")
    assert speeches == [
        {"speaker_printed": "HERMIONE", "text": "So far as in me lies, ye are saved."},
        {
            "speaker_printed": "ELECTRA",
            "text": "Ho ye, armed friends within.",
            "directions_before": ["Enters the palace."],
        },
    ]


def test_lindsay_format_keeps_a_bracketed_line_as_speech():
    # Same guard as the underscore case just below: the comedy (Lindsay)
    # format never reads a direction at all, bracket or underscore, so a
    # leading `[To someone]` stays put as spoken text.
    text = """LYSISTRATA
The Persons of the drama.

LYSISTRATA
[To attendant] Lead the way faster!
"""
    speeches, _notes = parse_play_speeches(text, "LYSISTRATA")
    assert speeches[0] == {
        "speaker_printed": "LYSISTRATA",
        "text": "[To attendant] Lead the way faster!",
    }


def test_lindsay_format_keeps_an_underscored_line_as_speech():
    # Only verse-own-line reads `_..._` as a direction; Gutenberg's own-line
    # speakers (the 1912 comedies) keep it as speech text, as before.
    text = """LYSISTRATA
The Persons of the drama.

LYSISTRATA
This is the first speech in the play.
_Exit._

CALONICE.
This is the second speech in the play.
"""
    speeches, _notes = parse_play_speeches(text, "LYSISTRATA")
    assert speeches[0] == {
        "speaker_printed": "LYSISTRATA",
        "text": "This is the first speech in the play. Exit.",
    }


def _parse_directions(tmp_path, text: str, spine: dict):
    path = tmp_path / "play.txt"
    path.write_text(text, encoding="utf-8")
    return parse_translation(
        path,
        spine,
        work_id="antigone",
        translation_id="arrowsmith",
        play="THE PLAY",
        sigla={"ΑΝ.": "Antigone", "ΙΣ.": "Ismene", "Χο.": "Chorus", "ΚΡ.": "Creon"},
        english_aliases={
            "ANTIGONE": "Antigone",
            "ISMENE": "Ismene",
            "CHORUS": "Chorus",
            "CREON": "Creon",
        },
        footnotes_enabled=False,
        format="verse-own-line",
    )


def test_stage_directions_ride_the_chunks_and_never_touch_pairing(tmp_path):
    from drama_pipeline.stage1_turn_english import chunks_as_overlay

    english, _fn, report = _parse_directions(tmp_path, DIRECTIONS, _antigone_spine())
    chunks = {c["id"]: c for c in english["chunks"]}
    assert chunks["1:1"]["directionsBefore"] == ["The scene opens."]
    assert "\n_She turns slowly._\n" in chunks["1:1"]["text"]
    assert chunks["1:2"]["directionsBefore"] == ["Ismene enters."]
    assert "directionsBefore" not in chunks["1:3"]
    assert chunks["1:4"]["text"].endswith("\n_Exit Creon._")
    overlay = chunks_as_overlay(english)
    assert overlay["1:1"][0]["directionsBefore"] == ["The scene opens."]
    assert "directionsBefore" not in overlay["1:3"][0]

    _e, _f, plain = _parse_directions(tmp_path, _without_directions(DIRECTIONS), _antigone_spine())
    for key in ("paired", "pairing_rate", "turn_shift_rate", "head_unassigned", "length_ratio_outliers"):
        assert report[key] == plain[key], key


def test_a_direction_between_two_speeches_of_one_segment_rides_the_later_turn(tmp_path):
    # Clouds 1:866: one Greek segment holds Strepsiades and Sokrates, and
    # "Enter Sokrates from the Thinkery" falls between them. It rides the
    # later speech's turn, never the earlier speech's text, so the reader can
    # give it a row of its own between the two (Codex review of 7a9a16d).
    from drama_pipeline.stage1_turn_english import chunks_as_overlay

    spine = {
        "work": "antigone",
        "segments": [
            {
                "id": "1:1",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": 1, "ref": "1", "text": "Greek sample text"},
                    {"n": 2, "ref": "2", "text": "Greek sample text"},
                ],
                "speakers": [
                    {"line": 1, "offset": 0, "label": "ΑΝ."},
                    {"line": 2, "offset": 0, "label": "ΙΣ."},
                ],
            }
        ],
    }
    text = (
        "THE PLAY\n\nANTIGONE\nAh, good dutiful boy.\n_Enter Sokrates from the Thinkery._\n\n"
        "ISMENE\nWhy, he's still a baby.\n"
    )
    english, _fn, report = _parse_directions(tmp_path, text, spine)
    (chunk,) = english["chunks"]
    assert "directionsBefore" not in chunk
    assert chunk["text"] == "Ah, good dutiful boy.\n\nWhy, he's still a baby."
    assert [t["offset"] for t in chunk["turns"]] == [0, chunk["text"].index("Why,")]
    assert "directionsBefore" not in chunk["turns"][0]
    assert chunk["turns"][1]["directionsBefore"] == ["Enter Sokrates from the Thinkery."]
    # The overlay has no turns: the piece says which prefixed turn it precedes.
    (piece,) = chunks_as_overlay(english)["1:1"]
    assert "_" not in piece["text"]
    assert piece["turnDirections"] == [{"turn": 1, "directions": ["Enter Sokrates from the Thinkery."]}]
    assert "directionsBefore" not in piece
    _e, _f, plain = _parse_directions(tmp_path, _without_directions(text), spine)
    for key in ("paired", "pairing_rate", "turn_shift_rate", "head_unassigned"):
        assert report[key] == plain[key], key
    assert "turnDirections" not in chunks_as_overlay(_e)["1:1"][0]


def test_spread_keeps_a_direction_whole_and_on_the_first_piece_only():
    from drama_pipeline.stage1_turn_english import _spread_long_speeches

    text = (
        "First sentence here.\n_Exit Meton. From the side enters another._\n"
        "Second sentence there. Third sentence now."
    )
    chunk = {
        "id": "1:1", "book": 1, "column": "1", "text": text, "notes": [], "markers": [],
        "bekker": [], "turns": [{"offset": 0, "speaker": "Chorus", "display": "CHORUS"}],
        "directionsBefore": ["Enter Meton."],
    }
    segments = [
        {"id": "1:1", "column": "1", "lines": [{"n": 1}], "speakers": [{"line": 1, "offset": 0}]},
        {"id": "1:2", "column": "2", "lines": [{"n": 2}]},
    ]
    first, second = _spread_long_speeches([chunk], segments)
    assert "_Exit Meton. From the side enters another._" in first["text"]
    assert second["text"] == "Third sentence now."
    assert first["directionsBefore"] == ["Enter Meton."]
    assert "directionsBefore" not in second


def test_spread_stops_before_the_thin_floor_across_a_same_speaker_run():
    # Codex review of 05e6855: after crossing a "same"-speaker continuation,
    # later crossed segments stopped counting in `lines_before`, so the 0.5x
    # floor (_THIN) was checked against too few lines. A head (1 line) plus
    # four five-line "same" continuations, at a column median of 20 chars per
    # line, used to let all four in even though the true density over all 21
    # lines is 0.238x the median; fixed, it stops after the first
    # continuation, where the true density (0.833x, over 6 lines) still clears
    # the floor -- the next one would not (0.4545x, over 11).
    from drama_pipeline.stage1_turn_english import _spread_long_speeches

    def lines(from_n, to_n):
        return [{"n": n, "text": "λόγος ἄλλος"} for n in range(from_n, to_n + 1)]

    def speech(n):
        return [{"line": n, "offset": 0, "label": "ΧΟ."}]

    head = {
        "id": "1:1", "book": 1, "column": "1",
        "text": (
            "One is here. Two is here too. Three now enters the scene. "
            "Four then arrives quickly. Five ends here."
        ),
        "notes": [], "markers": [], "bekker": [], "turns": [],
    }
    # Two owned 1-line/20-char segments pull the column median to 20 (median
    # of [100, 20, 20]), independent of the head's own 100-char speech.
    dummy = lambda cid: {"id": cid, "book": 1, "column": "1", "text": "x" * 20,
                          "notes": [], "markers": [], "bekker": [], "turns": []}
    segments = [
        {"id": "1:1", "column": "1", "lines": lines(1, 1), "speakers": speech(1)},
        {"id": "1:2", "column": "1", "lines": lines(2, 6), "speakers": speech(2)},
        {"id": "1:3", "column": "1", "lines": lines(7, 11), "speakers": speech(7)},
        {"id": "1:4", "column": "1", "lines": lines(12, 16), "speakers": speech(12)},
        {"id": "1:5", "column": "1", "lines": lines(17, 21), "speakers": speech(17)},
        {"id": "1:6", "column": "1", "lines": lines(22, 22)},
        {"id": "1:7", "column": "1", "lines": lines(23, 23)},
    ]
    chunks = [head, dummy("1:6"), dummy("1:7")]
    out = {c["id"]: c["text"] for c in _spread_long_speeches(chunks, segments)}
    # Only "1:1" and "1:2" (the head and its first continuation) hold English;
    # "1:3"/"1:4"/"1:5" stay bare -- the loop stopped at the floor.
    assert set(out) & {"1:1", "1:2", "1:3", "1:4", "1:5"} == {"1:1", "1:2"}
    assert out["1:2"] == (
        "Two is here too. Three now enters the scene. "
        "Four then arrives quickly. Five ends here."
    )


def _dash_group(turns):
    from drama_pipeline.stage1_turn_english import _spread_long_speeches

    def lines(from_n, to_n):
        return [{"n": n, "text": "λόγος ἄλλος"} for n in range(from_n, to_n + 1)]

    text = "Aa bit one. Bb marker1 bit two. Cc marker2 bit three. Dd marker3 bit four."
    head = {
        "id": "1:1", "book": 1, "column": "1", "text": text,
        "notes": [], "markers": [], "bekker": [],
        "turns": [{"offset": o} for o in turns],
    }
    dummy = lambda cid: {"id": cid, "book": 1, "column": "1", "text": "xx",
                          "notes": [], "markers": [], "bekker": [], "turns": []}
    segments = [
        {"id": "1:1", "column": "1", "lines": lines(1, 1), "speakers": [{"line": 1, "offset": 0, "label": "CHORUS"}]},
        {"id": "1:2", "column": "1", "lines": lines(2, 2), "speakers": [{"line": 2, "offset": 0, "label": "—"}]},
        {"id": "1:3", "column": "1", "lines": lines(3, 3), "speakers": [{"line": 3, "offset": 0, "label": "—"}]},
        {"id": "1:4", "column": "1", "lines": lines(4, 4), "speakers": [{"line": 4, "offset": 0, "label": "—"}]},
        {"id": "1:8", "column": "1", "lines": lines(5, 5)},
        {"id": "1:9", "column": "1", "lines": lines(6, 6)},
    ]
    chunks = [head, dummy("1:8"), dummy("1:9")]
    out = _spread_long_speeches(chunks, segments)
    return {c["id"]: c["text"] for c in out if c["id"] in ("1:1", "1:2", "1:3", "1:4")}


def test_dash_continuations_fall_back_to_sentence_starts_when_turns_run_short():
    # Codex review of 05e6855: OCR-damaged speaker labels leave a translation
    # with fewer turn marks than there are unnamed ("dash") continuations to
    # place (Suppliants-eur 600-619). Taking the turn pool anyway misreads
    # later dashes -- here it loses two of three outright. With only one turn
    # for three dashes, every cut must come from the sentence-start pool
    # (`aim`), matching what a translation with no turns at all would give.
    turn_case = _dash_group([15])
    no_turns = _dash_group([])
    assert turn_case == no_turns == {
        "1:1": "Aa bit one.",
        "1:2": "Bb marker1 bit two.",
        "1:3": "Cc marker2 bit three.",
        "1:4": "Dd marker3 bit four.",
    }


def test_dash_continuations_still_use_complete_turns():
    # A turn for every dash still to place: unchanged, the turn pool wins.
    assert _dash_group([15, 35, 57]) == {
        "1:1": "Aa bit one. Bb",
        "1:2": "marker1 bit two. Cc",
        "1:3": "marker2 bit three. Dd",
        "1:4": "marker3 bit four.",
    }


def test_dash_run_measures_stacking_at_the_head_and_the_floor_over_all():
    # 1a3902b measured "stacked" over every line crossed, so a chorus head's
    # English stopped at the second unnamed dash and the half-chorus turns
    # after it piled onto one row (Way's Suppliants-eur 598-632). Stacking is
    # judged at the head (4.3x the median here); the 0.5x floor over all six
    # lines (0.71x) still holds, so every dash takes its own turn.
    from drama_pipeline.stage1_turn_english import _spread_long_speeches

    text = "Aa won. Bb won. Cc won. Dd won. Ee won. Ff won."
    head = {
        "id": "1:1", "book": 1, "column": "1", "text": text,
        "notes": [], "markers": [], "bekker": [],
        "turns": [{"offset": o} for o in (0, 8, 16, 24, 32, 40)],
    }
    dummy = lambda cid: {"id": cid, "book": 1, "column": "1", "text": "x" * (len(text) // 4),
                          "notes": [], "markers": [], "bekker": [], "turns": []}
    line = lambda n: [{"n": n, "text": "λόγος ἄλλος"}]
    segments = [
        {"id": "1:1", "column": "1", "lines": line(1), "speakers": [{"line": 1, "offset": 0, "label": "CHORUS"}]},
        *[
            {"id": f"1:{n}", "column": "1", "lines": line(n), "speakers": [{"line": n, "offset": 0, "label": "—"}]}
            for n in range(2, 7)
        ],
        {"id": "1:8", "column": "1", "lines": line(8)},
        {"id": "1:9", "column": "1", "lines": line(9)},
    ]
    out = {c["id"]: c["text"] for c in _spread_long_speeches([head, dummy("1:8"), dummy("1:9")], segments)}
    assert [out.get(f"1:{n}") for n in range(1, 7)] == [
        "Aa won.", "Bb won.", "Cc won.", "Dd won.", "Ee won.", "Ff won.",
    ]


def test_run_secondary_writes_ross_chunks(tmp_path, monkeypatch):
    from drama_pipeline.config import Manifest
    from drama_pipeline import stage1_turn_english as m

    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "play.txt").write_text(LOEB_OCR, encoding="utf-8")
    monkeypatch.setattr(m, "BUILD_DIR", tmp_path)
    monkeypatch.setattr(m, "SOURCES_DIR", src_dir)
    spine = _antigone_spine()
    man = Manifest(
        {
            "work": {"id": "antigone"},
            "english": {
                "secondary": {
                    "id": "storr",
                    "source": "play.txt",
                    "play": "ANTIGONE",
                    "format": "loeb-ocr",
                    "footnotes": False,
                }
            },
            "speakers": {
                "sigla": {
                    "ΑΝ.": "Antigone",
                    "ΙΣ.": "Ismene",
                    "Χο.": "Chorus",
                    "ΚΡ.": "Creon",
                    "—": None,
                },
                "english_secondary": {
                    "ANTIGONE": "Antigone",
                    "ISMENE": "Ismene",
                    "CHORUS": "Chorus",
                    "CREON": "Creon",
                },
            },
        },
        tmp_path / "antigone.yaml",
    )
    eng_path, _align, report_path = m.run(man, spine, slot="secondary")
    assert eng_path.name == "ross_chunks.json"
    ross = json.loads(eng_path.read_text(encoding="utf-8"))
    assert all(isinstance(v, list) and v[0]["text"] for v in ross.values())
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["translation"] == "storr"
    assert report["speeches_parsed"] == 4


def test_run_third_writes_third_chunks(tmp_path, monkeypatch):
    from drama_pipeline.config import Manifest
    from drama_pipeline import stage1_turn_english as m

    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "play.txt").write_text(LOEB_OCR, encoding="utf-8")
    monkeypatch.setattr(m, "BUILD_DIR", tmp_path)
    monkeypatch.setattr(m, "SOURCES_DIR", src_dir)
    spine = _antigone_spine()
    man = Manifest(
        {
            "work": {"id": "antigone"},
            "english": {
                "third": {
                    "id": "hickie",
                    "source": "play.txt",
                    "play": "ANTIGONE",
                    "format": "loeb-ocr",
                    "footnotes": False,
                }
            },
            "speakers": {
                "sigla": {
                    "ΑΝ.": "Antigone",
                    "ΙΣ.": "Ismene",
                    "Χο.": "Chorus",
                    "ΚΡ.": "Creon",
                    "—": None,
                },
                "english_third": {
                    "ANTIGONE": "Antigone",
                    "ISMENE": "Ismene",
                    "CHORUS": "Chorus",
                    "CREON": "Creon",
                },
            },
        },
        tmp_path / "antigone.yaml",
    )
    eng_path, _align, report_path = m.run(man, spine, slot="third")
    assert eng_path.name == "third_chunks.json"
    third = json.loads(eng_path.read_text(encoding="utf-8"))
    assert all(isinstance(v, list) and v[0]["text"] for v in third.values())
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["translation"] == "hickie"
    assert report["speeches_parsed"] == 4


def test_run_looks_up_verse_form_from_the_registry(tmp_path, monkeypatch):
    """`registry.translations[].form: verse` on the slot's translation id
    makes `run()` keep the source's own line breaks; a translation with no
    `form` (or `form: prose`) is unaffected (John, 2026-09-14, "show verse as
    verse!!!!")."""
    from drama_pipeline.config import Manifest
    from drama_pipeline import stage1_turn_english as m

    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "play.txt").write_text(LOEB_OCR, encoding="utf-8")
    monkeypatch.setattr(m, "BUILD_DIR", tmp_path)
    monkeypatch.setattr(m, "SOURCES_DIR", src_dir)
    spine = _antigone_spine()

    def _manifest(form: str | None) -> Manifest:
        data = {
            "work": {"id": "antigone"},
            "english": {
                "secondary": {
                    "id": "storr",
                    "source": "play.txt",
                    "play": "ANTIGONE",
                    "format": "loeb-ocr",
                    "footnotes": False,
                }
            },
            "speakers": {
                "sigla": {
                    "ΑΝ.": "Antigone", "ΙΣ.": "Ismene", "Χο.": "Chorus", "ΚΡ.": "Creon",
                    "—": None,
                },
                "english_secondary": {
                    "ANTIGONE": "Antigone", "ISMENE": "Ismene", "CHORUS": "Chorus", "CREON": "Creon",
                },
            },
        }
        if form is not None:
            data["registry"] = {"translations": [{"id": "storr", "form": form}]}
        return Manifest(data, tmp_path / "antigone.yaml")

    # Antigone's own speech (chunk "1:1") is three source lines.
    verse_path, _a, _r = m.run(_manifest("verse"), spine, slot="secondary")
    verse_text = json.loads(verse_path.read_text(encoding="utf-8"))["1:1"][0]["text"]
    assert "\n" in verse_text

    for form in (None, "prose"):
        prose_path, _a, _r = m.run(_manifest(form), spine, slot="secondary")
        prose_text = json.loads(prose_path.read_text(encoding="utf-8"))["1:1"][0]["text"]
        assert "\n" not in prose_text
        assert verse_text.replace("\n", " ") == prose_text


def test_loeb_ocr_unaliased_speakers_are_unattributed_not_fatal(tmp_path):
    """An OCR junk label in a loeb-ocr comparison slot must not fail the play:
    the speech stays, unattributed (no colour key), and is reported."""
    from drama_pipeline import stage1_turn_english as m
    src = tmp_path / "storr.txt"
    src.write_text("ANTIGONE\n\nANTIGONE. Sister, dear sister.\nWOU. junk line.\nISMENE. What is it?\n")
    spine = {"segments": [
        {"id": "1:1", "book": 1, "column": "1", "speakers": [{"label": "ΑΝ.", "line": 1, "offset": 0}], "greek": [{"n": 1, "ref": "1", "text": "ὦ κοινόν"}]},
        {"id": "1:2", "book": 1, "column": "1", "speakers": [{"label": "ΙΣ.", "line": 2, "offset": 0}], "greek": [{"n": 2, "ref": "2", "text": "τί δ᾽ ἔστι"}]},
    ]}
    chunks, _notes, report = m.parse_translation(
        src, spine, work_id="antigone", translation_id="storr", play="ANTIGONE",
        sigla={"ΑΝ.": "Antigone", "ΙΣ.": "Ismene"},
        english_aliases={"ANTIGONE": "Antigone", "ISMENE": "Ismene"},
        footnotes_enabled=False, format="loeb-ocr",
    )
    assert report["speakers"]["unaliased_ocr_speakers"] == ["WOU"]
    assert report["speakers"]["only_in_english"] == []


# ── P2g: speaker-line shape, OCR junk, single-letter caps ──────────────────


def test_caps_run_ends_before_a_single_letter_capital():
    """`MYRRHINÉ I could not…` built the name "MYRRHINÉ I", failed the alias
    test and folded into the previous speech (P2g finding 6). A name that
    BEGINS with a single capital keeps it."""
    from drama_pipeline.stage1_turn_english import _periodless_speaker

    known = {"MYRRHINÉ", "CHREMYLUS", "A HERALD", "CHORUS OF ATHENIANS"}
    assert _periodless_speaker("MYRRHINÉ I could not find my girdle", known) == (
        "MYRRHINÉ",
        "I could not find my girdle",
    )
    assert _periodless_speaker("CHREMYLUS I shall be soon, if the god", known) == (
        "CHREMYLUS",
        "I shall be soon, if the god",
    )
    assert _periodless_speaker("A HERALD comes forward", known) == (
        "A HERALD",
        "comes forward",
    )
    assert _periodless_speaker("CHORUS OF ATHENIANS Appear, dancers", known) == (
        "CHORUS OF ATHENIANS",
        "Appear, dancers",
    )


def test_real_single_letter_opening_speeches_are_their_own():
    pg8688 = (SOURCES_DIR / "gutenberg/pg8688.txt").read_text(encoding="utf-8").splitlines()
    pg8689 = (SOURCES_DIR / "gutenberg/pg8689.txt").read_text(encoding="utf-8").splitlines()
    assert pg8688[7538].startswith("MYRRHINÉ I could not find my girdle")
    assert pg8689[13351].startswith("CHREMYLUS I shall be soon")

    lysistrata, _notes = _manifest_speeches("lysistrata")
    girdle = [
        speech for speech in lysistrata
        if speech["text"].startswith("I could not find my girdle")
    ]
    assert [speech["speaker_printed"] for speech in girdle] == ["MYRRHINÉ"]

    wealth, _notes = _manifest_speeches("wealth")
    soon = [
        speech for speech in wealth
        if speech["text"].startswith("I shall be soon, if the god")
    ]
    assert [speech["speaker_printed"] for speech in soon] == ["CHREMYLUS"]


def test_speaker_full_stop_needs_a_space_or_end_of_line():
    """`O.God!` (Storr philoctetes.txt:830) is prose, not a speaker named "O";
    `\\.\\s*` matched with zero space (P2g finding 7)."""
    from drama_pipeline.stage1_turn_english import _SPEAKER_LINE

    assert _SPEAKER_LINE.match("O.God!") is None
    assert _SPEAKER_LINE.match("PHILOCTETES.No space here") is None
    assert _SPEAKER_LINE.match("CHORUS. The curses work").group("name") == "CHORUS"
    assert _SPEAKER_LINE.match("CHORUS.").group("name") == "CHORUS"
    # The Gutenberg footnote form `NAME.[412] text` stays a speaker line.
    marked = _SPEAKER_LINE.match("CHORUS OF OLD MEN.[412] Come along")
    assert marked.group("name") == "CHORUS OF OLD MEN"
    assert marked.group("fn3") == "412"


def test_speaker_line_accepts_a_digit_led_continuation_word():
    """Ajax's Storr text prints "SEMI-CHORUS 1." for the search-scene
    semichorus (storr/ajax.txt:977, `Πόνος πόνῳ πόνον φέρει`); the
    continuation branch required its next token to start [A-ZÀ-Þ], so the
    digit broke the name, the required "." never landed, and the whole
    semichorus scene glued onto Ajax's suicide speech (ajax finding #5,
    2026-09-15)."""
    from drama_pipeline.stage1_turn_english import _SPEAKER_LINE

    m = _SPEAKER_LINE.match("SEMI-CHORUS 1. Toil, toil, and toil on toil !")
    assert m is not None
    assert m.group("name") == "SEMI-CHORUS 1"


@pytest.mark.parametrize(
    "work, line_no, junk",
    [("oedipus-tyrannus", 951, "WOU. 4, F"), ("electra-soph", 1771, "VQL. I. R")],
)
def test_bench_scanner_junk_lines_are_declared_line_fixes(work, line_no, junk):
    """The two spaced OCR artefacts are real `NAME. text` shapes, so the
    regex cannot see them: the manifest blanks the line (P2g finding 7)."""
    manifest = Manifest.for_work(work)
    cfg = manifest.data["english"]["secondary"]
    fixes = cfg.get("line_fixes") or {}
    assert int(line_no) in {int(k) for k in fixes}
    assert fixes[line_no] == ""
    source = SOURCES_DIR / cfg["source"]
    if not source.exists():  # bench scans are not part of a minimal checkout
        return
    lines = source.read_text(encoding="utf-8").splitlines()
    assert lines[line_no - 1] == junk
    speeches, _notes = parse_play_speeches(
        "\n".join(lines),
        cfg["play"],
        format=cfg.get("format") or "gutenberg",
        known_names=set(manifest.data["speakers"].get("english") or {}),
        line_fixes=fixes,
    )
    name = junk.split(".")[0]
    assert all(speech["speaker_printed"] != name for speech in speeches)


def test_ocr_junk_speech_is_unattributed_and_never_pairs(tmp_path):
    """A junk label must not become a pairing wildcard (None agrees with every
    Greek speaker) nor be printed as a speaker (P2g finding 8)."""
    from drama_pipeline.stage1_turn_english import _OCR_JUNK

    path = tmp_path / "play.txt"
    path.write_text(
        "TEST PLAY\n"
        "ALPHA. First words of the play here.\n"
        "WOU. 4, F\n"
        "BETA. Second words of the play here.\n"
        "FINIS\n",
        encoding="utf-8",
    )
    spine = {
        "work": "test",
        "segments": [
            {
                "id": f"1:{n}",
                "book": 1,
                "column": "1",
                "lines": [{"n": n, "ref": str(n), "text": "Greek sample text"}],
                "speakers": [{"line": n, "offset": 0, "label": label}],
            }
            for n, label in enumerate(("Α.", "Β."), 1)
        ],
    }
    english, _footnotes, report = parse_translation(
        path,
        spine,
        work_id="test",
        translation_id="storr",
        play="TEST PLAY",
        sigla={"Α.": "Alpha", "Β.": "Beta"},
        english_aliases={"ALPHA": "Alpha", "BETA": "Beta"},
        footnotes_enabled=False,
        format="loeb-ocr",
    )
    assert report["speakers"]["unaliased_ocr_speakers"] == ["WOU"]
    assert report["speakers"]["only_in_english"] == []
    turns = [turn for chunk in english["chunks"] for turn in chunk["turns"]]
    assert [turn["display"] for turn in turns] == ["ALPHA", "BETA"]
    assert all(turn["speaker"] != _OCR_JUNK for turn in turns)
    # The words themselves are still shown, unattributed.
    assert any("4, F" in chunk["text"] for chunk in english["chunks"])
    assert report["turn_shift_count"] == 0


def test_greek_segment_name_is_the_first_lines_start_speaker(tmp_path):
    """P3.4 replaces the alternative-name escape this test used to assert.

    A packed segment (an antilabe hands the line over mid-way) offered ONE
    pairing slot, so P2h finding 9 let a gap turn agree with any share of its
    lines (`_pair_turns(..., greek_alt)`).  Pairing now runs over the shares
    themselves — one slot each — so that escape is gone with the packing it
    worked around, and the segment-level speaker rule (the speaker of the
    first line at offset 0) survives only to report
    `segment_pairing_rate`.  The line-level rules it feeds (`speaker_at`,
    used by the perseus-play builder) are unchanged.
    """
    from drama_pipeline import stage1_turn_english as m

    resolver = m._SiglaResolver(
        Manifest(
            {
                "work": {"id": "k"},
                "speakers": {"sigla": {"Ισ.": "Ismene", "ΚΗΡΥΞ": "Herald", "—": None}},
            },
            tmp_path / "k.yaml",
        )
    )
    packed = {
        "id": "1:1004",
        "lines": [{"n": n, "ref": str(n), "text": "g"} for n in (1004, 1005, 1006)],
        "speakers": [
            {"line": 1004, "offset": 0, "label": "Ισ."},
            {"line": 1005, "offset": 1, "label": "ΚΗΡΥΞ"},
        ],
    }
    assert m._greek_segment_name(packed, resolver) == "Ismene"
    assert m._segment_speaks(packed, resolver) == {"Ismene", "Herald"}
    # The line-level rule, offset and all.
    assert m.speaker_at(packed, 1004, resolver) == "Ismene"
    assert m.speaker_at(packed, 1005, resolver) == "Ismene"
    assert m.speaker_at(packed, 1005, resolver, prefer="Herald") == "Herald"
    assert m.speaker_at(packed, 1006, resolver) == "Herald"
    # The packed segment is TWO pairing slots, so the Herald's English pairs
    # with the Herald's own share instead of borrowing Ismene's slot, and an
    # English speech naming a third character still pairs with neither.
    slots = m._greek_event_slots([packed], resolver)
    assert [(s["segment"], s["line"], s["offset"], s["name"]) for s in slots] == [
        (0, 1004, 0, "Ismene"),
        (0, 1005, 1, "Herald"),
    ]
    # `_pair_turns` is deleted (turn-pairing-design-2026-09-15); the DP
    # replaces it, and the outcome is the same: the packed segment is TWO
    # pairing slots, so the Herald's English pairs with the Herald's own
    # share instead of borrowing Ismene's slot.
    from drama_pipeline.pair_dp import EnglishNode, GreekNode, align

    greek_nodes = [
        GreekNode(name=s["name"], chars=10, line_key=(s["segment"], s["line"]))
        for s in slots
    ]
    result = align(
        greek_nodes,
        [EnglishNode(name="Ismene", chars=10), EnglishNode(name="Herald", chars=10)],
        pins=[],
    )
    assert result.pairs == [(0, 0), (1, 1)]
    # Round 4 (turn-pairing-round4-2026-09-15.md, P2): `w_spk` dropped so a
    # disagreeing run is matched-with-flags at every length, not tunnelled,
    # which now includes this two-node one. An English speech naming a third
    # character is cheaper matched (and flagged as crossed) than skipping
    # both Greek shares outright, so it lands on the node closest to it in
    # length and position rather than pairing with neither.
    result2 = align(greek_nodes, [EnglishNode(name="Antigone", chars=10)], pins=[])
    assert result2.pairs == [(0, 0)]


def _one_liner(tmp_path, source: str, spine: dict, sigla: dict, aliases: dict):
    path = tmp_path / "play.txt"
    path.write_text(f"TEST PLAY\n{source}\nFINIS\n", encoding="utf-8")
    return parse_translation(
        path,
        spine,
        work_id="test",
        translation_id="test",
        play="TEST PLAY",
        sigla=sigla,
        english_aliases=aliases,
        footnotes_enabled=False,
    )


def test_antilabe_shares_each_take_their_own_english(tmp_path):
    """P3.4: a line the antilabe splits packs two speakers into ONE segment.

    Pairing over segments offered that segment a single slot, so Beta's
    speech could never pair however exactly it agreed — it parked flagged on
    Alpha's segment.  One slot per share pairs both, and the segment's chunk
    carries the two pieces in share order, each with its own turn offset.
    """
    spine = {
        "work": "test",
        "segments": [
            {
                "id": "1:1", "book": 1, "column": "1",
                "lines": [{"n": 1, "ref": "1", "text": "ἄλφα λέγει· βῆτα λέγει."}],
                "speakers": [
                    {"line": 1, "offset": 0, "label": "Α."},
                    {"line": 1, "offset": 12, "label": "Β."},
                ],
            },
        ],
    }
    english, _footnotes, report = _one_liner(
        tmp_path,
        "ALPHA. Alpha speaks.\nBETA. Beta answers.",
        spine,
        {"Α.": "Alpha", "Β.": "Beta"},
        {"ALPHA": "Alpha", "BETA": "Beta"},
    )
    assert report["greek_events"] == 2
    assert report["paired"] == 2
    assert report["pairing_rate"] == 1.0
    assert report["segment_pairing_rate"] == 1.0
    assert report["residual_flagged"] == 0
    assert report["residual_grouped"] == 0
    assert report["turn_shift_count"] == 0
    chunk = english["chunks"][0]
    assert chunk["id"] == "1:1"
    assert chunk["text"] == "Alpha speaks.\n\nBeta answers."
    assert [(turn["offset"], turn["speaker"]) for turn in chunk["turns"]] == [
        (0, "Alpha"),
        (len("Alpha speaks.\n\n"), "Beta"),
    ]
    assert all("speakerMismatch" not in turn for turn in chunk["turns"])


def test_three_shares_on_one_line_all_pair(tmp_path):
    """The A–B–A line (P2i finding 7): three shares, three slots, three pairs,
    and the returning speaker gets the LAST share, not the first."""
    spine = {
        "work": "test",
        "segments": [
            {
                "id": "1:1", "book": 1, "column": "1",
                "lines": [{"n": 1, "ref": "1", "text": "ἄλφα· βῆτα· ἄλφα πάλιν."}],
                "speakers": [
                    {"line": 1, "offset": 0, "label": "Α."},
                    {"line": 1, "offset": 6, "label": "Β."},
                    {"line": 1, "offset": 12, "label": "Α."},
                ],
            },
        ],
    }
    english, _footnotes, report = _one_liner(
        tmp_path,
        "ALPHA. First.\nBETA. Second.\nALPHA. Third.",
        spine,
        {"Α.": "Alpha", "Β.": "Beta"},
        {"ALPHA": "Alpha", "BETA": "Beta"},
    )
    assert report["greek_events"] == 3
    assert report["paired"] == 3
    assert report["pairing_rate"] == 1.0
    assert report["residual_flagged"] == 0
    chunk = english["chunks"][0]
    assert [turn["speaker"] for turn in chunk["turns"]] == ["Alpha", "Beta", "Alpha"]
    assert chunk["text"] == "First.\n\nSecond.\n\nThird."


def test_turn_shift_detects_a_one_turn_drift(tmp_path):
    """P3.4's drift detector.

    Names agree at every pair by construction now, so `turn_shift` compares
    POSITION instead: the English speech's place among its own same-name run
    against the Greek share's place among its.  Here the translation gives
    Beta's first speech to Alpha, so every later Beta pairs one turn behind
    the Greek — the shape of the Birds prologue, and invisible to the P3.3
    name check.
    """
    spine = {
        "work": "test",
        "segments": [
            {
                "id": f"1:{n}", "book": 1, "column": "1",
                "lines": [{"n": n, "ref": str(n), "text": "γραμμη τις εστιν."}],
                "speakers": [{"line": n, "offset": 0, "label": label}],
            }
            for n, label in enumerate(["Α.", "Β.", "Α.", "Β."], 1)
        ],
    }
    _english, _footnotes, report = _one_liner(
        tmp_path,
        "ALPHA. First.\nALPHA. Second.\nBETA. Third.",
        spine,
        {"Α.": "Alpha", "Β.": "Beta"},
        {"ALPHA": "Alpha", "BETA": "Beta"},
    )
    assert report["paired"] == 3
    assert report["turn_shift_count"] == 1
    assert report["turn_shift_rate"] == 1 / 3
    shift = report["turn_shifts"][0]
    assert shift["greek_id"] == "1:4"
    assert shift["greek_speaker"] == "Beta"
    assert shift["english_speaker"] == "Beta"
    # The Greek's second Beta paired with the English's first.
    assert (shift["greek_ordinal"], shift["english_ordinal"]) == (1, 0)


def test_a_segment_with_no_speaker_event_keeps_one_slot(tmp_path):
    """A lyric continuation carries no speaker event of its own.  It still
    gets exactly one (unnamed) slot, so residual English can park on it and
    no segment becomes unreachable."""
    from drama_pipeline import stage1_turn_english as m

    segments = [
        {
            "id": "1:1",
            "lines": [{"n": 1, "ref": "1", "text": "g"}],
            "speakers": [{"line": 1, "offset": 0, "label": "Α."}],
        },
        {"id": "1:2", "lines": [{"n": 2, "ref": "2", "text": "g"}], "speakers": []},
    ]
    slots = m._greek_event_slots(segments, {"Α.": "Alpha"})
    assert [(s["segment"], s["line"], s["name"]) for s in slots] == [
        (0, 1, "Alpha"),
        (1, 2, None),
    ]


def test_an_unnamed_slot_never_steals_a_named_pair():
    """`_pair_turns` and its gap zip are deleted (turn-pairing-design-
    2026-09-15); the DP replaces the whole mechanism. The outcome P3.5
    finding 2 cared about survives: a speakerless lyric slot or an
    unattributed English continuation must not disrupt the named pairs
    either side of it, and a same-length, name-agreeing run still pairs
    position for position."""
    from drama_pipeline.pair_dp import EnglishNode, GreekNode, align

    def g(name):
        return GreekNode(name=name, chars=20)

    def e(name):
        return EnglishNode(name=name, chars=20)

    result = align([g("Alpha"), g(None), g("Gamma")], [e("Alpha"), e("Beta"), e("Gamma")], pins=[])
    assert (0, 0) in result.pairs and (2, 2) in result.pairs

    result = align([g("Alpha"), g("Beta"), g("Gamma")], [e("Alpha"), e(None), e("Gamma")], pins=[])
    assert (0, 0) in result.pairs and (2, 2) in result.pairs

    result = align([g("Alpha"), g(None), g("Gamma")], [e("Alpha"), e(None), e("Gamma")], pins=[])
    assert (0, 0) in result.pairs and (2, 2) in result.pairs

    # A named run of equal length still pairs position for position.
    result = align([g("Alpha"), g("Beta")], [e("Alpha"), e("Beta")], pins=[])
    assert result.pairs == [(0, 0), (1, 1)]


def test_crossed_antilabe_parks_on_its_own_share_and_reads_in_english_order(tmp_path):
    """P3.5 finding 4, the Frogs 405–406 shape.

    The Greek gives 405 to Xanthias and hands 406 to Dionysus part-way
    through, so both are shares of ONE segment; the translation speaks
    Dionysus first.  Dionysus pairs with his own share (the LCS keeps one of
    the two crossing pairs), and Xanthias' speech used to fall back to the
    cursor's share because the SEGMENT speaks him — the chunk then read
    Dionysus, Xanthias with both turns credited off Dionysus' slot.  Now the
    walk reaches the packed neighbour and Xanthias parks on the Xanthias
    share.  The emitted order stays the ENGLISH order, because slot order and
    English order cross here and printing the translation backwards would be
    worse than printing the shares out of order.
    """
    from drama_pipeline import stage1_turn_english as m

    # The park: Xanthias' speech (English 1) reaches slot 0, his own share,
    # instead of parking on the cursor's slot 1, and it stays CLEAN.
    assigned, residual, _head, unassigned, flags = _assign_speeches(
        2,
        [(1, 0)],
        2,
        greek_names=["Xanthias", "Dionysus"],
        english_names=["Dionysus", "Xanthias"],
        greek_alt=[{"Xanthias", "Dionysus"}, {"Xanthias", "Dionysus"}],
        greek_segments=[0, 0],
    )
    assert assigned == {0: [1], 1: [0]}
    assert (residual, unassigned, flags) == (1, 0, {})

    spine = {
        "work": "test",
        "segments": [
            {
                "id": "1:405", "book": 1, "column": "405",
                "lines": [
                    {"n": 405, "ref": "405", "text": "ξανθιας λεγει."},
                    {"n": 406, "ref": "406", "text": "λεγει τι· διονυσος λεγει."},
                ],
                "speakers": [
                    {"line": 405, "offset": 0, "label": "Ξα."},
                    {"line": 406, "offset": 10, "label": "Δι."},
                ],
            },
        ],
    }
    english, _footnotes, report = _one_liner(
        tmp_path,
        "DIONYSUS. Dionysus first.\nXANTHIAS. Xanthias second.",
        spine,
        {"Ξα.": "Xanthias", "Δι.": "Dionysus"},
        {"XANTHIAS": "Xanthias", "DIONYSUS": "Dionysus"},
    )
    assert (report["paired"], report["greek_events"]) == (1, 2)
    assert report["residual_grouped"] == 1
    assert report["residual_flagged"] == 0
    chunk = english["chunks"][0]
    assert chunk["text"] == "Dionysus first.\n\nXanthias second."
    assert [(turn["offset"], turn["speaker"]) for turn in chunk["turns"]] == [
        (0, "Dionysus"),
        (len("Dionysus first.\n\n"), "Xanthias"),
    ]
    assert all("speakerMismatch" not in turn for turn in chunk["turns"])


def test_flagged_extra_names_the_share_it_is_printed_in(tmp_path):
    """P3.5 finding 7, the Birds 1:280 shape.

    Euelpides speaks 277 and the Hoopoe takes 278 part-way through — one
    packed segment, two shares.  The 1912 translation puts a Peisthetaerus
    speech between them that the Greek edition does not, so it parks flagged;
    the flag must name the share the reader is standing in at that offset
    (Euelpides, whose share the speech is printed inside), not merely
    whichever slot the pairing last touched.  Slot order and English order
    agree here, so the chunk reads in share order.
    """
    spine = {
        "work": "test",
        "segments": [
            {
                "id": "1:280", "book": 1, "column": "280",
                "lines": [
                    {"n": 277, "ref": "280", "text": "τι το τερας τουτι ποτ' εστιν;"},
                    {"n": 278, "ref": "281", "text": "αλλα χουτος ετερος; ουτοσι."},
                ],
                "speakers": [
                    {"line": 277, "offset": 0, "label": "ΕΥ."},
                    {"line": 278, "offset": 20, "label": "ΕΠ."},
                ],
            },
            # Peisthetaerus is on the play's roster and speaks next, but his
            # Greek segment is past the window bound (the Hoopoe's share takes
            # the next pair), so the walk cannot reach it: the interposed
            # speech is flagged where it stands, not carried forward.
            {
                "id": "1:282", "book": 1, "column": "282",
                "lines": [{"n": 279, "ref": "282", "text": "τουτο μεν ουν."}],
                "speakers": [{"line": 279, "offset": 0, "label": "ΠΙ."}],
            },
        ],
    }
    english, _footnotes, report = _one_liner(
        tmp_path,
        "EUELPIDES. Here's another bird with a crest.\n"
        "PISTHETAERUS. Ah! that's curious.\n"
        "EPOPS. This bird is the son of Philocles.\n"
        "PISTHETAERUS. So that I am his grandfather.",
        spine,
        {"ΕΥ.": "Euelpides", "ΕΠ.": "Hoopoe", "ΠΙ.": "Peisthetaerus"},
        {
            "EUELPIDES": "Euelpides",
            "PISTHETAERUS": "Peisthetaerus",
            "EPOPS": "Hoopoe",
        },
    )
    assert report["paired"] == 3
    assert report["residual_flagged"] == 1
    turns = english["chunks"][0]["turns"]
    assert [turn["speaker"] for turn in turns] == [
        "Euelpides",
        "Peisthetaerus",
        "Hoopoe",
    ]
    assert "speakerMismatch" not in turns[0]
    assert turns[1]["speakerMismatch"] == {
        "english": "Peisthetaerus",
        "greek": "Euelpides",
    }
    assert "speakerMismatch" not in turns[2]


def test_residual_reaches_a_later_share_of_the_line_the_next_pair_sits_on():
    """P3.6 finding 1, the Birds 666 shape.

    The forward bound of the park window was the SLOT of the next pair.  When
    that pair kept the earlier share of a packed line (Hoopoe, slot 1), the
    later share of the same line (Peisthetaerus, slot 2) lay outside the
    window, and the segment-set fallback parked Peisthetaerus' speech on the
    Hoopoe slot — clean, but on the wrong share.  The bound now widens to the
    last share of that segment, so the speech reaches its own slot.
    """
    assigned, residual, _head, unassigned, flags = _assign_speeches(
        3,
        [(0, 0), (1, 2)],
        3,
        greek_names=["Alpha", "Hoopoe", "Peisthetaerus"],
        english_names=["Alpha", "Peisthetaerus", "Hoopoe"],
        greek_alt=[{"Alpha"}, {"Hoopoe", "Peisthetaerus"}, {"Hoopoe", "Peisthetaerus"}],
        greek_segments=[0, 1, 1],
    )
    assert assigned == {0: [0], 1: [2], 2: [1]}
    assert (residual, unassigned, flags) == (1, 0, {})

    # The bound never crosses into the NEXT segment for the exact-name pass:
    # the Peisthetaerus share in segment 2 is out of reach, so the speech is
    # shown flagged. R12 says WHERE -- on the next paired English's own
    # segment (1), not welded to the cursor's (0), because that is the Greek
    # just before the anchor this speech precedes.
    assigned, _r, _h, _u, flags = _assign_speeches(
        3,
        [(0, 0), (1, 2)],
        3,
        greek_names=["Alpha", "Hoopoe", "Peisthetaerus"],
        english_names=["Alpha", "Peisthetaerus", "Hoopoe"],
        greek_alt=[{"Alpha"}, {"Hoopoe"}, {"Peisthetaerus"}],
        greek_segments=[0, 1, 2],
    )
    assert assigned == {0: [0], 1: [1, 2], 2: []}
    assert flags == {1: "Hoopoe"}


def test_residual_prefers_the_slot_that_is_the_speaker_over_the_segment_set():
    """P3.5 finding 8.

    `speaks()` is true for EVERY slot of a segment whose lines carry the name,
    so the cursor's own segment always answered first and a later segment
    dedicated to that speaker was never tried.  The walk now looks for a slot
    whose own event IS the speaker before falling back to the segment set.
    """
    # Slot 0 (Alpha) and slot 2 (Gamma) are in the cursor's window; the
    # cursor's segment carries Gamma somewhere in its lines (a share past the
    # window bound), so the old fallback parked Gamma's speech on Alpha.
    assigned, residual, _head, unassigned, flags = _assign_speeches(
        3,
        [(0, 0)],
        2,
        greek_names=["Alpha", "Beta", "Gamma"],
        english_names=["Alpha", "Gamma"],
        greek_alt=[{"Alpha", "Gamma"}, {"Beta"}, {"Gamma"}],
        greek_segments=[0, 1, 2],
    )
    assert assigned == {0: [0], 1: [], 2: [1]}
    assert (residual, unassigned, flags) == (1, 0, {})

    # The segment-set fallback still catches what no slot in the window names:
    # Delta is nobody's own event, so the P3.3 clean park stands.
    fallback, fb_residual, _h, fb_unassigned, fb_flags = _assign_speeches(
        3,
        [(0, 0)],
        2,
        greek_names=["Alpha", "Beta", "Gamma"],
        english_names=["Alpha", "Delta"],
        greek_alt=[{"Alpha"}, {"Beta", "Delta"}, {"Gamma"}],
        greek_segments=[0, 1, 2],
    )
    assert fallback == {0: [0], 1: [1], 2: []}
    assert (fb_residual, fb_unassigned, fb_flags) == (1, 0, {})


def test_join_parts_drops_gutenberg_italic_underscores():
    """"(_to Dionysus_)" is Gutenberg's italics markup, not text (John, 2026-09-09)."""
    from drama_pipeline.stage1_turn_english import _join_parts
    assert _join_parts(["(_to Dionysus_) Your advice is in vain,", "I shall not vacate the chair."]) == "(to Dionysus) Your advice is in vain, I shall not vacate the chair."
    assert _join_parts(["a _b_ c", "", "d"]) == "a b c\n\nd"
    assert _join_parts(["snake_case stays"]) == "snake_case stays"


def test_join_parts_verse_keeps_source_line_breaks():
    """A verse-form translation prints one line per source line instead of
    running a speech together as one paragraph (John, 2026-09-14, "show verse
    as verse!!!!"); replacing every `\\n` with a space must reproduce exactly
    what the prose join already produces -- byte offsets must not move."""
    from drama_pipeline.stage1_turn_english import _join_parts
    parts = ["let them, and refuse", "The corpses, setting the Gods' laws at naught."]
    prose = _join_parts(parts)
    verse = _join_parts(parts, verse=True)
    assert verse == "let them, and refuse\nThe corpses, setting the Gods' laws at naught."
    assert verse.replace("\n", " ") == prose
    # a paragraph break (a blank source line) still prints as "\n\n"
    assert _join_parts(["a", "", "b"], verse=True) == "a\n\nb"
    # Gutenberg italics markup still strips within one line
    assert _join_parts(["(_to Dionysus_) hail"], verse=True) == "(to Dionysus) hail"


def test_mismatched_match_is_possible_but_priced():
    """`_pair_turns`' disagreeing zip is deleted (turn-pairing-design-
    2026-09-15, section 1: "the rule that holds the Frogs 83-87 exchange one
    turn out. Delete it."). Design section 3.2 replaces the free zip with a
    priced one: a disagreeing MATCH (Birds 223's Coulon-vs-1912-text
    re-attribution) must stay POSSIBLE, at a real cost (`w_spk`), never
    forbidden outright and never bought for free. Whichever the DP prefers
    for a single stray turn under default weights, the content is never
    silently dropped."""
    from drama_pipeline.pair_dp import EnglishNode, GreekNode, Weights, align

    g = [GreekNode(name="Euelpides", chars=20)]
    e = [EnglishNode(name="Pisthetaerus", chars=20)]
    cheap_skip = align(g, e, pins=[])
    assert cheap_skip.pairs == [(0, 0)] or (
        cheap_skip.greek_skips == [(0, 1)] and cheap_skip.english_skips == [0]
    )
    # Once skipping is made expensive, the mismatched match must still be
    # reachable -- the mechanism is possible, not structurally forbidden.
    forced_match = align(g, e, pins=[], weights=Weights(open_g=10.0, open_e=10.0))
    assert forced_match.pairs == [(0, 0)]


def test_pins_reanchor_a_swap_and_the_crossing_reads_off_the_names():
    """Item 6 pins (2026-09-09), Birds 223-226 in miniature: pins are
    UNCHANGED hard constraints under the DP (design 3.3) -- the translator
    swapped Euelpides and Pisthetaerus for the exchange, and a pin on the
    first speech with a run holds the whole exchange by position. A crossed
    pair is just one whose two names disagree, read directly off the result
    (the call site sets `speakerMismatch` from exactly this comparison)."""
    from drama_pipeline.pair_dp import EnglishNode, GreekNode, align

    g = [GreekNode(name=n, chars=20) for n in
         ["Hoopoe", "Euelpides", "Pisthetaerus", "Euelpides", "Pisthetaerus", "Chorus"]]
    e = [EnglishNode(name=n, chars=20) for n in
         ["Hoopoe", "Pisthetaerus", "Euelpides", "Pisthetaerus", "Euelpides", "Chorus"]]
    forced = [(1, 1), (2, 2), (3, 3), (4, 4)]
    result = align(g, e, pins=forced)
    assert set(forced) <= set(result.pairs)
    assert (0, 0) in result.pairs and (5, 5) in result.pairs
    crossed = {ej: g[gi].name for gi, ej in result.pairs if g[gi].name != e[ej].name}
    assert crossed == {1: "Euelpides", 2: "Pisthetaerus", 3: "Euelpides", 4: "Pisthetaerus"}

    with pytest.raises(ValueError):
        align(g, e, pins=[(3, 1), (1, 3)])


def test_resolve_pins_finds_the_speech_by_its_opening_words_and_fails_loud():
    from drama_pipeline import stage1_turn_english as m

    segments = [
        {"greek": [{"n": 1, "ref": "222"}]},
        {"greek": [{"n": 2, "ref": "223"}, {"n": 3, "ref": "224"}]},
        {"greek": [{"n": 4, "ref": "225"}]},
    ]
    slots = [
        {"segment": 0, "line": 1, "offset": 0, "name": "Hoopoe"},
        {"segment": 1, "line": 2, "offset": 0, "name": "Euelpides"},
        {"segment": 2, "line": 4, "offset": 0, "name": "Pisthetaerus"},
        {"segment": 2, "line": 4, "offset": 7, "name": "Euelpides"},
    ]
    speeches = [
        {"text": "Chase off drowsy sleep", "canonical": "Hoopoe"},
        {"text": "Oh! by Zeus!  what a throat", "canonical": "Pisthetaerus"},
        {"text": "Hush!", "canonical": "Euelpides"},
        {"text": "What's the matter?", "canonical": "Pisthetaerus"},
    ]
    refs = m._slot_refs(segments, slots)
    assert refs == ["222", "223", "225", "225"]
    assert m._resolve_pins([{"greek": "223", "english": "Oh! by Zeus! what a", "run": 2}], slots, refs, speeches, "t") == [(1, 1), (2, 2)]
    assert m._resolve_pins([{"greek": "225", "english": "Hush!"}], slots, refs, speeches, "t") == [(3, 2)]
    with pytest.raises(ValueError):
        m._resolve_pins([{"greek": "999", "english": "Hush!"}], slots, refs, speeches, "t")
    with pytest.raises(ValueError):
        m._resolve_pins([{"greek": "223", "english": "no such speech"}], slots, refs, speeches, "t")


def test_resolve_pins_reads_past_punctuation_footnotes_and_a_run_on_quote():
    """Item 6 review pins (2026-09-09): a reviewer quotes what the reader
    shows -- footnote markers, curly quotes and a leading stage note
    dropped, and sometimes two short turns run together."""
    from drama_pipeline import stage1_turn_english as m

    segments = [{"greek": [{"n": 1, "ref": "10"}, {"n": 2, "ref": "11"}, {"n": 3, "ref": "12"}]}]
    slots = [
        {"segment": 0, "line": 1, "offset": 0, "name": "Scythian"},
        {"segment": 0, "line": 2, "offset": 0, "name": "Euripides"},
        {"segment": 0, "line": 3, "offset": 0, "name": "Mnesilochus"},
    ]
    speeches = [
        {"text": "Aye, that I will.", "canonical": "Scythian"},
        {"text": "Hand over the money.", "canonical": "Euripides"},
        {"text": '(as Helen) "These shores[^3.1] are those of the Nile"', "canonical": "Mnesilochus"},
    ]
    refs = m._slot_refs(segments, slots)
    assert m._resolve_pins([{"greek": "10", "english": "Aye, that I will. Hand over the money."}], slots, refs, speeches, "t") == [(0, 0)]
    assert m._resolve_pins([{"greek": "12", "english": "These shores are those"}], slots, refs, speeches, "t") == [(2, 2)]


def test_resolve_pins_snaps_inside_a_greek_speech_and_settles_duplicates():
    from drama_pipeline import stage1_turn_english as m

    segments = [{"greek": [{"n": 1, "ref": "340"}, {"n": 2, "ref": "342a"}, {"n": 3, "ref": "345"}, {"n": 4, "ref": "348"}]}]
    slots = [
        {"segment": 0, "line": 1, "offset": 0, "name": "Philocleon"},
        {"segment": 0, "line": 2, "offset": 0, "name": "Chorus"},
        {"segment": 0, "line": 4, "offset": 0, "name": "Philocleon"},
    ]
    speeches = [
        {"text": "Tell us.", "canonical": "Philocleon"},
        {"text": "He would not have dared, had he", "canonical": "Chorus"},
        {"text": "Tell us.", "canonical": "Philocleon"},
    ]
    refs = m._slot_refs(segments, slots)
    notes: list[str] = []
    # 345 has no speaker change: the pin snaps to the Chorus slot at 342a
    # (the speech's own speaker), not to Philocleon's at 348 though nearer.
    assert m._resolve_pins([{"greek": "345", "english": "He would not have dared"}], slots, refs, speeches, "t", notes) == [(1, 1)]
    assert notes and "snapped back to slot 342a" in notes[0]
    # A short speech printed twice: the occurrence nearest the slot's position.
    assert m._resolve_pins([{"greek": "348", "english": "Tell us."}], slots, refs, speeches, "t") == [(2, 2)]
    # Two pins on one slot: the first holds, the second is noted and skipped.
    notes.clear()
    forced = m._resolve_pins(
        [{"greek": "342a", "english": "He would not"}, {"greek": "342a", "english": "Tell us."}],
        slots, refs, speeches, "t", notes,
    )
    assert forced == [(1, 1)] and any("already pinned" in n for n in notes)
    # One speech pinned to two lines: the later pin replaces the earlier.
    notes.clear()
    forced = m._resolve_pins(
        [{"greek": "340", "english": "He would not"}, {"greek": "342a", "english": "He would not"}],
        slots, refs, speeches, "t", notes,
    )
    assert forced == [(1, 1)] and any("replaces the earlier pin" in n for n in notes)
    # A pin that crosses an earlier one (Greek order against English order)
    # is skipped with a note rather than failing the play.  (Unique texts:
    # a repeated speech now settles between its neighbouring pins, which
    # keeps the order and so never crosses.)
    notes.clear()
    crossed = speeches[:2] + [{"text": "Speak.", "canonical": "Philocleon"}]
    forced = m._resolve_pins(
        [{"greek": "342a", "english": "Tell us."}, {"greek": "340", "english": "He would not"}],
        slots, refs, crossed, "t", notes,
    )
    assert forced == [(1, 0)] and any("crosses the pin" in n for n in notes)
    with pytest.raises(ValueError):
        m._resolve_pins([{"greek": "400", "english": "Tell us."}], slots, refs, speeches, "t")


def test_apply_splits_cuts_a_run_together_speech_at_the_greek_change():
    from drama_pipeline import stage1_turn_english as m

    speeches = [
        {"speaker_printed": "DIONYSUS", "text": "Oh! my god! how white I went. But yonder[^2.9] fellow got red instead!"},
        {"speaker_printed": "XANTHIAS", "text": "Where are we?"},
    ]
    m._apply_splits(speeches, [{"english": "But yonder fellow got red", "speaker": "XANTHIAS"}], "t")
    assert [s["speaker_printed"] for s in speeches] == ["DIONYSUS", "XANTHIAS", "XANTHIAS"]
    assert speeches[0]["text"] == "Oh! my god! how white I went."
    assert speeches[1]["text"].startswith("But yonder[^2.9] fellow got red")
    with pytest.raises(ValueError):
        m._apply_splits(speeches, [{"english": "no such words", "speaker": "XANTHIAS"}], "t")
    with pytest.raises(ValueError):
        m._apply_splits(speeches, [{"english": "Where are we", "speaker": "DIONYSUS"}], "t")
    # Already a speech start: with a greek ref it becomes a pin instead.
    assert m._apply_splits(speeches, [{"greek": "5", "english": "Where are we", "speaker": "DIONYSUS"}], "t") == [
        {"greek": "5", "english": "Where are we", "run": 1}
    ]


def test_apply_splits_is_whole_word_unique_and_pins_greek():
    """Astra lane C, F6: no substring cuts; one match position; greek becomes a pin."""
    from drama_pipeline import stage1_turn_english as m

    speeches = [
        {
            "speaker_printed": "A",
            "text": "I therefore agree to wait for your reply. There will be another chance after we finish.",
        }
    ]
    pins = m._apply_splits(
        speeches,
        [{"english": "there", "speaker": "B", "greek": "30"}],
        "t",
    )
    assert speeches[0]["text"] == "I therefore agree to wait for your reply."
    assert speeches[1]["speaker_printed"] == "B"
    assert speeches[1]["text"].startswith("There will be another chance")
    assert pins == [{"greek": "30", "english": "there", "run": 1}]

    doubled = [{"speaker_printed": "A", "text": "Go there now, then wait there later."}]
    with pytest.raises(ValueError, match="matches 2 positions"):
        m._apply_splits(doubled, [{"english": "there", "speaker": "B"}], "t")


def test_resolve_pins_places_a_repeated_speech_between_the_neighbouring_pins():
    """Peace 1337: two identical "What shall we do to her?" between the pins
    at 1333 and 1346. Ten early slots the translation lacks make the
    play-wide proportion point at the second; the anchors either side put
    the pin on the first."""
    from drama_pipeline import stage1_turn_english as m

    refs_g = [str(100 + i) for i in range(10)] + ["1333", "1337", "1338", "1339", "1340", "1346"]
    segments = [{"greek": [{"n": i + 1, "ref": r} for i, r in enumerate(refs_g)]}]
    names = ["Chorus"] * 10 + ["Chorus", "Trygaeus", "Chorus", "Trygaeus", "Chorus", "Trygaeus"]
    slots = [{"segment": 0, "line": i + 1, "offset": 0, "name": nm} for i, nm in enumerate(names)]
    texts = ["Early one.", "Early two.", "Oh! thrice happy man", "Oh! Hymen!", "Oh! Hymen!",
             "What shall we do to her?", "What shall we do to her?", "We will gather her kisses.",
             "We will gather her kisses.", "Come, comrades", "You shall have a fine house"]
    speeches = [{"text": x, "canonical": "Chorus"} for x in texts]
    refs = m._slot_refs(segments, slots)
    pins = [
        {"greek": "1346", "english": "You shall have a fine house"},
        {"greek": "1337", "english": "What shall we do to her?", "run": 4},
        {"greek": "1333", "english": "Oh! thrice happy man"},
    ]
    forced = m._resolve_pins(pins, slots, refs, speeches, "t")
    assert (11, 5) in forced and (12, 6) in forced and (13, 7) in forced and (14, 8) in forced
    # With no other pin the play-wide proportion still decides.
    assert m._resolve_pins([pins[1]], slots, refs, speeches, "t")[0] == (11, 6)


def test_resolve_pins_caps_a_long_run_and_refuses_a_line_inside_another_speaker():
    from drama_pipeline import stage1_turn_english as m

    names = ["A", "B"] * 6
    segments = [{"greek": [{"n": i + 1, "ref": str(100 + i)} for i in range(12)]}]
    slots = [{"segment": 0, "line": i + 1, "offset": 0, "name": nm} for i, nm in enumerate(names)]
    speeches = [{"text": f"speech {i}", "canonical": nm} for i, nm in enumerate(names)]
    refs = m._slot_refs(segments, slots)
    notes: list[str] = []
    # A run of 12 holds eight pairs by position; the LCS carries the rest.
    forced = m._resolve_pins([{"greek": "100", "english": "speech 0", "run": 12}], slots, refs, speeches, "t", notes)
    assert forced == [(k, k) for k in range(8)] and any("capped at 8" in n for n in notes)
    # Peace 1227: the line sits inside A's speech, but the English speech is
    # B's -- the translation divides the passage differently; fail loud.
    slots2 = [{"segment": 0, "line": 1, "offset": 0, "name": "A"}, {"segment": 0, "line": 4, "offset": 0, "name": "B"}]
    refs2 = m._slot_refs(segments, slots2)
    with pytest.raises(ValueError, match="divides the passage differently"):
        m._resolve_pins([{"greek": "101", "english": "speech 1"}], slots2, refs2, speeches, "t")


def test_stage2_strict_coverage_names_every_undeclared_hole(tmp_path, monkeypatch):
    """Item 6 (John, 2026-09-09): with english.strict_coverage a Greek
    speech with no English of its own fails the build unless declared."""
    base = {
        "work": "test-play",
        "pairing_rate": 0.99,
        "paired": 100,
        "length_ratio_outlier_count": 10,
        "turn_shift_count": 2,
        "turn_shift_rate": 0.02,
        "turn_shift_new_drifts": 2,
    }
    loose = _stage2_with_report(monkeypatch, tmp_path, base, _turn_text_manifest(), unmatched_ids=("1:2",))
    assert "turn_text_strict_coverage" not in loose["checks"]
    strict = _stage2_with_report(
        monkeypatch, tmp_path, base, _turn_text_manifest(strict_coverage=True), unmatched_ids=("1:2",)
    )
    check = strict["checks"]["turn_text_strict_coverage"]
    assert check["ok"] is False and check["holes"] == ["1:2"] and "declared: 2" in check["error"]
    declared = _stage2_with_report(
        monkeypatch, tmp_path, base, _turn_text_manifest(strict_coverage=True, gaps=["2"]), unmatched_ids=("1:2",)
    )
    assert declared["checks"]["turn_text_strict_coverage"]["ok"] is True


def test_resolve_covered_maps_first_line_refs_to_segments_and_fails_loud():
    from drama_pipeline import stage1_turn_english as m

    segments = [
        {"id": "1:777", "lines": [{"n": 1, "ref": "777"}]},
        {"id": "1:778", "lines": [{"n": 2, "ref": "778"}, {"n": 3, "ref": "779"}]},
    ]
    assert m._resolve_covered([{"greek": "777", "by": "778"}], segments, "t") == {"1:777": "1:778"}
    joined = [{"id": "1:873-875", "lines": [{"n": 1, "ref": "873-875"}]}, {"id": "1:878", "lines": [{"n": 2, "ref": "878"}]}]
    assert m._resolve_covered([{"greek": "878", "by": "873"}], joined, "t") == {"1:878": "1:873-875"}
    # A line that no longer opens a segment covers nothing (John, 2026-09-11:
    # the 40-line cap now meets the English's speech starts, so declared
    # openers can move inside a segment); a line the play lacks is a typo.
    assert m._resolve_covered([{"greek": "779", "by": "778"}], segments, "t") == {}
    with pytest.raises(ValueError):
        m._resolve_covered([{"greek": "999", "by": "778"}], segments, "t")
    with pytest.raises(ValueError):
        m._resolve_covered([{"greek": "777", "by": "777"}], segments, "t")


def test_owning_covered_follows_chains_and_fails_cycles():
    """Astra lane C, F7: emit the English-holding segment; fail cycles.

    A CYCLE stays a hard failure (a real bug: ``_resolve_covered`` never
    produces one on its own). A chain that reaches no English used to raise
    too, but round 2 task 3 of the turn-pairing fix (Peace and Wasps: a
    manifest-declared `covered` target losing its own chunk under the new
    DP pairing) downgrades that one case to a dropped, warned-about
    declaration -- named in the optional `stale_report` list rather than
    crashing the build.
    """
    from drama_pipeline import stage1_turn_english as m

    covered = {"1:443": "1:449", "1:449": "1:447"}
    assert m._owning_covered(covered, {"1:447"}, "peace") == {
        "1:443": "1:447",
        "1:449": "1:447",
    }
    with pytest.raises(ValueError, match="covered cycle"):
        m._owning_covered({"1:29": "1:30", "1:30": "1:29"}, set(), "t")
    stale: list[dict] = []
    assert m._owning_covered({"1:29": "1:30"}, set(), "t", stale_report=stale) == {}
    assert stale == [{"greek": "1:29", "chain": ["1:29", "1:30"]}]


_CLOUDS_MANIFEST_PATH = Path(__file__).resolve().parents[2] / "manifests" / "clouds.yaml"


def _clouds_export_xml_path() -> Path | None:
    # A from-scratch drama checkout may not carry manifests/clouds.yaml at
    # all -- check for the manifest itself first so collection never raises
    # before the skipif below gets a chance to run (same guard shape as
    # test_stage1_lined_source.py's `requires_export`).
    if not _CLOUDS_MANIFEST_PATH.exists():
        return None
    from drama_pipeline import stage1_greek

    manifest = Manifest.for_work("clouds")
    return stage1_greek.exported_xml_path(manifest)


_clouds_export = _clouds_export_xml_path()

requires_clouds_export = pytest.mark.skipif(
    _clouds_export is None or not _clouds_export.exists(),
    reason="build/export's Diogenes TLG export for Clouds (author 0019, "
           "work 003) is not present in this checkout -- run the Diogenes "
           "export recipe in docs/tlg-phi-export.md before this test can "
           "build the real Greek spine",
)


def _clouds_third_chunks(pins: list[dict]) -> dict:
    """The real Arrowsmith `third`-slot English, cut on the real Clouds
    Greek spine, exactly as `stage1_turn_english.run(manifest, spine,
    slot="third")` builds it -- with `pins` substituted for the manifest's
    own, so the caller can test with and without the Clouds 102 pin."""
    from drama_pipeline import stage1_greek
    from drama_pipeline.stage1_turn_english import (
        _aliases_for_slot,
        _SiglaResolver,
        _spread_long_speeches,
        chunks_as_overlay,
    )

    manifest = Manifest.for_work("clouds")
    xml_path = stage1_greek.run_export(manifest)
    spine = stage1_greek.parse_spine(xml_path, manifest)
    cfg = manifest.data["english"]["third"]
    speakers = manifest.data["speakers"]
    aliases = _aliases_for_slot(speakers, "third", cfg["id"])
    sigla = _SiglaResolver(manifest)
    english, _footnotes, _report = parse_translation(
        SOURCES_DIR / cfg["source"],
        spine,
        work_id=manifest.work_id,
        translation_id=cfg["id"],
        play=cfg["play"],
        sigla=sigla,
        english_aliases=aliases,
        footnotes_enabled=bool(cfg.get("footnotes", False)),
        format=cfg.get("format") or "gutenberg",
        line_fixes=cfg.get("line_fixes") or {},
        pins=pins,
        splits=cfg.get("splits") or [],
        covered=cfg.get("covered") or [],
    )
    english["chunks"] = _spread_long_speeches(english.get("chunks") or [], spine.get("segments") or [], sigla)
    return chunks_as_overlay(english)


@requires_clouds_export
def test_clouds_102_pin_keeps_the_thinkery_identification_off_of_the_stall():
    # Codex re-review finding 4 (2026-09-11): none of the eight tests added
    # for finding 7 actually exercised the Thinkery alignment the "102" pin
    # fixes. Arrowsmith's own stalling exchange ("Fine. Who are they?" /
    # "Er . . . Gentlemen. Men of Learning.") sits right before the Greek
    # 102 turn that names Socrates and Chaerephon.
    #
    # Under the name-LCS pairer this pin was load-bearing: without it, the
    # zip still "agreed" turn for turn on the inserted pair and shifted
    # everything one slot early. Under the turn-pairing DP (design
    # 2026-09-15) the pin is a no-op here -- exactly what section 3.5
    # predicts ("expected to become mostly no-ops; measured, not deleted"):
    # the length and position terms alone now place the stalling exchange at
    # 1:100 and the identification at 1:102 with no pin at all. The pin
    # stays in the manifest (pins are not deleted in this change) and this
    # test now documents the improvement instead of the old regression.
    manifest = Manifest.for_work("clouds")
    real_pins = manifest.data["english"]["third"].get("pins") or []
    assert any(p.get("greek") == "102" for p in real_pins), (
        "the Clouds 102 pin is missing from manifests/clouds.yaml -- this "
        "test can no longer prove the pin still resolves (or has become a "
        "no-op for) the alignment"
    )

    with_pin = _clouds_third_chunks(real_pins)
    assert "Chairephon and that humbug, Sokrates" in with_pin["1:102"][0]["text"]
    assert "Fine. Who are they?" not in with_pin["1:102"][0]["text"]

    # The pin is now a no-op: the same build, minus the 102 pin, still gets
    # the identification right without it.
    without_102 = [p for p in real_pins if p.get("greek") != "102"]
    assert len(without_102) < len(real_pins)
    unpinned = _clouds_third_chunks(without_102)
    assert "Fine. Who are they?" in unpinned["1:100"][0]["text"]
    assert "Chairephon and that humbug, Sokrates" in unpinned["1:102"][0]["text"]


_BACCHAE_MANIFEST_PATH = Path(__file__).resolve().parents[2] / "manifests" / "bacchae.yaml"


def _bacchae_export_xml_path() -> Path | None:
    if not _BACCHAE_MANIFEST_PATH.exists():
        return None
    from drama_pipeline import stage1_greek

    manifest = Manifest.for_work("bacchae")
    return stage1_greek.exported_xml_path(manifest)


_bacchae_export = _bacchae_export_xml_path()

requires_bacchae_export = pytest.mark.skipif(
    _bacchae_export is None or not _bacchae_export.exists(),
    reason="build/export's Diogenes TLG export for Bacchae (author 0006, "
           "work 050) is not present in this checkout -- run the Diogenes "
           "export recipe in docs/tlg-phi-export.md before this test can "
           "build the real Greek spine",
)


@requires_bacchae_export
def test_bacchae_greek_spine_corrects_the_export_parodos_ref():
    """The export's lone 1448a typo builds as 148a, in printed order."""
    from drama_pipeline import stage1_greek

    manifest = Manifest.for_work("bacchae")
    spine = stage1_greek.parse_spine(stage1_greek.run_export(manifest), manifest)
    refs = [line["ref"] for segment in spine["segments"] for line in segment["lines"]]
    parodos = refs[refs.index("147"):refs.index("149") + 1]
    assert parodos == ["147", "148a", "148b", "149"]
    assert "1448a" not in refs


def _bacchae_murray_chunks(pins: list[dict]) -> dict:
    """The real Murray overlay English, cut on the real Bacchae Greek spine,
    exactly as `stage1_turn_english.run(manifest, spine, slot="overlay",
    overlay_entry=...)` builds it -- with `pins` substituted for the
    manifest's own, so the caller can test with and without the second
    messenger's pins."""
    from drama_pipeline import stage1_greek
    from drama_pipeline.stage1_turn_english import (
        _aliases_for_slot,
        _SiglaResolver,
        _spread_long_speeches,
        chunks_as_overlay,
    )

    manifest = Manifest.for_work("bacchae")
    xml_path = stage1_greek.run_export(manifest)
    spine = stage1_greek.parse_spine(xml_path, manifest)
    overlays = manifest.data["english"]["overlays"]
    cfg = next(o for o in overlays if o["id"] == "murray-verse")
    speakers = manifest.data["speakers"]
    aliases = _aliases_for_slot(speakers, "overlay", cfg["id"])
    sigla = _SiglaResolver(manifest)
    # Bacchae's primary is perseus-play (a tragedy): `run()` bridges every
    # turn-text slot -- including an overlay -- against it (design 3.2, term
    # B), so this direct `parse_translation` call must build and pass the
    # same bridge `run()` would, or it is testing a code path no play ever
    # takes in the real pipeline.
    from drama_pipeline import stage1_perseus_play_english

    primary_cfg = manifest.data["english"]["primary"]
    assert primary_cfg.get("model") == "perseus-play"
    primary_english, _primary_footnotes, _primary_report = stage1_perseus_play_english.parse_translation(
        SOURCES_DIR / primary_cfg["source"],
        spine,
        work_id=manifest.work_id,
        covered_decl=primary_cfg.get("covered") or [],
        translation_id=primary_cfg["id"],
        sigla=sigla,
        english_aliases=speakers.get("english") or {},
    )
    primary_bridge = {c["id"]: c for c in primary_english.get("chunks") or []}
    english, _footnotes, _report = parse_translation(
        SOURCES_DIR / cfg["source"],
        spine,
        work_id=manifest.work_id,
        translation_id=cfg["id"],
        play=cfg["play"],
        sigla=sigla,
        english_aliases=aliases,
        footnotes_enabled=bool(cfg.get("footnotes", False)),
        format=cfg.get("format") or "gutenberg",
        line_fixes=cfg.get("line_fixes") or {},
        pins=pins,
        splits=cfg.get("splits") or [],
        covered=cfg.get("covered") or [],
        primary_bridge=primary_bridge,
    )
    english["chunks"] = _spread_long_speeches(english.get("chunks") or [], spine.get("segments") or [])
    return chunks_as_overlay(english)


@requires_bacchae_export
def test_bacchae_murray_second_messenger_pins_keep_the_death_report_on_its_own_line():
    # Codex review (2026-09-12): Murray's cast list says "TWO MESSENGERS" but
    # he cues both the herdsman and Pentheus' servant MESSENGER in the text
    # itself, while the Greek splits into Messenger/Second Messenger at 1024
    # (speakers.overrides). With no anchor, the second messenger's
    # stichomythia with the Chorus (1024-1042) and his death report (1043ff)
    # fall into the same "equal-length gap" the Dionysus/Pentheus dressing
    # scene just vacated, and the whole run -- LEADER's cue to speak and the
    # death report itself -- drifts forward onto 1:1153, the Chorus's ode
    # after the report, instead of the second messenger's own lines.
    manifest = Manifest.for_work("bacchae")
    overlays = manifest.data["english"]["overlays"]
    cfg = next(o for o in overlays if o["id"] == "murray-verse")
    real_pins = cfg.get("pins") or []
    assert any(p.get("greek") == "1024" for p in real_pins) and any(
        p.get("greek") == "1043" for p in real_pins
    ), (
        "the Bacchae second-messenger pins are missing from "
        "manifests/bacchae.yaml -- this test can no longer prove the pins "
        "(rather than a coincidence) fix the alignment"
    )

    with_pins = _bacchae_murray_chunks(real_pins)
    assert "We climbed beyond the utmost habitings" in with_pins["1:1043"][0]["text"]
    assert "Speak of the mountain side" in with_pins["1:1041"][0]["text"]
    assert "We climbed beyond" not in with_pins["1:1153"][0]["text"]
    assert "Weave ye the dance" in with_pins["1:1153"][0]["text"]

    # Round 3 (turn-pairing-round3-2026-09-15.md, P1): the pins are no longer
    # load-bearing for this shape. `pair_dp` now inherits the preceding named
    # speaker onto a speakerless continuation slot before matching it
    # (defect 1's fix), so the second messenger's death report lands on its
    # own line even with the pins removed -- the regression this assertion
    # used to reproduce ("minus the two pins") no longer reproduces, because
    # the fix is in the alignment itself, not only in the manifest's pins.
    # Rule 5's inherited discipline: a test asserting a bug's reproduction is
    # a claim about the deleted defect, not a reader outcome, and it is
    # replaced here with the outcome the pins and the fix both now agree on.
    unpinned = _bacchae_murray_chunks([])
    assert "We climbed beyond the utmost habitings" in unpinned["1:1043"][0]["text"]
    assert "Weave ye the dance" in unpinned["1:1153"][0]["text"]
    assert "We climbed beyond" not in unpinned["1:1153"][0]["text"]
def test_loeb_ocr_roman_numeral_heading_is_not_a_speaker():
    text = "\n".join([
        "HERACLES",
        "",
        "CHORUS. First the grove of Zeus he freed",
        "I. The Nemean Lion",
        "Of the lion, and about his shoulders bound",
        "II. The Centaurs",
        "The hide of the beast.",
        "AMPHITRYON. Enough.",
    ])
    speeches, _notes = parse_play_speeches(text, "HERACLES", format="loeb-ocr")
    assert [sp["speaker_printed"] for sp in speeches] == ["CHORUS", "AMPHITRYON"]
    assert "I. The Nemean Lion" in speeches[0]["text"]
    assert "II. The Centaurs" in speeches[0]["text"]


# --- Round 9: the Persians parodos, the shape `_spread_long_speeches` governs.
#
# One Chorus speech, Greek 1-158, which the segmenter cut across six segments
# (64 + 42 + 28 + 10 + 5 + 4 = 153 lines): 1:1 named, 1:65 and 1:111 with no
# speaker event at all, and 1:140 / 1:150 / 1:155 each opening on a bare "—".
# Round 7's `_align_speech_runs` merges all six into ONE DP node, so the whole
# of Johnston's English -- 140 printed verse lines -- lands on 1:1 and the
# spread has to hand it back out. The character counts are chosen so the
# density readings match the real build's: 1.78x the column median at 1:65,
# 1.08x at 1:111, 0.85x at 1:140.
_PERSIANS_RUN = [("1:1", 64), ("1:65", 42), ("1:111", 28), ("1:140", 10), ("1:150", 5), ("1:155", 4)]


def _persians_parodos():
    from drama_pipeline.stage1_turn_english import _printed_line_starts

    def glines(first, count):
        # No Greek stop anywhere: `_greek_breaks` finds nothing, so every
        # segment aims at its own first line and the cut is the proportion,
        # undisturbed by the 1.5-line sentence snap.
        return [{"n": n, "ref": str(n), "text": "λόγος ἄλλος ἔτι"}
                for n in range(first, first + count)]

    segments = []
    n = 1
    for i, (sid, size) in enumerate(_PERSIANS_RUN):
        seg = {"id": sid, "column": "1", "lines": glines(n, size)}
        if i == 0:
            seg["speakers"] = [{"line": n, "offset": 0, "label": "CHORUS"}]
        elif i >= 3:
            seg["speakers"] = [{"line": n, "offset": 0, "label": "—"}]
        segments.append(seg)
        n += size
    # Two one-line segments with English of their own, to set the column
    # median at 55 characters per Greek line, which puts the run's density
    # readings on the real build's: 1.79x at 1:65, 1.08x at 1:111, 0.854x at
    # 1:140 (the real Persians build reads 1.787, 1.079, 0.854).
    segments += [
        {"id": "1:159", "column": "1", "lines": glines(200, 1),
         "speakers": [{"line": 200, "offset": 0, "label": "ΒΑ."}]},
        {"id": "1:160", "column": "1", "lines": glines(201, 1),
         "speakers": [{"line": 201, "offset": 0, "label": "CHORUS"}]},
    ]
    # 140 printed lines: 60 long ones (the anapaestic catalogue) then 80 short
    # ones (the lyric). Characters per printed line therefore differ by more
    # than two to one across the speech, which is where a cut measured in
    # characters and a cut measured in lines part company. Every line opens on
    # a capital so that the sentence-start pool and the printed-line pool hold
    # the same offsets: the two cuts below then differ only in the METRIC.
    long_line = "Streaming out of Susa and the ancient parapets of Kissa."
    short_line = "And groans with fierce desire."
    lines = [f"{long_line[:-1]} {i}." for i in range(60)]
    lines += [f"{short_line[:-1]} {i}." for i in range(80)]
    text = "\n".join(lines)
    assert len(_printed_line_starts(text)) == 140
    head = {"id": "1:1", "book": 1, "column": "1", "text": text,
            "notes": [], "markers": [], "bekker": [],
            "turns": [{"offset": 0, "speaker": "Chorus", "display": "CHORUS LEADER"}]}
    filler = lambda cid: {"id": cid, "book": 1, "column": "1", "text": "x" * 55,
                          "notes": [], "markers": [], "bekker": [], "turns": []}
    chunks = [head, filler("1:159"), filler("1:160")]
    covered = {sid: "1:1" for sid, _size in _PERSIANS_RUN[1:]}
    return chunks, segments, covered


def _printed(text):
    import re as _re

    return [l for l in text.split("\n")
            if l.strip() and not _re.fullmatch(r"_.*_", l.strip())]


def test_the_spread_reaches_every_segment_the_aligner_merged_into_one_speech():
    """Persians 1-158, Johnston (round 8 §1.4, findings 6, 7 and 13).

    The unvouched half asserts the WRONG behaviour deliberately, and says so:
    `_continuation_kind` refuses the three bare-dash segments because the
    bare-dash test wants `stacked >= 2.5` and a lyric run reads 0.85 -- the
    English is thinner per Greek line than the dialogue that sets the column
    median, so no long lyric can ever pass it. Refusing them does not merely
    empty 1:140-1:155: it shortens the denominator of the proportional cut,
    so the three segments that DO get English take 67, 44 and 29 printed lines
    against Greek spans of 64, 42 and 28. Vouched by the aligner's own
    derived-covered map, every segment of the speech takes its share.
    """
    from drama_pipeline.stage1_turn_english import _spread_long_speeches

    chunks, segments, covered = _persians_parodos()
    shipped = {c["id"]: c["text"] for c in _spread_long_speeches(chunks, segments, verse=True)}
    assert [len(_printed(shipped[sid])) if sid in shipped else None
            for sid, _size in _PERSIANS_RUN] == [67, 44, 29, None, None, None]

    out = {c["id"]: c["text"]
           for c in _spread_long_speeches(chunks, segments, covered=covered, verse=True)}
    got = [len(_printed(out[sid])) for sid, _size in _PERSIANS_RUN]
    assert got == [59, 38, 26, 9, 4, 4]
    assert sum(got) == 140
    # Each segment's English within one printed line of its Greek's share of
    # the run -- which is what "line for line" means across a cut speech.
    total_greek = sum(size for _sid, size in _PERSIANS_RUN)
    for (sid, size), lines in zip(_PERSIANS_RUN, got):
        assert abs(lines - 140 * size / total_greek) <= 1.0, sid


def test_a_verse_cut_is_measured_in_printed_lines_and_falls_on_a_line():
    """The same run, cut by characters (prose) and by printed lines (verse).

    A verse column renders line for line, so the unit of the cut is the
    translator's printed line: measured in characters, the 60 long lines of
    the catalogue eat the head's whole budget and it keeps only 40 of the 59
    lines its Greek is owed, with the shortfall pushed down the run. No piece
    may begin inside a verse either -- a line split across two segments is a
    verse broken across two rows.
    """
    from drama_pipeline.stage1_turn_english import _spread_long_speeches, _printed_line_starts

    chunks, segments, covered = _persians_parodos()
    text = chunks[0]["text"]
    by_chars = {c["id"]: c["text"]
                for c in _spread_long_speeches(chunks, segments, covered=covered, verse=False)}
    assert [len(_printed(by_chars[sid])) for sid, _size in _PERSIANS_RUN] == [44, 39, 34, 12, 6, 5]

    out = _spread_long_speeches(chunks, segments, covered=covered, verse=True)
    starts = set(_printed_line_starts(text))
    at = 0
    for piece in out:
        if piece["id"] not in dict(_PERSIANS_RUN):
            continue
        at = text.index(piece["text"].split("\n")[0], at)
        assert at in starts, piece["id"]
    # Every printed line of the speech survives the cut, in order, whole.
    assert [l for c in out if c["id"] in dict(_PERSIANS_RUN)
            for l in _printed(c["text"])] == _printed(text)


def test_a_turn_too_far_from_the_boundary_is_marking_something_else():
    """Way's Heracles ode at 755 (round 9).

    One Chorus speech over five segments of 2 / 54 / 3 / 2 / 2 Greek lines,
    each continuation opening on a bare "—", against seventy-four printed
    English lines whose four turns all fall inside the first twelve: Way
    divides the opening exchange and runs the rest of the ode together. The
    count test (`turns_left >= dashes_left`) passes on that by coincidence,
    and the rule then took the last remaining turn for a boundary
    forty-six Greek lines further on -- fifty-eight of the seventy-four lines
    landed on a three-line segment while the fifty-four-line segment kept
    nine. A turn that marks a segment's opening stands within that segment's
    own Greek span of it in proportion; this one is forty-six lines out, so
    the ordinary pool decides and the long segment keeps its share.
    """
    from drama_pipeline.stage1_turn_english import _spread_long_speeches

    sizes = [2, 54, 3, 2, 2]
    ids = ["1:755", "1:757", "1:815", "1:818", "1:820"]
    segments = []
    n = 750
    for i, (sid, size) in enumerate(zip(ids, sizes)):
        segments.append({
            "id": sid, "column": "1",
            "lines": [{"n": m, "ref": str(m), "text": "λόγος ἄλλος"} for m in range(n, n + size)],
            "speakers": [{"line": n, "offset": 0, "label": "CHORUS" if i == 0 else "—"}],
        })
        n += size
    segments.append({"id": "1:822", "column": "1", "lines": [{"n": 900, "text": "λ"}],
                     "speakers": [{"line": 900, "offset": 0, "label": "IRIS"}]})
    lines = [f"Line {i} of the ode that Way runs together." for i in range(74)]
    text = "\n".join(lines)
    # Four turns, all inside the first twelve printed lines.
    offsets = [0] + [text.index(lines[i]) for i in (3, 8, 11)]
    head = {"id": "1:755", "book": 1, "column": "1", "text": text,
            "notes": [], "markers": [], "bekker": [],
            "turns": [{"offset": o, "speaker": "Chorus"} for o in offsets]}
    filler = {"id": "1:822", "book": 1, "column": "1", "text": "x" * 45,
              "notes": [], "markers": [], "bekker": [], "turns": []}
    covered = {sid: "1:755" for sid in ids[1:]}

    out = {c["id"]: c["text"]
           for c in _spread_long_speeches([head, filler], segments, covered=covered, verse=True)}
    got = [len(_printed(out[sid])) if sid in out else 0 for sid in ids]
    assert got == [2, 64, 3, 3, 2]
    # The fifty-four-line segment keeps the bulk; nothing lands on a
    # three-line segment that its own Greek cannot hold.
    assert got[1] > 0.7 * 74 and got[2] <= 2 * sizes[2]


# Sol re-check finding 8 (2026-09-16): `margin_p10`'s index was
# `floor(0.1n) - 1`, which undercounts nearest-rank -- for n=11 it picked
# index 0 (the 1st of 11 sorted margins) where nearest-rank picks index 1
# (the 2nd, at or above which 10% of the data falls). Fixed to
# `max(0, ceil(0.10n) - 1)`.
def test_p10_index_is_nearest_rank_not_floor_minus_one():
    from drama_pipeline.stage1_turn_english import _p10_index

    # n=1: only one value -- its own index, never negative.
    assert _p10_index(1) == 0
    # n=9, n=10: the old floor(0.1n)-1 formula already agreed with
    # nearest-rank here (both 0); the fix must not regress them.
    assert _p10_index(9) == 0
    assert _p10_index(10) == 0
    # n=11: the bug's own evidence -- floor(0.1*11)-1 = 0, nearest-rank = 1.
    assert _p10_index(11) == 1
    # n=20: an exact decile boundary, unaffected either way.
    assert _p10_index(20) == 1


# --- A1: a declared transposition and the order a translation follows -------
#
# `citation.transpositions` says the edition prints lines `start..end` AFTER
# line `before`, so inside the numeric window `[start, before]` the Greek's
# printed order and its numeric order differ.  A translation follows one or
# the other and nothing in the bench text says which: Johnston's Hippolytus
# prints 106, 107, 104, 105 (Diggle's order), Way's prints 104, 105, 106, 107.
# The pairer therefore offers the DP both orderings of the speeches inside
# each declared window and keeps the cheaper one.  Only the ORDER the Greek
# speeches are offered in changes; the display stays as the edition prints it.


def _bridge(chunks: dict[str, str]) -> dict[str, dict]:
    """A `primary_bridge` map (the line-keyed primary column's own English)."""
    return {sid: {"id": sid, "text": text, "turns": []} for sid, text in chunks.items()}


def _transposed(tmp_path, source, spine, sigla, aliases, bridge, blocks, *, verse=False):
    path = tmp_path / "play.txt"
    path.write_text(f"TEST PLAY\n{source}\nFINIS\n", encoding="utf-8")
    return parse_translation(
        path,
        spine,
        work_id="test",
        translation_id="test",
        play="TEST PLAY",
        sigla=sigla,
        english_aliases=aliases,
        footnotes_enabled=False,
        primary_bridge=_bridge(bridge),
        transpositions=blocks,
        verse=verse,
    )


_T_SIGLA = {"Α.": "Alpha", "Β.": "Beta", "Γ.": "Gamma"}
_T_ALIASES = {"ALPHA": "Alpha", "BETA": "Beta", "GAMMA": "Gamma"}


def _spine_of(*segments: dict) -> dict:
    return {"work": "test", "segments": list(segments)}


def _numbered(sid, refs, label, start_n):
    return {
        "id": sid,
        "book": 1,
        "column": refs[0],
        "lines": [
            {"n": start_n + i, "ref": ref, "text": f"γραμμὴ {ref} ἐστίν."}
            for i, ref in enumerate(refs)
        ],
        "speakers": [{"line": start_n, "offset": 0, "label": label}],
    }


def test_a1_moved_block_pairs_with_its_own_speech_not_the_one_before(tmp_path):
    """Eumenides 64-84: the edition prints Apollo's speech after Orestes'.

    The English (Morshead, Kosmos, Johnston) prints it in numeric order, so a
    pairer walking both in sequence put Apollo's long speech inside the
    Priestess's segment and gave his six closing lines the whole of `1:64`.
    """
    spine = _spine_of(
        _numbered("1:1", ["1", "2", "3"], "Α.", 1),
        _numbered("1:5", ["5", "6"], "Β.", 4),
        _numbered("1:4", ["4", "7"], "Γ.", 6),
    )
    source = (
        "ALPHA. First in my prayer I honour Earth the ancient prophet mother.\n"
        "GAMMA. I will never abandon you; your guardian to the very end.\n"
        "BETA. You know what it is to do no wrong; learn also not to fail.\n"
        "GAMMA. Remember, and let no fear overcome your mind."
    )
    bridge = {
        "1:1": "First in this prayer I give honour to Earth the first prophet mother.",
        "1:5": "You know what it is to do no wrong; learn now not to fail.",
        "1:4": (
            "I will not abandon you; I am your guardian to the end. "
            "Remember, do not let fear conquer your mind."
        ),
    }
    english, _fn, _report = _transposed(
        tmp_path, source, spine, _T_SIGLA, _T_ALIASES, bridge,
        [{"start": "4", "end": "4", "before": "6"}],
    )
    chunks = {c["id"]: c["text"] for c in english["chunks"]}
    assert chunks["1:4"].startswith("I will never abandon you")
    assert "Remember, and let no fear" in chunks["1:4"]
    assert chunks["1:5"].startswith("You know what it is to do no wrong")
    assert chunks["1:1"].startswith("First in my prayer")
    assert "abandon" not in chunks["1:1"]


def test_a1_a_translation_in_numeric_order_pairs_line_for_line(tmp_path):
    """Hippolytus 104-105, printed after 107, against Way's numeric order."""
    spine = _spine_of(
        _numbered("1:1", ["1"], "Β.", 1),
        _numbered("1:4", ["4"], "Α.", 2),
        _numbered("1:5", ["5"], "Β.", 3),
        _numbered("1:2", ["2"], "Α.", 4),
        _numbered("1:3", ["3"], "Β.", 5),
    )
    source = (
        "BETA. Worshipful is she, glorious among men.\n"
        "ALPHA. Of gods, of men, each maketh still his choice.\n"
        "BETA. Now prosper thou; be needful wisdom thine.\n"
        "ALPHA. No god who hath night-homage pleaseth me.\n"
        "BETA. Guerdons of gods, my son, ought men to use."
    )
    bridge = {
        "1:1": "Yet is she an august goddess, far renowned on earth.",
        "1:2": "Among gods as well as men we have our several preferences.",
        "1:3": "I wish thee luck, and wisdom too, so far as thou dost need it.",
        "1:4": "No god, whose worship craves the night, hath charms for me.",
        "1:5": "My son, we should avail us of the gifts that gods confer.",
    }
    english, _fn, _report = _transposed(
        tmp_path, source, spine, _T_SIGLA, _T_ALIASES, bridge,
        [{"start": "2", "end": "3", "before": "5"}],
    )
    chunks = {c["id"]: c["text"] for c in english["chunks"]}
    assert chunks["1:4"].startswith("No god who hath night-homage")
    assert chunks["1:5"].startswith("Guerdons of gods")
    assert chunks["1:2"].startswith("Of gods, of men")
    assert chunks["1:3"].startswith("Now prosper thou")


def test_a1_a_translation_in_the_editions_order_is_left_alone(tmp_path):
    """The same Greek, and Johnston's text, which prints 106, 107, 104, 105.

    The fix must not disturb a column that already matches: the printed order
    is what this translation follows, so it stays.
    """
    spine = _spine_of(
        _numbered("1:1", ["1"], "Β.", 1),
        _numbered("1:4", ["4"], "Α.", 2),
        _numbered("1:5", ["5"], "Β.", 3),
        _numbered("1:2", ["2"], "Α.", 4),
        _numbered("1:3", ["3"], "Β.", 5),
    )
    source = (
        "BETA. But men revere her and celebrate her fame.\n"
        "ALPHA. I am not fond of gods worshipped at night.\n"
        "BETA. My son, one must pay tribute to the gods.\n"
        "ALPHA. But with both gods and men different people have different preferences.\n"
        "BETA. I wish you luck and all the prudent judgment you may need."
    )
    bridge = {
        "1:1": "Yet is she an august goddess, far renowned on earth.",
        "1:2": "Among gods as well as men we have our several preferences.",
        "1:3": "I wish thee luck, and wisdom too, so far as thou dost need it.",
        "1:4": "No god, whose worship craves the night, hath charms for me.",
        "1:5": "My son, we should avail us of the gifts that gods confer.",
    }
    english, _fn, _report = _transposed(
        tmp_path, source, spine, _T_SIGLA, _T_ALIASES, bridge,
        [{"start": "2", "end": "3", "before": "5"}],
    )
    chunks = {c["id"]: c["text"] for c in english["chunks"]}
    assert chunks["1:4"].startswith("I am not fond of gods")
    assert chunks["1:5"].startswith("My son, one must pay tribute")
    assert chunks["1:2"].startswith("But with both gods and men")
    assert chunks["1:3"].startswith("I wish you luck")


def test_a1_a_two_line_block_printed_early_keeps_its_own_english(tmp_path):
    """Medea 1273-1274, which Diggle prints before 1271-1272."""
    spine = _spine_of(
        _numbered("1:1", ["1", "2"], "Α.", 1),
        _numbered("1:5", ["5", "6"], "Β.", 3),
        _numbered("1:3", ["3", "4"], "Γ.", 5),
    )
    source = (
        "ALPHA. Woe for the deed I dare, and the ruin I bring on my house.\n"
        "GAMMA. What shall I do? Whither shall I flee my mother's hands?\n"
        "BETA. Dost thou hear the cry, the children's cry? Wretched woman!\n"
    )
    bridge = {
        "1:1": "Woe is me for the deed I dare and the ruin I bring upon my house.",
        "1:3": "Ah me, what shall I do? Whither shall I flee my mother's hands?",
        "1:5": "Dost thou hear the cry, dost thou hear the children? Wretched woman.",
    }
    english, _fn, _report = _transposed(
        tmp_path, source, spine, _T_SIGLA, _T_ALIASES, bridge,
        [{"start": "3", "end": "4", "before": "6"}],
    )
    chunks = {c["id"]: c["text"] for c in english["chunks"]}
    assert chunks["1:3"].startswith("What shall I do?")
    assert chunks["1:5"].startswith("Dost thou hear the cry")


# --- A2: the block a `coveredBy` note names -------------------------------


def test_a2_covered_by_names_the_block_that_holds_the_text_not_the_neighbour(tmp_path):
    """The DP's own rule names the match immediately BEFORE a skipped run.

    Eumenides 117-139: Morshead prints the Ghost's whole scene as one speech
    with the Furies' mutters as italic directions, so the English that covers
    Greek 121-122 sits two blocks back, and the note sent the reader to the
    neighbour instead.  Medea 1273-1274 is the same defect forwards: Way's
    rendering is in the LATER block.
    """
    spine = _spine_of(
        _numbered("1:1", ["1", "2"], "Α.", 1),
        _numbered("1:3", ["3"], "Β.", 3),
        _numbered("1:4", ["4"], "Α.", 4),
        _numbered("1:5", ["5"], "Β.", 5),
    )
    # One long Alpha speech carries both of Alpha's Greek turns; Beta's two
    # one-liners pair on their own.  1:4 is left empty and its English is in
    # 1:1 -- two blocks back, not in the neighbour 1:3.
    source = (
        "ALPHA. The ship was wrecked upon the reef at dawn.\n"
        "The sailors swam ashore and lit a beacon there.\n"
        "BETA. A grievous night.\n"
        "BETA. And a long morning after it."
    )
    bridge = {
        "1:1": "The ship was wrecked upon the reef at dawn.",
        "1:3": "A grievous night indeed.",
        "1:4": "The sailors swam ashore and lit a beacon there.",
        "1:5": "And a long morning after it.",
    }
    english, _fn, _report = _transposed(
        tmp_path, source, spine, _T_SIGLA, _T_ALIASES, bridge, [],
    )
    assert "1:4" not in {c["id"] for c in english["chunks"]}
    assert english["english_covered_by"].get("1:4") == "1:1"


def test_a2_covered_by_can_name_a_later_block(tmp_path):
    """Medea 1:1273: Way's rendering of 1273-74 sits two segments ON."""
    spine = _spine_of(
        _numbered("1:1", ["1"], "Α.", 1),
        _numbered("1:2", ["2"], "Β.", 2),
        _numbered("1:3", ["3"], "Α.", 3),
        _numbered("1:4", ["4"], "Β.", 4),
    )
    # Beta's two Greek turns are one undivided block in the translation, and
    # the DP hangs it on the LATER of them.
    source = (
        "ALPHA. A sound of weeping in the inner room.\n"
        "ALPHA. I know not, dearest brother; death is here.\n"
        "BETA. Dost thou hear the cry, the children's cry?\n"
        "Shall I go in and ward the murder off?"
    )
    bridge = {
        "1:1": "A sound of weeping in the inner room.",
        "1:2": "Dost thou hear the cry, dost thou hear the children?",
        "1:3": "I know not, sweet brother mine; we are undone.",
        "1:4": "Shall I enter the house? I am resolved to ward off the murder.",
    }
    english, _fn, _report = _transposed(
        tmp_path, source, spine, _T_SIGLA, _T_ALIASES, bridge, [],
    )
    assert "1:2" not in {c["id"] for c in english["chunks"]}
    assert english["english_covered_by"].get("1:2") == "1:4"


# --- A8: a lacuna row is not a pairing seat --------------------------------


def test_a8_a_lacuna_row_never_takes_a_turn(tmp_path):
    """Electra 650 / `post 651`: Diggle's empty `post N` placeholder carries a
    conjectured speaker in angle brackets, so it offered the pairer a named
    seat of zero length. Diggle gives 650 to Orestes and every translator
    gives it to the Old Man, so the placeholder's `<Pr.` won the speech on
    the name -- 1:650 went bare in all four columns and the run after it
    slid. A row with no Greek line is no seat: the speech belongs beside the
    Greek it translates, flagged where the editions disagree.
    """
    spine = _spine_of(
        _numbered("1:1", ["1"], "Α.", 1),
        _numbered("1:2", ["2"], "Α.", 2),
        {
            "id": "1:post 2", "book": 1, "column": "post 2",
            "lines": [{"n": 3, "ref": "post 2", "text": "", "role": "lacuna"}],
            "speakers": [{"line": 3, "offset": 0, "label": "<Γ."}],
        },
        _numbered("1:3", ["3"], "Β.", 4),
    )
    source = (
        "ALPHA. The first line of the scene.\n"
        "GAMMA. The second line answers it.\n"
        "BETA. And the third closes it."
    )
    english, _fn, report = _transposed(
        tmp_path, source, spine, _T_SIGLA, _T_ALIASES,
        {
            "1:1": "The first line of the scene.",
            "1:2": "The second line answers it.",
            "1:3": "And the third closes it.",
        },
        [],
    )
    chunks = {c["id"]: c["text"] for c in english["chunks"]}
    assert "1:post 2" not in chunks
    assert chunks["1:2"].startswith("The second line answers it")
    assert chunks["1:3"].startswith("And the third closes it")
    # The placeholder is not a Greek speech, so it is out of the pairing
    # rate's denominator too.
    assert report["greek_events"] == 3


def test_a8b_a_lacuna_row_takes_no_spread_piece(tmp_path):
    """A lacuna placeholder cannot claim a share of the speech above it."""
    spine = _spine_of(
        _numbered("1:1", ["1", "2"], "Α.", 1),
        {
            "id": "1:post 2", "book": 1, "column": "post 2",
            "lines": [{"n": 3, "ref": "post 2", "text": "", "role": "lacuna"}],
            "speakers": [
                {"line": 3, "offset": 0, "label": "<Γ."},
                {"line": 3, "offset": 0, "label": "<Β."},
            ],
        },
        _numbered("1:3", ["3"], "Β.", 4),
    )
    source = (
        "ALPHA. The first line of the scene.\n"
        "The second line completes the speech.\n"
        "BETA. And the third closes it."
    )
    english, _fn, _report = _transposed(
        tmp_path, source, spine, _T_SIGLA, _T_ALIASES,
        {
            "1:1": "The first line of the scene. The second line completes the speech.",
            "1:3": "And the third closes it.",
        },
        [],
        verse=True,
    )
    chunks = {c["id"]: c["text"] for c in english["chunks"]}
    assert "1:post 2" not in chunks
    assert chunks["1:1"] == "The first line of the scene.\nThe second line completes the speech."
    assert "1:post 2" not in english["english_covered_by"]


def test_r6b_a_one_line_claim_is_a_note_not_a_spread(tmp_path):
    """R6's one-line claim remains a reader note, not spread authority."""
    from drama_pipeline.stage1_turn_english import _content_covered, _spread_long_speeches

    spine = _spine_of(
        _numbered("1:1", ["1", "2"], "Α.", 1),
        _numbered("1:3", ["3"], "Β.", 3),
        _numbered("1:4", ["4"], "Γ.", 4),
    )
    chunks = [
        {"id": "1:1", "book": 1, "column": "1",
         "text": "The first printed line of the speech.\nThe last printed line of the speech.",
         "turns": [], "notes": [], "markers": [], "bekker": []},
        {"id": "1:4", "book": 1, "column": "4",
         "text": "The next speech begins here.",
         "turns": [], "notes": [], "markers": [], "bekker": []},
    ]
    tail_claims: set[str] = set()
    english_covered_by = _content_covered(
        spine["segments"], chunks,
        _bridge({
            "1:1": "The first printed line of the speech. The last printed line of the speech.",
            "1:3": "A bare Greek line has no English turn.",
            "1:4": "The next speech begins here.",
        }),
        {}, tail_claims=tail_claims,
    )
    assert english_covered_by.get("1:3") == "1:1"
    assert tail_claims == {"1:3"}
    out = _spread_long_speeches(
        chunks, spine["segments"], _T_SIGLA, verse=True,
        claimed={sid: cid for sid, cid in english_covered_by.items() if sid not in tail_claims},
    )
    by_id = {chunk["id"]: chunk["text"] for chunk in out}
    assert "1:3" not in by_id
    assert by_id["1:1"].endswith("The last printed line of the speech.")


# --- A4: a later turn's stage directions ----------------------------------


def test_a4_a_later_same_speaker_turn_keeps_its_directions(tmp_path):
    """A direction between two speeches of the SAME speaker inside one chunk
    rides the turn it precedes, not the chunk. (The corpus-wide loss the
    reviews report is a counting artefact -- a `_..._` sweep over
    `book-01.json` cannot see `directionsBefore`, which is emitted as plain
    strings; Agamemnon's benches keep 20/20, 21/21, 42/42 and 51/52 of their
    directions. This pins the behaviour so the merge cannot quietly drop
    one.)"""
    spine = _spine_of(
        _numbered("1:1", ["1", "2"], "Α.", 1),
        _numbered("1:3", ["3"], "Β.", 3),
    )
    source = (
        "ALPHA. The first thing I have to say.\n"
        "_ALPHA turns to the door._\n"
        "ALPHA. And the second, after a pause.\n"
        "BETA. My answer to both.\n"
    )
    english, _fn, _report = _transposed(
        tmp_path, source, spine, _T_SIGLA, _T_ALIASES,
        {"1:1": "The first thing I have to say. And the second, after a pause.",
         "1:3": "My answer to both."},
        [],
    )
    chunks = {c["id"]: c for c in english["chunks"]}
    # The direction before the SECOND speech of the same speaker rides that
    # turn, where the reader puts a row of its own between the two -- it is
    # not swallowed by the merge into one chunk.
    assert [t.get("directionsBefore") for t in chunks["1:1"]["turns"]] == [
        None, ["ALPHA turns to the door."],
    ]
    assert len(chunks["1:1"]["turns"]) == 2


# --- A6: a segment carrying two Greek sigla seats two turns ----------------


def test_a6_both_shares_of_a_line_take_their_own_english(tmp_path):
    """Bacchae 1372: the segment holds two Greek speeches, and Murray has a
    speech for each, yet the exodos ran a turn behind from 1374.

    Skipping the second share was priced as a MERGED antilabe
    (`ext_g_same_line`, 0.60) whether or not any English covered the line, so
    the column bought its own displacement: the slid seating cost 0.60 + 0.55
    against 1.60 + 0.60 for the two holes Murray really has at 1379-1380, and
    won by 0.023. Round 4's discriminator (`pair_dp.merged_into_match`) asks
    instead whether the English just matched is long enough for its OWN share
    alone -- and `test_pair_dp.test_pinned_predecessor_keeps_the_same_line_
    rate_for_the_regions_first_share`, which pins the same rate from the
    other side, still passes: there the merged speech IS long for its share.
    """
    spine = _spine_of(
        _numbered("1:0", ["0"], "Γ.", 0),
        {
            "id": "1:1", "book": 1, "column": "1",
            "lines": [{"n": 1, "ref": "1", "text": "στένομαί σε πάτερ· κἀγώ, τέκνον."}],
            "speakers": [
                {"line": 1, "offset": 0, "label": "Α."},
                {"line": 1, "offset": 18, "label": "Β."},
            ],
        },
        _numbered("1:2", ["2"], "Α.", 2),
        _numbered("1:3", ["3"], "Β.", 3),
        {
            "id": "1:4", "book": 1, "column": "4",
            "lines": [{"n": 4, "ref": "4", "text": "χαῖρε πάτερ μοι· χαῖρ' ὦ θύγατερ."}],
            "speakers": [
                {"line": 4, "offset": 0, "label": "Α."},
                {"line": 4, "offset": 17, "label": "Β."},
            ],
        },
        _numbered("1:5", ["5"], "Α.", 5),
    )
    source = (
        "GAMMA. Behold, the god stands here before the house.\n"
        "ALPHA. Father, for thee my tears are spent.\n"
        "BETA. Nay, child, it is I must weep for thee and for thy sisters twain.\n"
        "ALPHA. On all this house our lord has poured the utter dregs of pain.\n"
        "GAMMA. In bitter wise, for bitter was the shame ye did me.\n"
        "ALPHA. Then lead me where my sisters be, that we may go together."
    )
    bridge = {
        "1:0": "Behold, the god stands here before the house.",
        "1:1": "I grieve for you, father. And I for you, child, and I weep for your sisters.",
        "1:2": "Terribly indeed has lord Dionysus poured this suffering on your house.",
        "1:3": "Yes, for I suffered terrible things at your hands, in bitter shame.",
        "1:4": "Farewell, my father. Farewell, unhappy daughter.",
        "1:5": "Lead me, escorts, where my sisters are, that we may go together.",
    }
    english, _fn, _report = _transposed(
        tmp_path, source, spine, _T_SIGLA, _T_ALIASES, bridge, [],
    )
    chunks = {c["id"]: c for c in english["chunks"]}
    assert [t["speaker"] for t in chunks["1:1"]["turns"]] == ["Alpha", "Beta"]
    assert chunks["1:2"]["text"].startswith("On all this house")
    assert chunks["1:3"]["text"].startswith("In bitter wise")
    assert "1:4" not in chunks
    assert chunks["1:5"]["text"].startswith("Then lead me")


# --- Round 2 of Lane A: the five findings of the Sol review ----------------


def _antilabe(sid, ref, start_n, first, second):
    """A segment the edition cuts at ONE line-start event: two speakers share
    the printed line, so the segment offers two pairing slots on one ref."""
    text = "γραμμὴ {0} ἐστίν. καὶ πάλιν {0} ἐστίν.".format(ref)
    return {
        "id": sid,
        "book": 1,
        "column": ref,
        "lines": [{"n": start_n, "ref": ref, "text": text}],
        "speakers": [
            {"line": start_n, "offset": 0, "label": first},
            {"line": start_n, "offset": 16, "label": second},
        ],
    }


def test_a1_an_antilabe_inside_a_window_is_not_read_as_a_repeated_ref(tmp_path):
    """Finding 1: two speaker SHARES of one physical line are not a doublet.

    The guard that keeps a declared repeated ref (the Septem 803/810 doublet)
    in its printed seat was keyed on duplicate line keys, and an antilabe
    line makes two runs with the same key. So a window holding any antilabe
    was dropped whole and never offered in numeric order -- which is every
    one of Bacchae's three declared windows (967-970, 1168, 1372, 1379).
    """
    spine = _spine_of(
        _numbered("1:1", ["1"], "Β.", 1),
        _antilabe("1:4", "4", 2, "Α.", "Γ."),
        _numbered("1:5", ["5"], "Β.", 3),
        _numbered("1:2", ["2"], "Α.", 4),
        _numbered("1:3", ["3"], "Β.", 5),
    )
    source = (
        "BETA. Worshipful is she, glorious among men.\n"
        "ALPHA. Of gods, of men, each maketh still his choice.\n"
        "BETA. Now prosper thou; be needful wisdom thine.\n"
        "ALPHA. No god who hath night-homage pleaseth me.\n"
        "GAMMA. Yet darkness hides the shrine where I would kneel.\n"
        "BETA. Guerdons of gods, my son, ought men to use."
    )
    bridge = {
        "1:1": "Yet is she an august goddess, far renowned on earth.",
        "1:2": "Among gods as well as men we have our several preferences.",
        "1:3": "I wish thee luck, and wisdom too, so far as thou dost need it.",
        "1:4": (
            "No god, whose worship craves the night, hath charms for me. "
            "Yet darkness covers the shrine where I would kneel down."
        ),
        "1:5": "My son, we should avail us of the gifts that gods confer.",
    }
    english, _fn, _report = _transposed(
        tmp_path, source, spine, _T_SIGLA, _T_ALIASES, bridge,
        [{"start": "2", "end": "3", "before": "5"}],
    )
    chunks = {c["id"]: c["text"] for c in english["chunks"]}
    assert chunks["1:2"].startswith("Of gods, of men")
    assert chunks["1:3"].startswith("Now prosper thou")
    assert chunks["1:4"].startswith("No god who hath night-homage")
    assert "Yet darkness hides the shrine" in chunks["1:4"]
    assert chunks["1:5"].startswith("Guerdons of gods")


def test_a1_a_residual_english_inside_a_window_reaches_its_own_speech(tmp_path):
    """Finding 2: the residual walk runs in the order the DP chose.

    The residual pass holds `cursor = max(cursor, gi)` and searches forward,
    so it needs monotone Greek indices. Undoing the chosen order before it
    runs left a residual inside a crossed window unable to reach the lower
    PRINTED slot: here the translator divides Greek 4 into two turns, and the
    second parked on Greek 3 (printed after it) with a speaker mismatch.
    """
    spine = _spine_of(
        _numbered("1:1", ["1"], "Β.", 1),
        _numbered("1:4", ["4"], "Α.", 2),
        _numbered("1:5", ["5"], "Β.", 3),
        _numbered("1:2", ["2"], "Α.", 4),
        _numbered("1:3", ["3"], "Β.", 5),
    )
    source = (
        "BETA. Worshipful is she, glorious among men.\n"
        "ALPHA. Of gods, of men, each maketh still his choice.\n"
        "BETA. Now prosper thou; be needful wisdom thine.\n"
        "ALPHA. No god who hath night-homage pleaseth me.\n"
        "ALPHA. Their rites are wrought in darkness, and I hate them.\n"
        "BETA. Guerdons of gods, my son, ought men to use."
    )
    bridge = {
        "1:1": "Yet is she an august goddess, far renowned on earth.",
        "1:2": "Among gods as well as men we have our several preferences.",
        "1:3": "I wish thee luck, and wisdom too, so far as thou dost need it.",
        "1:4": "No god, whose worship craves the night, hath charms for me.",
        "1:5": "My son, we should avail us of the gifts that gods confer.",
    }
    english, _fn, _report = _transposed(
        tmp_path, source, spine, _T_SIGLA, _T_ALIASES, bridge,
        [{"start": "2", "end": "3", "before": "5"}],
    )
    chunks = {c["id"]: c for c in english["chunks"]}
    assert chunks["1:4"]["text"].startswith("No god who hath night-homage")
    assert "Their rites are wrought in darkness" in chunks["1:4"]["text"]
    assert "Their rites" not in chunks["1:3"]["text"]
    assert chunks["1:3"]["text"].startswith("Now prosper thou")
    assert not any(t.get("speakerMismatch") for t in chunks["1:4"]["turns"])


def test_a1_two_pins_inside_a_window_are_kept_for_the_order_choice(tmp_path):
    """Finding 3: a pin is checked against each candidate order, not printed.

    Two pins a reviewer states for a numeric-order translation cross in the
    PRINTED order of a transposition, and the later one was dropped as
    contradictory before the pairer ever saw it.
    """
    from drama_pipeline import stage1_turn_english as m

    blocks = [{"start": "2", "end": "3", "before": "5"}]
    segments = [
        {"greek": [{"n": 1, "ref": "1"}]},
        {"greek": [{"n": 2, "ref": "4"}]},
        {"greek": [{"n": 3, "ref": "5"}]},
        {"greek": [{"n": 4, "ref": "2"}]},
        {"greek": [{"n": 5, "ref": "3"}]},
    ]
    slots = [
        {"segment": 0, "line": 1, "offset": 0, "name": "Beta"},
        {"segment": 1, "line": 2, "offset": 0, "name": "Alpha"},
        {"segment": 2, "line": 3, "offset": 0, "name": "Beta"},
        {"segment": 3, "line": 4, "offset": 0, "name": "Alpha"},
        {"segment": 4, "line": 5, "offset": 0, "name": "Beta"},
    ]
    speeches = [
        {"text": "Worshipful is she, glorious among men.", "canonical": "Beta"},
        {"text": "Of gods, of men, each maketh still his choice.", "canonical": "Alpha"},
        {"text": "Now prosper thou; be needful wisdom thine.", "canonical": "Beta"},
        {"text": "No god who hath night-homage pleaseth me.", "canonical": "Alpha"},
        {"text": "Guerdons of gods, my son, ought men to use.", "canonical": "Beta"},
    ]
    refs = m._slot_refs(segments, slots)
    pins = [
        {"greek": "2", "english": "Of gods, of men"},
        {"greek": "4", "english": "No god who hath night-homage"},
    ]
    notes: list[str] = []
    forced = m._resolve_pins(
        pins, slots, refs, speeches, "t", notes, transpositions=blocks
    )
    assert forced == [(3, 1), (1, 3)]
    assert not [n for n in notes if "crosses" in n]
    # Outside a declared window the contradiction stands and the later pin is
    # still dropped.
    dropped: list[str] = []
    assert m._resolve_pins(pins, slots, refs, speeches, "t", dropped) == [(3, 1)]
    assert [n for n in dropped if "crosses" in n]

    # And the pairer seats both of them.
    spine = _spine_of(
        _numbered("1:1", ["1"], "Β.", 1),
        _numbered("1:4", ["4"], "Α.", 2),
        _numbered("1:5", ["5"], "Β.", 3),
        _numbered("1:2", ["2"], "Α.", 4),
        _numbered("1:3", ["3"], "Β.", 5),
    )
    path = tmp_path / "play.txt"
    path.write_text(
        "TEST PLAY\n"
        "BETA. Worshipful is she, glorious among men.\n"
        "ALPHA. Of gods, of men, each maketh still his choice.\n"
        "BETA. Now prosper thou; be needful wisdom thine.\n"
        "ALPHA. No god who hath night-homage pleaseth me.\n"
        "BETA. Guerdons of gods, my son, ought men to use.\n"
        "FINIS\n",
        encoding="utf-8",
    )
    english, _fn, _report = parse_translation(
        path, spine, work_id="test", translation_id="test", play="TEST PLAY",
        sigla=_T_SIGLA, english_aliases=_T_ALIASES, footnotes_enabled=False,
        pins=pins, transpositions=blocks,
    )
    chunks = {c["id"]: c["text"] for c in english["chunks"]}
    assert chunks["1:2"].startswith("Of gods, of men")
    assert chunks["1:4"].startswith("No god who hath night-homage")


def test_a2_a_short_reply_does_not_claim_a_donor():
    """Finding 4: a primary reference of two words asserts nothing.

    "Yes." scores 1.0 against any incidental "Yes." nearby, clearing both the
    floor and the lead, so A2 could name a false donor for the one-line
    replies that fill a stichomythia. Below the token minimum the DP's own
    reading stands.
    """
    from drama_pipeline import stage1_turn_english as m

    segments = [
        {"id": "1:1", "speakers": [{"label": "Α."}]},
        {"id": "1:2", "speakers": [{"label": "Β."}]},
        {"id": "1:3", "speakers": [{"label": "Α."}]},
    ]
    chunks = [
        {"id": "1:1", "text": "The ship was wrecked upon the reef at dawn."},
        {"id": "1:3", "text": "Yes. And the sailors swam ashore and lit a beacon."},
    ]
    primary = {
        "1:1": {"text": "The ship was wrecked upon the reef at dawn."},
        "1:2": {"text": "Yes."},
        "1:3": {"text": "Yes, and the sailors swam ashore and lit a beacon there."},
    }
    out = m._content_covered(segments, chunks, primary, {"1:2": "1:1"})
    assert out["1:2"] == "1:1"

    # The same segment with words of its own still names its donor.
    primary["1:2"] = {"text": "The sailors swam ashore and lit a beacon there."}
    moved = m._content_covered(segments, chunks, primary, {"1:2": "1:1"})
    assert moved["1:2"] == "1:3"


def test_a1_a_near_tie_keeps_the_printed_order():
    """Finding 5: "strictly cheaper" needs a tolerance.

    The two candidate orders sum the same terms in a different sequence, so
    mathematically equal totals can differ in the last bits and hand the
    window to numeric order on rounding noise alone.
    """
    from drama_pipeline import stage1_turn_english as m

    assert not m._strictly_cheaper(1000.0, 1000.0)
    assert not m._strictly_cheaper(1000.0 - 1e-10, 1000.0)
    assert not m._strictly_cheaper(1000.0 + 1e-10, 1000.0)
    assert m._strictly_cheaper(999.99, 1000.0)
    assert m._strictly_cheaper(-1e-6, 0.0)


def test_a1_a_reordered_window_is_no_turn_shift(tmp_path):
    """The drift diagnostic counts in the order the translation follows.

    Same-name ordinal drift compares each side's position among its own
    speeches. Inside a declared transposition the printed order and the
    translation's differ BY DECLARATION, so a column paired right through the
    window read as fresh drift -- four of them at Septem 983/993, enough to
    fail `turn_text_turn_shift` on the edition's own printed order.
    """
    spine = _spine_of(
        _numbered("1:1", ["1"], "Β.", 1),
        _numbered("1:4", ["4"], "Α.", 2),
        _numbered("1:5", ["5"], "Β.", 3),
        _numbered("1:2", ["2"], "Α.", 4),
        _numbered("1:3", ["3"], "Β.", 5),
    )
    source = (
        "BETA. Worshipful is she, glorious among men.\n"
        "ALPHA. Of gods, of men, each maketh still his choice.\n"
        "BETA. Now prosper thou; be needful wisdom thine.\n"
        "ALPHA. No god who hath night-homage pleaseth me.\n"
        "BETA. Guerdons of gods, my son, ought men to use."
    )
    bridge = {
        "1:1": "Yet is she an august goddess, far renowned on earth.",
        "1:2": "Among gods as well as men we have our several preferences.",
        "1:3": "I wish thee luck, and wisdom too, so far as thou dost need it.",
        "1:4": "No god, whose worship craves the night, hath charms for me.",
        "1:5": "My son, we should avail us of the gifts that gods confer.",
    }
    _english, _fn, report = _transposed(
        tmp_path, source, spine, _T_SIGLA, _T_ALIASES, bridge,
        [{"start": "2", "end": "3", "before": "5"}],
    )
    assert report["turn_shift_new_drifts"] == 0
    assert report["turn_shift_count"] == 0


# --- Round 3 of Lane A -----------------------------------------------------


def _paired(
    tmp_path, source, spine, sigla, aliases, *,
    bridge=None, blocks=None, repeated=None, pins=None, covered=None, verse=False,
    english_transpositions=None,
):
    """`parse_translation` over a synthetic play, bridge optional.

    Without `bridge` the column has no line-keyed primary to compare against
    -- the eleven comedies' shape, and the one that isolates the name,
    length and position terms.
    """
    path = tmp_path / "play.txt"
    path.write_text(f"TEST PLAY\n{source}\nFINIS\n", encoding="utf-8")
    return parse_translation(
        path,
        spine,
        work_id="test",
        translation_id="test",
        play="TEST PLAY",
        sigla=sigla,
        english_aliases=aliases,
        footnotes_enabled=False,
        primary_bridge=_bridge(bridge) if bridge else None,
        transpositions=blocks or [],
        repeated_refs=repeated or [],
        english_transpositions=english_transpositions or [],
        pins=pins or [],
        covered=covered or [],
        verse=verse,
    )


def test_r1_a_repeated_ref_does_not_seat_a_turn_of_its_own(tmp_path):
    """Septem 803/810: the edition prints the ref twice, the translator once.

    `citation.repeated_refs` declares the doublet, and the Greek keeps both
    printed seats (the hard rule).  The pairer used to offer the second seat
    to the English as well, and inside a choral run -- where every seat and
    every turn say the same name, so nothing but position discriminates --
    the column slid onto it: Morshead's third stasimon printed beside Greek
    810 and every speech after it one to five turns early, resyncing only at
    875, with the seat it really wanted left bare and unexplained.
    """
    spine = _spine_of(
        _numbered("1:1", ["1"], "\u0391.", 1),
        _numbered("1:2", ["2"], "\u0392.", 2),
        _numbered("1:2.2", ["2"], "\u0392.", 3),
        _numbered("1:3", ["3"], "\u0392.", 4),
        _numbered("1:4", ["4"], "\u0392.", 5),
        _numbered("1:5", ["5"], "\u0392.", 6),
    )
    source = (
        "ALPHA. What further woefulness besets our home?\n"
        "BETA. O mighty Zeus and guardian powers of Cadmus.\n"
        "BETA. A twofold sorrow and a twofold strife is come.\n"
        "BETA. Alas my sisters, be your sighs the gale that drives.\n"
        "BETA. Look up, look yonder, from the home they come.\n"
    )
    english, _fn, _report = _paired(
        tmp_path, source, spine, _T_SIGLA, _T_ALIASES, repeated=["2"],
    )
    chunks = {c["id"]: c["text"] for c in english["chunks"]}
    # The repeat holds no turn, and says where its line's English is.
    assert "1:2.2" not in chunks
    assert english["english_covered_by"].get("1:2.2") == "1:2"
    # ...so the three speeches that used to ride one seat early sit on their
    # own Greek and no real seat is left bare.
    assert chunks["1:3"].startswith("A twofold sorrow")
    assert chunks["1:4"].startswith("Alas my sisters")
    assert chunks["1:5"].startswith("Look up, look yonder")


def _anon(sid, ref, start_n, shares=1):
    """A segment the edition opens with `—`: a change of speaker it does not
    name (Rhesus' guard antilabe, Suppliants' exodos)."""
    text = "γραμμὴ {0} ἐστίν. καὶ πάλιν {0} ἐστίν.".format(ref)
    return {
        "id": sid,
        "book": 1,
        "column": ref,
        "lines": [{"n": start_n, "ref": ref, "text": text}],
        "speakers": [
            {"line": start_n, "offset": 16 * i, "label": "—"} for i in range(shares)
        ],
    }


def test_r11_a_dash_siglum_share_is_a_speech_of_its_own(tmp_path):
    """Rhesus 722-727, Suppliants 1038-1051: the `—` share is a speech.

    An anonymous speaker event used to be absorbed into the speech before it,
    so a whole antilabe run took ONE English turn between them: Way's first
    reply welded onto the end of the 1:710 stasimon block and the rest slid a
    turn each down to the single word "through." at 1:727; Suppliants' exodos
    left 14 Greek lines blank in both columns.
    """
    spine = _spine_of(
        _numbered("1:1", ["1", "2", "3"], "Α.", 1),
        _anon("1:4", "4", 4),
        _anon("1:5", "5", 5),
        _anon("1:6", "6", 6),
        _numbered("1:7", ["7"], "Γ.", 7),
    )
    source = (
        "ALPHA. Once before he came into this city, with swimming bleary eyes, "
        "clad in rags and tatters, his sword hidden in his cloak.\n"
        "GAMMA. Whether it was Odysseus or not, I am afraid for the sentinels.\n"
        "GAMMA. What can he allege against us? He will suspect.\n"
        "GAMMA. What have we done? Why are you afraid of him?\n"
        "GAMMA. Cruel stroke of fate! Woe, woe!\n"
    )
    english, _fn, _report = _paired(tmp_path, source, spine, _T_SIGLA, _T_ALIASES)
    chunks = {c["id"]: c["text"] for c in english["chunks"]}
    assert chunks["1:4"].startswith("Whether it was Odysseus")
    assert chunks["1:5"].startswith("What can he allege")
    assert chunks["1:6"].startswith("What have we done")
    assert "Odysseus" not in chunks["1:1"]
    assert chunks["1:7"].startswith("Cruel stroke of fate")


def test_r11_a_slot_with_no_speaker_event_is_still_a_continuation(tmp_path):
    """The other half of the R11 distinction, kept.

    A segment with no speaker event of its own -- a lyric the segmenter cut
    at a column break, Persians' strophe divisions -- is NOT a speech: it
    belongs to the speaker above it and takes its share of that speech from
    the spread, never a turn of its own. Only an event that names nobody is
    the edition saying "someone else now speaks".
    """
    continuation = {
        "id": "1:4", "book": 1, "column": "4",
        "lines": [{"n": 4, "ref": "4", "text": "γραμμὴ 4 ἐστίν."}],
    }
    spine = _spine_of(
        _numbered("1:1", ["1", "2", "3"], "Α.", 1),
        continuation,
        _numbered("1:5", ["5"], "Β.", 5),
    )
    source = (
        "ALPHA. The first stanza of the parodos, sung as they enter.\n"
        "ALPHA. A second stanza the Greek does not divide from it.\n"
        "BETA. The answer of the other speaker, plainly his own.\n"
    )
    english, _fn, _report = _paired(tmp_path, source, spine, _T_SIGLA, _T_ALIASES)
    chunks = {c["id"]: c["text"] for c in english["chunks"]}
    # The surplus Gamma speech parks with the speech it continues, not on a
    # turn of its own -- and "1:4" holds no cue of its own.
    assert "A second stanza the Greek does not divide" in chunks["1:1"]
    assert chunks["1:5"].startswith("The answer of the other speaker")


def test_r12_an_unplaceable_residual_is_not_welded_to_the_speech_before_it(tmp_path):
    """IT 118-202: Way's Chorus strophe welded onto Orestes' prologue-end.

    Way gives Greek 123-142 to the CHORUS where Diggle gives it to Iphigenia,
    and Way's own next speech is Iphigenia's, so the edition's name took 1:123
    and the strophe had no slot left in its window at all. It parked on the
    CURSOR -- the slot the English before it went to -- and so printed inside
    Orestes' prologue-end, against Greek it does not translate, and the whole
    parodos read a speech ahead for 85 lines. Its own place in document order
    says the other thing: it comes before the next paired English, so it
    belongs on the Greek just before that anchor, not on the Greek behind it.
    """
    spine = _spine_of(
        _numbered("1:1", ["1"], "\u0391.", 1),
        _numbered("1:2", ["2"], "\u0392.", 2),
        _numbered("1:3", ["3"], "\u0393.", 3),
    )
    source = (
        "ALPHA. Good: I must heed thee; best withdraw ourselves unseen.\n"
        "GAMMA. Keep reverent silence, ye beside the Euxine Sea who dwell.\n"
        "BETA. Ah maidens, sunken deep in mourning's dole I weep alway.\n"
        "GAMMA. Lo, yonder from the sea-shore one hath come to thee.\n"
    )
    english, _fn, _report = _paired(tmp_path, source, spine, _T_SIGLA, _T_ALIASES)
    chunks = {c["id"]: c for c in english["chunks"]}
    assert chunks["1:1"]["text"].startswith("Good: I must heed thee")
    assert "reverent silence" not in chunks["1:1"]["text"]
    # The strophe sits on the Greek it translates, flagged with the speaker
    # the edition gives those lines to, and Beta's own speech keeps its place.
    assert chunks["1:2"]["text"].startswith("Keep reverent silence")
    assert [t["speaker"] for t in chunks["1:2"]["turns"]] == ["Gamma", "Beta"]
    assert chunks["1:2"]["turns"][0]["speakerMismatch"] == {
        "english": "Gamma", "greek": "Beta",
    }
    assert chunks["1:3"]["text"].startswith("Lo, yonder from the sea-shore")


def test_r3_a_two_speaker_segments_second_turn_keeps_its_direction(tmp_path):
    """R3 (philoctetes finding 3), the verification the brief asks for.

    The ambush direction before Odysseus' entry at 974 falls after the FIRST
    cue of a two-speaker Greek segment, which is where the review found
    `directionsBefore` on 27 first parts and 0 later ones. It does not
    reproduce: a later speech's direction rides its own TURN
    (`turns[k].directionsBefore`, and `turnDirections` on the overlay piece
    `chunks_as_overlay` writes), which is the other of the emit's two
    channels, not a loss -- the reader puts it in a row of its own between
    the two speeches (`speakers.splitAtDirections`). This pins that.
    """
    segment = {
        "id": "1:1", "book": 1, "column": "1",
        "lines": [{"n": 1, "ref": "1", "text": "γραμμὴ 1. καὶ πάλιν 1."}],
        "speakers": [
            {"line": 1, "offset": 0, "label": "Α."},
            {"line": 1, "offset": 11, "label": "Β."},
        ],
    }
    spine = _spine_of(segment, _numbered("1:2", ["2"], "Γ.", 2))
    source = (
        "ALPHA. What shall we do, friends?\n"
        "_[ODYSSEUS appears suddenly from behind the cave.]_\n"
        "BETA. Wretch, what art thou at? Come back and give the bow.\n"
        "GAMMA. And I stand by, a witness of it all.\n"
    )
    english, _fn, _report = _paired(tmp_path, source, spine, _T_SIGLA, _T_ALIASES)
    chunks = {c["id"]: c for c in english["chunks"]}
    turns = chunks["1:1"]["turns"]
    assert [t["speaker"] for t in turns] == ["Alpha", "Beta"]
    # Not on the chunk (that row is for a direction before its FIRST speech):
    # on the turn it precedes, which is the second one.
    assert "directionsBefore" not in chunks["1:1"]
    assert turns[0].get("directionsBefore") is None
    assert turns[1]["directionsBefore"] == [
        "[ODYSSEUS appears suddenly from behind the cave.]"
    ]
    # ...and it survives into the overlay shape the comparison columns ship.
    from drama_pipeline.stage1_turn_english import chunks_as_overlay

    overlay = chunks_as_overlay(english)["1:1"][0]
    assert overlay["turnDirections"] == [
        {"turn": 1, "directions": ["[ODYSSEUS appears suddenly from behind the cave.]"]}
    ]


# --- R13 / R6: what a coverage claim has to be able to hold ----------------


def _seg(sid, nlines, start_n=1, ref=None):
    ref = ref or sid.split(":", 1)[1]
    return {
        "id": sid, "book": 1, "column": ref,
        "lines": [
            {"n": start_n + i, "ref": str(int(ref) + i), "text": "x" * 40}
            for i in range(nlines)
        ],
        "speakers": [{"line": start_n, "offset": 0, "label": "Α."}],
    }


def test_r13_a_donor_too_short_for_the_lines_it_claims_makes_no_claim():
    """Wealth 1:522-1:563 (finding 2): `coveredBy 1:519` on 42 Greek lines
    from a 246-character block -- five characters a line, where every other
    covering block in that play runs 44 to 76. The reader was told the
    translation is above when it is thirty segments above. A claim has to be
    able to HOLD the lines it claims."""
    from drama_pipeline.stage1_turn_english import _plausible_covers

    segments = [_seg("1:1", 2, 1), _seg("1:2", 20, 3), _seg("1:3", 22, 23)]
    chunks = [{"id": "1:1", "text": "x" * 246}]
    claimed = {"1:2": "1:1", "1:3": "1:1"}
    assert _plausible_covers(claimed, chunks, segments) == {}
    # A lone claim on the row next to it is exempt: the floor is about a
    # JOINT claim, and one neighbour is the DP's own reading of a skip right
    # after a match (R6's Heracles 1066 is 39 characters and is plainly it).
    assert _plausible_covers({"1:2": "1:1"}, chunks, segments) == {"1:2": "1:1"}
    # ...but a lone claim two rows off still has to be able to hold them.
    assert _plausible_covers({"1:3": "1:1"}, chunks, segments) == {}
    # The same donor, long enough for the same 42 lines, keeps both claims.
    fat = [{"id": "1:1", "text": "x" * 4000}]
    assert _plausible_covers(claimed, fat, segments) == claimed


def test_r6_a_bare_cry_is_covered_by_the_row_above():
    """Heracles 1:1066 (finding 13): Kosmos renders Greek 1065-1066 in one
    turn on the row above, and the bare row said nothing at all -- "no
    aligned passage", which is false. The DP's own rule wants the English to
    be twice as long as its Greek before it says "translated with the speech
    above", and a terse prose column never is; the cry's own primary text is
    two words, so the cosine cannot speak for it either."""
    from drama_pipeline.stage1_turn_english import _content_covered

    segments = [_seg("1:1064", 1, 1), _seg("1:1065", 1, 2), _seg("1:1066", 1, 3),
                _seg("1:1067", 4, 4)]
    chunks = [
        {"id": "1:1064", "text": "Now wail. I wail the ruin of his sons."},
        # 39 characters for two lyric cries: under every length test that
        # would let it through, which is why R6 applies none.
        {"id": "1:1065", "text": "And I, ah me! Lament your son, old man."},
        {"id": "1:1067", "text": "Silence, I pray you, silence -- see, he stirs."},
    ]
    primary = _bridge({
        "1:1064": "Groan now. I groan.",
        "1:1065": "for the ruin of your children.",
        # Three word tokens of three letters or more: under the minimum the
        # cosine needs before it may override the DP, so no claim is earned.
        "1:1066": "The children’s death— Ah me!",
        "1:1067": "Old man, be quiet, be quiet. He turns over as he wakes.",
    })
    out = _content_covered(segments, chunks, primary, {})
    assert out == {"1:1066": "1:1065"}


def test_r6_a_two_line_hole_still_says_nothing():
    """The other side of R6's line: a hole of more than one Greek line, or one
    whose own row above is bare too, is not "absorbed into the turn above" and
    stays on A3's warning list rather than getting a claim it cannot support."""
    from drama_pipeline.stage1_turn_english import _content_covered

    segments = [_seg("1:1", 1, 1), _seg("1:2", 2, 2), _seg("1:4", 1, 4)]
    chunks = [
        {"id": "1:1", "text": "The first speech, short and plain."},
        {"id": "1:4", "text": "The last speech, equally plain."},
    ]
    primary = _bridge({
        "1:1": "One thing.", "1:2": "Two more. Words.", "1:4": "A last thing.",
    })
    assert _content_covered(segments, chunks, primary, {}) == {}


def test_r6_a_run_head_inherits_the_claim_its_tail_earned():
    """Eumenides 1:117-1:120: the same absorbed mutter scene as 1:121-1:127,
    which named 1:94, but the forward-only inheritance left the head of the
    run bare and unexplained."""
    from drama_pipeline.stage1_turn_english import _content_covered

    segments = [_seg("1:1", 4, 1), _seg("1:2", 1, 5), _seg("1:3", 1, 6),
                _seg("1:4", 1, 7), _seg("1:9", 2, 8)]
    chunks = [
        {"id": "1:1", "text": (
            "Sleep on, awake! What skills your sleep to me? "
            "Seize him, seize him, mark him, hound him closely now! "
            "In dreams ye chase a prey, and like some hound ye bell and bay."
        )},
        {"id": "1:9", "text": "Out, I command you, out from this my home!"},
    ]
    primary = _bridge({
        "1:1": "Sleep on! Awake! What good is your sleeping to me?",
        # No words the cosine may speak for.
        "1:2": "(moan)",
        "1:3": "Seize him, seize him, mark him, hound him closely now.",
        "1:4": "(moan)",
        "1:9": "Out, I command you! Away from this house at once!",
    })
    out = _content_covered(segments, chunks, primary, {})
    assert out == {"1:2": "1:1", "1:3": "1:1", "1:4": "1:1"}


def test_r10_a_share_with_no_english_inside_a_full_segment_is_reported(tmp_path):
    """Acharnians 919 (finding 5): `Νεώριον θρυαλλίς; Οἶμαι. Τίνι
    τρόπω;` is three Greek shares and the 1912 renders one turn, so
    Nicarchus' `Οἶμαι` has no English anywhere -- and neither
    `greek_skip_runs` nor `strict_coverage` can see it, because both test the
    SEGMENT and this segment has English."""
    packed = {
        "id": "1:1", "book": 1, "column": "1",
        "lines": [{"n": 1, "ref": "1", "text": "γρ. 1. καὶ 1. καὶ 1."}],
        "speakers": [
            {"line": 1, "offset": 0, "label": "Α."},
            {"line": 1, "offset": 8, "label": "Β."},
            {"line": 1, "offset": 15, "label": "Α."},
        ],
    }
    spine = _spine_of(packed, _numbered("1:2", ["2"], "Γ.", 2))
    source = (
        "ALPHA. A wick set an arsenal ablaze! But how, great gods?\n"
        "GAMMA. And I stand by, a witness of it all.\n"
    )
    _english, _fn, report = _paired(tmp_path, source, spine, _T_SIGLA, _T_ALIASES)
    assert report["bare_events"] == 0
    assert report["unenglished_events"] == [
        {"ref": "1", "segment": "1:1", "speaker": "Beta"},
        {"ref": "1", "segment": "1:1", "speaker": "Alpha"},
    ]


def test_r9_a_translation_that_prints_two_pairs_in_the_other_order(tmp_path):
    """Acharnians 1107-1112 (finding 1): an ENGLISH transposition.

    The 1912 prints the arming duet's two couplet-pairs in the opposite order
    to Coulon -- its lophos pair first, "stop mocking my armour" after -- so
    the English of 1109-1112 belongs on 1107-1110 and the English of
    1107-1108 on 1111-1112. Two pairs that cross: a monotone DP cannot
    produce them and crossing pins cannot ask for them
    (`pair_dp.align` raises "pins must run forward in both texts"), so the six
    lines shipped wrong with nothing able to state otherwise.
    """
    spine = _spine_of(
        _numbered("1:1", ["1"], "Α.", 1),
        _numbered("1:2", ["2"], "Β.", 2),
        _numbered("1:3", ["3"], "Α.", 3),
        _numbered("1:4", ["4"], "Β.", 4),
        _numbered("1:5", ["5"], "Α.", 5),
    )
    source = (
        # The column's own order: 3, 4, then 1, 2.
        "ALPHA. Bring me the case for my triple plume.\n"
        "BETA. And bring me my dish of hare's meat.\n"
        "ALPHA. Hi, friend, try not to scoff at my armour.\n"
        "BETA. Hi, fellow, try not to eye my lunch.\n"
        "ALPHA. And now let both of us be going.\n"
    )
    declared = [{"start": "3", "end": "4", "before": "1"}]
    english, _fn, _report = _paired(
        tmp_path, source, spine, _T_SIGLA, _T_ALIASES,
        english_transpositions=declared,
    )
    chunks = {c["id"]: c["text"] for c in english["chunks"]}
    assert chunks["1:1"].startswith("Hi, friend, try not to scoff")
    assert chunks["1:2"].startswith("Hi, fellow, try not to eye")
    assert chunks["1:3"].startswith("Bring me the case")
    assert chunks["1:4"].startswith("And bring me my dish")
    assert chunks["1:5"].startswith("And now let both of us")


def test_r9_no_declaration_leaves_the_column_alone(tmp_path):
    """The same play with nothing declared keeps the edition's order, which is
    what every other column in the corpus needs."""
    spine = _spine_of(
        _numbered("1:1", ["1"], "Α.", 1),
        _numbered("1:2", ["2"], "Β.", 2),
        _numbered("1:3", ["3"], "Α.", 3),
    )
    source = (
        "ALPHA. Hi, friend, try not to scoff at my armour.\n"
        "BETA. Hi, fellow, try not to eye my lunch.\n"
        "ALPHA. And now let both of us be going.\n"
    )
    english, _fn, _report = _paired(tmp_path, source, spine, _T_SIGLA, _T_ALIASES)
    chunks = {c["id"]: c["text"] for c in english["chunks"]}
    assert chunks["1:1"].startswith("Hi, friend")
    assert chunks["1:3"].startswith("And now let both")


def test_r9a_a_crossing_pin_inside_a_declared_english_window_is_kept():
    """Grok's read of round 3, finding 1.

    The exemption read a block as the Greek window ``(start, before)``. A
    CITATION block prints ``start..end`` after ``before``, so ``before`` is
    the high end and the pair read right; an ENGLISH block prints the English
    of ``start..end`` BEFORE that of ``before``, so ``before`` is the LOW end
    and ``(start, before)`` is an empty interval -- the exemption never fired
    for the column it was extended for, and a pin pair crossing inside the
    declared window lost its later half.
    """
    from drama_pipeline import stage1_turn_english as m

    # The Acharnians shape: the Greek is printed in numeric order and this
    # COLUMN prints the English of 3-4 before that of 1-2.
    blocks = [{"start": "3", "end": "4", "before": "1"}]
    segments = [
        {"greek": [{"n": 1, "ref": "1"}]},
        {"greek": [{"n": 2, "ref": "2"}]},
        {"greek": [{"n": 3, "ref": "3"}]},
        {"greek": [{"n": 4, "ref": "4"}]},
    ]
    slots = [
        {"segment": 0, "line": 1, "offset": 0, "name": "Alpha"},
        {"segment": 1, "line": 2, "offset": 0, "name": "Beta"},
        {"segment": 2, "line": 3, "offset": 0, "name": "Alpha"},
        {"segment": 3, "line": 4, "offset": 0, "name": "Beta"},
    ]
    speeches = [
        {"text": "Bring me the case for my triple plume.", "canonical": "Alpha"},
        {"text": "And bring me my dish of hare's meat.", "canonical": "Beta"},
        {"text": "Hi, friend, try not to scoff at my armour.", "canonical": "Alpha"},
        {"text": "Hi, fellow, try not to eye my lunch.", "canonical": "Beta"},
    ]
    refs = m._slot_refs(segments, slots)
    pins = [
        {"greek": "3", "english": "Bring me the case"},
        {"greek": "1", "english": "Hi, friend, try not"},
    ]
    notes: list[str] = []
    forced = m._resolve_pins(
        pins, slots, refs, speeches, "t", notes, transpositions=blocks
    )
    assert forced == [(2, 0), (0, 2)]
    assert not [n for n in notes if "crosses" in n]
    # Outside a declared window the contradiction stands and the later pin is
    # still dropped.
    dropped: list[str] = []
    assert m._resolve_pins(pins, slots, refs, speeches, "t", dropped) == [(2, 0)]
    assert [n for n in dropped if "crosses" in n]


def test_r9b_an_adopted_english_order_is_not_re_chosen_by_a_greek_group():
    """Grok's read of round 3, finding 2.

    An English transposition is ADOPTED: the reviewer has read the column and
    is stating what it prints. A1's Greek groups are CHOSEN, by cost. With
    the English applied first, an overlapping `citation.transpositions` group
    could replace the same span with the numeric order when that order scored
    cheaper -- the declaration silently overruled by a guess.
    """
    from drama_pipeline import stage1_turn_english as m
    from drama_pipeline import pair_dp

    # Printed order 5, 2, 3: the edition prints 2-3 after 5, so A1's group
    # for `{2, 3, before 5}` is the numeric order [2, 3, 5]. This column
    # prints the English of 3 before that of 2, which is a permutation of
    # the same three speeches.
    refs = ["5", "2", "3"]
    names = ["Alpha", "Beta", "Gamma"]
    # Lengths that make the numeric order strictly cheaper, so A1 would take
    # it if it were allowed to choose here: in the numeric order every
    # English speech stands beside the Greek whose length it matches.
    gc, ec = [40, 200, 80], [200, 80, 40]
    greek = [pair_dp.GreekNode(name=n, chars=c) for n, c in zip(names, gc)]
    english = [pair_dp.EnglishNode(name=n, chars=c) for n, c in zip(names, ec)]
    spans = [(c, "") for c in gc]

    def align(citation, english_blocks):
        return m._align_speech_runs(
            greek, english, list(names), [], None, spans, list(refs),
            "test-work", "primary",
            transpositions=list(citation),
            english_transpositions=list(english_blocks),
        )

    citation = [{"start": "2", "end": "3", "before": "5"}]
    english_block = [{"start": "3", "end": "3", "before": "2"}]
    # A1 alone takes the numeric order: printed 5, 2, 3 read as 2, 3, 5.
    assert align(citation, []).slot_order == [1, 2, 0]
    # The declaration alone swaps the two speeches it names.
    assert align([], english_block).slot_order == [0, 2, 1]
    # Together, the declaration stands: A1 does not re-choose its span.
    assert align(citation, english_block).slot_order == [0, 2, 1]


def test_r9_a_malformed_declaration_is_loud():
    """A declaration is a statement about a column, so one that cannot be
    read is a manifest fault, not a no-op: it fails loud instead of being
    dropped with a `continue` nobody sees."""
    from drama_pipeline import stage1_turn_english as m

    keys = [m._play_line_start_key(r) for r in ("1", "2", "3", "4")]
    good = [{"start": "3", "end": "4", "before": "1"}]
    assert m._english_transposed_run_groups(keys, good) == [[2, 3, 0, 1]]
    for bad in (
        {"start": "3", "end": "4"},
        {"start": "1", "end": "2", "before": "3"},
        {"start": "3", "end": "4", "before": "99"},
    ):
        with pytest.raises(ValueError, match="transposition"):
            m._english_transposed_run_groups(keys, [bad], work_id="t", slot="third")
    # before < start, and no speech lies in [before, start), so the raise is
    # the empty stayed set ("moves nothing"), not the ordering check.
    gapped = [m._play_line_start_key(r) for r in ("2", "3", "4")]
    with pytest.raises(ValueError, match="moves nothing"):
        m._english_transposed_run_groups(
            gapped, [{"start": "2", "end": "4", "before": "1"}],
            work_id="t", slot="third",
        )


def test_r2_an_undivided_block_is_anchored_at_the_first_segment_it_claims():
    """Septem's kommos (round 3, R2): Johnston prints 875-960 as one block and
    the DP hung it on 1:951 -- the LAST of the segments that claim it, since
    that is where its one English speech was matched. `_spread_long_speeches`
    walks strictly forward (`while segments[k]["id"] not in by_id`), so the
    sixteen segments that named it could never be reached and stood bare with
    a note pointing at a block below them.

    Two things follow from the claim run, and both are needed: the block is
    anchored at the FIRST segment of the run it claims, and inside that run
    the walk does not stop at a change of Greek speaker -- Antigone and
    Ismene answer the Chorus inside the kommos, and the claim is precisely
    the statement that the translator did not divide there.
    """
    from drama_pipeline.stage1_turn_english import (
        _claim_anchors, _spread_long_speeches,
    )

    sigla = {"Χο.": "Chorus", "Αν.": "Antigone", "Ισ.": "Ismene"}

    def seg(sid, label, nlines):
        return {
            "id": sid, "column": sid.split(":")[1],
            "speakers": [{"line": int(sid.split(":")[1]), "offset": 0, "label": label}],
            "lines": [{} for _ in range(nlines)],
        }

    segs = [
        seg("1:822", "Χο.", 4),
        seg("1:871", "Χο.", 4),
        seg("1:875", "Χο.", 4),
        seg("1:879", "Αν.", 4),
        seg("1:881", "Ισ.", 4),
        seg("1:951", "Χο.", 4),
        seg("1:961", "Αν.", 2),
    ]
    text = " ".join([
        "Chorus, on the two men slain, and their bodies dripping blood aa.",
        "Antigone, for the curse of Oedipus has taken its effect now bb.",
        "Ismene, and the words the gods once spoke keep their sharp edge cc.",
        "Chorus, O you who bring us so much sorrow, follow the wind of sighs dd.",
    ])
    block = {"id": "1:951", "column": "951", "text": text,
             "turns": [], "notes": [], "markers": []}
    head = {"id": "1:822", "column": "822",
            "text": "Chorus, O almighty Zeus, shall I cry out or mourn our leaders? "
                    "The curse of Oedipus has fallen on this house.",
            "turns": [], "notes": [], "markers": []}
    tail = {"id": "1:961", "column": "961", "text": "I will bury him myself.",
            "turns": [], "notes": [], "markers": []}
    # The claim map is coarse: a claim earned at 875 is carried back over the
    # whole bare run, 1:871 included, and 1:871 is the block at 1:822 going
    # on -- which the DP said itself (`derived`) and which that block is
    # already spread across. The aligner's reading bounds the run.
    claimed = {"1:871": "1:951", "1:875": "1:951", "1:879": "1:951", "1:881": "1:951"}
    derived = {"1:871": "1:822"}

    assert _claim_anchors([head, block, tail], segs, claimed, derived) == {"1:951": "1:875"}
    assert _claim_anchors([head, block, tail], segs, claimed) == {"1:951": "1:871"}
    out = _spread_long_speeches(
        [head, block, tail], segs, sigla, covered=derived, claimed=claimed,
    )
    assert [c["id"] for c in out] == [
        "1:822", "1:871", "1:875", "1:879", "1:881", "1:951", "1:961",
    ]
    assert out[0]["text"].startswith("Chorus, O almighty Zeus")
    assert out[1]["text"].startswith("The curse of Oedipus")
    out = out[2:]
    assert out[0]["text"].startswith("Chorus, on the two men")
    assert out[1]["text"].startswith("Antigone, for the curse")
    assert out[2]["text"].startswith("Ismene, and the words")
    assert out[3]["text"].startswith("Chorus, O you who bring us")
    # With nothing claimed the block stays whole, on the segment the DP
    # matched it to: an undivided block is distributed because a claim says
    # it covers those speeches, never because it is long.
    assert [c["id"] for c in _spread_long_speeches([block, tail], segs, sigla)] == [
        "1:951", "1:961",
    ]


def test_a5a_an_inherited_claim_from_another_block_takes_no_spread():
    """A5a. A bare continuation inherits an A2 claim whose donor is a
    different block. That claim may still be written as a coveredBy note;
    it must not lay THIS block's English on the segment. A speakerless
    segment otherwise continues unconditionally ("bare"), so the foreign
    donor never gets a look.

    The Septem kommos is the other shape and stays in
    `test_r2_an_undivided_block_is_anchored_at_the_first_segment_it_claims`:
    there the claim's donor IS this block and derived names nobody else, so
    the walk still crosses Antigone and Ismene.
    """
    from drama_pipeline.stage1_turn_english import _spread_long_speeches

    sigla = {"Χο.": "Chorus", "Αγ.": "Messenger", "Φυ.": "Guard"}
    # 1:5 holds its own chunk, so the messenger's block cannot anchor back
    # onto 1:3. 1:3 stays bare, and the chorus walk is the thing that reaches it.
    segs = [
        {"id": "1:1", "column": "1",
         "speakers": [{"line": 1, "offset": 0, "label": "Χο."}],
         "lines": [{} for _ in range(2)]},
        {"id": "1:3", "column": "3", "lines": [{} for _ in range(2)]},
        {"id": "1:5", "column": "5",
         "speakers": [{"line": 5, "offset": 0, "label": "Φυ."}],
         "lines": [{} for _ in range(2)]},
        {"id": "1:9", "column": "9",
         "speakers": [{"line": 9, "offset": 0, "label": "Αγ."}],
         "lines": [{} for _ in range(2)]},
    ]
    chorus = {
        "id": "1:1", "column": "1",
        "text": (
            "Chorus, on the tenth year of the war, and the ships that sailed. "
            "They cried out the war-cry, and a god heard them."
        ),
        "turns": [], "notes": [], "markers": [],
    }
    guard = {
        "id": "1:5", "column": "5", "text": "The guard keeps his watch.",
        "turns": [], "notes": [], "markers": [],
    }
    messenger = {
        "id": "1:9", "column": "9",
        "text": "The messenger tells of the beacon.",
        "turns": [], "notes": [], "markers": [],
    }
    out = _spread_long_speeches(
        [chorus, guard, messenger], segs, sigla, claimed={"1:3": "1:9"},
    )
    by_id = {c["id"]: c["text"] for c in out}
    assert "1:3" not in by_id
    assert "They cried out" in by_id["1:1"]
    assert by_id["1:5"] == "The guard keeps his watch."
    assert by_id["1:9"] == "The messenger tells of the beacon."
    # The aligner already named the other block. An inherited A2 claim that
    # still points at the chorus must not cross onto that segment either.
    segs[1] = {
        "id": "1:3", "column": "3",
        "speakers": [{"line": 3, "offset": 0, "label": "Αγ."}],
        "lines": [{} for _ in range(2)],
    }
    out = _spread_long_speeches(
        [chorus, guard, messenger], segs, sigla,
        covered={"1:3": "1:9"}, claimed={"1:3": "1:1"},
    )
    by_id = {c["id"]: c["text"] for c in out}
    assert "1:3" not in by_id
    assert "They cried out" in by_id["1:1"]


def test_a7_a_paragraph_cut_is_chosen_by_the_primary_not_by_proportion():
    """Agamemnon's parodos in Kosmos (A7): one block over six segments, cut
    in proportion to the Greek lines -- and a translator's paragraphs are not
    proportional to them, so 1:160 opened a paragraph early ("And I call upon
    Paean", Greek 146) and 1:205 two early ("So then the captain of the
    Achaean ships", Greek 184).

    Round 3 tried a paragraph pool chosen by `where()` and its acceptance run
    failed: a paragraph chosen by a length estimate inherits the bias it is
    meant to correct. The primary column is keyed to the Greek LINE, so it is
    the one thing in the build that knows what a segment says. Heads are
    compared, not whole passages: a forty-line segment runs over several of
    the translator's paragraphs, and whole-text cosine answers a different
    question (which paragraph shares most words with these forty lines).
    """
    from drama_pipeline.stage1_turn_english import _spread_long_speeches

    sigla = {"Χο.": "Chorus"}
    segs = [
        {"id": "1:1", "column": "1", "speakers": [{"line": 1, "label": "Χο."}],
         "lines": [{} for _ in range(2)]},
        {"id": "1:3", "column": "3", "lines": [{} for _ in range(6)]},
        {"id": "1:9", "column": "9", "lines": [{} for _ in range(2)]},
    ]
    para1 = (
        "This is now the tenth year since the mighty plaintiff against Priam, "
        "King Menelaos, and with him King Agamemnon, set forth from this land "
        "with a fleet of a thousand ships. They cried out the shrill war-cry "
        "of Ares in their fury, like vultures that wheel over their nest in "
        "grief for their young. But some one of the gods hears the cry, and "
        "sends a late-avenging Fury upon the transgressors."
    )
    para2 = (
        "Zeus, whoever he may be, if by this name it pleases him to be "
        "invoked, by this name I call to him. I have nothing to compare, "
        "weighing all things in the balance, except Zeus, if I am truly to "
        "cast aside the vain burden of my thought."
    )
    para3 = (
        "Learning comes by suffering, and the pain of memory drips upon the "
        "heart in sleep."
    )
    block = {"id": "1:1", "column": "1", "text": "\n\n".join([para1, para2, para3]),
             "turns": [], "notes": [], "markers": []}

    plain = _spread_long_speeches([block], segs, sigla)
    assert [c["id"] for c in plain] == ["1:1", "1:3", "1:9"]
    # In proportion the second segment's six lines open two sentences inside
    # the first paragraph -- the shape the primary is there to correct.
    assert plain[1]["text"].startswith("They cried out")

    bridge = {
        "1:3": "Zeus, whoever he may be, if by this name it pleases him to be "
               "invoked, by this name I call to him, as I weigh all things.",
        "1:9": "Learning comes by suffering; the pain of memory drips upon the "
               "heart even in sleep.",
    }
    out = _spread_long_speeches([block], segs, sigla, bridge=bridge)
    assert [c["id"] for c in out] == ["1:1", "1:3", "1:9"]
    assert out[0]["text"].startswith("This is now the tenth year")
    assert out[1]["text"].startswith("Zeus, whoever he may be")
    assert out[2]["text"].startswith("Learning comes by suffering")
    # A segment the primary cannot speak for is left to the ordinary pool:
    # no claim, no move.
    assert _spread_long_speeches(
        [block], segs, sigla, bridge={"1:3": "Alas."},
    )[1]["text"] == plain[1]["text"]


# --- R5: the reach-back window comes from the windows the DP was given ------


def _align_for_reach(
    refs, names, transpositions, repeated=(), greek_chars=None, english_chars=None,
):
    """The order choice is speaker-BLIND (A1), so what decides between two
    candidate orders here is length: each case gives the English the lengths
    the NUMERIC order's Greek asks for, which is what a column that follows
    the numbering looks like."""
    from drama_pipeline import pair_dp
    from drama_pipeline.stage1_turn_english import _align_speech_runs

    gc = list(greek_chars or [40] * len(names))
    ec = list(english_chars or [80] * len(names))
    greek = [pair_dp.GreekNode(name=n, chars=c) for n, c in zip(names, gc)]
    english = [pair_dp.EnglishNode(name=n, chars=c) for n, c in zip(names, ec)]
    spans = [(c, "") for c in gc]
    return _align_speech_runs(
        greek, english, list(names), [], None, spans, list(refs),
        "test-work", "primary",
        transpositions=list(transpositions), repeated_refs=list(repeated),
    )


def test_r5_a_frozen_doublet_inside_a_window_does_not_split_the_reach_back():
    """Grok's read of round 2, finding 1.

    `reach_back`'s window used to be inferred downstream as the longest run
    of walk positions whose slot is not the one printed there. A ref the
    edition prints twice keeps its PRINTED seat inside a window (round 2,
    finding 1), which is a fixed point in the middle of that run: the inferred
    window split in two and pass 1b could not walk back to the real head.
    The aligner knows which blocks it applied, so it reports them.
    """
    # Printed order 1, 4, 2, 5, 3 with a window over [2, 5]; ref "4" is
    # declared doubled, so it keeps position 1 while 2, 3 and 5 sort into the
    # seats left over -- a reordered window with a fixed point inside it.
    out = _align_for_reach(
        ["1", "4", "2", "5", "3"],
        ["Alpha", "Beta", "Gamma", "Beta", "Alpha"],
        [{"start": "2", "end": "4", "before": "5"}],
        repeated=["4"],
        greek_chars=[40, 40, 40, 100, 20],
        english_chars=[80, 80, 80, 40, 200],
    )
    assert out.slot_order == [0, 1, 2, 4, 3]
    # One window, from the position after the first slot to the last -- not
    # the two runs the fixed point at position 1 would leave.
    assert out.reach_spans == [(1, 4)]


def test_r5_two_adjacent_windows_stay_two_windows():
    """The other half of the same finding: two declared windows with no slot
    left in its printed place between them merged into one inferred run, so
    pass 1b could park a residual on a same-name slot in the NEIGHBOURING
    window."""
    out = _align_for_reach(
        ["2", "1", "4", "3"],
        ["Alpha", "Beta", "Gamma", "Delta"],
        [{"start": "1", "end": "1", "before": "2"},
         {"start": "3", "end": "3", "before": "4"}],
        greek_chars=[20, 100, 20, 100],
        english_chars=[200, 40, 200, 40],
    )
    assert out.slot_order == [1, 0, 3, 2]
    assert out.reach_spans == [(0, 1), (2, 3)]


def test_r5_no_window_reports_no_window():
    out = _align_for_reach(["1", "2", "3"], ["Alpha", "Beta", "Alpha"], [])
    assert out.slot_order == [0, 1, 2]
    assert out.reach_spans == []


def test_r5_a_residual_behind_the_cursor_in_the_dps_order_reaches_its_speech(tmp_path):
    """Grok's read of round 2, finding 2: the residual test that locks pass 1b.

    Round 2's residual fixture put the surplus English AFTER its own speech in
    the DP's order, where the ordinary forward reach finds it, so the test
    passed with pass 1b deleted. The Eumenides shape is the other way round:
    the edition prints Orestes' three lines before Apollo's twenty-one, the
    translation follows the numbering, and a second Apollo turn printed after
    Orestes' sits BEHIND the cursor once the window is read in numeric order.
    Only the reach back inside the window can seat it on Apollo's own speech.
    """
    spine = _spine_of(
        _numbered("1:1", ["1"], "Α.", 1),
        _numbered("1:5", ["5", "6"], "Β.", 2),
        _numbered("1:2", ["2", "3", "4"], "Γ.", 4),
    )
    source = (
        "ALPHA. First in my prayer I honour Earth the ancient prophet mother.\n"
        "GAMMA. I will never abandon you; your guardian to the very end.\n"
        "BETA. O king Apollo, since right well thou knowest what is just.\n"
        "GAMMA. Remember, and let no fear overcome your mind.\n"
    )
    bridge = {
        "1:1": "First in this prayer I give honour to Earth the first prophet mother.",
        "1:2": (
            "I will not abandon you; I am your guardian to the end. "
            "Remember, do not let fear conquer your mind."
        ),
        "1:5": "King Apollo, you know yourself what justice is; learn also this.",
    }
    english, _fn, _report = _paired(
        tmp_path, source, spine, _T_SIGLA, _T_ALIASES, bridge=bridge,
        blocks=[{"start": "2", "end": "4", "before": "6"}],
    )
    chunks = {c["id"]: c for c in english["chunks"]}
    assert chunks["1:2"]["text"].startswith("I will never abandon you")
    assert "Remember, and let no fear" in chunks["1:2"]["text"]
    assert chunks["1:5"]["text"].startswith("O king Apollo")
    assert "Remember" not in chunks["1:5"]["text"]
    assert not any(t.get("speakerMismatch") for t in chunks["1:2"]["turns"])


def test_r5_a_near_tie_keeps_the_printed_order_through_the_aligner(monkeypatch):
    """Grok's read of round 2, finding 2: the tolerance test drives the choice.

    Round 2's near-tie test only called `_strictly_cheaper`, so a raw `<` at
    the call site would still have passed it. Here the two candidate orders
    are made to differ by 1e-10 -- the rounding noise two sums of the same
    terms in a different sequence actually produce -- and the printed order
    has to survive the aligner's own decision.
    """
    from drama_pipeline import pair_dp
    from drama_pipeline.stage1_turn_english import _align_speech_runs

    real = pair_dp.align
    seen: list[float] = []

    def fake(greek, english, **kw):
        out = real(greek, english, **kw)
        # The second candidate offered is the numeric order; make it cheaper
        # by a hair, which is what reordered floating-point sums do.
        out.cost = 1000.0 - (1e-10 if seen else 0.0)
        seen.append(out.cost)
        return out

    monkeypatch.setattr(pair_dp, "align", fake)
    greek = [pair_dp.GreekNode(name=n, chars=40) for n in ("Alpha", "Beta", "Gamma")]
    english = [pair_dp.EnglishNode(name=n, chars=80) for n in ("Alpha", "Beta", "Gamma")]
    out = _align_speech_runs(
        greek, english, ["Alpha", "Beta", "Gamma"], [], None,
        [(40, "")] * 3, ["1", "3", "2"], "test-work", "primary",
        transpositions=[{"start": "2", "end": "2", "before": "3"}],
    )
    assert len(seen) >= 2  # both candidates really were costed
    assert out.slot_order == [0, 1, 2]
    assert out.reach_spans == []


# P1 (andromache review B8, 2026-09-21): a cue's own parenthetical --
# `MOLOSSUS (kneeling to MENELAUS).` -- is already in `_SPEAKER_LINE`'s
# stage group, but the ordinary cue branch appends that group to the spoken
# text, so the direction prints as a verse line. The case-slip cue already
# drops the brackets and carries the words as a direction of that turn.
def test_loeb_ocr_cue_parenthetical_is_a_direction_of_that_turn():
    text = (
        "THE PLAY\n\n"
        "ANDROMACHE. Pray, at thy lord's knees suing,\n"
        "Child !\n"
        "MOLOSSUS (kneeling to MENELAUS).\n"
        "Friend, in mercy ruing\n"
        "My death, of pardon tell!\n"
        "\n"
        "ANDROMACHE. My streaming eyelids weep.\n"
    )
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert [s["speaker_printed"] for s in speeches] == ["ANDROMACHE", "MOLOSSUS", "ANDROMACHE"]
    molossus = speeches[1]
    assert "(kneeling" not in molossus["text"]
    assert molossus["text"] == "Friend, in mercy ruing\nMy death, of pardon tell!"
    assert molossus["shown"] == (
        "_kneeling to MENELAUS_\n"
        "Friend, in mercy ruing\n"
        "My death, of pardon tell!"
    )
    assert "directions_before" not in molossus


# P2 (andromache review B5, 2026-09-21): a 1-3 letter lowercase turn-up is a
# wrap tail when the line before it does not end a sentence. `.?!;:` and a
# closing quote end a sentence; a comma does not. A 1-3 letter tail after a
# finished sentence stays refused (the old G2 guard).
def test_loeb_ocr_short_lowercase_turnup_joins_an_unfinished_line():
    text = (
        "THE PLAY\n\n"
        "HERMIONE. By Heaven's Queen, were it in mine halls, she should\n"
        "not\n"
        "See light and reap the harvest of my bed.\n"
        "As from this house to help thee, shouldst thou grant\n"
        "me\n"
        "Speech of thee, as thou dost.\n"
        "Whom your own hands had fashioned, dishonoured to\n"
        "lie\n"
        "In wretchedness, wretchedness.\n"
        "At the hands of a wife : and with murder she bought\n"
        "her\n"
        "Death, at the hands of her child to receive it.\n"
        "And still the long unfinished clause runs on,\n"
        "yet\n"
        "The sense continues past the comma.\n"
        "And with a river always at its edge of ample flowing water.\n"
        "a\n"
        "More lines follow the orphan.\n"
    )
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert speeches == [
        {
            "speaker_printed": "HERMIONE",
            "text": (
                "By Heaven's Queen, were it in mine halls, she should not\n"
                "See light and reap the harvest of my bed.\n"
                "As from this house to help thee, shouldst thou grant me\n"
                "Speech of thee, as thou dost.\n"
                "Whom your own hands had fashioned, dishonoured to lie\n"
                "In wretchedness, wretchedness.\n"
                "At the hands of a wife : and with murder she bought her\n"
                "Death, at the hands of her child to receive it.\n"
                "And still the long unfinished clause runs on, yet\n"
                "The sense continues past the comma.\n"
                "And with a river always at its edge of ample flowing water.\n"
                "a\n"
                "More lines follow the orphan."
            ),
        }
    ]


# P3 (trachiniae review N11, 2026-09-21): an unbracketed `Enter`/`Exit`/
# `Exeunt` line that ends its speech is a direction of the next speech.
# The same words in the middle of a speech, or a verse line that merely
# begins with them, stay verse. Synthetic bench, so the test does not
# depend on whether a live bench still prints the line unwrapped.
def test_loeb_ocr_unbracketed_trailing_entrance_is_the_next_speechs_direction():
    text = (
        "THE PLAY\n\n"
        "DEIANIRA. Sudden from her home was torn.\n"
        "Enter DEIANIRA.\n"
        "\n"
        "LICHAS. Lady, what message shall I bear my lord?\n"
        "Re-enter LICHAS.\n"
        "\n"
        "HYLLUS. Mother, I would that one wish were granted me.\n"
        "Exit HYLLUS.\n"
        "\n"
        "CHORUS. The curses work; the buried live again.\n"
        "Enter the halls and speak.\n"
        "The rest can wait until the dawn.\n"
        "Enter this house. For me the host whose heart\n"
        "Leaps out in welcome, rather than the rich.\n"
        "\n"
        "NURSE. I have stolen forth to speak with you alone.\n"
        "Enter then and tell the king what thou hast seen today across the city.\n"
        "\n"
        "MESSENGER. Woe's me, woe's me!\n"
        "Exeunt.\n"
        "\n"
        "PELEUS. O my prophetic soul, what ill it bodes.\n"
    )
    speeches, _notes = parse_play_speeches(text, "THE PLAY", format="loeb-ocr", verse=True)
    assert speeches[0] == {
        "speaker_printed": "DEIANIRA",
        "text": "Sudden from her home was torn.",
    }
    assert speeches[1] == {
        "speaker_printed": "LICHAS",
        "text": "Lady, what message shall I bear my lord?",
        "directions_before": ["Enter DEIANIRA."],
    }
    assert speeches[2] == {
        "speaker_printed": "HYLLUS",
        "text": "Mother, I would that one wish were granted me.",
        "directions_before": ["Re-enter LICHAS."],
    }
    assert speeches[3]["speaker_printed"] == "CHORUS"
    assert speeches[3]["directions_before"] == ["Exit HYLLUS."]
    assert speeches[3]["text"] == (
        "The curses work; the buried live again.\n"
        "Enter the halls and speak.\n"
        "The rest can wait until the dawn.\n"
        "Enter this house. For me the host whose heart\n"
        "Leaps out in welcome, rather than the rich."
    )
    assert speeches[4] == {
        "speaker_printed": "NURSE",
        "text": (
            "I have stolen forth to speak with you alone.\n"
            "Enter then and tell the king what thou hast seen today across the city."
        ),
    }
    assert speeches[5] == {
        "speaker_printed": "MESSENGER",
        "text": "Woe's me, woe's me!",
    }
    assert speeches[6] == {
        "speaker_printed": "PELEUS",
        "text": "O my prophetic soul, what ill it bodes.",
        "directions_before": ["Exeunt."],
    }
    for speech in speeches:
        assert speech["text"].splitlines()[-1] not in {
            "Enter DEIANIRA.",
            "Re-enter LICHAS.",
            "Exit HYLLUS.",
            "Exeunt.",
        }
