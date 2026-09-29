"""WP6: work.author / work.language — manifest accessors, preflight schema
validation, and stage4/stage5 dictionary-path parameterization.

Uses synthetic manifest data in the style of tests/fixtures/preflight/*/manifests/
(a minimal Bekker-scheme work dict) rather than a real corpus manifest.
"""

import json
from pathlib import Path

import pytest

from drama_pipeline.config import Manifest
from drama_pipeline import stage3_tokenize, stage4_morphology, stage5_lsj, stage6_search
from drama_pipeline.preflight import WorkManifest, _validate_manifest_schema


def _sources() -> dict:
    return {
        "tlg_dir_env": "TLG_DIR",
        "tlg_dir_default": "../TLG Files/TLG",
        "diogenes_server": "/Applications/Diogenes.app/Contents/server",
        "diogenes_data": "/Applications/Diogenes.app/Contents/dependencies/data",
    }


def _bekker_manifest_data(work_overrides: dict | None = None) -> dict:
    work = {
        "id": "VAL",
        "title": "Valid Fixture",
        "author": "aristotle",
        "tlg_author": "0086",
        "tlg_work": "999",
        "greek_edition": "Fixture Greek",
        "english_translation": "Fixture English",
    }
    work.update(work_overrides or {})
    return {
        "work": work,
        "bekker_range": {"first_column": "1094a", "last_column": "1094a"},
        "chapters": {"source": "explicit", "list": [{"n": 1, "bekker": "1094a1"}]},
        "english": {
            "primary": {
                "id": "fixture",
                "name": "Fixture English",
                "model": "archive",
                "dir": "fixture",
                "books": 1,
                "chapter_marker": "number",
            }
        },
        "books": [{"n": 1, "start": "1094a1", "end": "1094a2"}],
        "sources": _sources(),
    }


def _schema_problems(data: dict) -> list[str]:
    manifest = WorkManifest(work_id=data["work"]["id"], path=Path("VAL.yaml"), data=data)
    problems: list = []
    _validate_manifest_schema(manifest, problems)
    return [message for _work, _file, message in problems]


# --- Manifest accessors (config.py) -----------------------------------------


def test_manifest_exposes_author():
    m = Manifest(_bekker_manifest_data(), Path("VAL.yaml"))
    assert m.author == "aristotle"


def test_manifest_language_defaults_to_grc():
    m = Manifest(_bekker_manifest_data(), Path("VAL.yaml"))
    assert m.language == "grc"


def test_manifest_language_honors_explicit_value():
    m = Manifest(_bekker_manifest_data({"language": "lat"}), Path("VAL.yaml"))
    assert m.language == "lat"


def test_manifest_lexicon_defaults_to_true():
    m = Manifest(_bekker_manifest_data(), Path("VAL.yaml"))
    assert m.lexicon is True


def test_manifest_lexicon_honors_explicit_false():
    m = Manifest(_bekker_manifest_data({"lexicon": False}), Path("VAL.yaml"))
    assert m.lexicon is False


# --- preflight schema validation --------------------------------------------


def test_preflight_schema_rejects_missing_author():
    data = _bekker_manifest_data()
    del data["work"]["author"]
    problems = _schema_problems(data)
    assert any("work.author must be a non-empty string" in p for p in problems)


def test_preflight_schema_rejects_unknown_language():
    data = _bekker_manifest_data({"language": "fra"})
    problems = _schema_problems(data)
    assert any(
        "work.language 'fra' is not supported by drama_pipeline" in p for p in problems
    )


def test_preflight_schema_rejects_lat_language():
    # Latin/PHI support was removed in the drama fork (docs/plan.md §1) — a
    # 'lat' manifest must now fail loudly here in preflight's schema gate,
    # not deep in some stage that no longer has Latin machinery at all.
    data = _bekker_manifest_data({"language": "lat"})
    problems = _schema_problems(data)
    assert any(
        "work.language 'lat' is not supported by drama_pipeline" in p for p in problems
    )


def test_preflight_schema_omitted_language_is_fine():
    data = _bekker_manifest_data()
    assert "language" not in data["work"]
    assert _schema_problems(data) == []


# --- Blocker 1(a): work.lexicon must not fail open (Sol) --------------------


def test_preflight_schema_rejects_lexicon_false():
    # The no-lexicon posture (Wave 2 §4.2) was a Latin-only affordance;
    # Latin support was removed in the drama fork, so lexicon: false is
    # never permitted now, for any work.
    data = _bekker_manifest_data({"lexicon": False})
    problems = _schema_problems(data)
    assert any(
        "work.lexicon: false is not permitted" in p
        for p in problems
    ), problems


def test_preflight_schema_lexicon_true_is_fine_on_grc_work():
    data = _bekker_manifest_data({"lexicon": True})
    assert _schema_problems(data) == []


# --- stage4/stage5 dictionary/morphology source-path parameterization ------


def _language_manifest(language: str) -> Manifest:
    return Manifest(_bekker_manifest_data({"language": language}), Path("VAL.yaml"))


def test_stage5_grc_dictionary_path_unchanged():
    path = stage5_lsj._dictionary_path(_language_manifest("grc"))
    assert path.name == "grc.lsj.xml"


def test_stage5_base_key_strips_diogenes_latin_homonym_hash():
    # Real-data finding (Wave 2 Batch 1b): stage4's Latin lemma field carries
    # Diogenes' OWN homonym marker as "qui#1", "edo#1" -- confirmed 10.79% of
    # ALL latin-analyses.txt lemma groups (common words: "qui", "edo",
    # "is#1"/"is#2"), a DIFFERENT convention from Lewis & Short's own
    # trailing-digit key ("qui1", "e^do1"). Without stripping '#',
    # base_key("qui#1") left a dangling "qui#" that could never match L&S's
    # base_index (keyed off base_key("qui1") == "qui"), silently failing the
    # base-match fallback for ~11% of Latin lemmata -- caught by exercising
    # the real Diogenes data, not by unit tests alone (Karpathy rule 5).
    assert stage5_lsj.base_key("qui#1") == stage5_lsj.base_key("qui1") == "qui"
    assert stage5_lsj.fold_key("edo#1") == stage5_lsj.fold_key("edo1") == "edo"


def test_stage5_shard_letter_skips_capital_and_star_like_the_readers_do():
    # Real-build finding (surfaced by the case-fold fix, item 2): the OLD
    # `ch.isalpha()` accepted an uppercase first letter, sharding a
    # capitalized L&S proper-name key ("Py_tha^go^ras") under 'P' -- but
    # every reader (preflight._lsj_shard, data.ts's lsjShard, LemmaPage
    # .astro's lsjShardLetter) skips non-[a-z] characters and looks under
    # 'y'. This pins parity with those three.
    assert stage5_lsj.shard_letter("Py_tha^go^ras") == "y"
    assert stage5_lsj.shard_letter("*a)rxh/") == "a"  # Greek: unaffected, '*' skipped
    assert stage5_lsj.shard_letter("honestus") == "h"
    assert stage5_lsj.shard_letter("123") == "_"


def test_stage5_grc_hash_in_lemma_fails_loud(tmp_path, monkeypatch):
    # The Greek '#'-absence gate (Wave 2 Batch 1b review finding, item 1): a
    # loud runtime assertion, not a comment -- '#' is Diogenes' Latin-only
    # homonym marker, and Greek's own base/fold strip (_BASE_STRIP,
    # _FOLD_STRIP) silently corrupts a real Greek lemma/key if this ever
    # drifts.
    monkeypatch.setattr(stage5_lsj, "BUILD_DIR", tmp_path)
    (tmp_path / "stage4").mkdir()
    analyses = {
        "logos": [
            {"lemma_id": 1, "form": "logos", "lemma": "lo/gos#1", "gloss": "word", "parse": "noun"},
        ],
    }
    (tmp_path / "stage4" / "analyses.json").write_text(json.dumps(analyses))
    manifest = Manifest(_bekker_manifest_data({"id": "TSTHASH"}), Path("TSTHASH.yaml"))
    with pytest.raises(ValueError, match="#"):
        stage5_lsj.run(manifest)


def test_stage5_grc_hash_in_dictionary_key_fails_loud(tmp_path, monkeypatch):
    # Mirror of the lemma-side gate above, on the dictionary side: a
    # grc.lsj.xml key carrying '#' must also fail loud, not silently
    # corrupt the base/fold strip.
    monkeypatch.setattr(stage5_lsj, "BUILD_DIR", tmp_path)
    (tmp_path / "stage4").mkdir()
    analyses = {
        "logos": [
            {"lemma_id": 1, "form": "logos", "lemma": "lo/gos", "gloss": "word", "parse": "noun"},
        ],
    }
    (tmp_path / "stage4" / "analyses.json").write_text(json.dumps(analyses))

    diogenes_dir = tmp_path / "diogenes"
    diogenes_dir.mkdir()
    (diogenes_dir / "grc.lsj.xml").write_text(
        '<div2 id="x" key="lo/gos#1" n="1" opt="n">'
        '<head extent="full" lang="greek" opt="n">λόγος</head>'
        '<sense id="n1.0" n="I" level="1" opt="n">word</sense></div2>\n',
        encoding="utf-8",
    )
    data = _bekker_manifest_data({"id": "TSTHASH2"})
    data["sources"] = _sources()
    data["sources"]["diogenes_data"] = str(diogenes_dir)
    manifest = Manifest(data, Path("TSTHASH2.yaml"))
    with pytest.raises(ValueError, match="#"):
        stage5_lsj.run(manifest)


def test_stage4_grc_analyses_path_unchanged():
    path = stage4_morphology._analyses_path(_language_manifest("grc"))
    assert path.name == "greek-analyses.txt"


def test_stage6_fold_rejects_unknown_language():
    with pytest.raises(ValueError, match="unsupported language"):
        stage6_search.fold("logos", "xyz")


def test_stage6_fold_dispatches_grc():
    assert stage6_search.fold("lo/gos", "grc") == "logos"
    assert stage6_search.fold("⟨lo/gos⟩", "grc") == "logos"


# --- stage4 integration: whole-form-first vs enclitic-host resolution -----


def _empty_tokens_doc() -> dict:
    # Every token is non-lexical (no `k`) — the shape a lexicon-on work
    # would carry if stage3's lexical gate silently produced no keys.
    return {"segments": [{"column": "1.1", "lines": [{"n": 1, "tokens": [{"t": "***"}]}]}]}


def test_stage4_lexicon_true_zero_keyed_tokens_fails_loudly(tmp_path, monkeypatch):
    monkeypatch.setattr(stage4_morphology, "BUILD_DIR", tmp_path)
    (tmp_path / "stage3").mkdir()
    (tmp_path / "stage3" / "tokens.json").write_text(json.dumps(_empty_tokens_doc()))

    data = _bekker_manifest_data({"language": "lat", "id": "TSTLAT", "lexicon": True})
    manifest = Manifest(data, Path("TSTLAT.yaml"))

    with pytest.raises(ValueError, match="zero keyed tokens"):
        stage4_morphology.run(manifest)


def test_stage4_lexicon_false_zero_keyed_tokens_is_the_legitimate_no_op(tmp_path, monkeypatch):
    # The exact same empty-artifact shape as above, but declared
    # `lexicon: false` — must NOT raise (this is what a real no-lexicon
    # work's stage3 output legitimately looks like).
    monkeypatch.setattr(stage4_morphology, "BUILD_DIR", tmp_path)
    (tmp_path / "stage3").mkdir()
    (tmp_path / "stage3" / "tokens.json").write_text(json.dumps(_empty_tokens_doc()))

    data = _bekker_manifest_data({"language": "lat", "id": "TSTLAT", "lexicon": False})
    manifest = Manifest(data, Path("TSTLAT.yaml"))

    out = stage4_morphology.run(manifest)
    summary = json.loads((tmp_path / "stage4" / "summary.json").read_text())
    assert summary["token_match_rate"] is None
    assert json.loads(out.read_text()) == {}


def test_stage5_lexicon_true_zero_lemmata_fails_loudly(tmp_path, monkeypatch):
    monkeypatch.setattr(stage5_lsj, "BUILD_DIR", tmp_path)
    (tmp_path / "stage4").mkdir()
    (tmp_path / "stage4" / "analyses.json").write_text("{}")

    data = _bekker_manifest_data({"language": "grc", "lexicon": True})
    manifest = Manifest(data, Path("VAL.yaml"))

    with pytest.raises(ValueError, match="zero lemmata"):
        stage5_lsj.run(manifest)
