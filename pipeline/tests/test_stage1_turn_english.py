import json
from pathlib import Path

from drama_pipeline.stage1_english import build_alignment
from drama_pipeline.stage1_turn_english import parse_play_speeches, parse_translation


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
    spine = json.loads((FIXTURES / "spine.json").read_text(encoding="utf-8"))
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
    spine = json.loads((FIXTURES / "spine.json").read_text(encoding="utf-8"))
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
                    "Δι.": "Dicaeopolis",
                    "Δη.Νι.": "Demosthenes and Nicias",
                    "Κη.": "Herald",
                    "Χο.": "Chorus",
                    "Αγγ.": "Messenger",
                    "Λα.": "Lamachus",
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
