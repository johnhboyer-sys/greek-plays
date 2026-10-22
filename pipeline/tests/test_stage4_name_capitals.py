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


def _run_stage4(tmp_path, monkeypatch, tokens, mid_caps, analyses_txt):
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
    }, Path("NAMES.yaml"))
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
