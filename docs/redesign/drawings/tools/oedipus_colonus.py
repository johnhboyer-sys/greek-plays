"""Oedipus at Colonus: blind Oedipus, seated at the altar with his staff, from
the Apulian red-figure calyx-krater close to the De Schulthess Painter,
340s BCE, Melbourne, Graham Geddes collection A 5:8: Taplin, Pots & Plays
(Getty, 2007) no. 27, plate p. 101. The plate is the only photo there is:
a 942x641 JPEG, page 112 of the Getty PDF, credited there "From Green
2003, p. 4" (J. R. Green, Ancient Voices, Modern Echoes, Nicholson Museum,
Sydney, 2003). The drawing traces only the ancient painting, which is public
domain (John, 2026-10-02); the photo is credited.
https://media.getty.edu/Text/6f3674dd-413a-56da-bec2-9da5564907df.pdf

    pdfimages -j -f 112 -l 112 6f3674dd-413a-56da-bec2-9da5564907df.pdf plate

Red-figure photo -> drawing, at 4x. Oedipus is about 360 px tall in the
plate, so the crop is cleaned of JPEG noise and enlarged 4x (Lanczos)
before anything is traced, as for the Pythia. He is clay on three grounds:
black glaze, the white altar and the white column. Inside a loose cut
(OUTLINE) the figure is what is neither glaze nor white; below the altar's
top the cut runs tight along his legs, so the altar's orange bands stay out.
His hair and beard are added white, so they are outlined, not filled. The
staff is added yellow, drawn as a straight rod (STAFF).

    python3 docs/redesign/drawings/tools/oedipus_colonus.py plate-001.jpg [qa.png]
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402
from oedipus_syracuse import centre_lines, drawn, pen  # noqa: E402  (shared helpers; that file is not changed)

OUT = Path(__file__).resolve().parent.parent / "oedipus-coloneus.svg"
BOX = (395, 205, 560, 590)  # plate crop around him; points below are plate (x, y)
F = 4                       # enlargement
BLACK_L, WHITE_B = 60, 110  # glaze is darker than BLACK_L; the white altar and column bluer than WHITE_B

# The cut, clockwise from the back of his head. Loose through the glaze and
# over the column (both drop out by colour); tight below the altar's top,
# along the hem of his cloak, the chiton over his knee and shin, the staff,
# his feet and the chiton's left edge, crossing the altar's bands at his edge.
OUTLINE = [(426, 228), (440, 216), (452, 213), (466, 212), (480, 215), (491, 222), (499, 234), (502, 240),
           (510, 236), (520, 238), (528, 246), (534, 258), (540, 270), (552, 300), (552, 345), (545, 362),
           (538, 375), (536, 400), (538, 408), (541.5, 414), (542, 418.5), (537, 422), (529.5, 423.5),
           (529, 430), (532.5, 437), (535.5, 446), (536.5, 457), (535, 468), (531, 478), (526.5, 487),
           (522, 496), (523, 503), (523.3, 552), (522, 554.5), (516, 554.5), (515.5, 506), (513.5, 511),
           (510.5, 520), (508, 530), (505.5, 539), (505, 547), (509, 553), (513.5, 560), (516.5, 568),
           (515.5, 573.5), (509, 573.5), (502, 569), (496, 565), (488, 564), (474, 562), (458, 560),
           (444, 557), (435, 556), (428, 552), (427.5, 545), (432, 542), (437.5, 537), (443.5, 526),
           (449.5, 511), (455.5, 494), (461.5, 476), (465.5, 460), (467.5, 450), (468.5, 444), (464, 439),
           (454, 429), (446, 421), (439, 414.5), (428, 410), (420, 400), (417, 380), (415, 362), (409, 346),
           (403, 326), (402, 300), (402, 285), (401, 272), (409, 258), (417, 244)]
# The staff: a straight rod on the line of the painted yellow (measured at y
# 290 and 520), from below his cloaked hand at the top to the altar's foot;
# his other hand covers it between HAND_TOP and HAND_FOOT.
STAFF, STAFF_W = ((513.9, 272.0), (520.6, 553.0)), 3.0

# The head. Hair and beard are one mass of added-white curls round the face
# (HEAD_ZONE holds it), told from the clay by colour: the white is yellower
# (green over red above HAIR_GR). It is outlined, not filled. The face is
# drawn by hand: its edge (FACE, along the hairline, the cheeks and the
# moustache, which runs along the base of the nose) and its lines
# (FACE_LINES), each placed on a painted mark measured in the plate by local
# contrast (2026-10-02).
HEAD_ZONE = [(404, 276), (408, 262), (416, 246), (424, 232), (434, 222), (448, 215), (464, 213), (480, 216),
             (492, 225), (498, 236), (497, 250), (492, 262), (489, 275), (486, 286), (478, 295), (466, 299),
             (450, 299), (436, 293), (424, 289), (412, 287), (404, 284)]
HAIR_GR = 0.665
FACE = [(442.5, 247.5), (444.5, 246), (450, 245.3), (456, 244.9), (462, 244.9), (468, 245.2), (473, 245.8),
        (476.5, 247.2), (476.8, 250), (476, 254.5), (475, 258.5), (474, 262), (472.5, 265.5), (470.8, 268.5),
        (469.3, 270.9), (466.5, 271.5), (464.4, 271.4), (462, 270.6), (457, 269.6), (452, 269), (447.5, 268),
        (444.5, 266.5), (442.6, 263.5), (442, 258), (442, 252)]
FACE_LINES = [
    [(446.2, 249.9), (452.5, 249.8), (459.3, 249.8)],  # a wrinkle across the forehead, in added white
    [(448.2, 255.0), (449.5, 254.6), (452, 254.0), (455, 254.1), (456.5, 254.7), (457.2, 255.4)],  # near brow
    [(448.3, 259.0), (450, 258.4), (453, 258.2), (455, 258.4), (456.0, 258.9)],  # near eye, closed
    [(465.5, 259.2), (467, 258.2), (469, 257.9), (471, 258.5), (472, 259.5), (472.3, 260.2)],  # far brow
    [(465.5, 261.3), (467.5, 261.4), (469, 261.9), (470.5, 262.3), (471.8, 262.9), (472.5, 263.8)],  # far eye, closed
    [(464.6, 261.6), (464.5, 264.0), (464.5, 267.0), (464.6, 269.5), (464.6, 271.2)],  # nose, near side
    [(468.6, 271.2), (468.9, 269.6), (469.6, 267.6), (470.6, 266.5), (471.8, 266.9), (472.6, 267.6)],
    # the tip of the nose, and the far nostril
]
# His right hand, across the staff and over the column: index and middle
# fingers raised, thumb out below them. Drawn stroke by stroke on its painted
# lines (measured by local contrast), each finger a closed outline; inside
# HAND only these strokes are drawn. The staff runs behind it (HAND_COVER).
HAND_LINES = [
    [(511.8, 334.5), (514.5, 331.8), (518.5, 327.8), (522.5, 323.8), (526.5, 320.0), (530.5, 316.3),
     (534.5, 312.2), (537.5, 309.0), (538.8, 307.6), (539.7, 307.9), (539.7, 308.8), (537.5, 311.3),
     (535.0, 314.0), (532.5, 317.0), (531.0, 319.2)],  # back of the hand, the index finger out and back
    [(531.0, 319.2), (534.0, 318.0), (537.5, 316.0), (541.0, 313.6), (543.0, 312.4), (543.9, 312.6),
     (544.2, 313.6), (541.5, 315.8), (538.0, 318.6), (535.0, 321.2), (532.5, 323.4), (531.5, 324.5)],
    # the middle finger
    [(531.5, 324.5), (533.5, 327.5), (536.0, 331.0), (538.5, 334.5), (540.6, 337.4), (543.2, 339.8),
     (546.2, 341.2), (547.0, 341.9), (545.8, 342.8), (542.5, 342.5), (539.0, 341.6), (536.0, 340.4),
     (534.0, 338.8), (532.4, 337.6)],  # the thumb
    [(532.4, 337.6), (530.5, 337.3), (528.6, 338.8), (526.2, 341.6), (522.5, 344.6), (518.5, 347.4),
     (514.5, 350.2), (511.8, 351.8)],  # the hand's lower edge
]
HAND = [(509, 334), (514, 329), (522, 321), (530, 313), (536, 306), (540, 304.5), (542, 307), (541.5, 310.5),
        (544.5, 310.5), (546.5, 313.5), (544, 317.5), (536, 324.5), (541, 333), (545, 338.5), (549, 340.5),
        (548.5, 344), (543, 345), (535, 343), (531, 340.5), (524, 347), (518, 351), (511, 354), (509, 352)]
HAND_COVER = [(511.8, 334.5), (514.5, 331.8), (518.5, 327.8), (522.5, 323.8), (526.5, 320.0), (530.0, 317.0),
              (533.0, 324.0), (531.0, 335.0), (528.6, 338.8), (526.2, 341.6), (522.5, 344.6), (518.5, 347.4),
              (514.5, 350.2), (511.8, 351.8)]
LINE_W = 3  # working px, the width of strokes drawn by hand
CURL_B, CURL_MIN = 115, 16  # curls: the brightest strokes of the white (bluer than CURL_B), at least CURL_MIN px long
# A thin grey line across the black ground between his beard and his raised
# hand, probably a scratch: left out with the ground.
SCRATCH = [(486, 270.5), (505.5, 271), (506, 275.5), (486, 275)]


def P(pts):
    """Plate (x, y) points -> working px of the 4x crop."""
    return [((x - BOX[0]) * F, (y - BOX[1]) * F) for x, y in pts]


def poly(shape, pts):
    return lw.polygon_mask(shape, np.array(P(pts), float))


def load(src):
    """The crop, cleaned of JPEG noise and enlarged F times."""
    a = np.asarray(Image.open(src).convert("RGB"))
    a = cv2.fastNlMeansDenoisingColored(a[:, :, ::-1].copy(), None, 3, 3, 5, 15)[:, :, ::-1]
    c = Image.fromarray(a).crop(BOX)
    c = c.resize((c.width * F, c.height * F), Image.LANCZOS)
    return np.asarray(c, dtype=np.float32)


def rod(shape, ends, w):
    """A straight rod w plate px wide between two plate points: (mask, along, off),
    with t along it (0-1) and the signed distance off its centre line, in working px."""
    (xa, ya), (xb, yb) = P(ends)
    Y, X = np.mgrid[0:shape[0], 0:shape[1]].astype(np.float32)
    d = np.array([xb - xa, yb - ya], np.float32)
    t = ((X - xa) * d[0] + (Y - ya) * d[1]) / float(d @ d)
    off = ((X - xa) * d[1] - (Y - ya) * d[0]) / float(np.hypot(*d))
    return (np.abs(off) <= w * F / 2) & (t >= 0) & (t <= 1), t, off


def staff_lines(shape):
    """The staff as a rod: its two edges and its two ends, LINE_W wide, with
    the stretch behind his hand left out."""
    _, t, off = rod(shape, STAFF, STAFF_W)
    r, lo = STAFF_W * F / 2, (np.hypot(STAFF[1][0] - STAFF[0][0], STAFF[1][1] - STAFF[0][1]) * F)
    sides = (np.abs(off) <= r) & (np.abs(off) > r - LINE_W) & (t >= 0) & (t <= 1)
    ends = (np.abs(off) <= r) & ((np.abs(t * lo) <= LINE_W / 2) | (np.abs((t - 1) * lo) <= LINE_W / 2))
    return (sides | ends) & ~poly(shape, HAND_COVER)


def curl_strokes(core, min_len):
    """Each stroke of the white as one smooth line: the longest path through its
    centre line, kept if it runs at least min_len px. Returns lists of (x, y)."""
    from collections import deque
    sk = morphology.skeletonize(core)
    lab, n = ndi.label(sk, structure=np.ones((3, 3)))
    nbr = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx]

    def far(start, pix):
        prev, q, last = {start: None}, deque([start]), start
        while q:
            last = cur = q.popleft()
            for dy, dx in nbr:
                nb = (cur[0] + dy, cur[1] + dx)
                if nb in pix and nb not in prev:
                    prev[nb] = cur
                    q.append(nb)
        return last, prev

    strokes = []
    for sl, k in zip(ndi.find_objects(lab), range(1, n + 1)):
        ys, xs = np.nonzero(lab[sl] == k)
        pix = set(zip((ys + sl[0].start).tolist(), (xs + sl[1].start).tolist()))
        if len(pix) < min_len:
            continue
        a, _ = far(next(iter(pix)), pix)
        b, prev = far(a, pix)
        path = [b]
        while prev[path[-1]] is not None:
            path.append(prev[path[-1]])
        if len(path) >= min_len:
            pts = path[::3] + ([path[-1]] if (len(path) - 1) % 3 else [])
            strokes.append([(x, y) for y, x in pts])
    return strokes


def main(src: str) -> None:
    a = load(src)
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    L = 0.2126 * R + 0.7152 * G + 0.0722 * B
    shape = L.shape
    inside = poly(shape, OUTLINE) & ~poly(shape, SCRATCH)
    black, white = L < BLACK_L, B > WHITE_B
    staff, _, _ = rod(shape, STAFF, STAFF_W)

    # hair and beard: the yellower white inside HEAD_ZONE, as one smooth mass
    head_zone = poly(shape, HEAD_ZONE)
    ratio = ndi.gaussian_filter(G, 1.5) / np.maximum(ndi.gaussian_filter(R, 1.5), 1)
    hair = (ratio > HAIR_GR) & (ndi.gaussian_filter(L, 1.0) >= BLACK_L) & head_zone
    hair = ndi.binary_closing(ndi.binary_opening(hair, structure=morphology.disk(2)), structure=morphology.disk(4))
    hair = morphology.remove_small_holes(morphology.remove_small_objects(hair, max_size=300), max_size=150)
    hair = ndi.gaussian_filter(hair.astype(float), 2.0) > 0.5
    face = poly(shape, FACE)
    hair &= ~face

    # the figure: clay inside the cut, his hair, and the staff
    clay = inside & ~black & ~white
    sil = ndi.binary_opening(clay, structure=morphology.disk(2)) | hair | staff
    sil = ndi.binary_fill_holes(morphology.remove_small_objects(sil, max_size=2000))
    sil = ndi.gaussian_filter(sil.astype(float), 1.0) > 0.5
    edge = sil & ~ndi.binary_erosion(sil, structure=morphology.disk(2))

    # painted lines inside him, by local contrast; the head, the hand and the
    # staff are drawn below instead
    hand_zone = poly(shape, HAND)
    lines = lw.ink_lines(L, size=15, low=10, high=24, sigma=1.0)
    lines &= ndi.binary_erosion(sil, structure=morphology.disk(3))
    lines &= ~(head_zone | hand_zone | ndi.binary_dilation(staff, iterations=2))
    lines = morphology.remove_small_objects(lines, max_size=40)
    lines = pen(lines, LINE_W)  # the enlarged photo blurs them: redrawn even, along their centres

    # the head: the mass outlined, curls as centre lines of the brightest
    # strokes, the face by hand
    hair_edge = hair & ~ndi.binary_erosion(hair, structure=morphology.disk(2))
    core = (ndi.gaussian_filter(B, 1.0) > CURL_B) & ndi.binary_erosion(hair, iterations=2)
    curls = drawn(shape, curl_strokes(core, CURL_MIN), LINE_W)

    # the hand: only its strokes; the clay under them fills the closed fingers
    hand = drawn(shape, [P(s_) for s_ in HAND_LINES], LINE_W)
    edge &= ~hand_zone
    sil = (sil & ~hand_zone) | (ndi.binary_fill_holes(hand | (sil & ~hand_zone)) & hand_zone)

    lines |= edge | hair_edge | curls | hand
    lines |= drawn(shape, [P(s_) for s_ in FACE_LINES], LINE_W)
    lines |= staff_lines(shape)

    if "--masks" in sys.argv:  # diagnostic: the masks over the photo
        g = L * 0.55
        rgb = np.stack([g, g, g], -1)
        rgb[sil] = rgb[sil] * 0.5 + np.array([255, 60, 60]) * 0.5
        rgb[staff] = rgb[staff] * 0.4 + np.array([60, 255, 60]) * 0.6
        rim = inside & ~ndi.binary_erosion(inside, iterations=2)
        rgb[rim] = (255, 255, 0)
        Image.fromarray(rgb.astype(np.uint8)).save(sys.argv[2])
        return

    info = lw.trace_svg(
        lines, OUT, body=sil,
        title="Oedipus, old and blind, seated, wrapped in his cloak, holding a staff, one hand raised",
        desc="Line drawing after the Apulian red-figure calyx-krater close to the De Schulthess Painter, "
             "340s BCE, Melbourne, Geddes collection A 5:8, read as a scene from Sophocles' Oedipus at "
             "Colonus (Taplin, Pots & Plays no. 27); traced from the plate in Pots & Plays: cut out, "
             "redrawn as line.")
    print(OUT, info)
    if len(sys.argv) > 2:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(L, OUT, info["box"], Path(sys.argv[2]))
        lw.qa_dark(OUT, info["box"], Path(sys.argv[2]).with_suffix(".dark.png"))


if __name__ == "__main__":
    main(sys.argv[1])
