from pathlib import Path

from drama_pipeline.stage1_perseus_play_english import parse_translation


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


def _spine() -> dict:
    return {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": n, "ref": str(n), "text": f"g{n}"}
                    for n in range(1, 6)
                ],
                "speakers": [{"line": 1, "offset": 0, "label": "A"}],
            },
            {
                "id": "1:10",
                "book": 1,
                "column": "10",
                "lines": [
                    {"n": n, "ref": str(n), "text": f"g{n}"}
                    for n in range(10, 13)
                ],
                "speakers": [
                    {"line": 10, "offset": 0, "label": "G"}
                ],
            },
        ],
    }


def test_perseus_play_chunks_ticks_notes_turns_and_report(tmp_path: Path):
    xml_path = tmp_path / "play.xml"
    xml_path.write_text(TEI, encoding="utf-8")
    english, footnotes, report = parse_translation(
        xml_path,
        _spine(),
        work_id="test-play",
        translation_id="smyth",
        sigla={"A": "Alpha", "G": "Gamma"},
    )

    assert [chunk["id"] for chunk in english["chunks"]] == ["1:1", "1:10"]
    first, second = english["chunks"]
    assert "cut me" not in first["text"]
    assert [tick["n"] for tick in first["bekker"]] == [1, 5, 5]
    assert [tick["n"] for tick in second["bekker"]] == [10]
    assert all(
        tick["real"] is True
        for chunk in english["chunks"]
        for tick in chunk["bekker"]
    )

    assert list(footnotes) == ["1.1", "2.1"]
    assert "<q>note</q>" in footnotes["1.1"]
    assert "[^1.1]" in first["text"] and "[^2.1]" in first["text"]

    beta_offset = first["text"].index("Second text.")
    assert first["turns"] == [
        {"offset": 0, "speaker": "Alpha", "display": "Alpha"},
        {"offset": beta_offset, "speaker": "Beta", "display": "Beta"},
    ]
    assert second["turns"] == [
        {"offset": 0, "speaker": "Gamma", "display": "Gamma"}
    ]

    assert report["anchor_count"] == 4
    assert report["snaps"] == [{"n_raw": 7, "snapped_to": "5", "segment": "1:1"}]
    assert report["segments_with_chunk"] == 2
    assert report["segments_total"] == 2
    assert report["coverage_ratio"] == 1.0
    assert report["speakers"]["only_in_english"] == ["Beta"]
