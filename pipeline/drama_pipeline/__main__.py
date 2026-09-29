"""Pipeline CLI: python -m drama_pipeline <stage>|all"""

from __future__ import annotations

import argparse
import json
import sys
import os
from pathlib import Path

# Each stage imports BUILD_DIR at module load, so set it before config loads.
if "--edition" in sys.argv:
    _i = sys.argv.index("--edition")
    if _i + 1 < len(sys.argv) and "--work" in sys.argv:
        _w = sys.argv[sys.argv.index("--work") + 1]
        os.environ["DRAMA_BUILD_DIR"] = str(Path(__file__).resolve().parents[2] / "build" / "editions" / _w / sys.argv[_i + 1])

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
    if manifest.data["work"].get("greek_source", {}).get("kind") in {"perseus-tei", "ocr-tei"}:
        from . import stage1_tei_greek as stage1_producer
    else:
        from . import stage1_greek as stage1_producer

    spine_path = stage1_producer.run(manifest)
    spine = json.loads(spine_path.read_text(encoding="utf-8"))

    # build/stage1 is single-work scratch; drop any secondary-translation chunks
    # left by a previous work's build so stage7 never emits a stale overlay. It
    # is rewritten below only when this work declares english.secondary.
    for scratch in ("ross_chunks.json", "third_chunks.json", "third_footnotes.json",
                    "overlays.json", "paratext.json", "context_english.json",
                    "citation_expansion.json", "english_report.json",
                    "english_footnotes.json", "secondary_footnotes.json",
                    "secondary_report.json", "third_report.json",
                    # secondary/third's own englishCoveredBy map (round 9 §4
                    # option A, stage7_emit.py's per-column "coveredBy"):
                    # left uncleared here before, these were never read back
                    # by anything, so a previous work's stale map sat
                    # harmlessly; stage7_emit.run now reads them, so a work
                    # with no english.secondary/third must see none of it.
                    "secondary_alignment.json", "third_alignment.json"):
        (BUILD_DIR / "stage1" / scratch).unlink(missing_ok=True)
    # Overlay report/alignment files are named per translation id
    # (overlay_<id>_report.json), so a fixed list can't cover them; a play
    # with fewer overlays than the previous build otherwise keeps the extra
    # overlay's stale report (the audit sheet reads it and reports it as
    # this play's) -- and, since round 9 §4, its stale coveredBy map too.
    for stale in (BUILD_DIR / "stage1").glob("overlay_*_report.json"):
        stale.unlink(missing_ok=True)
    for stale in (BUILD_DIR / "stage1").glob("overlay_*_alignment.json"):
        stale.unlink(missing_ok=True)
    for stale in (BUILD_DIR / "stage1").glob("overlay_*_footnotes.json"):
        stale.unlink(missing_ok=True)

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
        primary = ((manifest.data.get("english") or {}).get("primary") or {})
        if primary:
            model = primary.get("model")
            if model == "perseus-play":
                from . import stage1_perseus_play_english

                eng_path, align_path, report_path = stage1_perseus_play_english.run(
                    manifest, spine
                )
                english = json.loads(eng_path.read_text(encoding="utf-8"))
                alignment = json.loads(align_path.read_text(encoding="utf-8"))
                report = json.loads(report_path.read_text(encoding="utf-8"))
                unmatched = [p for p in alignment["pairs"] if p["english"] is None]
                print(
                    f"  english chunks={len(english['chunks'])} "
                    f"({english['translation']}) unmatched={len(unmatched)} "
                    f"anchors={report['anchor_count']} snaps={report['snap_count']} "
                    f"unresolved={report['unresolved_mismatch_count']} "
                    f"covered={report['covered_by_count']}"
                )
            elif model == "turn-text":
                from . import stage1_turn_english

                eng_path, align_path, report_path = stage1_turn_english.run(
                    manifest, spine
                )
                english = json.loads(eng_path.read_text(encoding="utf-8"))
                alignment = json.loads(align_path.read_text(encoding="utf-8"))
                report = json.loads(report_path.read_text(encoding="utf-8"))
                unmatched = [p for p in alignment["pairs"] if p["english"] is None]
                print(
                    f"  english chunks={len(english['chunks'])} "
                    f"({english['translation']}) unmatched={len(unmatched)} "
                    f"paired={report['paired']} residual={report['residual_grouped']} "
                    f"head_unassigned={report['head_unassigned']} "
                    f"residual_unassigned={report['residual_unassigned']} "
                    f"ratio_outliers={report['length_ratio_outlier_count']} "
                    f"shift_cum={report['turn_shift_count']} "
                    f"new_drifts={report['turn_shift_new_drifts']} "
                    f"shift_rate={report['turn_shift_rate']:.3f} "
                    f"flagged={report['residual_flagged']} "
                    f"rate={report['pairing_rate']:.3f} "
                    f"seg_rate={report['segment_pairing_rate']:.3f}"
                )
            else:
                raise NotImplementedError(
                    f"play-line English model {model!r} is not supported"
                )
        else:
            for scratch in ("english_chunks.json", "alignment.json"):
                (BUILD_DIR / "stage1" / scratch).unlink(missing_ok=True)
        secondary = ((manifest.data.get("english") or {}).get("secondary") or {})
        if secondary:
            sec_model = secondary.get("model")
            if sec_model == "turn-text":
                from . import stage1_turn_english

                _sec_eng, _sec_align, sec_report_path = stage1_turn_english.run(
                    manifest, spine, slot="secondary"
                )
                sec_report = json.loads(sec_report_path.read_text(encoding="utf-8"))
                print(
                    f"  secondary chunks={sec_report['segments_with_chunk']} "
                    f"({sec_report['translation']}) unpaired={sec_report['greek_unpaired']} "
                    f"paired={sec_report['paired']} residual={sec_report['residual_grouped']} "
                    f"head_unassigned={sec_report['head_unassigned']} "
                    f"residual_unassigned={sec_report['residual_unassigned']} "
                    f"ratio_outliers={sec_report['length_ratio_outlier_count']} "
                    f"shift_cum={sec_report['turn_shift_count']} "
                    f"new_drifts={sec_report['turn_shift_new_drifts']} "
                    f"shift_rate={sec_report['turn_shift_rate']:.3f} "
                    f"flagged={sec_report['residual_flagged']} "
                    f"rate={sec_report['pairing_rate']:.3f} "
                    f"seg_rate={sec_report['segment_pairing_rate']:.3f}"
                )
            elif sec_model == "perseus-play":
                from . import stage1_perseus_play_english

                _sec_eng, _sec_align, sec_report_path = stage1_perseus_play_english.run(
                    manifest, spine, slot="secondary"
                )
                sec_report = json.loads(sec_report_path.read_text(encoding="utf-8"))
                print(
                    f"  secondary chunks={sec_report['segments_with_chunk']} "
                    f"({sec_report['translation']}) "
                    f"coverage={sec_report['coverage_ratio']:.3f} "
                    f"anchors={sec_report['anchor_count']} snaps={sec_report['snap_count']} "
                    f"unresolved={sec_report['unresolved_mismatch_count']} "
                    f"covered={sec_report['covered_by_count']}"
                )
            else:
                raise NotImplementedError(
                    f"play-line english.secondary model {sec_model!r} is not supported"
                )
        third = ((manifest.data.get("english") or {}).get("third") or {})
        if third:
            third_model = third.get("model")
            if third_model == "turn-text":
                from . import stage1_turn_english

                _third_eng, _third_align, third_report_path = stage1_turn_english.run(
                    manifest, spine, slot="third"
                )
                third_report = json.loads(third_report_path.read_text(encoding="utf-8"))
                print(
                    f"  third chunks={third_report['segments_with_chunk']} "
                    f"({third_report['translation']}) unpaired={third_report['greek_unpaired']} "
                    f"paired={third_report['paired']} residual={third_report['residual_grouped']} "
                    f"head_unassigned={third_report['head_unassigned']} "
                    f"residual_unassigned={third_report['residual_unassigned']} "
                    f"ratio_outliers={third_report['length_ratio_outlier_count']} "
                    f"shift_cum={third_report['turn_shift_count']} "
                    f"new_drifts={third_report['turn_shift_new_drifts']} "
                    f"shift_rate={third_report['turn_shift_rate']:.3f} "
                    f"flagged={third_report['residual_flagged']} "
                    f"rate={third_report['pairing_rate']:.3f} "
                    f"seg_rate={third_report['segment_pairing_rate']:.3f}"
                )
            else:
                raise NotImplementedError(
                    f"play-line english.third model {third_model!r} is not supported"
                )
        for overlay_entry in ((manifest.data.get("english") or {}).get("overlays") or []):
            ov_model = overlay_entry.get("model")
            if ov_model != "turn-text":
                raise NotImplementedError(
                    f"play-line english.overlays model {ov_model!r} is not supported"
                )
            from . import stage1_turn_english

            _ov_eng, _ov_align, ov_report_path = stage1_turn_english.run(
                manifest, spine, slot="overlay", overlay_entry=overlay_entry
            )
            ov_report = json.loads(ov_report_path.read_text(encoding="utf-8"))
            print(
                f"  overlay {overlay_entry.get('id')} "
                f"chunks={ov_report['segments_with_chunk']} "
                f"({ov_report['translation']}) unpaired={ov_report['greek_unpaired']} "
                f"paired={ov_report['paired']} residual={ov_report['residual_grouped']} "
                f"head_unassigned={ov_report['head_unassigned']} "
                f"residual_unassigned={ov_report['residual_unassigned']} "
                f"ratio_outliers={ov_report['length_ratio_outlier_count']} "
                f"shift_cum={ov_report['turn_shift_count']} "
                f"new_drifts={ov_report['turn_shift_new_drifts']} "
                f"shift_rate={ov_report['turn_shift_rate']:.3f} "
                f"flagged={ov_report['residual_flagged']} "
                f"rate={ov_report['pairing_rate']:.3f} "
                f"seg_rate={ov_report['segment_pairing_rate']:.3f}"
            )
        n_lines = sum(len(s["lines"]) for s in spine["segments"])
        n_speakers = sum(len(s.get("speakers", [])) for s in spine["segments"])
        print(f"stage1 ({'greek+english' if primary else 'greek-only'}, play-line): "
              f"segments={len(spine['segments'])} "
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
        f"{name}={'warn' if c.get('warn') else ('ok' if c['ok'] else 'FAIL')}"
        for name, c in report["checks"].items()
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
    parser.add_argument("--edition", help="Greek edition id")
    args = parser.parse_args(argv)
    manifest = Manifest.for_work(args.work, public=args.public)
    if args.edition:
        manifest = manifest.for_edition(args.edition)
    if args.public:
        print(f"manifest: {manifest.path.relative_to(manifest.path.parents[1])}")
    if args.stage == "all":
        for fn in _STAGES.values():
            fn(manifest)
    else:
        _STAGES[args.stage](manifest)
    if args.edition and args.stage in {"all", "stage7"}:
        from .stage7_emit import assemble_edition
        assemble_edition(manifest)


if __name__ == "__main__":
    sys.exit(main())
