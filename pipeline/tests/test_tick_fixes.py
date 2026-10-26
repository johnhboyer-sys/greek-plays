"""english.<slot>.tick_fixes: a declared correction to one English margin
number, judged by reading the English against the translator's Greek
(John, 2026-10-25/26: a number names the line its English translates; a
number off inside a sentence moves to where its line's English begins)."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

from drama_pipeline.tick_fixes import apply_tick_fixes

AG_122 = ("In time those who here issue forth shall seize Priam's town, and fate shall "
          "violently ravage the public store of cattle. Only may no jealous god-sent wrath")


def _english(text=AG_122, ticks=None):
    return {"chunks": [{"id": "1:122", "column": "122", "text": text,
                        "bekker": ticks or [{"n": 125, "offset": 0, "real": True},
                                            {"n": 130, "offset": text.index("Only"), "real": True}]}]}


def test_move_puts_the_number_on_its_lines_words():
    eng = _english()
    apply_tick_fixes(eng, [{"column": "122", "shown": 130, "at": "fate shall violently"}], "agamemnon")
    ticks = eng["chunks"][0]["bekker"]
    assert ticks[1] == {"n": 130, "offset": AG_122.index("fate shall"), "real": True}


def test_renumber_keeps_the_place():
    eng = _english()
    apply_tick_fixes(eng, [{"column": "122", "shown": 130, "n": 131}], "agamemnon")
    assert eng["chunks"][0]["bekker"][1] == {"n": 131, "offset": AG_122.index("Only"), "real": True}


def test_ticks_stay_in_text_order_after_a_move():
    eng = _english()
    apply_tick_fixes(eng, [{"column": "122", "shown": 125, "at": "god-sent"}], "agamemnon")
    assert [t["n"] for t in eng["chunks"][0]["bekker"]] == [130, 125]


def test_nth_picks_one_of_two_equal_numbers():
    text = "Nothing that is untrue. The man is alive?"
    eng = _english(text, [{"n": 1221, "offset": 0, "real": True},
                          {"n": 1221, "offset": text.index("The"), "real": True}])
    apply_tick_fixes(eng, [{"column": "122", "shown": 1221, "nth": 1, "n": 1220}], "electra-soph")
    assert [t["n"] for t in eng["chunks"][0]["bekker"]] == [1220, 1221]


@pytest.mark.parametrize("fix, message", [
    ({"column": "122", "shown": 135, "n": 136}, "matches no"),
    ({"column": "999", "shown": 130, "n": 131}, "no English"),
    ({"column": "122", "shown": 130, "at": "not in the text"}, "occurs 0"),
    ({"column": "122", "shown": 130, "at": "shall"}, "occurs 2"),
    ({"column": "122", "shown": 130}, "neither"),
])
def test_a_stale_or_loose_fix_fails(fix, message):
    with pytest.raises(ValueError, match=message):
        apply_tick_fixes(_english(), [fix], "agamemnon")
