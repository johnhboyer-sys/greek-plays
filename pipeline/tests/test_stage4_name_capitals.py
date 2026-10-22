"""Names Morpheus also files under a common word (Ζεῦ under ζέω, Δί' under
δίω, Ἀπόλλων under ἀπό-λάω): a key printed capitalised mid-sentence gets
the capital key's readings (docs/proper-names/README.md)."""

import json
from pathlib import Path

from drama_pipeline import stage3_tokenize, stage4_morphology
from drama_pipeline.config import Manifest


def _spine(lines):
    return {
        "work": {"id": "NAMES"},
        "segments": [{"id": "1:1", "book": 1, "column": "1", "lines": [
            {"n": i + 1, "text": text} for i, text in enumerate(lines)
        ]}],
    }


def test_mid_sentence_capitals():
    spine = _spine([
        "Ναί, Ζεῦ, κλύε.",          # Ναί opens the play; Ζεῦ follows a comma
        "Ναὶ μὰ Δί'· Φέρ' ἴδω.",    # Δί' follows μὰ; Φέρ' follows a raised dot
        "τὸν Ἀπόλλω καλῶ;",          # mid-line after a lowercase word
        "Δίκη δ' ἔχει",              # line start after ';' on the line before
        "κράτος. ΧΟΡΟΣ",              # all capitals: a heading, not a name
        "καὶ ⟨Ζῆνα⟩",                 # editor's brackets do not hide the comma test
    ])
    tokens, _, _ = stage3_tokenize.tokenize(spine)
    assert stage3_tokenize.mid_sentence_capital_keys(spine, tokens) == {
        "zeu=", "di/'", "a)po/llw", "zh=na",
    }


def _run_stage4(tmp_path, monkeypatch, tokens, mid_caps, analyses_txt, patch=None):
    monkeypatch.setattr(stage4_morphology, "BUILD_DIR", tmp_path)
    (tmp_path / "stage3").mkdir()
    (tmp_path / "stage3" / "tokens.json").write_text(json.dumps({
        "segments": [{"column": "1", "lines": [{"n": 1, "tokens": tokens}]}],
    }))
    (tmp_path / "stage3" / "mid_caps.json").write_text(json.dumps(sorted(mid_caps)))
    diogenes = tmp_path / "diogenes"
    diogenes.mkdir()
    (diogenes / "greek-analyses.txt").write_text(analyses_txt)
    manifest = Manifest({
        "work": {"id": "NAMES", "author": "test", "language": "grc"},
        "books": [{"n": 1, "start": "1", "end": "9"}],
        "sources": {"diogenes_data": str(diogenes)},
    }, tmp_path / "NAMES.yaml")
    if patch:
        (tmp_path / "NAMES-analyses-patch.json").write_text(json.dumps(patch))
    stage4_morphology.run(manifest)
    analyses = json.loads((tmp_path / "stage4" / "analyses.json").read_text())
    key_map = json.loads((tmp_path / "stage4" / "key_map.json").read_text())
    return {k: [a["lemma"] for a in analyses[v]] for k, v in key_map.items()}


MORPHEUS = (
    "zeu=\t{1 9 zeu=,ze/w\tboil\tpres imperat act 2nd sg}\n"
    "*zeu=\t{2 0 *zeu=,*zeu/s\t\tmasc voc sg}\n"
    "di/kh\t{3 9 di/kh,di/kh\tjustice\tfem nom sg}\n"
    "*di/kh\t{4 0 *di/kh,*di/kh\t\tfem nom sg}\n"
    "nai/\t{5 9 nai/,nai/\tyes\tparticle}\n"
    "*nai/\t{6 0 *nai/,*nai/s\t\tfem voc sg}\n"
    "a)/rhs\t{7 0 a)/rhs,*)/arhs\t\tmasc nom sg}\n"
    "*)/arhs\t{8 0 *)/arhs,*)/aris\t\tmasc nom sg}\n"
)


def test_name_only_when_never_printed_lowercase(tmp_path, monkeypatch):
    lemmas = _run_stage4(tmp_path, monkeypatch, [{"t": "Ζεῦ", "k": "zeu="}], {"zeu="}, MORPHEUS)
    assert lemmas["zeu="] == ["*zeu/s"]


def test_both_readings_when_also_printed_lowercase(tmp_path, monkeypatch):
    tokens = [{"t": "Δίκη", "k": "di/kh"}, {"t": "δίκη", "k": "di/kh"}]
    lemmas = _run_stage4(tmp_path, monkeypatch, tokens, {"di/kh"}, MORPHEUS)
    assert lemmas["di/kh"] == ["di/kh", "*di/kh"]


def test_sentence_start_capital_unchanged(tmp_path, monkeypatch):
    lemmas = _run_stage4(tmp_path, monkeypatch, [{"t": "Ναί", "k": "nai/"}], set(), MORPHEUS)
    assert lemmas["nai/"] == ["nai/"]


def test_lowercase_key_already_a_name_unchanged(tmp_path, monkeypatch):
    lemmas = _run_stage4(tmp_path, monkeypatch, [{"t": "Ἄρης", "k": "a)/rhs"}], {"a)/rhs"}, MORPHEUS)
    assert lemmas["a)/rhs"] == ["*)/arhs"]


# Grok review, 2026-10-22 (findings 1-8).

def test_capital_behind_a_bracket_or_titlecase_counts(tmp_path, monkeypatch):
    tokens = [{"t": "⟨Ζεῦ⟩", "k": "zeu="}, {"t": "ᾍδης", "k": "a(/|dhs"}]
    morpheus = MORPHEUS + "a(/|dhs\t{9 9 a(/|dhs,a(/|dhs\tunseen\tmasc nom sg}\n*(/|adhs\t{10 0 *(/|adhs,*(/|adhs\t\tmasc nom sg}\n"
    lemmas = _run_stage4(tmp_path, monkeypatch, tokens, {"zeu=", "a(/|dhs"}, morpheus)
    assert lemmas["zeu="] == ["*zeu/s"]
    assert lemmas["a(/|dhs"] == ["*(/|adhs"]


def test_name_readings_do_not_overwrite_a_shared_hit(tmp_path, monkeypatch):
    # zeu+= resolves to zeu= too; it must keep the common reading.
    tokens = [{"t": "Ζεῦ", "k": "zeu="}, {"t": "ζεῦ̈", "k": "zeu+="}]
    lemmas = _run_stage4(tmp_path, monkeypatch, tokens, {"zeu="}, MORPHEUS)
    assert lemmas["zeu="] == ["*zeu/s"]
    assert lemmas["zeu+="] == ["ze/w"]


def test_hand_patch_wins(tmp_path, monkeypatch):
    patch = {"zeu=": [{"lemma_id": 0, "form": "zeu=", "lemma": "ze/w", "gloss": "HAND", "parse": "x"}]}
    lemmas = _run_stage4(tmp_path, monkeypatch, [{"t": "Ζεῦ", "k": "zeu="}], {"zeu="}, MORPHEUS, patch)
    assert lemmas["zeu="] == ["ze/w"]


def test_parse_filter_keeps_an_unresolved_name_beside_a_common_word():
    from drama_pipeline.parse_filter import filter_parses
    common = {"lemma": "ze/w", "gloss": "boil", "lsj": ["ze/w"]}
    name = {"lemma": "*zeu/s", "gloss": "", "lsj": []}
    assert filter_parses([common, name]) == [common, name]
    # a stray name reading beside a resolved name is still dropped (Εὐρώπης)
    real = {"lemma": "*eu)rw/ph", "gloss": "", "lsj": ["*eu)rw/ph"]}
    stray = {"lemma": "*eu)rw/phs", "gloss": "", "lsj": []}
    assert filter_parses([real, stray]) == [real]


def test_mid_sentence_edge_cases():
    spine = _spine([
        "κράτος. ΧΟΡΟΣ",      # a heading between a stop and the next line
        "Φέρε ἰδεῖν",          # opens a sentence: not mid-sentence
        "εἶπεν … Ἀλλά",        # an ellipsis ends the sentence
        "ΧΟΡΟΣʼ",              # a heading with a modifier-letter apostrophe
    ])
    tokens, _, _ = stage3_tokenize.tokenize(spine)
    assert stage3_tokenize.mid_sentence_capital_keys(spine, tokens) == set()
