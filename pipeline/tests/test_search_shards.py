"""Stage 9's corpus search shards preserve
the per-work indexes they are copied from.

shared/lib/search.ts runs its matching code on a shard's postings exactly as
it ran it on a work's own index, so the one thing a shard may never do is
differ from that index: a seg_idx that has drifted names the wrong passage.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

import pytest  # noqa: E402

from drama_pipeline.stage9_search_shards import run, shard_name  # noqa: E402

SHARD_FIXTURE = json.loads(
    (ROOT / "pipeline" / "tests" / "fixtures" / "search_shards.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize("case", SHARD_FIXTURE["cases"], ids=lambda c: c["word"] or "empty")
def test_shard_name_matches_the_shared_fixture(case):
    assert shard_name(case["word"]) == case["shard"]


def _write(path: Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")


# A Greek token spelling each form key, for the accents shards.
_SPELL = {"logou": ("λόγου", "lo/gou"), "logos": ("λόγος", "lo/gos"), "kai": ("καὶ", "kai\\")}


def _work(dist: Path, work: str, *, lemma, form, english, secondary=None) -> None:
    search = dist / work / "search"
    _write(search / "meta.json", [{"id": "1:1a", "book": 1, "column": "1a"}])
    _write(search / "greek_lemma.json", lemma)
    _write(search / "greek_form.json", form)
    if english is not None:
        _write(search / "english.json", english)
    if secondary is not None:
        _write(search / "english-secondary.json", secondary)
    _write(dist / work / "book-01.json", {"book": 1, "segments": [{"id": "1:1a", "greek": [
        {"n": 1, "tokens": [{"t": _SPELL[f][0], "k": _SPELL[f][1]} for f in form]}]}]})


def _corpus(tmp_path) -> Path:
    dist = tmp_path / "dist"
    _work(dist, "EN",
          lemma={"logos": [[0, 1]], "kai": [[0, 0], [0, 2]]},
          form={"logou": [[0, 1]], "kai": [[0, 0], [0, 2]]},
          english={"happiness": [[0, 3]], "the": [[0, 0]], "a": [[0, 1]]},
          secondary={"happiness": [[0, 2]], "virtue": [[0, 5]]})
    _work(dist, "Meta",
          lemma={"logos": [[0, 4]]},
          form={"logos": [[0, 4]]},
          english={"happiness": [[0, 7]], "being": [[0, 2]]})
    run(dist)
    return dist


def _shard(dist: Path, stream: str, name: str) -> dict:
    return json.loads((dist / "search-shards" / stream / f"{name}.json").read_text(encoding="utf-8"))


# -- The stage ---------------------------------------------------------------

def test_a_word_in_every_work_sits_in_one_shard(tmp_path):
    dist = _corpus(tmp_path)
    assert _shard(dist, "english", "ha") == {
        "happiness": {"EN/english": [[0, 3]], "EN/secondary": [[0, 2]], "Meta/english": [[0, 7]]},
    }
    assert _shard(dist, "lemma", "lo") == {"logos": {"EN": [[0, 1]], "Meta": [[0, 4]]}}
    assert _shard(dist, "form", "lo") == {"logos": {"Meta": [[0, 4]]}, "logou": {"EN": [[0, 1]]}}
    assert _shard(dist, "english", "a_") == {"a": {"EN/english": [[0, 1]]}}
    assert _shard(dist, "english", "vi") == {"virtue": {"EN/secondary": [[0, 5]]}}


def test_the_index_lists_every_shard_and_source(tmp_path):
    dist = _corpus(tmp_path)
    index = json.loads((dist / "search-shards" / "index.json").read_text())
    english = index["streams"]["english"]
    assert english["shards"] == ["a_", "be", "ha", "th", "vi"]
    assert sorted(english["sources"]) == ["EN/english", "EN/secondary", "Meta/english"]
    assert sorted(index["streams"]["lemma"]["sources"]) == ["EN", "Meta"]


def test_a_rebuild_drops_shards_no_word_needs_any_more(tmp_path):
    dist = _corpus(tmp_path)
    path = dist / "EN" / "search" / "english-secondary.json"
    english = json.loads(path.read_text())
    del english["virtue"]
    _write(path, english)
    run(dist)
    assert not (dist / "search-shards" / "english" / "vi.json").exists()


def test_a_work_without_its_greek_index_is_an_error(tmp_path):
    dist = _corpus(tmp_path)
    (dist / "Meta" / "search" / "greek_form.json").unlink()
    with pytest.raises(ValueError, match="Meta has no search/greek_form.json"):
        run(dist)




def test_greek_only_work_has_no_english_source(tmp_path):
    dist = tmp_path / "dist"
    _work(dist, "greek-only", lemma={"kai": [[0, 0]]}, form={"kai": [[0, 0]]}, english=None)
    run(dist)
    index = json.loads((dist / "search-shards/index.json").read_text())
    assert index["streams"]["english"] == {"shards": [], "sources": {}}
    assert _shard(dist, "form", "ka") == {"kai": {"greek-only": [[0, 0]]}}


def test_source_hashes_match_exact_per_work_bytes(tmp_path):
    import hashlib

    dist = _corpus(tmp_path)
    index = json.loads((dist / "search-shards/index.json").read_text())
    names = {"lemma": "greek_lemma", "form": "greek_form"}
    for stream, info in index["streams"].items():
        for source, digest in info["sources"].items():
            work, _, slot = source.partition("/")
            name = names.get(stream) or ("english" if slot == "english" else f"english-{slot}")
            raw = (dist / work / "search" / f"{name}.json").read_bytes()
            assert digest == hashlib.sha256(raw).hexdigest()[:16]


def test_empty_corpus_is_an_error(tmp_path):
    with pytest.raises(ValueError, match="no work"):
        run(tmp_path)
