import json
import re
from pathlib import Path

import pytest
from lxml import etree

from drama_pipeline.config import Manifest
from drama_pipeline.stage1_perseus_play_english import (
    _iter_speech_slices,
    _LineText,
    parse_translation,
)
from drama_pipeline.stage1_turn_english import _SiglaResolver
from drama_pipeline.stage2_validate import validate
from drama_pipeline.stage7_emit import (
    _manifest_v1_fields,
    _play_line_english_roster_gate,
    chapter_ranges,
    emit_books,
)


TEI = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker>
      <l n="0">Alpha</l>
      <l n="1">First <del>cut me</del> text<note n="1" resp="Smyth">One <q>note</q>.</note>.</l>
    </sp>
    <sp><speaker>Beta</speaker>
      <l n="5">Second text.</l>
      <l n="7">Snapped text<note n="1" resp="Smyth">Another note.</note>.</l>
    </sp>
    <sp><speaker>Gamma</speaker><l n="10">Third text.</l></sp>
  </div>
</body></text></TEI>
"""

ALIASES = {"Alpha": "Alpha", "Beta": "Beta", "Gamma": "Gamma"}
SIGLA = {"A": "Alpha", "B": "Beta", "G": "Gamma"}


def _spine() -> dict:
    return {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1",
                "book": 1,
                "column": "1",
                "lines": [{"n": n, "ref": str(n), "text": f"g{n}"} for n in range(1, 5)],
                "speakers": [{"line": 1, "offset": 0, "label": "A"}],
            },
            {
                "id": "1:5",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": n, "ref": str(n), "text": f"g{n}"} for n in (5, 6, 8)
                ],
                "speakers": [{"line": 1, "offset": 0, "label": "B"}],
            },
            {
                "id": "1:10",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": n, "ref": str(n), "text": f"g{n}"} for n in range(10, 13)
                ],
                "speakers": [{"line": 10, "offset": 0, "label": "G"}],
            },
        ],
    }


def _parse(
    tmp_path: Path, tei: str, spine: dict, *, aliases=None, sigla=None, covered=None,
    transpositions=None, line_fixes=None, repeated_refs=None, cuts=None,
):
    xml_path = tmp_path / "play.xml"
    xml_path.write_text(tei, encoding="utf-8")
    return parse_translation(
        xml_path,
        spine,
        work_id="test-play",
        translation_id="smyth",
        sigla=sigla if sigla is not None else SIGLA,
        english_aliases=aliases if aliases is not None else ALIASES,
        covered_decl=covered,
        transpositions=transpositions,
        line_fixes=line_fixes,
        cuts=cuts,
        repeated_refs=repeated_refs,
    )


def test_primary_cut_moves_numbered_line_tail_to_greek_ref(tmp_path: Path):
    tei = '<TEI><div type="translation"><sp><speaker>Alpha</speaker><l n="1">First words. New speech starts here.</l></sp></div></TEI>'
    english, _notes, _report = _parse(
        tmp_path, tei, _spine(), cuts=[{"greek": "5", "english": "New speech"}],
    )
    chunks = {chunk["id"]: chunk["text"] for chunk in english["chunks"]}
    assert chunks["1:1"] == "First words."
    assert chunks["1:5"] == "New speech starts here."


def test_primary_cut_rejects_stale_words_or_ref(tmp_path: Path):
    tei = '<TEI><div type="translation"><sp><speaker>Alpha</speaker><l n="1">First words. New speech starts here.</l></sp></div></TEI>'
    for ref, words in [("5", "Absent words"), ("999", "New speech")]:
        with pytest.raises(ValueError, match="test-play: stale english.primary.cuts") as error:
            _parse(tmp_path, tei, _spine(), cuts=[{"greek": ref, "english": words}])
        assert ref in str(error.value) and words in str(error.value)


def test_primary_cut_refuses_line_with_markup(tmp_path: Path):
    tei = '<TEI><div type="translation"><sp><speaker>Alpha</speaker><l n="1">First words.<note>n</note> New speech starts here.</l></sp></div></TEI>'
    with pytest.raises(ValueError, match="carries markup"):
        _parse(tmp_path, tei, _spine(), cuts=[{"greek": "5", "english": "New speech"}])


def test_comment_tail_survives_inside_line():
    """Hippolytus review finding 1 (2026-09-17): the walk returned as soon as
    it hit a comment node (no string tag) without reading the comment's
    tail, so a line with an XML comment lost everything after it."""
    speech = etree.fromstring(
        '<sp><speaker>A</speaker><l n="1">before <!-- note --> after</l></sp>'
    )
    anomalies: list[dict] = []
    slices = _iter_speech_slices(
        speech,
        split=False,
        text_parser=_LineText({}, anomalies),
        anomalies=anomalies,
        sp_index=1,
        printed="A",
    )
    assert [s.text() for s in slices] == ["before after"]
    assert anomalies == []
    # The tail stays anchored to its own line (Grok read, 2026-09-17).
    assert [n for n, _part in slices[0].pieces] == ["1"]


def test_comment_first_child_of_line_keeps_that_line():
    """A comment as the first child of a new <l> must not push its tail
    back onto the previous line."""
    speech = etree.fromstring(
        '<sp><speaker>A</speaker><l n="1">one</l><l n="2"><!-- c -->after</l></sp>'
    )
    anomalies: list[dict] = []
    slices = _iter_speech_slices(
        speech,
        split=False,
        text_parser=_LineText({}, anomalies),
        anomalies=anomalies,
        sp_index=1,
        printed="A",
    )
    assert slices[0].pieces == [("1", "one"), ("2", "after")]


def test_comment_tail_survives_nested_in_child_element():
    """Same bug, one level deeper: the comment sits inside a child element
    of the <l>, not directly inside it."""
    speech = etree.fromstring(
        "<sp><speaker>A</speaker>"
        "<l n=\"1\">before <foreign>mid <!-- x --> tail</foreign> after</l>"
        "</sp>"
    )
    anomalies: list[dict] = []
    slices = _iter_speech_slices(
        speech,
        split=False,
        text_parser=_LineText({}, anomalies),
        anomalies=anomalies,
        sp_index=1,
        printed="A",
    )
    assert [s.text() for s in slices] == ["before mid tail after"]
    assert anomalies == []


def test_manifest_covered_declarations_join_the_covered_map(tmp_path: Path):
    """REVIEW-CHECKLIST 7 (2026-09-09): a hole the span rule cannot prove but
    a reviewer confirmed sits in a neighbour's block is declared in the
    manifest and rides into english_covered_by like a computed one."""
    english, _f, _r = _parse(tmp_path, TEI, _spine(), covered=[{"greek": "10", "by": "5"}])
    assert english["english_covered_by"].get("1:10") == "1:5"
    with pytest.raises(ValueError):
        _parse(tmp_path, TEI, _spine(), covered=[{"greek": "999", "by": "5"}])


def test_perseus_play_chunks_ticks_notes_turns_and_report(tmp_path: Path):
    english, footnotes, report = _parse(tmp_path, TEI, _spine())

    assert [chunk["id"] for chunk in english["chunks"]] == ["1:1", "1:5", "1:10"]
    first, second, third = english["chunks"]
    # C13 (round 4): `<del>` is the editor's deletion — printed, bracketed,
    # never dropped.  This line asserted the drop until 2026-09-18.
    assert "[cut me]" in first["text"]
    assert [tick["n"] for tick in first["bekker"]] == [1]
    assert [tick["n"] for tick in second["bekker"]] == [5, 8]
    assert [tick["n"] for tick in third["bekker"]] == [10]
    assert all(
        tick["real"] is True
        for chunk in english["chunks"]
        for tick in chunk["bekker"]
    )

    assert list(footnotes) == ["1.1", "2.1"]
    assert "<q>note</q>" in footnotes["1.1"]
    assert "[^1.1]" in first["text"] and "[^2.1]" in second["text"]

    assert first["turns"] == [
        {"offset": 0, "speaker": "Alpha", "display": "Alpha"},
    ]
    assert second["turns"] == [
        {"offset": 0, "speaker": "Beta", "display": "Beta"},
    ]
    assert third["turns"] == [
        {"offset": 0, "speaker": "Gamma", "display": "Gamma"},
    ]

    assert report["anchor_count"] == 4
    assert report["snaps"] == [
        {
            "play": "test-play",
            "english_line": 7,
            "greek_ref": "8",
            "english_speaker": "Beta",
            "greek_speaker": "Beta",
            "snapped_to": "8",
            "segment": "1:5",
        }
    ]
    assert report["speech_mismatch_count"] == 0
    assert report["segments_with_chunk"] == 3
    assert report["segments_total"] == 3
    assert report["coverage_ratio"] == 1.0
    assert report["speakers"]["only_in_english"] == []


def test_one_line_drift_on_a_crowded_seat_binds_to_the_right_speaker(
    tmp_path: Path,
):
    """The Agamemnon 1077 contract, restored (S3, Lane C round 3).  Smyth's
    ``<l n="1077">`` is the Chorus answering Cassandra, and the Greek seat it
    lands on ALREADY holds Cassandra's own 1076 — two English lines on one
    Greek speech — while the Chorus's own speech at 1:1078 stands empty.
    Round 1's C1 blocked every lone repair and flipped this fixture's
    assertions; the sweep then found two live corpus instances of the same
    shape (Hecuba 709, Persians 1076) that the block had broken, so the rule
    is now "a lone anchor may move when its seat already holds a DIFFERENT
    line's matching English and the speech it would move to is bare".  The
    anchor that is genuinely alone on its seat still stays put — see
    ``test_oedipus_tyrannus_625_stays_on_its_own_line``,
    ``test_lone_anchor_stays_when_its_only_co_occupant_is_its_own_antilabe_half``
    and ``test_electra_650_stays_on_its_own_line_not_the_lacuna``."""
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1076",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": 1076, "ref": "1076", "text": "k"},
                    {"n": 1077, "ref": "1077", "text": "k"},
                ],
                "speakers": [{"line": 1, "offset": 0, "label": "Κα."}],
            },
            {
                "id": "1:1078",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": 1078, "ref": "1078", "text": "ch"},
                    {"n": 1079, "ref": "1079", "text": "ch"},
                ],
                "speakers": [{"line": 1, "offset": 0, "label": "Χο."}],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Cassandra</speaker><l n="1076">Woe.</l></sp>
    <sp><speaker>Chorus</speaker><l n="1077">Once more she cries.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Cassandra": "Cassandra", "Chorus": "Chorus"},
        sigla={"Κα.": "Cassandra", "Χο.": "Chorus"},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert by_id["1:1076"]["text"] == "Woe."
    assert by_id["1:1078"]["text"] == "Once more she cries."
    assert report["speech_mismatches"]
    mismatch = report["speech_mismatches"][0]
    assert mismatch["english_line"] == 1077
    assert mismatch["english_speaker"] == "Chorus"
    assert mismatch["greek_speaker"] == "Cassandra"
    assert mismatch["attached_to"] == "1:1078"
    assert mismatch["kind"] == "speaker_repair"
    # P2g finding 10: the tick names a line the TARGET segment prints.
    assert mismatch["attached_ref"] == "1078"
    assert report["speech_mismatch_count"] == 1
    assert report["unresolved_mismatch_count"] == 0
    assert report["attribution_differences"] == []


def test_oedipus_tyrannus_625_stays_on_its_own_line(tmp_path: Path):
    """Real corpus instance (C1, oedipus-tyrannus finding 1): Jebb's English
    ``<l n="625">`` is Creon's line by his own edition's reckoning, but the
    spine (Dain–Mazon) gives printed line 625 to Oedipus.  Before C1 this
    isolated disagreement drift-repaired onto 1:624 (Creon's own,
    un-anchored line) because Creon also speaks there within ±3 — leaving
    625 bare and 624 wrongly filled.  It must instead stay at 1:625,
    flagged."""
    spine = {
        "work": "oedipus-tyrannus",
        "segments": [
            {
                "id": "1:623",
                "book": 1,
                "column": "623",
                "lines": [{"n": 623, "ref": "623", "text": "g"}],
                "speakers": [{"line": 623, "offset": 0, "label": "ΟΙ."}],
            },
            {
                "id": "1:624",
                "book": 1,
                "column": "624",
                "lines": [{"n": 624, "ref": "624", "text": "g"}],
                "speakers": [{"line": 624, "offset": 0, "label": "ΚΡ."}],
            },
            {
                "id": "1:625",
                "book": 1,
                "column": "625",
                "lines": [{"n": 625, "ref": "625", "text": "g"}],
                "speakers": [{"line": 625, "offset": 0, "label": "ΟΙ."}],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Oedipus</speaker><l n="623">Hardly.  I desire your death.</l></sp>
    <sp><speaker>Creon</speaker><l n="625" part="I">Are you resolved not to yield or believe?</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Oedipus": "Oedipus", "Creon": "Creon"},
        sigla={"ΟΙ.": "Oedipus", "ΚΡ.": "Creon"},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert "1:624" not in by_id
    assert "Are you resolved" in by_id["1:625"]["text"]
    turn = next(t for t in by_id["1:625"]["turns"] if t["speaker"] == "Creon")
    assert turn["speakerMismatch"] == {"english": "Creon", "greek": "Oedipus"}
    mismatch = report["speech_mismatches"][0]
    assert mismatch["kind"] == "attribution_difference"
    assert mismatch["attached_to"] == "1:625"


def test_stage2_flags_a_dead_primary_covered_declaration(tmp_path: Path):
    """C1's stage2 check: once 1:625 carries its own chunk, a manifest still
    declaring ``english.primary.covered: [{greek: "625", by: "624"}]`` (the
    old oedipus-tyrannus declaration that used to mask the drift-repair bug)
    is dead.  stage2 names it for the orchestrator without failing or
    warning the build -- the stale entry is harmless at emission time."""
    spine = {
        "work": "oedipus-tyrannus",
        "segments": [
            {
                "id": "1:623",
                "book": 1,
                "column": "623",
                "lines": [{"n": 623, "ref": "623", "text": "g"}],
                "speakers": [{"line": 623, "offset": 0, "label": "ΟΙ."}],
            },
            {
                "id": "1:624",
                "book": 1,
                "column": "624",
                "lines": [{"n": 624, "ref": "624", "text": "g"}],
                "speakers": [{"line": 624, "offset": 0, "label": "ΚΡ."}],
            },
            {
                "id": "1:625",
                "book": 1,
                "column": "625",
                "lines": [{"n": 625, "ref": "625", "text": "g"}],
                "speakers": [{"line": 625, "offset": 0, "label": "ΟΙ."}],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Oedipus</speaker><l n="623">Hardly.  I desire your death.</l></sp>
    <sp><speaker>Creon</speaker><l n="625" part="I">Are you resolved not to yield or believe?</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, _report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Oedipus": "Oedipus", "Creon": "Creon"},
        sigla={"ΟΙ.": "Oedipus", "ΚΡ.": "Creon"},
    )
    alignment = _alignment_for(spine, english)
    manifest = _play_manifest(
        gaps=["1:624"], covered=[{"greek": "625", "by": "624"}]
    )
    result = validate(manifest, spine, english, alignment)
    dead = result["checks"]["primary_dead_covered"]
    assert dead["ok"] is True
    assert dead["dead"] == [{"greek": "625", "by": "624", "segment": "1:625"}]


def test_electra_650_stays_on_its_own_line_not_the_lacuna(tmp_path: Path):
    """Real corpus instance (C1 addendum, electra-eur finding 1): Diggle
    gives 650 to Orestes; Perseus's own transcription gives the English line
    to the Old Man.  Before C1 this isolated disagreement drift-repaired
    onto the ``post 651`` lacuna — whose editorial speaker label also reads
    Old Man — leaving 650 bare and the lacuna row holding a real turn.  A
    lacuna must never take a turn; 650 keeps its own English, flagged."""
    spine = {
        "work": "electra-eur",
        "segments": [
            {
                "id": "1:649",
                "book": 1,
                "column": "649",
                "lines": [{"n": 649, "ref": "649", "text": "g"}],
                "speakers": [{"line": 649, "offset": 0, "label": "Ηλ."}],
            },
            {
                "id": "1:650",
                "book": 1,
                "column": "650",
                "lines": [{"n": 650, "ref": "650", "text": "g"}],
                "speakers": [{"line": 650, "offset": 0, "label": "Ορ."}],
            },
            {
                "id": "1:post 651",
                "book": 1,
                "column": "post 651",
                "lines": [{"n": 651, "ref": "post 651", "text": "", "role": "lacuna"}],
                "speakers": [{"line": 651, "offset": 0, "label": "Πρ."}],
            },
            {
                "id": "1:651",
                "book": 1,
                "column": "651",
                "lines": [{"n": 651, "ref": "651", "text": "g"}],
                "speakers": [{"line": 651, "offset": 0, "label": "Ηλ."}],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Electra</speaker><l n="649">Let this man here help us with both.</l></sp>
    <sp><speaker>Old man</speaker><l n="650">I will; but how will you find a way to kill your mother?</l></sp>
    <sp><speaker>Electra</speaker><l n="651">Go to Clytemnestra, old man, and say this.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Electra": "Electra", "Old man": "Old Man"},
        sigla={"Ηλ.": "Electra", "Ορ.": "Orestes", "Πρ.": "Old Man"},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert "1:post 651" not in by_id
    assert "how will you find a way" in by_id["1:650"]["text"]
    turn = next(t for t in by_id["1:650"]["turns"] if t["speaker"] == "Old Man")
    assert turn["speakerMismatch"] == {"english": "Old Man", "greek": "Orestes"}


def test_electra_674_675_swap_is_not_auto_corrected(tmp_path: Path):
    """Real corpus instance (C1 addendum, electra-eur finding 5): Perseus
    gives 674 to Electra and 675 to Orestes; Diggle reverses them.  Both
    anchors keep their own place in the increasing ``<l n>`` sequence (not
    the Agamemnon 1203/1204 shape, a literal inversion in the TEI itself),
    and there are only two of them, not the three-or-more of a genuine
    multi-line drift (Seven 998–1026) — so the repair must not swap the
    lines, and the ``bekker`` marker on each must keep ITS OWN number so the
    disagreement stays detectable."""
    spine = {
        "work": "electra-eur",
        "segments": [
            {
                "id": "1:673",
                "book": 1,
                "column": "673",
                "lines": [{"n": 673, "ref": "673", "text": "g"}],
                "speakers": [{"line": 673, "offset": 0, "label": "Ηλ."}],
            },
            {
                "id": "1:674",
                "book": 1,
                "column": "674",
                "lines": [{"n": 674, "ref": "674", "text": "g"}],
                "speakers": [{"line": 674, "offset": 0, "label": "Ορ."}],
            },
            {
                "id": "1:675",
                "book": 1,
                "column": "675",
                "lines": [{"n": 675, "ref": "675", "text": "g"}],
                "speakers": [{"line": 675, "offset": 0, "label": "Ηλ."}],
            },
            {
                "id": "1:676",
                "book": 1,
                "column": "676",
                "lines": [{"n": 676, "ref": "676", "text": "g"}],
                "speakers": [{"line": 676, "offset": 0, "label": "Ορ."}],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Electra</speaker><l n="673">Yes, indeed, have pity on your own descendants.</l></sp>
    <sp><speaker>Electra</speaker><l n="674">And Hera, you who rule Mycenae's altars.</l></sp>
    <sp><speaker>Orestes</speaker><l n="675">Give us victory, if we are asking for what is right.</l></sp>
    <sp><speaker>Orestes</speaker><l n="676">Yes, indeed, give them the right of vengeance.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Electra": "Electra", "Orestes": "Orestes"},
        sigla={"Ηλ.": "Electra", "Ορ.": "Orestes"},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert "Mycenae's altars" in by_id["1:674"]["text"]
    assert "Give us victory" in by_id["1:675"]["text"]
    assert [m["n"] for m in by_id["1:674"]["bekker"]] == [674]
    assert [m["n"] for m in by_id["1:675"]["bekker"]] == [675]
    kinds = {row["english_line"]: row["kind"] for row in report["speech_mismatches"]}
    assert kinds[674] == "attribution_difference"
    assert kinds[675] == "attribution_difference"


def test_stichomythia_with_matching_speakers_never_repairs(tmp_path: Path):
    """Real corpus instance (C1 addendum, prometheus-bound findings 1/2): a
    line-by-line alternating stichomythia where a whole run's ``<l n>`` is
    off by a multiple of the alternation period (Smyth's own source XML
    prints PV 246-258 two lines late) is INVISIBLE to this file's repair
    machinery — shifting by two preserves which character's turn it is, so
    every anchor's own speaker matches its own segment's Greek speaker and
    ``nearest_matching_speech`` is never even consulted (``speech_mismatches``
    stays empty).  This is a source-data numbering error (the anchor's
    CONTENT is wrong, not its speaker), the same shape as Agamemnon's
    exodos (finding 1, 2026-09-17 fix-mechanisms brief) — a pin, not a
    mechanism fix; no per-line speaker check can distinguish it from a
    genuinely correct stichomythia.  This test pins down the surrounding
    claim: when every line's own speaker DOES match (no drift, no
    inversion, no disagreement at all), the repair path is never entered
    and nothing moves."""
    def stich(n: int, label: str, text: str) -> tuple[dict, str]:
        seg = {
            "id": f"1:{n}",
            "book": 1,
            "column": str(n),
            "lines": [{"n": n, "ref": str(n), "text": "g"}],
            "speakers": [{"line": n, "offset": 0, "label": label}],
        }
        return seg, f'<sp><speaker>{"Prometheus" if label == "Π" else "Chorus"}</speaker><l n="{n}">{text}</l></sp>'

    rows = [
        (246, "Π", "Yes, to my friends indeed I am a spectacle of pity."),
        (247, "Χ", "Did you perhaps transgress even somewhat beyond this?"),
        (248, "Π", "I stopped mortals from foreseeing their doom."),
        (249, "Χ", "What sort of cure did you find for this affliction?"),
        (250, "Π", "I caused blind hopes to dwell within their breasts."),
        (251, "Χ", "A great benefit was this you gave to mortals."),
    ]
    segments = []
    speeches = []
    for n, label, text in rows:
        seg, sp = stich(n, label, text)
        segments.append(seg)
        speeches.append(sp)
    spine = {"work": "test-play", "segments": segments}
    tei = (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>'
        f'<div type="translation">{"".join(speeches)}</div></body></text></TEI>'
    )
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Prometheus": "Prometheus", "Chorus": "Chorus"},
        sigla={"Π": "Prometheus", "Χ": "Chorus"},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    # Every line attaches to its own segment -- nothing moved, nothing
    # flagged, because nothing ever disagreed.
    for n, _label, text in rows:
        assert text in by_id[f"1:{n}"]["text"]
    assert report["speech_mismatches"] == []
    assert report["attribution_differences"] == []


def test_transposition_rekeys_the_primary_by_printed_position(tmp_path: Path):
    """Real corpus instance (C4, oedipus-coloneus finding 1): the spine
    (Dain-Mazon) prints 328 after 330 (``citation.transpositions``:
    ``{start: "328", end: "328", before: "330"}``), so its printed order for
    328-330 is 329, 330, 328.  Jebb's own ``<l n>`` never transposes -- his
    328th/329th/330th anchors are the plain digits 328/329/330 -- so without
    a printed-position remap they seat on the WRONG Greek line and the
    speaker-matching antilabe pattern (Oedipus then Ismene on every one of
    the three lines) never raises a mismatch to catch it.  Both antilabe
    halves of each line, including the lettered second share, must land on
    the Greek line at the SAME PRINTED POSITION as Jebb's own.

    That same repeating antilabe pattern is why the row carries
    ``english_keyed: printed`` (Lane C round 3b, item 1): the Greek's
    attributions score this stretch a tie, and a tie now stands down.  This
    is the one stretch in the corpus verified to follow the printed keying,
    and the manifest says so on the row."""
    def antilabe(ref: str) -> dict:
        return {
            "id": f"1:{ref}",
            "book": 1,
            "column": ref,
            "lines": [{"n": int(ref), "ref": ref, "text": "g"}],
            "speakers": [
                {"line": int(ref), "offset": 0, "label": "ΟΙ."},
                {"line": int(ref), "offset": 1, "label": "ΙΣ."},
            ],
        }

    # Printed (Dain-Mazon) order: 329, 330, 328.
    spine = {
        "work": "oedipus-coloneus",
        "segments": [antilabe("329"), antilabe("330"), antilabe("328")],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Oedipus</speaker><l n="328" part="I">Are you with us, my child?</l></sp>
    <sp><speaker>Ismene</speaker><l n="328a" part="F">Not without toil, indeed, for myself.</l></sp>
    <sp><speaker>Oedipus</speaker><l n="329" part="I">Touch me, my daughter!</l></sp>
    <sp><speaker>Ismene</speaker><l n="329a" part="F">I give a hand to each at once.</l></sp>
    <sp><speaker>Oedipus</speaker><l n="330" part="I">Ah my children, my sisters!</l></sp>
    <sp><speaker>Ismene</speaker><l n="330a" part="F">Alas, twice-wretched life!</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Oedipus": "Oedipus", "Ismene": "Ismene"},
        sigla={"ΟΙ.": "Oedipus", "ΙΣ.": "Ismene"},
        transpositions=[
            {
                "start": "328",
                "end": "328",
                "before": "330",
                "english_keyed": "printed",
            }
        ],
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert "Are you with us, my child?" in by_id["1:329"]["text"]
    assert "Not without toil, indeed, for myself." in by_id["1:329"]["text"]
    assert "Touch me, my daughter!" in by_id["1:330"]["text"]
    assert "I give a hand to each at once." in by_id["1:330"]["text"]
    assert "Ah my children, my sisters!" in by_id["1:328"]["text"]
    assert "Alas, twice-wretched life!" in by_id["1:328"]["text"]
    # No mismatch anywhere: the antilabe's speaker pattern (Oedipus, then
    # Ismene) repeats on every line, so nothing is left to flag once the
    # anchors are re-keyed to the right printed position.
    assert report["speech_mismatches"] == []


def test_attribution_difference_attaches_to_line_owner_with_flag(tmp_path: Path):
    """Greek gives 1320 to the Messenger; English is Agamemnon with no
    Agamemnon speech within ±3 → attach to 1:1320 with speakerMismatch."""
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1310",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1310, "ref": "1310", "text": "g"}],
                "speakers": [{"line": 1, "offset": 0, "label": "Αγ."}],
            },
            {
                "id": "1:1320",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1320, "ref": "1320", "text": "g"}],
                "speakers": [{"line": 1, "offset": 0, "label": "Αγγ."}],
            },
            {
                "id": "1:1324",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1324, "ref": "1324", "text": "g"}],
                "speakers": [{"line": 1, "offset": 0, "label": "Οδ."}],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Agamemnon</speaker><l n="1320">I will not hear him.</l></sp>
  </div>
</body></text></TEI>
"""
    aliases = {
        "Agamemnon": "Agamemnon",
        "Messenger": "Messenger",
        "Odysseus": "Odysseus",
    }
    sigla = {"Αγ.": "Agamemnon", "Αγγ.": "Messenger", "Οδ.": "Odysseus"}
    english, _footnotes, report = _parse(
        tmp_path, tei, spine, aliases=aliases, sigla=sigla
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert set(by_id) == {"1:1320"}
    assert "I will not hear him." in by_id["1:1320"]["text"]
    assert by_id["1:1320"]["speakerMismatch"] == {
        "english": "Agamemnon",
        "greek": "Messenger",
    }
    # P2h finding 3: the disagreement rides on the English TURN; the
    # chunk-level field survives only because every turn here carries it.
    assert by_id["1:1320"]["turns"] == [
        {
            "offset": 0,
            "speaker": "Agamemnon",
            "display": "Agamemnon",
            "speakerMismatch": {"english": "Agamemnon", "greek": "Messenger"},
        },
    ]
    assert report["attribution_differences"] == [
        {
            "greek_id": "1:1320",
            "line": 1320,
            "english_speaker": "Agamemnon",
            "greek_speaker": "Messenger",
        }
    ]
    assert report["attribution_difference_count"] == 1
    assert report["speech_mismatch_count"] == 1
    assert report["unresolved_mismatch_count"] == 0
    mismatch = report["speech_mismatches"][0]
    assert mismatch["attached_to"] == "1:1320"
    assert mismatch["kind"] == "attribution_difference"

    alignment = _alignment_for(spine, english)
    result = validate(_play_manifest(gaps=[]), spine, english, alignment)
    unexpected = result["checks"]["alignment"]["unexpected_unmatched"]
    assert "1:1320" not in unexpected

    tokens = {
        "segments": [
            {
                "id": seg["id"],
                "lines": [{"n": line["n"], "tokens": []} for line in seg["lines"]],
            }
            for seg in spine["segments"]
        ]
    }
    out_dir = tmp_path / "dist"
    out_dir.mkdir()
    emit_books(spine, tokens, english, chapter_ranges(spine, []), out_dir)
    book = json.loads((out_dir / "book-01.json").read_text(encoding="utf-8"))
    emitted = {seg["id"]: seg for seg in book["segments"]}
    assert emitted["1:1320"]["english"]["text"] == "I will not hear him."
    assert emitted["1:1320"]["english"]["speakerMismatch"] == {
        "english": "Agamemnon",
        "greek": "Messenger",
    }
    assert "speakerMismatch" not in (emitted["1:1310"].get("english") or {})
    assert emitted["1:1310"]["english"] is None


def test_english_speech_splits_across_greek_line_owners(tmp_path: Path):
    """One English <sp> whose <l n> anchors fall in two Greek speeches
    emits one chunk per Greek segment, even when the English speaker
    differs from the second Greek speaker. Each chunk carries the English
    speech's turn at offset 0."""
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:100",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": n, "ref": str(n), "text": "g"} for n in (100, 101)
                ],
                "speakers": [{"line": 1, "offset": 0, "label": "Χο."}],
            },
            {
                "id": "1:102",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": n, "ref": str(n), "text": "g"} for n in (102, 103)
                ],
                "speakers": [{"line": 1, "offset": 0, "label": "Αγ."}],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Chorus</speaker>
      <l n="100">We sing.</l>
      <l n="102">A king replies, run together.</l>
    </sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Chorus": "Chorus", "Agamemnon": "Agamemnon"},
        sigla={"Χο.": "Chorus", "Αγ.": "Agamemnon"},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert "We sing." in by_id["1:100"]["text"]
    assert "A king replies, run together." in by_id["1:102"]["text"]
    assert "A king replies, run together." not in by_id["1:100"]["text"]
    assert by_id["1:100"]["turns"] == [
        {"offset": 0, "speaker": "Chorus", "display": "Chorus"},
    ]
    # P2j finding 1: the Agamemnon half of the Chorus's speech is attached and
    # FLAGGED — a multi-span piece disagrees exactly as a singleton does.
    assert by_id["1:102"]["turns"] == [
        {
            "offset": 0,
            "speaker": "Chorus",
            "display": "Chorus",
            "speakerMismatch": {"english": "Chorus", "greek": "Agamemnon"},
        },
    ]
    assert report["segments_with_chunk"] == 2
    assert any(
        item.get("attached_to") == "1:102" and item["english_speaker"] == "Chorus"
        for item in report["speech_mismatches"]
    )
    assert report["attribution_differences"] == [
        {
            "greek_id": "1:102",
            "line": 102,
            "english_speaker": "Chorus",
            "greek_speaker": "Agamemnon",
        }
    ]


@pytest.mark.parametrize(
    ("ref", "text"),
    [("513b", "Abandoned wretch!"), ("1270a", "Ah!")],
)
def test_lettered_anchor_attaches_to_exact_spine_ref(tmp_path: Path, ref: str, text: str):
    base = int(ref.rstrip("abcdefghijklmnopqrstuvwxyz"))
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": f"1:{base}",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1, "ref": str(base), "text": "g"}],
                "speakers": [{"line": 1, "offset": 0, "label": "A"}],
            },
            {
                "id": f"1:{ref}",
                "book": 1,
                "column": "1",
                "lines": [{"n": 2, "ref": ref, "text": "g"}],
                "speakers": [{"line": 1, "offset": 0, "label": "A"}],
            },
        ],
    }
    tei = f"""\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation"><sp><speaker>Alpha</speaker>
    <l n="{ref}">{text}</l>
  </sp></div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(tmp_path, tei, spine)
    assert [chunk["id"] for chunk in english["chunks"]] == [f"1:{ref}"]
    assert text in english["chunks"][0]["text"]
    assert not any(a["kind"] == "non_numeric_anchor" for a in report["anomalies"])


def test_lettered_anchor_falls_back_to_integer_base(tmp_path: Path):
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1270",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1, "ref": "1270", "text": "g"}],
                "speakers": [{"line": 1, "offset": 0, "label": "A"}],
            }
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation"><sp><speaker>Alpha</speaker>
    <l n="1270a">Ah!</l>
  </sp></div>
</body></text></TEI>
"""
    english, _footnotes, _report = _parse(tmp_path, tei, spine)
    assert english["chunks"][0]["id"] == "1:1270"
    assert english["chunks"][0]["text"] == "Ah!"


@pytest.mark.parametrize(
    ("filename", "ref", "expected"),
    [
        ("tlg0006.tlg008.perseus-eng2.xml", "513b", "Abandoned wretch!"),
        ("tlg0006.tlg003.perseus-eng2.xml", "1270a", "Ah!"),
    ],
)
def test_real_perseus_lettered_lines_attach(tmp_path, filename, ref, expected):
    source = Path(__file__).resolve().parents[2] / "sources" / "perseus" / filename
    tree = etree.parse(str(source))
    lines = tree.xpath(f'.//*[local-name()="l" and @n="{ref}"]')
    assert len(lines) == 1
    speech = lines[0].xpath('ancestor::*[local-name()="sp"][1]')[0]
    tei = (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>'
        '<div type="translation">'
        + etree.tostring(speech, encoding="unicode")
        + "</div></body></text></TEI>"
    )
    base = int(ref.rstrip("abcdefghijklmnopqrstuvwxyz"))
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": f"1:{ref}",
                "book": 1,
                "column": "1",
                "lines": [{"n": base, "ref": ref, "text": "g"}],
                "speakers": [],
            }
        ],
    }
    english, _footnotes, _report = _parse(
        tmp_path, tei, spine, aliases={}, sigla={}
    )
    assert english["chunks"][0]["id"] == f"1:{ref}"
    assert expected in english["chunks"][0]["text"]


def test_seven_multi_anchor_speech_does_not_fill_intervening_turns(tmp_path: Path):
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1040",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": n, "ref": str(n), "text": "g"} for n in (1040, 1041)
                ],
                "speakers": [{"line": 1, "offset": 0, "label": "Χο."}],
            },
            {
                "id": "1:1042",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": 1042, "ref": "1042", "text": "g"}
                ],
                "speakers": [{"line": 1, "offset": 0, "label": "Κη."}],
            },
            {
                "id": "1:1043",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": 1043, "ref": "1043", "text": "g"}
                ],
                "speakers": [{"line": 1, "offset": 0, "label": "Αν."}],
            },
            *[
                {
                    "id": f"1:{n}",
                    "book": 1,
                    "column": "1",
                    "lines": [{"n": n, "ref": str(n), "text": "g"}],
                    "speakers": [
                        {
                            "line": 1,
                            "offset": 0,
                            "label": "Κη." if n % 2 == 0 else "Αν.",
                        }
                    ],
                }
                for n in range(1044, 1048)
            ],
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Chorus</speaker>
      <l n="1040">I will find the means to bury him.</l>
      <l n="1045">With my own hands I will cover him.</l>
    </sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Antigone": "Antigone"},
        sigla={"Αν.": "Antigone", "Κη.": "Herald"},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert set(by_id) == {"1:1040", "1:1045"}
    assert "I will find" in by_id["1:1040"]["text"]
    assert "With my own hands" in by_id["1:1045"]["text"]
    combined = " ".join(chunk["text"] for chunk in english["chunks"])
    assert combined.count("I will find") == 1
    assert combined.count("With my own hands") == 1
    assert all(f"1:{n}" not in by_id for n in (1042, 1043, 1044, 1046, 1047))
    assert report["segments_with_chunk"] == 2
    # P2j finding 1: the second anchor lands in Antigone's speech, so that
    # turn — and its single-turn chunk — carry the disagreement.  1:1040's
    # siglum is outside this test's sigla map, so that half stays unflagged.
    assert "speakerMismatch" not in by_id["1:1040"]
    assert by_id["1:1045"]["speakerMismatch"] == {
        "english": "Chorus",
        "greek": "Antigone",
    }
    assert report["attribution_differences"] == [
        {
            "greek_id": "1:1045",
            "line": 1045,
            "english_speaker": "Chorus",
            "greek_speaker": "Antigone",
        }
    ]


def test_suppliants_anchor_stops_at_next_english_speech(tmp_path: Path):
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": f"1:{n}",
                "book": 1,
                "column": "1",
                "lines": [{"n": n, "ref": str(n), "text": "g"}],
                "speakers": [
                    {"line": 1, "offset": 0, "label": "H" if n < 513 else "C"}
                ],
            }
            for n in range(510, 514)
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Herald</speaker><l n="510">Hear my command.</l></sp>
    <sp><speaker>Chorus</speaker><l n="513">Do not leave me.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, _report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Herald": "Herald", "Chorus": "Chorus"},
        sigla={"H": "Herald", "C": "Chorus"},
    )
    by_id = {chunk["id"]: chunk["text"] for chunk in english["chunks"]}
    assert by_id == {"1:510": "Hear my command.", "1:513": "Do not leave me."}


def test_agamemnon_1203_to_1213_singletons_follow_speaker(tmp_path: Path):
    speakers = {
        n: ("Chorus" if n % 2 else "Cassandra") for n in range(1202, 1214)
    }
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": f"1:{n}",
                "book": 1,
                "column": "1",
                "lines": [{"n": n, "ref": str(n), "text": "g"}],
                "speakers": [{"line": 1, "offset": 0, "label": speakers[n]}],
            }
            for n in range(1202, 1214)
        ],
    }
    turns = [(1202, "Cassandra"), (1204, "Chorus"), (1203, "Cassandra")]
    turns.extend((n, speakers[n]) for n in range(1205, 1214))
    body = "".join(
        f'<sp><speaker>{speaker}</speaker><l n="{n}">{speaker} {n}.</l></sp>'
        for n, speaker in turns
    )
    tei = (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>'
        f'<div type="translation">{body}</div></body></text></TEI>'
    )
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Chorus": "Chorus", "Cassandra": "Cassandra"},
        sigla={"Chorus": "Chorus", "Cassandra": "Cassandra"},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert len(by_id) == 12
    for n in range(1203, 1214):
        assert by_id[f"1:{n}"]["turns"][0]["speaker"] == speakers[n]
    assert "Chorus 1204." in by_id["1:1203"]["text"]
    assert "Cassandra 1203." in by_id["1:1204"]["text"]
    assert report["speech_mismatch_count"] == 2
    assert report["unresolved_mismatch_count"] == 0


def test_packed_elders_split_into_twelve_slices(tmp_path: Path):
    segments = []
    sigla = {}
    for i, start in enumerate(range(1348, 1372, 2), start=1):
        label = f"{i}."
        sigla[label] = f"Elder {i}"
        segments.append(
            {
                "id": f"1:{start}",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": start, "ref": str(start), "text": "g"},
                    {"n": start + 1, "ref": str(start + 1), "text": "g"},
                ],
                "speakers": [{"line": 1, "offset": 0, "label": label}],
            }
        )
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp>
      <milestone unit="para"/><l n="1348">—Advice 1.</l>
      <milestone unit="para"/><l n="1350">—Advice 2.
        <milestone unit="para"/>—Advice 3.
        <milestone unit="para"/>—Advice 4</l>
      <l n="1355">continues 4.
        <milestone unit="para"/>—Advice 5.
        <milestone unit="para"/>—Advice 6.</l>
      <milestone unit="para"/><l n="1360">—Advice 7.
        <milestone unit="para"/>—Advice 8.
        <milestone unit="para"/>—Advice 9</l>
      <l n="1365">continues 9.
        <milestone unit="para"/>—Advice 10.
        <milestone unit="para"/>—Advice 11.</l>
      <milestone unit="para"/><l n="1370">—Advice 12.</l>
    </sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path, tei, {"work": "test-play", "segments": segments}, sigla=sigla
    )
    ids = [chunk["id"] for chunk in english["chunks"]]
    assert ids == [f"1:{n}" for n in range(1348, 1372, 2)]
    texts = {chunk["id"]: chunk["text"] for chunk in english["chunks"]}
    assert "Advice 1" in texts["1:1348"]
    assert "Advice 3" in texts["1:1352"]
    assert "Advice 4" in texts["1:1354"] and "continues 4" in texts["1:1354"]
    assert "Advice 6" in texts["1:1358"]
    assert "Advice 12" in texts["1:1370"]
    assert report["segments_with_chunk"] == 12
    assert all("speakerMismatch" not in chunk for chunk in english["chunks"])


def test_cross_speech_snap_is_refused(tmp_path: Path):
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:430",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": n, "ref": str(n), "text": "g"} for n in range(430, 437)
                ],
                "speakers": [{"line": 1, "offset": 0, "label": "Χο."}],
            },
            {
                "id": "1:438",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": n, "ref": str(n), "text": "g"} for n in range(438, 441)
                ],
                "speakers": [{"line": 1, "offset": 0, "label": "Κα."}],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Chorus</speaker><l n="435">Prior strophe.</l></sp>
    <sp><speaker>Chorus</speaker><l n="437">New strophe.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Chorus": "Chorus"},
        sigla={"Χο.": "Chorus", "Κα.": "Cassandra"},
    )
    by_id = {chunk["id"]: chunk["text"] for chunk in english["chunks"]}
    assert "Prior strophe." in by_id["1:430"]
    # The snap across the speech boundary stays refused: 437 never reaches
    # Cassandra.  C15 (round 4) stopped the piece being DROPPED for it — an
    # unprinted number seats beside the printed neighbour whose Greek speaker
    # it shares, which here is the Chorus's own 436.
    assert "New strophe." not in by_id.get("1:438", "")
    assert by_id["1:430"].endswith("New strophe.")
    assert any(
        item["kind"] == "unprinted_ref"
        and item["n_raw"] == "437"
        and item["attached_to"] == "1:430"
        for item in report["anomalies"]
    )
    assert not [a for a in report["anomalies"] if a["kind"] == "unmatched_anchor"]


def test_a_gap_is_skipped_and_a_mid_speech_stage_prints_inline(tmp_path: Path):
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker>
      <l n="1">Hello <stage>He descends by an inner stairway</stage> there
      <gap reason="lost"/>kept tail.</l>
    </sp>
  </div>
</body></text></TEI>
"""
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1, "ref": "1", "text": "g"}],
                "speakers": [{"line": 1, "offset": 0, "label": "A"}],
            }
        ],
    }
    english, _footnotes, _report = _parse(tmp_path, tei, spine)
    text = english["chunks"][0]["text"]
    # `<gap>` has no text to print.  The direction does, and prints (round 4
    # item 8); this line asserted its loss until 2026-09-18.
    assert text == "Hello\n_He descends by an inner stairway_\nthere kept tail."


def test_hyphenated_note_labels_are_sanitised(tmp_path: Path):
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker>
      <l n="1">Text<note n="69-71" resp="Smyth">A range note.</note>.</l>
    </sp>
  </div>
</body></text></TEI>
"""
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1, "ref": "1", "text": "g"}],
                "speakers": [{"line": 1, "offset": 0, "label": "A"}],
            }
        ],
    }
    english, footnotes, _report = _parse(tmp_path, tei, spine)
    assert list(footnotes) == ["1.69_71"]
    assert "[^1.69_71]" in english["chunks"][0]["text"]
    assert "-" not in next(iter(footnotes))


def _play_manifest(gaps=None, *, source=None, covered=None) -> Manifest:
    english = {
        "primary": {
            "id": "smyth",
            "name": "Smyth",
            "model": "perseus-play",
            "footnotes": True,
        }
    }
    if gaps is not None:
        english["gaps"] = gaps
    if source is not None:
        english["primary"]["source"] = str(source)
    if covered is not None:
        english["primary"]["covered"] = covered
    return Manifest(
        {
            "work": {"id": "test-play", "title": "Test", "author": "aeschylus"},
            "citation": {"scheme": "play-line"},
            "books": [{"n": 1, "start": "1", "end": "12"}],
            "english": english,
            "proper_names": [],
        },
        Path("test-play.yaml"),
    )


def _alignment_for(spine: dict, english: dict) -> dict:
    eng_ids = {chunk["id"] for chunk in english["chunks"]}
    covered = english.get("english_covered_by") or {}
    pairs = []
    for seg in spine["segments"]:
        pair = {
            "segment": seg["id"],
            "english": seg["id"] if seg["id"] in eng_ids else None,
        }
        if pair["english"] is None and seg["id"] in covered:
            pair["englishCoveredBy"] = covered[seg["id"]]
        pairs.append(pair)
    return {
        "pairs": pairs,
        "english_only": [],
        "english_covered_by": covered,
    }


def _stichomythia_spine() -> dict:
    """Greek one-liners 1320..1325, a lacuna inside the span, a line outside it."""
    segments = []
    for n in range(1320, 1326):
        segments.append(
            {
                "id": f"1:{n}",
                "book": 1,
                "column": "1",
                "lines": [{"n": n, "ref": str(n), "text": f"g{n}"}],
                "speakers": [
                    {
                        "line": 1,
                        "offset": 0,
                        "label": "A" if n % 2 == 0 else "B",
                    }
                ],
            }
        )
        if n == 1322:
            segments.append(
                {
                    "id": "1:post 1322",
                    "book": 1,
                    "column": "1",
                    "lines": [
                        {
                            "n": 1322,
                            "ref": "post 1322",
                            "text": "",
                            "role": "lacuna",
                        }
                    ],
                    "speakers": [],
                }
            )
    segments.append(
        {
            "id": "1:1400",
            "book": 1,
            "column": "1",
            "lines": [{"n": 1400, "ref": "1400", "text": "outside"}],
            "speakers": [{"line": 1, "offset": 0, "label": "A"}],
        }
    )
    return {"work": "test-play", "segments": segments}


STICHOMYTHIA_TEI = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker>
      <l n="1320">First block.</l>
      <l n="1325">Later block.</l>
    </sp>
  </div>
</body></text></TEI>
"""


def test_stichomythia_continuation_coverage(tmp_path: Path):
    spine = _stichomythia_spine()
    english, _footnotes, report = _parse(tmp_path, STICHOMYTHIA_TEI, spine)
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert set(by_id) == {"1:1320", "1:1325"}
    assert "First block." in by_id["1:1320"]["text"]
    assert "Later block." in by_id["1:1325"]["text"]
    # P2g finding 4: coverage never crosses speakers. 1321/1323 are the OTHER
    # speaker's one-liners inside Alpha's block: they are real holes, not
    # covered columns, and must be declared like any other gap.
    covered = english["english_covered_by"]
    assert covered == {"1:1322": "1:1320", "1:1324": "1:1320"}
    assert report["covered_by_count"] == 2

    alignment = _alignment_for(spine, english)
    result = validate(
        _play_manifest(gaps=["1:1321", "1:1323"]), spine, english, alignment
    )
    align = result["checks"]["alignment"]
    unexpected = align["unexpected_unmatched"]
    assert "1:1322" not in unexpected
    assert "1:1324" not in unexpected
    assert "1:post 1322" not in unexpected
    assert "1:1400" in unexpected
    # Coverage is an ALLOWANCE, reported, not a silent removal.
    assert align["covered_ids"] == ["1:1322", "1:1324"]
    assert "1:1322" in align["unmatched_segments"]
    assert "1:1322" in align["allowed_unmatched"]

    undeclared = validate(_play_manifest(gaps=[]), spine, english, alignment)
    assert "1:1321" in undeclared["checks"]["alignment"]["unexpected_unmatched"]
    assert "1:1323" in undeclared["checks"]["alignment"]["unexpected_unmatched"]

    tokens = {
        "segments": [
            {
                "id": seg["id"],
                "lines": [{"n": line["n"], "tokens": []} for line in seg["lines"]],
            }
            for seg in spine["segments"]
        ]
    }
    out_dir = tmp_path / "dist"
    out_dir.mkdir()
    emit_books(spine, tokens, english, chapter_ranges(spine, []), out_dir)
    book = json.loads((out_dir / "book-01.json").read_text(encoding="utf-8"))
    emitted = {seg["id"]: seg for seg in book["segments"]}
    assert emitted["1:1320"]["english"]["text"] == "First block."
    assert "englishCoveredBy" not in emitted["1:1320"]
    assert emitted["1:1321"]["english"] is None
    assert "englishCoveredBy" not in emitted["1:1321"]
    assert emitted["1:1322"]["englishCoveredBy"] == "1:1320"
    assert emitted["1:1324"]["englishCoveredBy"] == "1:1320"
    assert emitted["1:1325"]["english"]["text"] == "Later block."
    assert "englishCoveredBy" not in emitted["1:1325"]
    assert "englishCoveredBy" not in emitted["1:1400"]
    assert emitted["1:1400"]["english"] is None
    assert "englishCoveredBy" not in emitted["1:post 1322"]


def test_single_anchor_covers_until_next_english_owner(tmp_path: Path):
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": f"1:{n}",
                "book": 1,
                "column": "1",
                "lines": [{"n": n, "ref": str(n), "text": f"g{n}"}],
                "speakers": [{"line": 1, "offset": 0, "label": "A"}],
            }
            for n in range(10, 16)
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker><l n="10">Opens the block.</l></sp>
    <sp><speaker>Alpha</speaker><l n="15">Closes the block.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(tmp_path, tei, spine)
    assert {chunk["id"] for chunk in english["chunks"]} == {"1:10", "1:15"}
    covered = english["english_covered_by"]
    assert covered == {
        "1:11": "1:10",
        "1:12": "1:10",
        "1:13": "1:10",
        "1:14": "1:10",
    }
    assert report["covered_by_count"] == 4


def test_english_gaps_are_the_only_allowed_unmatched_play_line_ids(tmp_path: Path):
    spine = _spine()
    english = {
        "chunks": [
            {"id": "1:1", "column": "1", "text": "Alpha text here for length."},
            {"id": "1:5", "column": "1", "text": "Beta text here for length."},
        ]
    }
    alignment = _alignment_for(spine, english)
    denied = validate(_play_manifest(gaps=[]), spine, english, alignment)
    assert "1:10" in denied["checks"]["alignment"]["unexpected_unmatched"]
    assert denied["checks"]["alignment"]["ok"] is False

    allowed = validate(_play_manifest(gaps=["1:10"]), spine, english, alignment)
    assert allowed["checks"]["alignment"]["unexpected_unmatched"] == []
    assert allowed["checks"]["alignment"]["ok"] is True

    by_ref = validate(_play_manifest(gaps=["10"]), spine, english, alignment)
    assert by_ref["checks"]["alignment"]["ok"] is True


def test_twin_segments_need_no_declared_gap_when_lettered_source_is_empty(tmp_path):
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
                "id": "1:803",
                "book": 1,
                "column": "1",
                "lines": [{"n": 2, "ref": "803", "text": "first"}],
            },
            {
                "id": "1:803.2",
                "book": 1,
                "column": "1",
                "lines": [{"n": 3, "ref": "803", "text": "second"}],
            },
            {
                "id": "1:843a",
                "book": 1,
                "column": "1",
                "lines": [{"n": 4, "ref": "843a", "text": "a"}],
            },
            {
                "id": "1:843b",
                "book": 1,
                "column": "1",
                "lines": [{"n": 5, "ref": "843b", "text": "b"}],
            },
            {
                "id": "1:47a",
                "book": 1,
                "column": "1",
                "lines": [{"n": 6, "ref": "47a", "text": "unique"}],
            },
        ],
    }
    english = {
        "chunks": [
            {"id": "1:1", "column": "1", "text": "Alpha text here for length."},
            {"id": "1:803", "column": "1", "text": "First 803 text here for length."},
            {"id": "1:843a", "column": "1", "text": "Lettered a text here for length."},
        ]
    }
    alignment = _alignment_for(spine, english)
    source = tmp_path / "twins.xml"
    source.write_text(
        """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation"><sp><l n="843a">Translated a.</l></sp></div>
</body></text></TEI>
""",
        encoding="utf-8",
    )
    report = validate(
        _play_manifest(gaps=[], source=source), spine, english, alignment
    )
    unexpected = report["checks"]["alignment"]["unexpected_unmatched"]
    assert "1:803.2" not in unexpected
    assert "1:843b" not in unexpected
    assert "1:47a" in unexpected
    assert report["checks"]["alignment"]["ok"] is False


def test_translated_lettered_twin_is_not_auto_allowed(tmp_path):
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1270",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1, "ref": "1270", "text": "base"}],
            },
            {
                "id": "1:1270a",
                "book": 1,
                "column": "1",
                "lines": [{"n": 2, "ref": "1270a", "text": "lettered"}],
            },
        ],
    }
    english = {
        "chunks": [
            {"id": "1:1270", "column": "1", "text": "Base translation."}
        ]
    }
    source = tmp_path / "medea.xml"
    source.write_text(
        """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation"><sp><l n="1270a">Ah!</l></sp></div>
</body></text></TEI>
""",
        encoding="utf-8",
    )
    report = validate(
        _play_manifest(gaps=[], source=source),
        spine,
        english,
        _alignment_for(spine, english),
    )
    assert report["checks"]["alignment"]["unexpected_unmatched"] == ["1:1270a"]


def test_unmapped_english_speaker_is_a_hard_roster_error():
    english = {
        "chunks": [
            {
                "id": "1:1",
                "turns": [
                    {"offset": 0, "speaker": "Clytaemnestra", "display": "Clytaemnestra"}
                ],
            }
        ]
    }
    with pytest.raises(RuntimeError, match="unmapped English speaker"):
        _play_line_english_roster_gate(
            "agamemnon",
            english,
            {"Chorus": "Chorus"},
            {"Clytaemestra", "Chorus"},
        )


def test_footnotes_flag_stays_off_the_v1_translation_entry(tmp_path, monkeypatch):
    """manifest.v1's translation entry forbids extra keys; the flag used to be
    copied here (P2b) and failed the contract validator on 18 works at the
    first full build:public (2026-09-08). The fact rides in
    `apparatus.footnotes`, keyed on the emitted footnotes.json."""
    out_dir = tmp_path / "dist" / "test-play"
    out_dir.mkdir(parents=True)
    monkeypatch.delenv("CORPUS_VERSION", raising=False)
    manifest = Manifest(
        {
            "work": {
                "id": "test-play",
                "title": "Test Play",
                "author": "aeschylus",
                "language": "grc",
                "tlg_author": "0085",
                "tlg_work": "005",
                "greek_edition": "Murray",
            },
            "citation": {"scheme": "play-line"},
            "books": [{"n": 1, "start": "1", "end": "10"}],
            "english": {
                "primary": {
                    "id": "smyth",
                    "name": "H. W. Smyth (Loeb, 1926)",
                    "model": "perseus-play",
                    "footnotes": True,
                }
            },
        },
        Path("test-play.yaml"),
    )
    fields = _manifest_v1_fields(manifest, out_dir)
    assert "footnotes" not in fields["translations"][0]
    assert fields["translations"][0]["id"] == "smyth"
    assert fields["apparatus"]["footnotes"] is False
    (out_dir / "footnotes.json").write_text("{}")
    assert _manifest_v1_fields(manifest, out_dir)["apparatus"]["footnotes"] is True


# ── P2g: speaker resolution, speaker sets, repair ticks, loss gate ──────────


def _resolver(sigla: dict, overrides: list[dict] | None = None):
    from drama_pipeline.stage1_turn_english import _SiglaResolver

    return _SiglaResolver(
        Manifest(
            {
                "work": {"id": "test-play"},
                "citation": {"scheme": "play-line"},
                "speakers": {"sigla": sigla, "overrides": overrides or []},
            },
            Path("test-play.yaml"),
        )
    )


def test_speaker_override_resolves_like_stage7(tmp_path: Path):
    """Helen's Θε. is a servant until 1165 and Theoclymenus from 1165 on
    (speakers.overrides). Resolving with the bare sigla map read every later
    line as the servant, scored a false mismatch and deleted the English."""
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1100",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1, "ref": "1100", "text": "g"}],
                "speakers": [{"line": 1, "offset": 0, "label": "Θε."}],
            },
            {
                "id": "1:1180",
                "book": 1,
                "column": "1",
                "lines": [{"n": 2, "ref": "1180", "text": "g"}],
                "speakers": [{"line": 2, "offset": 0, "label": "Θε."}],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Servant</speaker><l n="1100">The servant speaks.</l></sp>
    <sp><speaker>Theoclymenus</speaker><l n="1180">The king speaks.</l></sp>
  </div>
</body></text></TEI>
"""
    resolver = _resolver(
        {"Θε.": "Servant", "—": None},
        [{"siglum": "Θε.", "from": "1165", "display": "Theoclymenus"}],
    )
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Servant": "Servant", "Theoclymenus": "Theoclymenus"},
        sigla=resolver,
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert by_id["1:1180"]["text"] == "The king speaks."
    assert "speakerMismatch" not in by_id["1:1180"]
    assert report["speech_mismatch_count"] == 0
    assert "Theoclymenus" in report["speakers"]["greek_roster"]
    assert report["speakers"]["only_in_english"] == []


def test_packed_second_speaker_accepts_its_own_english(tmp_path: Path):
    """Seven 1:1004 packs Ismene (1004) and the Herald (1005): the Herald's
    English must attach there without a mismatch. The first-speaker rule made
    it a mismatch the repair search could never target."""
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1004",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": 1004, "ref": "1004", "text": "g"},
                    {"n": 1005, "ref": "1005", "text": "g"},
                ],
                "speakers": [
                    {"line": 1004, "offset": 0, "label": "Ισ."},
                    {"line": 1005, "offset": 0, "label": "Κη."},
                ],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Herald</speaker><l n="1005">The city has decreed.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Herald": "Herald", "Ismene": "Ismene"},
        sigla={"Ισ.": "Ismene", "Κη.": "Herald", "—": None},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert by_id["1:1004"]["text"] == "The city has decreed."
    assert "speakerMismatch" not in by_id["1:1004"]
    assert report["speech_mismatch_count"] == 0
    assert report["attribution_difference_count"] == 0


def test_repair_tick_names_a_line_the_target_segment_prints(tmp_path: Path):
    """A repaired attachment must tick one of the TARGET's own lines, not the
    English n of the neighbour that printed it (P2g finding 10).

    C1: a lone disagreement no longer reaches the repair path at all (see
    ``test_isolated_single_line_disagreement_is_not_repaired``) — repair now
    needs a run of three or more consecutive mismatching anchors
    (``_repairable_anchors``).  This gives Alpha three in a row; the claims
    bookkeeping still lets only the first actually move, exactly as before
    C1, so the tick-naming check survives unchanged in substance."""
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1000",
                "book": 1,
                "column": "1",
                "lines": [
                    {"n": 1000, "ref": "1000", "text": "g"},
                    {"n": 1001, "ref": "1001", "text": "g"},
                ],
                "speakers": [{"line": 1000, "offset": 0, "label": "A"}],
            },
            {
                "id": "1:1002",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1002, "ref": "1002", "text": "g"}],
                "speakers": [{"line": 1002, "offset": 0, "label": "B"}],
            },
            {
                "id": "1:1003",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1003, "ref": "1003", "text": "g"}],
                "speakers": [{"line": 1003, "offset": 0, "label": "G"}],
            },
            {
                "id": "1:1004",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1004, "ref": "1004", "text": "g"}],
                "speakers": [{"line": 1004, "offset": 0, "label": "H"}],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker><l n="1002">Alpha's first stray line.</l></sp>
    <sp><speaker>Alpha</speaker><l n="1003">Alpha's own line.</l></sp>
    <sp><speaker>Alpha</speaker><l n="1004">Alpha's third stray line.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path, tei, spine, sigla={"A": "Alpha", "B": "Beta", "G": "Gamma", "H": "Delta"}
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert "Alpha's first stray line." in by_id["1:1000"]["text"]
    ticks = [mark["n"] for mark in by_id["1:1000"]["bekker"]]
    assert ticks == [1001]
    mismatches = {row["english_line"]: row for row in report["speech_mismatches"]}
    assert mismatches[1002]["kind"] == "speaker_repair"
    assert mismatches[1002]["attached_to"] == "1:1000"
    assert mismatches[1002]["attached_ref"] == "1001"
    # The other two exhaust the claim on 1:1000 and stay put, flagged.
    assert mismatches[1003]["kind"] == "attribution_difference"
    assert mismatches[1003]["attached_to"] == "1:1003"
    assert mismatches[1004]["kind"] == "attribution_difference"
    assert mismatches[1004]["attached_to"] == "1:1004"


def _write_english_report(monkeypatch, tmp_path: Path, data: dict) -> None:
    from drama_pipeline import stage2_validate as s2

    stage1 = tmp_path / "stage1"
    stage1.mkdir(exist_ok=True)
    (stage1 / "english_report.json").write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(s2, "BUILD_DIR", tmp_path)


def test_attachment_loss_is_gated(tmp_path: Path, monkeypatch):
    """Unattached English is deleted translation: it must fail the build
    unless the manifest declares an allowance (P2g finding 3)."""
    spine = _spine()
    english = {
        "chunks": [
            {"id": "1:1", "column": "1", "text": "Alpha text here for length."},
            {"id": "1:5", "column": "1", "text": "Beta text here for length."},
            {"id": "1:10", "column": "1", "text": "Gamma text here for length."},
        ]
    }
    alignment = _alignment_for(spine, english)

    _write_english_report(
        monkeypatch,
        tmp_path,
        {"work": "test-play", "unresolved_mismatch_count": 0},
    )
    clean = validate(_play_manifest(gaps=[]), spine, english, alignment)
    assert clean["checks"]["attachment_loss"]["ok"] is True
    assert clean["checks"]["attachment_loss"]["unresolved"] == 0

    _write_english_report(
        monkeypatch,
        tmp_path,
        {
            "work": "test-play",
            "unresolved_mismatch_count": 3,
            "speech_mismatch_count": 9,
            "attribution_difference_count": 2,
        },
    )
    lossy = validate(_play_manifest(gaps=[]), spine, english, alignment)
    check = lossy["checks"]["attachment_loss"]
    assert check["ok"] is False
    assert "3 English piece(s) attached to no Greek speech" in check["error"]
    assert lossy["ok"] is False

    manifest = _play_manifest(gaps=[])
    manifest.data["english"]["max_unresolved_mismatches"] = 3
    allowed = validate(manifest, spine, english, alignment)
    assert allowed["checks"]["attachment_loss"]["ok"] is True


def test_non_numeric_and_zero_n_prose_count_as_attachment_loss(
    tmp_path: Path, monkeypatch
):
    """Astra lane C, F8: dropped nonempty <l> without a supported n is gated."""
    from drama_pipeline.stage2_validate import _attachment_loss_check

    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1, "ref": "1", "text": "λογος"}],
                "speakers": [{"line": 1, "offset": 0, "label": "A"}],
            }
        ],
    }

    def parse_tail(tail: str):
        tei = (
            "<TEI xmlns=\"http://www.tei-c.org/ns/1.0\"><text><body>"
            "<div type=\"translation\"><sp><speaker>A</speaker>"
            f"<l n=\"1\">Kept.</l>{tail}</sp></div></body></text></TEI>"
        )
        return _parse(tmp_path, tei, spine, aliases={"A": "A"}, sigla={"A": "A"})

    def gate(report: dict) -> dict:
        _write_english_report(monkeypatch, tmp_path, report)
        return _attachment_loss_check(_play_manifest(gaps=[]))

    english, _f, report = parse_tail('<l n="2-3">Lost speech.</l>')
    assert "Lost speech" not in english["chunks"][0]["text"]
    assert any(a["kind"] == "non_numeric_anchor" for a in report["anomalies"])
    check = gate(report)
    assert check["ok"] is False
    assert check["dropped"]["non_numeric_anchor"] == 1

    english, _f, report = parse_tail("<l>Lost speech.</l>")
    assert any(a["kind"] == "non_numeric_anchor" for a in report["anomalies"])
    assert gate(report)["ok"] is False

    english, _f, report = parse_tail('<l n="0">Lost speech.</l>')
    assert "Lost speech" not in english["chunks"][0]["text"]
    assert any(a["kind"] == "zero_n_content" for a in report["anomalies"])
    assert gate(report)["ok"] is False

    english, _f, report = parse_tail('<l n="0">A</l>')
    assert not any(a["kind"] == "zero_n_content" for a in report["anomalies"])
    assert "Kept." in english["chunks"][0]["text"]
    assert gate({**report, "work": "test-play"})["ok"] is True


def test_attachment_loss_fails_closed_without_this_works_report(
    tmp_path: Path, monkeypatch
):
    spine = _spine()
    english = {"chunks": [{"id": "1:1", "column": "1", "text": "Alpha text."}]}
    alignment = _alignment_for(spine, english)
    from drama_pipeline import stage2_validate as s2

    monkeypatch.setattr(s2, "BUILD_DIR", tmp_path)
    missing = validate(_play_manifest(gaps=["1:5", "1:10"]), spine, english, alignment)
    assert missing["checks"]["attachment_loss"]["ok"] is False
    assert "no stage1 English report" in missing["checks"]["attachment_loss"]["error"]

    _write_english_report(
        monkeypatch, tmp_path, {"work": "frogs", "unresolved_mismatch_count": 0}
    )
    foreign = validate(_play_manifest(gaps=["1:5", "1:10"]), spine, english, alignment)
    assert foreign["checks"]["attachment_loss"]["ok"] is False
    assert "not 'test-play'" in foreign["checks"]["attachment_loss"]["error"]


def test_helen_override_is_live_in_the_english_builder():
    """The real manifest, resolved the way _SpeechIndex now resolves it."""
    from drama_pipeline.stage1_perseus_play_english import _SpeechIndex

    manifest = Manifest.for_work("helen")
    spine = {
        "work": "helen",
        "segments": [
            {
                "id": "1:700",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1, "ref": "700", "text": "g"}],
                "speakers": [{"line": 1, "offset": 0, "label": "Θε."}],
            },
            {
                "id": "1:1200",
                "book": 1,
                "column": "1",
                "lines": [{"n": 2, "ref": "1200", "text": "g"}],
                "speakers": [{"line": 2, "offset": 0, "label": "Θε."}],
            },
        ],
    }
    index = _SpeechIndex(spine, _resolver_for(manifest))
    assert index.speakers_of["1:700"] == {"Servant"}
    assert index.speakers_of["1:1200"] == {"Theoclymenus"}


def _resolver_for(manifest: Manifest):
    from drama_pipeline.stage1_turn_english import _SiglaResolver

    return _SiglaResolver(manifest)


# ── P2h: every speaker decision is per printed LINE ─────────────────────────


def _seven_spine() -> dict:
    """Seven 1000–1026 as the TLG prints it.

    The Herald's label at 1005 sits after an editorial bracket, so its offset
    is 1, not 0: the spine cannot cut there and 1:1004 packs Ismene (1004) and
    the Herald (1005–1025) in one segment.
    """
    def stich(n: int, label: str) -> dict:
        return {
            "id": f"1:{n}",
            "book": 1,
            "column": str(n),
            "lines": [{"n": n, "ref": str(n), "text": "g"}],
            "speakers": [{"line": n, "offset": 0, "label": label}],
        }

    packed = {
        "id": "1:1004",
        "book": 1,
        "column": "1004",
        "lines": [{"n": n, "ref": str(n), "text": "g"} for n in range(1004, 1026)],
        "speakers": [
            {"line": 1004, "offset": 0, "label": "Ισ."},
            {"line": 1005, "offset": 1, "label": "ΚΗΡΥΞ"},
        ],
    }
    return {
        "work": "test-play",
        "segments": [
            {
                "id": "1:998",
                "book": 1,
                "column": "998",
                "lines": [
                    {"n": 998, "ref": "998", "text": "g"},
                    {"n": 999, "ref": "999", "text": "g"},
                ],
                "speakers": [{"line": 998, "offset": 0, "label": "Αν."}],
            },
            stich(1000, "Ισ."),
            stich(1001, "Αν."),
            stich(1002, "Ισ."),
            stich(1003, "Αν."),
            packed,
            stich(1026, "Αν."),
        ],
    }


SEVEN_SIGLA = {"Ισ.": "Ismene", "Αν.": "Antigone", "ΚΗΡΥΞ": "Herald", "—": None}
SEVEN_ALIASES = {
    "Ismene": "Ismene",
    "Antigone": "Antigone",
    "Herald": "Herald",
}
SEVEN_TEI = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Antigone</speaker><l n="998">A tale of destruction!</l></sp>
    <sp><speaker>Ismene</speaker><l n="999">Destruction to look upon!</l></sp>
    <sp><speaker>Antigone</speaker><l n="1000">Oh, the grief—</l></sp>
    <sp><speaker>Ismene</speaker><l n="1001">Oh, the evils—</l></sp>
    <sp><speaker>Antigone</speaker><l n="1002">For home and land.</l></sp>
    <sp><speaker>Ismene</speaker><l n="1003">Above all for me,</l></sp>
    <sp><speaker>Antigone</speaker><l n="1004">And more also for me.</l></sp>
    <sp><speaker>Ismene</speaker><l n="1005">Ah I pity your suffering, my king.</l></sp>
    <sp><speaker>Antigone</speaker><l n="1006">Pity for you both.</l></sp>
    <sp><speaker>Ismene</speaker><l n="1007">You were possessed by delusion.</l></sp>
    <sp><speaker>Antigone</speaker><l n="1008">Where shall we lay them?</l></sp>
    <sp><speaker>Ismene</speaker><l n="1009">Where their honor is greatest.</l></sp>
    <sp><speaker>Antigone</speaker><l n="1010">To lie beside their father.</l></sp>
    <sp><speaker>Herald</speaker>
      <l n="1011">It is my duty to announce the decrees.</l>
      <l n="1012">Eteocles they will bury.</l>
      <l n="1025">So the council of the Cadmeans decreed.</l>
    </sp>
    <sp><speaker>Antigone</speaker><l n="1026">But I say to the rulers.</l></sp>
  </div>
</body></text></TEI>
"""


def test_packed_antilabe_span_attaches_by_line_speaker(tmp_path: Path):
    """Seven 998–1026 (P2h findings 2, 6, 8 + the P2i ruling).

    Smyth's speakers run one line ahead of the TLG's, so every piece of this
    stichomythia is a drift repair until the claims run out.  The packed
    ``1:1004`` (Ismene 1004, the Herald 1005–1025) is never a repair TARGET:
    Ismene 1003 stays on the speech that prints 1003, flagged.  What the Greek
    prints on the Herald's lines attaches there, each turn flagged with the
    speaker of ITS printed line — attached and marked, never withheld.
    """
    english, _footnotes, report = _parse(
        tmp_path,
        SEVEN_TEI,
        _seven_spine(),
        aliases=SEVEN_ALIASES,
        sigla=SEVEN_SIGLA,
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    packed = by_id["1:1004"]

    # Everything Smyth numbers 1004–1025 is in the packed chunk, once.
    assert [turn["speaker"] for turn in packed["turns"]] == [
        "Antigone",
        "Ismene",
        "Antigone",
        "Ismene",
        "Antigone",
        "Ismene",
        "Antigone",
        "Herald",
    ]
    assert packed["text"].count("It is my duty") == 1
    assert "So the council of the Cadmeans decreed." in packed["text"]
    for words in ("And more also", "Ah I pity", "Pity for you both", "To lie beside"):
        assert words in packed["text"]
    # No English piece is attached twice.
    for words in ("Above all for me", "And more also", "You were possessed"):
        assert sum(chunk["text"].count(words) for chunk in english["chunks"]) == 1

    # P2i finding 1: Ismene 1003 stays on 1:1003 — the speech that prints her
    # line — instead of being dragged onto the Herald's 22-line block.
    assert "Above all for me" in by_id["1:1003"]["text"]
    assert "Above all for me" not in packed["text"]

    # P2i finding 2: no holes.  Every disagreement is an attached, flagged turn
    # naming the speaker of that printed line.
    assert not any(a["kind"] == "attribution_hole" for a in report["anomalies"])
    assert report["anomalies"] == []
    flagged = {
        (item["greek_id"], item["line"]): item["greek_speaker"]
        for item in report["attribution_differences"]
    }
    assert flagged == {
        ("1:1003", 1003): "Antigone",
        ("1:1004", 1004): "Ismene",
        ("1:1004", 1006): "Herald",
        ("1:1004", 1007): "Herald",
        ("1:1004", 1008): "Herald",
        ("1:1004", 1009): "Herald",
        ("1:1004", 1010): "Herald",
    }
    assert report["attribution_difference_count"] == 7
    assert all(
        item["english_speaker"] in {"Antigone", "Ismene"}
        for item in report["attribution_differences"]
    )

    # The flag rides the TURN, and only the turns that disagree.
    marked = {
        turn["speaker"]: turn["speakerMismatch"]
        for chunk in english["chunks"]
        for turn in chunk["turns"]
        if "speakerMismatch" in turn
    }
    assert marked["Antigone"] == {"english": "Antigone", "greek": "Herald"}
    assert [turn.get("speakerMismatch") for turn in packed["turns"]][-1] is None
    assert "speakerMismatch" not in packed  # not every turn of the chunk
    assert all(
        "/" not in (row.get("greek_speaker") or "")
        for row in report["speech_mismatches"]
    )

    rows = {row["english_line"]: row for row in report["speech_mismatches"]}
    # The Herald's own lines are a clean match: no mismatch row at all.
    assert not any(row["english_speaker"] == "Herald" for row in rows.values())
    assert 1005 not in rows  # Ismene still owns the start of the antilabe line
    assert rows[1003]["kind"] == "attribution_difference"
    assert rows[1003]["attached_to"] == "1:1003"
    for line in (1007, 1009):
        assert rows[line]["kind"] == "attribution_difference"
        assert rows[line]["attached_to"] == "1:1004"
        assert rows[line]["attached_speaker"] == "Herald"
    # Drift repair still works where the speaker has a speech of her own:
    # Ismene 999 moves to 1:1000, Antigone 1002 to 1:1003.
    assert rows[999]["kind"] == "speaker_repair"
    assert rows[999]["attached_to"] == "1:1000"
    assert rows[1002]["kind"] == "speaker_repair"
    assert rows[1002]["attached_to"] == "1:1003"


def test_multi_span_speech_flags_the_piece_it_leaves_in_another_speech(
    tmp_path: Path,
):
    """P2j finding 1: Seven's Herald speech spans 1011-1030, and its last
    anchor falls inside Antigone's 1:1026.  That piece attaches there — it is
    the Greek it translates — and the TURN says the editions disagree.  Before
    the fix a multi-span speech skipped the flag entirely and the reader saw
    an unmarked Herald turn on Antigone's lines."""
    spine = _seven_spine()
    tail = spine["segments"][-1]
    assert tail["id"] == "1:1026"
    # Antigone speaks 1026-1030 in the Greek; Smyth's Herald runs to 1030.
    tail["lines"] = [
        {"n": n, "ref": str(n), "text": "g"} for n in range(1026, 1031)
    ]
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Herald</speaker>
      <l n="1011">It is my duty to announce the decrees.</l>
      <l n="1030">And this is the will of the Cadmeans.</l>
    </sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path, tei, spine, aliases=SEVEN_ALIASES, sigla=SEVEN_SIGLA
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    # The Herald's own half is clean; the piece on Antigone's speech is not.
    assert "It is my duty" in by_id["1:1004"]["text"]
    assert all("speakerMismatch" not in turn for turn in by_id["1:1004"]["turns"])
    assert "will of the Cadmeans" in by_id["1:1026"]["text"]
    assert by_id["1:1026"]["turns"][0]["speakerMismatch"] == {
        "english": "Herald",
        "greek": "Antigone",
    }
    assert report["attribution_differences"] == [
        {
            "greek_id": "1:1026",
            "line": 1030,
            "english_speaker": "Herald",
            "greek_speaker": "Antigone",
        }
    ]
    row = next(r for r in report["speech_mismatches"] if r["english_line"] == 1030)
    assert row["kind"] == "attribution_difference"
    assert row["attached_to"] == "1:1026"
    assert row["attached_speaker"] == "Antigone"
    assert report["anomalies"] == []


def test_repair_prefers_the_speakers_own_one_liner_over_a_packed_span(
    tmp_path: Path,
):
    """P2i finding 1: distance is measured against the speaker's OWN printed
    lines, and a one-liner beats a packed span at equal distance."""
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:10",
                "book": 1,
                "column": "10",
                "lines": [{"n": 10, "ref": "10", "text": "g"}],
                "speakers": [{"line": 10, "offset": 0, "label": "Αν."}],
            },
            {
                "id": "1:11",
                "book": 1,
                "column": "11",
                "lines": [{"n": 11, "ref": "11", "text": "g"}],
                "speakers": [{"line": 11, "offset": 0, "label": "Ισ."}],
            },
            {
                "id": "1:12",
                "book": 1,
                "column": "12",
                "lines": [{"n": n, "ref": str(n), "text": "g"} for n in range(12, 20)],
                "speakers": [
                    {"line": 12, "offset": 0, "label": "Ισ."},
                    {"line": 13, "offset": 1, "label": "ΚΗΡΥΞ"},
                ],
            },
        ],
    }
    from drama_pipeline.stage1_perseus_play_english import _SpeechIndex

    index = _SpeechIndex(spine, SEVEN_SIGLA)
    # 1:11 and 1:12 are both one line from 10; the one-liner wins.
    assert index.nearest_matching_speech(10, "Ismene") == (spine["segments"][1], 11)
    # With the one-liner claimed, the packed span is still not a target.
    assert index.nearest_matching_speech(10, "Ismene", claimed={("1:11", "Ismene")}) is None


def test_attribution_hole_is_counted_as_attachment_loss(tmp_path: Path, monkeypatch):
    """A hole is dropped translation: stage2 must fail on it (P2h finding 5)."""
    spine = _spine()
    english = {"chunks": [{"id": "1:1", "column": "1", "text": "Alpha text."}]}
    alignment = _alignment_for(spine, english)
    report = {
        "work": "test-play",
        "unresolved_mismatch_count": 0,
        "anomalies": [
            {"kind": "attribution_hole", "greek_id": "1:5", "line": 6, "english_speaker": "Beta"},
            {"kind": "unmatched_anchor", "sp": 3, "n_raw": "9"},
            {"kind": "nless_slice_unattached", "sp": 4},
            {"kind": "note_skipped_non_smyth", "resp": "Ed."},
        ],
    }
    _write_english_report(monkeypatch, tmp_path, report)
    result = validate(_play_manifest(gaps=["1:5", "1:10"]), spine, english, alignment)
    check = result["checks"]["attachment_loss"]
    assert check["ok"] is False
    assert check["unresolved"] == 3
    assert check["dropped"]["unmatched_anchor"] == 1
    assert check["dropped"]["nless_slice_unattached"] == 1
    assert check["dropped"]["attribution_hole"] == 1
    assert check["dropped"]["non_numeric_anchor"] == 0
    assert check["dropped"]["zero_n_content"] == 0
    assert "3 English piece(s) attached to no Greek speech" in check["error"]

    manifest = _play_manifest(gaps=["1:5", "1:10"])
    manifest.data["english"]["max_unresolved_mismatches"] = 3
    allowed = validate(manifest, spine, english, alignment)
    assert allowed["checks"]["attachment_loss"]["ok"] is True


def test_continuation_coverage_uses_the_english_speakers_name(tmp_path: Path):
    """Coverage is the English speech's own speaker, not the covering
    segment's whole set (P2h finding 7): a packed covering segment must not
    lend its second speaker's name to the segments in between."""
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:100",
                "book": 1,
                "column": "100",
                "lines": [{"n": n, "ref": str(n), "text": "g"} for n in (100, 101)],
                "speakers": [
                    {"line": 100, "offset": 0, "label": "Χο."},
                    {"line": 101, "offset": 4, "label": "Κη."},
                ],
            },
            {
                "id": "1:102",
                "book": 1,
                "column": "102",
                "lines": [{"n": 102, "ref": "102", "text": "g"}],
                "speakers": [{"line": 102, "offset": 0, "label": "Κη."}],
            },
            {
                "id": "1:103",
                "book": 1,
                "column": "103",
                "lines": [{"n": 103, "ref": "103", "text": "g"}],
                "speakers": [{"line": 103, "offset": 0, "label": "Χο."}],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Chorus</speaker><l n="100">Chorus first.</l><l n="103">Chorus again.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, _report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Chorus": "Chorus", "Herald": "Herald"},
        sigla={"Χο.": "Chorus", "Κη.": "Herald", "—": None},
    )
    # The Herald's 1:102 is not the Chorus's continuation, though the covering
    # segment packs a Herald event of its own.
    assert english["english_covered_by"] == {}


def test_stage7_reads_spine_line_refs_for_speaker_overrides():
    """stage7 built its ref map from `greek`, a key the spine only grows later
    in the emit, so `speakers.overrides` never fired there: Helen's Θε. read
    as the Servant in the Greek column while the English said Theoclymenus
    (P2h finding 1)."""
    from drama_pipeline import stage7_emit

    manifest = Manifest.for_work("helen")
    spine = {
        "work": "helen",
        "segments": [
            {
                "id": "1:998",
                "book": 1,
                "column": "998",
                "lines": [{"n": 1, "ref": "998", "text": "g"}],
                "speakers": [{"line": 1, "offset": 0, "label": "Θε."}],
            },
            {
                "id": "1:1195",
                "book": 1,
                "column": "1195",
                "lines": [{"n": 2, "ref": "1195", "text": "g"}],
                "speakers": [{"line": 2, "offset": 0, "label": "Θε."}],
            },
        ],
    }
    rosters = stage7_emit._canonicalize_play_line_speakers(spine, manifest)
    displays = [
        event["display"]
        for segment in spine["segments"]
        for event in segment["speakers"]
    ]
    assert displays == ["Theonoe", "Theoclymenus"]
    assert "Theoclymenus" in rosters[1]


# ── P2i: shares of a line, continuation coverage, the nless-snap label ──────


# P2j finding 6: the lettered-share test runs on the REAL Helen tables --
# the manifest's own sigla (`Θε.` -> Servant, re-assigned to Theoclymenus from
# 1165 by `speakers.overrides`; `Θε.β` -> Second Servant) and its English
# aliases.  The P2i fixture invented an alias map, so it never showed what the
# build actually does with Coleridge's `Servant` at 1627-1640.
HELEN_MANIFEST = Manifest.for_work("helen")
HELEN_SIGLA = _SiglaResolver(HELEN_MANIFEST)
HELEN_ALIASES = (HELEN_MANIFEST.data.get("speakers") or {}).get("english") or {}
HELEN_TEI = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Theoklymenos</speaker>
      <l n="1630" part="I">Will you rule over your master?</l></sp>
    <sp><speaker>Servant</speaker>
      <l n="1630b" part="F">Yes, for I am in my right mind.</l></sp>
    <sp><speaker>Chorus</speaker>
      <l n="1631b" part="F">A stranger's word.</l></sp>
  </div>
</body></text></TEI>
"""


def _helen_antilabe_spine() -> dict:
    """Two Helen antilabe lines: Theoclymenus at offset 0, the Second Servant
    from mid-line (Diggle's ``Θε.β``)."""
    def antilabe(n: int) -> dict:
        return {
            "id": f"1:{n}",
            "book": 1,
            "column": str(n),
            "lines": [{"n": n, "ref": str(n), "text": "g"}],
            "speakers": [
                {"line": n, "offset": 0, "label": "Θε."},
                {"line": n, "offset": 20, "label": "Θε.β"},
            ],
        }

    return {"work": "test-play", "segments": [antilabe(1630), antilabe(1631)]}


def test_lettered_anchor_matches_the_mid_line_share(tmp_path: Path):
    """P2i finding 3 on the real Helen tables: ``1630b`` is the SECOND share
    of 1630, so it reads against ``Θε.β`` (the Second Servant) and not against
    the line-start ``Θε.``, which the manifest's override makes Theoclymenus
    from 1165 on.

    P2j finding 6/2: with the manifest's own aliases Coleridge's printed
    ``Servant`` canonicalises to ``Servant``, so the share is attached and
    FLAGGED as a name difference (Servant vs Second Servant) -- 13 turns at
    1627-1640 in the real build.  It is not a misattachment: the English is
    beside the Greek it translates.  Whether Helen's servant/messenger names
    should be reconciled at all is John's call (35 of the play's 39 flags are
    this same crossing), so the test states what the build does today."""
    english, _footnotes, report = _parse(
        tmp_path,
        HELEN_TEI,
        _helen_antilabe_spine(),
        aliases=HELEN_ALIASES,
        sigla=HELEN_SIGLA,
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    # Both shares of 1630 land on 1:1630 -- the letter picked the right share.
    assert "Will you rule" in by_id["1:1630"]["text"]
    assert "in my right mind" in by_id["1:1630"]["text"]
    turns = {turn["display"]: turn for turn in by_id["1:1630"]["turns"]}
    assert "speakerMismatch" not in turns["Theoklymenos"]
    assert turns["Servant"]["speakerMismatch"] == {
        "english": "Servant",
        "greek": "Second Servant",
    }
    # The Chorus owns no share of 1631: attached to the printing speech and
    # flagged with the speaker of the share the letter names.
    assert "A stranger's word." in by_id["1:1631"]["text"]
    assert report["attribution_differences"] == [
        {
            "greek_id": "1:1630",
            "line": 1630,
            "english_speaker": "Servant",
            "greek_speaker": "Second Servant",
        },
        {
            "greek_id": "1:1631",
            "line": 1631,
            "english_speaker": "Chorus",
            "greek_speaker": "Second Servant",
        },
    ]
    assert report["anomalies"] == []


def test_line_shares_reads_an_a_b_a_line(tmp_path: Path):
    """P2i finding 7: a three-event line has three shares, and a lettered
    anchor names the LAST same-name share, not the first."""
    from drama_pipeline.stage1_perseus_play_english import _SpeechIndex
    from drama_pipeline.stage1_turn_english import speaker_at

    segment = {
        "id": "1:500",
        "book": 1,
        "column": "500",
        "lines": [{"n": 500, "ref": "500", "text": "g"}],
        "speakers": [
            {"line": 500, "offset": 0, "label": "Αν."},
            {"line": 500, "offset": 20, "label": "Ισ."},
            {"line": 500, "offset": 40, "label": "Αν."},
        ],
    }
    index = _SpeechIndex({"work": "t", "segments": [segment]}, SEVEN_SIGLA)
    assert index.line_shares(segment, 500) == ["Antigone", "Ismene", "Antigone"]
    # `500c` is the third share — Antigone again, after Ismene's interruption:
    # a speaker who owns any share of the line reads clean either way.
    assert index.share_speaker(segment, 500, "500c", prefer="Antigone") == "Antigone"
    assert index.share_speaker(segment, 500, "500b", prefer="Antigone") == "Antigone"
    # A speaker with no share of the line disagrees with the share the letter
    # names, not with the line-start speaker.
    assert index.share_speaker(segment, 500, "500b", prefer="Herald") == "Ismene"
    assert index.share_speaker(segment, 500, "500c", prefer="Herald") == "Antigone"
    assert index.share_speaker(segment, 500, "500", prefer="Herald") == "Antigone"
    # The plain line rule still answers with the speaker's own share.
    assert speaker_at(segment, 500, SEVEN_SIGLA, prefer="Antigone") == "Antigone"
    assert speaker_at(segment, 500, SEVEN_SIGLA) == "Antigone"


def test_continuation_coverage_needs_every_printed_line(tmp_path: Path):
    """P2i finding 4: the covered side is per printed LINE.  A candidate whose
    later lines belong to the character the antilabe handed over to is a real
    hole, not a continuation of the English block."""
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:100",
                "book": 1,
                "column": "100",
                "lines": [{"n": n, "ref": str(n), "text": "g"} for n in (100, 101)],
                "speakers": [{"line": 100, "offset": 0, "label": "Αν."}],
            },
            {
                "id": "1:102",
                "book": 1,
                "column": "102",
                "lines": [
                    {"n": n, "ref": str(n), "text": "g"} for n in (102, 103, 104)
                ],
                "speakers": [
                    {"line": 102, "offset": 0, "label": "Αν."},
                    {"line": 103, "offset": 4, "label": "ΚΗΡΥΞ"},
                ],
            },
            {
                "id": "1:105",
                "book": 1,
                "column": "105",
                "lines": [{"n": 105, "ref": "105", "text": "g"}],
                "speakers": [{"line": 105, "offset": 0, "label": "Αν."}],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Antigone</speaker>
      <l n="100">A long block of Antigone.</l>
      <l n="105">Still Antigone, five lines later.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, _report = _parse(
        tmp_path, tei, spine, aliases=SEVEN_ALIASES, sigla=SEVEN_SIGLA
    )
    assert english["english_covered_by"] == {}

    # Without the handover the same shape is covered as before.
    spine["segments"][1]["speakers"] = [{"line": 102, "offset": 0, "label": "Αν."}]
    english, _footnotes, _report = _parse(
        tmp_path, tei, spine, aliases=SEVEN_ALIASES, sigla=SEVEN_SIGLA
    )
    assert english["english_covered_by"] == {"1:102": "1:100"}


def test_a_paragraph_with_no_line_number_of_its_own_gets_no_tick(tmp_path: Path):
    """Agamemnon 1:1 (John, 2026-09-12): Smyth's "So now I am still watching"
    renders line 8 but opens a paragraph inside <l n="5">; it was ticked with
    the NEXT anchor (10) and "real", so the reader put it at 10. A paragraph
    with no anchor at all took the segment's first line mid-chunk (1@1081).
    Neither is the translator's marker: no tick, so the reader interpolates."""
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1",
                "book": 1,
                "column": "1",
                "lines": [{"n": n, "ref": str(n), "text": f"g{n}"} for n in range(1, 13)],
                "speakers": [{"line": 1, "offset": 0, "label": "A"}],
            }
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker>
      <l n="1">First part.</l>
      <l n="5">Second part. <milestone unit="para"/>So now I watch.</l>
      <l n="10">Tenth line here. <milestone unit="para"/>Loose paragraph.</l>
    </sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, _report = _parse(tmp_path, tei, spine)
    (chunk,) = english["chunks"]
    text = chunk["text"]
    assert [(t["n"], t["offset"]) for t in chunk["bekker"]] == [
        (1, 0),
        (5, text.index("Second")),
        (10, text.index("Tenth")),
    ]
    assert "So now I watch." in text and "Loose paragraph." in text


def test_nless_snap_reports_the_speaker_of_the_tick_line(tmp_path: Path):
    """P2i finding 6: the snap row names the speaker of the line it ticked,
    never the segment's joined speaker set.  (1:2 carries no English anchor
    of its own, so after C9 the paragraph still walks on to it.)"""
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1",
                "book": 1,
                "column": "1",
                "lines": [{"n": 1, "ref": "1", "text": "g"}],
                "speakers": [{"line": 1, "offset": 0, "label": "Αν."}],
            },
            {
                "id": "1:2",
                "book": 1,
                "column": "2",
                "lines": [{"n": n, "ref": str(n), "text": "g"} for n in (2, 3)],
                "speakers": [
                    {"line": 2, "offset": 0, "label": "Ισ."},
                    {"line": 3, "offset": 3, "label": "ΚΗΡΥΞ"},
                ],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><l n="1">The first line.<milestone unit="para"/>A second paragraph.</l></sp>
  </div>
</body></text></TEI>
"""
    _english, _footnotes, report = _parse(
        tmp_path, tei, spine, aliases=SEVEN_ALIASES, sigla=SEVEN_SIGLA
    )
    snap = next(row for row in report["snaps"] if row.get("kind") == "nless_para")
    assert snap["segment"] == "1:2"
    assert snap["greek_speaker"] == "Ismene"
    assert "/" not in snap["greek_speaker"]


# ── C2: a lettered repeat of an earlier plain anchor is skipped, not doubled ──

def test_lettered_repeat_of_earlier_plain_anchor_is_not_duplicated(tmp_path: Path):
    """C2 (fix-mechanisms brief round 2, eumenides #5): Murray's Eumenides
    reprints the ephymnion refrain verbatim under a lettered anchor
    (372a/375a) with no Greek line of its own to hold the second copy.
    Before the fix this re-attached to the base's own segment and wrote
    the sentence twice; the fix recognises the piece's own text as a
    VERBATIM repeat of that base's earlier occurrence and skips it."""
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:5",
                "book": 1, "column": "1",
                "lines": [{"n": 5, "ref": "5", "text": "g5"}],
                "speakers": [{"line": 5, "offset": 0, "label": "A"}],
            },
            {
                "id": "1:6",
                "book": 1, "column": "1",
                "lines": [{"n": 6, "ref": "6", "text": "g6"}],
                "speakers": [{"line": 6, "offset": 0, "label": "B"}],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker><l n="5">The refrain returns again in full.</l></sp>
    <sp><speaker>Beta</speaker><l n="6">A different line entirely.</l></sp>
    <sp><speaker>Alpha</speaker><l n="5a">The refrain returns again in full.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(tmp_path, tei, spine)
    by_id = {c["id"]: c for c in english["chunks"]}
    assert by_id["1:5"]["text"] == "The refrain returns again in full."
    assert report["anomalies"] == []


def test_lettered_answering_half_with_new_text_is_kept_not_treated_as_repeat(tmp_path: Path):
    """The repeat check must not swallow a genuine antilabe answering half
    just because it shares a base number with an earlier piece — only an
    IDENTICAL piece text is a repeat (Electra's `1221a`, a different
    sentence, must still attach)."""
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:5",
                "book": 1, "column": "1",
                "lines": [{"n": 5, "ref": "5", "text": "g5"}],
                "speakers": [
                    {"line": 5, "offset": 0, "label": "A"},
                    {"line": 5, "offset": 5, "label": "B"},
                ],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker><l n="5">Nothing that is untrue, said plainly.</l></sp>
    <sp><speaker>Beta</speaker><l n="5a">The man is alive?</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, _report = _parse(tmp_path, tei, spine)
    by_id = {c["id"]: c for c in english["chunks"]}
    assert "The man is alive?" in by_id["1:5"]["text"]


# ── C7: a multi-span speech's tail, displaced onto the next speech's own
# segment by a one-line collision, redirects back to its own speech ──────

def test_multi_span_tail_colliding_with_the_next_speech_redirects_back(tmp_path: Path):
    """C7 (fix-mechanisms brief round 2, prometheus-bound #4): Smyth's own
    line count sometimes runs a beat ahead of the Greek's real speech
    boundary for exactly one line, so a multi-span speech's LAST piece
    lands, by an exact ref match, on the segment the VERY NEXT speech also
    owns (PV 189-195 and others). The tail piece must merge back into its
    OWN speech's previous segment instead of opening the next speaker's
    segment with a foreign name."""
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1",
                "book": 1, "column": "1",
                "lines": [{"n": 1, "ref": "1", "text": "g1"}],
                "speakers": [{"line": 1, "offset": 0, "label": "A"}],
            },
            {
                "id": "1:2",
                "book": 1, "column": "1",
                "lines": [{"n": 2, "ref": "2", "text": "g2"}],
                "speakers": [{"line": 2, "offset": 0, "label": "B"}],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker>
      <l n="1">Alpha's own opening line,</l>
      <l n="2">as eager as I am to welcome him.</l>
    </sp>
    <sp><speaker>Beta</speaker><l n="2">Unfold the whole story.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(tmp_path, tei, spine)
    by_id = {c["id"]: c for c in english["chunks"]}
    # The tail merges back into Alpha's own segment 1:1, not 1:2.
    assert by_id["1:1"]["text"] == (
        "Alpha's own opening line, as eager as I am to welcome him."
    )
    assert by_id["1:1"]["turns"] == [
        {"offset": 0, "speaker": "Alpha", "display": "Alpha"}
    ]
    # Segment 1:2 opens cleanly with Beta's own, correctly-anchored speech.
    assert by_id["1:2"]["text"] == "Unfold the whole story."
    assert by_id["1:2"]["turns"] == [
        {"offset": 0, "speaker": "Beta", "display": "Beta"}
    ]
    assert report["speech_mismatch_count"] == 0


# ── C6: a two-speaker antilabe fixture (Electra's kommos shape) ─────────────

def test_antilabe_run_resyncs_by_position_not_number(tmp_path: Path):
    """C6 (fix-mechanisms brief round 2, electra-soph #2/#3/#12): Jebb's own
    ``<l n>`` increments once per antilabe SHARE, so once an edition packs
    two shares onto one Greek line his numbers run a half-line ahead of
    the Greek's; any half whose own number then lands on no Greek ref is
    dropped outright.  This reproduces electra-soph's own 827-831 shape at
    the smallest possible scale: two packed Greek lines (1 and 2, each
    Alpha then Beta), five English speeches numbered 1, 2, 3, 4, 4a — an
    orphan (2, no Greek ref) and a lettered answering half (4a) among
    them.  The fix must recover the orphan and place every half under the
    right speaker, in Greek order, not Jebb's."""
    spine = {
        "work": "test-play",
        "segments": [
            {
                "id": "1:1",
                "book": 1, "column": "1",
                "lines": [{"n": 1, "ref": "1", "text": "g1"}],
                "speakers": [
                    {"line": 1, "offset": 0, "label": "A"},
                    {"line": 1, "offset": 5, "label": "B"},
                ],
            },
            {
                "id": "1:3",
                "book": 1, "column": "1",
                "lines": [{"n": 3, "ref": "3", "text": "g3"}],
                "speakers": [
                    {"line": 3, "offset": 0, "label": "A"},
                    {"line": 3, "offset": 5, "label": "B"},
                ],
            },
            {
                "id": "1:9",
                "book": 1, "column": "1",
                "lines": [{"n": 9, "ref": "9", "text": "g9"}],
                "speakers": [{"line": 9, "offset": 0, "label": "A"}],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker><l n="1">Ah, me, ah, me!</l></sp>
    <sp><speaker>Beta</speaker><l n="2">My child, why do you weep?</l></sp>
    <sp><speaker>Alpha</speaker><l n="3" part="I">Give no cry of bad omen!</l></sp>
    <sp><speaker>Beta</speaker><l n="3a" part="F">You will break my heart!</l></sp>
    <sp><speaker>Alpha</speaker><l n="9">A long speech resumes here in step.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(tmp_path, tei, spine)
    by_id = {c["id"]: c for c in english["chunks"]}
    assert by_id["1:1"]["text"] == "Ah, me, ah, me! My child, why do you weep?"
    assert by_id["1:1"]["turns"] == [
        {"offset": 0, "speaker": "Alpha", "display": "Alpha"},
        {"offset": 16, "speaker": "Beta", "display": "Beta"},
    ]
    assert by_id["1:3"]["text"] == "Give no cry of bad omen! You will break my heart!"
    assert by_id["1:3"]["turns"] == [
        {"offset": 0, "speaker": "Alpha", "display": "Alpha"},
        {"offset": 25, "speaker": "Beta", "display": "Beta"},
    ]
    assert not any(a["kind"] == "unmatched_anchor" for a in report["anomalies"])
    # A plain, already-in-step speech elsewhere must not be disturbed.
    assert by_id["1:9"]["text"] == "A long speech resumes here in step."


# ---------------------------------------------------------------------------
# Lane C round 3, item 1: the transposition remap (S1, G3, G4)
# ---------------------------------------------------------------------------


def _line_seg(seg_id: str, refs: list[str], label: str) -> dict:
    """One Greek speech printing ``refs``, all spoken by ``label``."""
    first = int(re.match(r"\d+", refs[0]).group(0))
    return {
        "id": seg_id,
        "book": 1,
        "column": refs[0],
        "lines": [
            {"n": int(re.match(r"\d+", ref).group(0)), "ref": ref, "text": f"g{ref}"}
            for ref in refs
        ],
        "speakers": [{"line": first, "offset": 0, "label": label}],
    }


def test_transposition_remap_skipped_when_a_translator_folds_two_lines(
    tmp_path: Path,
):
    """Real corpus instance (S1, andromache; the sweep's root cause A): the
    spine prints 68, 69, 73, 70, 71, 72, so ``citation.transpositions``
    declares ``{start: 70, end: 72, before: 73}``.  Coleridge, though, gives
    the couplet 70+71 ONE ``<l n="70">`` and 72+73 one ``<l n="72">`` — the
    block's four printed lines carry three anchors, so "the translation's nth
    line is the edition's nth printed line" is simply false here.  Remapping
    anyway sends n=70 to ref 73 (the Maid's segment), invents a numeric drop
    that satisfies Rule A, and the repair cascade empties 1:70.  The anchors
    must keep their own numbers, and the skip must be reported."""
    spine = {
        "work": "andromache",
        "segments": [
            _line_seg("1:68", ["68", "69", "73"], "Θε."),
            _line_seg("1:70", ["70", "71"], "Ανδ."),
            _line_seg("1:72", ["72"], "Θε."),
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Maid</speaker><l n="68">Alas! poor lady, they intend to slay thy son.</l></sp>
    <sp><speaker>Andromache</speaker><l n="70">Ah me! Has she heard that my babe was put out of her reach?</l></sp>
    <sp><speaker>Maid</speaker><l n="72">I know not; and Menelaus has left the house to fetch him.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Maid": "Maid", "Andromache": "Andromache"},
        sigla={"Θε.": "Maid", "Ανδ.": "Andromache"},
        transpositions=[{"start": "70", "end": "72", "before": "73"}],
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert "Ah me! Has she heard" in by_id["1:70"]["text"]
    assert "Alas! poor lady" in by_id["1:68"]["text"]
    assert "I know not" in by_id["1:72"]["text"]
    assert report["speech_mismatches"] == []
    skipped = [
        a for a in report["anomalies"] if a["kind"] == "transposition_remap_skipped"
    ]
    assert len(skipped) == 1
    assert skipped[0]["reason"] == "anchors_not_one_per_printed_line"


def test_transposition_remap_merges_two_rows_over_one_printed_stretch(
    tmp_path: Path,
):
    """G4 (seven-against-thebes): the derived allowlist splits ONE printed
    rotation — 993, then 984-992, then 983 — into two rows
    (``{984,992,before:993}`` and ``{983,983,before:993}``).  Folding both
    rows' arithmetic into a single dict lets the second overwrite the first
    and every anchor in the stretch lands one line out.  Read the stretch off
    the spine's own printed order instead: the translation's 1st, 2nd, …
    line in it seats on the edition's 1st, 2nd, … printed ref."""
    spine = {
        "work": "seven-against-thebes",
        "segments": [
            _line_seg("1:982", ["982"], "ΧΟ."),
            _line_seg("1:986", ["986"], "ΑΝ."),   # printed 1st of the stretch
            _line_seg("1:984", ["984"], "ΙΣ."),   # printed 2nd
            _line_seg("1:985", ["985"], "ΑΝ."),   # printed 3rd
            _line_seg("1:983", ["983"], "ΙΣ."),   # printed 4th
            _line_seg("1:987", ["987"], "ΧΟ."),
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Chorus</speaker><l n="982">Chorus before.</l></sp>
    <sp><speaker>Antigone</speaker><l n="983">First printed of the four.</l></sp>
    <sp><speaker>Ismene</speaker><l n="984">Second printed of the four.</l></sp>
    <sp><speaker>Antigone</speaker><l n="985">Third printed of the four.</l></sp>
    <sp><speaker>Ismene</speaker><l n="986">Fourth printed of the four.</l></sp>
    <sp><speaker>Chorus</speaker><l n="987">Chorus after.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={
            "Chorus": "Chorus",
            "Antigone": "Antigone",
            "Ismene": "Ismene",
        },
        sigla={"ΧΟ.": "Chorus", "ΑΝ.": "Antigone", "ΙΣ.": "Ismene"},
        transpositions=[
            {"start": "984", "end": "985", "before": "986"},
            {"start": "983", "end": "983", "before": "986"},
        ],
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert by_id["1:986"]["text"] == "First printed of the four."
    assert by_id["1:984"]["text"] == "Second printed of the four."
    assert by_id["1:985"]["text"] == "Third printed of the four."
    assert by_id["1:983"]["text"] == "Fourth printed of the four."
    assert by_id["1:982"]["text"] == "Chorus before."
    assert by_id["1:987"]["text"] == "Chorus after."
    assert report["speech_mismatches"] == []


def test_transposition_row_whose_before_is_off_the_stretch_is_reported(
    tmp_path: Path,
):
    """G4 (bacchae 847-1392 "before" 1448a, orestes 1488b, rhesus 678-679):
    a derived row whose ``before`` is a lettered ref, or sits nowhere near
    the run it names, is not a rotation the primary can key against.  The
    old code int-parsed the bounds and returned silently; it must remap
    nothing AND say so."""
    spine = {
        "work": "bacchae",
        "segments": [
            _line_seg("1:146", ["146", "1448a"], "ΧΟ."),
            _line_seg("1:147", ["147"], "ΧΟ."),
            _line_seg("1:148", ["148"], "ΧΟ."),
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Chorus</speaker><l n="146">One.</l><l n="147">Two.</l><l n="148">Three.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Chorus": "Chorus"},
        sigla={"ΧΟ.": "Chorus"},
        # Bacchae's third derived row: the run 148 sits below a running
        # maximum set 700 lines earlier by one stray fragment ref, so
        # `before` names a ref nowhere near the run.
        transpositions=[{"start": "148", "end": "148", "before": "1448a"}],
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert "One." in by_id["1:146"]["text"]
    assert by_id["1:147"]["text"] == "Two."
    assert by_id["1:148"]["text"] == "Three."
    skipped = [
        a for a in report["anomalies"] if a["kind"] == "transposition_remap_skipped"
    ]
    assert len(skipped) == 1
    assert skipped[0]["reason"] == "before_outside_printed_stretch"


def test_rule_a_inversion_reads_the_raw_tei_number_not_the_remapped_one(
    tmp_path: Path,
):
    """G3 (Grok's read of round 1): C4 rewrites a piece's anchor BEFORE the
    jobs are built, so Rule A — "the translation's own ``<l n>`` runs
    backwards here, the number cannot be trusted" — was reading the rewritten
    number.  Every successful rotation ends in a numeric drop, so the remap
    manufactured its own repair evidence and any speaker disagreement on the
    wrap pair was moved off its line.  Rule A must read the number the TEI
    actually printed: 99, 100, 101 ascending is no inversion at all, and
    Delta's disagreement at the wrap stays where the rotation put it."""
    spine = {
        "work": "test-play",
        "segments": [
            _line_seg("1:100", ["100"], "A"),
            _line_seg("1:101", ["101"], "B"),
            _line_seg("1:99", ["99"], "G"),
            _line_seg("1:102", ["102"], "D"),
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker><l n="99">First printed.</l></sp>
    <sp><speaker>Beta</speaker><l n="100">Second printed.</l></sp>
    <sp><speaker>Delta</speaker><l n="101">Third printed.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Alpha": "Alpha", "Beta": "Beta", "Delta": "Delta"},
        sigla={"A": "Alpha", "B": "Beta", "G": "Gamma", "D": "Delta"},
        transpositions=[{"start": "99", "end": "99", "before": "101"}],
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert by_id["1:100"]["text"] == "First printed."
    assert by_id["1:101"]["text"] == "Second printed."
    # The rotation's wrap: Delta's line seats on 1:99 and merely disagrees
    # with the Greek about who speaks it. It must not be dragged to 1:102.
    assert by_id["1:99"]["text"] == "Third printed."
    assert "1:102" not in by_id
    mismatch = report["speech_mismatches"][0]
    assert mismatch["kind"] == "attribution_difference"
    assert mismatch["attached_to"] == "1:99"


def test_transposition_remap_stands_down_when_the_greek_speakers_contradict_it(
    tmp_path: Path,
):
    """Real corpus instance (hecuba 758/759; the same shape in
    iphigenia-at-aulis 653-665, iphigenia-in-tauris 1050/1051,
    phoenician-women 1747-1749, rhesus 334-338): a declared row can mean
    either of two things.  Either the two editions NUMBER the same verses
    differently and the translation's nth line in the stretch is the
    edition's nth printed line (Oedipus at Colonus 328-330, where Jebb
    renumbers his transposed line and Dain-Mazon keeps the vulgate number),
    or both editions number the verses alike and only the printed order
    differs — and then the anchor's own number is right.  Diggle prints
    Hecuba 759 before 758, but Coleridge's ``n="758"`` is Greek 758 and his
    ``n="759"`` is Greek 759: re-keying by printed position puts each on the
    other's line and the Greek's own speaker attributions say so, two
    disagreements where the numbers give none.  The remap must stand down
    whenever it scores strictly worse than leaving the anchors alone."""
    spine = {
        "work": "hecuba",
        "segments": [
            _line_seg("1:757", ["757"], "Αγ."),
            _line_seg("1:759", ["759"], "Εκ."),
            _line_seg("1:758", ["758"], "Αγ."),
            _line_seg("1:760", ["760"], "Εκ."),
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Agamemnon</speaker><l n="757">Before that.</l></sp>
    <sp><speaker>Agamemnon</speaker><l n="758">Well, but why do you call me to your aid?</l></sp>
    <sp><speaker>Hecuba</speaker><l n="759">It is a matter you little know of, king.</l></sp>
    <sp><speaker>Hecuba</speaker><l n="760">Do you see this corpse?</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Agamemnon": "Agamemnon", "Hecuba": "Hecuba"},
        sigla={"Αγ.": "Agamemnon", "Εκ.": "Hecuba"},
        transpositions=[{"start": "758", "end": "758", "before": "759"}],
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert by_id["1:758"]["text"] == "Well, but why do you call me to your aid?"
    assert by_id["1:759"]["text"] == "It is a matter you little know of, king."
    assert report["speech_mismatches"] == []
    stood_down = [
        a
        for a in report["anomalies"]
        if a["kind"] == "transposition_remap_skipped"
        and a["reason"] == "printed_keying_contradicted_by_greek_speakers"
    ]
    assert len(stood_down) == 1


def test_transposition_remap_stands_down_on_a_speaker_tie(tmp_path: Path):
    """Real corpus instance (Sol review of 6e8a9d6, finding 1: hippolytus
    104-107).  Barrett prints 104-105 after 107, and the stichomythia
    alternates Hippolytus/Attendants in BOTH texts, so the Greek's own
    attributions cannot tell the two readings apart: keying by printed
    position and keying by the anchors' own numbers each score zero
    speaker disagreements.  The corpus says the numbers are right in
    fourteen such tie stretches and printed position in one (oedipus-
    coloneus 328-330, which now says so on its own row), and the content
    agrees: Coleridge's ``n="104"`` is "'Mongst gods as well as men we have
    our several preferences", which translates Greek 104 ``ἄλλοισιν ἄλλος
    θεῶν τε κἀνθρώπων μέλει``.  So a tie stands down and is reported."""
    spine = {
        "work": "hippolytus",
        "segments": [
            _line_seg("1:106", ["106"], "Ιπ."),
            _line_seg("1:107", ["107"], "Θε."),
            _line_seg("1:104", ["104"], "Ιπ."),
            _line_seg("1:105", ["105"], "Θε."),
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Hippolytus</speaker><l n="104">’Mongst gods as well as men we have our several preferences.</l></sp>
    <sp><speaker>Attendants</speaker><l n="105">I wish thee luck, and wisdom too, so far as thou dost need it.</l></sp>
    <sp><speaker>Hippolytus</speaker><l n="106">No god, whose worship craves the night, hath charms for me.</l></sp>
    <sp><speaker>Attendants</speaker><l n="107">My son, we should avail us of the gifts that gods confer.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Hippolytus": "Hippolytus", "Attendants": "Attendants"},
        sigla={"Ιπ.": "Hippolytus", "Θε.": "Attendants"},
        transpositions=[{"start": "104", "end": "105", "before": "107"}],
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert by_id["1:104"]["text"] == (
        "’Mongst gods as well as men we have our several preferences."
    )
    assert by_id["1:107"]["text"] == (
        "My son, we should avail us of the gifts that gods confer."
    )
    assert report["speech_mismatches"] == []
    tied = [
        a
        for a in report["anomalies"]
        if a["kind"] == "transposition_remap_skipped"
        and a["reason"] == "printed_keying_not_favoured_by_greek_speakers"
    ]
    assert len(tied) == 1
    assert tied[0]["disagreements"] == {"by_number": 0, "by_printed": 0}


def test_a_row_declaring_printed_keying_overrides_the_speaker_evidence(
    tmp_path: Path,
):
    """The ``english_keyed: printed`` escape hatch (Sol finding 1's second
    half).  Which reading a play's translation follows is a per-play data
    call; the Greek's speakers are only evidence for it, and where they are
    silent (a tie) or misleading the manifest has to be able to say so.  A
    row that declares the printed keying is honoured whatever the speaker
    count says — a verified declaration outranks an inference, the same way
    a hand-written ``speakers.overrides`` entry outranks the synthesized
    one.  Shown here on the hecuba 758/759 spine, whose speakers argue
    AGAINST printed keying (two disagreements against none), so nothing but
    the declaration can produce this result."""
    spine = {
        "work": "hecuba",
        "segments": [
            _line_seg("1:757", ["757"], "Αγ."),
            _line_seg("1:759", ["759"], "Εκ."),
            _line_seg("1:758", ["758"], "Αγ."),
            _line_seg("1:760", ["760"], "Εκ."),
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Agamemnon</speaker><l n="757">Before that.</l></sp>
    <sp><speaker>Agamemnon</speaker><l n="758">Well, but why do you call me to your aid?</l></sp>
    <sp><speaker>Hecuba</speaker><l n="759">It is a matter you little know of, king.</l></sp>
    <sp><speaker>Hecuba</speaker><l n="760">Do you see this corpse?</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Agamemnon": "Agamemnon", "Hecuba": "Hecuba"},
        sigla={"Αγ.": "Agamemnon", "Εκ.": "Hecuba"},
        transpositions=[
            {
                "start": "758",
                "end": "758",
                "before": "759",
                "english_keyed": "printed",
            }
        ],
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    # 758 -> 759 and 759 -> 758, by printed position, as declared.
    assert by_id["1:759"]["text"] == "Well, but why do you call me to your aid?"
    assert by_id["1:758"]["text"] == "It is a matter you little know of, king."
    assert [
        a for a in report["anomalies"] if a["kind"] == "transposition_remap_skipped"
    ] == []


# ---------------------------------------------------------------------------
# Lane C round 3, item 3: Rule B refined (S3, G1, G2)
# ---------------------------------------------------------------------------


def test_lone_anchor_moves_when_its_seat_already_holds_another_line_of_english(
    tmp_path: Path,
):
    """Real corpus instances (S3: hecuba anchor 709, persians anchor 1076).
    Diggle prints Hecuba 709-710 as one ref; Coleridge numbers the Chorus's
    question 709 and Hecuba's answer 710, so his numbering runs one ahead of
    the Greek's through here.  Both anchors land on the one Greek seat, 710
    agreeing with it and 709 not — two English LINES on one Greek verse,
    which a translation never numbers.  C1 forbade every lone repair and so
    left the Chorus's question glued to the front of Hecuba's answer with
    1:708 bare.  A lone anchor may move when its seat already holds the
    English of a DIFFERENT line number that the Greek agrees with, and when
    the same-speaker speech it would move to holds no English of its own."""
    spine = {
        "work": "hecuba",
        "segments": [
            _line_seg("1:708", ["708"], "ΧΟ."),
            _line_seg("1:709-710", ["709-710", "711"], "ΕΚ."),
            _line_seg("1:713", ["713"], "ΧΟ."),
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Chorus Leader</speaker><l n="709">Who slew him then?</l></sp>
    <sp><speaker>Hecuba</speaker><l n="710">It was my own familiar friend, the knight of Thrace.</l></sp>
    <sp><speaker>Chorus Leader</speaker><l n="713">O horror! what will you say?</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Chorus Leader": "Chorus", "Hecuba": "Hecuba"},
        sigla={"ΧΟ.": "Chorus", "ΕΚ.": "Hecuba"},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert by_id["1:708"]["text"] == "Who slew him then?"
    assert (
        by_id["1:709-710"]["text"]
        == "It was my own familiar friend, the knight of Thrace."
    )
    assert report["speech_mismatches"][0]["kind"] == "speaker_repair"
    assert report["speech_mismatches"][0]["attached_to"] == "1:708"


def test_lone_anchor_stays_when_its_only_co_occupant_is_its_own_antilabe_half(
    tmp_path: Path,
):
    """The case C1 was written to protect, in its real shape (oedipus-tyrannus
    625, which Jebb splits into 625 part=I and 625a part=F).  Both halves sit
    on Greek 625, and the Ismene-half agrees with the Greek while the
    Creon-half does not — the same "seat already holds matching English"
    picture as Hecuba 709, except that the co-occupant is the SECOND HALF OF
    ITS OWN LINE.  That is what an antilabe is; it implies no slip in the
    numbering, so 625 keeps its line and stays an attribution difference
    even though Creon does speak 624 next door."""
    spine = {
        "work": "oedipus-tyrannus",
        "segments": [
            _line_seg("1:623", ["623"], "ΟΙ."),
            _line_seg("1:624", ["624"], "ΚΡ."),
            _line_seg("1:625", ["625"], "ΟΙ."),
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Oedipus</speaker><l n="623">Hardly.  I desire your death.</l></sp>
    <sp><speaker>Creon</speaker><l n="625" part="I">Are you resolved not to yield or believe?</l></sp>
    <sp><speaker>Oedipus</speaker><l n="625a" part="F">No, for you persuade me that you are unworthy of trust.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Oedipus": "Oedipus", "Creon": "Creon"},
        sigla={"ΟΙ.": "Oedipus", "ΚΡ.": "Creon"},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert "1:624" not in by_id
    assert by_id["1:625"]["text"].startswith("Are you resolved")
    assert report["speech_mismatches"][0]["kind"] == "attribution_difference"
    assert report["speech_mismatches"][0]["attached_to"] == "1:625"


def test_two_anchors_on_one_greek_line_are_one_source_line_not_two(
    tmp_path: Path,
):
    """Sol review of 6e8a9d6, finding 2: the crowded-seat rule exempted a
    co-occupant only when it carried the SAME integer n, which is the
    ``625``/``625a`` spelling of an antilabe.  A translator may instead
    number the two halves of one Greek line ``625`` and ``626``, and a
    range ref (``709-710``) or a prose seat can hold several anchors the
    same way.  Their bases differ, so the agreeing half counted as "the
    seat already holds a settled DIFFERENT line" and the disagreeing half
    was free to move — into a hole a correct neighbour was going to want.
    Two anchors that resolve to ONE printed Greek line or range are one
    source line whatever their numbers say; only a co-occupant on another
    line is evidence that two English lines have collapsed onto one verse.

    Here the edition prints one line for the halves the translator numbers
    625 and 626 and gives both halves to Oedipus and Creon, while the
    translator gives the second to the Chorus — who speaks 624, bare, next
    door.  Nothing may move: the disagreement is an ordinary attribution
    difference on its own line."""
    spine = {
        "work": "test-play",
        "segments": [
            _line_seg("1:623", ["623"], "ΟΙ."),
            _line_seg("1:624", ["624"], "ΧΟ."),
            {
                "id": "1:625",
                "book": 1,
                "column": "625",
                "lines": [{"n": 625, "ref": "625-626", "text": "g625"}],
                "speakers": [
                    {"line": 625, "offset": 0, "label": "ΟΙ."},
                    {"line": 625, "offset": 20, "label": "ΚΡ."},
                ],
            },
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Oedipus</speaker><l n="623">Hardly.  I desire your death.</l></sp>
    <sp><speaker>Oedipus</speaker><l n="625">Are you resolved not to yield?</l></sp>
    <sp><speaker>Chorus</speaker><l n="626">Cease, my lords, from strife.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Oedipus": "Oedipus", "Chorus": "Chorus", "Creon": "Creon"},
        sigla={"ΟΙ.": "Oedipus", "ΚΡ.": "Creon", "ΧΟ.": "Chorus"},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert "1:624" not in by_id
    assert by_id["1:625"]["text"] == (
        "Are you resolved not to yield? Cease, my lords, from strife."
    )
    assert report["speech_mismatches"][0]["kind"] == "attribution_difference"
    assert report["speech_mismatches"][0]["attached_to"] == "1:625"


def test_a_run_of_three_must_advance_line_by_line(tmp_path: Path):
    """G1 (Grok's read of round 1): Rule B counted consecutive NUMBERED JOBS,
    so three disagreements scattered across a speech — 1000, 1010, 1020, with
    nothing numbered between them — passed as "a run of three consecutive
    anchors" and every one of them was moved.  A drift is a drift only if it
    runs line by line; three anchors ten lines apart are three independent
    attribution differences and each stays on its own line."""
    spine = {
        "work": "test-play",
        "segments": [
            _line_seg("1:1000", ["1000"], "A"),
            _line_seg("1:1001", ["1001"], "B"),
            _line_seg("1:1010", ["1010"], "A"),
            _line_seg("1:1011", ["1011"], "B"),
            _line_seg("1:1020", ["1020"], "A"),
            _line_seg("1:1021", ["1021"], "B"),
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Beta</speaker><l n="1000">One.</l></sp>
    <sp><speaker>Beta</speaker><l n="1010">Two.</l></sp>
    <sp><speaker>Beta</speaker><l n="1020">Three.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Alpha": "Alpha", "Beta": "Beta"},
        sigla={"A": "Alpha", "B": "Beta"},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert by_id["1:1000"]["text"] == "One."
    assert by_id["1:1010"]["text"] == "Two."
    assert by_id["1:1020"]["text"] == "Three."
    assert [m["kind"] for m in report["speech_mismatches"]] == [
        "attribution_difference"
    ] * 3


def test_antilabe_halves_are_scored_by_their_own_mismatch_not_a_shared_one(
    tmp_path: Path,
):
    """G2 (Grok's read of round 1): the mismatch verdicts were kept in a dict
    keyed by the integer base, so an antilabe's two halves (``328`` and
    ``328a``) wrote to one slot and the last one won.  Here the FIRST half of
    1001 agrees with the Greek and the second does not: under a shared slot
    the agreeing half inherited the disagreeing one's verdict, 1000, 1001,
    1001a and 1002 read as four disagreements in a row, and Rule B moved
    every one of them onto Alpha's neighbouring speeches.  Scored per half,
    the agreeing half breaks the run and each disagreement stays put."""
    spine = {
        "work": "test-play",
        "segments": [
            _line_seg("1:999", ["999"], "A"),
            _line_seg("1:1000", ["1000"], "B"),
            {
                "id": "1:1001",
                "book": 1,
                "column": "1001",
                "lines": [{"n": 1001, "ref": "1001", "text": "g"}],
                "speakers": [
                    {"line": 1001, "offset": 0, "label": "A"},
                    {"line": 1001, "offset": 1, "label": "B"},
                ],
            },
            _line_seg("1:1002", ["1002"], "B"),
            _line_seg("1:1003", ["1003"], "A"),
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker><l n="1000">Disagrees here.</l></sp>
    <sp><speaker>Alpha</speaker><l n="1001" part="I">First half.</l></sp>
    <sp><speaker>Gamma</speaker><l n="1001a" part="F">Second half.</l></sp>
    <sp><speaker>Alpha</speaker><l n="1002">Disagrees here too.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Alpha": "Alpha", "Beta": "Beta", "Gamma": "Gamma"},
        sigla={"A": "Alpha", "B": "Beta"},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert by_id["1:1000"]["text"] == "Disagrees here."
    assert by_id["1:1001"]["text"] == "First half. Second half."
    assert by_id["1:1002"]["text"] == "Disagrees here too."
    assert "1:999" not in by_id
    assert "1:1003" not in by_id
    assert {m["kind"] for m in report["speech_mismatches"]} == {
        "attribution_difference"
    }


def test_a_crowded_seat_seeds_the_whole_run_it_belongs_to(tmp_path: Path):
    """Real corpus instance (suppliants-eur 1158-1161): Coleridge numbers the
    close of the kommos one ahead of Diggle, and only TWO of his anchors
    disagree with the Greek about their speaker — one short of Rule B's run
    of three — because his 1161 lands on the tail of the same Greek seat as
    his 1160 and inherits that speech's speaker.  That doubling IS the
    evidence: two English line numbers on one Greek seat.  It seeds the run,
    the run shifts back together (each member freeing the seat the next one
    needs), and 1:1158 stops being bare."""
    spine = {
        "work": "suppliants-eur",
        "segments": [
            _line_seg("1:1158", ["1158"], "ΠΑ."),
            _line_seg("1:1159", ["1159"], "ΧΟ."),
            _line_seg("1:1160", ["1160", "1161"], "ΠΑ."),
            _line_seg("1:1162", ["1162", "1163"], "ΧΟ."),
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Children</speaker><l n="1159">The weight of grief I have to bear hath crushed me utterly.</l></sp>
    <sp><speaker>Chorus</speaker><l n="1160">Come, let me clasp the ashes of my son to my bosom.</l></sp>
    <sp><speaker>Children</speaker><l n="1161">I weep to hear that piteous word.</l></sp>
    <sp><speaker>Chorus</speaker><l n="1163">My child, thou art undone.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, _report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Children": "Children", "Chorus": "Chorus"},
        sigla={"ΠΑ.": "Children", "ΧΟ.": "Chorus"},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert (
        by_id["1:1158"]["text"]
        == "The weight of grief I have to bear hath crushed me utterly."
    )
    assert (
        by_id["1:1159"]["text"] == "Come, let me clasp the ashes of my son to my bosom."
    )
    assert by_id["1:1160"]["text"] == "I weep to hear that piteous word."
    assert by_id["1:1162"]["text"] == "My child, thou art undone."


# ---------------------------------------------------------------------------
# Lane C round 3, item 5: C9 — an <l> resolved against its own <sp>
# ---------------------------------------------------------------------------


def test_a_speech_opening_on_the_previous_speakers_line_joins_its_own_speech(
    tmp_path: Path,
):
    """C9 (trachiniae findings 3, 4, 6): Jebb's numbering and Dain-Mazon's part
    company by one line at a speech boundary, so a speech's FIRST ``<l n>``
    names a line the previous Greek speech prints while the rest of the same
    ``<sp>`` sits correctly in the next.  The Old Man's 1017 printed at the
    end of Heracles's speech and Hyllus's segment then opened mid-sentence
    ("more than mine."); the Chorus's 881b did the same inside the Nurse's
    one-line speech, and 879b inside hers again.  A speech's own opening
    clause belongs with the rest of that speech, at the head of its turn —
    the mirror of C7's tail redirect.

    The head's own text carries the evidence for that (round 3b, item 3):
    each of these heads breaks off mid-sentence and its own next piece
    finishes the sentence, which is why the fixture quotes Jebb's 1017 in
    full, to its trailing comma, instead of the shortened line the first
    version of this test used."""
    spine = {
        "work": "trachiniae",
        "segments": [
            _line_seg("1:993", ["1014", "1015", "1016", "1017"], "ΗΡ."),
            _line_seg("1:1018", ["1018", "1019", "1020"], "ΠΡ."),
            _line_seg("1:1023", ["1023"], "ΗΡ."),
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Heracles</speaker><l n="1015">Will no one strike the head from this accursed body?</l></sp>
    <sp><speaker>Old Man</speaker><l n="1017">You are the man’s son, and this task exceeds my strength.  Help him, for the strength to save him is at your command,</l>
      <l n="1020a">more than mine.</l></sp>
    <sp><speaker>Heracles</speaker><l n="1023">Ah me!</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Heracles": "Heracles", "Old Man": "Old Man"},
        sigla={"ΗΡ.": "Heracles", "ΠΡ.": "Old Man"},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert (
        by_id["1:993"]["text"]
        == "Will no one strike the head from this accursed body?"
    )
    assert by_id["1:1018"]["text"] == (
        "You are the man’s son, and this task exceeds my strength. Help him, "
        "for the strength to save him is at your command, more than mine."
    )
    assert by_id["1:1018"]["turns"] == [
        {"offset": 0, "speaker": "Old Man", "display": "Old Man"}
    ]


def test_a_paragraph_stays_put_when_the_next_greek_speech_is_taken(tmp_path: Path):
    """C9 (trachiniae finding 5): a speakerless ``<sp>`` is split at each
    ``<milestone unit="para"/>`` so Agamemnon's packed elders (1348-1371)
    become one slice per utterance, and a slice with no ``<l n>`` of its own
    then walks on to the NEXT Greek segment.  Heracles's dying speech is one
    such ``<sp>``, with paragraph breaks inside ``<l n="1080">`` and
    ``<l n="1105">`` that are not new speakers at all, so two blocks of it
    were flushed into the Chorus's following couplet and his own speech
    carried a visible splice.  A paragraph may take the next Greek speech
    only when that speech has no English of its own; the Chorus's couplet
    carries its own ``<l n="1112">``, so the paragraphs stay where they are
    printed."""
    spine = {
        "work": "trachiniae",
        "segments": [
            _line_seg("1:1046", ["1046", "1080", "1081", "1105"], "ΗΡ."),
            _line_seg("1:1112", ["1112"], "ΧΟ."),
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp>
      <l n="1080">see how wretched I am!
        <milestone unit="para"/>Ah, misery!  The ruinous spasm flames again.
        <milestone unit="para"/>
      </l>
      <l n="1105">—I, who am reputed the seed of Zeus.</l>
    </sp>
    <sp><speaker>Chorus</speaker><l n="1112">Ah, unhappy Greece.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, _report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Heracles": "Heracles", "Chorus": "Chorus"},
        sigla={"ΗΡ.": "Heracles", "ΧΟ.": "Chorus"},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert "Ah, misery!" in by_id["1:1046"]["text"]
    # And an em-dash reached MID-LINE is punctuation, not a new voice: Jebb's
    # 1105 carries on the sentence 1100 began, so it keeps its own seat too.
    assert "seed of Zeus" in by_id["1:1046"]["text"]
    assert by_id["1:1112"]["text"] == "Ah, unhappy Greece."


def test_a_paragraph_takes_the_next_greek_speech_when_it_is_empty(
    tmp_path: Path,
):
    """The other half of the same rule (Agamemnon 1348-1371, and the Eumenides
    Furies at 255-275, and Seven's sisters' kommos): Smyth packs the elders'
    one-liners into one speakerless ``<sp>``, several of them inside a single
    ``<l n="1350">``.  Each of the Greek speeches they render is empty, so
    each paragraph walks on and takes one."""
    spine = {
        "work": "agamemnon",
        "segments": [
            _line_seg("1:1348", ["1348", "1349"], "ΧΟ."),
            _line_seg("1:1350", ["1350"], "ΧΟ."),
            _line_seg("1:1351", ["1351"], "ΧΟ."),
            _line_seg("1:1352", ["1352"], "ΧΟ."),
            _line_seg("1:1360", ["1360"], "ΧΟ."),
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp>
      <milestone unit="para"/><l n="1348">—I tell you my advice: summon the townsfolk.</l>
      <milestone unit="para"/><l n="1350">—To my thinking we must burst in.
        <milestone unit="para"/>—I, too, am for taking part in some such plan.
        <milestone unit="para"/>—It is plain.</l>
      <milestone unit="para"/><l n="1360">—I too am of this mind.</l>
    </sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, _report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Chorus": "Chorus"},
        sigla={"ΧΟ.": "Chorus"},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert by_id["1:1348"]["text"] == "—I tell you my advice: summon the townsfolk."
    assert by_id["1:1350"]["text"] == "—To my thinking we must burst in."
    assert by_id["1:1351"]["text"] == "—I, too, am for taking part in some such plan."
    assert by_id["1:1352"]["text"] == "—It is plain."
    assert by_id["1:1360"]["text"] == "—I too am of this mind."


def test_a_speech_head_joins_its_own_speech_after_the_previous_one_was_repaired(
    tmp_path: Path,
):
    """C10 (trojan-women 274/275): Coleridge's whole Talthybius/Hecuba
    exchange runs a line behind Diggle's, so Talthybius's answer is first
    moved onto 1:274 by the drift repair; Hecuba's next speech then opens
    with ``<l n="274">`` — "As for me" — which lands on that very segment and
    printed inside his answer, leaving her own segment to open mid-sentence
    ("whose hair is white with age").  The head belongs with the rest of her
    speech, so the test is against the segment the previous speech ACTUALLY
    landed on, repair included, not the one its number names."""
    spine = {
        "work": "trojan-women",
        "segments": [
            _line_seg("1:269", ["269", "270"], "ΕΚ."),
            _line_seg("1:271", ["271"], "ΤΑ."),
            _line_seg("1:272", ["272", "273"], "ΕΚ."),
            _line_seg("1:274", ["274"], "ΤΑ."),
            _line_seg("1:275", ["275", "276"], "ΕΚ."),
            _line_seg("1:277", ["277"], "ΤΑ."),
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Hecuba</speaker><l n="269">Alas for me! Is she still alive?</l></sp>
    <sp><speaker>Talthybius</speaker><l n="270">Her fate sets her free from trouble.</l></sp>
    <sp><speaker>Hecuba</speaker><l n="271">And what of the wife of Hector, sad Andromache?</l></sp>
    <sp><speaker>Talthybius</speaker><l n="273">She too was a chosen prize; Achilles’ son took her.</l></sp>
    <sp><speaker>Hecuba</speaker><l n="274">As for me</l>
      <l n="275">whose hair is white with age, whose servant am I to be?</l></sp>
    <sp><speaker>Talthybius</speaker><l n="277">Odysseus has taken you to be his slave.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, _report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Talthybius": "Talthybius", "Hecuba": "Hecuba"},
        sigla={"ΤΑ.": "Talthybius", "ΕΚ.": "Hecuba"},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert by_id["1:269"]["text"] == "Alas for me! Is she still alive?"
    assert by_id["1:271"]["text"] == "Her fate sets her free from trouble."
    assert by_id["1:272"]["text"] == (
        "And what of the wife of Hector, sad Andromache?"
    )
    assert by_id["1:274"]["text"] == (
        "She too was a chosen prize; Achilles’ son took her."
    )
    assert by_id["1:275"]["text"] == (
        "As for me whose hair is white with age, whose servant am I to be?"
    )
    assert by_id["1:277"]["text"] == "Odysseus has taken you to be his slave."


def test_a_whole_sentence_opening_a_speech_is_not_moved_off_its_own_line(
    tmp_path: Path,
):
    """Sol review of 6e8a9d6, finding 3 (real instance: trojan-women 160).
    The head redirect fired on speaker layout alone — the head disagrees
    with the Greek speaker of the line its number names, the next piece of
    the speech agrees with its own — and that pattern is also what a plain
    attribution difference looks like when the translator gives the
    previous speaker's last line to the incoming one.

    Coleridge's First Semi-Chorus ``n="160"`` is "The rower's hand is
    busy?", which renders Greek 160 ``κινεῖται κωπήρης χείρ`` — the second
    line of Hecuba's couplet, and Perseus says so in the file: "This part
    of the line is assigned to Hecuba in the translation and has been moved
    to align with the Greek."  Moving it to 1:161 takes Greek 160's only
    English off Greek 160 and leaves Hecuba's line ending on its dash.

    So the redirect now needs evidence in the TEXT that the head is a
    continuation and not an opening: the head begins mid-sentence, or it
    ends without terminal punctuation (Trachiniae's "Speak," / "Sure,",
    Trojan Women's "As for me").  A sentence that opens and closes is left
    where its own number puts it, flagged."""
    spine = {
        "work": "trojan-women",
        "segments": [
            _line_seg("1:157", ["157", "158"], "ΧΟ."),
            _line_seg("1:159", ["159", "160"], "ΕΚ."),
            _line_seg("1:161", ["161", "162"], "ΗΜ."),
            _line_seg("1:163", ["163"], "ΕΚ."),
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Chorus</speaker><l n="157">They mourn their slavish lot.</l></sp>
    <sp><speaker>Hecuba</speaker><l n="159">My child, even now at the ships of the Argives—</l></sp>
    <sp><speaker>First Semi-Chorus</speaker><l n="160">The rower’s hand is busy?</l>
      <l n="161">Ah, woe is me! what is their intent?</l></sp>
    <sp><speaker>Hecuba</speaker><l n="163">I do not know, though I guess our doom.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={
            "Chorus": "Chorus",
            "Hecuba": "Hecuba",
            "First Semi-Chorus": "Semichorus",
        },
        sigla={"ΧΟ.": "Chorus", "ΕΚ.": "Hecuba", "ΗΜ.": "Semichorus"},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert by_id["1:159"]["text"] == (
        "My child, even now at the ships of the Argives— "
        "The rower’s hand is busy?"
    )
    assert by_id["1:161"]["text"] == "Ah, woe is me! what is their intent?"
    flagged = [m for m in report["speech_mismatches"] if m["english_line"] == 160]
    assert flagged and flagged[0]["kind"] == "attribution_difference"
    assert flagged[0]["attached_to"] == "1:159"


def test_a_whole_sentence_head_still_moves_when_the_numbering_has_parted(
    tmp_path: Path,
):
    """The other half of the same rule (real instance: oedipus-coloneus
    148).  Asking every head for a split sentence would cost six moves that
    the Greek says are right, so the text test is asked for only where the
    head's own number is worth something — where the previous English
    speech numbered the line immediately before it.

    Jebb numbers Oedipus's five-line answer 144 and 146 only, so his
    lineation has already parted from Dain-Mazon's before the Chorus
    replies; his ``n="148"`` is "Alas! Were you sightless even from birth?",
    which renders Greek 149-150 ``Ἐή, ἀλαῶν ὀμμάτων / ἆρα καὶ ἦσθα
    φυτάλμιος;``.  A whole sentence, and it still belongs with the rest of
    its speech."""
    spine = {
        "work": "oedipus-coloneus",
        "segments": [
            _line_seg("1:144", ["144", "145", "146", "147", "148"], "ΟΙ."),
            _line_seg("1:149", ["149", "150", "152"], "ΧΟ."),
            _line_seg("1:153", ["153"], "ΟΙ."),
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Oedipus</speaker><l n="144">Not so wholly of the best fate, guardians of this land!</l>
      <l n="146">It is plain; otherwise I would not creep with the eyes of others.</l></sp>
    <sp><speaker>Chorus</speaker><l n="148">Alas! Were you sightless even from birth?</l>
      <l n="150">Evil have been your days, and many, it appears.</l></sp>
    <sp><speaker>Oedipus</speaker><l n="153">You shall not add this curse.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, _report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Oedipus": "Oedipus", "Chorus": "Chorus"},
        sigla={"ΟΙ.": "Oedipus", "ΧΟ.": "Chorus"},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert by_id["1:149"]["text"] == (
        "Alas! Were you sightless even from birth? "
        "Evil have been your days, and many, it appears."
    )
    assert "Alas!" not in by_id["1:144"]["text"]


# ---------------------------------------------------------------------------
# Lane C round 3, item 7: C11 — <note resp="perseus">l. N</note> as the anchor
# ---------------------------------------------------------------------------


def test_a_perseus_line_note_re_anchors_a_contested_line(tmp_path: Path):
    """C11 (suppliants-aesch 905-910): Smyth's ``<l n>`` follows one edition's
    numbering of the Herald scene and the spine's another, and the Perseus
    encoders recorded the answer in the text: ``<note resp="perseus">l.
    908</note>``.  The converter dropped those notes as non-Smyth, so four
    consecutive turns held the neighbouring turn's words in every column.

    The note is honoured only where it settles a contest — the spine gives
    the ``<l>``'s own number to somebody else and gives the note's number to
    this very speaker.  Three more notes in the same play (207, 209, 210)
    name lines whose own slots already agree with the speaker, and the build
    is right there: those are left alone."""
    spine = {
        "work": "suppliants-aesch",
        "segments": [
            _line_seg("1:903", ["903", "904"], "ΚΗ."),
            _line_seg("1:905", ["905"], "ΧΟ."),
            _line_seg("1:906", ["906", "907"], "ΚΗ."),
            _line_seg("1:908", ["908"], "ΧΟ."),
            _line_seg("1:909", ["909", "910"], "ΚΗ."),
            # The uncontested pair: both numbers already agree.
            _line_seg("1:207", ["207"], "ΔΑ."),
            _line_seg("1:209", ["209"], "ΔΑ."),
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Herald</speaker><l n="903">Get to the ship.</l></sp>
    <sp><speaker>Chorus</speaker><l n="904">We are lost!  O King, we suffer violence!<note resp="perseus">l. 908</note></l></sp>
    <sp><speaker>Herald</speaker><l n="905"><note resp="perseus">l. 906</note>You will soon see many kings.</l></sp>
    <sp><speaker>Chorus</speaker><l n="907">Listen!  Chiefs and rulers of the city!<note resp="perseus">l. 905</note></l></sp>
    <sp><speaker>Herald</speaker><l n="908">I will seize you by the hair.<note resp="perseus">l. 909</note></l></sp>
    <sp><speaker>Danaus</speaker><l n="207">May he behold you with a gracious eye.<note resp="perseus">l. 210</note></l></sp>
    <sp><speaker>Danaus</speaker><l n="209">Then do not delay.<note resp="perseus">l. 207</note></l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, _report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Herald": "Herald", "Chorus": "Chorus", "Danaus": "Danaus"},
        sigla={"ΚΗ.": "Herald", "ΧΟ.": "Chorus", "ΔΑ.": "Danaus"},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert by_id["1:903"]["text"] == "Get to the ship."
    assert by_id["1:905"]["text"] == "Listen! Chiefs and rulers of the city!"
    assert by_id["1:906"]["text"] == "You will soon see many kings."
    assert by_id["1:908"]["text"] == "We are lost! O King, we suffer violence!"
    assert by_id["1:909"]["text"] == "I will seize you by the hair."
    # Uncontested: the notes at 207 and 209 change nothing.
    assert by_id["1:207"]["text"] == "May he behold you with a gracious eye."
    assert by_id["1:209"]["text"] == "Then do not delay."


# ---------------------------------------------------------------------------
# Lane C round 3, item 8: C12 — Perseus <stage> tags as directions
# ---------------------------------------------------------------------------


def test_perseus_stage_tags_become_directions_before_the_speech(tmp_path: Path):
    """C12 (hecuba finding 5): every Perseus ``<stage>`` was dropped with the
    rest of ``_SKIP_TAGS`` — 47 in Hecuba alone, entrances and exits between
    speeches and asides ("stirring", "rising", "To Talthybius") at the head
    of one.  A direction that precedes a speech's own words is emitted as
    that turn's ``directionsBefore``, which the reader already renders.  One
    reached in the middle of a speech has no turn to hang on and no inline
    slot in a collapsed prose chunk, so it is counted as an anomaly rather
    than lost in silence."""
    spine = {
        "work": "hecuba",
        "segments": [
            _line_seg("1:216", ["216"], "ΧΟ."),
            _line_seg("1:218", ["218", "219"], "ΟΔ."),
            _line_seg("1:604", ["604", "605"], "ΕΚ."),
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Chorus Leader</speaker><l n="216">See where Odysseus comes in haste.</l></sp>
    <stage rend="italic">Odysseus enters with his attendants.</stage>
    <sp><speaker>Odysseus</speaker><l n="218"><stage rend="italic">rising</stage>Lady, I think you know the army’s will.</l></sp>
    <sp><speaker>Hecuba</speaker><l n="604">Go and proclaim to the Argives<stage rend="italic">Talthybius goes out.</stage></l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Chorus Leader": "Chorus", "Odysseus": "Odysseus", "Hecuba": "Hecuba"},
        sigla={"ΧΟ.": "Chorus", "ΟΔ.": "Odysseus", "ΕΚ.": "Hecuba"},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert by_id["1:218"]["turns"] == [
        {
            "offset": 0,
            "speaker": "Odysseus",
            "display": "Odysseus",
            "directionsBefore": [
                "Odysseus enters with his attendants.",
                "rising",
            ],
        }
    ]
    assert by_id["1:218"]["text"] == "Lady, I think you know the army’s will."
    assert by_id["1:216"]["turns"][0].get("directionsBefore") is None
    # Round 4 item 8: the mid-speech one is PRINTED where the edition prints
    # it, on its own line inside the prose, in the reader's own
    # `_direction_` convention (shared/lib/speakers.ts markStageDirections).
    assert by_id["1:604"]["text"] == (
        "Go and proclaim to the Argives\n_Talthybius goes out._"
    )
    mid = [a for a in report["anomalies"] if a["kind"] == "stage_direction_inline"]
    assert len(mid) == 1
    assert mid[0]["text"] == "Talthybius goes out."
    assert not [
        a for a in report["anomalies"] if a["kind"] == "stage_direction_mid_speech"
    ]


# ── Lane C, round 4 ───────────────────────────────────────────────────────


def test_deleted_text_is_kept_in_square_brackets(tmp_path: Path):
    """C13 (iphigenia-at-aulis finding 1, 2026-09-17): a Perseus `<del>` is
    the editor's deletion — text the edition PRINTS and brackets, never text
    that is absent.  The converter dropped every `<del>` unread, so ten lines
    of Agamemnon's prologue (IA 105-114) and four more passages vanished from
    the reader's default column with no trace in the build.  The Greek column
    prints those lines, so the English must too."""
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker>
      <l n="1">Kept <del>and cut</del> again.</l>
      <l n="2"><del rend="merge">Whole line deleted<note n="1" resp="Smyth">A note.</note>.</del></l>
    </sp>
    <sp><speaker>Beta</speaker><l n="5">Plain.</l></sp>
  </div>
</body></text></TEI>
"""
    english, footnotes, report = _parse(tmp_path, tei, _spine())
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert by_id["1:1"]["text"] == "Kept [and cut] again. [Whole line deleted[^1.1].]"
    assert list(footnotes) == ["1.1"]
    kept = [a for a in report["anomalies"] if a["kind"] == "deleted_text_kept"]
    assert [a["text"] for a in kept] == ["and cut", "Whole line deleted."]


def test_an_unprinted_english_line_number_attaches_to_its_printed_neighbour(
    tmp_path: Path,
):
    """C15 (andromache finding 5, 2026-09-17): an `<l n>` whose number the
    Greek edition does not print resolved to no segment at all and its text
    was dropped (Coleridge's 1203, his rendering of Diggle's 1204; 14 such
    lines across 11 plays).  It belongs beside the printed line next to it
    whose Greek speaker it shares, flagged, never nowhere."""
    spine = _spine()
    # 1:5 prints 5, 6, 8 — the translation numbers a Beta line 7.
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker><l n="1">Alpha line.</l></sp>
    <sp><speaker>Beta</speaker><l n="7">The unprinted line.</l></sp>
    <sp><speaker>Gamma</speaker><l n="10">Gamma line.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _f, report = _parse(tmp_path, tei, spine)
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert by_id["1:5"]["text"] == "The unprinted line."
    assert [a["kind"] for a in report["anomalies"]] == ["unprinted_ref"]
    row = report["anomalies"][0]
    assert row["n_raw"] == "7" and row["attached_to"] == "1:5" and row["ref"] == "6"
    assert not [a for a in report["anomalies"] if a["kind"] == "unmatched_anchor"]


def test_an_unprinted_line_number_far_from_the_spine_stays_unmatched(
    tmp_path: Path,
):
    """The other half of C15: Helen's TEI numbers one line `5563` (a typo for
    563).  A number nowhere near a printed line is not a neighbour of
    anything — it is a typo, and belongs in `english.primary.line_fixes`
    (C16), not seated by guesswork at the end of the play."""
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker><l n="1">Alpha line.</l></sp>
    <sp><speaker>Beta</speaker><l n="5563">A typo for five.</l></sp>
  </div>
</body></text></TEI>
"""
    _english, _f, report = _parse(tmp_path, tei, _spine())
    assert [a["kind"] for a in report["anomalies"]] == ["unmatched_anchor"]


def test_a_declared_line_fix_is_honoured_before_anchoring(tmp_path: Path):
    """C16 (iphigenia-in-tauris finding 5, 2026-09-17): Perseus files Thoas's
    1188 under `n="188"`, so it printed a thousand lines early, glued to the
    end of the Chorus's parodos with a Thoas turn inside it, and the manifest
    declared `1:1188` a gap to mask it.  A per-play
    `english.primary.line_fixes` maps the TEI's typo to the number the line
    really carries, before anything reads the anchor."""
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker><l n="1">Alpha line.</l></sp>
    <sp><speaker>Gamma</speaker><l n="3">Filed under the wrong number.</l></sp>
  </div>
</body></text></TEI>
"""
    plain, _f, _r = _parse(tmp_path, tei, _spine())
    assert "Filed under the wrong number." in {
        chunk["id"]: chunk["text"] for chunk in plain["chunks"]
    }["1:1"]
    fixed, _f, _r = _parse(tmp_path, tei, _spine(), line_fixes={"3": "10"})
    by_id = {chunk["id"]: chunk["text"] for chunk in fixed["chunks"]}
    assert by_id["1:1"] == "Alpha line."
    assert by_id["1:10"] == "Filed under the wrong number."


def _doublet_spine() -> dict:
    """One ref printed twice, with different text, and a line on either side."""
    def seg(sid: str, ref: str, text: str, label: str) -> dict:
        return {
            "id": sid,
            "book": 1,
            "column": ref,
            "lines": [{"n": 1, "ref": ref, "text": text}],
            "speakers": [{"line": 1, "offset": 0, "label": label}],
        }

    return {
        "work": "test-play",
        "segments": [
            seg("1:1", "1", "opening", "A"),
            seg("1:10", "10", "first printing", "B"),
            seg("1:11", "11", "between", "A"),
            seg("1:10.2", "10", "second printing, different words", "B"),
            seg("1:12", "12", "after", "A"),
        ],
    }


_DOUBLET_TEI = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker><l n="1">Alpha stays.</l></sp>
    <sp><speaker>Beta</speaker><l n="10">First English.</l></sp>
    <sp><speaker>Beta</speaker><l n="4">Second printing English.</l></sp>
    <sp><speaker>Alpha</speaker><l n="12">After.</l></sp>
  </div>
</body></text></TEI>
"""


def test_a_line_fix_can_name_a_repeated_refs_second_printing(tmp_path: Path):
    """A line_fixes value ``N.2`` is the second printing of a ref Murray
    prints twice. The first printing keeps the English anchored ``N``; the
    rewritten line lands on the ``.2`` segment. A raw ``<l n="N.2">`` is
    not that form and does not seat there."""
    english, _f, report = _parse(
        tmp_path, _DOUBLET_TEI, _doublet_spine(),
        line_fixes={"4": "10.2"},
        repeated_refs={"10": 2},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert by_id["1:10"]["text"] == "First English."
    assert by_id["1:10.2"]["text"] == "Second printing English."
    assert [b["n"] for b in by_id["1:10.2"]["bekker"]] == [10]
    assert not any(a.get("kind") == "non_numeric_anchor" for a in report["anomalies"])

    raw = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Beta</speaker><l n="10">First English.</l></sp>
    <sp><speaker>Beta</speaker><l n="10.2">Not a line fix.</l></sp>
  </div>
</body></text></TEI>
"""
    dropped, _f, dropped_report = _parse(
        tmp_path, raw, _doublet_spine(), repeated_refs={"10": 2},
    )
    assert "1:10.2" not in {chunk["id"] for chunk in dropped["chunks"]}
    assert any(a.get("kind") == "non_numeric_anchor" and a.get("n_raw") == "10.2"
               for a in dropped_report["anomalies"])


def test_a_line_fix_second_printing_of_an_undeclared_ref_raises(tmp_path: Path):
    """``N.2`` on a ref citation.repeated_refs does not declare is a stale
    fix. It raises, naming the manifest key and the value, rather than
    dropping the sentence."""
    with pytest.raises(ValueError, match=r"line_fixes.*10\.2"):
        _parse(
            tmp_path, _DOUBLET_TEI, _doublet_spine(),
            line_fixes={"4": "10.2"},
            repeated_refs={"11": 2},
        )


def test_a_line_fix_past_the_printing_count_raises(tmp_path: Path):
    """``N.3`` when the ref is printed only twice raises the same way."""
    with pytest.raises(ValueError, match=r"line_fixes.*10\.3"):
        _parse(
            tmp_path, _DOUBLET_TEI, _doublet_spine(),
            line_fixes={"4": "10.3"},
            repeated_refs={"10": 2},
        )


def test_a_line_fix_naming_a_second_printing_is_not_excused_from_alignment(tmp_path: Path):
    """Stage 2 still excuses a repeated-ref copy that no line_fix names.
    A value ``803.2`` withdraws that excuse: the second printing can own
    English, so an unmatched copy is a hole."""
    from drama_pipeline.stage2_validate import _play_line_allowed_twin_ids

    segs = [
        {"id": "1:803", "lines": [{"ref": "803", "text": "a"}]},
        {"id": "1:803.2", "lines": [{"ref": "803", "text": "b"}]},
    ]
    assert "1:803.2" in _play_line_allowed_twin_ids(_play_manifest(), segs)
    addressed = _play_manifest()
    addressed.data["english"]["primary"]["line_fixes"] = {"8": "803.2"}
    assert "1:803.2" not in _play_line_allowed_twin_ids(addressed, segs)


def test_a_line_fix_naming_no_such_anchor_raises(tmp_path: Path):
    """A fix map that matches no `<l n>`, or more than one, is a typo in the
    manifest and fails loudly rather than passing unread."""
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker><l n="1">Alpha line.</l><l n="1">Twice.</l></sp>
  </div>
</body></text></TEI>
"""
    with pytest.raises(ValueError, match="line_fixes"):
        _parse(tmp_path, tei, _spine(), line_fixes={"999": "10"})
    with pytest.raises(ValueError, match="line_fixes"):
        _parse(tmp_path, tei, _spine(), line_fixes={"1": "10"})


def test_a_transposition_overlap_refuses_a_mixed_english_keying():
    """Grok's read of 134dbe0: two overlapping `citation.transpositions` rows
    merge into one printed stretch, and the merge ORed `english_keyed:
    printed`, so one declaring row forced printed keying over the whole
    stretch.  Number keying is the default and printed the exception; a
    merged stretch whose rows disagree is a manifest the author has to
    settle, not a silent promotion."""
    from drama_pipeline.stage1_perseus_play_english import (
        _transposition_printed_stretches,
    )

    # Seven's real shape: 993 printed early, then 984-992, then 983.
    printed = ["980", "993"] + [str(n) for n in range(984, 993)] + ["983", "995"]
    rows = [
        {"start": "984", "end": "992", "before": "993"},
        {"start": "983", "end": "983", "before": "993"},
    ]
    merged, skipped = _transposition_printed_stretches(rows, printed)
    assert skipped == []
    assert [span for span, _forced in merged] == [list(range(1, 12))]
    assert [forced for _span, forced in merged] == [False]

    both, _skipped = _transposition_printed_stretches(
        [dict(row, english_keyed="printed") for row in rows], printed
    )
    assert [forced for _span, forced in both] == [True]

    mixed = [dict(rows[0], english_keyed="printed"), dict(rows[1])]
    with pytest.raises(ValueError, match="english_keyed"):
        _transposition_printed_stretches(mixed, printed)


def test_a_mid_speech_direction_keeps_the_text_around_it_intact(tmp_path: Path):
    """Round 4 item 8: a `<stage>` reached in the middle of a speech had no
    turn to hang on, so 375 of them across 33 plays were counted as lost and
    dropped.  They print inline, on their own line, between the words they
    interrupt — and the words on both sides stay whole."""
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker>
      <l n="1">Before the exit.<stage>Exit Alpha.</stage>After the exit.</l>
    </sp>
  </div>
</body></text></TEI>
"""
    english, _f, report = _parse(tmp_path, tei, _spine())
    by_id = {chunk["id"]: chunk["text"] for chunk in english["chunks"]}
    assert by_id["1:1"] == "Before the exit.\n_Exit Alpha._\nAfter the exit."
    assert [a["kind"] for a in report["anomalies"]] == ["stage_direction_inline"]


# ── Lane C, round 5 ─────────────────────────────────────────────────────


def test_a_mid_speech_stage_between_l_siblings_seats_beside_its_own_line(
    tmp_path: Path,
):
    """Sol's integration review, finding 1 (2026-09-18): a `<stage>` that is
    a SIBLING of `<l>` (not nested inside one) carries no anchor of its own,
    and the converter fell back to the whole slice's FIRST anchor for every
    such piece, wherever in the speech it actually sat.  Orestes' TEI
    (tlg0006.tlg016.perseus-eng2.xml:1671) has `spoken` before 1286, `sung`
    before 1288, and `spoken` before 1291: the head one is a real
    `directionsBefore`, but the other two both landed on 1286 (the speech's
    first line), and `1:1288`/`1:1291` got neither.  A mid-speech one must
    seat beside the NEXT line (printing before its text); one after the
    speech's last `<l>` seats beside the PREVIOUS line (printing after it)."""
    spine = {
        "work": "orestes",
        "segments": [
            _line_seg("1:1286", ["1286"], "Ηλ."),
            _line_seg("1:1288", ["1288", "1289"], "Ηλ."),
            _line_seg("1:1290", ["1290"], "Ηλ."),
            _line_seg("1:1291", ["1291"], "Ηλ."),
        ],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Electra</speaker>
      <stage resp="perseus">spoken</stage>
      <l n="1286">They do not hear; alas for my troubles!</l>
      <stage resp="perseus">sung</stage>
      <l n="1288">Soon some Argive in full armor, hurrying</l>
      <l n="1290">to her rescue, will attack the palace.</l>
      <stage resp="perseus">spoken</stage>
      <l n="1291">Keep a better look-out.</l>
    </sp>
  </div>
</body></text></TEI>
"""
    english, _f, report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Electra": "Electra"},
        sigla={"Ηλ.": "Electra"},
    )
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    # Before: both landed on 1286, and 1286 held both markers.
    assert by_id["1:1286"]["text"] == "They do not hear; alas for my troubles!"
    assert by_id["1:1286"]["turns"][0]["directionsBefore"] == ["spoken"]
    assert by_id["1:1288"]["text"] == (
        "_sung_\nSoon some Argive in full armor, hurrying"
    )
    assert by_id["1:1290"]["text"] == "to her rescue, will attack the palace."
    assert by_id["1:1291"]["text"] == "_spoken_\nKeep a better look-out."
    mid = [a for a in report["anomalies"] if a["kind"] == "stage_direction_inline"]
    assert [a["text"] for a in mid] == ["sung", "spoken"]


def test_an_unprinted_ref_tie_breaks_toward_the_earlier_line(tmp_path: Path):
    """Round 5, Grok's nit on d348247: two candidate seats at the same delta
    that agree with the speaker equally broke the tie toward the LOWER line
    number — the opposite of `_nearest_line`'s snap-forward convention used
    elsewhere in this module.  No real corpus instance reaches this exact
    tie (see the design paragraph on `_unprinted_ref_seat`), so round 5
    keeps the already-verified backward seat rather than flip a convention
    with nothing in the corpus to check the flip against.  This pins the
    decision itself, including the bekker tick the reader jumps to, which
    the round-4 test does not check."""
    spine = _spine()
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker><l n="1">Alpha line.</l></sp>
    <sp><speaker>Beta</speaker><l n="7">Equidistant from 6 and 8.</l></sp>
    <sp><speaker>Gamma</speaker><l n="10">Gamma line.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _f, report = _parse(tmp_path, tei, spine)
    by_id = {chunk["id"]: chunk for chunk in english["chunks"]}
    assert [a["kind"] for a in report["anomalies"]] == ["unprinted_ref"]
    row = report["anomalies"][0]
    assert row["ref"] == "6"
    assert [tick["n"] for tick in by_id["1:5"]["bekker"]] == [6]


# ── Lane C round 6: C6 stands down across a settled transposition ────────


def test_antilabe_walk_stands_down_across_a_one_to_one_transposition(
    tmp_path: Path,
):
    """Heracles 1185–1188. Diggle prints four antilabe lines out of numeric
    order (here 3, 4, 2, 1, declared as ``{start 2, before 4}`` and
    ``{start 1, before 4}``). The translation's own anchors already name
    those lines one for one — Alpha's ``n="1"`` translates Greek 1 — and
    the two orders legitimately differ. The walk matches by document
    position, so today it rotates every share onto the line printed in
    that slot. It must leave a settled stretch alone."""
    def antilabe(ref: str) -> dict:
        n = int(ref)
        return {
            "id": f"1:{ref}",
            "book": 1,
            "column": ref,
            "lines": [{"n": n, "ref": ref, "text": f"g{ref}"}],
            "speakers": [
                {"line": n, "offset": 0, "label": "Α."},
                {"line": n, "offset": 1, "label": "Β."},
            ],
        }

    # Printed order: 3, 4, 2, 1.
    spine = {
        "work": "test-play",
        "segments": [antilabe("3"), antilabe("4"), antilabe("2"), antilabe("1")],
    }
    tei = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Alpha</speaker><l n="1">Alpha on one.</l></sp>
    <sp><speaker>Beta</speaker><l n="1a">Beta on one.</l></sp>
    <sp><speaker>Alpha</speaker><l n="2">Alpha on two.</l></sp>
    <sp><speaker>Beta</speaker><l n="2a">Beta on two.</l></sp>
    <sp><speaker>Alpha</speaker><l n="3">Alpha on three.</l></sp>
    <sp><speaker>Beta</speaker><l n="3a">Beta on three.</l></sp>
    <sp><speaker>Alpha</speaker><l n="4">Alpha on four.</l></sp>
    <sp><speaker>Beta</speaker><l n="4a">Beta on four.</l></sp>
  </div>
</body></text></TEI>
"""
    english, _footnotes, _report = _parse(
        tmp_path,
        tei,
        spine,
        aliases={"Alpha": "Alpha", "Beta": "Beta"},
        sigla={"Α.": "Alpha", "Β.": "Beta"},
        transpositions=[
            {"start": "2", "end": "2", "before": "4"},
            {"start": "1", "end": "1", "before": "4"},
        ],
    )
    by_id = {chunk["id"]: chunk["text"] for chunk in english["chunks"]}
    assert by_id["1:1"] == "Alpha on one. Beta on one."
    assert by_id["1:2"] == "Alpha on two. Beta on two."
    assert by_id["1:3"] == "Alpha on three. Beta on three."
    assert by_id["1:4"] == "Alpha on four. Beta on four."


def _kommos_spine() -> dict:
    """Seven 994-1001 in Murray: two antilabe lines, then one line each,
    alternating Antigone and Ismene."""
    def seg(ref: str, *labels: str) -> dict:
        return {
            "id": f"1:{ref}",
            "book": 1,
            "column": "1",
            "lines": [{"n": int(ref), "ref": ref, "text": f"g{ref}"}],
            "speakers": [
                {"line": int(ref), "offset": i, "label": label}
                for i, label in enumerate(labels)
            ],
        }

    return {
        "work": "test-play",
        "segments": [
            seg("994", "Αν.", "Ισ."),
            seg("995", "Αν.", "Ισ."),
            seg("996", "Αν."),
            seg("997", "Ισ."),
            seg("998", "Αν."),
            seg("1000", "Ισ."),
            seg("1001", "Αν."),
        ],
    }


_KOMMOS_TEI = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
  <div type="translation">
    <sp><speaker>Antigone</speaker><l n="1000">Oh, the grief—</l></sp>
    <sp><speaker>Ismene</speaker><l n="1001">Oh, the evils—</l></sp>
    <sp><speaker>Antigone</speaker><l n="1002">For home and land.</l></sp>
    <sp><speaker>Ismene</speaker><l n="1003">Above all for me,</l></sp>
    <sp><speaker>Antigone</speaker><l n="1004">And more also for me.</l></sp>
    <sp><speaker>Ismene</speaker><l n="1005">Ah I pity your suffering.</l></sp>
    <sp><speaker>Antigone</speaker><l n="1006">Pity for you both.</l></sp>
    <sp><speaker>Ismene</speaker><l n="1007">You were possessed.</l></sp>
  </div>
</body></text></TEI>
"""


def test_a_line_fixed_anchor_is_not_moved_by_speaker(tmp_path: Path):
    """Seven 996-1004 (S11 sweep row 853, 2026-09-25): Smyth numbers the
    dirge by the vulgate and gives each line from 1003 on to the other
    sister, so every line disagrees with Murray about its speaker.  The
    manifest's ``line_fixes`` keys each Smyth line to the Murray line it
    renders.  That placement is the manifest's own reading of the Greek:
    neither the speaker repair (a run of three mismatches) nor the antilabe
    walk may move the line off it by speaker.  The speaker difference stays
    as a flagged attribution difference on the line's own seat."""
    fixes = {
        "1000": "994", "1001": "994", "1002": "995", "1003": "996",
        "1004": "997", "1005": "998", "1006": "1000", "1007": "1001",
    }
    english, _f, report = _parse(
        tmp_path,
        _KOMMOS_TEI,
        _kommos_spine(),
        aliases={"Antigone": "Antigone", "Ismene": "Ismene"},
        sigla={"Αν.": "Antigone", "Ισ.": "Ismene"},
        line_fixes=fixes,
    )
    by_id = {chunk["id"]: chunk["text"] for chunk in english["chunks"]}
    assert by_id["1:994"] == "Oh, the grief— Oh, the evils—"
    assert by_id["1:995"] == "For home and land."
    assert by_id["1:996"] == "Above all for me,"
    assert by_id["1:997"] == "And more also for me."
    assert by_id["1:998"] == "Ah I pity your suffering."
    assert by_id["1:1000"] == "Pity for you both."
    assert by_id["1:1001"] == "You were possessed."
    assert not [m for m in report["speech_mismatches"] if m["kind"] == "speaker_repair"]
    flagged = {m["english_line"] for m in report["speech_mismatches"]}
    assert flagged == {996, 997, 998, 1000, 1001}


def test_an_unfixed_run_of_speaker_mismatches_is_still_repaired(tmp_path: Path):
    """The other half: with no ``line_fixes``, a run of three or more
    mismatching anchors is still evidence the numbers slipped (Rule B), and
    the repair still moves them."""
    tei = _KOMMOS_TEI
    for old, new in (("1000", "994"), ("1002", "995"), ("1003", "996"),
                     ("1004", "997"), ("1005", "998"), ("1006", "1000"),
                     ("1007", "1001")):
        tei = tei.replace(f'n="{old}"', f'n="{new}"')
    tei = tei.replace('<l n="1001">Oh, the evils', '<l n="994">Oh, the evils')
    _english, _f, report = _parse(
        tmp_path,
        tei,
        _kommos_spine(),
        aliases={"Antigone": "Antigone", "Ismene": "Ismene"},
        sigla={"Αν.": "Antigone", "Ισ.": "Ismene"},
    )
    assert [m for m in report["speech_mismatches"] if m["kind"] == "speaker_repair"]


def test_a_line_fix_onto_a_number_the_translation_also_prints_is_exempt(
    tmp_path: Path,
):
    """Codex review of 5c9b7c4, finding 1: the exemption was inferred from
    the number a fix produced, less every number the translation prints
    unfixed.  Seven prints ``<l n="971">`` unfixed while the manifest maps
    ``972: "971"``, so the fixed line lost its exemption.  The exemption now
    follows the ``<l>`` element a fix rewrote: here Ismene's line fixed onto
    996 shares the number with Antigone's unfixed 996, and the speaker repair
    must still leave it on 996."""
    fixes = {
        "1000": "994", "1001": "994", "1002": "995", "1003": "996",
        "1004": "997", "1005": "998", "1006": "1000", "1007": "1001",
    }
    tei = _KOMMOS_TEI.replace(
        '<sp><speaker>Ismene</speaker><l n="1003">',
        '<sp><speaker>Antigone</speaker><l n="996">Unfixed.</l></sp>\n'
        '    <sp><speaker>Ismene</speaker><l n="1003">',
    )
    english, _f, report = _parse(
        tmp_path,
        tei,
        _kommos_spine(),
        aliases={"Antigone": "Antigone", "Ismene": "Ismene"},
        sigla={"Αν.": "Antigone", "Ισ.": "Ismene"},
        line_fixes=fixes,
    )
    by_id = {chunk["id"]: chunk["text"] for chunk in english["chunks"]}
    assert by_id["1:995"] == "For home and land."
    assert by_id["1:996"] == "Unfixed. Above all for me,"
    assert by_id["1:997"] == "And more also for me."
    assert by_id["1:998"] == "Ah I pity your suffering."
    assert not [m for m in report["speech_mismatches"] if m["kind"] == "speaker_repair"]


def test_a_note_inside_a_fixed_line_keeps_the_fixed_mark(tmp_path: Path):
    """Codex review of ab7cdc4: a note marker inside a line-fixed <l> was
    added without the fixed mark, so the mark-aware merge split the line
    into separate pieces ("Above all [^1.1] for me," with extra ticks) and
    the marker's piece lost its seat exemption."""
    fixes = {
        "1000": "994", "1001": "994", "1002": "995", "1003": "996",
        "1004": "997", "1005": "998", "1006": "1000", "1007": "1001",
    }
    tei = _KOMMOS_TEI.replace(
        '<l n="1003">Above all for me,</l>',
        '<l n="1003">Above all<note n="1" resp="Smyth">A note.</note> for me,</l>',
    )
    english, _f, report = _parse(
        tmp_path,
        tei,
        _kommos_spine(),
        aliases={"Antigone": "Antigone", "Ismene": "Ismene"},
        sigla={"Αν.": "Antigone", "Ισ.": "Ismene"},
        line_fixes=fixes,
    )
    by_id = {chunk["id"]: chunk["text"] for chunk in english["chunks"]}
    assert by_id["1:996"] == "Above all[^1.1] for me,"
    assert not [m for m in report["speech_mismatches"] if m["kind"] == "speaker_repair"]
