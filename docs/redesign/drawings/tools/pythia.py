"""Aeschylus: the Pythia fleeing the temple at Delphi (Eumenides 34 ff.),
from Carl Bötticher's drawing of the Black Fury Painter's krater (Orestes at
Delphi), Der Omphalos des Zeus zu Delphi (Berlin, 1859), plate fig. 1, as
scanned by Heidelberg University Library (Public Domain Mark):
https://digi.ub.uni-heidelberg.de/diglitData/image/bwpr1859/4/010a.jpg
(The Commons copy of this plate is a blurred 1.5x upscale of the same scan.)

Engraved plate -> drawing:
  1. ink = dark lines on the paper, with the paper tone divided out;
  2. the Pythia is cut out along her own lines with a least-cost path
     through hand-placed points (Apollo, his N-patterned cloak, the laver
     behind her and the black Fury above are left out; both ends of her
     starred shawl, the black folds included, are kept; Apollo's raised back
     foot, which lies across her hem, is erased and the hem left blank there);
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
# raised right hand. The guided path snaps them onto her own lines; check the
# result with the QA overlay (second argument).
OUTLINE = [
    # her raised right hand, then straight across the blank gap from the thumb to the
    # locks beside her face (a lasso path would detour along her arm and lose them)
    (483, 429), (494, 423), (505, 423), (515, 430), (517, 450), (521, 459), lw.STRAIGHT, (531, 457),
    (533, 440), (540, 428), (565, 420), (575, 414), (588, 416), (596, 423), (600, 428), (618, 438), (630, 446),
    (634, 451), lw.STRAIGHT,
    # over the curls on the right of her head, straight across to her raised left hand, up its index finger
    (641, 448), (642, 433), (645, 423), (657, 418), (677, 421), (682, 445), (675, 465), (688, 483), (698, 498),
    # out along the upper end of her shawl to its black fringe, back along its lower edge, then out
    # along the lower end to its black folds (Apollo's cloak is the one with the N pattern and leaf border)
    (720, 496), (760, 498), (785, 496), (803, 506), (798, 521), (790, 527), (765, 530), (740, 530), (715, 530),
    (702, 535), (712, 542), (735, 548), (752, 553), (775, 570), (780, 582), (768, 594), (752, 612), (742, 617),
    (728, 609), (712, 600), (705, 608),
    # down the front of Apollo's thigh and shin to his boot
    (724, 634), (742, 656), (743, 690), (744, 725), (743, 760), (742, 777),
    # under his boot, round his raised back foot (erased below), then her trailing foot
    (772, 786), (773, 801), (766, 815), (766, 840), (764, 864), (751, 874), (737, 860), (733, 845),
    # her hem: straight along the blank paper under the lowest ruffles, then round the
    # sole of her front foot, back up her left side, and round her raised right arm
    (715, 841), (675, 838), (640, 852), lw.STRAIGHT, (600, 862), lw.STRAIGHT, (560, 865), (553, 862),
    (520, 865), (495, 864),
    (487, 854), (497, 844), (510, 831), (505, 801), (505, 761), (515, 731), (527, 701), (535, 671), (540, 631),
    (537, 590), (527, 560), (510, 551), (494, 546), (476, 540), (463, 530), (459, 515), (461, 498), (467, 480),
    (479, 460),
]
# Apollo's raised back foot lies across her hem; its lines are erased and the
# hem is left blank there (nothing is drawn in).
APOLLO_FOOT = [(696, 782), (740, 776), (772, 782), (775, 806), (764, 816), (735, 814), (700, 806), (692, 795)]
# The toe of his sandal reaches past her hem's right edge: no body fill there.
APOLLO_TOE = [(760, 774), (782, 774), (782, 820), (760, 820)]
X0, Y0, X1, Y1 = 440, 400, 830, 890  # working crop of the page around her
F = 4                                 # resample factor before thresholding


def main(src: str) -> None:
    g = np.asarray(Image.open(src).convert("L"), dtype=np.float32)
    ink = lw.ink_from_scan(g, bg_sigma=20, k=0.78)
    soft = ndi.gaussian_filter(ink.astype(float), 1.5)
    cost = 1 + 30 * (1 - np.clip(soft * 2, 0, 1))
    path, on_straight = lw.livewire(cost, OUTLINE, closed=True, flags=True)
    keep, inner, wall = lw.cut_masks(ink.shape, path, on_straight)
    foot = lw.polygon_mask(ink.shape, np.array(APOLLO_FOOT, float))

    crop = Image.fromarray(g[Y0:Y1, X0:X1].astype(np.uint8))
    g3 = np.asarray(crop.resize((crop.width * F, crop.height * F), Image.LANCZOS), dtype=np.float32)
    g3 = ndi.gaussian_filter(g3, 1.5)  # paper grain
    ink3 = lw.ink_from_scan(g3, bg_sigma=60, k=0.80)
    up = lambda m: np.asarray(Image.fromarray(m[Y0:Y1, X0:X1].astype(np.uint8) * 255)
                              .resize(((X1 - X0) * F, (Y1 - Y0) * F), Image.NEAREST)) > 0
    keep3, inner3, wall3, foot3 = up(keep), up(inner), ndi.binary_dilation(up(wall), iterations=2), up(foot)
    fig = morphology.remove_small_objects(ink3 & ndi.binary_dilation(keep3 & ~foot3, iterations=2), max_size=30)
    # her hem behind Apollo's erased foot is part of her: the body fills it
    body = lw.body_from_cut(fig, inner3, wall3, close=6)
    body &= ~up(lw.polygon_mask(ink.shape, np.array(APOLLO_TOE, float)))
    info = lw.trace_svg(
        fig, OUT, body=body,
        title="The Pythia, Apollo's priestess, fleeing in terror with her hands raised",
        desc="Line drawing after Carl Bötticher's 1859 drawing of an Apulian red-figure krater "
             "showing Orestes at Delphi (Naples); cut out and retraced.")
    print(OUT, info)
    if len(sys.argv) > 2:  # optional: the drawing over its source, for checking
        lw.qa_overlay(g3, OUT, info["box"], Path(sys.argv[2]))


if __name__ == "__main__":
    main(sys.argv[1])
