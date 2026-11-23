"""build/dist/lemma-map/*.json must not depend on the order the disk lists
the plays' folders in. A Mac lists them by name and Linux does not, so CI's
Linux build wrote the same maps with their keys in another order than the
live site's (HANDOFF-PORTABILITY.md, phase 1, test 2)."""

from __future__ import annotations

import json
from pathlib import Path

from drama_pipeline import stage6_search


def _dist(tmp_path: Path) -> Path:
    for work, words in (("alpha", {"lo/gon": "lo/gos", "a)/ndra": "a)nh/r"}),
                        ("beta", {"lo/gou": "lo/gos", "qeo/s": "qeo/s"}),
                        ("gamma", {"a)ndro/s": "a)nh/r", "zeu=": "*zeu/s"})):
        d = tmp_path / "dist" / work
        d.mkdir(parents=True)
        (d / "analyses.json").write_text(json.dumps({f: [{"lemma": h}] for f, h in words.items()}), encoding="utf-8")
    return tmp_path


def _maps(build: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in sorted((build / "dist" / "lemma-map").glob("*.json"))}


def test_the_lemma_map_is_the_same_whatever_order_the_disk_lists_the_plays(tmp_path, monkeypatch):
    # Each order is forced, not left to this disk: a Mac's APFS lists a
    # folder in its own hash order, Linux in another.
    build = _dist(tmp_path)
    current = json.loads((build / "dist" / "gamma" / "analyses.json").read_text(encoding="utf-8"))
    real_glob = Path.glob
    made = []
    for order in (sorted, lambda paths: list(reversed(sorted(paths)))):
        monkeypatch.setattr(Path, "glob", lambda self, pattern, order=order: iter(order(list(real_glob(self, pattern)))))
        stage6_search.build_lemma_map(current, "gamma", build)
        monkeypatch.setattr(Path, "glob", real_glob)
        made.append(_maps(build))
    assert made[0] == made[1]
    assert set(made[0]) == {"a.json", "l.json", "q.json", "z.json"}
    # and the order is the plays' names: alpha's words before beta's
    assert list(json.loads(made[0]["l.json"])) == ["logon", "logos", "logou"]
