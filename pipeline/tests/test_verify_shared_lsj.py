"""verify_shared_lsj.py — the shared-dictionary safety gate (LSJ/Greek,
Lewis & Short/Latin). Covers the FAIL-OPEN fix (Wave 2 Batch 1b review,
item 4): an unrecognized `work.language` used to fall back to "lsj"
(Greek's shard dir) via `SHARD_DIR.get(language, "lsj")`, silently checking
a mis-declared work's dictionary keys against the wrong dictionary instead
of failing the build. It must reject instead.
"""

import json
from pathlib import Path

from drama_pipeline import verify_shared_lsj


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


def test_rejects_unknown_language(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(verify_shared_lsj, "BUILD_DIR", tmp_path)
    dist = tmp_path / "dist"
    _write(dist / "badwork" / "analyses.json", {
        "foo": [{"lemma": "foo", "gloss": "", "parse": "", "lsj": ["foo-key"]}],
    })
    _write(dist / "badwork" / "manifest.json", {"work": {"language": "xx"}})

    rc = verify_shared_lsj.main()

    assert rc == 1
    err = capsys.readouterr().err
    assert "UNRECOGNIZED language" in err
    assert "badwork" in err


def test_grc_default_language_still_resolves(tmp_path, monkeypatch):
    # Sanity check alongside the rejection test above: a work with NO
    # manifest.json (or none carrying work.language) still defaults to
    # 'grc' and resolves against the 'lsj' shard dir exactly as before --
    # the fix rejects UNRECOGNIZED languages, not the legitimate default.
    monkeypatch.setattr(verify_shared_lsj, "BUILD_DIR", tmp_path)
    dist = tmp_path / "dist"
    _write(dist / "goodwork" / "analyses.json", {
        "foo": [{"lemma": "foo", "gloss": "", "parse": "", "lsj": ["lo/gos"]}],
    })
    _write(dist / "lsj" / "l.json", {"lo/gos": {"key": "lo/gos", "head": "λόγος", "html": ""}})

    rc = verify_shared_lsj.main()

    assert rc == 0
