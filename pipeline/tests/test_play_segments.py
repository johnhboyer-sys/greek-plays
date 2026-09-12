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
    assert _starts(_segment_play_lines(flat, {"41", "87"})) == ["41", "87"]


def test_the_cut_falls_at_the_ceiling_when_the_english_opens_no_block():
    flat = _flat(1, 100)
    assert _starts(_segment_play_lines(flat, {"1"})) == ["1", "81"]


def test_past_the_ceiling_the_cut_waits_for_a_line_the_english_marks():
    # Bacchae 677-756: a messenger speech Coleridge never breaks; the 80-line
    # ceiling fell on 757 while his next marker was 760.
    flat = _flat(677, 120)  # lines 677..796
    assert _starts(_segment_play_lines(flat, {"677"}, {"677", "760", "765"})) == ["677", "760"]
    # No marked line in reach: the hard stop at 100 lines.
    assert _starts(_segment_play_lines(flat, {"677"}, {"677"})) == ["677", "777"]


def test_a_speaker_change_still_cuts_at_once():
    flat = _flat(1, 10) + _flat(11, 10)
    assert _starts(_segment_play_lines(flat, {"1"})) == ["1", "11"]


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


def test_a_long_speech_english_is_spread_over_its_continuation_segments():
    # Morshead's Agamemnon parodos: one speech, one chunk on 40-103; the
    # segments continuing the Greek speech (no speaker change) stood bare.
    from drama_pipeline.stage1_turn_english import _spread_long_speeches

    segs = [
        {"id": "1:40", "column": "40", "speakers": [{"line": 1}], "lines": [{}] * 10},
        {"id": "1:104", "column": "104", "lines": [{}] * 10},
        {"id": "1:258", "column": "258", "speakers": [{"line": 21}], "lines": [{}] * 2},
    ]
    chunk = {"id": "1:40", "column": "40", "text": "Ten years ago. The king went. Now the fire comes. It burns high.",
             "turns": [{"offset": 0, "speaker": "Chorus"}], "notes": [], "markers": []}
    other = {"id": "1:258", "column": "258", "text": "Herald speaks.", "turns": [], "notes": [], "markers": []}
    out = _spread_long_speeches([chunk, other], segs)
    assert [(c["id"], c["text"]) for c in out] == [
        ("1:40", "Ten years ago. The king went."),
        ("1:104", "Now the fire comes. It burns high."),
        ("1:258", "Herald speaks."),
    ]
    # The lead-in stays with the speech's first segment only.
    assert out[0]["turns"] == [{"offset": 0, "speaker": "Chorus"}] and out[1]["turns"] == []
    # A continuation that already has English of its own is left alone.
    own = {"id": "1:104", "column": "104", "text": "Its own.", "turns": [], "notes": [], "markers": []}
    assert [c["text"] for c in _spread_long_speeches([chunk, own], segs[:2])] == [chunk["text"], "Its own."]


def test_the_spread_keeps_other_chunks_in_place_and_leaves_noted_chunks_whole():
    # Grok review of b294d29: only a spread chunk is replaced by its pieces;
    # a chunk carrying offset-keyed notes or markers is not cut.
    from drama_pipeline.stage1_turn_english import _spread_long_speeches

    segs = [
        {"id": "1:40", "column": "40", "speakers": [{"line": 1}], "lines": [{}] * 10},
        {"id": "1:104", "column": "104", "lines": [{}] * 10},
        {"id": "1:258", "column": "258", "speakers": [{"line": 21}], "lines": [{}] * 2},
    ]
    text = "Ten years ago. The king went. Now the fire comes. It burns high."
    chunk = {"id": "1:40", "column": "40", "text": text, "turns": [], "notes": [], "markers": []}
    stray = {"id": "sd", "column": "0", "text": "[Exit].", "turns": [], "notes": [], "markers": []}
    other = {"id": "1:258", "column": "258", "text": "Herald speaks.", "turns": [], "notes": [], "markers": []}
    assert [c["id"] for c in _spread_long_speeches([other, stray, chunk], segs)] == ["1:258", "sd", "1:40", "1:104"]
    noted = {**chunk, "notes": [{"offset": 16, "text": "fn"}]}
    assert [c["id"] for c in _spread_long_speeches([noted], segs)] == ["1:40"]


def test_the_spread_crosses_unnamed_and_same_speaker_events():
    # Morshead's Agamemnon ode: the English speech of 351 runs to 502, but
    # the Greek marks strophes with unnamed "—" events (355, 501) and names
    # the Chorus again at 489; the spread stopped at 355 and 355-502 stood
    # bare (John, 2026-09-12).
    from drama_pipeline.stage1_turn_english import _spread_long_speeches

    sigla = {"Χο.": "Chorus", "ΚΗΡΥΞ": "Herald"}
    segs = [
        {"id": "1:351", "column": "351", "speakers": [{"line": 1, "label": "Χο."}], "lines": [{}]},
        {"id": "1:355", "column": "355", "speakers": [{"line": 2, "label": "—"}], "lines": [{}]},
        {"id": "1:420", "column": "420", "lines": [{}]},
        {"id": "1:489", "column": "489", "speakers": [{"line": 4, "label": "Χο."}], "lines": [{}]},
        {"id": "1:503", "column": "503", "speakers": [{"line": 5, "label": "ΚΗΡΥΞ"}], "lines": [{}]},
    ]
    chunk = {"id": "1:351", "column": "351", "text": "One aaaa. Two bbbb. Six cccc. Ten dddd.",
             "turns": [{"offset": 0, "speaker": "Chorus"}], "notes": [], "markers": []}
    herald = {"id": "1:503", "column": "503", "text": "Herald speaks.", "turns": [], "notes": [], "markers": []}
    out = _spread_long_speeches([chunk, herald], segs, sigla)
    assert [(c["id"], c["text"]) for c in out] == [
        ("1:351", "One aaaa."), ("1:355", "Two bbbb."), ("1:420", "Six cccc."),
        ("1:489", "Ten dddd."), ("1:503", "Herald speaks."),
    ]
    # A bare segment that names somebody else is not the speech going on.
    other = [segs[0], {**segs[1], "speakers": [{"line": 2, "label": "ΚΗΡΥΞ"}]}]
    assert [c["id"] for c in _spread_long_speeches([chunk], other, sigla)] == ["1:351"]
    # Nor is one that names the head's FIRST speaker after a mid-line change
    # (Wasps 416: Chorus, then Bdelycleon; 417 is the Chorus again).
    antilabe = [
        {**segs[0], "speakers": [{"line": 1, "label": "Χο."}, {"line": 1, "offset": 9, "label": "ΚΗΡΥΞ"}]},
        {**segs[1], "speakers": [{"line": 2, "label": "Χο."}]},
    ]
    assert [c["id"] for c in _spread_long_speeches([chunk], antilabe, sigla)] == ["1:351"]


def test_speech_block_starts_are_read_from_the_tei():
    tei = (
        '<div><sp><speaker>Chorus</speaker><l n="41">For all</l><l n="45">the men</l></sp>'
        '<milestone unit="card" n="81"/><sp><speaker>Chorus</speaker><l n="81">With eyes</l>'
        '<l n="85">he leads</l></sp><sp><l n="87a">And there</l></sp></div>'
    )
    assert _speech_start_lines_from_tei(tei) == {"41", "81", "87a"}


def test_grok_review_of_fa76916_edge_cases():
    # A speech quoted inside a messenger's speech neither supplies nor hides a start.
    tei = ('<text><sp><speaker>Mes.</speaker><l n="100">the report</l>'
           '<quote><sp><l n="112">he said</l></sp></quote><l n="120">more</l></sp>'
           '<sp><l n="160">next</l></sp></text>')
    assert _speech_start_lines_from_tei(tei) == {"100", "160"}
    # A joined or lacuna ref never opens a segment, not even at the hard stop.
    flat = _flat(1, 99) + [{"ref": "post 99", "text": "gap"}] + _flat(100, 10)
    for e in flat[99:]:
        e.pop("speakers", None)
    starts = _starts(_segment_play_lines(flat, {"1"}, {"1"}))
    assert "post 99" not in starts and starts[1] == "100"


def test_a_declared_line_must_match_exactly():
    import pytest
    from drama_pipeline.stage1_turn_english import _resolve_covered

    segs = [{"id": "1:328", "lines": [{"ref": "328"}, {"ref": "368a"}]}]
    with pytest.raises(ValueError):
        _resolve_covered([{"greek": "368", "by": "328"}], segs, "t")
