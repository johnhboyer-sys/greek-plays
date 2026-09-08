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


def test_lcs_leaves_a_foreign_residual_unassigned():
    """P2i finding 5: the extra Dicaeopolis speech is not the Herald's, so it
    is left out and counted rather than parked in his column."""
    english, _footnotes, report = _parse()
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert "1:40" not in by_id
    herald = by_id["1:20"]
    assert "The assembly is open." in herald["text"]
    assert "An extra speech the Greek does not split." not in herald["text"]
    assert [turn["speaker"] for turn in herald["turns"]] == ["Herald"]
    assert report["residual_unassigned"] == 1
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
    assert report["residual_unassigned"] == 1
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
    assert dionysus[0]["text"].startswith("(_to Xanthias_)\n\nBut why")


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
    assigned, residual, head_unassigned, unassigned = _assign_speeches(4, [(3, 2)], 3)
    assert assigned[0] == []
    assert assigned[3] == [2]
    assert residual == 0
    assert head_unassigned == 2
    assert unassigned == 0

    matched, matched_residual, matched_head, _un = _assign_speeches(
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

    skipped, skipped_residual, skipped_head, _un2 = _assign_speeches(
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


def test_residual_is_not_parked_on_a_segment_that_speaker_never_speaks():
    """P2i finding 5, Frogs-shaped: Dionysus and Xanthias alternate, the
    English runs two Xanthias speeches together, and the second one may not be
    parked on the Dionysus segment the pairing landed on."""
    greek = ["Dionysus", "Xanthias", "Dionysus", "Xanthias"]
    english = ["Dionysus", "Xanthias", "Dionysus", "Xanthias", "Dionysus"]
    # English 4 (Dionysus) has no pair; last_gi is the Xanthias segment 3.
    assigned, residual, head, unassigned = _assign_speeches(
        4,
        [(0, 0), (1, 1), (2, 2), (3, 3)],
        5,
        greek_names=greek,
        english_names=english,
    )
    assert assigned[3] == [3]
    assert residual == 0
    assert head == 0
    assert unassigned == 1

    # A name the segment's own lines carry (an antilabe share) still parks,
    # and so does an unnamed continuation.
    parked, parked_residual, _head, parked_unassigned = _assign_speeches(
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


def test_named_residual_does_not_park_on_a_speakerless_lyric():
    """P2j finding 4, Frogs-shaped: the ode at 1:383 carries no speaker at
    all, so the segment's primary is None.  That is not a wildcard — Dionysus'
    unpaired next speech used to park on the ode and print in its column.
    Only the nameless residuals (a continuation, or a bench scan's unreadable
    label) may still park there."""
    from drama_pipeline.stage1_turn_english import _OCR_JUNK

    greek = ["Dionysus", None]  # segment 1 is the unattributed ode
    pairs = [(0, 0), (1, 1)]
    assigned, residual, head, unassigned = _assign_speeches(
        2,
        pairs,
        3,
        greek_names=greek,
        english_names=["Dionysus", "Chorus", "Dionysus"],
    )
    assert assigned[1] == [1]
    assert residual == 0
    assert head == 0
    assert unassigned == 1

    parked, parked_residual, _head, parked_unassigned = _assign_speeches(
        2,
        pairs,
        4,
        greek_names=greek,
        english_names=["Dionysus", "Chorus", None, _OCR_JUNK],
    )
    assert parked[1] == [1, 2, 3]
    assert parked_residual == 2
    assert parked_unassigned == 0


def test_head_residue_unassigned_is_reported(tmp_path):
    path = tmp_path / "play.txt"
    path.write_text(
        "TEST PLAY\nCHORUS. Cast-list junk.\nALPHA. Real opening.\nFINIS\n",
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
    assert report["paired"] == 1
    assert [chunk["id"] for chunk in english["chunks"]] == ["1:1"]
    assert "Cast-list junk" not in english["chunks"][0]["text"]
    assert english["chunks"][0]["turns"][0]["speaker"] == "Alpha"


def test_quality_numbers_are_surfaced_in_the_stage1_summary():
    from drama_pipeline import __main__ as cli

    main_src = Path(cli.__file__).read_text(encoding="utf-8")
    assert "ratio_outliers={report['length_ratio_outlier_count']}" in main_src
    assert "turn_shifts={report['turn_shift_count']}" in main_src
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


def _stage2_with_report(monkeypatch, tmp_path, report: dict, manifest: Manifest):
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
        ]
    }
    alignment = {
        "pairs": [{"segment": f"1:{n}", "english": f"1:{n}"} for n in (1, 2, 3)],
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
        {**base, "turn_shift_count": 9, "turn_shift_rate": 0.09},
        _turn_text_manifest(),
    )
    shift = shifted["checks"]["turn_text_turn_shift"]
    assert shift["ok"] is False
    assert "turn-shift rate 0.090 exceeds maximum 0.050" in shift["error"]
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
            "text": "(_above_) This is the third speech in the play.",
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
        and speech["text"].startswith("(_above_)")
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
    """A packed segment (an antilabe hands the line over mid-way) used to pair
    as whichever speaker its first EVENT named. Pairing now uses the line-level
    rule — the speaker of the first line at offset 0 — and the packed second
    speaker rides as an alternative name (P2h finding 9)."""
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
    assert m._greek_segment_alt_names(packed, resolver) == {"Herald"}
    # The line-level rule, offset and all.
    assert m.speaker_at(packed, 1004, resolver) == "Ismene"
    assert m.speaker_at(packed, 1005, resolver) == "Ismene"
    assert m.speaker_at(packed, 1005, resolver, prefer="Herald") == "Herald"
    assert m.speaker_at(packed, 1006, resolver) == "Herald"
    # A gap turn may pair with either share of the packed line, and with
    # neither when the English names a third character.
    assert m._pair_turns(["Ismene"], ["Herald"], [{"Herald"}]) == [(0, 0)]
    assert m._pair_turns(["Ismene"], ["Antigone"], [{"Herald"}]) == []
    assert m._pair_turns(
        ["Chorus", "Ismene", "Chorus"],
        ["Chorus", "Herald", "Chorus"],
        [set(), {"Herald"}, set()],
    ) == [(0, 0), (1, 1), (2, 2)]
