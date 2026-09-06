"""Pipeline CLI: python -m drama_pipeline <stage>|all"""

from __future__ import annotations

import argparse
import json
import sys

from .config import BUILD_DIR, Manifest


def _stage1(manifest):
    # drama_pipeline supports 'grc' only — Latin/PHI support (stage1_latin.py)
    # was removed in the drama fork. preflight's schema gate already rejects a
    # 'lat' manifest with a clear message; this is a defensive backstop for a
    # direct `drama_pipeline all`/`astro build` invocation that bypassed it.
    if manifest.language != "grc":
        raise SystemExit(
            f"{manifest.work_id}: work.language {manifest.language!r} is not "
            "supported by drama_pipeline (Latin/PHI support was removed in "
            "the drama fork; only 'grc' is supported) — this should have "
            "been caught by preflight"
        )
    from . import stage1_greek as stage1_producer

    spine_path = stage1_producer.run(manifest)
    spine = json.loads(spine_path.read_text(encoding="utf-8"))

    # build/stage1 is single-work scratch; drop any secondary-translation chunks
    # left by a previous work's build so stage7 never emits a stale overlay. It
    # is rewritten below only when this work declares english.secondary.
    for scratch in ("ross_chunks.json", "third_chunks.json", "third_footnotes.json",
                    "overlays.json", "paratext.json", "context_english.json",
                    "citation_expansion.json"):
        (BUILD_DIR / "stage1" / scratch).unlink(missing_ok=True)

    # Section-scheme works can opt into a parallel Perseus Stephanus TEI pass.
    # Others remain Greek-only, with stale English scratch removed.
    from . import scheme as scheme_mod
    sch = scheme_mod.for_manifest(manifest)
    # verse-line, numeric_section (book-section), flat_numeric, and the dk
    # fragment scheme each had their own dedicated English builder in CPR
    # (stage1_verse_line_english / stage1_book_section_english /
    # stage1_chapter_concordance_english / stage1_flat_english /
    # stage1_freeman_english) — all one-off builders with no drama use,
    # removed in the drama fork (docs/plan.md §1). The schemes themselves
    # stay registered (scheme.py); a manifest that reaches one of them here
    # has no English builder to dispatch to.
    if sch.verse_line_scheme or sch.numeric_section or sch.flat_numeric or sch.fragment_scheme:
        raise NotImplementedError(
            f"scheme {sch.name!r} has no English builder in drama_pipeline"
        )
    if sch.play_line_scheme:
        # play-line (P1 — Greek-only): no English builder yet (P2). Mirrors
        # the has_sections branch's own Greek-only posture below (stale
        # English scratch removed so a previous different-scheme work's
        # leftovers never leak into this build).
        for scratch in ("english_chunks.json", "alignment.json"):
            (BUILD_DIR / "stage1" / scratch).unlink(missing_ok=True)
        n_lines = sum(len(s["lines"]) for s in spine["segments"])
        n_speakers = sum(len(s.get("speakers", [])) for s in spine["segments"])
        print(f"stage1 (greek-only, play-line): segments={len(spine['segments'])} "
              f"lines={n_lines} speakers={n_speakers} "
              f"unassigned={len(spine['unassigned_lines'])}")
        return
    if sch.has_sections:
        primary = ((manifest.data.get("english") or {}).get("primary") or {})
        if primary.get("model") == "perseus_stephanus":
            from . import stage1_stephanus_english

            eng_path, align_path = stage1_stephanus_english.run(manifest, spine)
            english = json.loads(eng_path.read_text(encoding="utf-8"))
            alignment = json.loads(align_path.read_text(encoding="utf-8"))
            unmatched = [p["segment"] for p in alignment["pairs"] if p["english"] is None]
            print(f"  english chunks={len(english['chunks'])} ({english['translation']}) "
                  f"unmatched={len(unmatched)} english_only={len(alignment['english_only'])}")
        else:
            for scratch in ("english_chunks.json", "alignment.json"):
                (BUILD_DIR / "stage1" / scratch).unlink(missing_ok=True)
        n_lines = sum(len(s["lines"]) for s in spine["segments"])
        n_speakers = sum(len(s.get("speakers", [])) for s in spine["segments"])
        # Stephanus columns are page+letter ("17a" -> page "17"); a flat
        # scheme's column ("5") IS the page — stripping its last char would
        # collapse "5" to "" and "10"/"12" both to "1".
        pages = ({s["column"] for s in spine["segments"]} if sch.flat_numeric
                 else {s["column"][:-1] for s in spine["segments"]})
        print(f"stage1 ({'greek+english' if primary.get('model') == 'perseus_stephanus' else 'greek-only'}, {scheme_mod.for_manifest(manifest).name}): "
              f"segments={len(spine['segments'])} pages={len(pages)} "
              f"lines={n_lines} speakers={n_speakers} "
              f"unassigned={len(spine['unassigned_lines'])}")
        return

    # The remaining (Bekker-default) dispatch — chapter-anchored archive
    # English (stage1_archive/stage1_chapters) and Rackham+Ross+Ostwald
    # (stage1_english/stage1_ross/stage1_ostwald + the align/ subpackage) —
    # was entirely CPR/Aristotle-corpus machinery with no drama use, removed
    # in the drama fork (docs/plan.md §1). `has_sections` above covers every
    # scheme drama_pipeline actually builds today.
    raise NotImplementedError(
        f"scheme {sch.name!r} has no English builder in drama_pipeline"
    )


def _stage2(manifest):
    from . import stage2_validate

    stage2_validate.run(manifest)
    report = json.loads(
        (BUILD_DIR / "stage2" / "validation_report.json").read_text()
    )
    checks = " ".join(
        f"{name}={'ok' if c['ok'] else 'FAIL'}" for name, c in report["checks"].items()
    )
    print(f"stage2: {checks}")
    print(f"  overall: {'PASS' if report['ok'] else 'FAIL'}")
    if not report["ok"]:
        raise SystemExit("stage2 validation failed")


def _stage3(manifest):
    from . import stage3_tokenize

    out = stage3_tokenize.run(manifest)
    tokens = json.loads(out.read_text(encoding="utf-8"))
    n = sum(len(l["tokens"]) for s in tokens["segments"] for l in s["lines"])
    sigla = json.loads((BUILD_DIR / "stage3" / "sigla_log.json").read_text())
    failures = json.loads((BUILD_DIR / "stage3" / "key_failures.json").read_text())
    print(f"stage3: tokens={n} sigla_strips={len(sigla)} key_failures={len(failures)}")
    for fail in failures[:10]:
        print(f"  FAIL {fail['ref']}: {fail['token']} — {fail['error']}")


def _stage4(manifest):
    from . import stage4_morphology

    stage4_morphology.run(manifest)
    summary = json.loads((BUILD_DIR / "stage4" / "summary.json").read_text())
    print("stage4: " + " ".join(f"{k}={v}" for k, v in summary.items()))


def _stage5(manifest):
    from . import stage5_lsj

    out_dir = stage5_lsj.run(manifest)
    summary = json.loads((out_dir / "summary.json").read_text())
    print("stage5: " + " ".join(f"{k}={v}" for k, v in summary.items()))


def _stage6(manifest):
    from . import stage6_search

    out_dir = stage6_search.run(manifest)
    summary = json.loads((out_dir / "summary.json").read_text())
    print("stage6: " + " ".join(f"{k}={v}" for k, v in summary.items()))


def _stage7(manifest):
    from . import stage7_emit

    out_dir = stage7_emit.run(manifest)
    man = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    print(f"stage7: {out_dir}")
    print(f"  books={len(man['books'])} token_keys={man['analyses']['token_keys']} "
          f"lsj_entries={man['lsj']['lsj_entries_kept']}")


_STAGES = {
    "stage1": _stage1,
    "stage2": _stage2,
    "stage3": _stage3,
    "stage4": _stage4,
    "stage5": _stage5,
    "stage6": _stage6,
    "stage7": _stage7,
}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="drama_pipeline")
    parser.add_argument("stage", choices=[*_STAGES, "all"])
    parser.add_argument(
        "--work", default="EN",
        help="work slug = manifest filename stem (default: EN)",
    )
    parser.add_argument(
        "--public",
        action="store_true",
        help="use manifests/<work>-public.yaml when present",
    )
    args = parser.parse_args(argv)
    manifest = Manifest.for_work(args.work, public=args.public)
    if args.public:
        print(f"manifest: {manifest.path.relative_to(manifest.path.parents[1])}")
    if args.stage == "all":
        for fn in _STAGES.values():
            fn(manifest)
    else:
        _STAGES[args.stage](manifest)


if __name__ == "__main__":
    sys.exit(main())
