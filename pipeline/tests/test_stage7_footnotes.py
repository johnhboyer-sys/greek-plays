"""_resolve_footnotes_source (stage7_emit.py): which stage1 footnotes file
becomes a play's dist/<id>/footnotes.json, for the case a SECONDARY
(bench comparison) translation supplies footnotes rather than the primary
(Way's Loeb, 2026-09-14). Before this helper existed, `run()` only ever
looked at `english_footnotes.json` (the primary's), so a play whose primary
had no footnotes and whose secondary did would silently emit no
footnotes.json at all, and there was no guard against a play whose primary
AND secondary would both want to own footnotes.json (the reader loads only
one file per play)."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

import pytest

from drama_pipeline.config import Manifest
from drama_pipeline.stage7_emit import (
    _footnotes_overlay_candidates,
    _merge_footnotes,
    _resolve_footnotes_source,
)


def _manifest(
    *, primary_footnotes=False, primary_dir=None, third_footnotes=False,
    overlays=None,
) -> Manifest:
    primary: dict = {}
    if primary_footnotes:
        primary["footnotes"] = True
    if primary_dir:
        primary["dir"] = primary_dir
    english: dict = {"primary": primary}
    if third_footnotes:
        english["third"] = {"footnotes": True}
    if overlays is not None:
        english["overlays"] = overlays
    data = {
        "work": {"id": "suppliants-eur"},
        "english": english,
    }
    return Manifest(data, Path("manifests/suppliants-eur.yaml"))


def test_secondary_footnotes_used_when_primary_emits_none(tmp_path):
    stage1 = tmp_path
    (stage1 / "secondary_footnotes.json").write_text(
        json.dumps({"1.1": "Thebes: round the old citadel..."}), encoding="utf-8"
    )
    src = _resolve_footnotes_source(_manifest(), stage1)
    assert src == stage1 / "secondary_footnotes.json"


def test_empty_secondary_footnotes_file_is_ignored(tmp_path):
    stage1 = tmp_path
    (stage1 / "secondary_footnotes.json").write_text("{}", encoding="utf-8")
    assert _resolve_footnotes_source(_manifest(), stage1) is None


def test_primary_wins_when_secondary_absent(tmp_path):
    stage1 = tmp_path
    (stage1 / "english_footnotes.json").write_text(
        json.dumps({"1.1": "primary note"}), encoding="utf-8"
    )
    src = _resolve_footnotes_source(_manifest(primary_footnotes=True), stage1)
    assert src == stage1 / "english_footnotes.json"


def test_both_primary_and_secondary_footnotes_is_a_hard_failure(tmp_path):
    stage1 = tmp_path
    (stage1 / "english_footnotes.json").write_text(
        json.dumps({"1.1": "primary note"}), encoding="utf-8"
    )
    (stage1 / "secondary_footnotes.json").write_text(
        json.dumps({"1.1": "secondary note"}), encoding="utf-8"
    )
    manifest = _manifest(primary_footnotes=True)
    with pytest.raises(RuntimeError, match="suppliants-eur"):
        _resolve_footnotes_source(manifest, stage1)


# ---------------------------------------------------------------- 2026-09-24
# Rogers's Loeb Aristophanes (a `third`/`overlays` comparison column, e.g.
# Ecclesiazusae/Thesmophoriazusae/Wealth's `third` and Lysistrata's
# `overlays: [{id: rogers}]`) carries its own `[^n.m]` footnote calls, but
# `stage1_turn_english.run` computed and discarded them for every third/
# overlay slot: no `third_footnotes.json` / `overlay_<id>_footnotes.json`
# ever reached disk, so every one of Rogers's calls resolved nowhere. Fixed
# by writing those files (stage1_turn_english.py) and merging them into the
# primary's footnotes.json here (`_footnotes_overlay_candidates` +
# `_merge_footnotes`), disjoint keys required.


def test_third_footnotes_flagged_but_not_written_yields_no_candidate(tmp_path):
    """A play whose manifest flags `third.footnotes: true` but whose stage1
    build predates the fix (no third_footnotes.json on disk) must not crash
    -- it simply contributes nothing, same as before the fix existed."""
    manifest = _manifest(third_footnotes=True)
    assert _footnotes_overlay_candidates(manifest, tmp_path) == []


def test_third_footnotes_not_flagged_is_never_a_candidate_even_if_present(tmp_path):
    """third.footnotes: false (the common case) must ignore a
    third_footnotes.json on disk, e.g. a stale file from a previous work's
    build that single-work scratch cleanup missed."""
    (tmp_path / "third_footnotes.json").write_text(
        json.dumps({"1.1": "should not be picked up"}), encoding="utf-8"
    )
    manifest = _manifest(third_footnotes=False)
    assert _footnotes_overlay_candidates(manifest, tmp_path) == []


def test_primary_and_third_footnotes_merge_when_keys_are_disjoint(tmp_path):
    """The bug, fixed: a primary with notes and a third with notes (Rogers)
    both end up in the merged footnotes.json, keyed as their `[^n.m]` calls
    expect."""
    (tmp_path / "english_footnotes.json").write_text(
        json.dumps({"1.648": "primary note"}), encoding="utf-8"
    )
    (tmp_path / "third_footnotes.json").write_text(
        json.dumps({"1.1": "Rogers note"}), encoding="utf-8"
    )
    manifest = _manifest(primary_footnotes=True, third_footnotes=True)
    base_src = _resolve_footnotes_source(manifest, tmp_path)
    extra = _footnotes_overlay_candidates(manifest, tmp_path)
    merged = _merge_footnotes(base_src, extra, manifest.work_id)
    assert merged == {"1.648": "primary note", "1.1": "Rogers note"}


def test_primary_and_overlay_footnotes_merge(tmp_path):
    """Lysistrata's shape: Rogers rides as an `overlays` entry, not `third`."""
    (tmp_path / "english_footnotes.json").write_text(
        json.dumps({"1.390": "primary note"}), encoding="utf-8"
    )
    (tmp_path / "overlay_rogers_footnotes.json").write_text(
        json.dumps({"1.1": "Rogers note"}), encoding="utf-8"
    )
    manifest = _manifest(
        primary_footnotes=True,
        overlays=[{"id": "rogers", "footnotes": True}],
    )
    base_src = _resolve_footnotes_source(manifest, tmp_path)
    extra = _footnotes_overlay_candidates(manifest, tmp_path)
    merged = _merge_footnotes(base_src, extra, manifest.work_id)
    assert merged == {"1.390": "primary note", "1.1": "Rogers note"}


def test_overlay_footnotes_ignored_when_not_flagged(tmp_path):
    """An overlay translation without `footnotes: true` (e.g. Johnston in
    Lysistrata) never contributes, even if a footnotes file for it exists."""
    (tmp_path / "overlay_johnston_footnotes.json").write_text(
        json.dumps({"1.1": "should not be picked up"}), encoding="utf-8"
    )
    manifest = _manifest(overlays=[{"id": "johnston", "footnotes": False}])
    assert _footnotes_overlay_candidates(manifest, tmp_path) == []


def test_colliding_key_between_primary_and_third_is_a_hard_failure(tmp_path):
    (tmp_path / "english_footnotes.json").write_text(
        json.dumps({"1.1": "primary note"}), encoding="utf-8"
    )
    (tmp_path / "third_footnotes.json").write_text(
        json.dumps({"1.1": "Rogers note, same key"}), encoding="utf-8"
    )
    manifest = _manifest(primary_footnotes=True, third_footnotes=True)
    base_src = _resolve_footnotes_source(manifest, tmp_path)
    extra = _footnotes_overlay_candidates(manifest, tmp_path)
    with pytest.raises(RuntimeError, match="suppliants-eur.*1.1"):
        _merge_footnotes(base_src, extra, manifest.work_id)


def test_empty_third_footnotes_file_is_not_a_candidate(tmp_path):
    (tmp_path / "third_footnotes.json").write_text("{}", encoding="utf-8")
    manifest = _manifest(third_footnotes=True)
    assert _footnotes_overlay_candidates(manifest, tmp_path) == []


def test_merge_footnotes_returns_none_when_nothing_present(tmp_path):
    manifest = _manifest()
    base_src = _resolve_footnotes_source(manifest, tmp_path)
    extra = _footnotes_overlay_candidates(manifest, tmp_path)
    assert _merge_footnotes(base_src, extra, manifest.work_id) is None
