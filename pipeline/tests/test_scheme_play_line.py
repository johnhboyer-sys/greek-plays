"""play-line citation scheme (P1, the Greek drama corpus — docs/p1-probe.md):
grammar, order key, parse-time normalization, transposition derivation,
strophe/speaker classification, and antilabe offsets, on a small synthetic
export fixture (real-export coverage is Agamemnon, verified separately by
the `all --work agamemnon --public` pipeline run)."""

import hashlib
import json
import sys
from pathlib import Path

import pytest
from lxml import etree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

from drama_pipeline import scheme as scheme_mod
from drama_pipeline import preflight, stage1_greek, stage7_emit
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


@pytest.mark.parametrize("bad", ["107-106", "106-106", "1000-999"])
def test_play_line_kind_rejects_reversed_or_empty_range(bad):
    # Sol review 2026-09-05, item 8: the grammar admits any two integers, but
    # a range whose end is not after its start can never resolve an interior
    # number, and the order key would sort on the wrong endpoint. Loud.
    assert scheme_mod.get("play-line").column_re.match(bad)  # grammar alone admits it
    with pytest.raises(ValueError):
        scheme_mod.play_line_kind(bad)


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
              "Str. 1.", "Ant. 2.", "στρ.", "ἀντ.",
              # Persians 673/899/1066: Murray spells the epode marker out in
              # full ("[ἐπῳδός.") rather than abbreviating it -- the bare
              # "ἐπῳδ" alternative's \b fails right after "δ" since "ός"
              # continues the word, so the inflected form is its own
              # alternative (P2-Greek, docs/p2-greek-report.md).
              "[ἐπῳδός."],
)
def test_strophe_regex_matches(label):
    assert stage1_greek._PLAY_LINE_STROPHE_RE.match(label)


@pytest.mark.parametrize(
    "label",
    ["Χο.", "ΚΛΥΤΑΙΜΗΣΤΡΑ", "—", "Αγ.", "1.",
     # Sol review 2026-09-05, item 9: a capitalised siglum sharing the
     # marker's letters is a SPEAKER (Strophius), never a strophe mark — the
     # regex is case-sensitive, so neither the Greek nor the Latin fold fires.
     "Στρ.", "ΣΤΡ.", "STR.", "ANT.", "Ἀντ."],
)
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
        "speakers": {"sigla": {
            "ΑΛΦΑ": "Alpha", "Α.": "Alpha", "Β.": "Beta",
            "Χο.": "Chorus", "Γ.": "Gamma", "—": None,
        }},
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


def test_parse_rejects_repeated_play_line_ref():
    tree = etree.parse(str(FIX / "synthetic6.xml"))
    duplicate = tree.xpath(".//*[local-name()='l'][@n='3-4']")[0]
    duplicate.set("n", "2")
    manifest = _fixture_manifest()
    with pytest.raises(ValueError, match=r"repeated play-line ref '2'"):
        stage1_greek._parse_play(
            tree, scheme_mod.for_manifest(manifest), manifest, "duplicate.xml"
        )


def test_parse_rejects_stale_declared_title_hash():
    tree = etree.parse(str(FIX / "synthetic6.xml"))
    manifest = _fixture_manifest()
    stale_hash = "0123456789abcdef"
    manifest.data["citation"]["title_labels"].append(
        {"sha256_16": stale_hash, "note": "stale title"}
    )
    with pytest.raises(ValueError, match=stale_hash):
        stage1_greek._parse_play(
            tree, scheme_mod.for_manifest(manifest), manifest, "stale-title.xml"
        )


def test_dist_preflight_rejects_repeated_play_line_ref():
    data = {
        "citation": {"fingerprint": {"count": 2, "sha256": "unused"}},
        "books": [{"n": 1}],
    }
    manifest = preflight.WorkManifest("testplay", Path("testplay.yaml"), data)
    loaded = {"book-01.json": {"segments": [
        {"id": "1:1", "greek": [{"n": 1, "ref": "1", "tokens": []}]},
        {"id": "1:1-again", "greek": [{"n": 2, "ref": "1", "tokens": []}]},
    ]}}
    problems = []
    preflight._validate_play_line_work(
        manifest, loaded, problems, scheme_mod.get("play-line")
    )
    assert any("repeated play-line ref '1'" in problem for _, _, problem in problems)


def _transposition_manifest(*, declared: bool = True) -> Manifest:
    title_hash = hashlib.sha256("ΤΕΣΤ".encode("utf-8")).hexdigest()[:16]
    citation = {
        "scheme": "play-line",
        "lacunae": {"1": []},
        "title_labels": [{"sha256_16": title_hash, "note": "test title"}],
    }
    if declared:
        citation["transpositions"] = {
            "1": [{"start": "1284", "end": "1285", "before": "1290"}]
        }
    return Manifest({
        "work": {
            "id": "transposed-play", "title": "Test Play", "author": "nobody",
            "language": "grc", "tlg_author": "0000", "tlg_work": "000",
            "greek_edition": "Nobody",
        },
        "citation": citation,
        "speakers": {"sigla": {"—": None}},
    }, Path("transposed-play.yaml"))


def test_transposed_fixture_emits_printed_order_and_no_seam_note(tmp_path):
    manifest = _transposition_manifest()
    sch = scheme_mod.for_manifest(manifest)
    spine = stage1_greek._parse_spine_play(
        FIX / "synthetic_transposition.xml", manifest, sch
    )
    spine["segments"][0]["lines"][0]["seam_note"] = "must not ship"
    tokens = {"segments": [
        {"id": seg["id"], "lines": [{"tokens": []} for _ in seg["lines"]]}
        for seg in spine["segments"]
    ]}
    stage7_emit.emit_books(
        spine, tokens, {"chunks": []}, {}, tmp_path, scheme=sch
    )
    book = json.loads((tmp_path / "book-01.json").read_text(encoding="utf-8"))
    lines = [line for seg in book["segments"] for line in seg["greek"]]
    assert [line["ref"] for line in lines] == ["1283", "1290", "1284", "1285", "1291"]
    assert all("seamNote" not in line for line in lines)


def test_transposition_declaration_remains_required():
    manifest = _transposition_manifest(declared=False)
    with pytest.raises(ValueError, match=r"citation\.transpositions\['1'\] is required"):
        stage1_greek._parse_spine_play(
            FIX / "synthetic_transposition.xml",
            manifest,
            scheme_mod.for_manifest(manifest),
        )


def test_play_line_speaker_events_are_canonical_and_roster_is_first_appearance(tmp_path):
    manifest = _fixture_manifest()
    spine = _fixture_spine()
    rosters = stage7_emit._canonicalize_play_line_speakers(spine, manifest)
    assert rosters == {1: ["Alpha", "Beta", "Chorus", "Gamma"]}

    tokens = {"segments": [
        {"id": seg["id"], "lines": [{"tokens": []} for _ in seg["lines"]]}
        for seg in spine["segments"]
    ]}
    stage7_emit.emit_books(
        spine, tokens, {"chunks": []}, {}, tmp_path,
        scheme=scheme_mod.for_manifest(manifest), speaker_rosters=rosters,
    )
    book = json.loads((tmp_path / "book-01.json").read_text(encoding="utf-8"))
    assert book["speakerRoster"] == ["Alpha", "Beta", "Chorus", "Gamma"]
    events = [event for seg in book["segments"] for event in seg.get("speakers", [])]
    assert [(event["label"], event["display"]) for event in events] == [
        ("ΑΛΦΑ", "Alpha"), ("Α.", "Alpha"), ("Β.", "Beta"),
        ("Χο.", "Chorus"), ("Γ.", "Gamma"),
    ]


def test_play_line_speaker_map_is_required_and_unmapped_siglum_fails():
    missing = _fixture_manifest()
    del missing.data["speakers"]
    with pytest.raises(RuntimeError, match=r"speakers\.sigla is required"):
        stage7_emit._canonicalize_play_line_speakers(_fixture_spine(), missing)

    unmapped = _fixture_manifest()
    del unmapped.data["speakers"]["sigla"]["Β."]
    with pytest.raises(RuntimeError, match=r"testplay.*1:2.*Β\."):
        stage7_emit._canonicalize_play_line_speakers(_fixture_spine(), unmapped)


def test_play_line_manifest_preflight_requires_speaker_map():
    data = {
        "work": {"id": "testplay", "no_english": True},
        "citation": {"scheme": "play-line"},
        "books": [{"n": 1, "start": "1", "end": "6"}],
    }
    manifest = preflight.WorkManifest("testplay", Path("testplay.yaml"), data)
    problems = []
    preflight._validate_section_manifest_schema(
        manifest, problems, scheme_mod.get("play-line")
    )
    assert any(
        problem == "speakers must be an object for a play-line work"
        for _, _, problem in problems
    )


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


# ── Repeated printed refs (John's ruling 2026-09-06, REVIEW-CHECKLIST 3) ──

def _play_xml(refs_and_text):
    body = "".join(f'<l n="{n}">{t}</l>' for n, t in refs_and_text)
    return etree.fromstring(
        f'<TEI><text><body><l n="t"><label type="head">ΤΙΤΛΟΣ</label></l>{body}</body></text></TEI>'
    )


class _M:
    def __init__(self, citation):
        self.data = {"citation": citation}
        self.work_id = "t"


def _title_decl():
    h = stage1_greek._flat_title_content_hash("ΤΙΤΛΟΣ")
    return [{"sha256_16": h, "note": "t"}]


def test_repeated_ref_fails_undeclared():
    tree = _play_xml([("1", "α"), ("2", "β"), ("2", "γ")])
    m = _M({"title_labels": _title_decl(), "transpositions": {"1": []}})
    with pytest.raises(ValueError, match="repeated play-line ref '2'"):
        stage1_greek._parse_play(tree, scheme_mod.get("play-line"), m)


def test_repeated_ref_declared_passes_and_keeps_both_lines():
    tree = _play_xml([("1", "α"), ("2", "β"), ("2", "γ"), ("3", "δ")])
    m = _M({"title_labels": _title_decl(), "transpositions": {"1": []},
            "repeated_refs": {"1": [{"ref": "2", "count": 2, "note": "doublet"}]}})
    flat = stage1_greek._parse_play(tree, scheme_mod.get("play-line"), m)
    assert [e["ref"] for e in flat] == ["1", "2", "2", "3"]


def test_repeated_ref_declared_count_mismatch_fails():
    tree = _play_xml([("1", "α"), ("2", "β"), ("3", "δ")])
    m = _M({"title_labels": _title_decl(), "transpositions": {"1": []},
            "repeated_refs": {"1": [{"ref": "2", "count": 2}]}})
    with pytest.raises(ValueError, match="declares '2' x2 but the export prints it x1"):
        stage1_greek._parse_play(tree, scheme_mod.get("play-line"), m)


# ── Speaker sigla: normalization + range overrides (stage7) ──────────────

def test_norm_siglum_strips_editorial_noise():
    assert stage7_emit._norm_siglum("<Ηρ.>") == "Ηρ"
    assert stage7_emit._norm_siglum("[Αμ.") == "Αμ"
    assert stage7_emit._norm_siglum("(Ηλ.)") == "Ηλ"
    assert stage7_emit._norm_siglum("Ιων") == stage7_emit._norm_siglum("Ιων.")
    assert stage7_emit._norm_siglum("Χο.α") == "Χο.α"


def test_play_line_display_override_by_ref():
    sigla = {stage7_emit._norm_siglum(k): v for k, v in {"ΑΓ.": "Messenger", "—": None}.items()}
    ov = [("ΑΓ", scheme_mod.play_line_order_key("1226"), "Agamemnon")]
    assert stage7_emit._play_line_display("ΑΓ.", sigla, ov, "718") == ("Messenger", True)
    assert stage7_emit._play_line_display("ΑΓ.", sigla, ov, "1226") == ("Agamemnon", True)
    assert stage7_emit._play_line_display("ΑΓ.", sigla, ov, "1300") == ("Agamemnon", True)
    assert stage7_emit._play_line_display("<ΑΓ.>", sigla, ov, "10") == ("Messenger", True)
    assert stage7_emit._play_line_display("—", sigla, ov, "10") == (None, True)
    assert stage7_emit._play_line_display("ΞΕ.", sigla, ov, "10") == ("ΞΕ.", False)


def test_strophe_regex_epod_form():
    assert stage1_greek._PLAY_LINE_STROPHE_RE.match("Epod.")


def test_norm_siglum_folds_prime_variants():
    assert stage7_emit._norm_siglum("ΗΜΙΧΟΡΙΟΝ Α\u0374") == stage7_emit._norm_siglum("ΗΜΙΧΟΡΙΟΝ Α\u02b9")
    assert stage7_emit._norm_siglum("Α\u2032") == stage7_emit._norm_siglum("Α\u02b9")


def test_lacuna_only_segments_need_no_declared_gap():
    from drama_pipeline import stage2_validate
    segs = [
        {"id": "1:post 146", "lines": [{"ref": "post 146", "text": "", "role": "lacuna"}]},
        {"id": "1:147", "lines": [{"ref": "147", "text": "x"}, {"ref": "post 148", "text": "", "role": "lacuna"}]},
        {"id": "1:empty", "lines": []},
        {"id": "1:post 1", "lines": [{"ref": "post 1", "text": "not empty", "role": "lacuna"}]},
    ]
    assert stage2_validate._play_line_lacuna_segment_ids(segs) == {"1:post 146"}


def test_play_line_twin_segment_ids():
    from drama_pipeline import stage2_validate
    segs = [
        {"id": "1:803", "lines": [{"ref": "803", "text": "a"}]},
        {"id": "1:803.2", "lines": [{"ref": "803", "text": "b"}]},
        {"id": "1:843a", "lines": [{"ref": "843a", "text": "c"}]},
        {"id": "1:843b", "lines": [{"ref": "843b", "text": "d"}]},
        {"id": "1:1270", "lines": [{"ref": "1270", "text": "e"}]},
        {"id": "1:1270a", "lines": [{"ref": "1270a", "text": "f"}]},
        {"id": "1:47a", "lines": [{"ref": "47a", "text": "g"}]},
        {"id": "1:107", "lines": [{"ref": "107", "text": "h"}]},
        {"id": "1:106-107", "lines": [{"ref": "106-107", "text": "i"}]},
    ]
    assert stage2_validate._play_line_twin_segment_ids(segs) == {
        "1:803.2",
        "1:843b",
        "1:1270a",
    }


def test_lacuna_auto_allow_through_validate_requires_empty_text():
    from drama_pipeline import stage2_validate

    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1, "ref": "1", "text": "g"}],
            },
            {
                "id": "1:post 1226",
                "book": 1,
                "column": "1",
                "lines": [{"n": 2, "ref": "post 1226", "text": "", "role": "lacuna"}],
            },
            {
                "id": "1:post 1226.2",
                "book": 1,
                "column": "1",
                "lines": [{"n": 3, "ref": "post 1226", "text": "", "role": "lacuna"}],
            },
            {
                "id": "1:10",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": 4, "ref": "10", "text": "mixed text", "role": "lacuna"}
                ],
            },
        ],
    }
    english = {
        "chunks": [{"id": "1:1", "column": "1", "text": "Alpha text here for length."}]
    }
    alignment = {
        "pairs": [
            {"segment": "1:1", "english": "1:1"},
            {"segment": "1:post 1226", "english": None},
            {"segment": "1:post 1226.2", "english": None},
            {"segment": "1:10", "english": None},
        ],
        "english_only": [],
    }
    manifest = Manifest(
        {
            "work": {"id": "test-play", "title": "Test", "author": "aeschylus"},
            "citation": {"scheme": "play-line"},
            "books": [{"n": 1, "start": "1", "end": "10"}],
            "english": {
                "primary": {
                    "id": "smyth",
                    "name": "Smyth",
                    "model": "perseus-play",
                },
                "gaps": [],
            },
            "proper_names": [],
        },
        Path("test-play.yaml"),
    )
    report = stage2_validate.validate(manifest, spine, english, alignment)
    unexpected = report["checks"]["alignment"]["unexpected_unmatched"]
    assert "1:post 1226" not in unexpected
    assert "1:post 1226.2" not in unexpected
    assert "1:10" in unexpected
    assert report["checks"]["alignment"]["ok"] is False


def test_missing_title_line_is_fine_when_none_declared(tmp_path):
    """The comedies' exports carry no <l n="t"> line (Coulon, Dover, MacDowell,
    Ussher); a manifest that declares no title_labels must parse them."""
    xml = tmp_path / "play.xml"
    xml.write_text('<TEI><text><body><l n="1"><label type="speaker">ΔΙ.</label> ὅσα δὴ δέδηγμαι</l><l n="2">τὴν ἐμαυτοῦ καρδίαν</l></body></text></TEI>')
    m = Manifest({"work": {"id": "x"}, "citation": {"scheme": "play-line", "title_labels": [], "transpositions": {"1": []}, "lacunae": {"1": []}}, "speakers": {"sigla": {"ΔΙ.": "Dicaeopolis"}}}, tmp_path / "x.yaml")
    tree = etree.parse(str(xml))
    flat = stage1_greek._parse_play(tree, scheme_mod.get("play-line"), m, str(xml))
    assert [e["ref"] for e in flat] == ["1", "2"]


def test_turn_text_floor_ignores_another_plays_report(tmp_path, monkeypatch):
    """The pairing-rate floor reads the single-work scratch report; a report
    written by a different play must not authorise this one, and its absence
    must not open the gate either (P2g finding 11)."""
    from drama_pipeline import stage2_validate
    stage1 = tmp_path / "stage1"; stage1.mkdir()
    (stage1 / "english_report.json").write_text(json.dumps({"work": "frogs", "pairing_rate": 0.99}))
    monkeypatch.setattr(stage2_validate, "BUILD_DIR", tmp_path)
    data, error = stage2_validate._stage1_english_report("lysistrata")
    assert data is None
    assert "not 'lysistrata'" in error
    assert stage2_validate._stage1_english_report("frogs")[0]["pairing_rate"] == 0.99

    monkeypatch.setattr(stage2_validate, "BUILD_DIR", tmp_path / "elsewhere")
    assert stage2_validate._stage1_english_report("frogs") == (
        None,
        f"no stage1 English report at {tmp_path / 'elsewhere' / 'stage1' / 'english_report.json'}",
    )


def test_preflight_accepts_a_turn_text_primary_on_a_play_line_work():
    """The comedies' primaries are turn-text with `source` + `play`
    (stage1_turn_english), not perseus-play with `file`. Corpus preflight
    refused all eleven at the first full build:public after P3 (2026-09-08);
    it now takes either play-line model, and still refuses a typo."""
    from drama_pipeline import preflight

    def problems_for(model: str, **extra: str) -> list[str]:
        data = {
            "work": {"id": "test-play", "title": "Test", "author": "aristophanes", "tlg_author": "0019", "tlg_work": "009"},
            "citation": {"scheme": "play-line", "fingerprint": {"count": 1, "sha256": "x"}},
            "books": [{"n": 1, "start": "1", "end": "10"}],
            "english": {"primary": {"id": "athenian-society", "name": "The Eleven Comedies", "model": model, **extra}, "gaps": []},
            "proper_names": [],
        }
        manifest = preflight.WorkManifest("test-play", Path("test-play.yaml"), data)
        out: list = []
        preflight._validate_manifest_schema(manifest, out)
        return [p[2] for p in out if "english.primary" in p[2]]

    assert problems_for("turn-text", source="gutenberg/pg8689.txt", play="THE FROGS") == []
    assert any("not a recognized model" in p for p in problems_for("turn-txt", source="gutenberg/pg8689.txt"))
    assert any("english.primary.source must be a non-empty string" in p for p in problems_for("turn-text"))
