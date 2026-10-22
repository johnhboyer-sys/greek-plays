# Proper names and Grammata T8: stage 1 count

2026-10-22. John, after Πυλάδη at Libation Bearers 20 showed "Entry not found in the vendored lexicon": find every proper name in the 44 plays and see how many Grammata's T8 lookup finds.

Data: `build/dist` of 2026-10-21 (all 44 works, default Greek text plus the other Greek editions under `ed/`), and Grammata's live packs (`grc-analyses`, `grc-lsj-t8`, `grc-lsj` from the R2 base that `lookup.js` reads), fetched 2026-10-22. Script: `scripts/sweeps/proper-names-t8.mjs`.

## Result

| | name lemmas | occurrences in the default text |
|---|---:|---:|
| all names | 1,497 | 12,434 (in 11,622 word tokens) |
| T8 shows an entry | 764 | 10,087 |
| T8 shows "Entry not found" | **733** | **2,347** |

Most of the misses are rare names: of the 733, 49 occur 10 or more times, 57 occur 5–9 times, 205 occur 2–4 times, 416 occur once, and 6 occur only in another Greek edition. The 20 most frequent misses cover 27% of the missed occurrences, the top 100 cover 58%, and the top 300 cover 81%.

The 20 most frequent misses:

| # | name | times | plays |
|---:|---|---:|---:|
| 1 | Καδμεῖος | 70 | 9 |
| 2 | Αἴγισθος | 66 | 5 |
| 3 | Εὐρυσθεύς | 39 | 4 |
| 4 | Πυλάδης | 37 | 5 |
| 5 | Ἀτρεύς | 35 | 12 |
| 6 | Ἠλέκτρη | 32 | 8 |
| 7 | Θηβαῖος | 31 | 9 |
| 8 | Κλυταιμνήστρα | 30 | 9 |
| 9 | Πενθεύς | 30 | 1 |
| 10 | Αἰσχύλος | 29 | 6 |
| 11 | Ἑκάβη | 28 | 2 |
| 12 | Ἐτεοκλῆς | 27 | 5 |
| 13 | Μυκηναῖος | 27 | 9 |
| 14 | Δαναίδαι | 25 | 9 |
| 15 | Ἀλκμήνη | 25 | 10 |
| 16 | Κιθαιρών | 24 | 5 |
| 17 | Τεῦκρος | 23 | 4 |
| 18 | Κλεώνυμος | 21 | 7 |
| 19 | Πριαμίδης | 21 | 7 |
| 20 | Θρῄκιος | 21 | 7 |

(Ἠλέκτρη is the analyser's lemma for Ἠλέκτρα; the word panel sends the lemma, so the lemma is what T8 must find.)

## Files

- `name-lemmas.tsv`: all 1,497 name lemmas: Greek, Beta Code lemma, `found`/`MISSING`, how T8 resolved it, occurrences, how many of those the edition prints lowercase, the analyser's gloss, plays, and every line citation. Sorted by occurrences.
- `missing.tsv`: the 733 misses only, same columns, most frequent first.
- `wrong-lemma.tsv`: 60 lowercase lemmas under which the editions print a capitalised name (see "Names under the wrong word" below).

No Greek text is in these files: lemmas, counts, and citations only.

## Where "Entry not found in the vendored lexicon" comes from

Grammata's `lookup.js` prints it; this site's code never does. `WordPopup.svelte` makes one card per analysis:

- If the analysis carries LSJ keys (`lsj: ['*loci/as']`), it calls `lookup('', el, { lang: 'grc', key })`. Grammata looks the key up in `grc-lsj-t8`, then `grc-lsj`. 622 name lemmas go this way; all 622 render. Four of the keys (Αἰγαίων, Ἱππόβινος, Νειλοθερής, Σκυθικός) are missing from `lsj-heads.json`, so their cards fall back to the lemma as head, but the entry still renders.
- If it has no keys, it calls `lookup(betaToGreek(lemma), el, { lang: 'grc' })`. Grammata first looks the word up in its own form index (`grc-analyses`). **If the form index knows the word, only the dictionary keys it lists there count.** Πυλάδης is in the form index with an empty key list, so the lookup stops there and prints the message. Only when the form index does not know the word does Grammata try an exact headword in `grc-lsj-t8`.

How the 733 misses fail:

- 510: Grammata's form index knows the name but lists no dictionary entry for it (Πυλάδης, Αἴγισθος, Εὐρυσθεύς).
- 219: Grammata knows neither the word nor a headword (Θρῄκιος, Τειρεσίης, Εὐρώτης).
- 4: a headword exists only lowercase or with different marks (Βορραῖος → βορραῖος, Ἰμαῖος, Μάρδος), plus Ῥῆσος, which this site's `betaToGreek` turns into `Ρ(ῆσος` (a site bug: the title character of a play).

I checked my copy of this logic against the live module in a browser on 33 lookups (14 found, 19 missed, Πυλάδης, Ὀρέστης, and ὀρέστης among them); all 33 agreed.

## What counts as a proper name

1. **A capitalised lemma** (Beta Code `*`) in the site's analyses (`analyses.json`, per work and per Greek edition). This is the analyser's own call, so it covers people, gods, places, peoples, festivals, and the adjectives made from them (Καδμεῖος, Θηβαῖος, Ἀργεῖος) wherever the analyser capitalises them.
2. **A lowercase lemma the editions print as a name.** The analyser files some major names lowercase: φοῖβος, ὀρέστης, ἑλένη, κρέων, ἕκτωρ, βρόμιος. A lowercase lemma counts when the default text prints it capitalised in at least 80% of at least 3 occurrences **and** Grammata's form index lists the capitalised word as a lemma (Ὀρέστης, Φοῖβος). 76 lemmas pass; nearly all render, because they carry LSJ keys.
3. A token counts once for each name lemma among its analyses. Counts come from the default Greek text only; the other Greek editions add lemmas (18 occur only there) and citations, not counts.

Edge cases:

- **A capitalised common word at the start of a line or speech.** These editions do not capitalise line starts, but some capitalise the first word of a speech or paragraph (ἀλλά 778 times, εἰμί 669). Rule 2's 80% test and the Grammata check keep these out.
- **Epithets** (Λοξίας, Βρόμιος, Φοῖβος, Κύπρις, Παλλάς, Κρονίδης, Λύκειος) count as names. All of them are found: LSJ files them under their own keys.
- **A capitalised lemma used as a common word**: Γαῖα is the analyser's lemma for γῆ "land", 686 of 726 times printed lowercase. Likewise Ἀπίς (70, all lowercase), Βορέας "north wind", Βάκχη and Βακχεύω, Παιάν, Πειθώ, and Αἶσα. They stay in the list (the analyser calls them names) and are marked by the `printed_lowercase` column. None of them is a miss.
- **Names under the wrong word.** 60 lowercase lemmas collect capitalised names that belong to another word. For these the word panel shows the wrong entry, not "Entry not found": Δί' (Zeus) under δίω "flee" 282 times, Ζεῦ under ζέω "boil" 123 times, Ἀπόλλων under ἀπό-λάω, Ἀντιγόνη under ἀντί-γονάω, Λαΐου under λήιον, Ἑρμῆς under ἑρμάζω, Κάλχας under κάλχη "murex". About 1,070 tokens are affected. (5 of the 60, such as ἰφιγένεια and σωκρατέω, are the right name filed lowercase under a spelling Grammata does not list capitalised.) They are not in the 1,497, and are listed in `wrong-lemma.tsv` with the lemma Grammata gives the same form. This is a fault in this site's analyses, not in Grammata, and it is a separate fix.
- **"Found" is not always the right entry.** Φοῖβος lands on LSJ's adjective φοῖβος ("pure, bright"), whose entry includes the god; Λοξίας's gloss reads "the zodiac" (LSJ's sense II). These count as found.

## The Grammata repositories (read only; nothing touched)

- `~/Developer/grammar-site`: the Astro site that deploys to grammata.pages.dev; `public/t8/lookup.js` is the module. Its checkout is on a feature branch (`claude/weekly-usage-catchup-05ktmf`), and its `lookup.js` differs from the live one.
- `~/Developer/grammars`: builds the T8 data packs on R2 (`scripts/wordtool/build_wordtool.py`, `t8rows.py`, `SPEC-t8-rows.md`). A names supplement would most likely be built here: entries in a name pack, or in `grc-lsj-t8`, plus dictionary keys on the matching form-index rows. If it is built that way, `lookup.js` and this site need no change.

## What lsj.gr does

lsj.gr shows every dictionary it has under one headword. Πυλάδης there has English and Greek Wikipedia, Bailly abrégé (French, 1901), and Dvoretsky (Russian); Στρόφιος adds Autenrieth (the Homeric dictionary, public domain); Λοξίας has LSJ itself, Slater (Pindar), Middle Liddell, and others. Each source's licence must be checked before we borrow the idea: Wikipedia is CC BY-SA (allowed under John's rule, with credit and share-alike); Dvoretsky (1958) is likely still in copyright.
