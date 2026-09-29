"""The Jebb OCR -> TEI converter (scripts/ocr/jebb_to_tei.py): review-fix tests."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("jebb_to_tei", ROOT / "scripts" / "ocr" / "jebb_to_tei.py")
J = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(J)

VERSE = ["ἀρχὴ λόγου πολλὴ καλή", "δεύτερον ἔπος ἐστὶν τόδε", "τρίτον δὲ ῥῆμα μακρὸν",
         "τέταρτον ἔπος ἐστὶν νόμος", "πέμπτον ἔπος ἐστὶ κάλλιστον", "ἕκτον δὲ τέλος ἐστὶ βραχύ"]


@pytest.fixture
def play(tmp_path, monkeypatch):
    """A one-page fake play 't' whose text file holds the given lines."""
    def make(rows):
        text = ["---", "ΣΟΦΟΚΛΕΟΥΣ", "10", *rows, "---"]
        (tmp_path / "t.txt").write_text("\n".join(text) + "\n", encoding="utf-8")
        monkeypatch.setattr(J, "GENIE", tmp_path)
        monkeypatch.setitem(J.PLAYS, "t", ("t.txt", "004", "x", 1, len(text)))
    return make


def ref_keys():
    return [J.key(v) for v in VERSE]


def test_a_latin_slip_row_no_longer_drops_the_verse_after_it(play):
    # Row 4 has a verse word read in Latin letters: it stops the block. The
    # rows after it still match reference lines, so the block goes on.
    play([VERSE[0], VERSE[1], VERSE[2], "τέταρτον ἔπος ἐστὶν nomos", VERSE[4], VERSE[5],
          "**5 πέμπτον** Latin comment", "cf. Latin note"])
    rows, log, stops = J.extract("t", ref_keys())
    assert [r["text"] for r in rows] == [VERSE[0], VERSE[1], VERSE[2], VERSE[4], VERSE[5]]
    first, second = stops
    assert (first["page"], first["src"], first["reason"]) == (10, 7, "apparatus text")
    assert first["dropped"] == [7] and first["resumed_at"] == 8
    assert second["reason"] == "apparatus marker" and second["resumed_at"] is None
    assert second["dropped"] == [10, 11]


def test_every_stop_is_reported_with_the_verse_like_rows_it_dropped(play):
    # No reference to check against: the block stops at the slip, and the
    # report names the stop and the verse rows dropped after it.
    play([VERSE[0], "τέταρτον ἔπος ἐστὶν nomos", VERSE[4], VERSE[5]])
    rows, log, stops = J.extract("t")
    assert [r["text"] for r in rows] == [VERSE[0]]
    (stop,) = stops
    assert (stop["src"], stop["reason"], stop["dropped"]) == (5, "apparatus text", [5, 6, 7])
    assert [s[0] for s in stop["suspect"]] == [6, 7]


def test_a_long_line_stop_is_reported_too(play):
    play([VERSE[0], "ἀρχὴ " * 20, VERSE[1]])
    rows, log, stops = J.extract("t", ref_keys())
    assert [r["text"] for r in rows] == [VERSE[0], VERSE[1]]
    assert stops[0]["reason"] == "row over 90 characters"


def test_a_name_row_before_the_resuming_verse_comes_back_with_it(play):
    play([VERSE[0], "τέταρτον ἔπος ἐστὶν nomos", "ΧΟΡΟΣ.", VERSE[4], "**5 πέμπτον** Latin"])
    rows, log, stops = J.extract("t", ref_keys())
    assert [(r["kind"], r["text"]) for r in rows] == [("verse", VERSE[0]), ("name", "ΧΟΡΟΣ"), ("verse", VERSE[4])]
    assert stops[0]["dropped"] == [5]


def _turn_rows():
    base = {"kind": "verse", "colon": None, "strophe": None, "speaker": None, "page": 1}
    return [{**base, "text": "ἀρχὴ λόγου πολλὴ", "printed": 1190, "turn": False, "src": 1},
            {**base, "text": "καλή", "printed": 1191, "turn": True, "src": 2}]


def test_a_turn_over_keeps_its_own_printed_number_beside_the_targets():
    (joined,) = J.join_turnovers(_turn_rows(), [J.key(VERSE[0])])
    assert joined["text"] == "ἀρχὴ λόγου πολλὴ καλή"
    assert joined["printed"] == 1190 and joined["printed_more"] == [1191]


def _joined_line(more, next_n="1193"):
    (joined,) = J.join_turnovers(_turn_rows(), [J.key(VERSE[0])])
    joined["printed_more"] = more
    joined.update(n="1190", shares=[(None, joined["text"])])
    follow = {"kind": "verse", "text": "x", "printed": None, "n": next_n, "page": 1, "src": 3, "shares": [(None, "x")]}
    return [joined, follow]


def test_both_printed_numbers_reach_the_tei_and_the_check():
    lines = _joined_line([1191])
    assert 'rend="margin-1190 margin-1191 turn"' in J.write_tei("antigone", lines)
    assert J.check_margins("antigone", lines) == []
    assert lines[0]["margin_ok"] == "equal"
    # The turn-over's number lies beyond the next line's: reported.
    bad = J.check_margins("antigone", _joined_line([1195]))
    assert [b["printed"] for b in bad] == [1195]


def _fix_case(monkeypatch, fix_n, lemma_n):
    ref = [{"n": str(k), "text": t, "parts": []} for k, t in enumerate(VERSE[:3], 1)]
    refs = {"S": ref, "T": ref}
    covers = {"S": [[0], [1], [2]], "T": [[0], [1], [2]]}
    jebb = [{"text": t, "src": 10 + k, "page": 1, "printed": None} for k, t in enumerate(VERSE[:3])]
    monkeypatch.setattr(J, "lemma_checkpoints", lambda slug, jebb: {2: [lemma_n]})
    monkeypatch.setitem(J.NUMBER_FIXES, "t", {12: (fix_n, "hand fix")})
    J.number_lines("t", jebb, refs, covers)
    return jebb


def test_a_hand_fix_against_a_commentary_lemma_is_reported(monkeypatch):
    jebb = _fix_case(monkeypatch, "9", 3)
    assert jebb[2]["n"] == "9"
    assert jebb[2]["fix_conflicts"] == [(3, "lemma")]
    assert _fix_case(monkeypatch, "3", 3)[2]["fix_conflicts"] == []


def test_the_normal_report_counts_lemma_disagreements_and_fix_conflicts(tmp_path, monkeypatch):
    rows = [*VERSE[:3], "**3 δεύτερον ἔπος ἐστὶν** Latin note"]
    text = ["---", "ΣΟΦΟΚΛΕΟΥΣ", "10", *rows, "---"]
    (tmp_path / "t.txt").write_text("\n".join(text) + "\n", encoding="utf-8")
    ref = [{"n": str(k), "text": t, "parts": []} for k, t in enumerate(VERSE[:3], 1)]
    monkeypatch.setattr(J, "GENIE", tmp_path)
    monkeypatch.setattr(J, "OUT", tmp_path / "out")
    monkeypatch.setattr(J, "ROOT", tmp_path)
    monkeypatch.setattr(J, "storr_lines", lambda w: ref)
    monkeypatch.setattr(J, "tlg_lines", lambda slug: ref)
    monkeypatch.setitem(J.PLAYS, "antigone", ("t.txt", "002", "x", 1, len(text)))
    monkeypatch.setitem(J.NUMBER_FIXES, "antigone", {5: ("9", "hand fix")})
    report = J.convert("antigone")            # no qa
    assert report["commentary_lemmas"]["disagree"] == 1
    assert [(c["src"], c["fix"], c["checkpoint"]) for c in report["fix_conflicts"]] == [(5, "9", 3)]
    assert [(s["src"], s["reason"]) for s in report["stops"]] == [(7, "apparatus marker")]


# John, 2026-09-29: Jebb's own numbers govern his edition.
def _count_case(monkeypatch, lemmas, printed=None):
    ref = [{"n": str(k), "text": t, "parts": []} for k, t in zip((156, 157, 158, 160), VERSE[:4])]
    refs = {"S": ref, "T": ref}
    covers = {"S": [[0], [1], [2], [3]], "T": [[0], [1], [2], [3]]}
    jebb = [{"text": t, "src": 10 + k, "page": 1, "printed": None, "colon": k + 1} for k, t in enumerate(VERSE[:4])]
    if printed:
        for i, p in printed.items():
            jebb[i]["printed"] = p
    monkeypatch.setattr(J, "lemma_checkpoints", lambda slug, jebb: lemmas)
    J.number_lines("t", jebb, refs, covers)
    return [x["n"] for x in jebb]


def test_a_lemma_that_opens_a_line_numbers_it_over_the_reference(monkeypatch):
    # OT 159 πρῶτά σε: the TLG says 158, Jebb's note says 159.
    assert _count_case(monkeypatch, {2: [(159, 0, 0)]}, {3: 160}) == ["156", "157", "159", "160"]


def test_without_jebb_numbers_the_reference_count_stands(monkeypatch):
    assert _count_case(monkeypatch, {}) == ["156", "157", "158", "160"]


def test_a_late_lemma_is_a_number_the_line_holds(monkeypatch):
    # OT 690 ἴσθι δὲ … '692 ἐπὶ φρόνιμα': the line is 690 and holds 692, so
    # the next colon is 693 by Jebb's count, not the reference's 691.
    ref = [{"n": str(k), "text": t, "parts": []} for k, t in zip((689, 690, 691, 695), VERSE[:4])]
    covers = {x: [[0], [1], [2], [3]] for x in "ST"}
    jebb = [{"text": t, "src": 10 + k, "page": 1, "printed": None, "colon": k + 1} for k, t in enumerate(VERSE[:4])]
    jebb[0]["printed"], jebb[3]["printed"] = 689, 695
    pos = len(J.key(VERSE[1])) - 3
    monkeypatch.setattr(J, "lemma_checkpoints", lambda slug, jebb: {1: [(692, pos, 0)]})
    J.number_lines("t", jebb, {"S": ref, "T": ref}, covers)
    assert [x["n"] for x in jebb] == ["689", "690", "693", "695"]


def test_row_cleaning_and_word_joins():
    assert J.clean_row("> &nbsp;7 νόμος ὅδ’\\") .strip().endswith("νόμος ὅδ’")
    assert J.clean_row("καίτοι 〈καὶ〉 γενεᾷ") == "καίτοι <καὶ> γενεᾷ"
    assert "…" in J.clean_row("ἀκταὶ Βοσπόριαι — ◡ —")
    base = {"kind": "verse", "colon": 5, "strophe": None, "speaker": None, "page": 1, "turn": False}
    rows = [{**base, "text": "τέγγει δ’ ὑπ’ ὀφρύσι παγ-", "printed": None, "src": 1},
            {**base, "colon": None, "text": "κλαύτοις", "printed": 830, "src": 2}]
    (joined,) = J.join_turnovers(rows, [J.key("τέγγει δ’ ὑπ’ ὀφρύσι παγκλαύτοις")])
    assert joined["text"] == "τέγγει δ’ ὑπ’ ὀφρύσι παγκλαύτοις"
