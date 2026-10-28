"""Stage 8: the rules that decide which phrases exist at all.

A phrase excluded here is beyond the reach of any later filter — it was never
indexed — so these tests guard the exclusions specifically: book edges, keyless
tokens, the recurrence rule, and the lemma readings that must NOT be narrowed.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

from drama_pipeline.stage8_ngrams import _phrases, _readings  # noqa: E402


def grams(stream, books, total, n=None):
    """{phrase: [offsets]} for a stream of option-lists."""
    out = {}
    for gram, at in _phrases(stream, books, total):
        if n is None or len(gram.split(" ")) == n:
            out.setdefault(gram, []).append(at)
    return out


def one(*words):
    """A stream of unambiguous positions."""
    return [[w] for w in words]


class TestBoundaries:
    def test_a_phrase_never_spans_a_book_edge(self):
        # Book 1 is offsets 0-2, book 2 is 3-5.
        stream = one("a", "b", "c", "d", "e", "f")
        found = grams(stream, [0, 3], 6, n=2)
        assert "b c" in found          # inside book 1
        assert "d e" in found          # inside book 2
        assert "c d" not in found      # across the edge

    def test_a_phrase_never_spans_a_keyless_token(self):
        stream = one("a", "b") + [None] + one("c", "d")
        found = grams(stream, [0], 5, n=2)
        assert "a b" in found
        assert "c d" in found
        assert "b c" not in found      # the gap breaks the stream
        assert not any(g for g in grams(stream, [0], 5, n=3) if g.startswith("b"))

    def test_offsets_are_the_phrase_start(self):
        stream = one("a", "b", "c")
        assert grams(stream, [0], 3, n=2) == {"a b": [0], "b c": [1]}

    def test_every_length_from_two_to_five(self):
        stream = one(*"abcdef")
        lengths = {len(g.split(" ")) for g in grams(stream, [0], 6)}
        assert lengths == {2, 3, 4, 5}


class TestLemmaReadings:
    def test_an_ambiguous_position_contributes_every_reading(self):
        # The second position licenses two lemmas; both phrases must exist.
        stream = [["a"], ["b", "c"]]
        assert set(grams(stream, [0], 2, n=2)) == {"a b", "a c"}

    def test_readings_multiply_across_positions(self):
        stream = [["a", "b"], ["c", "d"]]
        assert set(grams(stream, [0], 2, n=2)) == {"a c", "a d", "b c", "b d"}

    def test_readings_of_an_unambiguous_window_is_one_phrase(self):
        assert _readings([["a"], ["b"]]) == [["a", "b"]]

    def test_every_reading_shares_the_one_offset(self):
        stream = [["a"], ["b", "c"]]
        found = grams(stream, [0], 2, n=2)
        assert found["a b"] == [0] and found["a c"] == [0]


class TestEnglishStream:
    def test_tokenizes_the_translation_the_way_stage6_indexes_it(self, tmp_path, monkeypatch):
        """english-segments.json offsets count words; stage6's english.json
        keys them. Both must split the same text into the same words — the
        archive translations print possessives with U+2019, which the old
        [a-z']+ scan broke into "aristotle" + "s"."""
        import json
        from drama_pipeline import stage8_ngrams

        work = tmp_path / "build" / "dist" / "TST"
        work.mkdir(parents=True)
        (work / "book-01.json").write_text(json.dumps({"book": 1, "segments": [
            {"id": "1:244b", "column": "244b",
             "english": {"text": "Aristotle’s first ‘change’ isn’t the last."}},
        ]}), encoding="utf-8")
        monkeypatch.setattr(stage8_ngrams, "BUILD_DIR", tmp_path / "build")
        stream, bounds, segments = stage8_ngrams._english_stream("TST")
        assert stream == [["aristotle's"], ["first"], ["change"], ["isn't"], ["the"], ["last"]]
        assert bounds == [0]
        assert segments == [{"book": 1, "column": "244b", "base": 0, "words": 6}]


def _build_corpus(tmp_path, monkeypatch):
    import json
    from drama_pipeline import stage8_ngrams

    monkeypatch.setattr(stage8_ngrams, "BUILD_DIR", tmp_path)
    (tmp_path / "ngrams").mkdir()
    lemma_map = tmp_path / "dist/lemma-map/a.json"
    lemma_map.parent.mkdir(parents=True)
    lemma_map.write_text('{"a":[["a","a/"]]}')
    for work in ("medea", "frogs"):
        (tmp_path / "ngrams" / f"{work}.json").write_text(json.dumps({
            "work": work, "token_count": 3,
            "book_bounds": [{"book": 1, "start": 0}], "chapter_bounds": [],
            "form": ["a", "b", "c"], "lemma": [["a"], ["b", "d"], ["c"]],
        }))
        work_dir = tmp_path / "dist" / work
        work_dir.mkdir()
        (work_dir / "book-01.json").write_text(json.dumps({"book": 1, "segments": [
            {"column": "1", "english": {"text": "The good[^1] [[s2]] life."}},
            {"column": "2", "english": {"text": "Begins here."}},
        ]}))
    return stage8_ngrams, lemma_map


def test_corpus_run_counts_scores_and_delta_encodes_without_touching_lemma_map(tmp_path, monkeypatch):
    import json
    import math

    stage8, lemma_map = _build_corpus(tmp_path, monkeypatch)
    before = lemma_map.read_bytes()
    out = stage8.run()
    summary = json.loads((out / "summary.json").read_text())
    assert summary["works"] == summary["english_works"] == 2
    assert "surface_forms" not in summary
    assert summary["streams"]["form"]["kept"] == 3
    browse = json.loads((out / "form/a.json").read_text())
    assert browse["a b"] == [2, 2, round(2 * math.log2(3), 1), 2]
    assert json.loads((out / "lemma/occ/a-2.json").read_text())["a d"] == {
        "frogs": [0], "medea": [0],
    }
    assert lemma_map.read_bytes() == before
    assert list(lemma_map.parent.iterdir()) == [lemma_map]
    english = json.loads((out / "english/t.json").read_text())
    assert "the good life" in english
    assert not (out / "english/l.json").exists()  # no "life begins" across segments
    citations = json.loads((out / "english-segments.json").read_text())
    assert citations["medea"] == [
        {"book": 1, "column": "1", "base": 0, "words": 3},
        {"book": 1, "column": "2", "base": 3, "words": 2},
    ]
    # Repeated offsets encode their first position then the gap.
    doc_path = tmp_path / "ngrams/medea.json"
    doc = json.loads(doc_path.read_text())
    doc.update(token_count=6, form=["a", "b", "c"] * 2, lemma=[["a"], ["b"], ["c"]] * 2)
    doc_path.write_text(json.dumps(doc))
    (out / "form/z.json").write_text('{}')
    stage8.run()
    assert not (out / "form/z.json").exists()
    assert json.loads((out / "form/occ/a-2.json").read_text())["a b"]["medea"] == [0, 3]
    assert lemma_map.read_bytes() == before


def test_corpus_run_rejects_stale_stream_lengths(tmp_path, monkeypatch):
    import json
    import pytest

    stage8, _ = _build_corpus(tmp_path, monkeypatch)
    path = tmp_path / "ngrams/medea.json"
    doc = json.loads(path.read_text())
    doc["token_count"] += 1
    path.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="stale build"):
        stage8.run()


def test_corpus_run_rejects_empty_corpus(tmp_path, monkeypatch):
    import pytest
    from drama_pipeline import stage8_ngrams

    monkeypatch.setattr(stage8_ngrams, "BUILD_DIR", tmp_path)
    with pytest.raises(ValueError, match="no per-work streams"):
        stage8_ngrams.run()


def test_phrases_carry_their_accented_display():
    # As written: the commonest printed spelling. Any form: the accented LSJ
    # headwords, null where a fold has none.
    from collections import Counter
    from drama_pipeline.stage8_ngrams import _display
    surfaces = {"A": ["πρὸς", "θεῶν", "x", "πρὸς", "θεῶν"], "B": ["Πρὸς", "θεῶν"]}
    at = {"A": [0, 3], "B": [0]}
    assert _display("form", "pros qewn", at, surfaces, {}) == "πρὸς θεῶν"
    heads = {"pros": "πρός", "qeos": "θεός"}
    assert _display("lemma", "pros qeos", {}, {}, heads) == "πρός θεός"
    assert _display("lemma", "pros zzz", {}, {}, heads) == ["πρός", None]
    assert _display("lemma", "yyy zzz", {}, {}, heads) is None
    assert _display("english", "by the gods", {}, {}, heads) is None


def test_accented_heads_find_capitalised_keys_where_stage5_files_them(tmp_path, monkeypatch):
    # Stage 5 skips capitals when it chooses a key's shard: Ba/qrakos is in a.json.
    from collections import Counter
    import json as _json
    from drama_pipeline import stage8_ngrams
    from drama_pipeline.stage5_lsj import shard_letter
    monkeypatch.setattr(stage8_ngrams, "BUILD_DIR", tmp_path)
    lsj = tmp_path / "dist" / "lsj"
    lsj.mkdir(parents=True)
    for key, head in (("Ba/qrakos", "Βάθρακος"), ("*Seilhniko/s", "Σειληνικός")):
        (lsj / f"{shard_letter(key)}.json").write_text(_json.dumps({key: {"head": head}}), encoding="utf-8")
    heads = stage8_ngrams._accented_heads({"baqrakos": Counter({"Ba/qrakos": 1}), "seilhnikos": Counter({"*Seilhniko/s": 1})})
    assert heads == {"baqrakos": "Βάθρακος", "seilhnikos": "Σειληνικός"}
