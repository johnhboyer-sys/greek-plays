"""Re-keying a translation's line anchors onto another Greek edition's count.

Jebb's English is anchored in the count of Perseus's Greek (Storr's); Jebb's own
Greek counts differently in places. `english.<slot>.anchor_map` (declared under
`greek_editions[i].alignment.<pair>`) maps each English anchor by the text of
the two Greek editions and touches nothing else.
"""
import copy
import json
from pathlib import Path

import pytest

from drama_pipeline.anchor_map import build_anchor_map, remap_anchor
from drama_pipeline.config import Manifest
from drama_pipeline.stage1_perseus_play_english import parse_translation
from drama_pipeline.stage1_turn_english import _SiglaResolver

STORR = [
    {"ref": "1", "text": "alpha beta gamma delta epsilon"},
    {"ref": "2", "text": "zeta eta theta iota kappa"},
    {"ref": "3", "text": "lambda mu nu xi omicron"},
    {"ref": "4", "text": "pi rho"},                       # too short to match
    {"ref": "5", "text": "phi chi psi omega alpha"},
    {"ref": "6", "text": "tau"},                          # last line, short: no neighbour after it
]
# The target prints one line the source does not (3), so every later number moves up by one.
JEBB = [
    {"ref": "1", "text": "alpha beta gamma delta epsilon"},
    {"ref": "2", "text": "zeta eta theta iota kappa"},
    {"ref": "3", "text": "an added line of the other edition"},
    {"ref": "4", "text": "lambda mu nu xi omicron"},
    {"ref": "5", "text": "pi rho"},
    {"ref": "6", "text": "phi chi psi omega alpha"},
    {"ref": "7", "text": "tau"},
]

TEI = """\
<TEI><div type="translation">
  <sp><speaker>Alpha</speaker>
    <l n="0">Alpha</l>
    <l n="2">Second.</l>
    <l n="3">Third, which the other edition numbers four.</l>
    <l n="4">Fourth, a short line the text cannot match.</l>
    <l n="5">Fifth, which the other edition numbers six.</l>
    <l n="6">Sixth, the last short line.</l>
  </sp>
</div></TEI>
"""


def _spine() -> dict:
    return {
        "work": "test-play",
        "segments": [{
            "id": "1:1", "book": 1, "column": "1",
            "lines": [{"n": i + 1, "ref": line["ref"], "text": line["text"]} for i, line in enumerate(JEBB)],
            "speakers": [{"line": 1, "offset": 0, "label": "A"}],
        }],
    }


def _parse(tmp_path: Path, *, anchor_map=None, line_fixes=None):
    xml_path = tmp_path / "play.xml"
    xml_path.write_text(TEI, encoding="utf-8")
    return parse_translation(
        xml_path, _spine(), work_id="test-play", translation_id="jebb",
        sigla={"A": "Alpha"}, english_aliases={"Alpha": "Alpha"},
        line_fixes=line_fixes, anchor_map=anchor_map,
    )


def _map():
    mapping, inferred = build_anchor_map(STORR, JEBB)
    return mapping, inferred, [line["ref"] for line in JEBB], "storr-loeb"


def test_a_source_line_maps_to_the_target_line_with_the_same_text():
    mapping, inferred = build_anchor_map(STORR, JEBB)
    assert mapping["3"] == "4" and mapping["5"] == "6" and mapping["1"] == "1"
    assert "3" not in inferred


def test_a_short_line_between_two_matches_that_agree_takes_their_offset():
    mapping, inferred = build_anchor_map(STORR, JEBB)
    assert mapping["4"] == "5" and inferred == {"4"}


def test_a_line_with_no_neighbour_after_it_stays_unmapped():
    mapping, _ = build_anchor_map(STORR, JEBB)
    assert "6" not in mapping
    assert remap_anchor("6", mapping, {line["ref"] for line in JEBB}) is None


def test_a_lettered_anchor_keeps_its_letter_only_where_the_target_has_it():
    mapping = {"10": "11"}
    assert remap_anchor("10b", mapping, {"11", "11b"}) == "11b"
    assert remap_anchor("10b", mapping, {"11"}) == "11"
    assert remap_anchor("10b", {"10b": "12"}, {"12"}) == "12"


def test_parse_translation_rekeys_anchors_and_reports_the_one_it_could_not(tmp_path):
    _english, _notes, report = _parse(tmp_path, anchor_map=_map())
    block = report["anchor_map"]
    assert block["source_edition"] == "storr-loeb"
    assert {(m["from"], m["to"]) for m in block["moved_anchors"]} == {("3", "4"), ("4", "5"), ("5", "6")}
    assert block["unmatched"] == ["6"]
    assert block["inferred"] == 1 and block["anchors"] == 5
    assert block["present_after"] == 5


def test_an_edition_line_fix_beats_the_map(tmp_path):
    _english, _notes, report = _parse(tmp_path, anchor_map=_map(), line_fixes={"3": "2"})
    moved = {(m["from"], m["to"]) for m in report["anchor_map"]["moved_anchors"]}
    assert ("3", "4") not in moved and ("3", "2") not in moved   # the fix's line is left as fixed
    assert report["anchor_map"]["anchors"] == 4


def test_no_anchor_map_leaves_the_build_as_it_was(tmp_path):
    with_none = _parse(tmp_path)
    plain = _parse(tmp_path, anchor_map=None)
    assert "anchor_map" not in with_none[2]
    assert json.dumps(with_none[0], sort_keys=True) == json.dumps(plain[0], sort_keys=True)


def test_jebb_editions_declare_the_map_and_the_reference_does_not():
    for play in ("oedipus-tyrannus", "oedipus-coloneus", "antigone", "electra-soph", "ajax"):
        reference = Manifest.for_work(play)
        assert "anchor_map" not in reference.data["english"]["primary"]
        assert not hasattr(reference, "anchor_editions")
        view = reference.for_edition("jebb")
        assert view.data["english"]["primary"]["anchor_map"] == "storr-loeb"
        assert set(view.anchor_editions) == {"storr-loeb"}
        # Reference data is not touched by building the view.
        assert "anchor_map" not in reference.data["english"]["primary"]
        # Other editions of the play carry no map.
        other = reference.for_edition("storr-loeb")
        assert other.anchor_editions == {}
        assert all("anchor_map" not in slot for slot in other.data["english"].values() if isinstance(slot, dict))


def test_a_map_must_name_another_declared_edition():
    reference = Manifest.for_work("ajax")
    for bad in ("jebb", "no-such-edition"):
        data = copy.deepcopy(reference.data)
        next(e for e in data["greek_editions"] if e["id"] == "jebb")["alignment"]["jebb"]["anchor_map"] = bad
        with pytest.raises(ValueError, match="anchor_map"):
            Manifest(data, reference.path).for_edition("jebb")
