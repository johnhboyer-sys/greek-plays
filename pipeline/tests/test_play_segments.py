import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

from drama_pipeline.stage1_greek import _segment_play_lines, _speech_start_lines_from_tei


def _flat(first: int, count: int) -> list[dict]:
    """One speaker's unbroken speech: the opening line carries the siglum."""
    out = [{"ref": str(first + k), "text": f"line {first + k}"} for k in range(count)]
    out[0]["speakers"] = [{"offset": 0, "label": "Χο."}]
    return out


def _starts(segments: list[dict]) -> list[str]:
    return [s["column"] for s in segments]


def test_a_long_speech_is_cut_where_the_english_opens_a_speech_block():
    # John, 2026-09-11 (Persians 83): cut at line 41's 40th-line cap, the new
    # segment's English only began at the translator's next marker.
    flat = _flat(41, 60)  # lines 41..100
    assert _starts(_segment_play_lines(flat)) == ["41", "81"]
    # With the English's speech-block starts known, the cut waits for one.
    assert _starts(_segment_play_lines(flat, {41, 87})) == ["41", "87"]


def test_the_cut_falls_at_the_ceiling_when_the_english_opens_no_block():
    flat = _flat(1, 100)
    assert _starts(_segment_play_lines(flat, {1})) == ["1", "81"]


def test_past_the_ceiling_the_cut_waits_for_a_line_the_english_marks():
    # Bacchae 677-756: a messenger speech Coleridge never breaks; the 80-line
    # ceiling fell on 757 while his next marker was 760.
    flat = _flat(677, 120)  # lines 677..796
    assert _starts(_segment_play_lines(flat, {677}, {677, 760, 765})) == ["677", "760"]
    # No marked line in reach: the hard stop at 100 lines.
    assert _starts(_segment_play_lines(flat, {677}, {677})) == ["677", "777"]


def test_a_speaker_change_still_cuts_at_once():
    flat = _flat(1, 10) + _flat(11, 10)
    assert _starts(_segment_play_lines(flat, {1})) == ["1", "11"]


def test_a_covered_speech_inside_its_covering_block_needs_no_mapping():
    # Alcestis 368 (covered by 328) was a 40-line-cap segment start; with the
    # cut moved to the English's own speech start it sits inside 328's block.
    import pytest
    from drama_pipeline.stage1_turn_english import _resolve_covered

    segs = [
        {"id": "1:328", "lines": [{"ref": str(n)} for n in range(328, 372)]},
        {"id": "1:372", "lines": [{"ref": str(n)} for n in range(372, 380)]},
    ]
    assert _resolve_covered([{"greek": "368", "by": "328"}], segs, "t") == {}
    assert _resolve_covered([{"greek": "372", "by": "328"}], segs, "t") == {"1:372": "1:328"}
    # Hippolytus 1253 by 1213: the cover's own opener moved; the block that
    # now holds 1213 covers.
    segs2 = [
        {"id": "1:1180", "lines": [{"ref": str(n)} for n in range(1180, 1253)]},
        {"id": "1:1253", "lines": [{"ref": str(n)} for n in range(1253, 1260)]},
    ]
    assert _resolve_covered([{"greek": "1253", "by": "1213"}], segs2, "t") == {"1:1253": "1:1180"}
    # Seven 367 by 327: the declared line now sits inside another segment,
    # which has English of its own; nothing to cover. A line the play lacks
    # is still a typo.
    assert _resolve_covered([{"greek": "375", "by": "328"}], segs, "t") == {}
    with pytest.raises(ValueError, match="no segment opens on line 999"):
        _resolve_covered([{"greek": "999", "by": "328"}], segs, "t")


def test_speech_block_starts_are_read_from_the_tei():
    tei = (
        '<div><sp><speaker>Chorus</speaker><l n="41">For all</l><l n="45">the men</l></sp>'
        '<milestone unit="card" n="81"/><sp><speaker>Chorus</speaker><l n="81">With eyes</l>'
        '<l n="85">he leads</l></sp><sp><l n="87a">And there</l></sp></div>'
    )
    assert _speech_start_lines_from_tei(tei) == {41, 81, 87}
