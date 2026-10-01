"""Way's Loeb OCR -> TEI converter (scripts/ocr/way_to_tei.py)."""
import copy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("way_to_tei", ROOT / "scripts" / "ocr" / "way_to_tei.py")
W = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(W)
J = W.J

VERSE = ["ἀρχὴ λόγου πολλὴ καλή", "δεύτερον ἔπος ἐστὶν τόδε", "τρίτον δὲ ῥῆμα μακρὸν",
         "τέταρτον ἔπος ἐστὶν νόμος", "πέμπτον ἔπος ἐστὶ κάλλιστον", "ἕκτον δὲ τέλος ἐστὶ βραχύ"]


@pytest.fixture
def play(tmp_path, monkeypatch):
    """A fake play 't' whose OCR file holds the given pages."""
    def make(*pages):
        text = []
        for page in pages:
            text += ["---", *page]
        text.append("---")
        (tmp_path / "t.txt").write_text("\n".join(text) + "\n", encoding="utf-8")
        monkeypatch.setattr(W, "GENIE", tmp_path)
        monkeypatch.setitem(W.PLAYS, "t", {"ocr": "t.txt", "ident": "x", "first": 1, "last": len(text),
                                           "head": "ΜΗΔΕΙΑ", "title": "Μήδεια", "murray": "murray-oct"})
    return make


def rows_of(*pages):
    counts = {}
    rows, log, stops = W.extract("t", counts)
    return rows, log, stops, counts


def test_greek_pages_by_running_head_drop_head_folio_and_footnotes(play):
    play(["ΜΗΔΕΙΑ", "ΤΡΟΦΟΣ", VERSE[0], "10 " + VERSE[1], "$^1$ Elmsley : for MSS. τι.", "284"],
         ["MEDEA", "NURSE", "Would God that Argo's hull", "285"],
         ["MHΔΕΙΑ", VERSE[2], "286"])   # a head in Latin lookalikes
    rows, log, stops, _ = rows_of()
    assert [(r["kind"], r.get("text")) for r in rows] == [
        ("name", "ΤΡΟΦΟΣ"), ("verse", VERSE[0]), ("verse", VERSE[1]), ("verse", VERSE[2])]
    assert rows[2]["printed"] == 10 and rows[1]["printed"] is None
    assert [r["page"] for r in rows] == [284, 284, 284, 286]
    # The OCR page index is the leaf; the fixture's opening '---' closes an
    # empty page 1.
    assert [r["leaf"] for r in rows] == [2, 2, 2, 4]
    (stop,) = stops
    assert stop["reason"] == "footnote" and stop["page"] == 284


def test_row_forms_numbers_names_marks_and_markup():
    c = {}
    assert W.parse_row("1400", c) == {"kind": "num", "number": 1400}
    assert W.parse_row("**ΧΟΡΟΣ**", c) == {"kind": "name", "text": "ΧΟΡΟΣ"}
    assert W.parse_row("ΠΑΙΣ αʹ", c)["text"] == "ΠΑΙΣ αʹ"
    assert W.parse_row("HMIXOPION", c)["text"] == "ΗΜΙΧΟΡΙΟΝ"
    assert W.parse_row("*ἀντ. α'*", c) == {"kind": "label", "strophe": ("antistrophe", 1)}
    r = W.parse_row("βέβακε δ᾽ ὅρκων χάρις, οὐδ᾽ ἔτ᾽ αἰδὼς *ἀντ. β᾽*", c)
    assert r["strophe"] == ("antistrophe", 2) and r["text"] == "βέβακε δ’ ὅρκων χάρις, οὐδ’ ἔτ’ αἰδὼς"
    r = W.parse_row("Μενέλα’, ἐπίσχες· μὴ τάχυν’ ἄνευ δίκης. 550", c)
    assert r["printed"] == 550
    r = W.parse_row("980 ξανθᾷ δ᾽ ἀμφὶ κόμᾳ θήσει τὸν ῞Αιδα", c)
    assert r["printed"] == 980 and r["text"].endswith("τὸν Ἅιδα")
    r = W.parse_row("στέγοι $^1$ δέ με σωφροσύνα, τάχ᾽¹ ἂν 'Αργεῖος", c)
    assert r["text"] == "στέγοι δέ με σωφροσύνα, τάχ’ ἂν Ἀργεῖος"
    assert c["capital_breathing"] == 2


def _verse(text, page=1, src=0, **kw):
    return {"kind": "verse", "text": text, "printed": None, "strophe": None, "colon": None,
            "speaker": None, "turn": False, "lacuna": None, "page": page, "src": src, **kw}


def test_an_own_row_strophe_mark_labels_the_row_above_unless_that_row_ends_a_sentence():
    lab = {"kind": "label", "strophe": ("strophe", 2), "page": 1, "src": 2}
    out = W.place_numbers_and_labels([_verse("ὦ πατρίς, ὦ δώματα, μὴ", src=1), lab, _verse("δῆτ’ ἄπολις γενοίμαν", src=3)])
    assert out[0]["strophe"] == ("strophe", 2) and out[1]["strophe"] is None
    out = W.place_numbers_and_labels([_verse("γυναῖκας ἕξει.", src=1), lab, _verse("μοῦσαι δὲ παλαιγενέων", src=3)])
    assert out[0]["strophe"] is None and out[1]["strophe"] == ("strophe", 2)


def test_an_own_row_number_goes_to_the_row_a_reference_numbers_so():
    num = {"kind": "num", "number": 1400, "page": 1, "src": 2}
    rows = W.place_numbers_and_labels([_verse("παίδων ὁ τάλας", src=1), num, _verse("νῦν σφε προσαυδᾷς", src=3)])
    lines = J.build_lines(rows)
    refs = {"S": [{"n": "1400", "text": "x"}, {"n": "1401", "text": "y"}], "T": []}
    W.resolve_apart(lines, refs, {"S": [[0], [1]], "T": [[], []]})
    assert lines[0]["printed"] == 1400 and lines[1]["printed"] is None
    assert lines[0]["printed_apart"]["placed"] == "above"
    rows = W.place_numbers_and_labels([_verse("ἀχὰν οἵαν", src=1), {**num, "number": 150}, _verse("μέλπει νύμφα", src=3)])
    lines = J.build_lines(rows)
    refs = {"S": [{"n": "149", "text": "x"}, {"n": "150", "text": "y"}], "T": []}
    W.resolve_apart(lines, refs, {"S": [[0], [1]], "T": [[], []]})
    assert lines[1]["printed"] == 150 and lines[0]["printed"] is None


def test_shares_on_rows_of_their_own_join_into_one_line():
    ref = [J.key("αἰαῖ μάλ’ αὖθις. μῶν τιν’ ἀγγέλλων τύχην")]
    rows = [{"kind": "name", "text": "ΜΗΔΕΙΑ"}, _verse("αἰαῖ μάλ’ αὖθις.", src=1),
            {"kind": "name", "text": "ΠΑΙΔΑΓΩΓΟΣ"}, _verse("μῶν τιν’ ἀγγέλλων τύχην", src=2),
            _verse("οὐκ οἶδα, δόξης δ’ ἐσφάλην εὐαγγέλου;", src=3, printed=1010)]
    lines = W.merge_antilabe(J.build_lines(rows), ref)
    assert len(lines) == 2
    assert lines[0]["shares"] == [("ΜΗΔΕΙΑ", "αἰαῖ μάλ’ αὖθις."), ("ΠΑΙΔΑΓΩΓΟΣ", "μῶν τιν’ ἀγγέλλων τύχην")]
    assert lines[0]["antilabe_rows"] == [2]


def test_only_a_long_row_takes_a_turn_over():
    long_row = "ἐννέπων, ἅπας δ’ ἐν ἔργῳ δοῦλος ἦν, μάτην"
    ref = [J.key(long_row + " πονῶν."), J.key("σὺ δ’, ὦ τάλαν, ὦ κακόνυμφε κηδεμὼν τυράννων")]
    out = W.join_turnovers([_verse(long_row, src=1), _verse("πονῶν.", src=2)], ref)
    assert len(out) == 1 and out[0]["text"] == long_row + " πονῶν." and out[0]["turnovers"][0]["src"] == 2
    lyric = [_verse("σὺ δ’, ὦ τάλαν, ὦ κακόνυμφε", src=1), _verse("κηδεμὼν τυράννων,", src=2)]
    assert len(W.join_turnovers(lyric, ref)) == 2   # Way's colon stays his own line


def test_a_cry_takes_murrays_number_and_the_verse_after_it_his_lettered_one():
    lines = [{"n": "95a", "n_how": "lettered", "text": "ἰώ,", "src": 1},
             {"n": "96", "n_how": "storr", "text": "δύστανος ἐγὼ μελέα τε πόνων,", "src": 2, "printed": None}]
    murray = [{"n": "96", "text": "ἰώ,"}, {"n": "96a", "text": "δύστανος ἐγὼ μελέα τε πόνων,"}]
    assert W.follow_murray_cries(lines, murray) == [(1, "95a", "96"), (2, "96", "96a")]
    assert [x["n"] for x in lines] == ["96", "96a"]


def test_tei_parts_and_a_stanza_closed_by_the_next_speaker(monkeypatch):
    monkeypatch.setitem(W.PLAYS, "t", {"ocr": "t.txt", "ident": "x", "title": "Μήδεια"})
    base = {"page": 2, "leaf": 14, "printed": None, "printed_more": [], "ref_parts": []}
    lines = [{**base, "n": "148", "strophe": ("strophe", None), "shares": [("ΧΟΡΟΣ", "ἄιες")], "printed": 148},
             {**base, "n": "149", "strophe": None, "shares": [(None, "ἀχὰν οἵαν")]},
             {**base, "n": "160", "strophe": None, "shares": [("ΜΗΔΕΙΑ", "ὦ μεγάλα"), ("ΧΟΡΟΣ", "τί φής")],
              "ref_parts": ["160b"]}]
    tei = W.write_tei("t", lines)
    assert '<pb n="2" facs="https://archive.org/details/x/page/n13"/>' in tei
    body = tei[tei.index("<body>"):]
    assert body.index("</div>") < body.index("<speaker>ΜΗΔΕΙΑ</speaker>")
    assert '<l n="148" rend="margin-148">ἄιες</l>' in body
    assert '<l n="160" part="I">ὦ μεγάλα</l>' in body and '<l n="160b" part="F">τί φής</l>' in body


def _tei_lines(*specs):
    """Line records for write_tei: (n, speaker or None, text, strophe or None, Murray stanza or None)."""
    base = {"page": 2, "leaf": 14, "printed": None, "printed_more": [], "ref_parts": []}
    return [{**base, "n": n, "shares": [(spk, text)], "strophe": strophe, "stanza": stanza}
            for n, spk, text, strophe, stanza in specs]


def _divs(tei):
    """[(subtype, [n, ...])] for each strophe div of the TEI."""
    import xml.etree.ElementTree as ET
    ns = "{http://www.tei-c.org/ns/1.0}"
    body = ET.fromstring(tei).find(f".//{ns}body")
    return [(d.get("subtype"), [l.get("n") for l in d.iter(f"{ns}l")]) for d in body.iter(f"{ns}div")]


def test_an_unlabelled_stanza_closes_before_the_spoken_speech_after_it(monkeypatch):
    # Medea 996-1002: the antistrophe carries no speaker (the chorus sings
    # on); the Paedagogus' 1002 is spoken, outside Murray's stanza.
    monkeypatch.setitem(W.PLAYS, "t", {"ocr": "t.txt", "ident": "x", "title": "Μήδεια"})
    lines = _tei_lines(("990", "ΧΟΡΟΣ", "σὺ δ’, ὦ τάλαν", ("strophe", 2), "s2"),
                       ("996", None, "μεταστένομαι δὲ σὸν ἄλγος", ("antistrophe", 2), "a2"),
                       ("1001", None, "ἄλλᾳ ξυνοικεῖ πόσις συνεύνῳ.", None, "a2"),
                       ("1002", "ΠΑΙΔΑΓΩΓΟΣ", "δέσποιν’, ἀφεῖνται παῖδες", None, None),
                       ("1003", None, "καὶ δῶρα νύμφη βασιλὶς", None, None))
    assert _divs(W.write_tei("t", lines)) == [("strophe", ["990"]), ("antistrophe", ["996", "1001"])]


def test_an_exchange_inside_one_stanza_stays_one_stanza(monkeypatch):
    # Medea 1273-1281 (Murray's second strophe): the sons' cries are sung
    # inside the strophe, so their speeches do not close it; Jason's
    # spoken 1293 does.
    monkeypatch.setitem(W.PLAYS, "t", {"ocr": "t.txt", "ident": "x", "title": "Μήδεια"})
    lines = _tei_lines(("1273", "ΧΟΡΟΣ", "ἀκούεις βοὰν", ("strophe", 2), "s2"),
                       ("1277", "ΠΑΙΣ αʹ", "ναί, πρὸς θεῶν", None, "s2"),
                       ("1278", "ΠΑΙΣ βʹ", "ὡς ἐγγὺς ἤδη", None, "s2"),
                       ("1279", "ΧΟΡΟΣ", "τάλαιν’, ὡς ἄρ’ ἦσθα", None, "s2"),
                       ("1293", "ΙΑΣΩΝ", "γυναῖκες αἳ τῆσδ’", None, None))
    assert _divs(W.write_tei("t", lines)) == [("strophe", ["1273", "1277", "1278", "1279"])]


JEBB_GLOBALS = ("PLAYS", "NUMBER_FIXES", "MARGIN_NOTES", "ROW_FIXES", "ROW_FIXES_ACTIVE", "PRINTED_FIXES")


def _jebb_state():
    return {name: copy.deepcopy(getattr(J, name)) for name in JEBB_GLOBALS}, J.lemma_checkpoints


@pytest.mark.parametrize("fail", [False, True])
def test_converting_leaves_jebbs_globals_exactly_as_they_were(monkeypatch, tmp_path, fail):
    # Way's conversion lends Jebb's module its tables for the call only: no
    # play entry is added to Jebb's PLAYS, and an entry Jebb's module already
    # holds for the slug is put back as it was; on an exception too.
    monkeypatch.setitem(J.NUMBER_FIXES, "t", {7: ("7", "Jebb's own")})
    monkeypatch.setitem(J.MARGIN_NOTES, "t", {7: "Jebb's own"})
    monkeypatch.setitem(W.NUMBER_FIXES, "t", {3: ("4", "a hand fix")})
    ref = [{"n": "1", "text": VERSE[0], "parts": []}]
    monkeypatch.setattr(W, "murray_lines", lambda slug: ref)
    monkeypatch.setattr(W, "murray_stanzas", lambda slug: {}, raising=False)
    monkeypatch.setattr(J, "tlg_lines", lambda slug: ref)
    monkeypatch.setattr(W, "extract", lambda slug, counts: ([{**_verse(VERSE[0], src=1), "leaf": 3}], [], []))
    monkeypatch.setitem(W.PLAYS, "t", {"ocr": "t.txt", "ident": "x", "title": "Μήδεια"})
    monkeypatch.setattr(W, "OUT", tmp_path)
    monkeypatch.setattr(W, "DUMP", tmp_path)
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
            W.convert("t")
    else:
        W.convert("t")
    assert seen["fixes"] == {3: ("4", "a hand fix")}   # lent for the call
    assert _jebb_state() == before


def test_a_greek_page_with_a_misread_head_is_reported_not_dropped(play):
    play(["ΜΗΔΕΙΑ", VERSE[0], VERSE[1], "284"],
         ["MEDEA", "Would God that Argo's hull", "285"],
         ["ΜΗΔΑΙΑ ΚΑΙ", "5 " + VERSE[2], VERSE[3], VERSE[4], "286"],   # the head misread past the match
         ["ΤΑ ΤΟΥ ΔΡΑΜΑΤΟΣ ΠΡΟΣΩΠΑ", "ΤΡΟΦΟΣ", "ΧΟΡΟΣ"])                # a cast list: no verse
    rows, log, stops, _ = rows_of()
    assert [r["text"] for r in rows] == [VERSE[0], VERSE[1]]
    (stop,) = stops
    assert stop["reason"].startswith("no running head") and stop["leaf"] == 4 and stop["verse_rows"] == 3
    assert log == ["3 pages without the Greek running head skipped: leaves 3, 4, 5"]


def test_two_own_row_numbers_before_one_verse_keep_both():
    n1 = {"kind": "num", "number": 100, "page": 1, "src": 2}
    n2 = {"kind": "num", "number": 105, "page": 1, "src": 3}
    rows = W.place_numbers_and_labels([_verse(VERSE[0], src=1), n1, n2, _verse(VERSE[1], src=4)])
    lines = J.build_lines(rows)
    refs = {"S": [{"n": "104", "text": "x"}, {"n": "105", "text": "y"}], "T": []}
    W.resolve_apart(lines, refs, {"S": [[0], [1]], "T": [[], []]})
    assert lines[1]["printed"] == 105
    # The earlier number cannot be placed by the rows: a checkpoint apart.
    assert lines[1]["detached"] == [100] and lines[1]["unplaced"] == [{"number": 100, "src": 2}]


def test_a_number_after_the_last_verse_row_is_kept():
    rows = W.place_numbers_and_labels([_verse(VERSE[0], src=1), _verse(VERSE[1], src=2),
                                       {"kind": "num", "number": 1419, "page": 1, "src": 3}])
    lines = J.build_lines(rows)
    W.resolve_apart(lines, {"S": [], "T": []}, {"S": [[], []], "T": [[], []]})
    assert lines[1]["detached"] == [1419]


def test_a_number_apart_is_written_and_checked_against_its_page(monkeypatch):
    monkeypatch.setitem(W.PLAYS, "t", {"ocr": "t.txt", "ident": "x", "title": "Μήδεια"})
    lines = _tei_lines(("104", None, VERSE[0], None, None), ("105", None, VERSE[1], None, None))
    lines[1]["printed"], lines[1]["detached"] = 105, [100]
    assert '<l n="105" rend="margin-105 margin-apart-100">' in W.write_tei("t", lines)
    for x in lines:
        x["src"], x["text"] = 0, x["shares"][0][1]
    bad = J.check_margins("t", lines)
    assert [b["printed"] for b in bad] == [100]   # 100 is no number of its page
