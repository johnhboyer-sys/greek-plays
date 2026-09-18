"""audit.py: the per-play audit sheet built from build/dist/<id> and
build/stage1/*_report.json. A tiny fixture play ("testplay") drives
sections 1-3, 8, 9 (one seeded defect and one clean case each) and the
report `work`-field refusal (build/stage1 is single-work scratch, so a
stale report from a different play must never be read as this play's)."""

import json
from pathlib import Path

import pytest

from drama_pipeline import audit
from drama_pipeline.config import Manifest

WORK = "testplay"


def _manifest(english=None, registry_translations=None):
    data = {
        "work": {"id": WORK, "language": "grc"},
        "english": english or {
            "primary": {"id": "prim", "model": "perseus-play", "source": "perseus/prim.xml"},
            "secondary": {"id": "sec", "model": "turn-text", "source": "bench/sec/testplay.txt"},
        },
        "registry": {
            "translations": registry_translations or [
                {"id": "prim", "form": "prose"},
                {"id": "sec", "form": "verse"},
            ],
        },
    }
    return Manifest(data, Path("manifests/testplay.yaml"))


def _segment(seg_id, greek_lines, english_text=None, ross_pieces=None, greek_start=1):
    greek = [
        {"n": greek_start + i, "text": "x" * 10, "ref": str(greek_start + i)}
        for i in range(greek_lines)
    ]
    seg = {"id": seg_id, "column": "1", "greek": greek}
    seg["english"] = {"text": english_text} if english_text is not None else None
    seg["ross"] = ross_pieces if ross_pieces is not None else []
    return seg


def _write_book(dist_dir: Path, segments, roster=None):
    dist_dir.mkdir(parents=True, exist_ok=True)
    (dist_dir / "book-01.json").write_text(
        json.dumps({"book": 1, "segments": segments, "speakerRoster": roster or ["Chorus"]}),
        encoding="utf-8",
    )


def _write_report(stage1_dir: Path, name: str, **fields):
    stage1_dir.mkdir(parents=True, exist_ok=True)
    base = {"work": WORK, "translation": name, "footnotes": 0, "speakers": {
        "only_in_english": [], "only_in_greek": [],
    }}
    base.update(fields)
    (stage1_dir / f"{name}_report.json").write_text(json.dumps(base), encoding="utf-8")


# ---------------------------------------------------------- section 1-3 --

def test_columns_section_reports_pairing_rate_and_shift_runs(tmp_path):
    dist_dir = tmp_path / "dist" / WORK
    stage1_dir = tmp_path / "stage1"
    _write_book(dist_dir, [_segment("1:1", 2, english_text="hello")])
    _write_report(
        stage1_dir, "english",
        coverage_ratio=0.5, segments_total=2, segments_with_chunk=1,
    )
    _write_report(
        stage1_dir, "secondary",
        pairing_rate=0.9, greek_unpaired=1, turn_shift_count=2,
        turn_shifts=[
            {"greek_id": "1:1", "greek_speaker": "Chorus", "greek_ordinal": 1, "english_ordinal": 2},
            {"greek_id": "1:2", "greek_speaker": "Chorus", "greek_ordinal": 2, "english_ordinal": 3},
        ],
    )
    manifest = _manifest()
    manifest.data["english"]["primary"]["id"] = "english"
    manifest.data["english"]["secondary"]["id"] = "secondary"
    manifest.data["registry"]["translations"] = [
        {"id": "english", "form": "prose"}, {"id": "secondary", "form": "verse"},
    ]
    sheet, totals = audit.build_sheet(WORK, dist_dir, stage1_dir, manifest)
    assert "0.500" in sheet  # primary's coverage_ratio stands in for pairing rate
    assert "0.900" in sheet  # secondary's real pairing_rate
    assert "1:1 (×2)" in sheet  # one run of 2 consecutive same-offset shifts


def test_bare_greek_flags_short_column_but_not_a_full_one(tmp_path):
    dist_dir = tmp_path / "dist" / WORK
    stage1_dir = tmp_path / "stage1"
    bare = _segment("1:1", 10, english_text="short")  # far under 25% of greek chars
    full = _segment("1:11", 10, english_text="y" * 100, greek_start=11)  # plenty of text
    _write_book(dist_dir, [bare, full])
    manifest = _manifest(english={
        "primary": {"id": "prim", "model": "perseus-play", "source": "perseus/prim.xml"},
    }, registry_translations=[{"id": "prim", "form": "prose"}])
    sheet, totals = audit.build_sheet(WORK, dist_dir, stage1_dir, manifest)
    assert totals["bare_greek"] == 1
    assert "1:1" in sheet
    assert "1:11" not in sheet.split("## 3.")[0].split("## 2.")[1]


def test_bare_greek_flags_a_wholly_empty_column_under_the_eight_line_floor(tmp_path):
    """Ajax review finding B (2026-09-16): three Storr cells at 1:529, 1:939,
    1:1130 have no `ross` text at all, but each is a one-line stichomythia
    turn, so the old 8-line floor skipped the segment before the "no text"
    check ever ran. A wholly empty column must be flagged at any Greek
    content (a segment with zero Greek lines has nothing to compare and
    stays skipped); the 8-line floor still gates the 30%/25% ratio checks."""
    dist_dir = tmp_path / "dist" / WORK
    stage1_dir = tmp_path / "stage1"
    empty = _segment("1:1", 1, ross_pieces=[])  # one greek line, ross wholly empty
    clean = _segment("1:2", 1, ross_pieces=[{"text": "a line"}], greek_start=2)
    no_greek = _segment("1:3", 0, ross_pieces=[], greek_start=3)  # nothing to compare
    _write_book(dist_dir, [empty, clean, no_greek])
    manifest = _manifest(english={
        "secondary": {"id": "sec", "model": "turn-text", "source": "bench/sec/testplay.txt"},
    }, registry_translations=[{"id": "sec", "form": "verse"}])
    sheet, totals = audit.build_sheet(WORK, dist_dir, stage1_dir, manifest)
    section2 = sheet.split("## 2. Bare Greek")[1].split("## 3.")[0]
    assert "1:1" in section2
    assert "no text" in section2
    assert "1:2" not in section2
    assert "1:3" not in section2
    assert totals["bare_greek"] == 1


def test_overstuffed_flags_oversized_column_but_not_a_proportionate_one(tmp_path):
    dist_dir = tmp_path / "dist" / WORK
    stage1_dir = tmp_path / "stage1"
    stuffed = _segment("1:1", 2, english_text="z" * 200)  # >>4x the 20 greek chars
    proportionate = _segment("1:3", 2, english_text="z" * 30, greek_start=3)
    _write_book(dist_dir, [stuffed, proportionate])
    manifest = _manifest(english={
        "primary": {"id": "prim", "model": "perseus-play", "source": "perseus/prim.xml"},
    }, registry_translations=[{"id": "prim", "form": "prose"}])
    sheet, totals = audit.build_sheet(WORK, dist_dir, stage1_dir, manifest)
    assert totals["overstuffed"] == 1
    section3 = sheet.split("## 3. Overstuffed")[1].split("## 4.")[0]
    assert "1:1" in section3
    assert "1:3" not in section3


# --------------------------------------------------------------- section 6 --

def test_directions_counts_built_directionsbefore_when_source_has_none(monkeypatch, tmp_path):
    """Ajax review finding B (2026-09-16): the loeb-ocr turn-english path
    lifts stage directions onto the built pieces' `directionsBefore`
    (commit 7db48a2) without ever writing `_..._` markup into the raw bench
    text, so the old source-only scan reported "0" for a play the built
    JSON carries eight directions for. Directions must be counted from the
    built pieces (and their turns) as well as from the source, and both
    numbers printed."""
    dist_dir = tmp_path / "dist" / WORK
    stage1_dir = tmp_path / "stage1"
    seg1 = _segment("1:1", 3, ross_pieces=[
        {"text": "TECMESSA. Aye, my dear lord.", "directionsBefore": ["Enter TECMESSA."]},
    ])
    seg2 = _segment("1:4", 3, ross_pieces=[
        {"text": "more verse", "turns": [{"speaker": "Ajax", "directionsBefore": ["Exit MENELAUS."]}]},
    ], greek_start=4)
    _write_book(dist_dir, [seg1, seg2])
    manifest = _manifest(english={
        "secondary": {"id": "sec", "model": "turn-text", "source": "bench/sec/testplay.txt"},
    }, registry_translations=[{"id": "sec", "form": "verse"}])
    # The loeb-ocr bench file itself has no `_..._` markup -- both directions
    # live only in the built pieces.
    monkeypatch.setattr(audit, "_read_source_lines", lambda col: ["TECMESSA. Aye, my dear lord."])
    sheet, totals = audit.build_sheet(WORK, dist_dir, stage1_dir, manifest)
    section6 = sheet.split("## 6. Directions")[1].split("## 7.")[0]
    assert "| sec | 0 | 2 | - |" in section6  # 0 source markers, 2 built directions


# --------------------------------------------------------------- section 8 --

def test_footnotes_section_flags_marker_and_note_without_a_match(tmp_path):
    dist_dir = tmp_path / "dist" / WORK
    stage1_dir = tmp_path / "stage1"
    seg = _segment("1:1", 2, english_text="a note[^1] here")
    _write_book(dist_dir, [seg])
    (dist_dir / "footnotes.json").write_text(
        json.dumps({"1": "matched note", "9": "orphan note"}), encoding="utf-8"
    )
    manifest = _manifest(english={
        "primary": {"id": "prim", "model": "perseus-play", "source": "perseus/prim.xml"},
    }, registry_translations=[{"id": "prim", "form": "prose"}])
    sheet, totals = audit.build_sheet(WORK, dist_dir, stage1_dir, manifest)
    section8 = sheet.split("## 8. Footnotes")[1].split("## 9.")[0]
    assert "note 9" in section8
    assert "no matching marker" in section8
    assert "marker [^1]" not in section8  # 1 has a matching note: clean


# --------------------------------------------------------------- section 9 --

def test_verse_shape_flags_long_line_and_line_count_mismatch(tmp_path):
    dist_dir = tmp_path / "dist" / WORK
    stage1_dir = tmp_path / "stage1"
    long_line = "w" * 95
    bad = _segment("1:1", 10, ross_pieces=[{"text": long_line + "\nshort"}])  # 95 chars, 2 lines vs 10 greek
    clean = _segment("1:11", 2, ross_pieces=[{"text": "one\ntwo"}], greek_start=11)
    _write_book(dist_dir, [bad, clean])
    manifest = _manifest(english={
        "secondary": {"id": "sec", "model": "turn-text", "source": "bench/sec/testplay.txt"},
    }, registry_translations=[{"id": "sec", "form": "verse"}])
    sheet, totals = audit.build_sheet(WORK, dist_dir, stage1_dir, manifest)
    section9 = sheet.split("## 9. Verse shape")[1].split("## 10.")[0]
    assert "95" in section9
    assert "1:1" in section9
    assert "1:11" not in section9


# ------------------------------------------------------- work-id refusal --

def test_stale_report_from_a_different_play_is_refused(tmp_path):
    dist_dir = tmp_path / "dist" / WORK
    stage1_dir = tmp_path / "stage1"
    _write_book(dist_dir, [_segment("1:1", 2, english_text="hi")])
    stage1_dir.mkdir(parents=True)
    (stage1_dir / "english_report.json").write_text(
        json.dumps({"work": "some-other-play", "pairing_rate": 0.99}), encoding="utf-8"
    )
    manifest = _manifest(english={
        "primary": {"id": "prim", "model": "perseus-play", "source": "perseus/prim.xml"},
    }, registry_translations=[{"id": "prim", "form": "prose"}])
    sheet, totals = audit.build_sheet(WORK, dist_dir, stage1_dir, manifest)
    assert "0.990" not in sheet  # the other play's report is never read as this one's


# -------------------------------------------------------------- __main__ --

def test_stage1_clears_stale_report_jsons(tmp_path, monkeypatch):
    import drama_pipeline.__main__ as m
    import drama_pipeline.stage1_greek as stage1_greek

    monkeypatch.setattr(m, "BUILD_DIR", tmp_path)
    stage1_dir = tmp_path / "stage1"
    stage1_dir.mkdir(parents=True)
    stale_names = ["secondary_report.json", "third_report.json", "overlay_foo_report.json"]
    for name in stale_names:
        (stage1_dir / name).write_text("{}", encoding="utf-8")

    spine_path = tmp_path / "spine.json"
    spine_path.write_text(json.dumps({"segments": [], "unassigned_lines": []}), encoding="utf-8")
    monkeypatch.setattr(stage1_greek, "run", lambda manifest: spine_path)

    manifest = Manifest({"work": {"id": "x", "language": "grc"}}, Path("manifests/x.yaml"))
    # The bare manifest declares no citation.scheme and no english block, so
    # dispatch falls through to the removed Bekker-default builders past the
    # clear-list; only the clear-list's behavior is under test here.
    with pytest.raises(NotImplementedError):
        m._stage1(manifest)

    for name in stale_names:
        assert not (stage1_dir / name).exists()


# ------------------------------------------------- cues_in_speech / scan_noise --

def test_cues_in_speech_excludes_a_genuine_standalone_cue(monkeypatch):
    """Review finding 8: a line the model's own `_parse_as_speeches` cue
    rule (`_SPEAKER_LINE`) already recognises as a standalone speaker cue
    is a real cue, not one embedded inside a speech -- it must not be
    reported as a defect (nine such rows in Alcestis, review 2026-09-16)."""
    lines = ["CHORUS.", "Some running speech text that continues here."]
    monkeypatch.setattr(audit, "_read_source_lines", lambda col: lines)
    columns = [{"id": "sec", "model": "turn-text", "source": "x"}]
    _, total = audit.section_cues_in_speech(columns, roster=["Chorus"])
    assert total == 0


def test_cues_in_speech_still_flags_a_line_the_parser_would_not_treat_as_a_cue(monkeypatch):
    """A cue-shaped line the model's cue rule would NOT recognise (here,
    title case rather than the format's all-caps cue convention, so
    `_SPEAKER_LINE` does not match) is a genuine defect and stays flagged."""
    lines = ["Chorus."]
    monkeypatch.setattr(audit, "_read_source_lines", lambda col: lines)
    columns = [{"id": "sec", "model": "turn-text", "source": "x"}]
    _, total = audit.section_cues_in_speech(columns, roster=["Chorus"])
    assert total == 1


def test_scan_noise_does_not_flag_accented_latin_verse(monkeypatch):
    """Review finding 9: accented Latin letters (Latin-1 Supplement,
    Latin Extended-A, and combining marks) are ordinary English verse
    diacritics (`cursed`, `winged`, `Cyllene`, `Phaethon`), not scan
    noise, and must not inflate the audit's non-Latin-glyph count."""
    lines = ["The cursèd king with wingèd feet climbs Cyllené's height,", "Phaéthon fell."]
    monkeypatch.setattr(audit, "_read_source_lines", lambda col: lines)
    columns = [{"id": "sec", "model": "turn-text", "source": "x"}]
    _, total = audit.section_scan_noise(columns)
    assert total == 0


def test_scan_noise_still_flags_a_genuine_non_latin_glyph(monkeypatch):
    lines = ["This line has a stray Cyrillic д letter in it."]
    monkeypatch.setattr(audit, "_read_source_lines", lambda col: lines)
    columns = [{"id": "sec", "model": "turn-text", "source": "x"}]
    _, total = audit.section_scan_noise(columns)
    assert total == 1


# --------------------------------------------- D1: mid-line/pseudo cues --

def test_cues_in_speech_flags_a_cue_that_repeats_the_previous_cues_name(monkeypatch):
    """oedipus-tyrannus review finding 2, 2026-09-17: Storr's bench text
    gives Creon two consecutive cues with nothing but a blank line between
    ("CREON. My royal cousin..." / "CREON. Good news...") -- the Loeb gives
    the first speech to Oedipus. Two "CREON." cues in a row with no other
    speaker's cue between them is the tell, whichever line is the wrong
    one; both the old whole-line roster check and the all-caps check let
    it straight through because each line, alone, is a perfectly
    well-formed cue."""
    lines = [
        "CREON. My royal cousin, say, Menoeceus’ child,",
        "What message hast thou brought us from the god?",
        "",
        "CREON. Good news, for e’en intolerable ills,",
        "Finding right issue, tend to naught but good.",
    ]
    monkeypatch.setattr(audit, "_read_source_lines", lambda col: lines)
    columns = [{"id": "storr", "model": "turn-text", "source": "x"}]
    table, total = audit.section_cues_in_speech(columns, roster=["Creon", "Oedipus"])
    assert total == 2
    assert "cue repeated at line 4" in table
    assert "repeats the cue at line 1" in table


def test_cues_in_speech_flags_a_roster_name_embedded_mid_line(monkeypatch):
    """oedipus-tyrannus review finding 5, 2026-09-17: Kosmos's own
    paragraph break was lost, so Teiresias's reply runs on from Oedipus's
    speech with no cue period of its own -- "...Teiresias You find fault
    with my anger..." -- and the old check only ever looked at a whole
    line for a cue, never inside one."""
    lines = [
        "Will you never come to an end [telos]? Teiresias You find fault "
        "with my anger, but you do not perceive your own that lives with "
        "you; no, you blame me.",
    ]
    monkeypatch.setattr(audit, "_read_source_lines", lambda col: lines)
    columns = [{"id": "kosmos", "model": "turn-text", "source": "x"}]
    _, total = audit.section_cues_in_speech(columns, roster=["Oedipus", "Teiresias"])
    assert total == 1


def test_cues_in_speech_does_not_flag_an_ordinary_vocative_address(monkeypatch):
    """A character addressed by name mid-speech ("O Teiresias, hear me")
    is not a cue: the comma before the next word is what tells the two
    apart from finding 5's shape above, and must not itself become noise."""
    lines = ["O Teiresias, hear me now and heed my prayer."]
    monkeypatch.setattr(audit, "_read_source_lines", lambda col: lines)
    columns = [{"id": "kosmos", "model": "turn-text", "source": "x"}]
    _, total = audit.section_cues_in_speech(columns, roster=["Oedipus", "Teiresias"])
    assert total == 0


def test_cues_in_speech_flags_a_cue_with_an_unclosed_bracket_tail(monkeypatch):
    """oedipus-tyrannus review finding 6, 2026-09-17: Murray's "LEADER.
    [Strophe." glues a metrical label onto the cue with no closing
    bracket; the Chorus's actual line follows on the next source line, so
    neither the roster-fold check nor the all-caps check ever recognised
    this as a cue at all (only section 7's generic scan-noise scan caught
    the line, as a "bracket-tail turnover", not as a cue)."""
    lines = ["LEADER. [Strophe.", "Yield; consent; think! My Lord, I conjure thee!"]
    monkeypatch.setattr(audit, "_read_source_lines", lambda col: lines)
    columns = [{"id": "murray-verse", "model": "turn-text", "source": "x"}]
    _, total = audit.section_cues_in_speech(columns, roster=["Chorus"])
    assert total == 1


# ---------------------------------- D1: play-scoped raw-source reading --

def test_read_source_lines_blanks_out_a_different_play_sharing_the_file(tmp_path, monkeypatch):
    """clouds review finding, 2026-09-17: `gutenberg/pg8688.txt` holds all
    eleven Athenian Society comedies in one file; a raw-source scan of the
    whole file picks up another play's scan noise (and the trailing
    Gutenberg licence) and reports it as THIS play's defect. Section 7
    found athenian-society "bracket-tail turnover" and "non-Latin glyph"
    rows at lines that were really The Wasps, footnotes several plays
    over, or the licence -- none of them ever reaches the built columns.
    `_read_source_lines` must confine a multi-play source to the named
    play's own span, without shifting any other line's number."""
    text = "\n".join([
        "THE WASPS",
        "",
        "The Persons of the drama.",
        "",
        "BDELYCLEON",
        "",
        "Some Wasps speech with a stray Cyrillic д letter in it.",
        "",
        "FINIS OF \"THE WASPS\"",
        "",
        "THE CLOUDS",
        "",
        "The Persons of the drama.",
        "",
        "STREPSIADES",
        "",
        "An ordinary Clouds line.",
        "",
        "FINIS OF \"THE CLOUDS\"",
    ])
    source = tmp_path / "pg8688.txt"
    source.write_text(text, encoding="utf-8")
    monkeypatch.setattr(audit, "SOURCES_DIR", tmp_path)
    col = {"model": "turn-text", "source": "pg8688.txt", "play": "THE CLOUDS"}
    lines = audit._read_source_lines(col)
    joined = "\n".join(lines)
    assert "Cyrillic" not in joined
    assert "An ordinary Clouds line." in joined
    # Blanked, not sliced: line numbers for the surviving play stay the
    # file's own, so a reviewer's line reference still greps correctly --
    # index 8 (0-based) was "FINIS OF \"THE WASPS\"" and is now blank,
    # while index 10, "THE CLOUDS" itself, is untouched.
    assert lines[8] == "" and lines[10] == "THE CLOUDS"


def test_play_span_leaves_a_verse_own_line_bench_whole_when_the_title_is_a_cue():
    """Johnston's Ajax names the play `AJAX` and cues the hero `AJAX` 44
    times; with no dramatis list after the title the file is one play and
    must be read whole (Grok read of Lane D, 2026-09-17)."""
    from drama_pipeline.audit import _play_span

    lines = ["AJAX", "", "ATHENA", "I see you, son of Laertes.", "", "AJAX",
             "Hail, Athena.", "", "AJAX", "Now I go."]
    assert _play_span(lines, "AJAX") is None
