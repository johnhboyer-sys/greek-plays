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
