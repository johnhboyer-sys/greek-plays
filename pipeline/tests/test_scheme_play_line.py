"""play-line citation scheme (P1, the Greek drama corpus — docs/p1-probe.md):
grammar, order key, parse-time normalization, transposition derivation,
strophe/speaker classification, and antilabe offsets, on a small synthetic
export fixture (real-export coverage is Agamemnon, verified separately by
the `all --work agamemnon --public` pipeline run)."""

import hashlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

from drama_pipeline import scheme as scheme_mod
from drama_pipeline import stage1_greek
from drama_pipeline.config import Manifest

FIX = Path(__file__).resolve().parent / "fixtures" / "play_line"


# ── Scheme registration + grammar ────────────────────────────────────────

def test_registered_scheme_shape():
    s = scheme_mod.get("play-line")
    assert s.name == "play-line"
    assert s.lines_user_facing is True
    assert s.validation_mode == "observed"
    assert s.has_sections is False
    assert s.play_line_scheme is True
    # Every other scheme's own discriminator must stay False for it.
    assert s.verse_line_scheme is False
    assert s.fragment_scheme is False
    assert s.flat_numeric is False


@pytest.mark.parametrize("ref", ["1", "1234", "47a", "106-107", "post 1226"])
def test_ref_grammar_accepts(ref):
    assert scheme_mod.get("play-line").column_re.match(ref)


@pytest.mark.parametrize(
    "bad", ["", "1.101", "47A", "106--107", "post1226", "post  1226", " 1", "1 ", "-1", "1-"]
)
def test_ref_grammar_rejects(bad):
    assert not scheme_mod.get("play-line").column_re.match(bad)


def test_play_line_kind():
    assert scheme_mod.play_line_kind("1234") == "line"
    assert scheme_mod.play_line_kind("47a") == "line"
    assert scheme_mod.play_line_kind("106-107") == "range"
    assert scheme_mod.play_line_kind("post 1226") == "post"
    with pytest.raises(ValueError):
        scheme_mod.play_line_kind("not-a-ref")


# ── Order key (docs/p1-probe.md's frozen rule) ───────────────────────────

def test_order_key_plain_and_suffix():
    assert scheme_mod.play_line_order_key("47") == (47, 0, "")
    assert scheme_mod.play_line_order_key("47a") == (47, 0, "a")
    # leading integer dominates; suffix sorts after the plain line of the
    # same number, never lexicographically across numbers.
    assert scheme_mod.play_line_order_key("47") < scheme_mod.play_line_order_key("47a")
    assert scheme_mod.play_line_order_key("47a") < scheme_mod.play_line_order_key("48")
    assert scheme_mod.play_line_order_key("9") < scheme_mod.play_line_order_key("10")


def test_order_key_range_sorts_at_start():
    assert scheme_mod.play_line_order_key("106-107") == (106, 0, "")


def test_order_key_post_sorts_after_n():
    assert scheme_mod.play_line_order_key("post 1226") == (1226, 1, "")
    assert scheme_mod.play_line_order_key("1226") < scheme_mod.play_line_order_key("post 1226")
    assert scheme_mod.play_line_order_key("post 1226") < scheme_mod.play_line_order_key("1227")


# ── Parse-time normalization (stage1_greek._normalize_play_lineref) ──────

def test_normalize_post_and_slash_range():
    assert stage1_greek._normalize_play_lineref("post1226") == "post 1226"
    assert stage1_greek._normalize_play_lineref("post 1226") == "post 1226"
    assert stage1_greek._normalize_play_lineref("289/290") == "289-290"
    assert stage1_greek._normalize_play_lineref("47a") == "47a"
    assert stage1_greek._normalize_play_lineref("1234") == "1234"


def test_normalize_then_grammar_parity():
    """Every normalized token must satisfy the grammar it feeds — a parity
    check that the two steps agree (normalize, then classify)."""
    for raw, expected_kind in [("post1226", "post"), ("289/290", "range"), ("47a", "line")]:
        normalized = stage1_greek._normalize_play_lineref(raw)
        assert scheme_mod.play_line_kind(normalized) == expected_kind


# ── Transposition derivation ──────────────────────────────────────────────

def test_derive_transposed_blocks_agamemnon_shape():
    """The exact shape measured against the real Agamemnon export
    (docs/p1-probe.md): line 1290 is printed one position early, so the
    ascending run 1284-1289 sits below the running max 1290 set one ref
    earlier — the algorithm attributes the anomaly to that run, not to
    "1290" itself (see stage1_greek.py's own doc comment on this)."""
    refs = [str(n) for n in range(1280, 1284)] + ["1290"] + [str(n) for n in range(1284, 1292)]
    blocks = stage1_greek._derive_play_line_transposed_blocks(refs)
    assert blocks == [{"start": "1284", "end": "1289", "before": "1290"}]


def test_derive_transposed_blocks_single_swap():
    refs = ["1", "2", "3", "5", "4", "6"]
    blocks = stage1_greek._derive_play_line_transposed_blocks(refs)
    assert blocks == [{"start": "4", "end": "4", "before": "5"}]


def test_derive_transposed_blocks_none():
    refs = [str(n) for n in range(1, 11)]
    assert stage1_greek._derive_play_line_transposed_blocks(refs) == []


def test_derive_transposed_blocks_range_sorts_at_start():
    """A declared range token participates in the scan at its START number
    (the same convention as an ordinary line)."""
    refs = ["1", "2", "5", "3-4", "6"]
    blocks = stage1_greek._derive_play_line_transposed_blocks(refs)
    assert blocks == [{"start": "3-4", "end": "3-4", "before": "5"}]


# ── Strophe classification ────────────────────────────────────────────────

@pytest.mark.parametrize(
    "label", ["[στρ. α.", "[ἀντ. β.", "[ἐπῳδ.", "[μεσῳδ.", "[ἐφυμν. γ", "[ἐφ. γ.",
              "Str. 1.", "Ant. 2.", "στρ.", "ἀντ."],
)
def test_strophe_regex_matches(label):
    assert stage1_greek._PLAY_LINE_STROPHE_RE.match(label)


@pytest.mark.parametrize("label", ["Χο.", "ΚΛΥΤΑΙΜΗΣΤΡΑ", "—", "Αγ.", "1."])
def test_strophe_regex_rejects_speakers(label):
    assert not stage1_greek._PLAY_LINE_STROPHE_RE.match(label)


def test_malformed_strophe_speaker_split():
    m = stage1_greek._PLAY_LINE_MALFORMED_RE.match("[ἀντ. α. Αν.")
    assert m
    assert m.group("strophe") == "[ἀντ. α."
    assert m.group("speaker") == "Αν."


def test_malformed_regex_does_not_fire_on_ordinary_strophe_labels():
    """Regression: an early draft of this regex mis-split "[στρ. α." itself
    (treating the marker's own stanza-number letter as a phantom speaker) —
    verified against the real Agamemnon export, which has ~50 ordinary
    two-token strophe labels and zero genuine occurrences of the malformed
    glued form."""
    for label in ["[στρ. α.", "[ἀντ. β.", "[στρ. δ.", "[ἐφυμν. α", "[ἐφ. γ."]:
        assert not stage1_greek._PLAY_LINE_MALFORMED_RE.match(label)


def test_normalize_strophe_label_strips_leading_bracket_only():
    assert stage1_greek._normalize_strophe_label("[στρ. α.") == "στρ. α."
    assert stage1_greek._normalize_strophe_label("Str. 1.") == "Str. 1."
    assert stage1_greek._normalize_strophe_label("στρ.") == "στρ."


# ── Antilabe offsets + strophe/speaker separation (6-line synthetic fixture) ──

def _fixture_manifest():
    title_hash = hashlib.sha256("ΤΕΣΤ".encode("utf-8")).hexdigest()[:16]
    data = {
        "work": {
            "id": "testplay", "title": "Test Play", "author": "nobody",
            "language": "grc", "tlg_author": "0000", "tlg_work": "000",
            "greek_edition": "Nobody",
        },
        "citation": {
            "scheme": "play-line",
            "lacunae": {"1": ["post 6"]},
            "transpositions": {"1": []},
            "title_labels": [{"sha256_16": title_hash, "note": "test title"}],
        },
    }
    return Manifest(data, Path("testplay.yaml"))


def _fixture_spine():
    manifest = _fixture_manifest()
    sch = scheme_mod.for_manifest(manifest)
    return stage1_greek._parse_spine_play(FIX / "synthetic6.xml", manifest, sch)


def test_fixture_title_drop_and_line_count():
    spine = _fixture_spine()
    n_lines = sum(len(s["lines"]) for s in spine["segments"])
    assert n_lines == 5  # the title line (n="t") is dropped, never counted


def test_fixture_antilabe_offsets():
    """A genuine mid-line speaker change (two real speakers on one physical
    line, l n="2": "Α. ἰδού. Β. παπαιάξ.") — the first speaker's offset is
    0 (line start), the second's offset lands exactly on its own speech's
    first character, after the first speech's text and the collapsed
    inter-speaker space."""
    spine = _fixture_spine()
    seg = next(s for s in spine["segments"] if s["id"] == "1:2")
    speakers = seg["speakers"]
    assert speakers[0] == {"line": 2, "offset": 0, "label": "Α."}
    assert speakers[1]["label"] == "Β."
    line2 = next(l for l in seg["lines"] if l["n"] == 2)
    assert line2["text"][speakers[1]["offset"]:].startswith("παπαιάξ")


def test_fixture_strophe_label_and_speaker_coexist():
    """l n="5" carries BOTH a real speaker (Χο.) at line start AND a
    trailing strophe marker on the SAME physical line — the strophe marker
    must be lifted into `label`, never counted as a second speaker."""
    spine = _fixture_spine()
    seg = next(s for s in spine["segments"] if s["id"] == "1:5")
    assert len(seg["speakers"]) == 1
    assert seg["speakers"][0] == {"line": 4, "offset": 0, "label": "Χο."}
    line = seg["lines"][0]
    assert line["label"] == "στρ. α."
    assert "στρ" not in line["text"]


def test_fixture_range_token_has_no_speaker_and_stays_citable():
    spine = _fixture_spine()
    seg = next(s for s in spine["segments"] if s["id"] == "1:2")
    range_line = next(l for l in seg["lines"] if l["ref"] == "3-4")
    assert "role" not in range_line


def test_fixture_lacuna_line_is_empty_and_keeps_its_speaker():
    spine = _fixture_spine()
    seg = next(s for s in spine["segments"] if s["id"] == "1:post 6")
    line = seg["lines"][0]
    assert line["role"] == "lacuna"
    assert line["text"] == ""
    assert seg["speakers"] == [{"line": 5, "offset": 0, "label": "Γ."}]


# ── TS<->Python regex-SOURCE parity ───────────────────────────────────────

def test_ts_python_regex_source_parity():
    """scheme.py's PLAY_LINE_REF_SOURCE and citation.ts's own copy must be
    byte-identical strings (not just behaviorally equivalent) — mirrors
    CPR's `_FLAT_COLUMN_RE` cross-language parity convention. Reads the TS
    file as text rather than importing it (no JS runtime in pytest)."""
    ts_path = ROOT / "shared" / "lib" / "citation.ts"
    ts_source = ts_path.read_text(encoding="utf-8")
    m = __import__("re").search(
        r"export const PLAY_LINE_REF_SOURCE = '([^']+)';", ts_source
    )
    assert m, "citation.ts must declare PLAY_LINE_REF_SOURCE as a plain string literal"
    ts_value = m.group(1)
    py_value = scheme_mod.PLAY_LINE_REF_SOURCE
    assert ts_value == py_value
    assert py_value == r"^[0-9]+$|^[0-9]+[a-z]$|^[0-9]+-[0-9]+$|^post [0-9]+$"
