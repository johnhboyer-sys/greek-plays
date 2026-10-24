"""Drama token offsets locate the printed surface, with editorial marks.

Stage 7 uses these character offsets to split table cells. Stage 6 counts
tokens instead; it must not confuse character offsets with token positions.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

from drama_pipeline.stage3_tokenize import tokenize
from drama_pipeline.stage7_emit import _greek_cells


def _tokens(text):
    spine = {"work": "TST", "segments": [
        {"id": "1:1a", "book": 1, "column": "1a",
         "lines": [{"n": 1, "text": text}]}]}
    doc, _sigla, _fail = tokenize(spine)
    return doc["segments"][0]["lines"][0]["tokens"]


def test_o_locates_the_surface_with_editorial_marks():
    text = "καὶ †λόγος† ἐστι"
    toks = _tokens(text)
    assert [t["t"] for t in toks] == ["καὶ", "†λόγος†", "ἐστι"]
    assert toks[1]["k"] == "lo/gos"
    for t in toks:
        assert text[t["o"]:t["o"] + len(t["t"])] == t["t"]


def test_o_is_a_word_start_for_an_unadorned_token():
    text = "καὶ λόγος ἐστι"
    for t in _tokens(text):
        assert text[t["o"]:t["o"] + len(t["t"])] == t["t"]


def test_greek_cells_partitions_a_table_row_on_the_raw_offsets():
    """The ⎪ divider is both a cell boundary and stripped sigla, so the two
    conventions have to agree for a table row to split correctly."""
    text = "ἀληθές ⎪ ψεῦδος"
    toks = _tokens(text)
    cells = _greek_cells(text, toks)
    assert [c["text"] for c in cells] == ["ἀληθές", "ψεῦδος"]
    assert [[t["t"] for t in c["tokens"]] for c in cells] == [["ἀληθές"], ["ψεῦδος"]]
    # rebased offsets locate inside their own cell
    for c in cells:
        for t in c["tokens"]:
            assert c["text"][t["o"]:t["o"] + len(t["t"])] == t["t"]


def test_a_non_table_line_is_not_split():
    assert _greek_cells("καὶ λόγος", _tokens("καὶ λόγος")) is None
