# Source inventory — The Greek Drama Reader

Greek: each play's main text is committed as a line file in `corpus/greek/`
(decision 1, `HANDOFF-PORTABILITY.md`), made from the local Diogenes export;
the TLG's own files, its beta code, and the export are never committed. The
other Greek editions and the English: vendored texts, one section per source
with provenance, US-PD rationale or licence, and per-file SHA-256
(`SHA256SUMS` beside the files). Populated from P2 on.

## Licences in this repository (John, 2026-11-23)

| Part | Licence |
|---|---|
| The code (pipeline, app, shared, scripts) | MIT, in `LICENSE` |
| `corpus/greek/` (each play's main Greek, one printed line per row; the editions are named in each file and below) | CC0 1.0, for whatever rights John holds in the files; an editor's rights in his edition, if any, are not his to give (see below) |
| John's own apparatus and derived data: the manifests' speaker rosters, alignments, line fixes and text fixes; the drawings (`docs/redesign/drawings/`, served at `/drawings/`); the site's own prose | CC BY 4.0 |
| The OCR'd Greek editions (`ocr/`: Jebb, Paley, Way), John's transcriptions of public-domain books | CC0 1.0 (John, 2026-11-23). The note "Not for redistribution until the owner rules on it" in each file's header predates the ruling and no longer holds |
| The fonts (`app/public/fonts/`) | SIL Open Font License 1.1, each family's text beside it |
| Everything else under `sources/`, and site data built from it | Its own terms, below. Not covered by `LICENSE` |

The terms that bind most, each as this file and the site's attribution page
already state them:

- **Perseus TEI** (`perseus/`): CC BY-SA 4.0 on the encoding; the texts are
  public domain (Smyth's, Storr's, Murray's, and Hall and Geldart's Greek;
  the English of Smyth, Jebb, Coleridge, Buckley, and Hickie's *Clouds*).
  The site's data built from them stays CC BY-SA 4.0.
- **The Kosmos Society translations** (`kosmos/`, `bench/kosmos/`): CC
  BY-NC-ND 3.0, reproduced without change, with every translator and reviser
  credited. NonCommercial and NoDerivatives: these files keep their own terms.
- **Ian Johnston's translations** (`johnston/`, `bench/johnston/`): his own
  terms (free to download, edit, and share, but not in a commercial
  publication). NonCommercial; not public domain.
- **Wikisource transcriptions** (`wikisource/`: Murray's *Frogs*, Morshead's
  Aeschylus): CC BY-SA 4.0 on the transcription; the texts are public domain.
- **Arrowsmith's *Birds* and *Clouds*** (`fulcrum/`, `bench/arrowsmith/`): the
  publisher's Creative Commons Public Domain Mark 1.0 (John's ruling,
  2026-09-11).
- **Project Gutenberg** (`gutenberg/`) and the archive.org scans
  (`archive-org/`): public-domain texts; Gutenberg's own licence terms ride
  with its files.
- **`bench/`**: the cleaned texts the build reads, each under its source's
  terms above.
- **The LSJ** (`grc.lsj.xml`, from Diogenes 4.7.2; pinned, not vendored): CC
  BY-SA 3.0 US. The site's lexicon data built from it stays CC BY-SA.
- **The Morpheus table** (`greek-analyses.txt`, from Diogenes 4.7.2; pinned,
  not vendored): its terms were not read for this table; the parses in each
  play's `analyses.json` come from it.

**The Greek editions in `corpus/greek/`.** Eight plays are from Coulon and
van Daele's Budé (1923-1930), public domain in the US. The other 36 are from
editions printed after 1930: Murray's Aeschylus (OCT, 2nd ed., 1955; 7
plays), Diggle's Euripides (OCT, 1981-1994; 19), Dain and Mazon's Sophocles
(Belles Lettres, 1955-1960; 7), Dover's *Clouds* (1968), MacDowell's *Wasps*
(1971), and Ussher's *Ecclesiazusae* (1973). The text of an ancient play holds
at most a thin copyright in the editor's choices; the site already shows all
of it.

The site's built bundle, which each deploy will attach to a GitHub release,
carries all of these. While the repository is private, so are its releases;
once it is public, every release is public with every source under its own
terms (the NonCommercial and NoDerivatives ones among them).

## perseus/ — PerseusDL/canonical-greekLit @ `341e309c821d5eca8c976bebca77c28b10bad58f` (vendored 2026-09-05; CC BY-SA 4.0 on the TEI encoding, underlying texts as listed)

Per-file SHA-256 in `sources/perseus/SHA256SUMS`. Greek files are STRUCTURAL
DONORS ONLY (Gate A line-set comparison against the TLG spine; never displayed —
the served Greek is the TLG export). English files are translation sources.

US public-domain status (pre-1931 publication) per translator — John confirms
before ship: Smyth (Loeb 1922–26) PD · Jebb (1883–1900) PD · Coleridge
(1891/1906) PD · Browning (1877) PD · Gilbert Murray, Rhesus (1913) PD ·
Hickie, Clouds (Bohn 1853) PD but BOWDLERIZED (comparison slot only) ·
**Birds "Anonymous"** = the 1912 Athenian Society text as reprinted in *The
Complete Greek Drama* (Random House 1938, ed. Oates & O'Neill). John's ruling
(2026-09-05): a PD text publicly hosted by a reputable site is used as hosted,
later editorial edits included (the MIT Classics precedent from
aristotle-reader) — so this line-keyed file is a full source for Birds, not
just an alignment aid · Perseus's other Aristophanes English (O'Neill's OWN
1938 translations) is a different translator's work: NOT vendored, DENIED
unless John rules on it explicitly.

| file | work | kind | translator / editor |
|---|---|---|---|
| tlg0006.tlg001.perseus-eng2.xml | The Cyclops | English | Edward P. Coleridge |
| tlg0006.tlg001.perseus-grc2.xml | Κύκλωψ | Greek | Gilbert Murray |
| tlg0006.tlg002.perseus-eng2.xml | Alcestis | English | Edward P. Coleridge |
| tlg0006.tlg002.perseus-grc2.xml | Ἄλκηστις | Greek | Gilbert Murray |
| tlg0006.tlg003.perseus-eng2.xml | Medea | English | Edward P. Coleridge |
| tlg0006.tlg003.perseus-grc2.xml | Μήδεια | Greek | Gilbert Murray |
| tlg0006.tlg004.perseus-eng2.xml | Heracleidae | English | Edward P. Coleridge |
| tlg0006.tlg004.perseus-grc2.xml | Ἡρακλεῖδαι | Greek | Gilbert Murray |
| tlg0006.tlg005.perseus-eng2.xml | Hippolytus | English | Edward P. Coleridge |
| tlg0006.tlg005.perseus-grc2.xml | Ἱππόλυτος | Greek | Gilbert Murray |
| tlg0006.tlg006.perseus-eng2.xml | Andromache | English | Edward P. Coleridge |
| tlg0006.tlg006.perseus-grc2.xml | Ἀνδρομάχη | Greek | Gilbert Murray |
| tlg0006.tlg007.perseus-eng2.xml | Hecuba | English | Edward P. Coleridge |
| tlg0006.tlg007.perseus-grc2.xml | Ἑκάβη | Greek | Gilbert Murray |
| tlg0006.tlg008.perseus-eng2.xml | The Suppliants | English | E. P. Coleridge |
| tlg0006.tlg008.perseus-grc2.xml | Ἱκέτιδες | Greek | Gilbert Murray |
| tlg0006.tlg009.perseus-eng2.xml | Heracles | English | Edward P. Coleridge |
| tlg0006.tlg009.perseus-grc2.xml | Ἡρακλῆς | Greek | Gilbert Murray |
| tlg0006.tlg010.perseus-eng2.xml | Ion | English | Edward P. Coleridge |
| tlg0006.tlg010.perseus-grc2.xml | Ἴων | Greek | Gilbert Murray |
| tlg0006.tlg011.perseus-eng2.xml | The Trojan Women | English | Edward P. Coleridge |
| tlg0006.tlg011.perseus-grc2.xml | Τρῳάδες | Greek | Gilbert Murray |
| tlg0006.tlg012.perseus-eng2.xml | Electra | English | Edward P. Coleridge |
| tlg0006.tlg012.perseus-grc2.xml | Ἠλέκτρα | Greek | Gilbert Murray |
| tlg0006.tlg013.perseus-eng2.xml | Iphigenia Among the Tauri | English | Edward P. Coleridge |
| tlg0006.tlg013.perseus-grc2.xml | Ἰφιγένεια ἐν Ταύροις | Greek | Gilbert Murray |
| tlg0006.tlg014.perseus-eng2.xml | Helen | English | Edward P. Coleridge |
| tlg0006.tlg014.perseus-grc2.xml | Ἑλένη | Greek | Gilbert Murray |
| tlg0006.tlg015.perseus-eng2.xml | The Phoenician Maidens | English | Edward P. Coleridge |
| tlg0006.tlg015.perseus-grc2.xml | Φοίνισσαι | Greek | Gilbert Murray |
| tlg0006.tlg016.perseus-eng2.xml | Orestes | English | Edward P. Coleridge |
| tlg0006.tlg016.perseus-grc2.xml | Ὀρέστης | Greek | Gilbert Murray |
| tlg0006.tlg017.perseus-eng2.xml | Bacchae | English | T. A. Buckley |
| tlg0006.tlg017.perseus-grc2.xml | Βάκχαι | Greek | Gilbert Murray |
| tlg0006.tlg018.perseus-eng2.xml | Iphigenia in Aulis | English | Edward P. Coleridge |
| tlg0006.tlg018.perseus-grc2.xml | Ἰφιγένεια ἐν Αὐλίδι | Greek | Gilbert Murray |
| tlg0006.tlg019.perseus-eng3.xml | Rhesus | English | Edward P. Coleridge |
| tlg0006.tlg019.perseus-eng4.xml | Rhesus | English | Gilbert Murray |
| tlg0006.tlg019.perseus-grc2.xml | Ῥῆσος | Greek | Gilbert Murray |
| tlg0011.tlg001.perseus-eng3.xml | Trachiniae | English | Richard Jebb |
| tlg0011.tlg001.perseus-grc2.xml | Τραχίνιαι | Greek | Francis Storr |
| tlg0011.tlg002.perseus-eng2.xml | Antigone | English | Richard Jebb |
| tlg0011.tlg002.perseus-grc2.xml | Ἀντιγόνη | Greek | Francis Storr |
| tlg0011.tlg003.perseus-eng2.xml | Ajax | English | Richard Jebb |
| tlg0011.tlg003.perseus-grc2.xml | Αἴας | Greek | Francis Storr |
| tlg0011.tlg004.perseus-eng2.xml | Oedipus Tyrannus | English | Richard Jebb |
| tlg0011.tlg004.perseus-grc2.xml | Οἰδίπους Τύραννος | Greek | Francis Storr |
| tlg0011.tlg005.perseus-eng2.xml | Electra | English | Richard Jebb |
| tlg0011.tlg005.perseus-grc2.xml | Ἠλέκτρα | Greek | Francis Storr |
| tlg0011.tlg006.perseus-eng2.xml | Philoctetes | English | Richard Jebb |
| tlg0011.tlg006.perseus-grc2.xml | Φιλοκτήτης | Greek | Francis Storr |
| tlg0011.tlg007.perseus-eng2.xml | Oedipus at Colonus | English | Richard Jebb |
| tlg0011.tlg007.perseus-grc2.xml | Οἰδίπους ἐπὶ Κολωνῷ | Greek | Francis Storr |
| tlg0019.tlg001.perseus-grc2.xml | Ἀχαρνῆς | Greek | F. W. Hall |
| tlg0019.tlg002.perseus-grc2.xml | Ἱππῆς | Greek | F. W. Hall |
| tlg0019.tlg003.perseus-eng2.xml | Clouds | English | William James Hickie |
| tlg0019.tlg003.perseus-grc2.xml | Νεφέλαι | Greek | F. W. Hall |
| tlg0019.tlg004.perseus-grc2.xml | Σφῆκες | Greek | F. W. Hall |
| tlg0019.tlg005.perseus-grc2.xml | Εἰρήνη | Greek | F. W. Hall |
| tlg0019.tlg006.perseus-eng2.xml | Birds | English | Anonymous |
| tlg0019.tlg006.perseus-grc2.xml | ? | Greek | F. W. Hall |
| tlg0019.tlg007.perseus-grc2.xml | Λυσιστράτη | Greek | F. W. Hall |
| tlg0019.tlg008.perseus-grc2.xml | Θεσμοφοριάζουσαι | Greek | F. W. Hall |
| tlg0019.tlg009.perseus-grc2.xml | Βάτραχοι | Greek | F. W. Hall |
| tlg0019.tlg010.perseus-grc2.xml | Ἐκκλησιάζουσαι | Greek | F. W. Hall |
| tlg0019.tlg011.perseus-grc2.xml | Πλοῦτος | Greek | F. W. Hall |
| tlg0085.tlg001.perseus-eng2.xml | Suppliant Maidens | English | Herbert Weir Smyth |
| tlg0085.tlg001.perseus-grc2.xml | Ἱκέτιδες | Greek | Herbert Weir Smyth |
| tlg0085.tlg002.perseus-eng2.xml | Persians | English | Herbert Weir Smyth |
| tlg0085.tlg002.perseus-grc2.xml | Πέρσαι | Greek | Herbert Weir Smyth |
| tlg0085.tlg003.perseus-eng2.xml | Prometheus Bound | English | Herbert Weir Smyth |
| tlg0085.tlg003.perseus-grc2.xml | Προμηθεὺς δεσμώτης | Greek | Herbert Weir Smyth |
| tlg0085.tlg004.perseus-eng2.xml | Seven Against Thebes | English | Herbert Weir Smyth |
| tlg0085.tlg004.perseus-grc2.xml | Ἑπτὰ ἐπὶ Θήβας | Greek | Herbert Weir Smyth |
| tlg0085.tlg005.perseus-eng3.xml | Agamemnon | English | Herbert Weir Smyth |
| tlg0085.tlg005.perseus-eng4.xml | Agamemnon | English | Robert Browning |
| tlg0085.tlg005.perseus-grc2.xml | Ἀγαμέμνων | Greek | Herbert Weir Smyth |
| tlg0085.tlg006.perseus-eng2.xml | Libation Bearers | English | Herbert Weir Smyth |
| tlg0085.tlg006.perseus-grc2.xml | Χοηφóρoι | Greek | Herbert Weir Smyth |
| tlg0085.tlg007.perseus-eng2.xml | Eumenides | English | Herbert Weir Smyth |
| tlg0085.tlg007.perseus-grc2.xml | Εὐμενίδες | Greek | Herbert Weir Smyth |

## gutenberg/ — Project Gutenberg plaintext + HTML (vendored 2026-09-05; PG license permits redistribution; the texts are PD-US)

| file | contents | translator / edition | PD basis |
|---|---|---|---|
| pg8688.* | *The Eleven Comedies*, vol. 1: Knights, Acharnians, Peace, Lysistrata, Clouds | Anonymous, The Athenian Society, London 1912 ("literally and completely translated" — unexpurgated) | 1912 < 1931 |
| pg8689.* | *The Eleven Comedies*, vol. 2: Wasps, Birds, Frogs, Thesmophoriazusae, Ecclesiazusae, Plutus | same | 1912 < 1931 |
| pg7700.* | Lysistrata | Jack Lindsay (Fanfrolico Press, 1925; unexpurgated) | 1925 < 1931 (UK publication, PD-US by date) |
| pg14417.txt | Aeschylus, *Agamemnon* | Gilbert Murray, rhyming verse; London: George Allen & Unwin, "Tenth Thousand" (no date printed in the file) | first published 1920 (not verified from the file) < 1931 |
| pg27673.txt | Sophocles, *Oedipus, King of Thebes* | Gilbert Murray ("First published February 1911") | 1911 < 1931 |
| pg35451.txt | Euripides, *Medea* | Gilbert Murray ("Copyright, 1906"; Oxford University Press, American Branch, 1912) | 1906 < 1931 |
| pg35173.txt | Euripides, *Bacchae* | Gilbert Murray (George Allen, second edition, 1906) | 1906 < 1931 |
| pg35171.txt | Euripides, *The Trojan Women* | Gilbert Murray (1905) | 1905 < 1931 |
| pg8418.txt | Euripides, *Hippolytus* and *Bacchae* (only Hippolytus is used) | Gilbert Murray (no date printed in the file) | first published 1902 (not verified from the file) < 1931 |
| pg5063.txt | Euripides, *Iphigenia in Tauris* | Gilbert Murray (no date printed in the file) | first published 1910 (not verified from the file) < 1931 |
| pg35170.txt | Euripides, *Rhesus* | Gilbert Murray (1913) | 1913 < 1931 |
| pg14322.txt | Euripides, *Electra* | Gilbert Murray ("First Edition, November 1905") | 1905 < 1931 |
| pg10523.txt | Euripides, *Alcestis* | Gilbert Murray (1915) | 1915 < 1931 |

SHA-256 in `sources/gutenberg/SHA256SUMS`. No Greek line numbers in any of these; they align by speaker turn (plan §4).
The ten Murray files were fetched 2026-09-12 from gutenberg.org/files/<n>/ (`-8.txt` Latin-1, `-0.txt` UTF-8, as served).
`sources/bench/murray/<work id>.txt` (verse-own-line turn-text) is written from them, and from the Wikisource Frogs below, by
`python -m drama_pipeline.murray_clean`; `pipeline/tests/test_murray_clean.py` checks each committed file is exactly the
converter's output. Each play is cut at its own heading and at its notes; stage directions stay; a lettered cue joins its
name ("ELDER B" → "ELDER-B") and a leading article goes, as for Johnston.

## wikisource/ — Gilbert Murray's *Frogs* (vendored 2026-09-12; comparison slot)

`frogs-murray-1912.html`: the rendered text of https://en.wikisource.org/wiki/Frogs_(Murray_1912)/Text
(page revision 11384750; the text is transcluded from the proofread scan pages of `Index:Frogs (Murray
1912).djvu`, pages 11–116), fetched 2026-09-12 through the MediaWiki `action=parse` API. Aristophanes, *The
Frogs*, translated into English rhyming verse by Gilbert Murray (1912, per the Wikisource header): 1912 < 1931,
public domain in the US. SHA-256 in `sources/wikisource/SHA256SUMS`.

## wikisource/morshead/ — E. D. A. Morshead's Aeschylus (vendored 2026-09-15; replaces the archive-org OCR scans below as the secondary slot for all seven Aeschylus plays)

Fetched 2026-09-15 through the REST `page/html` API (`https://en.wikisource.org/api/rest_v1/page/html/<title>`).
Aeschylus, translated into English verse by E. D. A. Morshead: the translation is public domain (1881 and 1908,
both < 1931); Wikisource's transcription of it is licensed CC BY-SA 4.0 (per the site's standard terms). SHA-256
in `sources/wikisource/morshead/SHA256SUMS`.

| file | source page | revision | status as the page shows it |
|---|---|---|---|
| persians.html | [Four Plays of Aeschylus (1908) Morshead/Persians](https://en.wikisource.org/wiki/Four_Plays_of_Aeschylus_(1908)_Morshead/Persians) | 6905898 | validated |
| prometheus-bound.html | [Four Plays of Aeschylus (1908) Morshead/Prometheus Bound](https://en.wikisource.org/wiki/Four_Plays_of_Aeschylus_(1908)_Morshead/Prometheus_Bound) | 6907853 | validated |
| seven-against-thebes.html | [Four Plays of Aeschylus (1908) Morshead/Seven against Thebes](https://en.wikisource.org/wiki/Four_Plays_of_Aeschylus_(1908)_Morshead/Seven_against_Thebes) | 6909680 | validated |
| suppliants-aesch.html | [Four Plays of Aeschylus (1908) Morshead/Suppliant Maidens](https://en.wikisource.org/wiki/Four_Plays_of_Aeschylus_(1908)_Morshead/Suppliant_Maidens) | 6885638 | validated |
| agamemnon.html | [The House of Atreus/Agamemnon](https://en.wikisource.org/wiki/The_House_of_Atreus/Agamemnon) | 14482130 | no ProofreadPage status (plain wikitext, not scan-backed) |
| libation-bearers.html | [The House of Atreus/The Libation-Bearers](https://en.wikisource.org/wiki/The_House_of_Atreus/The_Libation-Bearers) | 14482122 | no ProofreadPage status (plain wikitext, not scan-backed) |
| eumenides.html | [The House of Atreus/The Furies](https://en.wikisource.org/wiki/The_House_of_Atreus/The_Furies) | 14482129 | no ProofreadPage status (plain wikitext, not scan-backed) |

*Four Plays of Aeschylus* (1908) is scan-backed (ProofreadPage transclusion of `Index:Four Plays of Aeschylus
(1908) Morshead.djvu`) and every one of its pages carries `data-page-quality="4"` ("validated": proofread twice
against the scan). *The House of Atreus* (1881, in `<poem>` markup) carries no such indicator at all -- it was
never run through ProofreadPage, so there is no page-by-page quality signal to report for those three.
`sources/bench/morshead/<work id>.txt` is written from these by `python -m drama_pipeline.morshead_clean`;
`pipeline/tests/test_morshead_clean.py` checks each committed file is exactly the converter's output.

## archive-org/ — OCR plaintext (`_djvu.txt`) of bench-translation scans (vendored 2026-09-05; texts pre-1931, PD-US; OCR quality to be judged per volume in P3)

| file | contents | translator / edition |
|---|---|---|
| sophocleswitheng01soph.txt | Sophocles Loeb vol. 1 (OT, OC, Antigone) | F. Storr, 1912 |
| in.ernet.dli.2015.183451.txt | Sophocles Loeb vol. 2 (Ajax, Electra, Trachiniae, Philoctetes) | F. Storr, 1913 |
| euripidesway01–04euriuoft.txt | Euripides Loeb vols. 1–4 (all 19 plays) | A. S. Way, 1912 |
| houseofatreusbei00aesc.txt | The House of Atreus (Agamemnon, Libation-Bearers, Furies) | E. D. A. Morshead, 1904 ed. — **retired from the site 2026-09-15: the secondary slot for these three plays now reads Wikisource's proofread transcription of the 1881 first edition (`sources/wikisource/morshead/`), not this OCR scan; kept vendored, unused.** |
| suppliantmaidens00aesc.txt | Suppliant Maidens, Persians, Seven, Prometheus | E. D. A. Morshead, 1908 ed. — **retired from the site 2026-09-15: the secondary slot for these four plays now reads Wikisource's validated transcription (`sources/wikisource/morshead/`), not this OCR scan; kept vendored, unused.** |

SHA-256 in `sources/archive-org/SHA256SUMS`. Loeb scans interleave the Greek
facing pages with the English; the P3 builder keeps only the English pages.

## archive-org/ additions (vendored 2026-09-08; OCR `_djvu.txt`; PD-US)

| file | contents | translator / edition |
|---|---|---|
| in.ernet.dli.2015.515629.txt | The Comedies of Aristophanes vol. 1 (Bohn): Acharnians, Knights, Clouds, Wasps, Peace, Birds | W. J. Hickie, 1853 — prose, bowdlerized (comparison slot only) — **retired from the site 2026-09-14 (OCR too damaged on the ten comedies it fed, 1,095 of 2,912 pieces measured); back on the site 2026-09-22 for the five comedies this volume covers besides Clouds, from the owner's own History Genie OCR of the same scan (`build/genie/in.ernet.dli.2015.515629.txt`, not this ABBYY text), read fresh by `pipeline/drama_pipeline/hickie_clean.py`. All five ride the `secondary` slot. A handful of Greek line spans Genie's own OCR drops outright (Wasps 1475; Birds 474–476, 830–849, 1412–1414; Acharnians, Knights, Peace none) are left as honest gaps, never spliced — logged per play in the converter's own run output. Clouds still uses Hickie via the Perseus TEI, not this file. This ABBYY text stays vendored, unused.** |
| in.ernet.dli.2015.515630.txt | The Comedies of Aristophanes vol. 2 (Bohn): Lysistrata, Thesmophoriazusae, Frogs, Ecclesiazusae, Plutus | W. J. Hickie, 1853 — prose, bowdlerized (comparison slot only) — **back on the site 2026-09-17 for all five plays this volume covers, from the owner's own History Genie OCR of the same scan (`build/genie/in.ernet.dli.2015.515630.txt`, not this ABBYY text), read fresh by `pipeline/drama_pipeline/hickie_clean.py`. Lysistrata rides the `third` slot, the other four `secondary`. A handful of Greek line spans Genie's own OCR drops outright (Lysistrata 591–612; Thesmophoriazusae 127–143; Frogs 1230–1244 and 1322–1345; Ecclesiazusae none) are left as honest gaps, never spliced (no earlier good Hickie bench exists for these five plays to splice from) — logged per play in the converter's own run output. Thesmophoriazusae's Echo/Andromeda scene keeps two short passages (mirroring Rogers's own declined 643–648 in the same scene) where Hickie himself substituted a Latin citation for the English. This ABBYY text stays vendored, unused.** |
| aristophanes0003benj_r6k0.txt | Aristophanes, Loeb vol. 3 (Lysistrata, Thesmophoriazusae, Ecclesiazusae, Plutus) | B. B. Rogers, 1924 — verse, bowdlerized (comparison only) — **rebuilt 2026-09-17: the Rogers bench (`sources/bench/rogers/*.txt`) now comes from the owner's second, independent History Genie OCR pass of this same item (`build/genie/aristophanes0003benj_r6k0.txt`), read fresh by `pipeline/drama_pipeline/rogers_clean.py`, not patched line by line against this ABBYY text as before. Four short stretches Genie's own OCR drops outright (Thesmophoriazusae 1040–1055 and 1152–1153, Ecclesiazusae 464–468, Wealth 819–843) were checked against this ABBYY text for a splice; none was usable (itself either the collapsed-cue/bare-cue OCR damage this rebuild exists to fix, or Greek-letter garbage), so those four stretches are left as honest gaps rather than papered over, logged in `build/genie/rebuild-rogers-<id>-2026-09-17.tsv`.** |
| aristophaniscomo04aris.txt | The Comedies of Aristophanes (1910 collected volume incl. Lysistrata) | B. B. Rogers |

## fulcrum/ — William Arrowsmith's Birds and Clouds (vendored 2026-09-11; third comparison slot)

William Arrowsmith, *The Complete Greek Comedy* (University of Michigan Press):
*Birds* (1961) and *Clouds* (1962), verse, unexpurgated. Downloaded by the
project owner from Fulcrum (free, open access) and OCR'd by him with History
Genie; the PDFs and .docx files are not committed, the extracted text is:
*Birds* https://www.fulcrum.org/concern/monographs/n009w531d (DOI
[10.3998/mpub.12945782](https://doi.org/10.3998/mpub.12945782)); *Clouds*
https://www.fulcrum.org/concern/monographs/pr76f649p (DOI
[10.3998/mpub.12945776](https://doi.org/10.3998/mpub.12945776)).

**Licence basis** (owner's ruling 2026-09-11, supersedes the "never renewed"
wording used elsewhere in this file): these two books were NOT left
unrenewed. Copyright Office records show renewals by Arrowsmith as author —
*Birds* RE0000457018 (1989-12-26, renewing A00000527041 of 1961-10-13) and
*Clouds* RE0000500595 (1990-12-03, renewing A00000552209 of 1962-03-02). The
basis for treating them as public domain is instead the publisher's own
label: the University of Michigan Press marks both Fulcrum editions with the
Creative Commons [Public Domain Mark 1.0](https://creativecommons.org/publicdomain/mark/1.0/).
The owner's ruling: "If they label that way, and they are the publisher,
that's good enough for me."

**Provenance**: the owner OCR'd each play from the Fulcrum PDF with History
Genie (`.docx`, then `textutil -convert html`/`-convert txt` to
`build/arrowsmith/genie-{birds,clouds}.{html,txt}` — the html keeps the
italic runs the txt loses, and is the cleaner's actual input). The `.docx`
covers the whole book; only the play (not the introduction, notes, or
glossary) is vendored. SHA-256 of the owner's `.docx` files: *Birds*
`9acbb23ab32880dfae1f2d91e5b675e9bf6c949b2dbd075b5e1163b014d45d8c`; *Clouds*
`66d5ecd3a83a187beed70204ebac2d12e9ed3b81d20a0064f3e4ae36d972bd71`. SHA-256
of the Fulcrum PDFs (not committed): *Birds* (9780472910861.pdf)
`e5b9cf5df6b51ba519129d80437b7502fa06c3a606a4fa989a863b615eed2f03`; *Clouds*
(9780472910809.pdf)
`b471e248f75772701982928029290e9d65722340dfa1b0729dd3b0b202e0007f`. A
word-level diff of the play text against each PDF's own `pdftotext` layer
(`sources/fulcrum/{birds,clouds}.txt`, extraction command below) found the
PDF layer wrong in nearly every disagreement (`Pil`/`J`/`'m` for `I'll`/`I`/
`I'm`, scrambled column reading order); no Genie slip survived into the
cleaned dialogue text — see `build/arrowsmith/{birds,clouds}-changes.tsv`.

| file | contents | extraction command |
|---|---|---|
| birds.txt | *Birds*, printed pp. 13–113 (PDF pp. 18–113) | `pdftotext -f 18 -l 113 9780472910861.pdf birds.txt` |
| clouds.txt | *Clouds*, printed pp. 11–113 (PDF pp. 14–116) | `pdftotext -f 14 -l 116 9780472910809.pdf clouds.txt` |

SHA-256 (raw text plus the two PDFs) in `sources/fulcrum/SHA256SUMS`. The
cleaned turn-text the site actually reads is `sources/bench/arrowsmith/
{birds,clouds}.txt` (verse-own-line, built by `bench_clean_verse.
write_clean_genie_html` from the Genie html, not from these raw files).

## kosmos/ — Kosmos Society / Center for Hellenic Studies online Sourcebook (vendored 2026-09-12; third comparison slot on 13 tragedies)

The raw play pages as served on 2026-09-12 (curl, one page every 4 s),
listed from https://kosmossociety.org/text-library/. The Sourcebook is
edited by Gregory Nagy. Per-file SHA-256 in `sources/kosmos/SHA256SUMS`.

**Licence basis**: the texts are reproduced without change under
[CC BY-NC-ND 3.0](https://creativecommons.org/licenses/by-nc-nd/3.0/), with
credit to every translator and reviser; this site is non-commercial. Nagy,
as quoted on the text-library page: "All the translations in
this online Sourcebook are free from copyright restrictions. That is because
the translations belong either to me or to other authors who have waived
copyright or to authors who died in a time that precedes any further
application of copyright."

| file | work id | page | credit (as printed on the page) |
|---|---|---|---|
| seven-against-thebes.html | seven-against-thebes | https://kosmossociety.org/seven-against-thebes-aeschylus/ | Translated by Herbert Weir Smyth / Revised by the *Seven Against Thebes* Heroization team (Hélène Emeriaud, Kelly Lambert, Janet M. Ozsolak, Sarah Scott, Keith Stone) |
| agamemnon.html | agamemnon | https://kosmossociety.org/agamemnon-aeschylus/ | Translated by Herbert Weir Smyth / Revised by Gregory Crane and Graeme Bird / Further Revised by Gregory Nagy |
| libation-bearers.html | libation-bearers | https://kosmossociety.org/libation-bearers-aeschylus/ | Translated by Jim Erdman / Further Revised by Gregory Nagy |
| eumenides.html | eumenides | https://kosmossociety.org/eumenides-aeschylus/ | Translated by Herbert Weir Smyth / Revised by Cynthia Bannon / Further Revised by Gregory Nagy |
| antigone.html | antigone | https://kosmossociety.org/antigone-sophocles-2/ | Translation of R. C. Jebb / Revised by Pierre Habel and Gregory Nagy / Newly revised by the Hour 25 Antigone Team (Brian Prescott-Decie, Jacqui Donlon, Jessica Eichelburg, Claudia Filos, Sarah Scott) |
| oedipus-coloneus.html | oedipus-coloneus | https://kosmossociety.org/sophocles-oedipus-at-colonus/ | Translated by R. C. Jebb / Revised by Roger Ceragioli / Further Revised by Gregory Nagy |
| oedipus-tyrannus.html | oedipus-tyrannus | https://kosmossociety.org/oedipus-tyrannus-sophocles/ | Translated by R. C. Jebb / Revised by Alex Sens / Further Revised by Gregory Nagy |
| helen.html | helen | https://kosmossociety.org/euripides-helen/ | Translation by E. P. Coleridge / Revised by the Helen Heroization team (Hélène Emeriaud, Claudia Filos, Janet M. Ozsolak, Sarah Scott, Jack Vaughan) |
| heracles.html | heracles | https://chs.harvard.edu/primary-source/euripides-herakles | Translated by Robert Potter / Adapted by Mary Ebbott and Casey Dué / Further adapted by Miriam Kamil |
| medea.html | medea | https://kosmossociety.org/euripides-medea/ | Translated by E.P. Coleridge, / revised by Roger Ceragioli, / further revised by Gregory Nagy / Newly revised by the Hour 25 Medea Heroization Team / (Jessica Eichelburg, Hélène Emeriaud, Claudia Filos, Janet M. Ozsolak, Sarah Scott, Jack Vaughan) |
| trojan-women.html | trojan-women | https://kosmossociety.org/trojan-women-euripides/ | Translated by E. P. Coleridge. / Revised by the *Trojan Women* Heroization team (Keith DeStone, Hélène Emeriaud, Kelly Lambert, Janet M. Ozsolak, Sarah Scott) |
| bacchae.html | bacchae | https://kosmossociety.org/bacchae-euripides/ | Translated by T. A. Buckley / Revised by Alex Sens / Further Revised by Gregory Nagy |
| hippolytus.html | hippolytus | https://kosmossociety.org/hippolytus-euripides/ | Translated by E. P. Coleridge / Revised by Mary Jane Rein / Further Revised by Gregory Nagy |

The text-library link for *Seven* is malformed (`http://seven-against-thebes-aeschylus/`);
the page was fetched from its kosmossociety.org path. *Oedipus Tyrannus*
answered HTTP 500 once and was fetched on a retry.

**Derived text**: `sources/bench/kosmos/<work id>.txt` (verse-own-line
turn-text) is written from these pages by `python -m
drama_pipeline.kosmos_clean`; `pipeline/tests/test_kosmos_clean.py` checks
each committed file is exactly the converter's output. The Sourcebook's
Greek line numbers (every fifth line) and footnotes are dropped; bracketed
Greek terms stay as printed. The pages never number the first line of a
speech, so the column aligns by speaker turn, not by line.

## johnston/ — Ian Johnston's verse translations (vendored 2026-09-12; third or overlay comparison slot on 23 plays)

Ian Johnston (Vancouver Island University, Nanaimo, BC) keeps his
translations on his "johnstonia" pages at https://web.viu.ca/johnstoi/.
The 22 pages below were fetched from there on 2026-09-12 (curl, one page
every 2 s). The index links most plays to a mirror,
`johnstoniatexts.x10host.com`, whose account is suspended; `bacchae.htm` is
the Wayback Machine's 2022 copy of that mirror's Bacchae page
(https://web.archive.org/web/2022id_/http://johnstoniatexts.x10host.com/euripides/bacchaehtml.html,
gunzipped), his own page and text, since web.viu.ca has no Bacchae.
`copyright.htm` is his terms page as served. Per-file SHA-256 in
`sources/johnston/SHA256SUMS`.

**Licence basis** (owner's ruling 2026-09-12: a translation whose terms
allow reproduction may be used, honouring the terms and crediting the
translator). Johnston's terms, https://web.viu.ca/johnstoi/copyright.htm,
verbatim: "All general readers, teachers, students, and performing artists
may download any material on johnstonia web pages without permission and
without charge, provided they do not use the material in a commercial
publication. They may edit the material to suit their purposes and
distribute the texts in printed or electronic form to their friends and
students." The site is free and non-commercial. Not public domain: each
manifest slot declares `license: {status: licensed}`.

| file | work id | page |
|---|---|---|
| agamemnon.htm | agamemnon | https://web.viu.ca/johnstoi/aeschylus/aeschylus_agamemnon.htm |
| libation-bearers.htm | libation-bearers | https://web.viu.ca/johnstoi/aeschylus/libationbearers.htm |
| eumenides.htm | eumenides | https://web.viu.ca/johnstoi/aeschylus/aeschylus_eumenides.htm |
| persians.htm | persians | https://web.viu.ca/johnstoi/aeschylus/persiansweb.htm |
| prometheus-bound.htm | prometheus-bound | https://web.viu.ca/johnstoi/aeschylus/prometheusbound.htm |
| seven-against-thebes.htm | seven-against-thebes | https://web.viu.ca/johnstoi/aeschylus/sevenagainstthebesweb.htm |
| suppliants-aesch.htm | suppliants-aesch | https://web.viu.ca/johnstoi/aeschylus/suppliantwomen.htm |
| ajax.htm | ajax | https://web.viu.ca/johnstoi/sophocles/ajax.htm |
| antigone.htm | antigone | https://web.viu.ca/johnstoi/sophocles/antigone.htm |
| oedipus-tyrannus.htm | oedipus-tyrannus | https://web.viu.ca/johnstoi/sophocles/oedipustheking.htm |
| oedipus-coloneus.htm | oedipus-coloneus | https://web.viu.ca/johnstoi/sophocles/oedipusatcolonus.htm |
| philoctetes.htm | philoctetes | https://web.viu.ca/johnstoi/sophocles/philoctetes.htm |
| electra-eur.htm | electra-eur | https://web.viu.ca/johnstoi/euripides/electra.htm |
| hippolytus.htm | hippolytus | https://web.viu.ca/johnstoi/euripides/hippolytus.htm |
| medea.htm | medea | https://web.viu.ca/johnstoi/euripides/medea.htm |
| orestes.htm | orestes | https://web.viu.ca/johnstoi/euripides/orestes.htm |
| bacchae.htm | bacchae | Wayback copy of http://johnstoniatexts.x10host.com/euripides/bacchaehtml.html (2022) |
| birds.htm | birds | https://web.viu.ca/johnstoi/aristophanes/birds.htm |
| clouds.htm | clouds | https://web.viu.ca/johnstoi/aristophanes/clouds.htm |
| frogs.htm | frogs | https://web.viu.ca/johnstoi/aristophanes/frogs.htm |
| knights.htm | knights | https://web.viu.ca/johnstoi/aristophanes/knightsweb.htm |
| lysistrata.htm | lysistrata | https://web.viu.ca/johnstoi/aristophanes/lysistrata.htm |
| peace.htm | peace | https://web.viu.ca/johnstoi/aristophanes/peace.htm |

**Derived text**: `sources/bench/johnston/<work id>.txt` (verse-own-line
turn-text) is written from these pages by `python -m
drama_pipeline.johnston_clean`; `pipeline/tests/test_johnston_clean.py`
checks each committed file is exactly the converter's output. Johnston
numbers every tenth line of his English and every tenth Greek line in
brackets, mid-speech, never at a speech start, so the column aligns by
speaker turn; both numbers and the footnote calls are dropped, stage
directions stay. A few printed cues are respelled so the turn parser reads
them as cues, and the reader shows them so: a number becomes a word
("CHORUS MEMBER 1" → "CHORUS MEMBER ONE"), a lone letter joins its name
("WOMAN C" → "WOMAN-C"), a leading article goes ("A SECOND HOOPOE" →
"SECOND HOOPOE"), and a lowercase "and" in a joint cue is capitalised.
