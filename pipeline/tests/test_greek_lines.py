"""The committed line files' format (drama_pipeline.greek_lines).

The failing cases come first: what the reader and the writer must refuse, and
what the check for markup and beta code must catch. Then the claim the build
rests on: a line file gives stage 1 the same spine as the XML it was made
from, speakers, strophe marks, lacunae, transpositions, and all. The Greek in
these cases is made up or from the plays' opening lines.
"""

from __future__ import annotations

import string
from pathlib import Path

import pytest
from lxml import etree

from drama_pipeline import greek_lines as gl
from drama_pipeline import scheme as scheme_mod
from drama_pipeline import stage1_greek as s1
from drama_pipeline.config import Manifest

TEI = ('<TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader><fileDesc><sourceDesc><p>Test Play (0000: 000) '
       '"Fabulae", Ed. Nemo. Oxford, 1900.</p></sourceDesc></fileDesc></teiHeader><text><body>{}</body></text></TEI>')


def _tree(body: str):
    return etree.fromstring(TEI.format(body).encode("utf-8")).getroottree()


def _xml(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "t.xml"
    path.write_text(TEI.format(body), encoding="utf-8")
    return path


# ---- what rows_from_tree refuses -------------------------------------------

@pytest.mark.parametrize("body, message", [
    ("", "no lines"),                                              # an empty play
    ('<div><l n="1">α</l></div>', "a <div> in the body"),          # the old reader skipped it
    ('<l n="1">α</l><p>β</p>', "a <p> in the body"),
    ('<l n="1">α</l>λόγος', "outside a line"),
    ('λόγος<l n="1">α</l>', "outside a line"),
    ('<l n="1">α<l n="2">β</l></l>', "a line inside line"),
    ('<l n="1">α<note>β</note></l>', "holds a <note>"),
    ('<l n="1">α<gap/></l>', "holds a <gap>"),
    ('<l n="1"><label type="stage">ἔσωθεν</label> α</l>', "label of type 'stage'"),
    ('<l n="1"><label>Χο.</label> α</l>', "label of type None"),
    ('<l n="1"><hi><label type="speaker">Χο.</label></hi> α</l>', "label inside a <hi>"),
    ('<l>α</l>', "no number"),
    ('<l n="">α</l>', "no number"),
    ('<l n=" ">α</l>', "no number"),
    ('<l n="1">ἔα {β}</l>', "prints a brace"),
    ('<l n="1"><label type="speaker">Χο}.</label> α</l>', "prints a brace"),
])
def test_rows_from_tree_refuses_a_shape_it_cannot_carry(body, message):
    with pytest.raises(ValueError, match=message):
        gl.rows_from_tree(_tree(body))


def test_a_file_with_no_body_is_refused(tmp_path):
    path = tmp_path / "t.xml"
    path.write_text("<TEI><text/></TEI>", encoding="utf-8")
    with pytest.raises(ValueError, match="no TEI body"):
        gl.rows_from_xml(path)


# ---- what the writer and the reader refuse ---------------------------------

@pytest.mark.parametrize("row", [
    gl.Row("1", "α\tβ"),            # a tab would shift the fields
    gl.Row("1", "α\nβ"),            # a line break would make two lines
    gl.Row("1", "α\rβ"),
    gl.Row("1\t2", "α"),
    gl.Row("1", "α  β"),            # not flat: would not read back the same
    gl.Row("1", " α"),
    gl.Row("", "α"),
    gl.Row(" 1", "α"),
])
def test_format_refuses_what_would_not_read_back(row):
    with pytest.raises(ValueError):
        gl.format_tsv([row], "t", "an edition")


H = "# work: t\n# edition: e\n# columns: n\ttext\n"


@pytest.mark.parametrize("text, message", [
    ("# work: t\n# edition: e\n# columns: book\tn\tsigla\ttext\n1\t1\t\tα\n", "expected # work"),
    ("# work: t\n1\tα\n", "expected # work"),                                         # no columns line
    # a fourth heading line is a place to keep anything
    ("# work: t\n# edition: e\n# note: x\n# columns: n\ttext\n1\tα\n", "expected # work"),
    ("# edition: e\n# work: t\n# columns: n\ttext\n1\tα\n", "expected # work"),
    # ... and so is a "# " line among the lines of text: it is not skipped
    (H + "# mh=nin\n1\tα\n", "tab-separated fields"),
    (H + "1\tα\tβ\n", "tab-separated fields"),
    (H + "1\n", "tab-separated fields"),
    (H + "\tα\n", "empty line number"),
    (H + "1\tα\r\n", "tab-separated fields"),
    (H, "no lines of text"),     # examined nothing
    ("", "expected # work"),
])
def test_parse_refuses_a_file_of_the_wrong_shape(text, message):
    with pytest.raises(ValueError, match=message):
        gl.parse_tsv(text)


# ---- the check for markup, beta code, and bytes that are not text ----------

# A title, a line with a speaker, an antilabe, a strophe mark glued to a
# speaker, Coulon's Latin strophe marks with a stanza number, a starred
# lacuna, a split and a suffixed number, the crux, brackets, quotation marks,
# the ano teleia (U+0387), the Greek question mark (U+037E) and numeral sign
# (U+0374), a hyphen across lines, and a printed metrical scheme.
CLEAN = (H + "t\tΑΓΑΜΕΜΝΩΝ\n"
         "1\t{ΦΥΛΑΞ} Θεοὺς μὲν αἰτῶ τῶνδ' ἀπαλλαγὴν πόνων· τί;\n"
         "2\t{Α.} ἰδού. {Β.} παπαιάξ.\n"
         "3\t{[ἀντ. α. Αν.} †ὦ† [πόνοι] ⟨φεῦ⟩ «λόγος» \"ἔπος\" ‘μῦθος’ (ἔα) – — τρια-\n"
         "4\t{Str. 2.} {Ant. α\u0374.} {Epode.} {12.} κτῆρος ⏑ – ⏑ – ×\n"
         "post 6\t{⟨ΠΑΙΣ⟩ (ἔσωθεν)}\n"
         "post1226\t\n"
         "141a\tα\n208-209\tβ\n289/290\tγ\n")

NOT_GREEK = "characters that are not Greek"
LABEL = "a label that is not"
FIELDS = "a line number"
BRACES = "a brace outside a label"


@pytest.mark.parametrize("planted, what", [
    ('9\t<l n="2">λόγος</l>', "markup"),
    ("9\tλόγος</div>", "markup"),
    ('9\t<?xml version="1.0"?>', "markup"),
    ("9\tλόγος &amp; οὐσία", "markup"),
    ("9\tλόγος &#955; οὐσία", "markup"),
    ("9\t<καὶ/>", "markup"),                       # an element with a Greek name
    ("9\t<καὶ> λόγος", "markup"),                  # the file writes the editors' angle brackets ⟨ ⟩
    ('9\t{<label type="speaker">Χο.</label>} λόγος', "markup"),
    ('9\t{Χο.<hi rend="small">} λόγος', "markup"),
    # beta code: the TLG's own way of writing Greek, in Latin letters
    ("9\tmh=nin a)/eide qea/", NOT_GREEK),
    ("9\t*)axilh=os", NOT_GREEK),
    ("9\t(mh=nin), (a)/eide), (qea/).", NOT_GREEK),   # punctuation round each word
    ("9\tλόγος (A) οὐσία", NOT_GREEK),            # one Latin letter is enough
    ("9\tтекст не греческий", NOT_GREEK),          # another script
    ("9\tSing, goddess, the wrath", NOT_GREEK),
    ("9\tStr. λόγος", NOT_GREEK),                  # a strophe word outside a label is Latin like any other
    # Latin in another dress: none of these is a "letter" to str.isalpha
    ("9\tλόγος ⓗⓔⓛⓛⓞ", NOT_GREEK),                # circled
    ("9\tλόγος ｈｅｌｌｏ", NOT_GREEK),           # fullwidth
    ("9\tλόγοςͣ", NOT_GREEK),                 # a combining Latin a
    ("9\tλόγος 𝛼", NOT_GREEK),                     # a mathematical alpha is not a Greek letter
    ("9\tλόγος ᵞ", NOT_GREEK),                     # MODIFIER LETTER SMALL GREEK GAMMA: Greek in name only
    ("9\tλόγος 12", NOT_GREEK),                    # digits belong in the number field, or a label
    ("9\tλόγος | οὐσία", NOT_GREEK),
    ("9\tλόγος\rοὐσία", "a control character"),
    ("9\tλόγος\x00οὐσία", "a control character"),
    ("9\tλόγος οὐσία", "a control character"),
    # labels: Greek, or the five strophe words and a stanza number, whole
    ("9\t{mh=nin} λόγος", LABEL),
    ("9\t{Str} λόγος", LABEL),                     # the word without its full stop
    ("9\t{Strophe.} λόγος", LABEL),
    ("9\t{Str. qea/} λόγος", LABEL),
    ("9\t{Str.Ant.} λόγος", LABEL),                # run together
    ("9\t{13.} λόγος", LABEL),
    ("9\t{01.} λόγος", LABEL),
    ("9\t{1} λόγος", LABEL),
    ("9\t{} λόγος", LABEL),                        # an empty label
    ("9\t{ Χο.} λόγος", LABEL),                    # not flat
    ("9\t{Χο.  Αν.} λόγος", LABEL),
    ("9\t{Χο. A} λόγος", LABEL),
    ("9\t{Χο. ⓐ} λόγος", LABEL),
    # braces: only round a label, never nested or left open
    ("9\tλόγος {Χο.", BRACES),
    ("9\tλόγος Χο.}", BRACES),
    ("9\t{{Χο.}} λόγος", BRACES),
    ("9\t{Χο. {Αν.}} λόγος", BRACES),
    ("t\t{Χο.} ΤΙΤΛΟΣ", BRACES),                   # the title holds no label
    # text hidden in the number field, or in spare fields
    ("9\tm\th", FIELDS),
    ("mhnin\tλόγος", FIELDS),
    ("qea\tλόγος", FIELDS),
    ("a)/eide\tλόγος", FIELDS),
    ("09\tλόγος", FIELDS),                         # read as 9 by int(): two spellings, one line
    ("0\tλόγος", FIELDS),
    ("١\tλόγος", FIELDS),                     # an Arabic-Indic one
    ("9g\tλόγος", FIELDS),
    ("9ab\tλόγος", FIELDS),
    ("9-\tλόγος", FIELDS),
    ("post\tλόγος", FIELDS),
    ("post  9\tλόγος", FIELDS),
    ("12345\tλόγος", FIELDS),
    ("T\tλόγος", FIELDS),
    ("\tλόγος", FIELDS),
    ("# mh=nin a)/eide qea/", FIELDS),             # a "heading" below the heading
    ("λόγος", FIELDS),
    ("t\tΔΕΥΤΕΡΟΣ", "2 title lines"),
])
def test_forbidden_catches_each_planted_case(planted, what):
    assert gl.forbidden(CLEAN) == []                      # the plant alone fails it
    problems = gl.forbidden(CLEAN + planted + "\n")
    assert any(what in p for p in problems), problems


# Every ASCII letter and digit, and every sign beta code writes with, alone:
# a list of marks that let one of them in would pass beta code that uses it.
@pytest.mark.parametrize("ch", list(string.ascii_letters + string.digits + "=/\\|+*#$%@^_~`;:!?&{}<>"))
def test_forbidden_refuses_each_latin_letter_digit_and_beta_code_sign(ch):
    assert gl.forbidden(CLEAN) == []
    planted = gl.forbidden(CLEAN + f"9\tλόγος {ch} οὐσία\n")
    assert planted, ch


def test_forbidden_catches_one_bad_line_at_the_end_of_a_long_clean_file():
    # No share of the file is allowed to be something else: one line fails it.
    long = CLEAN + "".join(f"{n}\t{{Χο.}} λόγος τῆς οὐσίας ἕτερος\n" for n in range(1000, 6000))
    assert gl.forbidden(long) == []
    assert any(NOT_GREEK in p for p in gl.forbidden(long + "6000\t(mh=nin).\n"))


@pytest.mark.parametrize("text", [
    # anything above the three heading lines, in place of them, or between them
    '# <l n="1">mh=nin a)/eide qea/</l>\n' + CLEAN,
    CLEAN.replace("# edition: e\n", "# edition: e\n# mh=nin a)/eide qea/\n"),
    CLEAN.replace("# work: t\n", "# work: mh=nin a)/eide\n"),
    CLEAN.replace("# work: t\n", "# work: Agamemnon\n"),
    CLEAN.replace("# edition: e\n", "# note: mh=nin a)/eide qea/\n"),
    "# work: t\n# columns: n\ttext\n",
    H,                                    # the heading and no line
    "",
])
def test_forbidden_refuses_a_file_that_does_not_open_with_the_three_heading_lines(text):
    assert any("not a line file" in p for p in gl.forbidden(text))


# The lead's review of #17: the edition line named the export's own source
# statement, TLG numbers and all. It names the edition; a source
# description's words fail it.
@pytest.mark.parametrize("edition", [
    'Aeschylus Trag. (c. 6-5 B.C.), Agamemnon (0085: 005) "Aeschyli tragoediae, 2nd edn.", Ed. Murray, G. Oxford: Clarendon Press, 1955, Repr. 1960.',
    "Murray, Aeschyli tragoediae (0085: 005)",
    "Murray, Aeschyli tragoediae (0085:005)",
    "Aeschylus Trag., Agamemnon",
    "Aristophanes Comic., Nubes",
    "Murray (c. 6-5 B.C.)",
    "Murray, Ed. Murray, G.",
    "Murray (OCT, 1955), Repr. 1960",
    "Murray, from the TLG",
    "Murray, via Diogenes",
    "Thesaurus Linguae Graecae",
])
def test_forbidden_fails_an_edition_line_that_holds_a_source_description(edition):
    problems = gl.forbidden(CLEAN.replace("# edition: e", f"# edition: {edition}"))
    assert any("source description" in p for p in problems), problems


# Grok's review of #17: the edition line was free text, so beta code, markup
# in look-alike brackets, or a whole play could sit on it. It holds a short
# bibliographic line: Latin letters (accents allowed), digits, spaces, and a
# few marks, at most 120 characters.
@pytest.mark.parametrize("edition", [
    "Murray, Aeschyli tragoediae, 2nd ed. (OCT, 1955). mh=nin a)/eide qea/",
    "Murray (OCT, 1955) *)axilh=os",
    "Murray (OCT, 1955) \uff1cl n=\"1\"\uff1e",          # fullwidth angle brackets
    "Murray (OCT, 1955) λόγος",                         # Greek text in the heading
    "Murray, " + "x" * 120,                              # a long line is a place to keep anything
    "Murray (OCT, 1955) | / \\ = + * # @ ~",
])
def test_forbidden_fails_an_edition_line_that_is_not_a_short_bibliographic_line(edition):
    problems = gl.forbidden(CLEAN.replace("# edition: e", f"# edition: {edition}"))
    assert any("the edition line" in p for p in problems), problems


# Grok's review: "Greek by its Unicode name" let in Greek symbols that are not
# text (the obol sign, vocal notation). A character is Greek when it is a
# Greek letter, or one of the three marks the editions print.
@pytest.mark.parametrize("ch", ["\U0001017c", "\U0001d200", "\u03f6", "\u03d0", "\u0375", "\u1fbd"])
def test_greek_symbols_that_are_not_letters_or_the_editions_marks_fail(ch):
    assert gl.forbidden(CLEAN) == []
    assert any(NOT_GREEK in p for p in gl.forbidden(CLEAN + f"9\tλόγος{ch} οὐσία\n")), ch


def test_the_three_greek_marks_the_editions_print_pass():
    assert gl.forbidden(CLEAN + "9\tλόγος\u0387 τί\u037e α\u0374\n") == []


def test_every_manifest_edition_passes_the_edition_line_check():
    import glob, yaml
    from drama_pipeline.config import REPO_ROOT
    editions = {yaml.safe_load(open(p, encoding="utf-8"))["work"]["greek_edition"]
                for p in glob.glob(str(REPO_ROOT / "manifests" / "*.yaml")) if not p.endswith("authors.yaml")}
    assert len(editions) >= 15, editions
    for edition in editions:
        assert gl.forbidden(CLEAN.replace("# edition: e", f"# edition: {edition}")) == [], edition


def test_forbidden_checks_the_heading_lines_too():
    assert any("markup" in p for p in gl.forbidden(CLEAN.replace("# edition: e", "# edition: <TEI>e</TEI>")))
    for columns in ("mh=nin a)/eide", "mhnin\ttext", "book\tn\tsigla\ttext", "n\ttext\textra"):
        assert any("not a line file" in p for p in gl.forbidden(CLEAN.replace("n\ttext\n", columns + "\n", 1)))
    # Homer's review: a tab in a heading line passed.
    assert any("not a line file" in p for p in gl.forbidden(CLEAN.replace("# edition: e", "# edition: e\tmh=nin")))
    assert any("not a line file" in p for p in gl.forbidden(CLEAN.replace("# work: t", "# work: t\tx")))
    assert any("control" in p for p in gl.forbidden(CLEAN.replace("# edition: e", "# edition: e\x00")))


def test_forbidden_passes_the_clean_file():
    assert gl.forbidden(CLEAN) == []


def test_forbidden_fails_a_file_whose_lines_hold_no_letters():
    assert any("no letters" in p for p in gl.forbidden(H + "1\t' .\npost 2\t{Χο.}\n"))


# ---- a line file gives stage 1 what the XML gives it -----------------------

def _manifest(**citation) -> Manifest:
    data = {"work": {"id": "t", "tlg_author": "0000", "tlg_work": "000", "greek_edition": "e",
                     "expected_sourcedesc": 'Test Play (0000: 000) "Fabulae"'},
            "citation": {"scheme": "play-line", "title_labels": [], "lacunae": {"1": []},
                         "transpositions": {"1": []}, **citation}}
    return Manifest(data, Path("t.yaml"))


# A title in its <label type="head"> (and <hi>); a speaker in <hi rend="small">;
# an antilabe; a strophe mark mid-line, glued to the words either side (no
# space added when it is dropped); a strophe mark glued to a speaker; a
# metrical scheme; ASCII angle brackets; a hyphen across lines; a line printed
# before its neighbour (a transposition); a lacuna with its speaker; a ref
# printed twice; a <pb/>, a <space/>, an <lb/>, a comment and a spaced <hi>.
CASE = (
    '<l n="t"><label type="head"><hi rend="large">ΤΕΣΤ</hi></label> </l>'
    '<l n="1"><label type="speaker"><hi rend="small">ΑΛΦΑ</hi></label> <space quantity="6.75"/>πρῶτος   λόγος<pb/> ἐστίν. </l>'
    '<l n="2"><label type="speaker">Α.</label> ἰδού.<label type="speaker">Β.</label> παπαιάξ.<!-- x --></l>'
    '<l n="3">ἔα<label type="speaker">[στρ. α.</label>τί τρια-</l>'
    '<l n="4" rend="indent(6.75)">κτῆρος &lt;φεῦ&gt; <hi rend="letter-spacing">ὦ</hi><lb/> ⏑ – ⏑ –</l>'
    '<l n="6"><label type="speaker">[ἀντ. α. Αν.</label> ἕκτος</l>'
    '<l n="5">πέμπτος</l>'
    '<l n="post 6"><label type="speaker">Γ.</label> </l>'
    '<l n="7">ἕβδομος</l><l n="7">ἕβδομος αὖθις</l>'
)
ROWS = [
    gl.Row("t", "ΤΕΣΤ"),
    gl.Row("1", "{ΑΛΦΑ} πρῶτος λόγος ἐστίν."),
    gl.Row("2", "{Α.} ἰδού.{Β.} παπαιάξ."),
    gl.Row("3", "ἔα{[στρ. α.}τί τρια-"),
    gl.Row("4", "κτῆρος ⟨φεῦ⟩ ὦ ⏑ – ⏑ –"),
    gl.Row("6", "{[ἀντ. α. Αν.} ἕκτος"),
    gl.Row("5", "πέμπτος"),
    gl.Row("post 6", "{Γ.}"),
    gl.Row("7", "ἕβδομος"),
    gl.Row("7", "ἕβδομος αὖθις"),
]
CASE_CITATION = {
    "title_labels": [{"sha256_16": s1._flat_title_content_hash("ΤΕΣΤ"), "text": "ΤΕΣΤ"}],
    "lacunae": {"1": ["post 6"]},
    "transpositions": {"1": [{"start": "5", "end": "5", "before": "6"}]},
    "repeated_refs": {"1": [{"ref": "7", "count": 2, "note": "printed twice"}]},
}


def _flat_lines(spine):
    return [line for seg in spine["segments"] for line in seg["lines"]]


def test_the_line_file_reads_back_and_makes_the_same_spine(tmp_path):
    manifest = _manifest(**CASE_CITATION)
    xml = _xml(tmp_path, CASE)
    rows, _source = gl.rows_from_xml(xml)
    assert len(rows) == CASE.count("<l ")                # every line, none dropped
    assert rows == ROWS                                   # written out by hand, above
    text = gl.format_tsv(rows, "t", "e")
    assert gl.parse_tsv(text) == (rows, "e")
    assert gl.forbidden(text) == []
    (tmp_path / "corpus").mkdir()
    (tmp_path / "corpus" / "t.tsv").write_text(text, encoding="utf-8")
    import pytest as _pt
    with _pt.MonkeyPatch.context() as mp:
        mp.setattr(gl, "CORPUS_DIR", tmp_path / "corpus")
        from_file = s1.play_spine(manifest)
    from_xml = s1.parse_spine(xml, manifest)
    assert from_file == from_xml
    # ... and both are what a reader of the case would write by hand
    lines = {l["ref"]: l for l in _flat_lines(from_file)}
    assert [l["ref"] for l in _flat_lines(from_file)] == ["1", "2", "3", "4", "6", "5", "post 6", "7", "7"]
    assert lines["3"]["text"] == "ἔατί τριακτῆρος" and lines["3"]["label"] == "στρ. α."
    assert lines["4"]["text"] == "⟨φεῦ⟩ ὦ"               # the scheme stripped, the hyphen joined back
    assert lines["6"]["label"] == "ἀντ. α." and lines["post 6"]["role"] == "lacuna"
    speakers = [s["label"] for seg in from_file["segments"] for s in seg.get("speakers", [])]
    assert speakers == ["ΑΛΦΑ", "Α.", "Β.", "Αν.", "Γ."]


def test_a_label_moved_in_the_line_file_moves_in_the_spine(tmp_path):
    # The comparison above would pass a reader that ignored the labels on both
    # sides; this one would not.
    manifest = _manifest(**CASE_CITATION)
    rows = list(ROWS)
    rows[2] = gl.Row("2", "{Α.} ἰδού. παπαιάξ.")
    rows[6] = gl.Row("5", "{Β.} πέμπτος")
    spine = s1._parse_spine_play_rows(rows, manifest, scheme_mod.for_manifest(manifest))
    speakers = [s["label"] for seg in spine["segments"] for s in seg.get("speakers", [])]
    assert speakers == ["ΑΛΦΑ", "Α.", "Αν.", "Β.", "Γ."]


def test_the_edition_line_is_held_to_the_manifest(tmp_path, monkeypatch):
    # The file names the manifest's greek_edition; a file of another edition
    # does not build as this one.
    monkeypatch.setattr(gl, "CORPUS_DIR", tmp_path)
    manifest = _manifest(**CASE_CITATION)
    (tmp_path / "t.tsv").write_text(gl.format_tsv(ROWS, "t", "another edition"), encoding="utf-8")
    with pytest.raises(ValueError, match="names the edition 'another edition', and the manifest 'e'"):
        s1.play_spine(manifest)
    (tmp_path / "t.tsv").write_text(gl.format_tsv(ROWS, "t", "e"), encoding="utf-8")
    assert s1.play_spine(manifest)["edition"] == "e"


def test_the_export_path_still_checks_the_export_source_statement(tmp_path):
    manifest = _manifest(**CASE_CITATION)
    manifest.data["work"]["expected_sourcedesc"] = "Another Play (0000: 001)"
    with pytest.raises(ValueError, match="expected_sourcedesc"):
        s1.parse_spine(_xml(tmp_path, CASE), manifest)


def test_stage_1_reads_the_committed_file_and_names_extract_when_it_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(gl, "CORPUS_DIR", tmp_path)
    manifest = _manifest(**CASE_CITATION)
    with pytest.raises(FileNotFoundError, match="drama_pipeline.extract --work t"):
        s1.read_lines(manifest)
    (tmp_path / "t.tsv").write_text(gl.format_tsv(ROWS, "t", "e"), encoding="utf-8")
    assert s1.read_lines(manifest) == (ROWS, "e")
