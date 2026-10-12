"""Persians (Aeschylus): the Persian king flees in his chariot (WORK IN PROGRESS; docstring filled at approval).
From H. Heydemann, Hallisches Winckelmannsprogramm 8 (1883), folding plate, top frieze (Naples H 3220), Heidelberg
hwpr1883 C.jpg (3682 x 2779; Public Domain Mark 1.0).

    python3 docs/redesign/drawings/tools/persians.py C.jpg [qa.png] [dump.npz]
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import morphology
from skimage.filters import apply_hysteresis_threshold

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "persians.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

# crop in plate px: the whole top frieze with its stars, plants and dotted ground line (John, 2026-10-10)
X0, Y0, X1, Y1 = 180, 185, 3460, 1275
UP = 3                                    # work at 3x the plate's px: the king's face is small
CLOSE_R = 5                               # plate px: Maximum then Minimum, wider than a line
LOW, HIGH = 16, 34                        # local contrast (grey levels): a line starts at HIGH, runs on down to LOW
SOLID = 120                               # solid black: darker than this, lightly blurred
CORE_R, HALF = 1.5, 0.5                   # a line's core: the darkest px within CORE_R plate px (no farther:
#                                           in the curls a darker neighbour hid the fainter strokes)
SMOOTH = 0.6                              # plate px: the line mask's Gaussian, cut at half
SPECK = 2                                 # plate px^2: smaller pieces of ink are specks of the print (the
#                                           mouth's dot and the beard's are 3)
SEAL = 6
# pockets of ground the figures close in (a point in each, plate px): the wheels' openings between the
# spokes (OPEN: the paper inside the spokes, narrower than OPEN_R across, stays clay), the space under the
# chariot's rear rail curl and between it and the left wheel, and the gaps between the legs and wheels under
# the chariot (John, 2026-10-10: "Still some areas that should be ground")
OPEN_R, NECK = 8, 5                       # plate px
POCKETS = [(1049, 917, OPEN_R), (1076, 1043, NECK), (1019, 1104, OPEN_R), (1107, 1087, NECK), (1152, 1038),
           (1153, 1057, NECK), (1156, 934, NECK), (1166, 844, NECK),
           (1463, 1141, OPEN_R), (1520, 1085, NECK), (1406, 1079, NECK), (1424, 1044, NECK), (1473, 1005), (1421, 966),
           # and those John marked blue on pass 1 (2026-10-11, "here are spots you missed"): between the
           # horseman's horse and the chariot, under the driver's arm, behind the chariot, the left wheel's
           # openings, between the horses' legs, and in the right-hand plant (he ruled each area, 2026-10-11:
           # two he marked, under the horseman's arm and at his horse's chest, are figure); each cut at its necks narrower
           # than NECK (John: "Some of your areas are a mix of illustration and ground": a gap in a line had
           # joined them)
           (986, 517, NECK), (828, 545, NECK), (1833, 556, NECK),
           (992, 564, NECK), (1090, 596, NECK), (1476, 684, NECK), (1528, 707, NECK), (1013, 757, NECK),
           (1013, 846, NECK), (966, 883, NECK), (1097, 971, NECK), (992, 988, NECK), (3231, 1053, NECK),
           (3185, 1086, NECK), (1084, 1112, NECK), (1795, 691, NECK)]
# shafts crossing ground (rough ends of the centre line, plate px; fitted to their edge lines by `shaft`, kept
# clay through the pockets): the horseman's lance, from its butt past his hand to the king; the spear over the
# horses' heads, from the mane to its collar, and its head
SHAFTS = [((482, 489), (1120, 550)), ((1768, 556), (1888, 503)), ((1912, 497), (1960, 476))]
# small closed parts (boxes, plate px): the paper the ink closes there, after a closing by CLOSE plate px, is
# clay: the horseman's spearhead; the horseman's horse's forelock (its first lock, closed by John's line on
# pass 2, reached the ground through a gap)
CLOSED = [(392, 452, 472, 496), (935, 360, 975, 400)]
CLOSE = 2
NEAR = 10                                 # plate px
GROUND_Y = 990                            # plate px: the ground line lies below
BIG = 20000                               # plate px^2
WEIGHT = 0.00025                          # 0.8 plate px: John chose it (2026-10-10, A/B of 0.8 and 1.4 on the
#                                           king's head; he asked for "crisp and precise"); the plate's pen line is about
#                                           1-1.2 px under the scan's blur (its half-maximum width is 1.5)
TRACE_H = 6400
# John's marks, drawn in PhotoCraft over each pass on the crop at MARKS_K x the plate px. Blue is ink as he
# drew it (outlines closed where the pen broke off, missing ones, the eyes); yellow is clay (2026-10-12: the
# paper round it, out to the lines, up to MARK_R); green is "erase or ground" (2026-10-12): the ink he covers
# mostly (MARK_COVER of a piece) goes, and the paper round it, out to the lines and up to MARK_R, is ground,
# or the whole area the lines close (sealed by the watershed, as the figures' area; cut at its necks narrower
# than NECK) if he covers MARK_FILL of it (marks 3, 2026-10-12: "I didn't color in all of the ground there"). Marks 1 (2026-10-11): pass 1; marks 2
# (2026-10-12): pass 2; marks 3 (2026-10-12): pass 3.
MARKS_FILES = [Path(__file__).parent / f"persians_marks_{i}.png" for i in (1, 2, 3)]
MARKS_K = 2
MARK_R, MARK_COVER, MARK_FILL = 8, 0.5, 0.15
# paired fine strokes the scan runs together (boxes, plate px): the slits between them, under SLIT plate px^2,
# filled and the pair drawn along its middle at a pen line's width, as one clean line (John, 2026-10-12: the horseman's greave, "those lines on
# the leg look bad": they came out as blobs with holes)
PAIRS = [(755, 770, 800, 940)]
SLIT = 40
WALLS = []
WALL_W = 2.0
# Shading: the plate shades some parts (the king's cap, sleeves and belt, the chariot's rails and panel, the
# shield's rim) finer than the scan resolves (strokes and dots 2-3 plate px apart). Each shaded area is given
# by a polygon drawn round it (plate px), outside its outlines and along the edge of the hair or the like
# where no line bounds it: the area is the polygon's px where the plate, blurred by DARK_S, is darker than
# DARK_DK below the paper (the paper outside the outlines and between the curls is lighter), closed and opened
# by a disk DARK_R wide (an entry's 'dk' sets its own, for the lighter stipple of the rails), holes under
# HOLE filled. Inside it the plate's dark lines (STRONG, by local contrast with hysteresis) of LINE_MIN or more
# are kept as printed (smaller are the shading's own darker specks; an entry's 'keep' sets its own: smaller
# for the sleeves' dotted pattern; 'edge' on the shield's rim and the rails, whose shading the scan blots
# into their outlines: none kept, the outline drawn new along the area's edge, a plate px wide;
# 'dk' lower on the rim's lighter lower half), and
# every line within EDGE of the area's border (its outlines, however broken), but for blots wider than BLOT
# (the scan's blur of shading against a line); the shading is drawn only inside the outlines (John,
# 2026-10-10: "Don't let hatching or stipples extend beyond outlines"), dots only where they fit whole; the shading is drawn evenly in its own
# kind (John, 2026-10-10): hatch ("Even hatch lines") as lines running the area's length (between its 'ends'
# or along its 'sides') and following both its sides ("They need to also follow the contours of the area they fill"), at the
# spacing (plate px) read off the plate at 8x, each line COVER of the spacing wide ("Thinner lines for
# hatching"), the outline smoothed by SMOOTH_D; stipple ("Even dots") as a staggered grid of dots DOT_D wide at the spacing.
STRONG = (65, 100)
DARK_S, DARK_DK, DARK_R = 1.0, 20, 1.5    # plate px, grey levels, plate px
HOLE, LINE_MIN = 80, 25                   # plate px^2
BLOT = 3.2                                # plate px
EDGE = 2                                  # plate px
INNER = 2                                 # plate px
COVER = 0.2
SMOOTH_D = 0.7                            # plate px
MERGE, SPLIT = 0.6, 1.4
DOT_D, DOT_SP = 0.8, 1.7                   # plate px: dot width and spacing (John, 2026-10-10: "stipple
#                                           should be denser"; first 2.5-3, read off the plate)
HATCH = [
    # the king's cap, its knob and its flaps down both sides of his face, cut along the hair
    ('lines', 2.6, [(1226, 442), (1222, 400), (1222, 368), (1228, 358), (1236, 350), (1234, 320), (1238, 300),
                    (1270, 300), (1305, 322), (1345, 340), (1362, 358), (1366, 368), (1368, 400), (1362, 445),
                    (1345, 448), (1338, 420), (1336, 395), (1332, 375), (1310, 365), (1285, 362), (1262, 362),
                    (1250, 368), (1248, 395), (1250, 420), (1246, 442)],
     {'sides': ((1226, 442), (1362, 446), (1246, 442), (1345, 448))}),
    # his raised sleeve, wrist to shoulder
    ('lines', 2.8, [(1098, 425), (1112, 402), (1150, 425), (1185, 444), (1225, 442), (1228, 470), (1222, 505),
               (1170, 505), (1140, 490), (1110, 465), (1095, 440)], {'keep': 8, 'sides': ((1112, 404), (1224, 447), (1099, 445), (1205, 505))}),
    # his belt
    ('lines', 2.4, [(1194, 575), (1200, 566), (1220, 556), (1250, 559), (1282, 569), (1305, 586), (1308, 600),
                (1300, 607), (1288, 602), (1250, 592), (1220, 590), (1196, 594)], {'sides': ((1197, 565), (1302, 594), (1196, 590), (1296, 610))}),
    # his other sleeve, by the driver's hand
    ('lines', 2.8, [(1376, 630), (1398, 620), (1420, 640), (1442, 668), (1430, 680), (1400, 690), (1382, 690),
               (1372, 660)], {'keep': 8, 'sides': ((1402, 618), (1444, 668), (1385, 627), (1440, 674))}),
    # the sword's scabbard, and its tip past his hand
    ('lines', 3.0, [(1322, 662), (1340, 660), (1425, 705), (1422, 722), (1410, 724), (1325, 684)], {'sides': ((1335, 664), (1422, 706), (1325, 682), (1414, 724))}),
    ('lines', 3.0, [(1438, 714), (1460, 716), (1498, 736), (1496, 750), (1438, 740)], {'sides': ((1453, 718), (1503, 742), (1450, 744), (1500, 748))}),
    # the sword's hilt: stipple
    ('dots', DOT_SP, [(1265, 620), (1300, 615), (1330, 640), (1335, 664), (1320, 674), (1290, 672), (1265, 665),
                   (1262, 640)]),
    # the chariot's rail curving round the king's legs, and its curl at the left: stipple
    ('dots', DOT_SP, [(1240, 752), (1245, 720), (1262, 690), (1300, 676), (1340, 682), (1362, 700), (1368, 728),
                   (1356, 732), (1350, 708), (1330, 692), (1300, 688), (1272, 698), (1258, 722), (1254, 752)],
     {'dk': 14, 'keep': 'edge'}),
    ('dots', DOT_SP, [(1215, 782), (1180, 786), (1150, 800), (1132, 830), (1126, 860), (1136, 890), (1160, 908),
                   (1190, 920), (1192, 905), (1165, 895), (1148, 875), (1144, 850), (1150, 822), (1165, 805),
                   (1195, 798), (1214, 796)], {'dk': 14, 'keep': 'edge'}),
    # the chariot's side panel, upper and lower zones (the scrolls kept as printed)
    ('lines', 3.0, [(1350, 904), (1436, 904), (1410, 992), (1288, 992)], {'sides': ((1352, 906), (1428, 906), (1287, 990), (1406, 995))}),
    ('lines', 3.0, [(1288, 988), (1410, 994), (1385, 1015), (1355, 1054), (1218, 1054), (1240, 1030)], {'sides': ((1288, 992), (1404, 998), (1222, 1045), (1350, 1050))}),
    # and its sliver showing between the horses' legs at the left
    ('lines', 3.0, [(1158, 1036), (1172, 1018), (1200, 996), (1224, 974), (1222, 985), (1205, 1012), (1185, 1025),
               (1176, 1040)], {'sides': ((1162, 1030), (1222, 976), (1175, 1040), (1222, 986))}),
    # the horseman: the patch under his arm, the one at his side, and the scalloped band at his waist
    ('lines', 2.8, [(640, 392), (672, 386), (700, 400), (702, 430), (690, 452), (660, 452), (640, 425), (634, 405)], {'ends': ((637, 400), (690, 450))}),
    ('lines', 2.8, [(780, 470), (805, 455), (830, 462), (828, 500), (815, 522), (780, 522), (775, 500)], {'sides': ((790, 460), (780, 518), (822, 460), (828, 505))}),
    ('lines', 2.6, [(622, 575), (640, 570), (660, 592), (720, 606), (758, 594), (775, 570), (795, 575), (800, 600),
               (780, 625), (740, 645), (700, 645), (660, 640), (630, 620), (618, 595)], {'sides': ((628, 575), (785, 573), (622, 600), (798, 600))}),
    # the axe-man's belt; the strap and the patch behind the shield: stipple
    ('lines', 2.5, [(2540, 668), (2580, 664), (2612, 674), (2645, 690), (2662, 704), (2656, 716), (2640, 714),
                (2608, 699), (2580, 688), (2540, 688)], {'sides': ((2541, 668), (2660, 702), (2541, 688), (2652, 716))}),
    ('dots', DOT_SP, [(2725, 575), (2740, 565), (2765, 570), (2795, 610), (2790, 632), (2770, 638), (2730, 600)]),
    ('dots', DOT_SP, [(2698, 650), (2712, 648), (2740, 672), (2735, 686), (2722, 686), (2700, 665)]),
    # the shield's rim
    ('lines', 2.2, [(2705, 690), (2710, 728), (2740, 750), (2790, 749), (2850, 736), (2910, 713),
                                 (2962, 688), (2999, 656), (3021, 622), (3020, 595), (3005, 575), (2985, 575),
                                 (2995, 600), (2990, 625), (2960, 655), (2915, 680), (2860, 700), (2800, 715),
                                 (2750, 722), (2722, 712), (2718, 695)], {'keep': 'edge', 'dk': 12, 'ends': ((2711, 708), (3012, 578))}),
    # the right-hand Greek's scabbard: its mount and its tip, stipple
    ('dots', DOT_SP, [(2895, 716), (2952, 712), (2955, 735), (2945, 750), (2905, 742)]),
    ('dots', DOT_SP, [(2965, 858), (2995, 852), (3000, 870), (2990, 890), (2972, 885)]),
]


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def masks(src):
    """The plate's ink and the figures' area at UP (work px), and the plate in grey."""
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        Image.open(src).convert("RGB").save(t / "src.png")
        w, h = X1 - X0, Y1 - Y0
        pc(t / "src.png", t / "up.png",
           ("image.crop", {"x": X0, "y": Y0, "width": w, "height": h}),
           ("image.imageSize", {"width": w * UP, "height": h * UP, "resample": "bicubic"}),
           ("image.mode.grayscale", None))
        pc(t / "up.png", t / "gl.png", ("filter.blur.gaussianBlur", {"radius": 0.5 * UP}))
        r = CLOSE_R * UP
        pc(t / "gl.png", t / "closed.png", ("filter.other.maximum", {"radius": r, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": r, "preserve": "squareness"}))
        pc(t / "gl.png", t / "solid.png", ("image.adjustments.threshold", {"level": SOLID}))
        pc(t / "gl.png", t / "core.png", ("filter.other.minimum", {"radius": CORE_R * UP, "preserve": "roundness"}))
        g, gl, closed, core = grey(t / "up.png"), grey(t / "gl.png"), grey(t / "closed.png"), grey(t / "core.png")
        # half maximum: darker than halfway between the paper and the line's darkest px near it, so each
        # line keeps its printed width (local contrast alone took in its soft edge, and the hair's strokes
        # ran together)
        half = (closed - gl) >= HALF * (closed - core)
        ink = apply_hysteresis_threshold(np.where(half, closed - gl, 0), LOW, HIGH) | (grey(t / "solid.png") < 128)
        Image.fromarray(np.where(ink, 0, 255).astype(np.uint8)).save(t / "ink.png")
        pc(t / "ink.png", t / "smooth.png", ("filter.blur.gaussianBlur", {"radius": SMOOTH * UP}),
           ("image.adjustments.threshold", {"level": 128}))
        ink = grey(t / "smooth.png") < 128
    lab, _ = ndi.label(ink)
    ink &= (np.bincount(lab.ravel()) > SPECK * UP * UP)[lab]
    dk = np.clip(closed - gl, 0, None)
    reg, inner, strong = hatched(dk)
    lines = ruled(reg, inner)
    reg = reg > 0
    ink = (ink & ~reg) | (strong & reg)
    return g, gl, ink, reg, lines & (inner > 0)


def hatched(dk):
    """The shaded areas (work px, numbered as HATCH), the part of each inside its outlines (where the shading
    is drawn), and the plate's dark lines kept in them."""
    from skimage.draw import polygon as poly
    strong = apply_hysteresis_threshold(dk, *STRONG)
    r = DARK_R * UP
    disk = np.hypot(*np.mgrid[-int(r):int(r) + 1, -int(r):int(r) + 1]) <= r
    blur = ndi.gaussian_filter(dk, DARK_S * UP)
    dark = {t: ndi.binary_opening(ndi.binary_closing(blur > t, structure=disk), structure=disk)
            for t in {e[3].get('dk', DARK_DK) if len(e) > 3 else DARK_DK for e in HATCH}}
    sl, _ = ndi.label(strong)
    size = np.bincount(sl.ravel())[sl]
    reg = np.zeros(dk.shape, np.int16)
    inner = np.zeros(dk.shape, np.int16)
    keep = np.zeros(dk.shape, bool)
    rims = np.zeros(dk.shape, bool)
    for i, (mode, _, pts, *opt) in enumerate(HATCH, 1):
        opt = opt[0] if opt else {}
        xs, ys = zip(*pts)
        rr, cc = poly((np.array(ys) - Y0 + 0.5) * UP, (np.array(xs) - X0 + 0.5) * UP, dk.shape)
        m = np.zeros(dk.shape, bool)
        m[rr, cc] = True
        m &= dark[opt.get('dk', DARK_DK)]
        holes = ndi.binary_fill_holes(m) & ~m
        hl, _ = ndi.label(holes)
        m |= (np.bincount(hl.ravel()) < HOLE * UP * UP)[hl] & holes
        m &= reg == 0
        reg[m] = i
        edge = opt.get('keep') == 'edge'
        k = np.zeros_like(m) if edge else m & ~ndi.binary_erosion(m, iterations=round(EDGE * UP))
        if not edge:
            k |= m & (size >= opt.get('keep', LINE_MIN) * UP * UP)
        keep |= k
        # inside the outlines: the area less the lines kept, without the strips beyond them (thinner than
        # INNER plate px: the blur took in a px or two past each outline)
        n = ndi.binary_opening(m & ~(strong & k), structure=morphology.disk(INNER * UP / 2))
        nl, _ = ndi.label(n)
        n &= (np.bincount(nl.ravel()) >= HOLE * UP * UP)[nl]
        inner[n] = i
        if edge:  # its outline drawn new along the area's edge
            rims |= n & ~ndi.binary_erosion(n, iterations=UP)
    # the dark blots the scan makes of the shading where it runs into a line (wider than BLOT): not lines
    blot = ndi.binary_opening(strong, structure=morphology.disk(BLOT * UP / 2)) & (reg > 0)
    return reg, inner, (strong & ~blot & (keep | (reg == 0))) | rims


def ruled(reg, inner):
    """The even lines or dots in each shaded area (reg, whole), drawn inside its outlines (inner), as its
    HATCH entry says. Lines run the area's length, following both its sides: the area's outline is split into
    two sides, at its two 'ends' (where it narrows to a point) or as its 'sides' give them (each from its first
    point to its second, where it ends square), and the lines are the levels of the share of the way across
    from one side to the other, as many as the median width holds at the spacing; where they close in
    toward an end, every other one stops each time they close to under MERGE of the spacing, and where they
    spread, one is added between each two each time they pass SPLIT of it (John, 2026-10-10: the cap's crown
    "could be denser")."""
    from skimage.measure import find_contours
    out = np.zeros(reg.shape, bool)
    for k, sl in enumerate(ndi.find_objects(reg), 1):
        if sl is None:
            continue
        mode, sp, pts, *opt = HATCH[k - 1]
        yy, xx = np.mgrid[sl]
        x, y = (xx + 0.5) / UP, (yy + 0.5) / UP
        if mode == 'dots':
            h = sp * np.sqrt(3) / 2
            j = np.round(y / h)
            i = np.round(x / sp - (j % 2) / 2)
            cx, cy = (i + (j % 2) / 2) * sp, j * h
            on = np.hypot(x - cx, y - cy) <= DOT_D / 2
            # only dots wholly inside the outlines
            fits = ndi.distance_transform_edt(inner[sl] == k) / UP >= DOT_D / 2 + 0.3
            on &= fits[np.clip(np.round(cy * UP - 0.5).astype(int) - sl[0].start, 0, fits.shape[0] - 1),
                       np.clip(np.round(cx * UP - 0.5).astype(int) - sl[1].start, 0, fits.shape[1] - 1)]
        else:
            a = ndi.binary_fill_holes(np.pad(reg[sl] == k, 3))
            c = max(find_contours(ndi.gaussian_filter(a.astype(float), SMOOTH_D * UP), 0.5), key=len)
            near = [int(np.argmin(np.hypot(c[:, 0] - ((ey - Y0) * UP - sl[0].start + 3),
                                           c[:, 1] - ((ex - X0) * UP - sl[1].start + 3))))
                    for ex, ey in opt[0].get('sides', opt[0].get('ends'))]
            N = len(c)
            run = lambda i, j: np.arange(i, j + 1 if j >= i else j + N + 1) % N
            if len(near) == 2:   # two ends: the two arcs between them
                arcs = [run(near[0], near[1]), run(near[1], near[0])]
            else:                # two sides, each from its first point to its second, not over the other's
                arcs = []
                for (i, j), other in (((near[0], near[1]), near[2:]), ((near[2], near[3]), near[:2])):
                    r = run(i, j)
                    arcs.append(r if not np.isin(other, r).any() else run(j, i))
            d = []
            for arc in (c[arcs[0]], c[arcs[1]]):
                m = np.ones(a.shape, bool)
                f = np.linspace(0, len(arc) - 1, len(arc) * 4)
                m[np.round(np.interp(f, np.arange(len(arc)), arc[:, 0])).astype(int).clip(0, a.shape[0] - 1),
                  np.round(np.interp(f, np.arange(len(arc)), arc[:, 1])).astype(int).clip(0, a.shape[1] - 1)] = False
                d.append(ndi.distance_transform_edt(m)[3:-3, 3:-3] / UP)
            w = d[0] + d[1]
            n = max(1, round(np.median(w[reg[sl] == k]) / sp))
            t = d[0] / np.maximum(w, 1e-6) * n
            # where the area widens, a line is added between each two each time they spread past SPLIT of
            # the spacing (else the lines stand apart, as on the cap's crown)
            up = np.ceil(np.log2(np.maximum(w / (n * sp) / SPLIT, 1))).astype(int)
            u = t * 2 ** up
            on = np.abs(u % 1 - 0.5) * w / (n * 2 ** up) < COVER * sp / 2
            # toward the ends, where the sides meet, every other line stops each time the lines close to
            # under MERGE of the spacing (else they run together in a fan)
            lv = np.ceil(np.log2(np.maximum(MERGE * sp * n / np.maximum(w, 1e-6), 1))).astype(int)
            on &= np.floor(t).astype(int) % (2 ** lv) == 0
        out[sl] |= on & (inner[sl] == k)
    return out


def shaft(gl, a, b):
    """A shaft's band (bool, work px): the paper between its two edge lines, along the centre line fitted
    to the midpoints between them (read across the shaft every 4 plate px, the darkest px on each side of
    the rough centre within 14 plate px), out to the edge lines' centres. Returns the band, its half-width
    and the fit's rms (plate px)."""
    a, b = np.array(a, float), np.array(b, float)
    u = (b - a) / np.hypot(*(b - a))
    n = np.array([-u[1], u[0]])
    mids, gaps = [], []
    for s in np.arange(0, np.hypot(*(b - a)), 4):
        p = a + s * u
        o = np.arange(-14, 14.01, 0.5)
        q = (p[None] + o[:, None] * n[None] - (X0, Y0)) * UP
        v = ndi.map_coordinates(gl, [q[:, 1], q[:, 0]], order=1)
        lo, hi = o < 0, o > 0
        i, j = np.argmin(np.where(lo, v, 1e9)), np.argmin(np.where(hi, v, 1e9))
        if v[i] < 150 and v[j] < 150 and 4 < o[j] - o[i] < 26:
            mids.append(p + (o[i] + o[j]) / 2 * n)
            gaps.append(o[j] - o[i])
    mids = np.array(mids)
    t = (mids - a) @ u
    f = np.polyfit(t, (mids - a) @ n, 1)
    res = (mids - a) @ n - np.polyval(f, t)
    hw = np.median(gaps) / 2
    band = np.zeros(gl.shape, bool)
    (cx0, cy0), (cx1, cy1) = [(np.floor((np.minimum(a, b) - 20 - (X0, Y0)) * UP)).astype(int).clip(0),
                              (np.ceil((np.maximum(a, b) + 20 - (X0, Y0)) * UP)).astype(int)]
    yy, xx = np.mgrid[cy0:cy1, cx0:cx1]
    px, py = (xx + 0.5) / UP + X0 - a[0], (yy + 0.5) / UP + Y0 - a[1]
    along_, across = px * u[0] + py * u[1], px * n[0] + py * n[1]
    band[cy0:cy1, cx0:cx1] = ((along_ >= 0) & (along_ <= np.hypot(*(b - a))) &
                              (np.abs(across - np.polyval(f, along_)) <= hw))
    return band, hw, float(np.sqrt(np.mean(res ** 2)))


def walls(shape):
    """WALLS as a mask (work px), WALL_W plate px wide."""
    m = np.zeros(shape, bool)
    for pts in WALLS:
        for (xa, ya), (xb, yb) in zip(pts[:-1], pts[1:]):
            k = int(np.hypot(xb - xa, yb - ya) * UP * 2) + 2
            xs, ys = np.linspace(xa, xb, k), np.linspace(ya, yb, k)
            m[np.round((ys - Y0) * UP).astype(int), np.round((xs - X0) * UP).astype(int)] = True
    return ndi.distance_transform_edt(~m) <= WALL_W * UP / 2 if m.any() else m


def figure(ink, gl):
    """The figures' area: the paper the ink closes off from the ground round the group by passages narrower
    than SEAL (the watershed areas but for those reaching the crop's edge and the POCKETS), the shafts, the
    small closed parts, and the ink touching them."""
    from skimage.segmentation import watershed
    paper = ~(ink | walls(ink.shape))
    mk, _ = ndi.label(ndi.binary_opening(paper, structure=morphology.disk(SEAL * UP)))
    ws = watershed(-ndi.distance_transform_edt(paper), mk, mask=paper)
    out = np.unique(np.r_[ws[0], ws[-1], ws[:, 0], ws[:, -1]])
    out = out[out > 0]
    ground = np.isin(ws, out)
    pk = np.zeros_like(ground)
    for x, y, *how in POCKETS:
        k = ws[round((y - Y0) * UP), round((x - X0) * UP)]
        if not k or k in out:
            print('pocket point', (x, y), 'is not on paper the group closes')
            continue
        m = ws == k
        if how:  # the wide part round the point, grown back into its corners but not through narrow necks
            r = how[0] * UP
            o = ndi.binary_opening(m, structure=morphology.disk(r))
            lab, _ = ndi.label(o)
            _, (iy, ix) = ndi.distance_transform_edt(lab == 0, return_indices=True)
            py, px = round((y - Y0) * UP), round((x - X0) * UP)
            o = lab == lab[iy[py, px], ix[py, px]]      # the piece holding the point (or nearest it)
            m = ndi.binary_dilation(o, iterations=r, mask=m) if o.any() else o   # step by step: not across lines
        ground |= m
        pk |= m
    clay = paper & ~ground
    bands = np.zeros_like(paper)
    for a, b in SHAFTS:
        band, hw, rms = shaft(gl, a, b)
        print('shaft', a, b, 'half-width', round(hw, 2), 'rms', round(rms, 2))
        clay |= band & paper
        bands |= band & paper
    kept = np.zeros_like(paper)                  # (thin clay there, which the body's smoothing would take)
    for bx0, by0, bx1, by1 in CLOSED:
        sl = np.s_[(by0 - Y0) * UP:(by1 - Y0) * UP, (bx0 - X0) * UP:(bx1 - X0) * UP]
        c = ndi.binary_closing(ink[sl], structure=morphology.disk(CLOSE * UP))
        clay[sl] |= ndi.binary_fill_holes(c) & ~c & paper[sl]
        kept[sl] |= ndi.binary_fill_holes(c) & ~c & paper[sl]
    # (the ink they close in too: the shield's star, wider than the reach)
    fig = ndi.binary_fill_holes(clay | (ink & ndi.binary_dilation(clay, iterations=2 * UP)))
    return fig & ~(ground & paper & ~bands), pk & ~bands, kept, ws


def marks(shape):
    """John's marks at the work px: (blue, green, yellow)."""
    blue, green, yellow = (np.zeros(shape, bool) for _ in range(3))
    for mf in MARKS_FILES:
        m = Image.open(mf).convert('RGBA')
        assert m.size == ((X1 - X0) * MARKS_K, (Y1 - Y0) * MARKS_K), m.size
        m = np.asarray(m.resize((shape[1], shape[0]), Image.NEAREST)).astype(int)
        r, gg, bb, al = (m[..., i] for i in range(4))
        blue |= (al > 40) & (bb > r + 40) & (bb > gg + 20)
        green |= (al > 40) & (gg > r + 40) & (gg > bb + 20)
        yellow |= (al > 40) & (r > 150) & (gg > 150) & (bb < r - 60)
    return blue, green, yellow


def main(src, qa=None, dump=None):
    g, gl, ink, reg, hatch = masks(src)
    blue, green, yellow = marks(ink.shape)
    near = ndi.binary_dilation(green, iterations=UP)
    lab, n = ndi.label(ink)
    covered = np.bincount(lab[near], minlength=n + 1) >= MARK_COVER * np.bincount(lab.ravel(), minlength=n + 1)
    covered[0] = False
    ink = (ink & ~covered[lab]) | blue
    for bx0, by0, bx1, by1 in PAIRS:
        sl = np.s_[(by0 - Y0) * UP:(by1 - Y0) * UP, (bx0 - X0) * UP:(bx1 - X0) * UP]
        holes = ndi.binary_fill_holes(ink[sl]) & ~ink[sl]
        hl, _ = ndi.label(holes)
        ink[sl] |= (np.bincount(hl.ravel()) < SLIT * UP * UP)[hl] & holes
        ink[sl] = ndi.binary_dilation(morphology.skeletonize(ink[sl]), iterations=UP // 2 + 1)  # one line wide
    fig, pk, kept, ws = figure(ink | reg, gl)
    paper = ~(ink | reg)
    grow = lambda m: ndi.binary_dilation(m & paper, iterations=MARK_R * UP, mask=paper) | m  # noqa: E731
    lab, n = ws, ws.max()                             # the areas the lines close, sealed as in `figure`
    size = np.bincount(lab.ravel(), minlength=n + 1)
    full = np.bincount(lab[green], minlength=n + 1) >= MARK_FILL * size
    full[0] = False
    whole = full[lab] & paper                         # (cut at its necks: a gap in the third horse's muzzle
    o = ndi.binary_opening(whole, structure=morphology.disk(NECK * UP))   # let the area run into it)
    ol, _ = ndi.label(o)
    o = np.isin(ol, np.unique(ol[ndi.binary_dilation(green, iterations=NECK * UP) & (ol > 0)]))
    gone = grow(green) | (ndi.binary_dilation(o, iterations=NECK * UP, mask=whole) if o.any() else o)
    clay = ndi.binary_fill_holes(grow(yellow))
    fig = (fig & ~gone) | clay
    pk = (pk | gone) & ~clay
    kept |= clay
    fig |= ndi.binary_dilation(blue, iterations=UP) & ~pk    # (his lines on clay, on the dark theme)
    fig |= reg                               # the hatched areas whole (the paper between the ruled lines is
    #                                          too narrow for the seal), and walls to the ground
    # specks on the paper round the group: ink farther than NEAR from every figure (a toe's tip stands just
    # outside the foot's outline: the left youth's rear foot)
    lab, n = ndi.label(ink)
    on = np.zeros(n + 1, bool)
    on[lab[ndi.distance_transform_edt(~fig) <= NEAR * UP]] = True
    on[lab[GROUND_Y * UP - Y0 * UP:]] = True          # the dotted ground line (John: keep it)
    on[0] = False
    ink &= on[lab]
    # The field ornaments (the stars, the plants, the dotted ground line; John, 2026-10-10: kept): everything
    # but the figures (pieces of the figures' area over BIG) and the ink at or near them. On the vase they are
    # painted in clay on the black, so the dark theme shows them as clay shapes (the ink a px wider), their
    # lines in day mode only (`day`).
    # (sized with the pockets filled: a pocket can cut a figure's part off, as the horseman's horse's head)
    fl, _ = ndi.label(fig | pk)
    big = (np.bincount(fl.ravel()) >= BIG * UP * UP)[fl] & fig
    orn = (ink & (ndi.distance_transform_edt(~big) > NEAR * UP)) | (fig & ~big)
    orn = ndi.binary_fill_holes(ndi.binary_dilation(orn, structure=morphology.disk(UP)))
    fig = (big | orn) & ~pk                  # (the pockets stay ground in the ornaments too)
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), gl=gl.astype(np.uint8), ink=ink | hatch, lines=ink, hatch=hatch, fig=fig, reg=reg)
    # weighted and traced at TRACE_H tall, not the house 4000 px: this wide frieze is only 3150 work px tall,
    # and at 4000 the thin scrolls broke when the lines were thinned to WEIGHT
    lw.WORK_H = TRACE_H
    info = lw.trace_svg(
        ink, OUT, body=fig, open_holes=~fig, weight=WEIGHT, dots=hatch, trace_h=lw.WORK_H,
        day=ndi.binary_dilation(orn, iterations=UP), add_clay=orn, keep=kept,
        title='The Persian king fleeing',
        desc='Line drawing after the 1883 plate of an Apulian amphora in Naples (Heydemann, Hallisches Winckelmannsprogramm 8); cut out and retraced.')
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(g, OUT, info['box'], Path(qa))
        lw.qa_dark(OUT, info['box'], Path(qa).with_suffix('.dark.png'))


if __name__ == '__main__':
    main(*sys.argv[1:4])
