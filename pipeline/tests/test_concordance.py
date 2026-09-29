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


def test_edition_splits_one_reference_line():
    # Agamemnon 49-51: the edition breaks where the reference does not.
    edition = [line("e1", "τρόπον αἰγυπιῶν, οἵτʼ ἐκπατίοις"),
               line("e2", "ἄλγεσι παίδων ὕπατοι λεχέων"),
               line("e3", "στροφοδινοῦνται"),
               line("e4", "πτερύγων ἐρετμοῖσιν ἐρεσσόμενοι,")]
    reference = [line("r1", "τρόπον αἰγυπιῶν,"),
                 line("r2", "οἵτ' ἐκπατίοις ἄλγεσι παίδων"),
                 line("r3", "ὕπατοι λεχέων στροφοδινοῦνται"),
                 line("r4", "πτερύγων ἐρετμοῖσιν ἐρεσσόμενοι,")]
    result = match_lines(edition, reference)
    assert result["e4"] == "r4"
    assert result["e1"] == "r1"
    assert result["e2"] == "r2"
    assert result["e3"] == "r3"


def test_edition_joins_two_reference_lines_and_keeps_range_ref():
    # Ag. 108-109: one reference line printed as two edition lines.
    edition = [line("e1", "ὅπως Ἀχαιῶν"),
               line("e2", "δίθρονον κράτος, Ἑλλάδος ἥβας"),
               line("e3", "ξύμφρονα ταγάν,")]
    reference = [line("108-109", "ὅπως Ἀχαιῶν δίθρονον κράτος, Ἑλλάδος ἥβας"),
                 line("110", "ξύμφρονα ταγάν,")]
    assert match_lines(edition, reference) == {"e2": "108-109", "e3": "110"}


def test_joined_lines_below_threshold_stay_unmapped():
    edition = [line("e1", "alpha beta gamma"), line("e2", "delta epsilon zeta")]
    reference = [line("r1", "kappa lambda mu"), line("r2", "nu xi omicron pi")]
    assert match_lines(edition, reference) == {}


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


def _padded_reference(start, *lines):
    def greek(n):  # distinct Greek-letter text; normalize drops other scripts
        return "".join(chr(0x3b1 + (n // 5 ** d) % 5 * 5 + d) for d in range(4)) * 3
    filler = [line(f"f{n}", greek(n)) for n in range(start)]
    return filler + [line(f"r{n}", text) for n, text in enumerate(lines)]


def test_joined_span_may_start_at_last_line_of_window():
    edition = [line("e1", "τρόπον αἰγυπιῶν οἵτ ἐκπατίοις")]
    reference = _padded_reference(50, "τρόπον αἰγυπιῶν,", "οἵτ' ἐκπατίοις")
    assert set(match_lines(edition, reference)) == {"e1"}


def test_joined_span_may_not_start_past_window():
    edition = [line("e1", "τρόπον αἰγυπιῶν οἵτ ἐκπατίοις")]
    reference = _padded_reference(51, "τρόπον αἰγυπιῶν,", "οἵτ' ἐκπατίοις")
    assert match_lines(edition, reference) == {}
