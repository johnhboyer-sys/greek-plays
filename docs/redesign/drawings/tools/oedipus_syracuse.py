"""Oedipus Tyrannus: Oedipus, standing with his hand to his beard, from the
Sicilian red-figure calyx-krater attributed to the Capodarso Painter,
c. 330-320 BCE, Syracuse, Museo Archeologico Regionale "Paolo Orsi" 66557,
excavated at Syracuse in 1968-69. The scene is usually read as one from the play:
the old Corinthian messenger, Oedipus, Jocasta, and their two daughters.
Photo: Dan Diffendale, 2024, CC BY-NC-SA 2.0. The drawing traces only the
ancient painting, which is public domain, so it does not carry the photo's
licence (John, 2026-10-02); the photo is credited:
https://www.flickr.com/photos/dandiffendale/53976554822/
original file: https://live.staticflickr.com/65535/53976554822_177bacc236_o.jpg

Red-figure photo -> drawing. Black glaze surrounds most of the figure, so
the cut is loose there: inside OUTLINE, wide areas of glaze that reach the
background are left out and the clay figure, with its painted lines, stays.
Hand-drawn shapes do the rest: the stage floor and the girl (FLOOR, below
the hem), the modern plaster fill by his elbow (PLASTER), his hair (HAIR,
drawn solid), and his two black shoes on the floor (SHOES). His beard's
strokes are redrawn as separate even hatching (BEARD), and his face lines
as even lines along their centres (FACE).
Three cracks cross the figure; their lines are erased (CRACKS) and painted
lines broken by them are joined across the gap. Below his sleeve the staff
is redrawn as a straight rod on its painted centre line (STAFF): flaking
has left its edges ragged.

    python3 docs/redesign/drawings/tools/oedipus_syracuse.py path/to/photo.jpg [qa.png]
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "oedipus-tyrannus.svg"
BOX = (1382, 922, 2962, 3917)  # photo crop around him; all points below are crop (x, y)
CLAY_L, WIDE = 75, 10           # clay is brighter than CLAY_L; glaze wider than 2*WIDE px is ground
SHOE_L = 105                    # the shoes are greyer than the floor
HAIR_REACH = 10                 # curls: glaze this close to the clay between them

# Loose cut through the glaze around him (the curls and the shoes included;
# the staff below his sleeve is drawn as a rod, STAFF); tight only where
# clay touches clay: the flaked glaze left of his robe (x 312, y 1200-1950)
# and the column (x 1188, y 850-1100).
OUTLINE = [(240, 30), (720, 30), (930, 160), (940, 400), (1060, 560), (1150, 760), (1188, 880),
           (1188, 1060), (1120, 1160), (1035, 1250), (1028, 1400), (1045, 1600), (1040, 2100), (1040, 2580),
           (1140, 2600), (1150, 2760), (1110, 2880), (940, 2940), (380, 2945), (370, 2860),
           (338, 2790), (336, 2600), (336, 2400), (334, 2250), (325, 2100), (315, 1950), (310, 1900),
           (312, 1800), (314, 1700), (314, 1600), (312, 1500), (312, 1400), (312, 1300), (314, 1200),
           (318, 1110),
           (60, 1000), (60, 860), (100, 700), (180, 540), (250, 440), (255, 300), (230, 150)]
# The stage floor and everything right of his shoe: below the hem.
FLOOR = [(0, 2780), (380, 2780), (430, 2815), (560, 2818), (700, 2815), (800, 2815), (935, 2808),
         (965, 2760), (985, 2690), (998, 2630), (1040, 2595), (1580, 2595), (1580, 2995), (0, 2995)]
PLASTER = [(0, 995), (110, 1012), (250, 1052), (262, 1100), (230, 1250), (170, 1400),
           (110, 1500), (0, 1520)]
# The head, in three zones. His hair is a mass of tiny curls that traces as
# speckle, so it is drawn solid, as hair often is on red-figure vases, with
# its curly outline (HAIR). The beard is hatched (BEARD): its strokes are
# redrawn as separate even lines. The face (FACE) has its own finer lines.
# The face's top edge runs just inside the forehead, below the hairline.
HAIRLINE = [(302, 258), (320, 240), (340, 228), (360, 222), (380, 224), (400, 236), (420, 250),
            (445, 264), (468, 290)]
HAIR = [(290, 262), (294, 205), (312, 150), (350, 110), (405, 82), (470, 68), (550, 62), (635, 80),
        (700, 108), (765, 150), (830, 205), (875, 262), (900, 335), (905, 420), (870, 462), (800, 482),
        (745, 492), (712, 540), (700, 600), (660, 630), (610, 615), (600, 560), (585, 480), (560, 420),
        (520, 380), (470, 360)] + HAIRLINE[::-1]
FACE = HAIRLINE + [(466, 345), (440, 372), (410, 392), (392, 428), (372, 424), (345, 370), (318, 300)]
BEARD = [(372, 424), (392, 428), (410, 392), (440, 372), (470, 360), (520, 380), (560, 420), (585, 480),
         (600, 560), (560, 600), (480, 600), (420, 560), (395, 500)]
POCKET = [(303, 1300), (290, 1400), (285, 1500)]  # points in the glaze between staff and robe
# Below his sleeve the staff runs over glaze so flaked that its edges are
# lost in flecks; it is drawn as the straight rod it is, on its painted
# centre line (measured at y 1200-1600), STAFF_W px wide.
STAFF, STAFF_W = ((338, 1000), (192, 1696)), 22
SHOES = [[(385, 2818), (755, 2818), (765, 2870), (700, 2918), (400, 2925), (378, 2870)],
         [(950, 2650), (1132, 2650), (1136, 2720), (1112, 2842), (990, 2852), (945, 2795)]]
# rough paths of the cracks; each is snapped to the line within CORRIDOR px
CRACKS = [[(0, 1005), (250, 1062), (450, 1100), (690, 1140), (970, 1112), (1290, 1000), (1580, 810)],
          [(125, 1465), (250, 1610), (340, 1720), (465, 1895), (665, 2165), (840, 2390), (955, 2500),
           (1065, 2600), (1200, 2740)],
          [(65, 16), (180, 230), (290, 468)]]


def poly(shape, pts):
    return lw.polygon_mask(shape, np.array(pts, float))


CORRIDOR = 14


def crack_bands(L, shape, width=5):
    """Each crack snapped to the line nearest its rough points, widened."""
    from skimage.draw import line
    band = np.zeros(shape, bool)
    # a crack is darker than the clay it crosses but lighter than the glaze
    contrast = np.abs(L - ndi.uniform_filter(L, 25))
    for pts in CRACKS:
        pts = [(min(x, shape[1] - 1), min(y, shape[0] - 1)) for x, y in pts]
        rough = np.zeros(shape, bool)
        for (xa, ya), (xb, yb) in zip(pts[:-1], pts[1:]):
            rr, cc = line(ya, xa, yb, xb)
            rough[rr, cc] = True
        near = ndi.distance_transform_edt(~rough) <= CORRIDOR
        cost = np.where(near, 1.0 + 40.0 / (1.0 + contrast), 1e4)
        xy = lw.livewire(cost, pts)
        yx = (xy[:, ::-1] - 0.5).astype(int)
        band[yx[:, 0], yx[:, 1]] = True
    return ndi.binary_dilation(band, structure=morphology.disk(width))


def staff_masks(shape):
    """The rod, and the strip beside it whose flecks are cleared: 25 px on
    the left, over open glaze; 4 px on the right, short of his robe."""
    (xa, ya), (xb, yb) = STAFF
    Y, X = np.mgrid[0:shape[0], 0:shape[1]]
    d = np.array([xb - xa, yb - ya], float)
    t = np.clip(((X - xa) * d[0] + (Y - ya) * d[1]) / (d @ d), 0, 1)
    off = ((X - xa) * d[1] - (Y - ya) * d[0]) / np.hypot(*d)  # signed distance; < 0 is left of the rod
    along = np.hypot(X - (xa + t * d[0]), Y - (ya + t * d[1]))
    r = STAFF_W / 2
    rod = (along <= r) & (Y >= ya + 10)
    beside = (Y >= ya + 10) & (Y <= yb + 30) & (off >= -(r + 25)) & (off <= r + 4) & (t > 0) & ~rod
    return rod, beside


PEN, BEARD_PEN = 5, 8  # px, the width of redrawn face lines and of beard strokes


def centre_lines(m, spur=6, min_len=14):
    """Centre lines of a stroke mask, with side spurs under `spur` px pruned
    (the line ends are kept) and pieces under `min_len` px dropped."""
    k = np.ones((3, 3), int)
    k[1, 1] = 0
    sk = morphology.skeletonize(m)
    s = sk.copy()
    for _ in range(spur):  # peel the ends...
        s &= ~((ndi.convolve(s.astype(int), k, mode="constant") == 1) & s)
    front = (ndi.convolve(s.astype(int), k, mode="constant") == 1) & s
    for _ in range(spur):  # ...and grow the surviving ends back
        front = ndi.binary_dilation(front, structure=np.ones((3, 3))) & sk & ~s
        s |= front
    return morphology.remove_small_objects(s, max_size=min_len, connectivity=2), k


def pen(m, w):
    """Strokes redrawn as even lines w px wide along their centre lines."""
    s, _ = centre_lines(m)
    return ndi.distance_transform_edt(~s) <= w / 2


def hatch(m, w):
    """Like pen, but a web of crossing strokes is cut at its crossings into
    separate strokes, as a beard is hatched."""
    s, k = centre_lines(m)
    s &= ~((ndi.convolve(s.astype(int), k, mode="constant") > 2) & s)
    s = morphology.remove_small_objects(s, max_size=10, connectivity=2)
    return ndi.distance_transform_edt(~s) <= w / 2


def main(src: str) -> None:
    a = np.asarray(Image.open(src).convert("RGB").crop(BOX), dtype=np.float32)
    L = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    shape = L.shape
    inside = poly(shape, OUTLINE) & ~poly(shape, FLOOR) & ~poly(shape, PLASTER)
    face_zone, beard_zone = poly(shape, FACE), poly(shape, BEARD)
    hair_zone = poly(shape, HAIR) & ~face_zone & ~beard_zone
    head = hair_zone | face_zone | beard_zone
    shoe_zone = np.zeros(shape, bool)
    for s in SHOES:
        shoe_zone |= poly(shape, s)
    cracks = crack_bands(L, shape)

    clay = ndi.binary_opening(L > CLAY_L, structure=morphology.disk(2))  # drops hairline cracks and specks
    dark = L <= CLAY_L
    # the figure: its large areas of clay (flecks of clay in the glaze are small)...
    body = morphology.remove_small_objects(clay & inside & ~cracks, max_size=4000)
    # ...his curls: glaze within reach of the clay showing between them...
    gaps = clay & hair_zone
    hair = hair_zone & dark & (ndi.distance_transform_edt(~gaps) <= HAIR_REACH)
    hair = ndi.binary_closing(hair, structure=morphology.disk(5)) & hair_zone
    hair = ndi.gaussian_filter(ndi.binary_fill_holes(hair).astype(float), 2.0) > 0.5
    hair = morphology.remove_small_objects(hair, max_size=400)
    # ...and his shoes, solid
    shoes = shoe_zone & (L < SHOE_L) & ~cracks
    shoes = ndi.binary_closing(ndi.binary_opening(shoes, structure=morphology.disk(3)), structure=morphology.disk(10))
    shoes = ndi.binary_fill_holes(morphology.remove_small_objects(shoes, max_size=2000))
    shoes = ndi.binary_opening(shoes, structure=morphology.disk(8))  # worn edges rounded off
    # painted lines inside the clay close up; glaze at the outline, and the
    # glaze between his staff and his robe (POCKET), stay out
    sil = ndi.binary_closing(body | hair | shoes, structure=morphology.disk(4))
    # whole again across the cracks, but not where a crack runs along his
    # outline: there the crack is the glaze's, not his
    glaze = ndi.binary_dilation(ndi.binary_opening(dark, structure=morphology.disk(WIDE)), structure=morphology.disk(12))
    sil |= ndi.binary_closing(sil, structure=morphology.disk(9)) & cracks & ~glaze
    holes, _ = ndi.label(ndi.binary_fill_holes(sil) & ~sil)
    open_ = [holes[y, x] for x, y in POCKET if holes[y, x]]
    sil |= (holes > 0) & ~np.isin(holes, open_)
    rod, beside = staff_masks(shape)
    sil = (sil & ~beside) | rod
    sil = morphology.remove_small_objects(sil, max_size=4000)
    sil = ndi.gaussian_filter(sil.astype(float), 1.5) > 0.5

    # painted lines and dots by local contrast; wide strokes by a wider window
    lines = lw.ink_lines(L, size=21, low=13, high=32, sigma=1.2) | lw.ink_lines(L, size=45, low=40, high=70, sigma=1.5)
    lines &= ndi.binary_erosion(sil, structure=morphology.disk(4))
    lines &= ~(beside | rod | head)
    beard = hatch(lw.ink_lines(L, size=15, low=14, high=30, sigma=1.0) & beard_zone, BEARD_PEN)
    face = lw.ink_lines(L, size=15, low=16, high=38, sigma=1.0) & ndi.binary_erosion(face_zone, iterations=3)
    face &= ~ndi.binary_dilation(ndi.binary_opening(dark, structure=morphology.disk(8)), iterations=3)  # the ground
    dots = ndi.binary_opening(face, structure=morphology.disk(3))  # the pupil, kept solid
    face = pen(face & ~ndi.binary_dilation(dots, iterations=2), PEN) | dots
    lines |= hair | beard | face | shoes
    broken = lines & ~cracks  # the cracks erased...
    lines = broken | (ndi.binary_closing(broken, structure=morphology.disk(6)) & cracks)  # ...lines rejoined
    lines = morphology.remove_small_objects(lines, max_size=120)  # specks of wear
    edge = sil & ~ndi.binary_erosion(sil, structure=morphology.disk(4))

    if "--masks" in sys.argv:  # diagnostic: the masks over the photo
        g = np.clip(L, 0, 255) * 0.55
        rgb = np.stack([g, g, g], -1)
        rgb[sil] = rgb[sil] * 0.55 + np.array([255, 60, 60]) * 0.45
        rgb[cracks] = [0, 255, 255]
        for m, c in ((poly(shape, OUTLINE), (255, 255, 0)), (poly(shape, FLOOR), (60, 120, 255)),
                     (poly(shape, PLASTER), (60, 255, 60)), (hair_zone, (255, 0, 255)), (shoe_zone, (255, 160, 0))):
            rim = m & ~ndi.binary_erosion(m, iterations=3)
            rgb[rim] = c
        Image.fromarray(rgb.astype(np.uint8)).save(sys.argv[2])
        return

    info = lw.trace_svg(
        edge | lines, OUT, body=sil,
        title="Oedipus, bearded, in a long embroidered robe, his hand at his beard, holding a staff",
        desc="Line drawing after the Sicilian red-figure calyx-krater attributed to the Capodarso Painter, "
             "c. 330-320 BCE, Syracuse, Museo Archeologico Regionale Paolo Orsi 66557, read as a scene from "
             "Sophocles' Oedipus Tyrannus; traced from Dan Diffendale's photograph: cut out, cracks removed, "
             "redrawn as line.")
    print(OUT, info)
    if len(sys.argv) > 2:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(L, OUT, info["box"], Path(sys.argv[2]))
        lw.qa_dark(OUT, info["box"], Path(sys.argv[2]).with_suffix(".dark.png"))


if __name__ == "__main__":
    main(sys.argv[1])
