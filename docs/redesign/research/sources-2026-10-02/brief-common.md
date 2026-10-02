# Research brief: source images for line drawings of the Greek plays

You are a research worker. Find source images that can be traced into line drawings, one drawing per Greek play, for a free, non-commercial website that reads the 44 surviving Greek plays in Greek and English. Your lane's plays are listed in the lane file named in your task. Report candidates. Do not trace or draw anything.

## What the drawings are

Each play gets one drawing: one whole figure (or a small group) taken from a real ancient object, mostly a painted vase. The figure is cut out along its own outline and traced to black lines on a transparent ground. Six test drawings are done. The owner, John Boyer, judged them like this:

- Best: two drawings traced from 19th-century engraved or lithographed plates of real vases (the Pythia from Bötticher 1859; Iphigenia from Archäologische Zeitung 1849 Taf. XII). He liked them because they are the most detailed: dense, crisp interior lines in faces, hands and drapery.
- Not detailed enough: two drawings traced from photos of red-figure vases whose interior lines are sparse or faint (Berlin F 2355, Würzburg H 5697).
- So rank by DETAIL first: (1) a high-resolution pre-1931 line plate of a real vase; (2) a sharp, high-resolution photo of a vase with rich interior drawing (late Apulian, Lucanian, Campanian and Paestan vases often have it; so do fine Attic red-figure pieces); (3) anything else.
- Failed: a worn low-relief bowl (Met 31.11.2, Iphigenia at Aulis). Relief, sculpture, terracotta figurines and worn or blurred surfaces do not trace. Do not propose them.

## Hard rules

1. Rights. The exact file must be one of:
   - public domain: a plate published before 1931, or a scan of one (a faithful scan of a 2D public-domain work counts);
   - CC0, or a museum's own "public domain" / "open access, no restrictions" label for that image (Met, Cleveland, Walters, Getty Open Content, Yale, Smithsonian and the like);
   - CC BY-SA (any version) or CC BY (any version). Mark CC BY as "CC BY" so it can be checked.
   Excluded: anything NonCommercial or NoDerivatives (CC BY-NC, BY-NC-SA, BY-ND), "all rights reserved", "editorial use only", and museums whose image terms are non-commercial (for example the British Museum's CC BY-NC-SA). Record the licence of the exact file you link, with the URL of the page that states it, and quote the words that state it.
2. Whole figure. Not cut by the frame, a handle, damage, or another figure. Small touches that can be cut cleanly are fine; say what touches what.
3. No nudity. No exposed genitals (including the costume phallus of comic actors and satyrs) and no exposed female breasts. A bare male chest is fine. Say plainly for each candidate whether anything would need hiding.
4. Size. The chosen figure should be at least 800 px tall in the file; 1,500 px or more is much better. Old plates copied onto Wikimedia Commons are sometimes blurred enlargements of a smaller scan: prefer the holding library's own scan (Heidelberg digi.ub.uni-heidelberg.de, Internet Archive, Gallica, HathiTrust full view, Getty, Biodiversity Heritage Library) and name it.
5. The link to the play. Prefer, in this order: an object scholars tie to the play itself; an identified depiction of the play's myth or central figure; a labelled thematic object. Give the source of the identification (museum record, LIMC, Trendall & Webster, Illustrations of Greek Drama (1971), Taplin, Pots and Plays (2007), a Beazley Archive record, or a 19th-century publication's own caption). Never present a myth scene as a record of a performance.
6. Spoilers. Avoid scenes that show a play's ending or a killing when another choice exists; say when a candidate shows the ending.
7. Distinct scenes. These are already used for the playwrights' own figures, so the plays named here need a DIFFERENT scene or object: Eumenides (the Black Fury Painter's krater in Naples, Orestes at Delphi, Bötticher's plate); Oedipus Tyrannus (Berlin F 2355, Oedipus and the Sphinx); Iphigenia in Tauris (the Buckingham vase, Iphigenia handing Pylades the letter); Women at the Thesmophoria (Würzburg H 5697). Medea already has a drawing (Cleveland 1991.1); for Medea report only a source that would be clearly more detailed. Also keep the paired plays apart: the three Electra/Orestes plays, the two Suppliant Women plays and the two Iphigenia plays each need a different scene.

## Where to look (not exhaustive)

- Plates: Gerhard, Auserlesene griechische Vasenbilder (1840–58); Monumenti inediti dell'Instituto (1829–91) and its Annali; Archäologische Zeitung (1843–85); Wiener Vorlegeblätter (1888–91); Furtwängler–Reichhold, Griechische Vasenmalerei (1900–32: only plates published before 1931); Millin, Peintures de vases antiques (1808–10); Inghirami, Pitture di vasi fittili (1833–37); Raoul-Rochette, Monuments inédits (1833); Overbeck, Gallerie heroischer Bildwerke (1853); Baumeister, Denkmäler (1885–88); Roscher's Lexikon; Heydemann's papers; Wieseler; Huddilston, Greek Tragedy in the Light of Vase Paintings (1898); Bieber (1920); Séchan, Études sur la tragédie grecque dans ses rapports avec la céramique (1926), whose figures were drawn for this very subject.
- Photos: Wikimedia Commons, especially ArchaiOptix (CC BY-SA 4.0, very sharp, many South Italian vases), Bibi Saint-Pol (public domain), Jastrow (public domain), Marie-Lan Nguyen (check each file: some are public domain, some CC BY); the Met, Cleveland, Getty, Walters and Yale open-access collections.

## Limits on your tools

- You have web search. Your shell has no network: do not run curl, wget or any download. Work from search results and the pages you can see.
- If you could not see the licence statement itself, set "licence_verified": false and say what you relied on.
- Do not edit any file anywhere except the two output files named in your task. No git commands.
- Breadth before depth: get at least one candidate for every play in your lane before polishing any one play. Aim for two or three per play. Spend no more than a few minutes per play on the first pass.
- Write your results to the output files as you go (update them after each author), so partial results survive if the run stops.

## Output

Write a JSON file (path in your task) shaped like this:

```json
{
  "lane": "A",
  "plays": [
    {
      "work_id": "persians",
      "title": "Persians",
      "status": "found | weak | none",
      "candidates": [
        {
          "rank": 1,
          "kind": "plate | photo",
          "object": {"museum": "", "inventory": "", "shape": "", "painter": "", "date": ""},
          "scene": "what the whole scene shows",
          "figure": "which figure to cut out, its pose and size in the scene",
          "link_to_play": "play itself | myth | thematic",
          "identification": "who identifies the scene, and where",
          "identification_url": "",
          "publication": "for plates: author, title, volume, year, plate/figure number",
          "file_page_url": "page that shows the file and its licence",
          "file_url": "direct URL of the largest file, if known",
          "pixel_size": "e.g. 3494x5094, or null if unknown",
          "figure_height_px": "estimate, or null",
          "licence": "public domain | CC0 | CC BY-SA 4.0 | CC BY 4.0 | ...",
          "licence_verified": true,
          "licence_evidence_url": "",
          "licence_evidence_quote": "",
          "detail": "how rich the interior lines are: high | medium | low, and why",
          "risks": "overlaps, nudity, damage, spoiler, blur",
          "notes": ""
        }
      ]
    }
  ]
}
```

Also write a short Markdown summary next to it: one line per play (best candidate and status), then a list of the plays you could not source and why.

Finish with a final message that gives the two file paths and the counts of found / weak / none. If writing a file failed, put the full JSON in your final message instead.
