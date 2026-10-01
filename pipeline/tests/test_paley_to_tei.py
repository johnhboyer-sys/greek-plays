"""The Paley OCR -> TEI converter (scripts/ocr/paley_to_tei.py)."""
import copy
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "ocr"))
_spec = importlib.util.spec_from_file_location("paley_to_tei", ROOT / "scripts" / "ocr" / "paley_to_tei.py")
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)
J = P.J

V = ["ἀρχὴ λόγου πολλὴ καλή", "δεύτερον ἔπος ἐστὶν τόδε", "τρίτον δὲ ῥῆμα μακρὸν",
     "τέταρτον ἔπος ἐστὶν νόμος", "πέμπτον ἔπος ἐστὶ κάλλιστον", "ἕκτον δὲ τέλος ἐστὶ βραχύ"]


@pytest.fixture
def play(tmp_path, monkeypatch):
    """A fake play 't' whose pages hold the given rows (a list per page)."""
    def make(pages, printed_fixes=None, row_fixes=None):
        text = []
        for rows in pages:
            text += ["---", *rows]
        text.append("---")
        (tmp_path / "t.txt").write_text("\n".join(text) + "\n", encoding="utf-8")
        monkeypatch.setattr(P, "GENIE", tmp_path)
        monkeypatch.setitem(P.PLAYS, "t", ("t.txt", "003", "x", 12, 1, len(text), "ΜΗΔΕΙΑ", "Μήδεια"))
        monkeypatch.setitem(P.PRINTED_FIXES, "t", printed_fixes or {})
        monkeypatch.setitem(P.ROW_FIXES, "t", row_fixes or {})
        return text
    return make


@pytest.mark.parametrize("rows,number,used", [
    (["ΜΗΔΕΙΑ. 41", V[0]], 41, 1),
    (["42 ΕΥΡΙΠΙΔΟΥ", V[0]], 42, 1),
    (["40", "EYPIΠIΔOY", V[0]], 40, 2),
    (["ΜΗΔΕΙΑ . 59", V[0]], 59, 1),
    (["60 &emsp;&emsp;&emsp; ΕΥΡΙΠΙΔΟΥ", V[0]], 60, 1),
    (["74 | ΕΥΡΙΠΙΔΟΥ", "---|---", V[0]], 74, 2),
    (["78 ΕΥΡΙΠΙΔΟΥ ΜΗΔΕΙΑ.", V[0]], 78, 1),
    # p. 55: the page number, the head, then a margin number on its own row
    (["55", "ΜΗΔΕΙΑ.", "561", V[0]], 55, 2),
])
def test_running_heads_in_every_form_are_read_and_dropped(rows, number, used):
    ne = list(enumerate(rows, 1))
    assert P.read_head(ne, "ΜΗΔΕΙΑ", None) == (True, number, used)


def test_a_page_without_a_head_word_reads_none():
    assert P.read_head([(1, V[0]), (2, V[1])], "ΜΗΔΕΙΑ", 40)[0] is False


@pytest.mark.parametrize("row,printed", [
    (V[0] + "\t5", 5),                                         # a tab
    (V[0] + " 1335", 1335),                                    # a space
    (V[0] + ' <span style="float:right;">1340</span>  ', 1340),  # a span
    (V[0] + " [465]", 465),                                    # brackets
    ("| | " + V[0] + " | 865 |", 865),                         # a table's last column
])
def test_printed_numbers_in_their_trailing_forms(row, printed):
    r = P.parse_row(row)
    assert (r["kind"], r["text"], r["printed"]) == ("verse", V[0], printed)


def test_a_table_row_with_the_speaker_in_its_first_cell():
    r = P.parse_row("| ΙΑ. | " + V[0] + " | |")
    assert (r["speaker"], r["text"], r["printed"]) == ("ΙΑ.", V[0], None)


def test_latin_lookalike_labels_read_as_greek():
    assert P.parse_row("TP. " + V[0])["speaker"] == "ΤΡ."
    assert P.parse_row("MH. ἔα.")["speaker"] == "ΜΗ."
    assert P.parse_row("**ΧΟ.** " + V[0])["speaker"] == "ΧΟ."


@pytest.mark.parametrize("row,strophe", [
    (V[0] + " στρ. α΄.", ("strophe", 1)),
    (V[0] + " *στρ. α'.*  ", ("strophe", 1)),
    (V[0] + "           [στρ. β΄.", ("strophe", 2)),
    (V[0] + " | ἀντ.", ("antistrophe", None)),
    (V[0] + " ἀντ β΄.", ("antistrophe", 2)),
])
def test_strophe_marks_at_the_rows_end(row, strophe):
    r = P.parse_row(row)
    assert (r["text"], r["strophe"]) == (V[0], strophe)


def test_a_strophe_mark_and_a_number_in_either_order():
    assert P.parse_row(V[0] + " 410 στρ.")["printed"] == 410
    r = P.parse_row(V[0] + "           ἀντ. α΄. 985")
    assert (r["printed"], r["strophe"], r["text"]) == (985, ("antistrophe", 1), V[0])


def test_a_numbered_son_keeps_his_number_in_the_label():
    r = P.parse_row("ΠΑ. α΄. οἴμοι, τί δράσω; ποῖ φύγω μητρὸς χέρας;  ")
    assert r["speaker"] == "ΠΑ. αʹ."
    assert r["text"].startswith("οἴμοι")


def test_names_numbers_and_lacunae():
    assert P.parse_row("### ΑΙΓΕΥΣ.") == {"kind": "name", "text": "ΑΙΓΕΥΣ"}
    assert P.parse_row("**ΤΡΟΦΟΣ.**") == {"kind": "name", "text": "ΤΡΟΦΟΣ"}
    assert P.parse_row("30") == {"kind": "num", "numbers": [30]}
    assert P.parse_row("ΔΙ. * * *")["lacuna"] == "* * *"


def test_an_antilabe_share_stays_in_the_line_for_the_split():
    line = P.parse_row("ΙΑ. ὦ τέκνα φίλτατα. ΜΗ. μητρί γε, σοὶ δ’ οὔ.")
    shares = J.split_shares(line["text"], line["speaker"])
    assert shares == [("ΙΑ.", "ὦ τέκνα φίλτατα."), ("ΜΗ.", "μητρί γε, σοὶ δ’ οὔ.")]


def test_a_lone_digit_at_a_pages_foot_is_a_signature_mark(play):
    play([["ΜΗΔΕΙΑ. 43", V[0] + " 160", V[1], "5"], ["44 ΕΥΡΙΠΙΔΟΥ", V[2]]])
    rows, log, dropped = P.extract("t")
    assert [r.get("text") for r in rows] == [V[0], V[1], V[2]]
    assert dropped[0]["reason"] == "signature mark at the page's foot"


def test_the_first_pages_number_comes_from_the_next(play):
    play([["# ΕΥΡΙΠΙΔΟΥ ΜΗΔΕΙΑ.", V[0]], ["40", "EYPIΠIΔOY", V[1]]])
    rows, log, _ = P.extract("t")
    assert [r["page"] for r in rows] == [39, 40]


def test_a_run_of_numbers_after_a_block_goes_by_the_count(play):
    # Medea p. 40: the block's numbers came out as a run after it.
    play([["ΜΗΔΕΙΑ. 39", V[0] + " 25", V[1], V[2]],
          ["40", "ΕΥΡΙΠΙΔΟΥ", V[3], V[4], V[5], "28", "30"]])
    rows, _, _ = P.extract("t")
    lines, runs = P.build_lines(rows)
    assert runs == [{"at": 6, "numbers": [28, 30], "src": 12, "srcs": [12, 13], "page": 40, "fix": None}]
    covers = {"S": [[] for _ in lines], "T": [[] for _ in lines]}
    report = P.attach_runs(lines, runs, {"S": [], "T": []}, covers)
    assert [x.get("printed") for x in lines] == [25, None, None, 28, None, 30]
    assert [e["how"] for e in report] == ["count from the number before the block"] * 2


def test_a_single_number_goes_to_the_neighbour_the_count_reaches(play):
    # Medea p. 55: a number on its own row before its line.
    play([["ΜΗΔΕΙΑ. 55", V[0] + " 565", V[1], V[2], V[3], "569", V[4], V[5]]])
    rows, _, _ = P.extract("t")
    lines, runs = P.build_lines(rows)
    covers = {"S": [[] for _ in lines], "T": [[] for _ in lines]}
    P.attach_runs(lines, runs, {"S": [], "T": []}, covers)
    assert [x.get("printed") for x in lines] == [565, None, None, None, 569, None]


def test_a_number_no_rule_places_stays_apart(play):
    play([["ΜΗΔΕΙΑ. 55", V[0] + " 565", V[1], "535", V[2]]])
    rows, _, _ = P.extract("t")
    lines, runs = P.build_lines(rows)
    covers = {"S": [[] for _ in lines], "T": [[] for _ in lines]}
    report = P.attach_runs(lines, runs, {"S": [], "T": []}, covers)
    assert report[0]["how"] == "left apart"
    assert lines[1]["detached"] == [535]


def test_printed_fixes_move_a_number_to_the_row_the_scan_prints_it_on(play):
    text = play([["ΜΗΔΕΙΑ. 50", V[0] + " 390", V[1]]])
    first = text.index(V[0] + " 390") + 1
    play([["ΜΗΔΕΙΑ. 50", V[0] + " 390", V[1]]],
         printed_fixes={first: (None, "moved"), first + 1: (390, "scan prints it here")})
    rows, _, _ = P.extract("t")
    assert [(r["text"], r["printed"]) for r in rows] == [(V[0], None), (V[1], 390)]
    assert rows[1]["printed_fix"] == "scan prints it here"


def test_row_fixes_move_a_strophe_mark_up_a_row(play):
    text = play([["ΜΗΔΕΙΑ. 57", V[0], V[1] + " *ἀντ. α'.*"]])
    a, b = text.index(V[0]) + 1, text.index(V[1] + " *ἀντ. α'.*") + 1
    play([["ΜΗΔΕΙΑ. 57", V[0], V[1] + " *ἀντ. α'.*"]],
         row_fixes={a: (V[0], V[0] + " ἀντ. α΄.", "r"), b: (" *ἀντ. α'.*", "", "r")})
    rows, _, _ = P.extract("t")
    assert [r["strophe"] for r in rows] == [("antistrophe", 1), None]


def test_count_breaks_name_the_intervals_whose_rows_disagree():
    lines = [{"text": v, "printed": p, "page": 1, "src": i, "strophe": None}
             for i, (v, p) in enumerate(zip(V, [5, None, None, 7, None, None]))]
    (brk,) = P.count_breaks(lines)
    assert (brk["from"], brk["to"], brk["rows"]) == (5, 7, 3)


def test_numbering_lends_jebbs_tables_and_takes_them_back(monkeypatch):
    lines = [{"text": v, "printed": p, "page": 1, "src": i, "strophe": None, "colon": None,
              "speaker": None, "turn": False, "shares": [(None, v)]}
             for i, (v, p) in enumerate(zip(V, [None, 2, None, None, 5, None]))]
    refs = {"S": [{"n": str(k), "text": v, "parts": []} for k, v in enumerate(V, 1)],
            "T": [{"n": str(k), "text": v, "parts": []} for k, v in enumerate(V, 1)]}
    covers = {"S": [[k] for k in range(6)], "T": [[k] for k in range(6)]}
    saved = J.lemma_checkpoints
    monkeypatch.setitem(P.NUMBER_FIXES, "t", {3: ("4", "a hand fix")})
    bad = P.number("t", lines, refs, covers)
    assert bad == []
    assert [x["n"] for x in lines] == ["1", "2", "3", "4", "5", "6"]
    assert lines[3]["n_how"] == "fix: a hand fix"
    assert J.lemma_checkpoints is saved and "t" not in J.NUMBER_FIXES and "t" not in J.MARGIN_NOTES


def _row(text, src, printed=None, page=74, speaker=None, strophe=None):
    return {"kind": "verse", "text": text, "printed": printed, "colon": None, "strophe": strophe,
            "speaker": speaker, "turn": False, "src": src, "page": page}


MURRAY_1274 = [J.key(t) for t in ("ἰὼ τλᾶμον, ὦ κακοτυχὲς γύναι.", "παρέλθω δόμους; ἀρῆξαι φόνον",
                                   "δοκεῖ μοι τέκνοις.", "ναί, πρὸς θεῶν, ἀρήξατ’· ἐν δέοντι γάρ.")]


def test_a_turn_over_joins_the_line_it_ends_without_its_hyphen():
    # Medea p. 74: 'παρέλθω … δοκεῖ μοι τέ-' / 'κνοις. | 1275'. The break
    # falls inside Murray's colon δοκεῖ μοι τέκνοις, so it is the printer's.
    rows = [_row("ἰὼ τλᾶμον, ὦ κακοτυχὲς γύναι.", 1),
            _row("παρέλθω δόμους; ἀρῆξαι φόνον δοκεῖ μοι τέ-", 2),
            _row("κνοις.", 3, printed=1275),
            _row("ναί, πρὸς θεῶν, ἀρήξατ’· ἐν δέοντι γάρ.", 4, speaker="ΠΑ. αʹ.")]
    out = P.join_turnovers(rows, MURRAY_1274)
    assert [r["src"] for r in out] == [1, 2, 4]
    assert out[1]["text"] == "παρέλθω δόμους; ἀρῆξαι φόνον δοκεῖ μοι τέκνοις."
    # Paley prints a line's number at its end: the number is the joined line's.
    assert out[1]["printed"] == 1275 and not out[1].get("printed_from_turn")
    assert out[1]["turnovers"] == [{"text": "κνοις.", "src": 3, "printed": 1275}]


def test_a_short_row_paley_counts_or_murray_prints_alone_keeps_its_line():
    # p. 43: 'μὴ λίαν' ends Murray's 157, but Paley's 155 and 160 count it
    # as a line of his own.
    murray = [J.key(t) for t in ("Ζεύς σοι τάδε συνδικήσει· μὴ λίαν", "τάκου δυρομένα σὸν εὐνέταν.")]
    rows = [_row("καινὰ λέχη σεβίζει,", 1, printed=155, page=43), _row("κείνῳ τόδε μὴ χαράσσου·", 2, page=43),
            _row("Ζεύς σοι τάδε συνδικήσει.", 3, page=43), _row("μὴ λίαν", 4, page=43),
            _row("τάκου δυρομένα σὸν εὐνέταν.", 5, page=43),
            _row("ὦ μεγάλα Θέμι καὶ πότνι’ Ἄρτεμι,", 6, printed=160, page=43, speaker="ΜΗ.")]
    assert len(P.join_turnovers(rows, murray)) == 6
    # A row that is a Murray line by itself stays one.
    rows = [_row("ὄλεθρον βιοτᾷ προσάγεις ἀλόχῳ τε", 1, page=66), _row("σᾷ στυγερὸν θάνατον.", 2, page=66)]
    assert len(P.join_turnovers(rows, [J.key(r["text"]) for r in rows])) == 2


def test_a_joined_turn_over_is_marked_in_the_tei(monkeypatch):
    monkeypatch.setitem(P.PLAYS, "t", ("t.txt", "003", "x", 12, 1, 2, "ΜΗΔΕΙΑ", "Μήδεια"))
    monkeypatch.setitem(P.VOLUME, "x", ("I", "1878"))
    line = {"n": "1275", "page": 74, "printed": 1275, "turnovers": [{"text": "κνοις.", "src": 3, "printed": 1275}],
            "strophe": None, "shares": [("ΧΟ.", "παρέλθω δόμους; ἀρῆξαι φόνον δοκεῖ μοι τέκνοις.")]}
    tei = P.write_tei("t", [line])
    assert '<l n="1275" rend="margin-1275 turn">παρέλθω δόμους; ἀρῆξαι φόνον δοκεῖ μοι τέκνοις.</l>' in tei



def _divs(tei):
    """[(subtype, [n, ...])] for each strophe div of the TEI."""
    import xml.etree.ElementTree as ET
    ns = "{http://www.tei-c.org/ns/1.0}"
    body = ET.fromstring(tei).find(f".//{ns}body")
    return [(d.get("subtype"), [l.get("n") for l in d.iter(f"{ns}l")]) for d in body.iter(f"{ns}div")]


def test_the_parodos_antistrophe_closes_before_the_dialogue_after_it(monkeypatch):
    # Medea 173-214 (p. 44): Paley marks no stanza between the antistrophe
    # and the first strophe of the next ode (409), so a div left open to the
    # next mark held the Nurse's anapaests and the whole Creon scene. The
    # Nurse's 184 is outside Murray's antistrophe (173-183a): it closes there.
    monkeypatch.setitem(P.PLAYS, "t", ("t.txt", "003", "x", 12, 1, 2, "ΜΗΔΕΙΑ", "Μήδεια"))
    monkeypatch.setitem(P.VOLUME, "x", ("I", "1878"))
    base = {"page": 44, "printed": None}
    specs = [("173", "ΧΟ.", "πῶς ἂν ἐς ὄψιν τὰν ἁμετέραν", ("antistrophe", None), "antistrophe 1 #11"),
             ("183b", None, "πένθος γὰρ μεγάλως τόδ’ ὁρμᾶται.", None, None),
             ("184", "ΤΡ.", "δράσω τάδ’· ἀτὰρ φόβος εἰ πείσω", None, None),
             ("271", "ΚΡΕΩΝ", "σὲ τὴν σκυθρωπὸν καὶ πόσει θυμουμένην", None, None),
             ("272", "ΜΗ.", "Μήδει’, ἀνεῖπον τῆσδε γῆς ἔξω περᾶν", None, None)]
    lines = [{**base, "n": n, "shares": [(spk, text)], "strophe": strophe, "stanza": stanza}
             for n, spk, text, strophe, stanza in specs]
    assert _divs(P.write_tei("t", lines)) == [("antistrophe", ["173", "183b"])]


def test_murrays_stanzas_are_read_from_his_tei():
    st = P.stanza_scope.murray_stanzas(P.PERSEUS / "tlg0006.tlg003.perseus-grc2.xml")
    assert st["173"] == st["183a"] and st["173"].startswith("antistrophe")
    assert "184" not in st and "271" not in st      # the Nurse's anapaests, Creon's iambics
    assert st["1273"] == st["1277"] and st["1273"].startswith("strophe 2")


JEBB_GLOBALS = ("PLAYS", "NUMBER_FIXES", "MARGIN_NOTES", "ROW_FIXES", "ROW_FIXES_ACTIVE", "PRINTED_FIXES")


def _jebb_state():
    return {name: copy.deepcopy(getattr(J, name)) for name in JEBB_GLOBALS}, J.lemma_checkpoints


@pytest.mark.parametrize("fail", [False, True])
def test_converting_leaves_jebbs_globals_exactly_as_they_were(monkeypatch, tmp_path, fail):
    # An entry Jebb's module already holds for the slug is put back as it
    # was, not removed; on an exception too.
    monkeypatch.setitem(J.NUMBER_FIXES, "t", {7: ("7", "Jebb's own")})
    monkeypatch.setitem(J.MARGIN_NOTES, "t", {7: "Jebb's own"})
    monkeypatch.setitem(P.PLAYS, "t", ("t.txt", "003", "x", 12, 1, 2, "ΜΗΔΕΙΑ", "Μήδεια"))
    monkeypatch.setitem(P.VOLUME, "x", ("I", "1878"))
    monkeypatch.setitem(P.NUMBER_FIXES, "t", {3: ("4", "a hand fix")})
    monkeypatch.setattr(P, "perseus_lines", lambda path: [{"n": "1", "text": V[0], "parts": []}])
    monkeypatch.setattr(J, "tlg_lines", lambda slug: [{"n": "1", "text": V[0], "parts": []}])
    monkeypatch.setattr(P, "extract", lambda slug: ([_row(V[0], 1, page=1)], [], []))
    monkeypatch.setattr(P, "OUT", tmp_path)
    monkeypatch.setattr(P, "DUMP", tmp_path)
    seen = {}

    def number_lines(slug, lines, refs, covers):
        seen["fixes"] = J.NUMBER_FIXES[slug]
        if fail:
            raise RuntimeError("numbering failed")
        for x in lines:
            x["n"], x["n_how"], x["cand"] = "1", "storr", {"S": "1", "T": "1"}

    monkeypatch.setattr(J, "number_lines", number_lines)
    before = _jebb_state()
    if fail:
        with pytest.raises(RuntimeError):
            P.convert("t")
    else:
        P.convert("t")
    assert seen["fixes"] == {3: ("4", "a hand fix")}   # lent for the call
    assert _jebb_state() == before
