import json
from pathlib import Path

import pytest
from lxml import etree

from drama_pipeline.config import Manifest
from drama_pipeline.stage1_perseus_play_english import parse_translation
from drama_pipeline.stage1_turn_english import _SiglaResolver
from drama_pipeline.stage2_validate import validate
from drama_pipeline.stage7_emit import (
    _manifest_v1_fields,
    _play_line_english_roster_gate,
    chapter_ranges,
    emit_books,
)


TEI = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker>
      <l n="0">Alpha</l>
      <l n="1">First <del>cut me</del> text<note n="1" resp="Smyth">One <q>note</q>.</note>.</l>
    </sp>
    <sp><speaker>Beta</speaker>
      <l n="5">Second text.</l>
      <l n="7">Snapped text<note n="1" resp="Smyth">Another note.</note>.</l>
    </sp>
    <sp><speaker>Gamma</speaker><l n="10">Third text.</l></sp>
  </div>
</body></text></TEI>
"""

ALIASES = {"Alpha": "Alpha", "Beta": "Beta", "Gamma": "Gamma"}
SIGLA = {"A": "Alpha", "B": "Beta", "G": "Gamma"}


def _spine() -> dict:
    return {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1",
                "book": 1,
                "column": "1",
                "lines": [{"n": n, "ref": str(n), "text": f"g{n}"} for n in range(1, 5)],
                "speakers": [{"line": 1, "offset": 0, "label": "A"}],
            },
            {
                "id": "1:5",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": n, "ref": str(n), "text": f"g{n}"} for n in (5, 6, 8)
                ],
                "speakers": [{"line": 1, "offset": 0, "label": "B"}],
            },
            {
                "id": "1:10",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": n, "ref": str(n), "text": f"g{n}"} for n in range(10, 13)
                ],
                "speakers": [{"line": 10, "offset": 0, "label": "G"}],
            },
        ],
    }


def _parse(tmp_path: Path, tei: str, spine: dict, *, aliases=None, sigla=None, covered=None):
    xml_path = tmp_path / "play.xml"
    xml_path.write_text(tei, encoding="utf-8")
    return parse_translation(
        xml_path,
        spine,
        work_id="test-play",
        translation_id="smyth",
        sigla=sigla if sigla is not None else SIGLA,
        english_aliases=aliases if aliases is not None else ALIASES,
        covered_decl=covered,
    )


def test_manifest_covered_declarations_join_the_covered_map(tmp_path: Path):
    """REVIEW-CHECKLIST 7 (2026-09-09): a hole the span rule cannot prove but
    a reviewer confirmed sits in a neighbour's block is declared in the
    manifest and rides into english_covered_by like a computed one."""
    english, _f, _r = _parse(tmp_path, TEI, _spine(), covered=[{"greek": "10", "by": "5"}])
    assert english["english_covered_by"].get("1:10") == "1:5"
    with pytest.raises(ValueError):
        _parse(tmp_path, TEI, _spine(), covered=[{"greek": "999", "by": "5"}])


def test_perseus_play_chunks_ticks_notes_turns_and_report(tmp_path: Path):
    english, footnotes, report = _parse(tmp_path, TEI, _spine())

    assert [chunk["id"] for chunk in english["chunks"]] == ["1:1", "1:5", "1:10"]
    first, second, third = english["chunks"]
    assert "cut me" not in first["text"]
    assert [tick["n"] for tick in first["bekker"]] == [1]
    assert [tick["n"] for tick in second["bekker"]] == [5, 8]
    assert [tick["n"] for tick in third["bekker"]] == [10]
    assert all(
        tick["real"] is True
        for chunk in english["chunks"]
        for tick in chunk["bekker"]
    )

    assert list(footnotes) == ["1.1", "2.1"]
    assert "<q>note</q>" in footnotes["1.1"]
    assert "[^1.1]" in first["text"] and "[^2.1]" in second["text"]

    assert first["turns"] == [
        {"offset": 0, "speaker": "Alpha", "display": "Alpha"},
    ]
    assert second["turns"] == [
        {"offset": 0, "speaker": "Beta", "display": "Beta"},
    ]
    assert third["turns"] == [
        {"offset": 0, "speaker": "Gamma", "display": "Gamma"},
    ]

    assert report["anchor_count"] == 4
    assert report["snaps"] == [
        {
            "play": "test-play",
            "english_line": 7,
            "greek_ref": "8",
            "english_speaker": "Beta",
            "greek_speaker": "Beta",
            "snapped_to": "8",
            "segment": "1:5",
        }
    ]
    assert report["speech_mismatch_count"] == 0
    assert report["segments_with_chunk"] == 3
    assert report["segments_total"] == 3
    assert report["coverage_ratio"] == 1.0
    assert report["speakers"]["only_in_english"] == []


def test_one_line_drift_binds_to_the_right_speaker(tmp_path: Path):
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1076",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": 1076, "ref": "1076", "text": "k"},
                    {"n": 1077, "ref": "1077", "text": "k"},
                ],
                "speakers": [{"line": 1, "offset": 0, "label": "Κα."}],
            },
            {
                "id": "1:1078",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": 1078, "ref": "1078", "text": "ch"},
                    {"n": 1079, "ref": "1079", "text": "ch"},
                ],
                "speakers": [{"line": 1, "offset": 0, "label": "Χο."}],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Cassandra</speaker><l n="1076">Woe.</l></sp>
    <sp><speaker>Chorus</speaker><l n="1077">Once more she cries.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Cassandra": "Cassandra", "Chorus": "Chorus"},
        sigla={"Κα.": "Cassandra", "Χο.": "Chorus"},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert "Once more she cries." not in by_id["1:1076"]["text"]
    assert "Once more she cries." in by_id["1:1078"]["text"]
    assert any(t["speaker"] == "Chorus" for t in by_id["1:1078"]["turns"])
    assert report["speech_mismatches"]
    mismatch = report["speech_mismatches"][0]
    assert mismatch["english_line"] == 1077
    assert mismatch["english_speaker"] == "Chorus"
    assert mismatch["greek_speaker"] == "Cassandra"
    assert mismatch["attached_to"] == "1:1078"
    assert mismatch["kind"] == "speaker_repair"
    assert "speakerMismatch" not in by_id["1:1078"]
    assert "speakerMismatch" not in by_id["1:1076"]
    assert report["speech_mismatch_count"] == 1
    assert report["unresolved_mismatch_count"] == 0
    assert report["attribution_differences"] == []
    assert report["attribution_difference_count"] == 0


def test_attribution_difference_attaches_to_line_owner_with_flag(tmp_path: Path):
    """Greek gives 1320 to the Messenger; English is Agamemnon with no
    Agamemnon speech within ±3 → attach to 1:1320 with speakerMismatch."""
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1310",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1310, "ref": "1310", "text": "g"}],
                "speakers": [{"line": 1, "offset": 0, "label": "Αγ."}],
            },
            {
                "id": "1:1320",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1320, "ref": "1320", "text": "g"}],
                "speakers": [{"line": 1, "offset": 0, "label": "Αγγ."}],
            },
            {
                "id": "1:1324",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1324, "ref": "1324", "text": "g"}],
                "speakers": [{"line": 1, "offset": 0, "label": "Οδ."}],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Agamemnon</speaker><l n="1320">I will not hear him.</l></sp>
  </div>
</body></text></TEI>
"""
    aliases = {
        "Agamemnon": "Agamemnon",
        "Messenger": "Messenger",
        "Odysseus": "Odysseus",
    }
    sigla = {"Αγ.": "Agamemnon", "Αγγ.": "Messenger", "Οδ.": "Odysseus"}
    english, _footnotes, report = _parse(
        tmp_path, tei, spine, aliases=aliases, sigla=sigla
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert set(by_id) == {"1:1320"}
    assert "I will not hear him." in by_id["1:1320"]["text"]
    assert by_id["1:1320"]["speakerMismatch"] == {
        "english": "Agamemnon",
        "greek": "Messenger",
    }
    # P2h finding 3: the disagreement rides on the English TURN; the
    # chunk-level field survives only because every turn here carries it.
    assert by_id["1:1320"]["turns"] == [
        {
            "offset": 0,
            "speaker": "Agamemnon",
            "display": "Agamemnon",
            "speakerMismatch": {"english": "Agamemnon", "greek": "Messenger"},
        },
    ]
    assert report["attribution_differences"] == [
        {
            "greek_id": "1:1320",
            "line": 1320,
            "english_speaker": "Agamemnon",
            "greek_speaker": "Messenger",
        }
    ]
    assert report["attribution_difference_count"] == 1
    assert report["speech_mismatch_count"] == 1
    assert report["unresolved_mismatch_count"] == 0
    mismatch = report["speech_mismatches"][0]
    assert mismatch["attached_to"] == "1:1320"
    assert mismatch["kind"] == "attribution_difference"

    alignment = _alignment_for(spine, english)
    result = validate(_play_manifest(gaps=[]), spine, english, alignment)
    unexpected = result["checks"]["alignment"]["unexpected_unmatched"]
    assert "1:1320" not in unexpected

    tokens = {
        "segments": [
            {
                "id": seg["id"],
                "lines": [{"n": line["n"], "tokens": []} for line in seg["lines"]],
            }
            for seg in spine["segments"]
        ]
    }
    out_dir = tmp_path / "dist"
    out_dir.mkdir()
    emit_books(spine, tokens, english, chapter_ranges(spine, []), out_dir)
    book = json.loads((out_dir / "book-01.json").read_text(encoding="utf-8"))
    emitted = {seg["id"]: seg for seg in book["segments"]}
    assert emitted["1:1320"]["english"]["text"] == "I will not hear him."
    assert emitted["1:1320"]["english"]["speakerMismatch"] == {
        "english": "Agamemnon",
        "greek": "Messenger",
    }
    assert "speakerMismatch" not in (emitted["1:1310"].get("english") or {})
    assert emitted["1:1310"]["english"] is None


def test_english_speech_splits_across_greek_line_owners(tmp_path: Path):
    """One English <sp> whose <l n> anchors fall in two Greek speeches
    emits one chunk per Greek segment, even when the English speaker
    differs from the second Greek speaker. Each chunk carries the English
    speech's turn at offset 0."""
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:100",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": n, "ref": str(n), "text": "g"} for n in (100, 101)
                ],
                "speakers": [{"line": 1, "offset": 0, "label": "Χο."}],
            },
            {
                "id": "1:102",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": n, "ref": str(n), "text": "g"} for n in (102, 103)
                ],
                "speakers": [{"line": 1, "offset": 0, "label": "Αγ."}],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Chorus</speaker>
      <l n="100">We sing.</l>
      <l n="102">A king replies, run together.</l>
    </sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Chorus": "Chorus", "Agamemnon": "Agamemnon"},
        sigla={"Χο.": "Chorus", "Αγ.": "Agamemnon"},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert "We sing." in by_id["1:100"]["text"]
    assert "A king replies, run together." in by_id["1:102"]["text"]
    assert "A king replies, run together." not in by_id["1:100"]["text"]
    assert by_id["1:100"]["turns"] == [
        {"offset": 0, "speaker": "Chorus", "display": "Chorus"},
    ]
    # P2j finding 1: the Agamemnon half of the Chorus's speech is attached and
    # FLAGGED — a multi-span piece disagrees exactly as a singleton does.
    assert by_id["1:102"]["turns"] == [
        {
            "offset": 0,
            "speaker": "Chorus",
            "display": "Chorus",
            "speakerMismatch": {"english": "Chorus", "greek": "Agamemnon"},
        },
    ]
    assert report["segments_with_chunk"] == 2
    assert any(
        item.get("attached_to") == "1:102" and item["english_speaker"] == "Chorus"
        for item in report["speech_mismatches"]
    )
    assert report["attribution_differences"] == [
        {
            "greek_id": "1:102",
            "line": 102,
            "english_speaker": "Chorus",
            "greek_speaker": "Agamemnon",
        }
    ]


@pytest.mark.parametrize(
    ("ref", "text"),
    [("513b", "Abandoned wretch!"), ("1270a", "Ah!")],
)
def test_lettered_anchor_attaches_to_exact_spine_ref(tmp_path: Path, ref: str, text: str):
    base = int(ref.rstrip("abcdefghijklmnopqrstuvwxyz"))
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": f"1:{base}",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1, "ref": str(base), "text": "g"}],
                "speakers": [{"line": 1, "offset": 0, "label": "A"}],
            },
            {
                "id": f"1:{ref}",
                "book": 1,
                "column": "1",
                "lines": [{"n": 2, "ref": ref, "text": "g"}],
                "speakers": [{"line": 1, "offset": 0, "label": "A"}],
            },
        ],
    }
    tei = f"""\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation"><sp><speaker>Alpha</speaker>
    <l n="{ref}">{text}</l>
  </sp></div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(tmp_path, tei, spine)
    assert [chunk["id"] for chunk in english["chunks"]] == [f"1:{ref}"]
    assert text in english["chunks"][0]["text"]
    assert not any(a["kind"] == "non_numeric_anchor" for a in report["anomalies"])


def test_lettered_anchor_falls_back_to_integer_base(tmp_path: Path):
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1270",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1, "ref": "1270", "text": "g"}],
                "speakers": [{"line": 1, "offset": 0, "label": "A"}],
            }
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation"><sp><speaker>Alpha</speaker>
    <l n="1270a">Ah!</l>
  </sp></div>
</body></text></TEI>
"""
    english, _footnotes, _report = _parse(tmp_path, tei, spine)
    assert english["chunks"][0]["id"] == "1:1270"
    assert english["chunks"][0]["text"] == "Ah!"


@pytest.mark.parametrize(
    ("filename", "ref", "expected"),
    [
        ("tlg0006.tlg008.perseus-eng2.xml", "513b", "Abandoned wretch!"),
        ("tlg0006.tlg003.perseus-eng2.xml", "1270a", "Ah!"),
    ],
)
def test_real_perseus_lettered_lines_attach(tmp_path, filename, ref, expected):
    source = Path(__file__).resolve().parents[2] / "sources" / "perseus" / filename
    tree = etree.parse(str(source))
    lines = tree.xpath(f'.//*[local-name()="l" and @n="{ref}"]')
    assert len(lines) == 1
    speech = lines[0].xpath('ancestor::*[local-name()="sp"][1]')[0]
    tei = (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>'
        '<div type="translation">'
        + etree.tostring(speech, encoding="unicode")
        + "</div></body></text></TEI>"
    )
    base = int(ref.rstrip("abcdefghijklmnopqrstuvwxyz"))
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": f"1:{ref}",
                "book": 1,
                "column": "1",
                "lines": [{"n": base, "ref": ref, "text": "g"}],
                "speakers": [],
            }
        ],
    }
    english, _footnotes, _report = _parse(
        tmp_path, tei, spine, aliases={}, sigla={}
    )
    assert english["chunks"][0]["id"] == f"1:{ref}"
    assert expected in english["chunks"][0]["text"]


def test_seven_multi_anchor_speech_does_not_fill_intervening_turns(tmp_path: Path):
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1040",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": n, "ref": str(n), "text": "g"} for n in (1040, 1041)
                ],
                "speakers": [{"line": 1, "offset": 0, "label": "Χο."}],
            },
            {
                "id": "1:1042",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": 1042, "ref": "1042", "text": "g"}
                ],
                "speakers": [{"line": 1, "offset": 0, "label": "Κη."}],
            },
            {
                "id": "1:1043",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": 1043, "ref": "1043", "text": "g"}
                ],
                "speakers": [{"line": 1, "offset": 0, "label": "Αν."}],
            },
            *[
                {
                    "id": f"1:{n}",
                    "book": 1,
                    "column": "1",
                    "lines": [{"n": n, "ref": str(n), "text": "g"}],
                    "speakers": [
                        {
                            "line": 1,
                            "offset": 0,
                            "label": "Κη." if n % 2 == 0 else "Αν.",
                        }
                    ],
                }
                for n in range(1044, 1048)
            ],
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Chorus</speaker>
      <l n="1040">I will find the means to bury him.</l>
      <l n="1045">With my own hands I will cover him.</l>
    </sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Antigone": "Antigone"},
        sigla={"Αν.": "Antigone", "Κη.": "Herald"},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert set(by_id) == {"1:1040", "1:1045"}
    assert "I will find" in by_id["1:1040"]["text"]
    assert "With my own hands" in by_id["1:1045"]["text"]
    combined = " ".join(chunk["text"] for chunk in english["chunks"])
    assert combined.count("I will find") == 1
    assert combined.count("With my own hands") == 1
    assert all(f"1:{n}" not in by_id for n in (1042, 1043, 1044, 1046, 1047))
    assert report["segments_with_chunk"] == 2
    # P2j finding 1: the second anchor lands in Antigone's speech, so that
    # turn — and its single-turn chunk — carry the disagreement.  1:1040's
    # siglum is outside this test's sigla map, so that half stays unflagged.
    assert "speakerMismatch" not in by_id["1:1040"]
    assert by_id["1:1045"]["speakerMismatch"] == {
        "english": "Chorus",
        "greek": "Antigone",
    }
    assert report["attribution_differences"] == [
        {
            "greek_id": "1:1045",
            "line": 1045,
            "english_speaker": "Chorus",
            "greek_speaker": "Antigone",
        }
    ]


def test_suppliants_anchor_stops_at_next_english_speech(tmp_path: Path):
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": f"1:{n}",
                "book": 1,
                "column": "1",
                "lines": [{"n": n, "ref": str(n), "text": "g"}],
                "speakers": [
                    {"line": 1, "offset": 0, "label": "H" if n < 513 else "C"}
                ],
            }
            for n in range(510, 514)
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Herald</speaker><l n="510">Hear my command.</l></sp>
    <sp><speaker>Chorus</speaker><l n="513">Do not leave me.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, _report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Herald": "Herald", "Chorus": "Chorus"},
        sigla={"H": "Herald", "C": "Chorus"},
    )
    by_id = {chunk["id"]: chunk["text"] for chunk in english["chunks"]}
    assert by_id == {"1:510": "Hear my command.", "1:513": "Do not leave me."}


def test_agamemnon_1203_to_1213_singletons_follow_speaker(tmp_path: Path):
    speakers = {
        n: ("Chorus" if n % 2 else "Cassandra") for n in range(1202, 1214)
    }
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": f"1:{n}",
                "book": 1,
                "column": "1",
                "lines": [{"n": n, "ref": str(n), "text": "g"}],
                "speakers": [{"line": 1, "offset": 0, "label": speakers[n]}],
            }
            for n in range(1202, 1214)
        ],
    }
    turns = [(1202, "Cassandra"), (1204, "Chorus"), (1203, "Cassandra")]
    turns.extend((n, speakers[n]) for n in range(1205, 1214))
    body = "".join(
        f'<sp><speaker>{speaker}</speaker><l n="{n}">{speaker} {n}.</l></sp>'
        for n, speaker in turns
    )
    tei = (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>'
        f'<div type="translation">{body}</div></body></text></TEI>'
    )
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Chorus": "Chorus", "Cassandra": "Cassandra"},
        sigla={"Chorus": "Chorus", "Cassandra": "Cassandra"},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert len(by_id) == 12
    for n in range(1203, 1214):
        assert by_id[f"1:{n}"]["turns"][0]["speaker"] == speakers[n]
    assert "Chorus 1204." in by_id["1:1203"]["text"]
    assert "Cassandra 1203." in by_id["1:1204"]["text"]
    assert report["speech_mismatch_count"] == 2
    assert report["unresolved_mismatch_count"] == 0


def test_packed_elders_split_into_twelve_slices(tmp_path: Path):
    segments = []
    sigla = {}
    for i, start in enumerate(range(1348, 1372, 2), start=1):
        label = f"{i}."
        sigla[label] = f"Elder {i}"
        segments.append(
            {
                "id": f"1:{start}",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": start, "ref": str(start), "text": "g"},
                    {"n": start + 1, "ref": str(start + 1), "text": "g"},
                ],
                "speakers": [{"line": 1, "offset": 0, "label": label}],
            }
        )
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp>
      <milestone unit="para"/><l n="1348">—Advice 1.</l>
      <milestone unit="para"/><l n="1350">—Advice 2.
        <milestone unit="para"/>—Advice 3.
        <milestone unit="para"/>—Advice 4</l>
      <l n="1355">continues 4.
        <milestone unit="para"/>—Advice 5.
        <milestone unit="para"/>—Advice 6.</l>
      <milestone unit="para"/><l n="1360">—Advice 7.
        <milestone unit="para"/>—Advice 8.
        <milestone unit="para"/>—Advice 9</l>
      <l n="1365">continues 9.
        <milestone unit="para"/>—Advice 10.
        <milestone unit="para"/>—Advice 11.</l>
      <milestone unit="para"/><l n="1370">—Advice 12.</l>
    </sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path, tei, {"work": "test-play", "segments": segments}, sigla=sigla
    )
    ids = [chunk["id"] for chunk in english["chunks"]]
    assert ids == [f"1:{n}" for n in range(1348, 1372, 2)]
    texts = {chunk["id"]: chunk["text"] for chunk in english["chunks"]}
    assert "Advice 1" in texts["1:1348"]
    assert "Advice 3" in texts["1:1352"]
    assert "Advice 4" in texts["1:1354"] and "continues 4" in texts["1:1354"]
    assert "Advice 6" in texts["1:1358"]
    assert "Advice 12" in texts["1:1370"]
    assert report["segments_with_chunk"] == 12
    assert all("speakerMismatch" not in chunk for chunk in english["chunks"])


def test_cross_speech_snap_is_refused(tmp_path: Path):
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:430",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": n, "ref": str(n), "text": "g"} for n in range(430, 437)
                ],
                "speakers": [{"line": 1, "offset": 0, "label": "Χο."}],
            },
            {
                "id": "1:438",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": n, "ref": str(n), "text": "g"} for n in range(438, 441)
                ],
                "speakers": [{"line": 1, "offset": 0, "label": "Κα."}],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Chorus</speaker><l n="435">Prior strophe.</l></sp>
    <sp><speaker>Chorus</speaker><l n="437">New strophe.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Chorus": "Chorus"},
        sigla={"Χο.": "Chorus", "Κα.": "Cassandra"},
    )
    by_id = {chunk["id"]: chunk["text"] for chunk in english["chunks"]}
    assert "Prior strophe." in by_id["1:430"]
    assert "New strophe." not in by_id.get("1:430", "")
    assert "New strophe." not in by_id.get("1:438", "")
    assert any(
        item["kind"] == "unmatched_anchor" and item["n_raw"] == "437"
        for item in report["anomalies"]
    )


def test_stage_and_gap_are_skipped_like_del(tmp_path: Path):
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker>
      <l n="1">Hello <stage>He descends by an inner stairway</stage> there
      <gap reason="lost"/>kept tail.</l>
    </sp>
  </div>
</body></text></TEI>
"""
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1, "ref": "1", "text": "g"}],
                "speakers": [{"line": 1, "offset": 0, "label": "A"}],
            }
        ],
    }
    english, _footnotes, _report = _parse(tmp_path, tei, spine)
    text = english["chunks"][0]["text"]
    assert "He descends" not in text
    assert "Hello" in text and "there" in text and "kept tail." in text


def test_hyphenated_note_labels_are_sanitised(tmp_path: Path):
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker>
      <l n="1">Text<note n="69-71" resp="Smyth">A range note.</note>.</l>
    </sp>
  </div>
</body></text></TEI>
"""
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1, "ref": "1", "text": "g"}],
                "speakers": [{"line": 1, "offset": 0, "label": "A"}],
            }
        ],
    }
    english, footnotes, _report = _parse(tmp_path, tei, spine)
    assert list(footnotes) == ["1.69_71"]
    assert "[^1.69_71]" in english["chunks"][0]["text"]
    assert "-" not in next(iter(footnotes))


def _play_manifest(gaps=None, *, source=None) -> Manifest:
    english = {
        "primary": {
            "id": "smyth",
            "name": "Smyth",
            "model": "perseus-play",
            "footnotes": True,
        }
    }
    if gaps is not None:
        english["gaps"] = gaps
    if source is not None:
        english["primary"]["source"] = str(source)
    return Manifest(
        {
            "work": {"id": "test-play", "title": "Test", "author": "aeschylus"},
            "citation": {"scheme": "play-line"},
            "books": [{"n": 1, "start": "1", "end": "12"}],
            "english": english,
            "proper_names": [],
        },
        Path("test-play.yaml"),
    )


def _alignment_for(spine: dict, english: dict) -> dict:
    eng_ids = {chunk["id"] for chunk in english["chunks"]}
    covered = english.get("english_covered_by") or {}
    pairs = []
    for seg in spine["segments"]:
        pair = {
            "segment": seg["id"],
            "english": seg["id"] if seg["id"] in eng_ids else None,
        }
        if pair["english"] is None and seg["id"] in covered:
            pair["englishCoveredBy"] = covered[seg["id"]]
        pairs.append(pair)
    return {
        "pairs": pairs,
        "english_only": [],
        "english_covered_by": covered,
    }


def _stichomythia_spine() -> dict:
    """Greek one-liners 1320..1325, a lacuna inside the span, a line outside it."""
    segments = []
    for n in range(1320, 1326):
        segments.append(
            {
                "id": f"1:{n}",
                "book": 1,
                "column": "1",
                "lines": [{"n": n, "ref": str(n), "text": f"g{n}"}],
                "speakers": [
                    {
                        "line": 1,
                        "offset": 0,
                        "label": "A" if n % 2 == 0 else "B",
                    }
                ],
            }
        )
        if n == 1322:
            segments.append(
                {
                    "id": "1:post 1322",
                    "book": 1,
                    "column": "1",
                    "lines": [
                        {
                            "n": 1322,
                            "ref": "post 1322",
                            "text": "",
                            "role": "lacuna",
                        }
                    ],
                    "speakers": [],
                }
            )
    segments.append(
        {
            "id": "1:1400",
            "book": 1,
            "column": "1",
            "lines": [{"n": 1400, "ref": "1400", "text": "outside"}],
            "speakers": [{"line": 1, "offset": 0, "label": "A"}],
        }
    )
    return {"work": "test-play", "segments": segments}


STICHOMYTHIA_TEI = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker>
      <l n="1320">First block.</l>
      <l n="1325">Later block.</l>
    </sp>
  </div>
</body></text></TEI>
"""


def test_stichomythia_continuation_coverage(tmp_path: Path):
    spine = _stichomythia_spine()
    english, _footnotes, report = _parse(tmp_path, STICHOMYTHIA_TEI, spine)
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert set(by_id) == {"1:1320", "1:1325"}
    assert "First block." in by_id["1:1320"]["text"]
    assert "Later block." in by_id["1:1325"]["text"]
    # P2g finding 4: coverage never crosses speakers. 1321/1323 are the OTHER
    # speaker's one-liners inside Alpha's block: they are real holes, not
    # covered columns, and must be declared like any other gap.
    covered = english["english_covered_by"]
    assert covered == {"1:1322": "1:1320", "1:1324": "1:1320"}
    assert report["covered_by_count"] == 2

    alignment = _alignment_for(spine, english)
    result = validate(
        _play_manifest(gaps=["1:1321", "1:1323"]), spine, english, alignment
    )
    align = result["checks"]["alignment"]
    unexpected = align["unexpected_unmatched"]
    assert "1:1322" not in unexpected
    assert "1:1324" not in unexpected
    assert "1:post 1322" not in unexpected
    assert "1:1400" in unexpected
    # Coverage is an ALLOWANCE, reported, not a silent removal.
    assert align["covered_ids"] == ["1:1322", "1:1324"]
    assert "1:1322" in align["unmatched_segments"]
    assert "1:1322" in align["allowed_unmatched"]

    undeclared = validate(_play_manifest(gaps=[]), spine, english, alignment)
    assert "1:1321" in undeclared["checks"]["alignment"]["unexpected_unmatched"]
    assert "1:1323" in undeclared["checks"]["alignment"]["unexpected_unmatched"]

    tokens = {
        "segments": [
            {
                "id": seg["id"],
                "lines": [{"n": line["n"], "tokens": []} for line in seg["lines"]],
            }
            for seg in spine["segments"]
        ]
    }
    out_dir = tmp_path / "dist"
    out_dir.mkdir()
    emit_books(spine, tokens, english, chapter_ranges(spine, []), out_dir)
    book = json.loads((out_dir / "book-01.json").read_text(encoding="utf-8"))
    emitted = {seg["id"]: seg for seg in book["segments"]}
    assert emitted["1:1320"]["english"]["text"] == "First block."
    assert "englishCoveredBy" not in emitted["1:1320"]
    assert emitted["1:1321"]["english"] is None
    assert "englishCoveredBy" not in emitted["1:1321"]
    assert emitted["1:1322"]["englishCoveredBy"] == "1:1320"
    assert emitted["1:1324"]["englishCoveredBy"] == "1:1320"
    assert emitted["1:1325"]["english"]["text"] == "Later block."
    assert "englishCoveredBy" not in emitted["1:1325"]
    assert "englishCoveredBy" not in emitted["1:1400"]
    assert emitted["1:1400"]["english"] is None
    assert "englishCoveredBy" not in emitted["1:post 1322"]


def test_single_anchor_covers_until_next_english_owner(tmp_path: Path):
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": f"1:{n}",
                "book": 1,
                "column": "1",
                "lines": [{"n": n, "ref": str(n), "text": f"g{n}"}],
                "speakers": [{"line": 1, "offset": 0, "label": "A"}],
            }
            for n in range(10, 16)
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker><l n="10">Opens the block.</l></sp>
    <sp><speaker>Alpha</speaker><l n="15">Closes the block.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(tmp_path, tei, spine)
    assert {chunk["id"] for chunk in english["chunks"]} == {"1:10", "1:15"}
    covered = english["english_covered_by"]
    assert covered == {
        "1:11": "1:10",
        "1:12": "1:10",
        "1:13": "1:10",
        "1:14": "1:10",
    }
    assert report["covered_by_count"] == 4


def test_english_gaps_are_the_only_allowed_unmatched_play_line_ids(tmp_path: Path):
    spine = _spine()
    english = {
        "chunks": [
            {"id": "1:1", "column": "1", "text": "Alpha text here for length."},
            {"id": "1:5", "column": "1", "text": "Beta text here for length."},
        ]
    }
    alignment = _alignment_for(spine, english)
    denied = validate(_play_manifest(gaps=[]), spine, english, alignment)
    assert "1:10" in denied["checks"]["alignment"]["unexpected_unmatched"]
    assert denied["checks"]["alignment"]["ok"] is False

    allowed = validate(_play_manifest(gaps=["1:10"]), spine, english, alignment)
    assert allowed["checks"]["alignment"]["unexpected_unmatched"] == []
    assert allowed["checks"]["alignment"]["ok"] is True

    by_ref = validate(_play_manifest(gaps=["10"]), spine, english, alignment)
    assert by_ref["checks"]["alignment"]["ok"] is True


def test_twin_segments_need_no_declared_gap_when_lettered_source_is_empty(tmp_path):
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1, "ref": "1", "text": "g"}],
            },
            {
                "id": "1:803",
                "book": 1,
                "column": "1",
                "lines": [{"n": 2, "ref": "803", "text": "first"}],
            },
            {
                "id": "1:803.2",
                "book": 1,
                "column": "1",
                "lines": [{"n": 3, "ref": "803", "text": "second"}],
            },
            {
                "id": "1:843a",
                "book": 1,
                "column": "1",
                "lines": [{"n": 4, "ref": "843a", "text": "a"}],
            },
            {
                "id": "1:843b",
                "book": 1,
                "column": "1",
                "lines": [{"n": 5, "ref": "843b", "text": "b"}],
            },
            {
                "id": "1:47a",
                "book": 1,
                "column": "1",
                "lines": [{"n": 6, "ref": "47a", "text": "unique"}],
            },
        ],
    }
    english = {
        "chunks": [
            {"id": "1:1", "column": "1", "text": "Alpha text here for length."},
            {"id": "1:803", "column": "1", "text": "First 803 text here for length."},
            {"id": "1:843a", "column": "1", "text": "Lettered a text here for length."},
        ]
    }
    alignment = _alignment_for(spine, english)
    source = tmp_path / "twins.xml"
    source.write_text(
        """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation"><sp><l n="843a">Translated a.</l></sp></div>
</body></text></TEI>
""",
        encoding="utf-8",
    )
    report = validate(
        _play_manifest(gaps=[], source=source), spine, english, alignment
    )
    unexpected = report["checks"]["alignment"]["unexpected_unmatched"]
    assert "1:803.2" not in unexpected
    assert "1:843b" not in unexpected
    assert "1:47a" in unexpected
    assert report["checks"]["alignment"]["ok"] is False


def test_translated_lettered_twin_is_not_auto_allowed(tmp_path):
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1270",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1, "ref": "1270", "text": "base"}],
            },
            {
                "id": "1:1270a",
                "book": 1,
                "column": "1",
                "lines": [{"n": 2, "ref": "1270a", "text": "lettered"}],
            },
        ],
    }
    english = {
        "chunks": [
            {"id": "1:1270", "column": "1", "text": "Base translation."}
        ]
    }
    source = tmp_path / "medea.xml"
    source.write_text(
        """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation"><sp><l n="1270a">Ah!</l></sp></div>
</body></text></TEI>
""",
        encoding="utf-8",
    )
    report = validate(
        _play_manifest(gaps=[], source=source),
        spine,
        english,
        _alignment_for(spine, english),
    )
    assert report["checks"]["alignment"]["unexpected_unmatched"] == ["1:1270a"]


def test_unmapped_english_speaker_is_a_hard_roster_error():
    english = {
        "chunks": [
            {
                "id": "1:1",
                "turns": [
                    {"offset": 0, "speaker": "Clytaemnestra", "display": "Clytaemnestra"}
                ],
            }
        ]
    }
    with pytest.raises(RuntimeError, match="unmapped English speaker"):
        _play_line_english_roster_gate(
            "agamemnon",
            english,
            {"Chorus": "Chorus"},
            {"Clytaemestra", "Chorus"},
        )


def test_footnotes_flag_stays_off_the_v1_translation_entry(tmp_path, monkeypatch):
    """manifest.v1's translation entry forbids extra keys; the flag used to be
    copied here (P2b) and failed the contract validator on 18 works at the
    first full build:public (2026-09-08). The fact rides in
    `apparatus.footnotes`, keyed on the emitted footnotes.json."""
    out_dir = tmp_path / "dist" / "test-play"
    out_dir.mkdir(parents=True)
    monkeypatch.delenv("CORPUS_VERSION", raising=False)
    manifest = Manifest(
        {
            "work": {
                "id": "test-play",
                "title": "Test Play",
                "author": "aeschylus",
                "language": "grc",
                "tlg_author": "0085",
                "tlg_work": "005",
                "greek_edition": "Murray",
            },
            "citation": {"scheme": "play-line"},
            "books": [{"n": 1, "start": "1", "end": "10"}],
            "english": {
                "primary": {
                    "id": "smyth",
                    "name": "H. W. Smyth (Loeb, 1926)",
                    "model": "perseus-play",
                    "footnotes": True,
                }
            },
        },
        Path("test-play.yaml"),
    )
    fields = _manifest_v1_fields(manifest, out_dir)
    assert "footnotes" not in fields["translations"][0]
    assert fields["translations"][0]["id"] == "smyth"
    assert fields["apparatus"]["footnotes"] is False
    (out_dir / "footnotes.json").write_text("{}")
    assert _manifest_v1_fields(manifest, out_dir)["apparatus"]["footnotes"] is True


# ── P2g: speaker resolution, speaker sets, repair ticks, loss gate ──────────


def _resolver(sigla: dict, overrides: list[dict] | None = None):
    from drama_pipeline.stage1_turn_english import _SiglaResolver

    return _SiglaResolver(
        Manifest(
            {
                "work": {"id": "test-play"},
                "citation": {"scheme": "play-line"},
                "speakers": {"sigla": sigla, "overrides": overrides or []},
            },
            Path("test-play.yaml"),
        )
    )


def test_speaker_override_resolves_like_stage7(tmp_path: Path):
    """Helen's Θε. is a servant until 1165 and Theoclymenus from 1165 on
    (speakers.overrides). Resolving with the bare sigla map read every later
    line as the servant, scored a false mismatch and deleted the English."""
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1100",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1, "ref": "1100", "text": "g"}],
                "speakers": [{"line": 1, "offset": 0, "label": "Θε."}],
            },
            {
                "id": "1:1180",
                "book": 1,
                "column": "1",
                "lines": [{"n": 2, "ref": "1180", "text": "g"}],
                "speakers": [{"line": 2, "offset": 0, "label": "Θε."}],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Servant</speaker><l n="1100">The servant speaks.</l></sp>
    <sp><speaker>Theoclymenus</speaker><l n="1180">The king speaks.</l></sp>
  </div>
</body></text></TEI>
"""
    resolver = _resolver(
        {"Θε.": "Servant", "—": None},
        [{"siglum": "Θε.", "from": "1165", "display": "Theoclymenus"}],
    )
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Servant": "Servant", "Theoclymenus": "Theoclymenus"},
        sigla=resolver,
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert by_id["1:1180"]["text"] == "The king speaks."
    assert "speakerMismatch" not in by_id["1:1180"]
    assert report["speech_mismatch_count"] == 0
    assert "Theoclymenus" in report["speakers"]["greek_roster"]
    assert report["speakers"]["only_in_english"] == []


def test_packed_second_speaker_accepts_its_own_english(tmp_path: Path):
    """Seven 1:1004 packs Ismene (1004) and the Herald (1005): the Herald's
    English must attach there without a mismatch. The first-speaker rule made
    it a mismatch the repair search could never target."""
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1004",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": 1004, "ref": "1004", "text": "g"},
                    {"n": 1005, "ref": "1005", "text": "g"},
                ],
                "speakers": [
                    {"line": 1004, "offset": 0, "label": "Ισ."},
                    {"line": 1005, "offset": 0, "label": "Κη."},
                ],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Herald</speaker><l n="1005">The city has decreed.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Herald": "Herald", "Ismene": "Ismene"},
        sigla={"Ισ.": "Ismene", "Κη.": "Herald", "—": None},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert by_id["1:1004"]["text"] == "The city has decreed."
    assert "speakerMismatch" not in by_id["1:1004"]
    assert report["speech_mismatch_count"] == 0
    assert report["attribution_difference_count"] == 0


def test_repair_tick_names_a_line_the_target_segment_prints(tmp_path: Path):
    """A repaired attachment must tick one of the TARGET's own lines, not the
    English n of the neighbour that printed it (P2g finding 10)."""
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1000",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": 1000, "ref": "1000", "text": "g"},
                    {"n": 1001, "ref": "1001", "text": "g"},
                ],
                "speakers": [{"line": 1000, "offset": 0, "label": "A"}],
            },
            {
                "id": "1:1002",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1002, "ref": "1002", "text": "g"}],
                "speakers": [{"line": 1002, "offset": 0, "label": "B"}],
            },
            {
                "id": "1:1003",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1003, "ref": "1003", "text": "g"}],
                "speakers": [{"line": 1003, "offset": 0, "label": "G"}],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker><l n="1003">Alpha's own line.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(tmp_path, tei, spine)
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert set(by_id) == {"1:1000"}
    ticks = [mark["n"] for mark in by_id["1:1000"]["bekker"]]
    assert ticks == [1001]
    mismatch = report["speech_mismatches"][0]
    assert mismatch["kind"] == "speaker_repair"
    assert mismatch["attached_to"] == "1:1000"
    assert mismatch["attached_ref"] == "1001"


def _write_english_report(monkeypatch, tmp_path: Path, data: dict) -> None:
    from drama_pipeline import stage2_validate as s2

    stage1 = tmp_path / "stage1"
    stage1.mkdir(exist_ok=True)
    (stage1 / "english_report.json").write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(s2, "BUILD_DIR", tmp_path)


def test_attachment_loss_is_gated(tmp_path: Path, monkeypatch):
    """Unattached English is deleted translation: it must fail the build
    unless the manifest declares an allowance (P2g finding 3)."""
    spine = _spine()
    english = {
        "chunks": [
            {"id": "1:1", "column": "1", "text": "Alpha text here for length."},
            {"id": "1:5", "column": "1", "text": "Beta text here for length."},
            {"id": "1:10", "column": "1", "text": "Gamma text here for length."},
        ]
    }
    alignment = _alignment_for(spine, english)

    _write_english_report(
        monkeypatch,
        tmp_path,
        {"work": "test-play", "unresolved_mismatch_count": 0},
    )
    clean = validate(_play_manifest(gaps=[]), spine, english, alignment)
    assert clean["checks"]["attachment_loss"]["ok"] is True
    assert clean["checks"]["attachment_loss"]["unresolved"] == 0

    _write_english_report(
        monkeypatch,
        tmp_path,
        {
            "work": "test-play",
            "unresolved_mismatch_count": 3,
            "speech_mismatch_count": 9,
            "attribution_difference_count": 2,
        },
    )
    lossy = validate(_play_manifest(gaps=[]), spine, english, alignment)
    check = lossy["checks"]["attachment_loss"]
    assert check["ok"] is False
    assert "3 English piece(s) attached to no Greek speech" in check["error"]
    assert lossy["ok"] is False

    manifest = _play_manifest(gaps=[])
    manifest.data["english"]["max_unresolved_mismatches"] = 3
    allowed = validate(manifest, spine, english, alignment)
    assert allowed["checks"]["attachment_loss"]["ok"] is True


def test_attachment_loss_fails_closed_without_this_works_report(
    tmp_path: Path, monkeypatch
):
    spine = _spine()
    english = {"chunks": [{"id": "1:1", "column": "1", "text": "Alpha text."}]}
    alignment = _alignment_for(spine, english)
    from drama_pipeline import stage2_validate as s2

    monkeypatch.setattr(s2, "BUILD_DIR", tmp_path)
    missing = validate(_play_manifest(gaps=["1:5", "1:10"]), spine, english, alignment)
    assert missing["checks"]["attachment_loss"]["ok"] is False
    assert "no stage1 English report" in missing["checks"]["attachment_loss"]["error"]

    _write_english_report(
        monkeypatch, tmp_path, {"work": "frogs", "unresolved_mismatch_count": 0}
    )
    foreign = validate(_play_manifest(gaps=["1:5", "1:10"]), spine, english, alignment)
    assert foreign["checks"]["attachment_loss"]["ok"] is False
    assert "not 'test-play'" in foreign["checks"]["attachment_loss"]["error"]


def test_helen_override_is_live_in_the_english_builder():
    """The real manifest, resolved the way _SpeechIndex now resolves it."""
    from drama_pipeline.stage1_perseus_play_english import _SpeechIndex

    manifest = Manifest.for_work("helen")
    spine = {
        "work": "helen",
        "segments": [
            {
                "id": "1:700",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1, "ref": "700", "text": "g"}],
                "speakers": [{"line": 1, "offset": 0, "label": "Θε."}],
            },
            {
                "id": "1:1200",
                "book": 1,
                "column": "1",
                "lines": [{"n": 2, "ref": "1200", "text": "g"}],
                "speakers": [{"line": 2, "offset": 0, "label": "Θε."}],
            },
        ],
    }
    index = _SpeechIndex(spine, _resolver_for(manifest))
    assert index.speakers_of["1:700"] == {"Servant"}
    assert index.speakers_of["1:1200"] == {"Theoclymenus"}


def _resolver_for(manifest: Manifest):
    from drama_pipeline.stage1_turn_english import _SiglaResolver

    return _SiglaResolver(manifest)


# ── P2h: every speaker decision is per printed LINE ─────────────────────────


def _seven_spine() -> dict:
    """Seven 1000–1026 as the TLG prints it.

    The Herald's label at 1005 sits after an editorial bracket, so its offset
    is 1, not 0: the spine cannot cut there and 1:1004 packs Ismene (1004) and
    the Herald (1005–1025) in one segment.
    """
    def stich(n: int, label: str) -> dict:
        return {
            "id": f"1:{n}",
            "book": 1,
            "column": str(n),
            "lines": [{"n": n, "ref": str(n), "text": "g"}],
            "speakers": [{"line": n, "offset": 0, "label": label}],
        }

    packed = {
        "id": "1:1004",
        "book": 1,
        "column": "1004",
        "lines": [{"n": n, "ref": str(n), "text": "g"} for n in range(1004, 1026)],
        "speakers": [
            {"line": 1004, "offset": 0, "label": "Ισ."},
            {"line": 1005, "offset": 1, "label": "ΚΗΡΥΞ"},
        ],
    }
    return {
        "work": "test-play",
        "segments": [
            {
                "id": "1:998",
                "book": 1,
                "column": "998",
                "lines": [
                    {"n": 998, "ref": "998", "text": "g"},
                    {"n": 999, "ref": "999", "text": "g"},
                ],
                "speakers": [{"line": 998, "offset": 0, "label": "Αν."}],
            },
            stich(1000, "Ισ."),
            stich(1001, "Αν."),
            stich(1002, "Ισ."),
            stich(1003, "Αν."),
            packed,
            stich(1026, "Αν."),
        ],
    }


SEVEN_SIGLA = {"Ισ.": "Ismene", "Αν.": "Antigone", "ΚΗΡΥΞ": "Herald", "—": None}
SEVEN_ALIASES = {
    "Ismene": "Ismene",
    "Antigone": "Antigone",
    "Herald": "Herald",
}
SEVEN_TEI = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Antigone</speaker><l n="998">A tale of destruction!</l></sp>
    <sp><speaker>Ismene</speaker><l n="999">Destruction to look upon!</l></sp>
    <sp><speaker>Antigone</speaker><l n="1000">Oh, the grief—</l></sp>
    <sp><speaker>Ismene</speaker><l n="1001">Oh, the evils—</l></sp>
    <sp><speaker>Antigone</speaker><l n="1002">For home and land.</l></sp>
    <sp><speaker>Ismene</speaker><l n="1003">Above all for me,</l></sp>
    <sp><speaker>Antigone</speaker><l n="1004">And more also for me.</l></sp>
    <sp><speaker>Ismene</speaker><l n="1005">Ah I pity your suffering, my king.</l></sp>
    <sp><speaker>Antigone</speaker><l n="1006">Pity for you both.</l></sp>
    <sp><speaker>Ismene</speaker><l n="1007">You were possessed by delusion.</l></sp>
    <sp><speaker>Antigone</speaker><l n="1008">Where shall we lay them?</l></sp>
    <sp><speaker>Ismene</speaker><l n="1009">Where their honor is greatest.</l></sp>
    <sp><speaker>Antigone</speaker><l n="1010">To lie beside their father.</l></sp>
    <sp><speaker>Herald</speaker>
      <l n="1011">It is my duty to announce the decrees.</l>
      <l n="1012">Eteocles they will bury.</l>
      <l n="1025">So the council of the Cadmeans decreed.</l>
    </sp>
    <sp><speaker>Antigone</speaker><l n="1026">But I say to the rulers.</l></sp>
  </div>
</body></text></TEI>
"""


def test_packed_antilabe_span_attaches_by_line_speaker(tmp_path: Path):
    """Seven 998–1026 (P2h findings 2, 6, 8 + the P2i ruling).

    Smyth's speakers run one line ahead of the TLG's, so every piece of this
    stichomythia is a drift repair until the claims run out.  The packed
    ``1:1004`` (Ismene 1004, the Herald 1005–1025) is never a repair TARGET:
    Ismene 1003 stays on the speech that prints 1003, flagged.  What the Greek
    prints on the Herald's lines attaches there, each turn flagged with the
    speaker of ITS printed line — attached and marked, never withheld.
    """
    english, _footnotes, report = _parse(
        tmp_path,
        SEVEN_TEI,
        _seven_spine(),
        aliases=SEVEN_ALIASES,
        sigla=SEVEN_SIGLA,
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    packed = by_id["1:1004"]

    # Everything Smyth numbers 1004–1025 is in the packed chunk, once.
    assert [turn["speaker"] for turn in packed["turns"]] == [
        "Antigone",
        "Ismene",
        "Antigone",
        "Ismene",
        "Antigone",
        "Ismene",
        "Antigone",
        "Herald",
    ]
    assert packed["text"].count("It is my duty") == 1
    assert "So the council of the Cadmeans decreed." in packed["text"]
    for words in ("And more also", "Ah I pity", "Pity for you both", "To lie beside"):
        assert words in packed["text"]
    # No English piece is attached twice.
    for words in ("Above all for me", "And more also", "You were possessed"):
        assert sum(chunk["text"].count(words) for chunk in english["chunks"]) == 1

    # P2i finding 1: Ismene 1003 stays on 1:1003 — the speech that prints her
    # line — instead of being dragged onto the Herald's 22-line block.
    assert "Above all for me" in by_id["1:1003"]["text"]
    assert "Above all for me" not in packed["text"]

    # P2i finding 2: no holes.  Every disagreement is an attached, flagged turn
    # naming the speaker of that printed line.
    assert not any(a["kind"] == "attribution_hole" for a in report["anomalies"])
    assert report["anomalies"] == []
    flagged = {
        (item["greek_id"], item["line"]): item["greek_speaker"]
        for item in report["attribution_differences"]
    }
    assert flagged == {
        ("1:1003", 1003): "Antigone",
        ("1:1004", 1004): "Ismene",
        ("1:1004", 1006): "Herald",
        ("1:1004", 1007): "Herald",
        ("1:1004", 1008): "Herald",
        ("1:1004", 1009): "Herald",
        ("1:1004", 1010): "Herald",
    }
    assert report["attribution_difference_count"] == 7
    assert all(
        item["english_speaker"] in {"Antigone", "Ismene"}
        for item in report["attribution_differences"]
    )

    # The flag rides the TURN, and only the turns that disagree.
    marked = {
        turn["speaker"]: turn["speakerMismatch"]
        for chunk in english["chunks"]
        for turn in chunk["turns"]
        if "speakerMismatch" in turn
    }
    assert marked["Antigone"] == {"english": "Antigone", "greek": "Herald"}
    assert [turn.get("speakerMismatch") for turn in packed["turns"]][-1] is None
    assert "speakerMismatch" not in packed  # not every turn of the chunk
    assert all(
        "/" not in (row.get("greek_speaker") or "")
        for row in report["speech_mismatches"]
    )

    rows = {row["english_line"]: row for row in report["speech_mismatches"]}
    # The Herald's own lines are a clean match: no mismatch row at all.
    assert not any(row["english_speaker"] == "Herald" for row in rows.values())
    assert 1005 not in rows  # Ismene still owns the start of the antilabe line
    assert rows[1003]["kind"] == "attribution_difference"
    assert rows[1003]["attached_to"] == "1:1003"
    for line in (1007, 1009):
        assert rows[line]["kind"] == "attribution_difference"
        assert rows[line]["attached_to"] == "1:1004"
        assert rows[line]["attached_speaker"] == "Herald"
    # Drift repair still works where the speaker has a speech of her own:
    # Ismene 999 moves to 1:1000, Antigone 1002 to 1:1003.
    assert rows[999]["kind"] == "speaker_repair"
    assert rows[999]["attached_to"] == "1:1000"
    assert rows[1002]["kind"] == "speaker_repair"
    assert rows[1002]["attached_to"] == "1:1003"


def test_multi_span_speech_flags_the_piece_it_leaves_in_another_speech(
    tmp_path: Path,
):
    """P2j finding 1: Seven's Herald speech spans 1011-1030, and its last
    anchor falls inside Antigone's 1:1026.  That piece attaches there — it is
    the Greek it translates — and the TURN says the editions disagree.  Before
    the fix a multi-span speech skipped the flag entirely and the reader saw
    an unmarked Herald turn on Antigone's lines."""
    spine = _seven_spine()
    tail = spine["segments"][-1]
    assert tail["id"] == "1:1026"
    # Antigone speaks 1026-1030 in the Greek; Smyth's Herald runs to 1030.
    tail["lines"] = [
        {"n": n, "ref": str(n), "text": "g"} for n in range(1026, 1031)
    ]
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Herald</speaker>
      <l n="1011">It is my duty to announce the decrees.</l>
      <l n="1030">And this is the will of the Cadmeans.</l>
    </sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path, tei, spine, aliases=SEVEN_ALIASES, sigla=SEVEN_SIGLA
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    # The Herald's own half is clean; the piece on Antigone's speech is not.
    assert "It is my duty" in by_id["1:1004"]["text"]
    assert all("speakerMismatch" not in turn for turn in by_id["1:1004"]["turns"])
    assert "will of the Cadmeans" in by_id["1:1026"]["text"]
    assert by_id["1:1026"]["turns"][0]["speakerMismatch"] == {
        "english": "Herald",
        "greek": "Antigone",
    }
    assert report["attribution_differences"] == [
        {
            "greek_id": "1:1026",
            "line": 1030,
            "english_speaker": "Herald",
            "greek_speaker": "Antigone",
        }
    ]
    row = next(r for r in report["speech_mismatches"] if r["english_line"] == 1030)
    assert row["kind"] == "attribution_difference"
    assert row["attached_to"] == "1:1026"
    assert row["attached_speaker"] == "Antigone"
    assert report["anomalies"] == []


def test_repair_prefers_the_speakers_own_one_liner_over_a_packed_span(
    tmp_path: Path,
):
    """P2i finding 1: distance is measured against the speaker's OWN printed
    lines, and a one-liner beats a packed span at equal distance."""
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:10",
                "book": 1,
                "column": "10",
                "lines": [{"n": 10, "ref": "10", "text": "g"}],
                "speakers": [{"line": 10, "offset": 0, "label": "Αν."}],
            },
            {
                "id": "1:11",
                "book": 1,
                "column": "11",
                "lines": [{"n": 11, "ref": "11", "text": "g"}],
                "speakers": [{"line": 11, "offset": 0, "label": "Ισ."}],
            },
            {
                "id": "1:12",
                "book": 1,
                "column": "12",
                "lines": [{"n": n, "ref": str(n), "text": "g"} for n in range(12, 20)],
                "speakers": [
                    {"line": 12, "offset": 0, "label": "Ισ."},
                    {"line": 13, "offset": 1, "label": "ΚΗΡΥΞ"},
                ],
            },
        ],
    }
    from drama_pipeline.stage1_perseus_play_english import _SpeechIndex

    index = _SpeechIndex(spine, SEVEN_SIGLA)
    # 1:11 and 1:12 are both one line from 10; the one-liner wins.
    assert index.nearest_matching_speech(10, "Ismene") == (spine["segments"][1], 11)
    # With the one-liner claimed, the packed span is still not a target.
    assert index.nearest_matching_speech(10, "Ismene", claimed={("1:11", "Ismene")}) is None


def test_attribution_hole_is_counted_as_attachment_loss(tmp_path: Path, monkeypatch):
    """A hole is dropped translation: stage2 must fail on it (P2h finding 5)."""
    spine = _spine()
    english = {"chunks": [{"id": "1:1", "column": "1", "text": "Alpha text."}]}
    alignment = _alignment_for(spine, english)
    report = {
        "work": "test-play",
        "unresolved_mismatch_count": 0,
        "anomalies": [
            {"kind": "attribution_hole", "greek_id": "1:5", "line": 6, "english_speaker": "Beta"},
            {"kind": "unmatched_anchor", "sp": 3, "n_raw": "9"},
            {"kind": "nless_slice_unattached", "sp": 4},
            {"kind": "note_skipped_non_smyth", "resp": "Ed."},
        ],
    }
    _write_english_report(monkeypatch, tmp_path, report)
    result = validate(_play_manifest(gaps=["1:5", "1:10"]), spine, english, alignment)
    check = result["checks"]["attachment_loss"]
    assert check["ok"] is False
    assert check["unresolved"] == 3
    assert check["dropped"] == {
        "unmatched_anchor": 1,
        "nless_slice_unattached": 1,
        "attribution_hole": 1,
    }
    assert "3 English piece(s) attached to no Greek speech" in check["error"]

    manifest = _play_manifest(gaps=["1:5", "1:10"])
    manifest.data["english"]["max_unresolved_mismatches"] = 3
    allowed = validate(manifest, spine, english, alignment)
    assert allowed["checks"]["attachment_loss"]["ok"] is True


def test_continuation_coverage_uses_the_english_speakers_name(tmp_path: Path):
    """Coverage is the English speech's own speaker, not the covering
    segment's whole set (P2h finding 7): a packed covering segment must not
    lend its second speaker's name to the segments in between."""
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:100",
                "book": 1,
                "column": "100",
                "lines": [{"n": n, "ref": str(n), "text": "g"} for n in (100, 101)],
                "speakers": [
                    {"line": 100, "offset": 0, "label": "Χο."},
                    {"line": 101, "offset": 4, "label": "Κη."},
                ],
            },
            {
                "id": "1:102",
                "book": 1,
                "column": "102",
                "lines": [{"n": 102, "ref": "102", "text": "g"}],
                "speakers": [{"line": 102, "offset": 0, "label": "Κη."}],
            },
            {
                "id": "1:103",
                "book": 1,
                "column": "103",
                "lines": [{"n": 103, "ref": "103", "text": "g"}],
                "speakers": [{"line": 103, "offset": 0, "label": "Χο."}],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Chorus</speaker><l n="100">Chorus first.</l><l n="103">Chorus again.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, _report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Chorus": "Chorus", "Herald": "Herald"},
        sigla={"Χο.": "Chorus", "Κη.": "Herald", "—": None},
    )
    # The Herald's 1:102 is not the Chorus's continuation, though the covering
    # segment packs a Herald event of its own.
    assert english["english_covered_by"] == {}


def test_stage7_reads_spine_line_refs_for_speaker_overrides():
    """stage7 built its ref map from `greek`, a key the spine only grows later
    in the emit, so `speakers.overrides` never fired there: Helen's Θε. read
    as the Servant in the Greek column while the English said Theoclymenus
    (P2h finding 1)."""
    from drama_pipeline import stage7_emit

    manifest = Manifest.for_work("helen")
    spine = {
        "work": "helen",
        "segments": [
            {
                "id": "1:998",
                "book": 1,
                "column": "998",
                "lines": [{"n": 1, "ref": "998", "text": "g"}],
                "speakers": [{"line": 1, "offset": 0, "label": "Θε."}],
            },
            {
                "id": "1:1195",
                "book": 1,
                "column": "1195",
                "lines": [{"n": 2, "ref": "1195", "text": "g"}],
                "speakers": [{"line": 2, "offset": 0, "label": "Θε."}],
            },
        ],
    }
    rosters = stage7_emit._canonicalize_play_line_speakers(spine, manifest)
    displays = [
        event["display"]
        for segment in spine["segments"]
        for event in segment["speakers"]
    ]
    assert displays == ["Theonoe", "Theoclymenus"]
    assert "Theoclymenus" in rosters[1]


# ── P2i: shares of a line, continuation coverage, the nless-snap label ──────


# P2j finding 6: the lettered-share test runs on the REAL Helen tables --
# the manifest's own sigla (`Θε.` -> Servant, re-assigned to Theoclymenus from
# 1165 by `speakers.overrides`; `Θε.β` -> Second Servant) and its English
# aliases.  The P2i fixture invented an alias map, so it never showed what the
# build actually does with Coleridge's `Servant` at 1627-1640.
HELEN_MANIFEST = Manifest.for_work("helen")
HELEN_SIGLA = _SiglaResolver(HELEN_MANIFEST)
HELEN_ALIASES = (HELEN_MANIFEST.data.get("speakers") or {}).get("english") or {}
HELEN_TEI = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Theoklymenos</speaker>
      <l n="1630" part="I">Will you rule over your master?</l></sp>
    <sp><speaker>Servant</speaker>
      <l n="1630b" part="F">Yes, for I am in my right mind.</l></sp>
    <sp><speaker>Chorus</speaker>
      <l n="1631b" part="F">A stranger's word.</l></sp>
  </div>
</body></text></TEI>
"""


def _helen_antilabe_spine() -> dict:
    """Two Helen antilabe lines: Theoclymenus at offset 0, the Second Servant
    from mid-line (Diggle's ``Θε.β``)."""
    def antilabe(n: int) -> dict:
        return {
            "id": f"1:{n}",
            "book": 1,
            "column": str(n),
            "lines": [{"n": n, "ref": str(n), "text": "g"}],
            "speakers": [
                {"line": n, "offset": 0, "label": "Θε."},
                {"line": n, "offset": 20, "label": "Θε.β"},
            ],
        }

    return {"work": "test-play", "segments": [antilabe(1630), antilabe(1631)]}


def test_lettered_anchor_matches_the_mid_line_share(tmp_path: Path):
    """P2i finding 3 on the real Helen tables: ``1630b`` is the SECOND share
    of 1630, so it reads against ``Θε.β`` (the Second Servant) and not against
    the line-start ``Θε.``, which the manifest's override makes Theoclymenus
    from 1165 on.

    P2j finding 6/2: with the manifest's own aliases Coleridge's printed
    ``Servant`` canonicalises to ``Servant``, so the share is attached and
    FLAGGED as a name difference (Servant vs Second Servant) -- 13 turns at
    1627-1640 in the real build.  It is not a misattachment: the English is
    beside the Greek it translates.  Whether Helen's servant/messenger names
    should be reconciled at all is John's call (35 of the play's 39 flags are
    this same crossing), so the test states what the build does today."""
    english, _footnotes, report = _parse(
        tmp_path,
        HELEN_TEI,
        _helen_antilabe_spine(),
        aliases=HELEN_ALIASES,
        sigla=HELEN_SIGLA,
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    # Both shares of 1630 land on 1:1630 -- the letter picked the right share.
    assert "Will you rule" in by_id["1:1630"]["text"]
    assert "in my right mind" in by_id["1:1630"]["text"]
    turns = {turn["display"]: turn for turn in by_id["1:1630"]["turns"]}
    assert "speakerMismatch" not in turns["Theoklymenos"]
    assert turns["Servant"]["speakerMismatch"] == {
        "english": "Servant",
        "greek": "Second Servant",
    }
    # The Chorus owns no share of 1631: attached to the printing speech and
    # flagged with the speaker of the share the letter names.
    assert "A stranger's word." in by_id["1:1631"]["text"]
    assert report["attribution_differences"] == [
        {
            "greek_id": "1:1630",
            "line": 1630,
            "english_speaker": "Servant",
            "greek_speaker": "Second Servant",
        },
        {
            "greek_id": "1:1631",
            "line": 1631,
            "english_speaker": "Chorus",
            "greek_speaker": "Second Servant",
        },
    ]
    assert report["anomalies"] == []


def test_line_shares_reads_an_a_b_a_line(tmp_path: Path):
    """P2i finding 7: a three-event line has three shares, and a lettered
    anchor names the LAST same-name share, not the first."""
    from drama_pipeline.stage1_perseus_play_english import _SpeechIndex
    from drama_pipeline.stage1_turn_english import speaker_at

    segment = {
        "id": "1:500",
        "book": 1,
        "column": "500",
        "lines": [{"n": 500, "ref": "500", "text": "g"}],
        "speakers": [
            {"line": 500, "offset": 0, "label": "Αν."},
            {"line": 500, "offset": 20, "label": "Ισ."},
            {"line": 500, "offset": 40, "label": "Αν."},
        ],
    }
    index = _SpeechIndex({"work": "t", "segments": [segment]}, SEVEN_SIGLA)
    assert index.line_shares(segment, 500) == ["Antigone", "Ismene", "Antigone"]
    # `500c` is the third share — Antigone again, after Ismene's interruption:
    # a speaker who owns any share of the line reads clean either way.
    assert index.share_speaker(segment, 500, "500c", prefer="Antigone") == "Antigone"
    assert index.share_speaker(segment, 500, "500b", prefer="Antigone") == "Antigone"
    # A speaker with no share of the line disagrees with the share the letter
    # names, not with the line-start speaker.
    assert index.share_speaker(segment, 500, "500b", prefer="Herald") == "Ismene"
    assert index.share_speaker(segment, 500, "500c", prefer="Herald") == "Antigone"
    assert index.share_speaker(segment, 500, "500", prefer="Herald") == "Antigone"
    # The plain line rule still answers with the speaker's own share.
    assert speaker_at(segment, 500, SEVEN_SIGLA, prefer="Antigone") == "Antigone"
    assert speaker_at(segment, 500, SEVEN_SIGLA) == "Antigone"


def test_continuation_coverage_needs_every_printed_line(tmp_path: Path):
    """P2i finding 4: the covered side is per printed LINE.  A candidate whose
    later lines belong to the character the antilabe handed over to is a real
    hole, not a continuation of the English block."""
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:100",
                "book": 1,
                "column": "100",
                "lines": [{"n": n, "ref": str(n), "text": "g"} for n in (100, 101)],
                "speakers": [{"line": 100, "offset": 0, "label": "Αν."}],
            },
            {
                "id": "1:102",
                "book": 1,
                "column": "102",
                "lines": [
                    {"n": n, "ref": str(n), "text": "g"} for n in (102, 103, 104)
                ],
                "speakers": [
                    {"line": 102, "offset": 0, "label": "Αν."},
                    {"line": 103, "offset": 4, "label": "ΚΗΡΥΞ"},
                ],
            },
            {
                "id": "1:105",
                "book": 1,
                "column": "105",
                "lines": [{"n": 105, "ref": "105", "text": "g"}],
                "speakers": [{"line": 105, "offset": 0, "label": "Αν."}],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Antigone</speaker>
      <l n="100">A long block of Antigone.</l>
      <l n="105">Still Antigone, five lines later.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, _report = _parse(
        tmp_path, tei, spine, aliases=SEVEN_ALIASES, sigla=SEVEN_SIGLA
    )
    assert english["english_covered_by"] == {}

    # Without the handover the same shape is covered as before.
    spine["segments"][1]["speakers"] = [{"line": 102, "offset": 0, "label": "Αν."}]
    english, _footnotes, _report = _parse(
        tmp_path, tei, spine, aliases=SEVEN_ALIASES, sigla=SEVEN_SIGLA
    )
    assert english["english_covered_by"] == {"1:102": "1:100"}


def test_nless_snap_reports_the_speaker_of_the_tick_line(tmp_path: Path):
    """P2i finding 6: the snap row names the speaker of the line it ticked,
    never the segment's joined speaker set."""
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1, "ref": "1", "text": "g"}],
                "speakers": [{"line": 1, "offset": 0, "label": "Αν."}],
            },
            {
                "id": "1:2",
                "book": 1,
                "column": "2",
                "lines": [{"n": n, "ref": str(n), "text": "g"} for n in (2, 3)],
                "speakers": [
                    {"line": 2, "offset": 0, "label": "Ισ."},
                    {"line": 3, "offset": 3, "label": "ΚΗΡΥΞ"},
                ],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><l n="1">The first line.<milestone unit="para"/>A second paragraph.</l></sp>
  </div>
</body></text></TEI>
"""
    _english, _footnotes, report = _parse(
        tmp_path, tei, spine, aliases=SEVEN_ALIASES, sigla=SEVEN_SIGLA
    )
    snap = next(row for row in report["snaps"] if row.get("kind") == "nless_para")
    assert snap["segment"] == "1:2"
    assert snap["greek_speaker"] == "Ismene"
    assert "/" not in snap["greek_speaker"]
