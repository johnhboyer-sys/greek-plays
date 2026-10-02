"""Medea in her serpent chariot, from Cleveland Museum of Art 1991.1 (CC0).

Source: the museum's detail view 1991.1_alt3_print.jpg (2753 x 3400),
https://openaccess-cdn.clevelandart.org/1991.1/1991.1_alt3_print.jpg

Red-figure photo -> line drawing:
  1. the figure is the light clay and added colour against the black glaze
     (luminance > 75);
  2. the painted disk's inner border touches the serpent tail and a wheel,
     so the border is cut away along its own curve (outermost light pixel
     per degree around the disk's centre);
  3. outline = the figure's silhouette edge; inner lines = dark relief and
     dilute lines inside it (black top-hat on luminance);
  4. lines are set to the house weight and traced with potrace.

    python3 docs/redesign/drawings/tools/medea.py path/to/1991.1_alt3_print.jpg
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "medea.svg"
X0, Y0, X1, Y1 = 560, 820, 2330, 2680          # crop around the disk
CX, CY = 880.0, 940.0                          # disk centre in the crop
GOAD = [(500, 440)]                            # seed on the detached goad and hand
# Her right sleeve, between the hand on the goad and her body, is covered in a
# dense dark net pattern, so brightness drops it and the hand floats. Its
# outline, read off the photo (crop coords), puts it back.
SLEEVE = [(828, 578), (890, 592), (960, 610), (985, 625), (988, 715), (910, 690), (860, 665), (832, 648)]


def main(src: str) -> None:
    a = np.asarray(Image.open(src).convert("RGB"), dtype=np.float32)[Y0:Y1, X0:X1]
    L = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    H, W = L.shape
    light = L > 75
    lab, _ = ndi.label(light, structure=np.ones((3, 3)))
    main_c = lab == np.argmax(np.bincount(lab.ravel())[1:]) + 1

    # cut the disk border: per 0.25 degree, the outermost light pixel is the border
    Y, X = np.mgrid[0:H, 0:W].astype(float)
    R = np.hypot(X - CX, Y - CY)
    deg = np.degrees(np.arctan2(Y - CY, X - CX))
    nb = 1440
    B = np.floor((deg + 180) / 360 * nb).astype(int) % nb
    rmax = np.full(nb, -1.0)
    idx = np.nonzero(main_c.ravel())[0]
    np.maximum.at(rmax, B.ravel()[idx], R.ravel()[idx])
    rmed = ndi.median_filter(rmax, size=9, mode="wrap")
    centre = (np.arange(nb) + 0.5) / nb * 360 - 180
    on_border = (centre > -150) & (centre < 66)  # where the border joins the figure's component
    band = main_c & on_border[B] & (R > rmed[B] - 13)
    lab2, _ = ndi.label(main_c & ~band, structure=np.ones((3, 3)))
    sizes = np.bincount(lab2.ravel())
    sizes[0] = 0
    grp = lab2 == np.argmax(sizes)
    for x, y in GOAD:
        grp |= lab == lab[y, x]
    grp |= lw.polygon_mask(grp.shape, np.array(SLEEVE, float))

    # silhouette: close the thin dark lines, fill only small holes
    sil = ndi.binary_closing(grp, structure=morphology.disk(4))
    holes = ndi.binary_fill_holes(sil) & ~sil
    hl, _ = ndi.label(holes)
    hs = np.bincount(hl.ravel())
    hs[0] = 0
    sil |= np.isin(hl, np.nonzero((hs > 0) & (hs < 1500))[0])
    lab3, _ = ndi.label(sil, structure=np.ones((3, 3)))
    s3 = np.bincount(lab3.ravel())
    s3[0] = 0
    sil = np.isin(lab3, np.nonzero(s3 > 200)[0])
    sil = ndi.gaussian_filter(sil.astype(float), 2.0) > 0.5

    # inner lines: dark detail on the clay
    Ls = ndi.gaussian_filter(L, 0.8)
    tophat = ndi.grey_closing(Ls, footprint=morphology.disk(7)) - Ls
    inner = (tophat > 40) & ndi.binary_erosion(sil, structure=morphology.disk(5))
    inner = morphology.remove_small_objects(inner, max_size=70)
    edge = sil & ~ndi.binary_erosion(sil, structure=morphology.disk(4))
    ink = edge | inner
    info = lw.trace_svg(
        ink, OUT,
        title="Medea in a chariot drawn by two serpents",
        desc="Line drawing after the Lucanian calyx-krater near the Policoro Painter, "
             "c. 400 BCE, Cleveland Museum of Art 1991.1 (CC0); traced from the museum's photograph.")
    print(OUT, info)


if __name__ == "__main__":
    main(sys.argv[1])
