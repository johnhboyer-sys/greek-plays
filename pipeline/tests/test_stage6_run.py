"""Stage 6 end to end on a synthetic build, pinning what the reader joins on.

shared/lib/search.ts consumes these files by POSITION, not by name: a posting
is (seg_idx, token_pos), its global offset is seg_base_offset[seg_idx] + pos,
and offsetRef() walks line_runs to name the Bekker line. meta.json names
each seg_idx's passage, and preview text. Each test here
builds the smallest corpus that exercises one seam and reads the emitted
files back the way the reader would.
"""

import copy
import json
import struct
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

from drama_pipeline import stage6_search  # noqa: E402
from drama_pipeline.beta import to_beta_key  # noqa: E402
from drama_pipeline.stage3_tokenize import tokenize  # noqa: E402
from drama_pipeline.stage6_search import fold_lemma  # noqa: E402


from drama_pipeline.config import Manifest


# Physics 244b as Ross prints it (lettered 5a between 5 and 6) and DA 430b.20
# as the OCT sets it (the plain number 20 twice around a secluded block), then
# a second book so book_bounds has an edge to find.
_SPINE = {
    "work": "TST",
    "segments": [
        {"id": "1:244b", "book": 1, "column": "244b", "lines": [
            {"n": 4, "text": "ἅπασι γὰρ"},
            {"n": 5, "text": "τὸ πρῶτον ἀλλοιούμενον"},
            {"n": 5, "sub": "a", "text": "ὑπόκειται γὰρ"},
            {"n": 6, "text": "εἰρημένων ταῦτα"},
        ]},
        {"id": "1:245a", "book": 1, "column": "245a", "lines": [
            {"n": 20, "text": "καὶ χρόνῳ καὶ μήκει."},
            {"n": 20, "text": "ἡ δὲ στιγμὴ"},
        ]},
        {"id": "2:245b", "book": 2, "column": "245b", "lines": [
            {"n": 1, "text": "Σωκράτης ᾠδῇ προϊέναι"},
        ]},
    ],
}

_LONG_ENGLISH = ("The point and every division " * 30).strip()


def _english(chapters):
    return {
        "chunks": [
            {"id": "1:244b", "book": 1, "column": "244b",
             "text": "Aristotle’s first ‘change’ isn’t the last.",
             "notes": [], "markers": []},
            {"id": "1:245a", "book": 1, "column": "245a",
             "text": _LONG_ENGLISH, "notes": [], "markers": []},
        ],
        "chapters": chapters,
    }


def _build(tmp_path, monkeypatch, *, edition=False, spine=None, unkeyed=False):
    build = tmp_path / "build"
    (build / "stage1").mkdir(parents=True)
    (build / "stage3").mkdir()
    (build / "stage4").mkdir()
    spine = copy.deepcopy(spine or _SPINE)
    tokens, _, failures = tokenize(spine)
    # Drama's stage3 drops sub today; supply it directly to test stage6's
    # contract for future token documents that carry a line suffix.
    for seg, token_seg in zip(spine["segments"], tokens["segments"]):
        for line, token_line in zip(seg["lines"], token_seg["lines"]):
            if "sub" in line:
                token_line["sub"] = line["sub"]
    assert not failures, failures
    if unkeyed:
        tokens["segments"][0]["lines"][0]["tokens"][0].pop("k")
    keys = sorted({t["k"] for s in tokens["segments"] for l in s["lines"] for t in l["tokens"] if "k" in t})
    key_map = {k: k for k in keys}
    # Morpheus-style analyses for a few tokens; the rest stay unanalysed.
    analyses = {
        "ga/r": [{"lemma": "ga/r", "gloss": "for", "parse": "conj"}],
        "kai/": [{"lemma": "kai/", "gloss": "and", "parse": "conj"}],
        "to/": [{"lemma": "o(", "gloss": "the", "parse": "neut nom/acc sg"}],
    }
    (build / "stage1" / "greek_spine.json").write_text(
        json.dumps(spine, ensure_ascii=False), encoding="utf-8")
    (build / "stage1" / "english_chunks.json").write_text(
        json.dumps(_english([]), ensure_ascii=False), encoding="utf-8")
    (build / "stage3" / "tokens.json").write_text(
        json.dumps(tokens, ensure_ascii=False), encoding="utf-8")
    (build / "stage4" / "key_map.json").write_text(json.dumps(key_map), encoding="utf-8")
    (build / "stage4" / "analyses.json").write_text(
        json.dumps(analyses, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(stage6_search, "BUILD_DIR", build)
    work = {"id": "TST"}
    if edition:
        work["edition_id"] = "alternate"
    out = stage6_search.run(Manifest({"work": work}, build / "TST.yaml"))
    load = lambda name: json.loads((out / name).read_text(encoding="utf-8"))  # noqa: E731
    return {
        "offsets": load("offsets.json"),
        "grammar": load("grammar-dict.json"),
        "column": (out / "grammar-col.bin").read_bytes(),
        "meta": load("meta.json"),
        "english": load("english.json") if not edition else None,
        "form": load("form.json"),
        "lemma": load("lemma.json"),
        "out": out,
        "ngrams": (json.loads((build / "ngrams" / "TST.json").read_text(encoding="utf-8"))
                   if not edition else None),
        "tokens": tokens,
    }


# -- The offset primitive ----------------------------------------------------

def test_line_runs_follow_stage3_lines_one_run_per_line(tmp_path, monkeypatch):
    """One run per stage3 line, lettered and repeated lines included, so that
    offsetRef() walking the runs lands on the same line stage7 emits at that
    position. A lettered line carries its suffix as a third element, so a
    token on 244b5a is cited as 244b5a and not as 244b5; a repeated bare
    number (DA 430b.20 twice) still has none to carry."""
    offsets = _build(tmp_path, monkeypatch)["offsets"]
    runs = [s["line_runs"] for s in offsets["segments"]]
    assert runs[0] == [[4, 2], [5, 3], [5, 2, "a"], [6, 2]]
    assert runs[1] == [[20, 4], [20, 3]]
    assert runs[2] == [[1, 3]]


def test_seg_base_offset_is_the_running_token_count(tmp_path, monkeypatch):
    got = _build(tmp_path, monkeypatch)
    offsets = got["offsets"]
    assert offsets["seg_base_offset"] == [0, 9, 16]
    assert offsets["token_count"] == 19
    assert offsets["book_bounds"] == [{"book": 1, "start": 0}, {"book": 2, "start": 16}]
    # Every posting resolves to the token it names through base + pos.
    stream = [t for s in got["tokens"]["segments"] for l in s["lines"] for t in l["tokens"]]
    for key, posts in got["form"].items():
        for si, pos in posts:
            assert fold_lemma(stream[offsets["seg_base_offset"][si] + pos]["k"]) == key


def test_ngram_stream_shares_the_offset_space(tmp_path, monkeypatch):
    got = _build(tmp_path, monkeypatch)
    ng = got["ngrams"]
    assert ng["token_count"] == got["offsets"]["token_count"]
    assert len(ng["form"]) == len(ng["lemma"]) == ng["token_count"]
    assert ng["book_bounds"] == got["offsets"]["book_bounds"]


def test_english_words_matches_the_readers_fold():
    """Mirror of englishFold()/englishWords() in shared/lib/search.ts:
    lowercase, U+2019 and U+02BC become ', anything outside [a-z'] splits."""
    from drama_pipeline.stage6_search import english_words

    assert english_words("Aristotle’s ‘good’ isnʼt—well") == [
        "aristotle's", "good", "isn't", "well"]


# -- Greek index keys --------------------------------------------------------

_GREEK_BETA = {
    "α": "a", "β": "b", "γ": "g", "δ": "d", "ε": "e", "ζ": "z", "η": "h",
    "θ": "q", "ι": "i", "κ": "k", "λ": "l", "μ": "m", "ν": "n", "ξ": "c",
    "ο": "o", "π": "p", "ρ": "r", "σ": "s", "ς": "s", "τ": "t", "υ": "u",
    "φ": "f", "χ": "x", "ψ": "y", "ω": "w", "ϝ": "v",
}


def _reader_fold(text: str) -> str:
    """Line-for-line port of greekFold() in shared/lib/search.ts."""
    out = []
    for ch in unicodedata.normalize("NFD", text):
        low = ch.lower()
        if low in _GREEK_BETA:
            out.append(_GREEK_BETA[low])
        elif "a" <= low <= "z":
            out.append(low)
        elif ch == "'":
            out.append("'")
    return "".join(out)


def test_index_keys_are_what_the_reader_folds_a_query_to(tmp_path, monkeypatch):
    """greek_form.json is keyed by fold_lemma(beta key); the reader keys a
    query by greekFold(unicode). They are two implementations of one fold and
    must agree on every surface form in the corpus — capitals, final sigma,
    iota subscript, diaeresis, digamma, elision — or a typed word misses."""
    got = _build(tmp_path, monkeypatch)
    surfaces = [t["t"] for s in got["tokens"]["segments"] for l in s["lines"] for t in l["tokens"]]
    for surface in surfaces + ["Ϝάναξ", "δ’", "δ᾽", "ᾠδῇ", "προϊέναι", "Σωκράτης"]:
        # The text elides with U+2019/U+1FBD; beta.py keys those as a straight
        # apostrophe, and greekFold() keeps only a straight one — so the
        # contract holds for the form a reader types. (A curly apostrophe
        # pasted from the page folds to "d", not "d'", on the reader side.)
        typed = surface.replace("’", "'").replace("᾽", "'")
        assert fold_lemma(to_beta_key(surface)) == _reader_fold(typed), surface
    assert {"apasi", "swkraths", "wdh", "proienai"} <= set(got["form"])


def test_index_keys_do_not_depend_on_unicode_normalization_form():
    for word in ("ἅπασι", "ᾠδῇ", "προϊέναι", "Σωκράτης"):
        nfc, nfd = unicodedata.normalize("NFC", word), unicodedata.normalize("NFD", word)
        assert nfc != nfd
        assert fold_lemma(to_beta_key(nfc)) == fold_lemma(to_beta_key(nfd))


def test_lemma_index_is_keyed_by_folded_headword(tmp_path, monkeypatch):
    got = _build(tmp_path, monkeypatch)
    # "τὸ" is analysed to the article o(; the token has no posting under "to".
    assert got["lemma"]["o"] == [[0, 2]]
    assert "to" not in got["lemma"]
    assert got["form"]["to"] == [[0, 2]]
    # γὰρ occurs on 244b4 and 244b5a: both postings, in document order.
    assert got["lemma"]["gar"] == [[0, 1], [0, 6]]


def test_grammar_column_joins_tokens_by_global_offset(tmp_path, monkeypatch):
    got = _build(tmp_path, monkeypatch)
    grammar = got["grammar"]
    total = got["offsets"]["token_count"]
    assert grammar["token_count"] == total == len(got["column"]) // grammar["width"]
    column = struct.unpack(f"<{total}H", got["column"])
    assert grammar["sigs"][column[1]] == [{"marker": ["conj"]}]
    assert grammar["sigs"][column[2]] == [{"case": ["acc", "nom"], "gender": ["neut"], "number": ["sg"]}]
    assert column[0] == grammar["reserved"]["unanalysed"]
    assert got["offsets"]["chapter_bounds"] == []


def test_offsets_preserve_transposed_and_noninteger_line_labels(tmp_path, monkeypatch):
    spine = copy.deepcopy(_SPINE)
    labels = ["5a", 5, 5, "3-4"]
    for line, label in zip(spine["segments"][0]["lines"], labels):
        line["n"] = label
    got = _build(tmp_path, monkeypatch, spine=spine)
    assert [run[0] for run in got["offsets"]["segments"][0]["line_runs"]] == labels


def test_edition_emits_grammar_and_offsets_without_corpus_stream(tmp_path, monkeypatch):
    got = _build(tmp_path, monkeypatch, edition=True)
    assert got["grammar"]["token_count"] == got["offsets"]["token_count"]
    assert not (tmp_path / "build/ngrams").exists()


def test_stage6_raises_on_failed_validation(tmp_path, monkeypatch):
    import pytest

    monkeypatch.setattr(stage6_search, "check_offsets", lambda *_: {"ok": False, "problems": ["bad offsets"]})
    with pytest.raises(ValueError, match="offset validation failed.*",):
        _build(tmp_path, monkeypatch)


def test_keyless_token_keeps_its_offset_and_breaks_both_streams(tmp_path, monkeypatch):
    got = _build(tmp_path, monkeypatch, unkeyed=True)
    assert got["offsets"]["token_count"] == 19
    assert struct.unpack_from("<H", got["column"])[0] == got["grammar"]["reserved"]["unkeyed"]
    assert got["ngrams"]["form"][0] is None
    assert got["ngrams"]["lemma"][0] is None
    assert got["form"]["gar"][0] == [0, 1]
