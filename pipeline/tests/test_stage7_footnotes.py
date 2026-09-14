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
from drama_pipeline.stage7_emit import _resolve_footnotes_source


def _manifest(*, primary_footnotes=False, primary_dir=None) -> Manifest:
    primary: dict = {}
    if primary_footnotes:
        primary["footnotes"] = True
    if primary_dir:
        primary["dir"] = primary_dir
    data = {
        "work": {"id": "suppliants-eur"},
        "english": {"primary": primary},
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
