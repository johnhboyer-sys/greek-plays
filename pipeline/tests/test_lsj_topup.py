"""Lyceum P3 stage 2 (docs/p3-plan.md, Settled decisions 4).

Tests drama_pipeline.lsj_topup -- the build:public stage that regenerates
LSJ dictionary entries for keys referenced only by a mounted corpus's works
(never by a classical one), from a local grc.lsj.xml, using stage5_lsj's own
renderer. See lsj_topup.py's module docstring for the "mounted-only, not
missing-only" design and why "classical entries never overwritten" is
defined structurally (referenced by any non-mounted work) rather than by
write-order/provenance.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

from drama_pipeline import lsj_topup


FAKE_LSJ_XML = """\
<div2 type="entry" key="u(liko/s">
<head>ὑλικός</head>
<sense n="1"><i>of or belonging to matter</i></sense>
</div2>
<div2 type="entry" key="proaireto/s">
<head>προαιρετός</head>
<sense n="1"><i>deliberately chosen</i></sense>
</div2>
<div2 type="entry" key="a)/gw">
<head>ἄγω</head>
<sense n="1"><i>lead, carry</i></sense>
</div2>
"""


@pytest.fixture
def build_dir(tmp_path, monkeypatch):
    build = tmp_path / "build"
    monkeypatch.setattr(lsj_topup, "BUILD_DIR", build)
    return build


@pytest.fixture
def diogenes_dir(tmp_path, monkeypatch):
    data_dir = tmp_path / "diogenes"
    data_dir.mkdir()
    (data_dir / "grc.lsj.xml").write_text(FAKE_LSJ_XML, encoding="utf-8")
    monkeypatch.setenv("DIOGENES_DATA", str(data_dir))
    return data_dir


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_no_op_when_no_mounts_directory(build_dir, capsys):
    dist = build_dir / "dist"
    dist.mkdir(parents=True)
    assert lsj_topup.main() == 0
    assert "no-op" in capsys.readouterr().out


def test_regenerates_only_mounted_only_keys(build_dir, diogenes_dir, capsys):
    dist = build_dir / "dist"

    # A mounted (aristotle-like) work referencing two keys: one ALSO used by
    # a classical work (never touched), one genuinely mounted-only.
    _write_json(
        dist / "EN" / "analyses.json",
        {
            "u(liko/n": [{"lemma": "u(liko/s", "gloss": "", "parse": "", "lsj": ["u(liko/s"]}],
            "proaireto/s": [{"lemma": "proaireto/s", "gloss": "", "parse": "", "lsj": ["proaireto/s"]}],
        },
    )
    _write_json(dist / "EN" / "manifest.json", {"language": "grc"})

    _write_json(
        dist / "meditations" / "analyses.json",
        {"u(liko/s": [{"lemma": "u(liko/s", "gloss": "", "parse": "", "lsj": ["u(liko/s"]}]},
    )
    _write_json(dist / "meditations" / "manifest.json", {"language": "grc"})

    _write_json(dist / ".mounts" / "aristotle.json", {"corpus": "aristotle", "works": ["EN"]})

    # Pre-seed the classical shard for u(liko/s with a sentinel value that
    # must survive untouched (classical entries are never overwritten).
    (dist / "lsj").mkdir(parents=True)
    _write_json(
        dist / "lsj" / "u.json",
        {"u(liko/s": {"key": "u(liko/s", "head": "SENTINEL-CLASSICAL", "html": "sentinel"}},
    )

    assert lsj_topup.main() == 0
    out = capsys.readouterr().out
    assert "1 to regenerate" in out
    assert "regenerated 1 key(s)" in out

    classical_shard = json.loads((dist / "lsj" / "u.json").read_text(encoding="utf-8"))
    assert classical_shard["u(liko/s"]["head"] == "SENTINEL-CLASSICAL"  # untouched

    p_shard = json.loads((dist / "lsj" / "p.json").read_text(encoding="utf-8"))
    assert p_shard["proaireto/s"]["head"] == "προαιρετός"
    assert "deliberately chosen" in p_shard["proaireto/s"]["html"]


def test_stops_when_grc_lsj_xml_missing(build_dir, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DIOGENES_DATA", str(tmp_path / "nonexistent-diogenes-dir"))
    dist = build_dir / "dist"
    _write_json(
        dist / "EN" / "analyses.json",
        {"proaireto/s": [{"lemma": "proaireto/s", "gloss": "", "parse": "", "lsj": ["proaireto/s"]}]},
    )
    _write_json(dist / "EN" / "manifest.json", {"language": "grc"})
    _write_json(dist / ".mounts" / "aristotle.json", {"corpus": "aristotle", "works": ["EN"]})

    assert lsj_topup.main() == 1
    assert "STOP" in capsys.readouterr().err


def test_raises_on_unsupported_mounted_language(build_dir, diogenes_dir):
    dist = build_dir / "dist"
    _write_json(
        dist / "LatWork" / "analyses.json",
        {"amor": [{"lemma": "amor", "gloss": "", "parse": "", "lsj": ["amor"]}]},
    )
    _write_json(dist / "LatWork" / "manifest.json", {"language": "lat"})
    _write_json(dist / ".mounts" / "someLatinCorpus.json", {"corpus": "x", "works": ["LatWork"]})

    with pytest.raises(ValueError, match="unsupported language"):
        lsj_topup.main()


def test_no_op_when_nothing_to_regenerate(build_dir, diogenes_dir, capsys):
    dist = build_dir / "dist"
    _write_json(
        dist / "EN" / "analyses.json",
        {"u(liko/n": [{"lemma": "u(liko/s", "gloss": "", "parse": "", "lsj": ["u(liko/s"]}]},
    )
    _write_json(dist / "EN" / "manifest.json", {"language": "grc"})
    _write_json(
        dist / "meditations" / "analyses.json",
        {"u(liko/s": [{"lemma": "u(liko/s", "gloss": "", "parse": "", "lsj": ["u(liko/s"]}]},
    )
    _write_json(dist / "meditations" / "manifest.json", {"language": "grc"})
    _write_json(dist / ".mounts" / "aristotle.json", {"corpus": "aristotle", "works": ["EN"]})

    assert lsj_topup.main() == 0
    assert "nothing to regenerate" in capsys.readouterr().out
