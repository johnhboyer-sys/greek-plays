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


def test_lcs_groups_extra_english_and_leaves_greek_unmatched():
    english, _footnotes, report = _parse()
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert "1:40" not in by_id
    herald = by_id["1:20"]
    assert "The assembly is open." in herald["text"]
    assert "An extra speech the Greek does not split." in herald["text"]
    assert "\n\n" in herald["text"]
    assert herald["turns"][0]["speaker"] == "Herald"
    assert herald["turns"][1]["speaker"] == "Dicaeopolis"
    assert herald["turns"][1]["offset"] > 0
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
    assert report["residual_grouped"] == 1
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


def test_lysistrata_chorus_of_athenians_stays_in_preceding_speech():
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
    assert "Appear, appear, dancers" in preceding[0]["text"]
    assert all(speech["speaker_printed"] != "CHORUS OF ATHENIANS" for speech in speeches)
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
    assert report["speech_mismatches"] == [
        {"greek_id": "1:3", "english_index": 2, "ratio": 10.0}
    ]
    assert report["speech_mismatch_count"] == 1


def test_head_residue_attaches_only_when_speaker_matches():
    assigned, residual, head_unassigned = _assign_speeches(4, [(3, 2)], 3)
    assert assigned[0] == []
    assert assigned[3] == [2]
    assert residual == 0
    assert head_unassigned == 2

    matched, matched_residual, matched_head = _assign_speeches(
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

    skipped, skipped_residual, skipped_head = _assign_speeches(
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


def test_mismatch_rate_is_surfaced_in_summary_and_stage2():
    from drama_pipeline import __main__ as cli
    from drama_pipeline import stage2_validate as s2

    main_src = Path(cli.__file__).read_text(encoding="utf-8")
    assert "mismatches={report['speech_mismatch_count']}" in main_src
    stage2_src = Path(s2.__file__).read_text(encoding="utf-8")
    assert 'english_cfg.get("max_mismatch_rate", 0.15)' in stage2_src
    assert "speech mismatch rate" in stage2_src
    assert "turn_text_mismatches" in stage2_src


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
