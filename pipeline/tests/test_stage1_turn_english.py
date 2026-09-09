import json
from pathlib import Path

import pytest

from drama_pipeline.config import Manifest, SOURCES_DIR
from drama_pipeline.stage1_english import build_alignment
from drama_pipeline.stage1_turn_english import (
    _assign_speeches,
    parse_play_speeches,
    parse_translation,
)


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
    """P3.3: the extra Dicaeopolis speech is not the Herald's and no segment
    between the surrounding pairs is his either — so it is SHOWN in the
    Herald's column carrying the disagreement, never dropped (it used to be
    counted as `residual_unassigned` and reach no chunk at all)."""
    english, _footnotes, report = _parse()
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert "1:40" not in by_id
    herald = by_id["1:20"]
    assert "The assembly is open." in herald["text"]
    assert "An extra speech the Greek does not split." in herald["text"]
    assert [turn["speaker"] for turn in herald["turns"]] == ["Herald", "Dicaeopolis"]
    assert "speakerMismatch" not in herald["turns"][0]
    assert herald["turns"][1]["speakerMismatch"] == {
        "english": "Dicaeopolis",
        "greek": "Herald",
    }
    # Not every turn of the chunk disagrees, so the pre-P2h chunk-level
    # compatibility flag stays off.
    assert "speakerMismatch" not in herald
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
):
    from drama_pipeline import stage2_validate as s2

    stage1 = tmp_path / "stage1"
    stage1.mkdir(exist_ok=True, parents=True)
    if report is not None:
        (stage1 / "english_report.json").write_text(
            json.dumps(report), encoding="utf-8"
        )
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
        "turn_text_pairing_floor",
    ):
        assert missing["checks"][key]["ok"] is False
        assert "no stage1 English report" in missing["checks"][key]["error"]


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
    assert len(speeches) == 537
    assert speeches[0]["speaker_printed"] == "LYSISTRATA"
    assert speeches[-1]["speaker_printed"] == "SPARTANS"
    printed = {speech["speaker_printed"] for speech in speeches}
    assert "MYRRHINE" in printed
    assert "STRATYLLIS" in printed
    assert "O" not in printed
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


@pytest.mark.parametrize(
    "work, line_no, junk",
    [("oedipus-tyrannus", 904, "WOU. 4, F"), ("electra-soph", 1706, "VQL. I. R")],
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
    assert m._pair_turns([s["name"] for s in slots], ["Ismene", "Herald"]) == [
        (0, 0),
        (1, 1),
    ]
    assert m._pair_turns(["Ismene", "Herald"], ["Antigone"]) == []


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


def test_an_unnamed_slot_never_pairs_in_a_gap_zip():
    """P3.5 finding 2: the gap zip used `turns._names_match`, where None is a
    WILDCARD.  So a speakerless lyric slot — the one every eventless segment
    gets — could take any named English speech that happened to fall in an
    equal-length gap, a pair the LCS and the residual walk both refuse.  A
    pair now needs two real, equal names on both sides."""
    from drama_pipeline import stage1_turn_english as m

    # The anchors are Alpha and Gamma; the gap is one slot against one speech.
    assert m._pair_turns(["Alpha", None, "Gamma"], ["Alpha", "Beta", "Gamma"]) == [
        (0, 0),
        (2, 2),
    ]
    # And symmetrically: an unattributed English continuation is residue, not
    # a pairing wildcard for a named Greek share.
    assert m._pair_turns(["Alpha", "Beta", "Gamma"], ["Alpha", None, "Gamma"]) == [
        (0, 0),
        (2, 2),
    ]
    assert m._pair_turns(["Alpha", None, "Gamma"], ["Alpha", None, "Gamma"]) == [
        (0, 0),
        (2, 2),
    ]
    # A named gap of equal length still zips — that is the whole point of it.
    assert m._pair_turns(["Alpha", "Beta"], ["Alpha", "Beta"]) == [(0, 0), (1, 1)]


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

    # The bound never crosses into the NEXT segment: a same-name share there
    # is out of reach, and the segment fallback still parks on the cursor's
    # window as before.
    assigned, _r, _h, _u, flags = _assign_speeches(
        3,
        [(0, 0), (1, 2)],
        3,
        greek_names=["Alpha", "Hoopoe", "Peisthetaerus"],
        english_names=["Alpha", "Peisthetaerus", "Hoopoe"],
        greek_alt=[{"Alpha"}, {"Hoopoe"}, {"Peisthetaerus"}],
        greek_segments=[0, 1, 2],
    )
    assert assigned == {0: [0, 1], 1: [2], 2: []}
    assert flags == {1: "Alpha"}


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
