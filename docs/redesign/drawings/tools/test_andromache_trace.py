"""Check for andromache.apply_trace: a trace drawn with a fine pen keeps its diagonal strokes.
A stroke 0.89 plate px wide (John's pen on the corpse's other hand), laid diagonally across clay,
must come through whole: once, the gaps' skeleton ran along such a stroke and the channels kept
open between close strokes cut it into dashes.

    python3 docs/redesign/drawings/tools/test_andromache_trace.py
"""
import sys
from pathlib import Path

import numpy as np
from skimage import draw

sys.path.insert(0, str(Path(__file__).parent))
import andromache as A  # noqa: E402

BOX = (2710, 1870, 2770, 1930)               # plate px, near the drawing's corner (X0, Y0)
STROKE = [(2716, 1876), (2764, 1924)]         # a diagonal across the box


def main() -> None:
    shape = ((BOX[3] - A.Y0 + 10) * A.UP, (BOX[2] - A.X0 + 10) * A.UP)
    fig = np.ones(shape, bool)
    empty = np.zeros(shape, bool)
    part = {'box': list(BOX), 'pen': 0.89, 'lines': [STROKE], 'solids': []}
    _, his, _, _ = A.apply_trace(part, empty.copy(), empty, fig, np.full(shape, 180.0, np.float32), empty, 5.0)
    (xa, ya), (xb, yb) = A.up(STROKE)
    rr, cc = draw.line(int(round(ya)), int(round(xa)), int(round(yb)), int(round(xb)))
    drawn = his[rr, cc].mean()
    print(f"a diagonal stroke at pen 0.89 plate px: {drawn:.0%} of it drawn ({len(rr)} px examined)")
    assert len(rr) > 50, "the stroke is too short: the check examined nothing"
    assert drawn > 0.95, "a fine diagonal stroke was cut into dashes"
    print("ok")


if __name__ == "__main__":
    main()
