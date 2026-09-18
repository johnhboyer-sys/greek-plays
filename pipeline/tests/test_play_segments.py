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
    # Four sentences of the ode on one Greek line: far above the column's
    # other chunks (a few words a line), so really stacked.
    one, two, six, ten = ("One " + "a" * 30 + ".", "Two " + "b" * 30 + ".",
                          "Six " + "c" * 30 + ".", "Ten " + "d" * 30 + ".")
    chunk = {"id": "1:351", "column": "351", "text": " ".join([one, two, six, ten]),
             "turns": [{"offset": 0, "speaker": "Chorus"}], "notes": [], "markers": []}
    herald = {"id": "1:503", "column": "503", "text": "Herald speaks.", "turns": [], "notes": [], "markers": []}
    fsegs, fchunks = _filler()
    out = _spread_long_speeches([chunk, herald, *fchunks], [*segs, *fsegs], sigla)
    assert [(c["id"], c["text"]) for c in out[:5]] == [
        ("1:351", one), ("1:355", two), ("1:420", six),
        ("1:489", ten), ("1:503", "Herald speaks."),
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


# The stacking guard (John, 2026-09-12, on the Codex review of 64e49a3): a
# Greek segment with a speaker mark continues the speech only when the
# English is really stacked, and only where the Greek goes on in one voice.
_SIGLA = {"Χο.": "Chorus", "Ιων": "Ion", "ΚΗΡΥΞ": "Herald"}


def _seg(sid, label=None, n=1, text="λόγος", strophe=None):
    lines = [{"text": text} for _ in range(n)]
    if strophe:
        lines[0]["label"] = strophe
    seg = {"id": sid, "column": sid.split(":")[1], "lines": lines}
    if label:
        seg["speakers"] = [{"line": 1, "label": label}]
    return seg


def _chunk(sid, text, turns=None):
    return {"id": sid, "column": sid.split(":")[1], "text": text,
            "turns": turns or [], "notes": [], "markers": []}


def _filler():
    # Ordinary chunks: 20 characters of English a Greek line (the median).
    segs = [_seg(f"1:{900 + i}", "ΚΗΡΥΞ") for i in range(3)]
    return segs, [_chunk(s["id"], "Twenty characters x.") for s in segs]


def _spread_ids(head_label, head_text, cont, head_lines=1):
    from drama_pipeline.stage1_turn_english import _spread_long_speeches

    fsegs, fchunks = _filler()
    segs = [_seg("1:1", head_label, head_lines), cont, *fsegs]
    out = _spread_long_speeches([_chunk("1:1", head_text), *fchunks], segs, _SIGLA)
    return [c["id"] for c in out if c["id"] in ("1:1", cont["id"])]


def _speech(chars):
    # Sentences of ten characters each, `chars` characters in all.
    return " ".join(["Aaaa bbbb."] * (chars // 11 + 1))[:chars].rstrip()


def test_a_bare_dash_is_crossed_only_when_the_english_is_really_stacked():
    # Bacchae 586/591: the English fits its Greek; "—" at 591 is not its
    # overflow (Codex: "With homage adore him" is 590, not 591).
    dash = _seg("1:591", "—", 3)
    assert _spread_ids("Χο.", _speech(40), dash) == ["1:1"]  # 2x the median
    assert _spread_ids("Χο.", _speech(60), dash) == ["1:1", "1:591"]  # 3x


def test_a_bare_dash_after_an_actor_is_a_new_speaker():
    # Ion 224/225: Ion speaks, and the unnamed "—" is the Chorus answering.
    assert _spread_ids("Ιων", _speech(200), _seg("1:225", "—")) == ["1:1"]
    # Ion named again is Ion going on.
    assert _spread_ids("Ιων", _speech(200), _seg("1:225", "Ιων")) == ["1:1", "1:225"]


def test_a_same_voice_mark_needs_only_english_above_the_median():
    # Orestes 1302/1311 (Χο. again, 1.1x) and Suppliants (Aesch.) 734/736
    # (a strophe begins under "—") cross; Hecuba 754/759 (0.99x) does not;
    # a bare dash at the same 1.1x does not.
    assert _spread_ids("Χο.", _speech(24), _seg("1:5", "Χο.")) == ["1:1", "1:5"]
    assert _spread_ids("Χο.", _speech(24), _seg("1:5", "—", strophe="στρ. α.")) == ["1:1", "1:5"]
    assert _spread_ids("Χο.", _speech(19), _seg("1:5", "Χο.")) == ["1:1"]
    assert _spread_ids("Χο.", _speech(24), _seg("1:5", "—")) == ["1:1"]


def test_english_that_marks_the_changes_of_voice_is_cut_at_its_turns():
    # Suppliants (Eur.) 598-602: half-choruses trade lines under bare "—";
    # Way prints each change. Cut by sentence proportion, 600's question got
    # 601's answer (Codex); cut at the turns, each lands on its own line.
    from drama_pipeline.stage1_turn_english import _spread_long_speeches

    t0 = "Ye hapless mothers. Ah, how my heart is tossed. What word is this."
    t1, t2 = "What news do you bring?", "Battle, or parley?"
    t3 = "This last were well. But if slaughter comes again. Then woe to us all."
    text = " ".join([t0, t1, t2, t3])
    turns = [{"offset": text.index(t), "speaker": "Half-Chorus"} for t in (t0, t1, t2, t3)]
    fsegs, fchunks = _filler()
    segs = [_seg("1:598", "Χο."), _seg("1:600", "—"), _seg("1:601", "—"), _seg("1:602", "—"), *fsegs]
    out = _spread_long_speeches([_chunk("1:598", text, turns), *fchunks], segs, _SIGLA)
    assert [(c["id"], c["text"]) for c in out[:4]] == [
        ("1:598", t0), ("1:600", t1), ("1:601", t2), ("1:602", t3),
    ]
    assert all(c["turns"] == [{"offset": 0, "speaker": "Half-Chorus"}] for c in out[:4])


def test_a_spread_cut_lands_on_a_greek_sentence_break():
    # John, 2026-09-12: a segment cut mid-sentence (the 40-line cap) opens
    # its English at its first Greek sentence start within 1.5 lines, so the
    # Greek sentence running over the cut keeps its English above. Here the
    # cut falls at line 4 of 8, mid-sentence; the next Greek sentence starts
    # on line 5. English sentences start at 3.3 and 4.8 lines by proportion:
    # 3.3 is nearer the cut, 4.8 nearer the Greek sentence.
    from drama_pipeline.stage1_turn_english import _spread_long_speeches

    greek = ["λόγος"] * 8
    greek[4] = "τέλος."
    head = {"id": "1:1", "column": "1", "speakers": [{"line": 1, "label": "Χο."}],
            "lines": [{"text": g} for g in greek[:4]]}
    cont = {"id": "1:5", "column": "5", "lines": [{"text": g} for g in greek[4:]]}
    s1, s2, s3 = "A" + "a" * 327 + ".", "B" + "b" * 147 + ".", "C" + "c" * 318 + "."
    text = " ".join([s1, s2, s3])
    assert (text.index("B"), text.index("C"), len(text)) == (330, 480, 800)
    out = _spread_long_speeches([_chunk("1:1", text)], [head, cont], _SIGLA)
    assert [(c["id"], c["text"]) for c in out] == [("1:1", f"{s1} {s2}"), ("1:5", s3)]


def test_a_mark_is_not_crossed_when_the_english_would_run_thin():
    # Thesmophoriazusae 1008/1015 (Codex): Hickie's English runs 2.3x the
    # median on 1008-1014, but none of it is the 39-line Andromeda lament;
    # spread over 1015 too it would be a third of the median.
    head = _speech(325)  # 7 lines at 20 a line would be 140
    assert _spread_ids("Ιων", head, _seg("1:1015", "Ιων", 39), head_lines=7) == ["1:1"]
    assert _spread_ids("Ιων", head, _seg("1:1015", "Ιων", 1), head_lines=7) == ["1:1", "1:1015"]


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


def test_a_bracketed_siglum_does_not_head_a_segment_it_sits_inside():
    """C17 (orestes finding 4, 2026-09-17): the edition brackets 957-959 as
    the editor's deletion, and the `Χο.` inside those brackets sits at offset
    2, so it never cut a segment — but it was the only speaker event in the
    segment the 80-line ceiling had just opened at 946, and so it HEADED it.
    The Messenger's last eleven lines were labelled and coloured Chorus, and
    both bench columns showed the Chorus's 957-959 beside them.

    A speaker label whose only predecessors on its line are the opening
    deletion bracket opens its own segment when the segment it would
    otherwise head has no speaker of its own.  The deleted lines keep their
    printed place and number (the hard rule); they simply stop capturing the
    speech above them.
    """
    flat = [{"ref": str(946 + k), "text": f"line {946 + k}"} for k in range(11)]
    flat += [
        {
            "ref": "957",
            "text": "[ ὦ δυστάλαινα παρθέν',",
            "speakers": [{"offset": 2, "label": "Χο."}],
        },
        {"ref": "958", "text": "πρόσωπον ἐς γῆν"},
        {"ref": "959", "text": "ὡς ἐς στεναγμοὺς]"},
    ]
    assert _starts(_segment_play_lines(flat)) == ["946", "957"]
    first, second = _segment_play_lines(flat)
    assert "speakers" not in first
    assert [e["label"] for e in second["speakers"]] == ["Χο."]


def test_a_bracketed_siglum_inside_a_headed_segment_still_does_not_cut():
    """The other twenty instances of the same shape: the segment already has
    its own line-start speaker, so the bracketed siglum is an ordinary
    mid-segment event (Medea 1415, Alcestis 1119, Rhesus 16) and must not
    split the speech it sits in."""
    flat = _flat(1410, 5)
    flat += [
        {
            "ref": "1415",
            "text": "[ ἀλλὰ",
            "speakers": [{"offset": 2, "label": "Χο."}],
        },
        {"ref": "1416", "text": "τέλος"},
    ]
    assert _starts(_segment_play_lines(flat)) == ["1410"]
