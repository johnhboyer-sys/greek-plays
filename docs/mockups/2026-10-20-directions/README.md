# Four directions, 20 October 2026

The review of the first overhaul pass and four design directions (A the
Frieze finished, B the Vase, C the Playbill, D the Edition) for the home
page, the author pages, a play page of its own, and the reader, in both
themes at 1440 and 390. Published as a Claude artifact for John's pick:
https://claude.ai/artifact/63Tg72iaZnUFAjFUDUcfMw

- `index.html`: the built page (open it from a local server; the drawing
  masks it needs are not committed).
- `page.html`, `style.css`, `app.js`: the source; `build.py` inlines them
  with `data/*.json` into `index.html`.
- `make-masks.py`: rasterizes `docs/redesign/drawings/*.svg` into the
  two-layer alpha masks under `drawings/` (needs rsvg-convert and Pillow).
- The Greek is Murray's 1902 Medea from Perseus and the English is
  Coleridge's, so the page may be shared; no TLG text is in it.
