"""Write the hand-classified samples as TSV beside the report.

Labels (one per sampled differing line; the reviewer's call, 2026-09-29):
  OCR     at least one misread the edition cannot print (count in n_err)
  UNSURE  could be a misread or the edition's own spelling; not scan-checked
  STRUCT  a layout/extraction matter, not a character misread (speaker label
          read as text, running head leak, a regex of this sweep cutting a word)
  EDIT    every difference is the edition's own reading, spelling, accentuation
          or colometry, or a slip in the comparison text
Samples come from <ed>-sample.json (seed 20260929). The Paley sample was drawn
before this sweep's strophe-mark regex was fixed; lines 83 and 194 show that bug.
"""
import json

from common import OUT

LABELS = {
    "paley": {
        "OCR": {13: "ἐκβέβηκ᾽ for ἐκβέβηχ᾽ (scan p.45)", 33: "κεὶ for κεἰ", 35: "φαίνεσθώ for φαίνεσθαί",
                46: "ὤμῳξα for ᾤμωξα (scan p.61)", 51: "οὖν for οὑν (scan p.61)", 58: "τυχοῖσ’ for τυχοῦσ’",
                65: "ἐσφάλιν for ἐσφάλην", 73: "ἀγγελεί for ἀγγελεῖ", 88: "Ἄιδου for Ἅιδου",
                104: "stray ': :'", 118: "πολὺν for πολιὸν", 126: "κάκεῖνος for κἀκεῖνος (scan p.202)",
                170: "πρέπειs (Latin s)", 191: "ὦλεσ’ for ὤλεσ’", 221: "προσειπέιν accent",
                225: "σωφρόν for σῶφρόν", 250: "ἔπεισέ μὴ spurious accent", 261: "παιδοποιήσαι for παιδοποίησαι",
                266: "οὐκ ἄζομαι for οὐχ ἅζομαι (scan p.139)", 267: "ἐκδακρύσαί for ἐκδακρῦσαί (scan p.139)",
                268: "ἐκκληΐσομεν for ἐκκλῄσομεν (scan p.139)", 279: "ἆραρ' for ἄραρ'", 293: "ἀφείσαι for ἀφεῖσαι",
                299: "πείθ᾽ for πεῖθ᾽"},
        "UNSURE": {133: "εἶρξας / εἷρξας", 200: "stray * in line", 210: "δίκα / δίκᾳ", 285: "εὐπᾶγι"},
        "STRUCT": {62: "ἔα half-line merged", 83: "sweep regex cut ἐπεστρατεύετο", 89: "child label α΄ as text",
                   121: "running head .ΒΑΚΧΑΙ. as verse", 132: "running head .ΒΑΚΧΑΙ. as verse",
                   146: "chorus-member label", 147: "chorus-member label", 148: "chorus-member label",
                   149: "chorus-member label", 150: "chorus-member label", 151: "chorus-member label",
                   152: "chorus-member label", 194: "sweep regex cut μετεστράφη"},
    },
    "jebb": {
        "OCR": {18: "’Αρτέμιδος breathing as separate mark", 26: "ἀμοὶ for ἁμοὶ", 35: "χώ for χὠ",
                47: "ἀτρεστὸν for ἄτρεστον; αὐθ’ for αὔθ’ (2 errors)", 48: "οὐπιβουλεύων for οὑπιβουλεύων",
                53: "κεί for κεἰ", 57: "μήνιν for μῆνιν", 72: "μήστι for μἤστι", 76: "κείνός for κεῖνός",
                103: "ξυνάδει for ξυνᾴδει", 112: "κἀγωγ’ for κἄγωγ’", 122: "τλήμον for τλῆμον",
                135: "τοίανδ᾽ for τοιάνδ᾽",
                161: "ηὐλάβεια for ηὑλάβεια", 163: "ἄζονθ᾽ for ἅζονθ᾽", 170: "ἄρμοσαι for ἅρμοσαι",
                180: "κεὶ for κεἰ", 181: "ἡλιοστερὴς for ἡλιοστεγὴς", 186: "σημανουσ᾽ for σημανοῦσ᾽",
                187: "κηδός for κῆδός", 188: "ὥραν for ὤραν", 190: "τούμοῦ for τοὐμοῦ",
                192: "οὐξεληλυθὼς for οὑξεληλυθὼς", 198: "χρῆσται μ’ for χρῆσταί μ’", 202: "\\ἀστάλη for ἁστάλη",
                225: "τὰν for τἀν", 228: "ξύναρπάσας accent", 233: "θείέν for θεῖέν", 234: "καθεξω for καθέξω",
                242: "᾿Αθήνας breathing as separate mark", 243: "ἔσταμεν for ἕσταμεν", 245: "χἡμεῖς for χἠμεῖς",
                252: "εὐρουσᾶν for εὑρουσᾶν", 261: "τοιάδε for τοιᾷδε", 266: "κασιγήτου for κασιγνήτου",
                268: "πτώχοι for πτωχοὶ", 272: "κὰν for κἀν", 273: "γελάσθαι for γελᾶσθαι", 275: "ἡδ᾽ for ἥδ᾽",
                296: "Αρης for Ἄρης"},
        "UNSURE": {2: "που / του", 82: "ματάζων / ματᾴζων", 109: "ἐκμήνους / ἑκμήνους", 142: "οἷν / αἷν",
                   169: "ἡσυχαίᾳ / ἁσυχαίᾳ", 185: "ἔπαθον / ἅπαθον", 193: "κατήνεσεν / κατῄνεσεν",
                   207: "ἀγὼν / ἁγὼν", 210: "ἀνὴρ / ἁνὴρ", 238: "ξυνήδη / ξυνῄδη", 269: "ἐπήσθετο / ἐπῄσθετο",
                   280: "ματᾶν / μάταν", 293: "ἀνὴρ / ἁνὴρ", 294: "παθούσα / παθοῦσα"},
        "STRUCT": {11: "strophe numeral left on line", 12: "strophe numeral left on line", 40: "turn-over [βροτῶν",
                   50: "κομμός label", 55: "strophe numeral left on line", 81: "strophe numeral left on line",
                   162: "strophe numeral", 168: "σύστ. γ' label", 214: "strophe numeral", 215: "strophe numeral",
                   217: "strophe numeral", 251: "strophe numeral", 259: "ἐπ. label", 278: "strophe numeral",
                   283: "LaTeX label $\\beta'$", 295: "running head as verse", 305: "strophe numeral"},
    },
}
TWO = {("jebb", 47)}

for ed, lab in LABELS.items():
    rows = json.loads((OUT / f"{ed}-sample.json").read_text(encoding="utf-8"))
    counts = {}
    with (OUT.parent / f"genie-ocr-quality-2026-09-29-{ed}-sample.tsv").open("w", encoding="utf-8") as fh:
        fh.write("n\tplay\tsrc_line\tcmp_n\thand_label\tn_err\tnote\tocr_line\tcomparison_line\tauto_diffs\n")
        for k, r in enumerate(rows, 1):
            label, note = "EDIT", ""
            for L in ("OCR", "UNSURE", "STRUCT"):
                if k in lab[L]:
                    label, note = L, lab[L][k]
            nerr = (2 if (ed, k) in TWO else 1) if label == "OCR" else 0
            key = (r["play"], label)
            counts[key] = counts.get(key, [0, 0])
            counts[key][0] += 1
            counts[key][1] += nerr
            d = "; ".join(f"{x['o']}>{x['c']}[{x['cls']}]" for x in r["diffs"])
            fh.write(f"{k}\t{r['play']}\t{r['src']}\t{r['pn']}\t{label}\t{nerr}\t{note}\t{r['ocr']}\t{r['cmp']}\t{d}\n")
    for k in sorted(counts):
        print(ed, k, counts[k])
