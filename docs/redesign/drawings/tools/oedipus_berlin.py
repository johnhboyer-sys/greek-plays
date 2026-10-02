"""Sophocles: Oedipus, standing with a spear before the Sphinx, from the Attic
red-figure pelike by the Achilles Painter, c. 445-440 BCE, Berlin
Antikensammlung F 2355 (ARV² 990.49). Photo: Gary Todd, released CC0 on
Wikimedia Commons:
https://commons.wikimedia.org/wiki/File:Attic_Red-figure_Ceramic_Pelike_Oedipus_in_front_of_the_Sphinx;_painted_by_Achilles_Painter,_c._445-440_BC_(28737512175).jpg

Red-figure photo -> drawing, as for Medea (see medea.py), except that this
glaze is shiny: its reflections are as bright as the clay, so the figure is
found by colour (red minus blue) rather than brightness. His dark hair is
outlined by hand (HAIR) and drawn as an outline. His feet and the
butt of his spear rest on the meander band; the cut follows the band's top
edge. The Sphinx, on her rock to the left, is a separate figure and is left out.

    python3 docs/redesign/drawings/tools/oedipus_berlin.py path/to/photo.jpg
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "sophocles-oedipus.svg"
BOX = (1600, 1760, 2720, 3960)   # photo crop around him
SEED = (700, 900)                # a point on his cloak, crop coords (x, y)
BAND_Y0, BAND_SLOPE = 2082, -0.057  # top edge of the meander band: y = Y0 + slope * x
# His hair is glaze-dark like the ground, so colour alone drops it and leaves
# the head bald. This outline follows the painter's two reserved arcs over
# the head and the curls on the forehead (crop coords); inside it, every
# pixel that is not clay is hair. The hair is drawn as its outline, not
# filled: a solid fill turns white in the dark theme and reads as white hair.
HAIR = [(507, 215), (525, 190), (545, 172), (575, 159), (615, 151), (645, 155), (670, 165), (687, 176),
        (705, 187), (725, 210), (740, 230), (747, 250), (752, 275), (750, 288), (730, 290), (705, 290),
        (680, 287), (655, 288), (645, 304), (630, 305), (610, 290), (602, 275), (600, 265), (580, 262),
        (555, 261), (535, 255), (520, 240), (510, 220)]


def main(src: str) -> None:
    a = np.asarray(Image.open(src).convert("RGB").crop(BOX), dtype=np.float32)
    clay = (a[..., 0] - a[..., 2]) > 70
    H, W = clay.shape
    Y, X = np.mgrid[0:H, 0:W]
    clay &= Y < BAND_Y0 + BAND_SLOPE * X
    lab, _ = ndi.label(clay, structure=np.ones((3, 3)))
    fig = lab == lab[SEED[1], SEED[0]]

    sil = ndi.binary_closing(fig, structure=morphology.disk(4))
    holes = ndi.binary_fill_holes(sil) & ~sil
    hl, _ = ndi.label(holes)
    hs = np.bincount(hl.ravel())
    hs[0] = 0
    sil |= np.isin(hl, np.nonzero((hs > 0) & (hs < 3000))[0])
    sil = ndi.gaussian_filter(sil.astype(float), 2.0) > 0.5

    L = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    Ls = ndi.gaussian_filter(L, 1.0)
    tophat = ndi.grey_closing(Ls, footprint=morphology.disk(8)) - Ls
    inner = (tophat > 35) & ndi.binary_erosion(sil, structure=morphology.disk(6))
    inner = morphology.remove_small_objects(inner, max_size=80)
    edge = sil & ~ndi.binary_erosion(sil, structure=morphology.disk(5))
    hair = lw.polygon_mask(clay.shape, np.array(HAIR, float)) & ~ndi.binary_dilation(clay, iterations=2)
    hair = ndi.binary_opening(hair, structure=morphology.disk(2))
    hair = hair & ~ndi.binary_erosion(hair, structure=morphology.disk(5))
    info = lw.trace_svg(
        edge | inner | hair, OUT,
        title="Oedipus, a young traveller in cloak and short tunic, standing with a spear",
        desc="Line drawing after the Attic red-figure pelike by the Achilles Painter, c. 445-440 BCE, "
             "Berlin F 2355, where he faces the Sphinx; traced from Gary Todd's CC0 photograph.")
    print(OUT, info)


if __name__ == "__main__":
    main(sys.argv[1])
