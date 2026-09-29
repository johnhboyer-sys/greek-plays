"""Greek edition line matching and secondary-only book output."""
import json

from drama_pipeline.concordance import match_lines, normalize
from drama_pipeline.stage7_emit import emit_books


def line(ref, text):
    return {"ref": ref, "text": text}


def test_exact_normalizes_marks_sigma_and_iota():
    assert normalize("[τῇ] ὁδῷ, λόγοςʼ") == normalize("ΤΗΙ ΟΔΩΙ ΛΟΓΟΣ")
    assert match_lines([line("e1", "[τῇ] ὁδῷ, λόγοςʼ")],
                       [line("r1", "ΤΗΙ ΟΔΩΙ ΛΟΓΟΣ")]) == {"e1": "r1"}


def test_fuzzy_nearby_match():
    edition = [line("e1", "ἀεὶ μέν ὦ παῖ Λαρτίου δέδορκά σε")]
    reference = [line("r1", "ἀεὶ μέν ὦ παῖ Λαρτίου δέδορκα σε")]
    assert match_lines(edition, reference) == {"e1": "r1"}


def test_matches_stay_monotonic():
    edition = [line("e1", "alpha beta gamma delta"),
               line("e2", "alpha beta gamma delta")]
    reference = [line("r1", "alpha beta gamma delta"),
                 line("r2", "alpha beta gamma delta")]
    assert match_lines(edition, reference) == {"e1": "r1", "e2": "r2"}


def test_below_threshold_stays_unmapped():
    edition = [line("e1", "alpha beta gamma delta")]
    reference = [line("r1", "zeta theta kappa mu nu")]
    assert match_lines(edition, reference) == {}


def test_secondary_only_book_has_empty_primary(tmp_path):
    spine = {"work": "test", "segments": [{
        "id": "1:1", "book": 1, "column": "1",
        "lines": [{"n": 1, "ref": "1", "text": "ἀεὶ μέν ὦ παῖ"}],
    }]}
    tokens = {"segments": [{"id": "1:1", "lines": [{"tokens": []}]}]}
    secondary = {"1:1": [{"chapter": "1", "text": "I see you, son.", "cont": False}]}
    emit_books(spine, tokens, {"chunks": []}, {}, tmp_path, ross=secondary)
    segment = json.loads((tmp_path / "book-01.json").read_text())["segments"][0]
    assert segment["english"] is None
    assert segment["ross"] == secondary["1:1"]
