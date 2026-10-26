"""An English margin number keeps the letter of the Greek line it names.

Ticks carry an integer `n` (order, search and links use it). Beside a Greek
line the edition prints with a letter (Jebb's OC 519a, 519b) the integer
alone showed 519 three times; stage7 adds `label` ("519a") when the tick's
segment prints the lettered line and no plain line of that number."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

from drama_pipeline.stage7_emit import lettered_tick_labels


def _tick(n, offset=0):
    return {"n": n, "offset": offset, "real": True}


def test_oc_519a_519b_keep_their_letters():
    assert lettered_tick_labels([_tick(519)], ["519"]) == [_tick(519)]
    assert lettered_tick_labels([_tick(519)], ["519a"]) == [{**_tick(519), "label": "519a"}]
    assert lettered_tick_labels([_tick(519)], ["519b"]) == [{**_tick(519), "label": "519b"}]


def test_plain_line_in_the_segment_wins():
    assert lettered_tick_labels([_tick(519)], ["519", "519a", "519b"]) == [_tick(519)]


def test_two_lettered_lines_of_one_number_stay_unlabelled():
    assert lettered_tick_labels([_tick(519)], ["519a", "519b"]) == [_tick(519)]


def test_other_numbers_and_schemes_untouched():
    ticks = [_tick(520), _tick(521, 30)]
    assert lettered_tick_labels(ticks, ["519a", "520", "521-522"]) == ticks
    assert lettered_tick_labels(ticks, []) == ticks


def test_a_declared_label_is_kept():
    tick = {**_tick(1575), "label": "1575b"}
    assert lettered_tick_labels([tick], ["1575a", "1575b"]) == [tick]
