import json

from drama_pipeline import stage6_search
from drama_pipeline.config import Manifest


def test_published_slots_and_lemma_map(tmp_path, monkeypatch):
    monkeypatch.setattr(stage6_search, "BUILD_DIR", tmp_path)
    for stage in ("stage1", "stage3", "stage4"):
        (tmp_path / stage).mkdir()
    def write(path, value):
        path.write_text(json.dumps(value), encoding="utf-8")

    write(tmp_path / "stage3/tokens.json", {"segments": [{
        "id": "1:1", "book": 1, "column": "1", "lines": [{"tokens": [{"k": "qeou/s", "t": "θεούς"}]}]
    }]})
    write(tmp_path / "stage4/key_map.json", {"qeou/s": "qeou/s"})
    write(tmp_path / "stage4/analyses.json", {"qeou/s": [{"lemma": "qeo/s"}, {"lemma": "qea/"}]})
    write(tmp_path / "stage1/english_chunks.json", {"chunks": [{"id": "1:1", "text": "first text"}]})
    write(tmp_path / "stage1/ross_chunks.json", {"1:1": [{"text": "second text"}]})
    write(tmp_path / "stage1/third_chunks.json", {"1:1": [{"text": "secret text"}]})
    write(tmp_path / "stage1/overlays.json", {"fourth": {"1:1": [{"text": "overlay text"}]}})
    manifest = Manifest({"work": {"id": "tiny"}, "english": {
        "primary": {"id": "first"}, "secondary": {"id": "second"},
        "third": {"id": "secret", "private": True},
        "overlays": [{"id": "fourth"}],
    }}, tmp_path / "tiny.yaml")
    out = stage6_search.run(manifest)
    english = json.loads((out / "english.json").read_text())
    assert english["text"] == [[0, "first"], [0, "fourth"], [0, "second"]]
    assert "secret" not in english
    meta = json.loads((out / "meta.json").read_text())
    assert set(meta[0]["english_slots"]) == {"second", "fourth"}
    shard = json.loads((tmp_path / "dist/lemma-map/q.json").read_text())
    assert shard["qeous"] == [["qea", "qea/"], ["qeos", "qeo/s"]]
    assert shard["qeos"] == [["qeos", "qeo/s"]]
