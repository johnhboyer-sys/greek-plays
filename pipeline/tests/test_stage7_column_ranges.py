"""column_line_ranges (stage7_emit.py, columns.json): a dk verse fragment's
role='context' lines carry a non-citable NEGATIVE synthetic n
(stage1_greek._parse_fragments) that must never widen a column's citable
line-number range -- a citation jump / nearest-line snap must never be able
to land on a non-citable context block (Sol review nit (a))."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

from drama_pipeline.stage7_emit import column_line_ranges


def test_negative_context_line_n_excluded_from_column_range():
    spine = {
        "segments": [
            {"id": "1:B8", "book": 1, "column": "B8", "lines": [
                {"n": -1, "text": "context block", "role": "context"},
                {"n": 1, "text": "text line one", "role": "text"},
                {"n": 2, "text": "text line two", "role": "text"},
            ]},
        ],
    }
    out = column_line_ranges(spine)
    assert out == {"B8": [{"book": 1, "lo": 1, "hi": 2}]}


def test_column_with_only_negative_context_lines_emits_no_range():
    # A fragment declared in citation.unmarked_columns (all context, no real
    # citable verse at all) must not synthesize a bogus range from its
    # negative synthetic n's.
    spine = {
        "segments": [
            {"id": "1:B22", "book": 1, "column": "B22", "lines": [
                {"n": -1, "text": "context only", "role": "context"},
            ]},
        ],
    }
    out = column_line_ranges(spine)
    assert out == {}


def test_ordinary_non_dk_scheme_range_unaffected():
    spine = {
        "segments": [
            {"id": "1:1097a", "book": 1, "column": "1097a", "lines": [
                {"n": 1, "text": "alpha"},
                {"n": 15, "text": "omega"},
            ]},
        ],
    }
    out = column_line_ranges(spine)
    assert out == {"1097a": [{"book": 1, "lo": 1, "hi": 15}]}
