"""Aeschylus: the Pythia fleeing the temple at Delphi (Eumenides 34 ff.),
from Carl Bötticher's drawing of the Black Fury Painter's krater (Orestes at
Delphi), Der Omphalos des Zeus zu Delphi (Berlin, 1859), plate fig. 1, as
scanned by Heidelberg University Library (Public Domain Mark):
https://digi.ub.uni-heidelberg.de/diglitData/image/bwpr1859/4/010a.jpg
(The Commons copy of this plate is a blurred 1.5x upscale of the same scan.)

Engraved plate -> drawing:
  1. ink = dark lines on the paper, with the paper tone divided out;
  2. the Pythia is cut out along her own lines with a least-cost path
     through hand-placed points (Apollo's cloak, leg and boot, the laver
     behind her and the black Fury above are left out; his raised back foot,
     which lies across her hem, is erased and the hem left blank there);
  3. she is about 450px tall in the scan, so the crop is resampled 4x
     before thresholding to keep the traced curves smooth; line weight and
     tracing as for every drawing (linework).

    python3 docs/redesign/drawings/tools/pythia.py path/to/plate.jpg
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "aeschylus-pythia.svg"

# Points on her outline in px of the Heidelberg page scan, clockwise from her
# raised left hand. The guided path snaps them onto her own lines.
OUTLINE = [
    (483, 429), (494, 423), (505, 423), (515, 430), (517, 454), (537, 438), (565, 420), (600, 428), (622, 440),
    (640, 448), (645, 425), (657, 418), (677, 421), (682, 445), (675, 465), (688, 483), (698, 498), (720, 496),
    (760, 498), (785, 496), (803, 506), (798, 521), (760, 518), (730, 521), (708, 533),
    # down her right side: the edge of Apollo's black cloth, his thigh, then his shin and boot
    (698, 557), (701, 585), (705, 608), (724, 634), (742, 656), (743, 690), (744, 725), (743, 760), (742, 777),
    # under his boot, round his raised back foot (erased below), then her trailing foot
    (772, 786), (773, 801), (766, 815), (766, 840), (764, 864), (751, 874), (737, 860), (733, 845),
    (715, 841), (675, 836), (635, 826), (600, 831), (560, 841), (550, 844), (535, 851),
    (520, 864), (495, 864), (487, 854), (497, 844), (510, 831), (505, 801), (505, 761), (515, 731), (527, 701),
    (535, 671), (540, 631), (537, 590), (527, 555), (522, 530), (500, 521), (472, 513), (460, 498), (466, 480),
    (479, 460),
]
# Apollo's raised back foot lies across her hem; its lines are erased and the
# hem is left blank there (nothing is drawn in).
APOLLO_FOOT = [(696, 782), (740, 776), (772, 782), (775, 806), (764, 816), (735, 814), (700, 806), (692, 795)]
X0, Y0, X1, Y1 = 440, 400, 830, 890  # working crop of the page around her
F = 4                                 # resample factor before thresholding


def main(src: str) -> None:
    g = np.asarray(Image.open(src).convert("L"), dtype=np.float32)
    ink = lw.ink_from_scan(g, bg_sigma=20, k=0.78)
    pts = OUTLINE
    soft = ndi.gaussian_filter(ink.astype(float), 1.5)
    cost = 1 + 30 * (1 - np.clip(soft * 2, 0, 1))
    path = lw.livewire(cost, pts, closed=True)
    ring = np.zeros_like(ink)
    ring[(path[:, 1] - 0.5).astype(int), (path[:, 0] - 0.5).astype(int)] = True
    keep = lw.polygon_mask(ink.shape, path) | ndi.binary_dilation(ring, iterations=2)
    keep &= ~lw.polygon_mask(ink.shape, np.array(APOLLO_FOOT, float))

    crop = Image.fromarray(g[Y0:Y1, X0:X1].astype(np.uint8))
    g3 = np.asarray(crop.resize((crop.width * F, crop.height * F), Image.LANCZOS), dtype=np.float32)
    g3 = ndi.gaussian_filter(g3, 1.5)  # paper grain
    ink3 = lw.ink_from_scan(g3, bg_sigma=60, k=0.80)
    m = Image.fromarray(keep[Y0:Y1, X0:X1].astype(np.uint8) * 255)
    keep3 = np.asarray(m.resize((m.width * F, m.height * F), Image.NEAREST)) > 0
    fig = morphology.remove_small_objects(ink3 & ndi.binary_dilation(keep3, iterations=2), max_size=30)
    info = lw.trace_svg(
        fig, OUT,
        title="The Pythia, Apollo's priestess, fleeing in terror with her hands raised",
        desc="Line drawing after Carl Bötticher's 1859 drawing of an Apulian red-figure krater "
             "showing Orestes at Delphi (Naples); cut out and retraced.")
    print(OUT, info)
    if len(sys.argv) > 2:  # optional: an overlay of the cut, for checking
        rgb = np.stack([g] * 3, -1).astype(np.uint8)
        rgb[keep & ink] = (200, 0, 0)
        rgb[ring] = (0, 160, 0)
        Image.fromarray(rgb[Y0:Y1, X0:X1]).resize(((X1 - X0) * 2, (Y1 - Y0) * 2)).save(sys.argv[2])


if __name__ == "__main__":
    main(sys.argv[1])
