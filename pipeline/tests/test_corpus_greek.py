"""The guard on the committed Greek (corpus/greek/).

Two promises. The build needs nothing but these files for a play's TLG Greek,
so each play has one and stage 1 never runs Diogenes. And the files hold
lines of Greek and nothing of the TLG's own: no beta code, no Diogenes XML.
The check (greek_lines.forbidden) has its planted failing cases in
test_greek_lines.py; here it runs over the files themselves, and says how
many it read. Below that, the same promise for every other tracked file: no
Diogenes export hides in the repo outside the files allowed by name.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

from drama_pipeline import extract, greek_lines, stage1_greek
from drama_pipeline.config import REPO_ROOT, Manifest

MANIFESTS = sorted(p.stem for p in (REPO_ROOT / "manifests").glob("*.yaml")
                   if p.stem != "authors" and not p.stem.endswith("-public"))
WORKS = [w for w in MANIFESTS if not Manifest.for_work(w).data["work"].get("greek_source")]


def test_the_guard_has_something_to_guard():
    # A check that examined nothing has not passed. Every play's reference
    # Greek is the TLG's; the other Greek editions are vendored TEI.
    assert len(MANIFESTS) == 44, MANIFESTS
    assert WORKS == MANIFESTS


def test_the_folder_holds_one_file_per_play_and_nothing_else():
    have = sorted(p.name for p in greek_lines.CORPUS_DIR.iterdir())
    assert have == sorted(["README.md", *(f"{w}.tsv" for w in WORKS)])
    assert all(p.is_file() and not p.is_symlink() for p in greek_lines.CORPUS_DIR.iterdir())


def test_the_readme_is_short_and_holds_no_markup():
    # The one file here the character rule cannot cover: it is English prose.
    # This holds it to a page (no export fits in 4 KB) and to no XML; that its
    # words are what they should be is for whoever reviews a change to it.
    readme = (greek_lines.CORPUS_DIR / "README.md").read_text(encoding="utf-8")
    assert 500 < len(readme.encode("utf-8")) < 4096, "the README has grown; nothing but a short page belongs there"
    assert not re.search(r"<\?xml|<TEI|<div|<l[ >]|</|xmlns", readme)
    assert "TLG" not in readme and "Diogenes" not in readme


@pytest.mark.parametrize("work", WORKS)
def test_each_file_is_lines_of_greek_under_its_own_heading(work):
    manifest = Manifest.for_work(work)
    path = greek_lines.corpus_path(manifest)
    text = path.read_text(encoding="utf-8")
    assert greek_lines.forbidden(text) == []
    rows, edition = greek_lines.parse_tsv(text, path.name)
    assert len(rows) >= 700, f"{work}: only {len(rows)} lines"   # the Cyclops has 707
    assert text.split("\n")[0] == f"# work: {work}"
    # The edition the manifest names, not the export's own source statement
    # (the lead's review of #17; John's rule that public files name editions).
    assert edition == " ".join(manifest.data["work"]["greek_edition"].split())
    # The licence page names editions; these files do the same and never name
    # the disc the text was read from.
    assert "TLG" not in text and "Thesaurus Linguae" not in text and "Diogenes" not in text


def test_the_whole_corpus_was_read(capsys):
    files = lines = labels = titles = 0
    for w in WORKS:
        rows, _edition = greek_lines.load(greek_lines.corpus_path(Manifest.for_work(w)))
        files += 1
        lines += len(rows)
        labels += sum(1 for r in rows for kind, _v in greek_lines.split_labels(r.text) if kind == "label")
        titles += sum(1 for r in rows if r.n == "t")
    with capsys.disabled():
        print(f"\ncorpus/greek guard: read {files} files, {lines} lines, {labels} labels, {titles} title lines")
    assert (files, lines, labels, titles) == (44, 58999, 17188, 33), (files, lines, labels, titles)


def test_the_spines_are_the_ones_the_build_has_always_made():
    # The 44 spines stage 1 makes from the line files, pinned (each spine's
    # sha256, in play order, hashed again). They were proved byte for byte the
    # spines the old code made from the export (HANDOFF-PORTABILITY.md, phase
    # 1 record); a change to a file or to stage 1 that moves one fails here.
    total, outer = 0, hashlib.sha256()
    for w in WORKS:
        body = json.dumps(stage1_greek.play_spine(Manifest.for_work(w)), ensure_ascii=False, indent=1).encode("utf-8")
        total += len(body)
        outer.update(hashlib.sha256(body).digest())
    assert (total, outer.hexdigest()) == (
        10430390, "5d199ab6b7af7f9d04ab712503c14ed446503b6eaf357419f3812a1b7b2f0972"), "a play's spine moved"


def test_stage_1_stops_on_a_missing_line_file_and_does_not_run_diogenes(tmp_path, monkeypatch):
    monkeypatch.setattr(greek_lines, "CORPUS_DIR", tmp_path)
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("the build ran a program"))
    monkeypatch.setattr(stage1_greek, "BUILD_DIR", tmp_path / "build")
    with pytest.raises(FileNotFoundError, match="drama_pipeline.extract --work agamemnon"):
        stage1_greek.run(Manifest.for_work("agamemnon"))
    # and stage 1 has no way to: the export call lives in extract alone
    assert not hasattr(stage1_greek, "subprocess")
    assert not (tmp_path / "build").exists()


def test_the_export_folder_cannot_be_committed():
    # extract writes the Diogenes XML under build/export; git must ignore it.
    probe = extract.EXPORT_DIR / "tlg0085" / "Diogenes-Resources" / "xml" / "tlg" / "tlg0085005.xml"
    r = subprocess.run(["git", "check-ignore", "-q", "--no-index", str(probe)], cwd=REPO_ROOT)
    assert r.returncode == 0, "build/export is not git-ignored"
    tracked = subprocess.run(["git", "ls-files", "build", "*Diogenes-Resources*"], cwd=REPO_ROOT,
                             capture_output=True, text=True)
    assert tracked.returncode == 0, tracked.stderr
    assert tracked.stdout == "", tracked.stdout[:400]
    # and git did answer: the same question about a folder it does track
    assert subprocess.run(["git", "ls-files", "manifests"], cwd=REPO_ROOT, capture_output=True, text=True).stdout


# ---- extract ---------------------------------------------------------------

SOURCE = ('Aeschylus Trag. (c. 6-5 B.C.), Agamemnon (0085: 005) "Aeschyli tragoediae, 2nd edn.", '
          'Ed. Murray, G. Oxford: Clarendon Press, 1955, Repr. 1960.')


def _export(tmp_path, lines: int, text: str = "λόγος", source: str = SOURCE):
    xml = tmp_path / f"x{lines}.xml"
    xml.write_text(f'<TEI><teiHeader><sourceDesc><p>{source}</p></sourceDesc></teiHeader><text><body>'
                   + "".join(f'<l n="{n}">{text}</l>' for n in range(1, lines + 1)) + "</body></text></TEI>",
                   encoding="utf-8")
    return xml


def test_extract_skips_a_play_whose_greek_is_vendored(monkeypatch):
    monkeypatch.setattr(extract, "ensure_export", lambda m: pytest.fail("exported a vendored work"))
    m = Manifest.for_work("medea").for_edition("paley")
    assert extract.line_file(m) is None


def test_extract_refuses_to_write_a_file_the_guard_would_fail(tmp_path, monkeypatch):
    monkeypatch.setattr(greek_lines, "CORPUS_DIR", tmp_path / "out")
    monkeypatch.setattr(extract, "ensure_export", lambda m: _export(tmp_path, 1, "mh=nin a)/eide qea/"))
    with pytest.raises(ValueError, match="refusing"):
        extract.main(["--work", "agamemnon"])
    assert not (tmp_path / "out").exists()


def test_extract_writes_the_manifest_edition_and_not_the_source_statement(tmp_path, monkeypatch):
    out = tmp_path / "out"
    monkeypatch.setattr(greek_lines, "CORPUS_DIR", out)
    monkeypatch.setattr(extract, "ensure_export", lambda m: _export(tmp_path, 3))
    assert extract.main(["--work", "agamemnon"]) == 0
    head = (out / "agamemnon.tsv").read_text(encoding="utf-8").split("\n")[:2]
    assert head == ["# work: agamemnon", "# edition: Murray, Aeschyli tragoediae, 2nd ed. (OCT, 1955)"]
    assert "0085" not in (out / "agamemnon.tsv").read_text(encoding="utf-8")


def test_extract_refuses_an_export_of_another_edition(tmp_path, monkeypatch):
    monkeypatch.setattr(greek_lines, "CORPUS_DIR", tmp_path / "out")
    monkeypatch.setattr(extract, "ensure_export", lambda m: _export(tmp_path, 3, source="Euripides Trag., Medea"))
    with pytest.raises(ValueError, match="expected_sourcedesc"):
        extract.main(["--work", "agamemnon"])
    assert not (tmp_path / "out").exists()


def test_extract_will_not_replace_a_file_with_a_shorter_one_unless_told(tmp_path, monkeypatch):
    out = tmp_path / "out"
    monkeypatch.setattr(greek_lines, "CORPUS_DIR", out)
    monkeypatch.setattr(extract, "ensure_export", lambda m: _export(tmp_path, 3))
    assert extract.main(["--work", "agamemnon"]) == 0
    full = (out / "agamemnon.tsv").read_text(encoding="utf-8")
    # the export comes back cut short: well formed, and two lines gone
    monkeypatch.setattr(extract, "ensure_export", lambda m: _export(tmp_path, 1))
    assert extract.main(["--work", "agamemnon"]) == 1
    assert (out / "agamemnon.tsv").read_text(encoding="utf-8") == full
    assert extract.main(["--work", "agamemnon", "--allow-fewer-lines"]) == 0
    assert len((out / "agamemnon.tsv").read_text(encoding="utf-8").split("\n")) == 3 + 1 + 1


def test_extract_refuses_a_file_that_does_not_read_back(tmp_path, monkeypatch):
    # Break the file's reader alone (a label lost on the way back) and it must stop.
    monkeypatch.setattr(greek_lines, "CORPUS_DIR", tmp_path / "out")
    monkeypatch.setattr(extract, "ensure_export", lambda m: _export(tmp_path, 3, "<label type='speaker'>Χο.</label> λόγος"))
    real = greek_lines.parse_tsv

    def lossy(text, name=""):
        rows, edition = real(text, name)
        return [r._replace(text=r.text.replace("{Χο.} ", "")) if r.n == "2" else r for r in rows], edition
    monkeypatch.setattr(greek_lines, "parse_tsv", lossy)
    with pytest.raises(ValueError, match="does not read back"):
        extract.main(["--work", "agamemnon"])
    assert not (tmp_path / "out").exists()


def test_extract_runs_diogenes_with_home_and_the_tlg_folder(tmp_path, monkeypatch):
    # Diogenes 4.7.2 stops with exit 25 when HOME is missing (Homer's and
    # Aristotle's ports found it); the export goes to the author's own folder.
    seen = {}

    def fake_run(argv, cwd, env, capture_output, text):
        seen.update(argv=argv, cwd=cwd, env=env)
        return subprocess.CompletedProcess(argv, 0, "", "")
    monkeypatch.setattr(extract.subprocess, "run", fake_run)
    monkeypatch.setattr(extract, "EXPORT_DIR", tmp_path / "export")
    monkeypatch.setenv("HOME", "/home/x")
    monkeypatch.setenv("TLG_DIR", "/tlg")
    extract.run_export(Manifest.for_work("clouds"))
    assert seen["argv"] == ["perl", "xml-export.pl", "-c", "tlg", "-n", "0019", "-y", "-o", str(tmp_path / "export" / "tlg0019")]
    assert seen["env"] == {"TLG_DIR": "/tlg", "HOME": "/home/x", "PATH": "/usr/bin:/bin"}
    monkeypatch.delenv("HOME")
    with pytest.raises(RuntimeError, match="HOME"):
        extract.run_export(Manifest.for_work("clouds"))


# write_all is shared with Aristotle's, Plato's and Homer's extract; its tests
# stage made-up works W1 to W5 directly.
FAKE = [f"W{i}" for i in range(1, 6)]


def _made(tag: str):
    return [(Manifest({"work": {"id": w}}, Path(f"{w}.yaml")), f"# work: {w} {tag}\n", 1) for w in FAKE]


def _old_corpus(tmp_path, monkeypatch):
    out = tmp_path / "out"
    monkeypatch.setattr(greek_lines, "CORPUS_DIR", out)
    extract.write_all(_made("old"))
    return out, {p.name: p.read_text(encoding="utf-8") for p in out.iterdir()}


def _third_move_fails(monkeypatch):
    real, moves = Path.replace, []

    def replace(self, target):
        if self.suffix == ".tmp":                         # a move into place, not a put-back
            moves.append(self.name)
            if len(moves) == 3:
                raise PermissionError(1, "Operation not permitted", str(target))
        return real(self, target)
    monkeypatch.setattr(Path, "replace", replace)
    return moves


def test_a_write_that_fails_part_way_leaves_every_old_file_as_it_was(tmp_path, monkeypatch):
    out, before = _old_corpus(tmp_path, monkeypatch)
    (out / "W4.tsv.tmp").mkdir()                          # the disk refuses one of the later ones
    with pytest.raises(OSError):
        extract.write_all(_made("new"))
    (out / "W4.tsv.tmp").rmdir()
    assert {p.name: p.read_text(encoding="utf-8") for p in out.iterdir()} == before


def test_a_move_that_fails_part_way_puts_back_the_files_already_moved(tmp_path, monkeypatch):
    out, before = _old_corpus(tmp_path, monkeypatch)
    (out / "W1.tsv").unlink()                             # the first moved has no file yet
    before.pop("W1.tsv")
    moves = _third_move_fails(monkeypatch)
    with pytest.raises(PermissionError):
        extract.write_all(_made("new"))
    assert len(moves) == 3
    assert {p.name: p.read_text(encoding="utf-8") for p in out.iterdir()} == before


def test_a_write_that_fails_part_way_leaves_no_temporary_file(tmp_path, monkeypatch):
    out = tmp_path / "out"
    monkeypatch.setattr(greek_lines, "CORPUS_DIR", out)
    real, writes = Path.write_text, []

    def write_text(self, text, *a, **k):
        writes.append(self.name)
        if len(writes) == 2:
            real(self, text[:3], *a, **k)
            raise OSError(28, "No space left on device")
        return real(self, text, *a, **k)
    monkeypatch.setattr(Path, "write_text", write_text)
    with pytest.raises(OSError):
        extract.write_all(_made("new"))
    assert list(out.iterdir()) == []


def test_a_put_back_that_fails_names_its_file_and_the_others_are_still_put_back(tmp_path, monkeypatch, capsys):
    out, before = _old_corpus(tmp_path, monkeypatch)
    _third_move_fails(monkeypatch)
    real_write = Path.write_bytes

    def write_bytes(self, data):
        if self.name == "W1.tsv.back":
            real_write(self, data[:2])
            raise OSError(28, "No space left on device")
        return real_write(self, data)
    monkeypatch.setattr(Path, "write_bytes", write_bytes)
    with pytest.raises(PermissionError):
        extract.write_all(_made("new"))
    after = {p.name: p.read_text(encoding="utf-8") for p in out.iterdir()}
    assert "W1.tsv" in capsys.readouterr().err
    assert after["W1.tsv"] == "# work: W1 new\n"         # whole, not cut short
    assert {k: v for k, v in after.items() if k != "W1.tsv"} == {k: v for k, v in before.items() if k != "W1.tsv"}


def test_a_temp_that_cannot_be_removed_stops_no_put_back_and_hides_no_error(tmp_path, monkeypatch, capsys):
    out, before = _old_corpus(tmp_path, monkeypatch)
    _third_move_fails(monkeypatch)
    real_unlink = Path.unlink

    def unlink(self, missing_ok=False):
        if self.name == "W3.tsv.tmp":
            raise OSError(30, "Read-only file system", str(self))
        return real_unlink(self, missing_ok=missing_ok)
    monkeypatch.setattr(Path, "unlink", unlink)
    with pytest.raises(PermissionError) as caught:
        extract.write_all(_made("new"))
    assert caught.value.errno == 1
    assert "W3.tsv.tmp" in capsys.readouterr().err
    assert {p.name: p.read_text(encoding="utf-8") for p in out.iterdir() if p.suffix == ".tsv"} == before
    assert sorted(p.name for p in out.iterdir() if p.suffix != ".tsv") == ["W3.tsv.tmp"]


def test_a_back_file_that_cannot_be_removed_stops_no_later_put_back(tmp_path, monkeypatch, capsys):
    out, before = _old_corpus(tmp_path, monkeypatch)
    (out / "W1.tsv.back").mkdir()
    _third_move_fails(monkeypatch)
    with pytest.raises(PermissionError) as caught:
        extract.write_all(_made("new"))
    assert caught.value.errno == 1 and not str(caught.value.filename).endswith(".back")
    assert "W1.tsv" in capsys.readouterr().err
    assert (out / "W2.tsv").read_text(encoding="utf-8") == before["W2.tsv"]


# ---- export-shaped text outside corpus/greek/ (decision 10) ---------------
# A Diogenes export is known by its line elements (<l n="1">…</l>), the marks
# its lines carry (<space quantity=…>, rend="indent(…)", <label
# type="speaker">), the sentence its header opens with (EXPORT_HEADER), or
# its file name (tlg0085005.xml). Two kinds of file may hold more than a few
# such lines: the four test fixtures pinned below by name, size and hash,
# each with its reason; and the vendored Perseus and OCR'd TEI the build reads
# for the other Greek editions and the English, each listed by its hash in
# its own folder's SHA256SUMS and holding none of the export's marks. Any
# other tracked file may hold a handful (the tests' made-up Greek, a doc's
# example) and no header or export name.

# A line or line-break element with a number, in either quote and either
# case, with or without a namespace prefix or a space after "<": <l n="1">,
# <l rend="x" n='1a'>, <lb n="1"/>, <tei:l n="1">, <L N="1">, < l n="1">.
EXPORT_LINE = re.compile(r"""<\s*(?:[^\s<>/:="']+:)?lb?\b[^<>]*?\bn\s*=\s*["'][^"'<>]*["']""", re.IGNORECASE)
# What Diogenes writes inside a play's lines and the vendored TEI never does.
EXPORT_MARK = re.compile(r"""\bquantity\s*=\s*["']|\brend\s*=\s*["']indent\(|<\s*(?:[^\s<>/:="']+:)?label\b[^<>]*\btype\s*=\s*["']speaker""",
                         re.IGNORECASE)
# Written with \s+ so that this file does not match itself.
EXPORT_HEADER = re.compile(r"generated\s+by\s+Diogenes|from\s+the\s+TLG\s+corpus", re.IGNORECASE)
EXPORT_NAME = re.compile(r"(^|/)tlg\d{7}\.xml$", re.I)
FEW = 30   # well under any play (the shortest, the Cyclops, runs to 707 lines)
# In all tracked files but the allowed ones together, so an export split small
# fails too: 97 today (the tests' made-up Greek and doc examples); 150 leaves
# room for a new test, and is a seventh of the shortest play.
ALL = 150
VENDORED = ("sources/perseus/", "sources/ocr/")
# Test files that build TEI by hand, in Perseus's shape (speakers in <sp>, no
# Diogenes marks), each with the most lines it may hold. By name and not by
# hash, since a test changes as the code does; the marks rule still holds them.
TEST_TEI = {
    "pipeline/tests/test_stage1_perseus_play_english.py": 300,   # 254 today, made-up English
    "pipeline/tests/test_stage1_tei_greek.py": 80,               # 52 today, made-up Greek
    "pipeline/tests/test_stage1_lined_source.py": 60,            # 48 today, CPR's lined-source cases
}
PINNED = {
    # Decision 10, ruled for the plays by John on 2026-11-23 ("Keep them"),
    # as for Plato (2026-11-21) and Homer ("keep em"): test fixtures in the
    # export's markup, kept and pinned.
    "pipeline/tests/fixtures/stephanus/euthyphro_p2_3.xml": {
        "bytes": 9369, "sha256": "38226581bfbb162fc7b8e67e375d954ba708cfb58fc240bd103543c3001420eb", "lines": 77,
        "why": "Plato's fixture, copied here; ruled A (kept, pinned) for plato-reader on 2026-11-21"},
    "pipeline/tests/fixtures/stephanus/edge_cases.xml": {
        "bytes": 744, "sha256": "d386f9efa89f67b573385274c71073772094d48c5f822701e4d6df42ee0518c9", "lines": 6,
        "why": "made-up Stephanus edge cases in the export's markup"},
    "pipeline/tests/fixtures/play_line/synthetic6.xml": {
        "bytes": 973, "sha256": "d23c7768b25e8c550535dabad64414b9c0de485a6e070b30a6df093ebfc17cf1", "lines": 6,
        "why": "made-up play lines (ΤΕΣΤ, πρῶτος λόγος) in the export's markup"},
    "pipeline/tests/fixtures/play_line/synthetic_transposition.xml": {
        "bytes": 563, "sha256": "03385f28fa5357f0f49c1268fda2768ba7358030567e0c4713fb712ae0174af3", "lines": 6,
        "why": "made-up play lines in printed order, for the transposition walk"},
}


def _texts(body: bytes) -> list[str]:
    """The file read as UTF-8, and, when it holds a NUL, as UTF-16 both ways
    too: a UTF-16 copy reads as letters with NULs between them in UTF-8."""
    texts = [body.decode("utf-8", errors="ignore")]
    if b"\0" in body:
        texts += [body.decode(enc, errors="ignore") for enc in ("utf-16-le", "utf-16-be")]
    return texts


# Grok's review of #17: a stripped export could pass in a vendored folder if
# that folder's SHA256SUMS were rewritten with it. The four lists are pinned
# here, so a change to any vendored TEI is a change to this file too.
SUM_LISTS = {
    "sources/perseus/SHA256SUMS": "6ba4bd39d6029cb942dc5858ea6f421bb2309f5f4f744489c50371549302de0b",
    "sources/ocr/jebb/SHA256SUMS": "c812440308d61df8fcec846c9d32051bff6ecb098b5a2574dffb5483a14f46a6",
    "sources/ocr/paley/SHA256SUMS": "5e56c57333e83d83e153ba44fefc9ef4db07c4e8b6141886f0275b0d155233a4",
    "sources/ocr/way-loeb/SHA256SUMS": "fbbafa12e4b9363b8fb8bd8a3214c50409812ccd1d2023abafa0081125de3b61",
}


def _listed(files: dict[str, bytes], path: str, body: bytes) -> bool:
    """Is the file listed, by its hash, in its own folder's tracked SHA256SUMS?"""
    folder = path.rsplit("/", 1)[0]
    sums = files.get(f"{folder}/SHA256SUMS")
    if sums is None:
        return False
    want = f"{hashlib.sha256(body).hexdigest()}  {path.rsplit('/', 1)[1]}"
    return want in sums.decode("utf-8", errors="ignore").splitlines()


def export_problems(files: dict[str, bytes]) -> list[str]:
    """What a text scan can find. Out of its reach, by its method: a
    compressed, encrypted, or otherwise encoded copy, a submodule's files,
    and files git does not track. Beta code outside corpus/greek/ is not
    looked for: the pipeline keeps beta-code lookup keys of its own."""
    problems = []
    total = 0
    for path, body in sorted(files.items()):
        texts = _texts(body)
        lines = max(len(EXPORT_LINE.findall(t)) for t in texts)
        marks = max(len(EXPORT_MARK.findall(t)) for t in texts)
        if EXPORT_NAME.search(path):
            problems.append(f"{path}: named like a Diogenes export")
        if any(EXPORT_HEADER.search(t) for t in texts):
            problems.append(f"{path}: holds a Diogenes export's header words")
        pin = PINNED.get(path)
        if pin:
            got = {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), "lines": lines}
            if got != {k: pin[k] for k in got}:
                problems.append(f"{path}: the pinned file changed: {got}, pinned {pin}")
            continue
        vendored = path.startswith(VENDORED) and path.endswith(".xml")
        if vendored and lines > FEW:
            if not _listed(files, path, body):
                problems.append(f"{path}: {lines} export lines, and not listed by its hash in its folder's SHA256SUMS")
            if marks > FEW:
                problems.append(f"{path}: {marks} of the export's own marks; vendored TEI has none")
            continue
        if path in TEST_TEI:
            if lines > TEST_TEI[path]:
                problems.append(f"{path}: {lines} export lines, more than the {TEST_TEI[path]} it may hold")
            if marks > FEW:
                problems.append(f"{path}: {marks} of the export's own marks, more than {FEW}")
            continue
        total += lines
        if lines > FEW:
            problems.append(f"{path}: {lines} export lines, more than {FEW}; only a pinned or vendored file may hold more")
        if marks > FEW:
            problems.append(f"{path}: {marks} of the export's own marks, more than {FEW}")
    if total > ALL:
        problems.append(f"{total} export lines in all tracked files but the allowed ones, more than {ALL}")
    for path in PINNED:
        if path not in files:
            problems.append(f"{path}: the pinned file is gone; take it off the list")
    for path, sha in SUM_LISTS.items():
        got = hashlib.sha256(files[path]).hexdigest() if path in files else None
        if got != sha:
            problems.append(f"{path}: the pinned list of vendored TEI changed ({got}); review the change, then pin it here")
    for path in files:
        if path.startswith(VENDORED) and path.endswith("/SHA256SUMS") and path not in SUM_LISTS:
            problems.append(f"{path}: a list of vendored TEI that is not pinned here")
    return problems


def _tracked(root: Path = REPO_ROOT) -> dict[str, bytes]:
    """Every path in git's index with the bytes git stores for it, read from
    git and not the working tree: a symlink's blob is its target string, and
    a file deleted from the working tree, or left out of a sparse checkout,
    keeps its blob. Submodules (mode 160000) have no blob here."""
    index = subprocess.run(["git", "ls-files", "-s", "-z"], cwd=root, capture_output=True, check=True).stdout
    entries = []
    for raw in filter(None, index.split(b"\0")):
        meta, name = raw.split(b"\t", 1)
        mode, sha, _stage = meta.split(b" ")
        if mode != b"160000":
            entries.append((name.decode("utf-8"), sha))
    batch = subprocess.run(["git", "cat-file", "--batch"], cwd=root, input=b"".join(sha + b"\n" for _n, sha in entries),
                           capture_output=True, check=True).stdout
    out, at = {}, 0
    for name, sha in entries:
        end = batch.index(b"\n", at)
        got_sha, kind, size = batch[at:end].split(b" ")
        assert got_sha == sha and kind == b"blob", (name, batch[at:end])
        out[name] = batch[end + 1:end + 1 + int(size)]
        at = end + 1 + int(size) + 1
    return out


def _pinned() -> dict[str, bytes]:
    return {p: (REPO_ROOT / p).read_bytes() for p in [*PINNED, *SUM_LISTS]}


_EXPORT = ('<?xml version="1.0"?>\n<TEI><text><body>\n'
           + "".join(f'<l n="{n}"><label type="speaker" rend="indent(1)">Χο.</label> <space quantity="6.75"/>λόγος</l>\n'
                     for n in range(1, 41)) + "</body></text></TEI>\n")
_PLAIN = "".join(f'<l n="{n}">λόγος</l>\n' for n in range(1, 41))
FIX = "pipeline/tests/fixtures/stephanus/euthyphro_p2_3.xml"
SYN = "pipeline/tests/fixtures/play_line/synthetic6.xml"
PERSEUS = "sources/perseus/tlg0085.tlg005.perseus-grc2.xml"
OCR = "sources/ocr/paley/medea.xml"


def _with_sums(path: str, body: bytes, listed: bool = True) -> dict[str, bytes]:
    folder, name = path.rsplit("/", 1)
    line = f"{hashlib.sha256(body if listed else b'other').hexdigest()}  {name}\n"
    return {path: body, f"{folder}/SHA256SUMS": line.encode()}


@pytest.mark.parametrize("files, wanted", [
    ({"sources/x.xml": _PLAIN.encode()}, "40 export lines, more than 30"),
    ({"docs/notes.md": ("This XML text was generated " + "by Diogenes (version 4.7.2)").encode()}, "header words"),
    ({"docs/notes.md": ("from the TLG " + "corpus of classical texts").encode()}, "header words"),
    ({"docs/notes.md": ("GENERATED " + "BY DIOGENES").encode()}, "header words"),
    ({"sources/tlg0085005.xml": b"<TEI/>"}, "named like a Diogenes export"),
    ({"x/TLG0019003.XML": b""}, "named like a Diogenes export"),
    ({FIX: _EXPORT.encode()}, "the pinned file changed"),
    ({SYN: _EXPORT.encode()}, "the pinned file changed"),
    ({"drop": FIX}, "the pinned file is gone"),
    ({"same size": SYN}, "the pinned file changed"),
    # an export under the vendored folders: unlisted, or listed and marked
    ({PERSEUS: _PLAIN.encode()}, "not listed by its hash"),
    (_with_sums(PERSEUS, _PLAIN.encode(), listed=False), "not listed by its hash"),
    (_with_sums(PERSEUS, _EXPORT.encode()), "of the export's own marks; vendored TEI has none"),
    (_with_sums(OCR, _EXPORT.encode()), "of the export's own marks; vendored TEI has none"),
    # listed in another folder's list
    ({PERSEUS: _PLAIN.encode(), "sources/ocr/paley/SHA256SUMS":
      f"{hashlib.sha256(_PLAIN.encode()).hexdigest()}  tlg0085.tlg005.perseus-grc2.xml\n".encode()}, "not listed by its hash"),
    # a vendored-looking name outside the two folders gets no pass
    (_with_sums("sources/gutenberg/x.xml", _PLAIN.encode()), "40 export lines, more than 30"),
    ({"sources/x.md": "".join(f'<space quantity="{n}"/>' for n in range(40)).encode()}, "of the export's own marks"),
    # a vendored list rewritten to pass a new file, a list dropped, a new list
    ({"sources/perseus/SHA256SUMS": b"0" * 64 + b"  tlg0085.tlg005.perseus-grc2.xml\n"}, "the pinned list of vendored TEI changed"),
    ({"drop": "sources/ocr/paley/SHA256SUMS"}, "the pinned list of vendored TEI changed (None)"),
    ({"sources/ocr/new/SHA256SUMS": b""}, "a list of vendored TEI that is not pinned here"),
    ({"pipeline/tests/test_stage1_tei_greek.py": "".join(f'<l n="{n}">λόγος</l>' for n in range(1, 82)).encode()},
     "more than the 80 it may hold"),
    ({"pipeline/tests/test_stage1_tei_greek.py": _EXPORT.encode()}, "of the export's own marks, more than 30"),
    ({"sources/x.xml": "".join(f"<l n='{n}'>λόγος</l>" for n in range(1, 41)).encode()}, "40 export lines"),
    ({"sources/x.xml": "".join(f'<l rend="x" n="{n}a">λόγος</l>' for n in range(1, 41)).encode()}, "40 export lines"),
    ({"sources/x.xml": "".join(f'<lb n="{n}"/>λόγος' for n in range(1, 41)).encode()}, "40 export lines"),
    ({"sources/x.xml": _PLAIN.encode("utf-16-le")}, "40 export lines"),
    ({"sources/x.xml": ("This XML text was generated " + "by Diogenes").encode("utf-16")}, "header words"),
    ({f"sources/part{i}.xml": "".join(f'<l n="{n}">λόγος</l>' for n in range(1, 21)).encode() for i in range(8)},
     "export lines in all"),
    # Homer's reviews: upper case, a space after "<", a prefix with a
    # character outside \w, a namespace prefix.
    ({"sources/x.xml": "".join(f'<L N="{n}">α</L>' for n in range(1, 41)).encode()}, "40 export lines"),
    ({"sources/x.xml": "".join(f'< l n="{n}">α</l>' for n in range(1, 41)).encode()}, "40 export lines"),
    ({"sources/x.xml": "".join(f'<a·b:l n="{n}">α</a·b:l>' for n in range(1, 41)).encode()}, "40 export lines"),
    ({"sources/x.xml": ('<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">'
                        + "".join(f'<tei:l n="{n}">λόγος</tei:l>' for n in range(1, 41)) + "</tei:TEI>").encode()},
     "40 export lines"),
    ({"sources/x.md": "".join(f'<TEI:LABEL TYPE="speaker">Χο.</TEI:LABEL>' for n in range(40)).encode()},
     "of the export's own marks"),
])
def test_export_shaped_text_outside_the_allowed_files_fails(files, wanted):
    base = _pinned()
    assert export_problems(base) == []                    # the plant alone fails it
    if "drop" in files:
        base.pop(files.pop("drop"))
    if "same size" in files:
        # One letter for another of the same length: size and lines kept, the hash not.
        path = files.pop("same size")
        body = base[path]
        files[path] = body.replace("λόγος".encode(), "λόγοι".encode(), 1)
        assert len(files[path]) == len(body) and files[path] != body
    assert any(wanted in p for p in export_problems({**base, **files})), export_problems({**base, **files})


def test_the_scan_reads_what_git_stores_not_the_working_tree(tmp_path):
    # Homer's reviews: git keeps a symlink's target string as its blob, and a
    # tracked file whose working copy is gone keeps its blob too; a scan of
    # the working tree skipped both. This one reads every blob from git's index.
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)
    git("init", "-q")
    target = "".join(f'<l n="{n}">α</l>' for n in range(1, 41))   # macOS holds a link's target to 1,024 bytes
    (tmp_path / "copy").symlink_to(target)
    (tmp_path / "gone.xml").write_text(target, encoding="utf-8")
    (tmp_path / "plain.txt").write_text("λόγος\n", encoding="utf-8")
    git("add", "copy", "gone.xml", "plain.txt")
    (tmp_path / "gone.xml").unlink()
    files = _tracked(tmp_path)
    assert files == {"copy": target.encode(), "gone.xml": target.encode(), "plain.txt": "λόγος\n".encode()}
    problems = export_problems({**files, **_pinned()})
    assert any(p.startswith("copy: 40 export lines") for p in problems), problems
    assert any(p.startswith("gone.xml: 40 export lines") for p in problems), problems


def test_a_few_made_up_lines_pass():
    few = "".join(f'<l n="{n}">λόγος</l>' for n in range(1, FEW + 1)).encode()
    assert export_problems({"pipeline/tests/x.py": few, **_pinned()}) == []


def test_no_tracked_file_is_export_shaped_but_the_allowed_ones(capsys):
    files = _tracked()
    with_lines = {p: max(len(EXPORT_LINE.findall(t)) for t in _texts(b)) for p, b in files.items()}
    with_lines = {p: n for p, n in with_lines.items() if n}
    vendored = sorted(p for p, n in with_lines.items() if n > FEW and p.startswith(VENDORED))
    with capsys.disabled():
        print(f"\nexport-shape guard: read {len(files)} tracked files, {sum(len(b) for b in files.values())} bytes; "
              f"export lines in {len(with_lines)}, {sum(with_lines.values())} in all; "
              f"{len(vendored)} vendored TEI files listed by hash; pinned: "
              + ", ".join(f"{p} {with_lines.get(p, 0)}" for p in sorted(PINNED)))
    assert len(files) > 1000, len(files)          # git answered with the repo, not nothing
    assert len(vendored) == 94, len(vendored)     # 81 Perseus, 13 OCR'd
    assert export_problems(files) == []
