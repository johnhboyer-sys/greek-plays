"""Iphigenia at Aulis, Met 31.11.2 (CC0): the attempt that FAILED.

The Boeotian relief bowl is low and worn, and the same colour as its ground.
Automatic line finding (XDoG, Canny at several scales, local-contrast
thresholds) gives a field of specks with no figure in it. What survives here
is a hand outline of the letter scene in view LC-31_11_2b (the old servant
holds out Agamemnon's letter; Menelaus, with his staff, reaches for it),
read off a local-contrast copy of the photo, plus the photo's darkest relief
shadows inside the outlines. It is kept to show the failure, not to be used.

    python3 docs/redesign/drawings/tools/iphigenia.py path/to/LC-31_11_2b.jpg
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import draw, exposure, morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "rejected" / "iphigenia-at-aulis.svg"

# Outlines in px of the photo at half size, read off the local-contrast copy.
OLD_MAN = [(600, 712), (640, 722), (657, 750), (657, 777), (660, 780), (690, 792), (720, 786), (752, 779),
           (765, 792), (757, 810), (720, 830), (690, 865), (720, 872), (760, 877), (770, 890), (760, 902),
           (690, 910), (700, 930), (720, 975), (740, 1020), (755, 1050), (767, 1072), (760, 1082),
           (725, 1080), (700, 1060), (680, 1040), (640, 985), (615, 1000), (590, 1040), (570, 1075),
           (545, 1090), (510, 1090), (502, 1077), (515, 1045), (530, 1010), (507, 940), (512, 890),
           (530, 840), (547, 805), (550, 790), (555, 755), (562, 725)]
MENELAUS = [(1035, 650), (1067, 660), (1079, 690), (1077, 725), (1070, 749), (1080, 760), (1095, 780),
            (1105, 820), (1112, 880), (1120, 960), (1115, 1010), (1120, 1050), (1145, 1092), (1130, 1098),
            (1100, 1090), (1075, 1060), (1040, 1025), (1015, 1015), (985, 1035), (960, 1065), (945, 1094),
            (925, 1090), (935, 1070), (948, 1035), (965, 1000), (975, 960), (985, 920), (995, 880),
            (985, 855), (950, 835), (905, 818), (885, 812), (890, 795), (915, 788), (950, 785),
            (990, 768), (1010, 750), (995, 715), (992, 690), (1000, 660)]
STAFF = ((937, 600), (940, 1000))
S = 4  # draw at 4x for smooth curves


def catmull_rom(points, n=12):
    P = np.array(points, float)
    out = []
    for i in range(len(P)):
        p0, p1, p2, p3 = P[i - 1], P[i], P[(i + 1) % len(P)], P[(i + 2) % len(P)]
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append(0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    return np.array(out)


def main(src: str) -> None:
    im = Image.open(src).convert("RGB")
    half = im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
    L = ndi.gaussian_filter(np.asarray(half, dtype=np.float32).mean(2) / 255, 2.2)
    E = exposure.equalize_adapthist(L, kernel_size=120, clip_limit=0.015)
    H, W = E.shape
    ink = np.zeros((H * S, W * S), bool)
    figs = np.zeros_like(ink)
    for poly in (OLD_MAN, MENELAUS):
        c = catmull_rom(poly) * S
        m = np.zeros_like(ink)
        rr, cc = draw.polygon(c[:, 1], c[:, 0], m.shape)
        m[rr, cc] = True
        figs |= m
        ink |= m & ~ndi.binary_erosion(m, iterations=5)
    shadow = (E < 0.30) & ndi.binary_erosion(figs[::S, ::S], iterations=3)
    shadow = morphology.remove_small_objects(shadow, max_size=40)
    sk = morphology.skeletonize(ndi.binary_opening(np.kron(shadow, np.ones((S, S), bool)), iterations=2))
    ink |= ndi.binary_dilation(morphology.remove_small_objects(sk, max_size=60), iterations=2) & figs
    (x0, y0), (x1, y1) = STAFF
    rr, cc = draw.line(y0 * S, x0 * S, y1 * S, x1 * S)
    staff = np.zeros_like(ink)
    staff[rr, cc] = True
    ink |= ndi.binary_dilation(staff, iterations=3)
    OUT.parent.mkdir(exist_ok=True)
    info = lw.trace_svg(
        ink, OUT,
        title="FAILED TEST: hand outline of the letter scene on the Met Iphigenia bowl",
        desc="Not for use. Met 31.11.2 (CC0), view LC-31_11_2b: the old servant and Menelaus; "
             "outlines placed by hand on a local-contrast copy of the photograph.")
    print(OUT, info)


if __name__ == "__main__":
    main(sys.argv[1])
