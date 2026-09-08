from pathlib import Path

import pytest
from lxml import etree

from drama_pipeline.config import Manifest
from drama_pipeline.stage1_perseus_play_english import parse_translation
from drama_pipeline.stage2_validate import validate
from drama_pipeline.stage7_emit import (
    _manifest_v1_fields,
    _play_line_english_roster_gate,
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


def _parse(tmp_path: Path, tei: str, spine: dict, *, aliases=None, sigla=None):
    xml_path = tmp_path / "play.xml"
    xml_path.write_text(tei, encoding="utf-8")
    return parse_translation(
        xml_path,
        spine,
        work_id="test-play",
        translation_id="smyth",
        sigla=sigla if sigla is not None else SIGLA,
        english_aliases=aliases if aliases is not None else ALIASES,
    )


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
    assert report["speech_mismatch_count"] == 1
    assert report["unresolved_mismatch_count"] == 0


def test_unresolved_speaker_mismatch_is_counted_and_not_attached(tmp_path: Path):
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:10",
                "book": 1,
                "column": "1",
                "lines": [{"n": 10, "ref": "10", "text": "g"}],
                "speakers": [{"line": 1, "offset": 0, "label": "B"}],
            }
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker><l n="10">Wrong owner.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(tmp_path, tei, spine)
    assert english["chunks"] == []
    assert report["speech_mismatch_count"] == 1
    assert report["unresolved_mismatch_count"] == 1
    assert "attached_to" not in report["speech_mismatches"][0]


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
    assert by_id["1:102"]["turns"] == [
        {"offset": 0, "speaker": "Chorus", "display": "Chorus"},
    ]
    assert report["segments_with_chunk"] == 2
    assert any(
        item.get("attached_to") == "1:102" and item["english_speaker"] == "Chorus"
        for item in report["speech_mismatches"]
    )


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
    return {
        "pairs": [
            {
                "segment": seg["id"],
                "english": seg["id"] if seg["id"] in eng_ids else None,
            }
            for seg in spine["segments"]
        ],
        "english_only": [],
    }


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


def test_footnotes_flag_is_copied_onto_v1_translation_entry(tmp_path, monkeypatch):
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
    assert fields["translations"][0]["footnotes"] is True
    assert fields["translations"][0]["id"] == "smyth"
