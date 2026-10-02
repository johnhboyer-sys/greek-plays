"""Aristophanes: Mika, in a comic old woman's mask, holding out a bowl, from
the Würzburg krater H 5697 (Apulian, Schiller Painter, c. 370 BCE), which
shows the mock sacrifice in Women at the Thesmophoria: Mnesilochus, on the
altar, threatens her "baby", a wineskin, and she asks for a bowl to catch
its blood (754-755 in the repo's Hall-Geldart text, where she is the First
Woman, called Mikka at 760). Photo: ArchaiOptix, CC BY-SA 4.0:
https://commons.wikimedia.org/wiki/File:Schiller_Painter_-_RVAp_4-4a_-_Thesmophoriazousai_as_phlyax_play_-_youths_-_W%C3%BCrzburg_MvWM_H_5697_-_04.jpg

Red-figure photo -> drawing, as for Medea (see medea.py): the figure is the
light clay; inner lines are the dark relief lines inside it. Two cuts: the
blade of Mnesilochus' knife, which touches the bowl's rim, is removed along
the blade's own edge. The bowl's foot is a separate shape and gets its own seed.
Her feet need no cut: a black line divides them from the border band.

    python3 docs/redesign/drawings/tools/mika.py path/to/photo.jpg
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "aristophanes-mika.svg"
BOX = (218, 1273, 2329, 3603)     # photo crop around her
SEEDS = [(600, 1200), (1000, 1370)]  # her robe; the bowl's foot (crop x, y)
KNIFE_X = 1398                    # blade's left edge where it meets the rim
KNIFE_Y = (540, 1260)


def main(src: str) -> None:
    a = np.asarray(Image.open(src).convert("RGB").crop(BOX), dtype=np.float32)
    L = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    light = L > 90
    light[KNIFE_Y[0]:KNIFE_Y[1], KNIFE_X:] = False
    lab, _ = ndi.label(light, structure=np.ones((3, 3)))
    fig = np.isin(lab, [lab[y, x] for x, y in SEEDS])

    sil = ndi.binary_closing(fig, structure=morphology.disk(5))
    holes = ndi.binary_fill_holes(sil) & ~sil
    hl, _ = ndi.label(holes)
    hs = np.bincount(hl.ravel())
    hs[0] = 0
    sil |= np.isin(hl, np.nonzero((hs > 0) & (hs < 3000))[0])
    sil = ndi.gaussian_filter(sil.astype(float), 2.5) > 0.5

    # inner lines by local contrast; hysteresis keeps each fold line whole
    inner = lw.ink_lines(L, size=21, low=12, high=30, sigma=1.2)
    inner &= ndi.binary_erosion(sil, structure=morphology.disk(7))
    inner = morphology.remove_small_objects(inner, max_size=120)
    edge = sil & ~ndi.binary_erosion(sil, structure=morphology.disk(6))
    info = lw.trace_svg(
        edge | inner, OUT, body=sil,
        title="Mika, in a comic old woman's mask, holding out a bowl",
        desc="Line drawing after the Apulian red-figure krater Würzburg H 5697, c. 370 BCE, "
             "a scene from Aristophanes' Women at the Thesmophoria; traced from a photograph by "
             "ArchaiOptix (CC BY-SA 4.0), changed. This drawing is CC BY-SA 4.0.")
    print(OUT, info)


if __name__ == "__main__":
    main(sys.argv[1])
