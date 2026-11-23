# corpus/greek

The Greek text of the 44 plays the site is built from: one printed line of
the edition per row, one file per play. The build reads these files for each
play's main Greek text. The other Greek editions a play offers are the
Perseus and scanned files in `sources/`. This folder holds the line files
and this page, and nothing more.

## Format

UTF-8, tab-separated, one row per printed line, in the order the edition
prints them (never sorted).

```
# work: agamemnon
# edition: Aeschylus Trag. (c. 6-5 B.C.), Agamemnon (0085: 005) "Aeschyli …
# columns: n	text
t	ΑΓΑΜΕΜΝΩΝ
1	{ΦΥΛΑΞ} Θεοὺς μὲν αἰτῶ τῶνδ' ἀπαλλαγὴν πόνων,
104	κύριός εἰμι θροεῖν ὅδιον κράτος αἴσιον ἀνδρῶν {[στρ. α.}
```

- `n` is the line's number as printed: `1`, `141a`, `208-209`, `post 410`
  for a lost line, and `t` for the title.
- The text is the line as the edition prints it, with runs of white space
  made one space. A speaker's name, or a strophe mark, stands in braces
  where the edition prints it. Angle brackets are written ⟨ ⟩. Nothing else
  is changed.
- The `# edition:` line names the edition the text is taken from.
- `pipeline/drama_pipeline/stage1_greek.py` reads the files: it tells
  speakers from strophe marks, and checks each play's lost lines,
  transposed lines, and repeated numbers against its manifest.

## Licence

CC0 1.0 Universal (https://creativecommons.org/publicdomain/zero/1.0/), for
whatever rights the site's author holds in these files. The texts are
ancient; an editor's rights in his edition, if any, are not his to give.
`sources/INVENTORY.md` names each edition and its year.

## Making the files

`python -m drama_pipeline.extract --all` (in `pipeline/`) writes them from
the digital source texts, on a machine that holds those. The source's own
files are never committed to this repository.
`pipeline/tests/test_corpus_greek.py` checks every file here on each test
run: every letter of every line must be Greek, and every label a speaker's
name or a strophe mark.
