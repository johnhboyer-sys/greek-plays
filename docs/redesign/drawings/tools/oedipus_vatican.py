"""ALTERNATE (not in the frieze): Oedipus and the Sphinx, from Juan José Moral's 2009 vector
redrawing of the Oedipus Painter's cup, Vatican 16541 (released into the
public domain on Wikimedia Commons):
https://commons.wikimedia.org/wiki/File:Oidipous_sphinx_MGEt_16541_reconstitution.svg

The redrawing is flat clay colour on black with black lines, so it goes
through the red-figure route (see medea.py) at 4000px: the tondo's borders,
the inscription, the palmette and the cup's ground strip are left out; the
group stands on the bottom of the column base.

    rsvg-convert -w 4000 -b '#000000' in.svg -o recon4000.png
    python3 docs/redesign/drawings/tools/oedipus_vatican.py recon4000.png
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "alternates" / "sophocles-oedipus-sphinx-vatican.svg"
CENTRE, RADIUS = (2000, 1980), 1660        # inside the tondo's inner ring
PALMETTE = (2600, 2690)                    # (x, y) on the palmette ornament
SEEDS = [(720, 1520), (2400, 1200), (2250, 2700)]  # Oedipus, Sphinx, column
BASE_X = 2250                              # a column through the base block


def main(src: str) -> None:
    a = np.asarray(Image.open(src).convert("RGB"), dtype=np.float32)
    L = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    H, W = L.shape
    light = L > 70
    lab, _ = ndi.label(light, structure=np.ones((3, 3)))
    Y, X = np.mgrid[0:H, 0:W]
    inside = np.hypot(X - CENTRE[0], Y - CENTRE[1]) < RADIUS
    light2 = light & inside & (lab != lab[PALMETTE[1], PALMETTE[0]])
    closed = ndi.binary_closing(light2, structure=morphology.disk(9))
    lab2, _ = ndi.label(closed, structure=np.ones((3, 3)))
    sil = np.isin(lab2, [lab2[y, x] for x, y in SEEDS])
    holes = ndi.binary_fill_holes(sil) & ~sil
    hl, _ = ndi.label(holes)
    hs = np.bincount(hl.ravel())
    hs[0] = 0
    sil |= np.isin(hl, np.nonzero((hs > 0) & (hs < 3000))[0])
    # the cup's own ground strip goes; the group stands on the base's bottom edge
    base_rows = np.nonzero(lab[:, BASE_X] == lab[3400, BASE_X])[0]
    sil[base_rows.max() + 1:, :] = False

    Ls = ndi.gaussian_filter(L, 1.0)
    tophat = ndi.grey_closing(Ls, footprint=morphology.disk(9)) - Ls
    inner = (tophat > 40) & ndi.binary_erosion(sil, structure=morphology.disk(6))
    inner = morphology.remove_small_objects(inner, max_size=60)
    edge = sil & ~ndi.binary_erosion(sil, structure=morphology.disk(6))
    info = lw.trace_svg(
        edge | inner, OUT, body=sil,
        title="Oedipus seated before the Sphinx, who sits on a column",
        desc="Line drawing after Juan José Moral's public-domain redrawing (2009) of the "
             "Attic red-figure cup by the Oedipus Painter, c. 470 BCE, Vatican 16541.")
    print(OUT, info)


if __name__ == "__main__":
    main(sys.argv[1])
