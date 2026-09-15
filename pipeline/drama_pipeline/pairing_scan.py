"""Corpus-wide turn-pairing scan: ``python -m drama_pipeline.pairing_scan --out <path>``.

Rebuilds every manifest (``all --work <id>``) and collects every turn-text
slot's stage1 report into one TSV, one row per (play, slot). Columns are the
2026-09-14 scan's columns (turn_shift_count, pairing_rate, and the rest of the
turn-text report's own numbers) plus the columns the turn-pairing design study
(build/review/turn-pairing-design-2026-09-15.md, section 7.B) adds for the DP
aligner: low_confidence, bare_run_events, derived_covered, shift_packed,
shift_unpacked. A report that predates those fields (the old LCS pairer, or
any report field not present) writes ``NA`` rather than a false zero.

This script itself does not touch the pairing algorithm; it is the instrument
used to take the pre-change baseline and, later, to score a change against it.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .audit import columns_for, load_report
from .config import BUILD_DIR, REPO_ROOT, Manifest

MANIFESTS_DIR = REPO_ROOT / "manifests"

# The 2026-09-14 scan's columns, in order, read straight off the turn-text
# report; then the columns the DP design adds (section 7.B).
_REPORT_COLUMNS = [
    "greek_events",
    "greek_events_named",
    "paired",
    "pairing_rate",
    "segment_pairing_rate",
    "turn_shift_count",
    "turn_shift_rate",
    "turn_shift_new_drifts",
    "turn_shift_rate_cumulative",
    "length_ratio_outlier_count",
    "residual_grouped",
    "residual_flagged",
    "residual_unassigned",
    "head_unassigned",
    "greek_unpaired",
    "crossed_pairs",
    "pinned_pairs",
]
_NEW_COLUMNS = [
    "low_confidence_rate",
    "low_confidence_pairs",
    "bare_run_events",
    "derived_covered_count",
    "turn_shift_count_packed",
    "turn_shift_count_unpacked",
    "band_widened",
    "align_cost",
]
_HEADER = ["play", "slot", "translation_id", *_REPORT_COLUMNS, *_NEW_COLUMNS, "play_wall_clock_s"]


def _all_work_ids() -> list[str]:
    ids = []
    for path in sorted(MANIFESTS_DIR.glob("*.yaml")):
        if path.name == "authors.yaml" or path.name.endswith("-public.yaml"):
            continue
        ids.append(path.stem)
    return ids


def _fmt(value) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def _bare_run_events(report: dict) -> int | None:
    runs = report.get("greek_skip_runs")
    if runs is None:
        return None
    return sum(int(r.get("events") or 0) for r in runs if not r.get("covered"))


def scan(work_ids: list[str] | None = None) -> list[list[str]]:
    from . import __main__ as cli

    rows: list[list[str]] = []
    failures: list[tuple[str, str]] = []
    for work_id in work_ids or _all_work_ids():
        start = time.time()
        try:
            cli.main(["all", "--work", work_id])
        except SystemExit as exc:
            # stage2 can legitimately fail a play (e.g. a new undeclared
            # bare-run gate catching a real hole a manifest has not yet
            # declared) -- stage1's reports are already on disk by then, so
            # the scan still collects this play's numbers and reports the
            # gate failure separately rather than aborting the whole corpus.
            failures.append((work_id, str(exc)))
            print(f"  {work_id}: gate failed -- {exc}")
        elapsed = time.time() - start
        manifest = Manifest.for_work(work_id)
        stage1_dir = BUILD_DIR / "stage1"
        for col in columns_for(manifest):
            if col.get("model") != "turn-text":
                continue
            report = load_report(stage1_dir, col, work_id)
            row = [work_id, col["slot"], col.get("id") or ""]
            if report is None:
                row.extend(["NA"] * len(_REPORT_COLUMNS))
                row.extend(["NA"] * len(_NEW_COLUMNS))
            else:
                row.extend(_fmt(report.get(key)) for key in _REPORT_COLUMNS)
                row.append(_fmt(report.get("low_confidence_rate")))
                row.append(_fmt(report.get("low_confidence_pairs")))
                row.append(_fmt(_bare_run_events(report)))
                row.append(_fmt(report.get("derived_covered_count")))
                row.append(_fmt(report.get("turn_shift_count_packed")))
                row.append(_fmt(report.get("turn_shift_count_unpacked")))
                row.append(_fmt(report.get("band_widened")))
                row.append(_fmt(report.get("align_cost")))
            row.append(f"{elapsed:.3f}")
            rows.append(row)
    if failures:
        print(f"{len(failures)} play(s) failed a pipeline gate: "
              f"{', '.join(w for w, _ in failures)}")
    return rows


def write_tsv(rows: list[list[str]], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        fh.write("\t".join(_HEADER) + "\n")
        for row in rows:
            fh.write("\t".join(row) + "\n")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="drama_pipeline.pairing_scan")
    parser.add_argument("--out", required=True, help="TSV output path")
    parser.add_argument("--work", action="append", help="limit to one work (repeatable)")
    args = parser.parse_args(argv)
    rows = scan(args.work)
    write_tsv(rows, Path(args.out))
    print(f"wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main(sys.argv[1:])
