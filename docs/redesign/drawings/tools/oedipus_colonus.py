"""Oedipus at Colonus: blind Oedipus at the altar between his daughters,
Ismene (left) and Antigone (right), from the Apulian red-figure calyx-krater
close to the De Schulthess Painter, 340s BCE, Melbourne, Graham Geddes
collection A 5:8: Taplin, Pots & Plays (Getty, 2007) no. 27, plate p. 101.
The plate is the sharpest photo found: a 942x641 JPEG, page 112 of the Getty
PDF, credited there "From Green 2003, p. 4" (J. R. Green, Ancient Voices,
Modern Echoes, Nicholson Museum, Sydney, 2003). The drawing traces only the
ancient painting, which is public domain (John, 2026-10-02); the photo is
credited. John chose the three on the altar (2026-10-02); the columns and
tripods behind them are left out.
https://media.getty.edu/Text/6f3674dd-413a-56da-bec2-9da5564907df.pdf

    pdfimages -j -f 112 -l 112 6f3674dd-413a-56da-bec2-9da5564907df.pdf plate

A second photo, the whole vase in black and white (Digital LIMC, monument
8378, photo 8569X101, credit "Graham Geddes Collection (once)", CC BY-NC 4.0
on the LIMC site), was aligned to the plate and used to read shapes the plate
blurs (the arm border, the mantle ends); it is credited too. The tool itself
reads only the plate:
https://iiif.dasch.swiss/080E/39p0GV9AZiB-7HG3RtcJ3N4.jpx/full/max/0/default.png

Red-figure photo -> drawing, at 4x. The figures are small (Oedipus is about
360 px tall in the plate), so the crop is cleaned of JPEG noise and enlarged
4x (Lanczos) before anything is traced, as for the Pythia. The group is clay
and added white (the altar, his hair) on black glaze. Inside a loose cut
(OUTLINE) the ground is the glaze that reaches the cut, with the two white
columns (COLUMNS) counted as ground; black inside the figures (the
daughters' hair, the borders of Ismene's mantle) stays, drawn solid. Lines:
the group's outline; the edges between clay, white and black inside it
(figures against the altar, the altar's bands, hair, borders); and the
painted lines on the clay, found by local contrast. His hair and beard are
outlined, not filled. The staff is added yellow, drawn as a straight rod
(STAFF). Faces and hands are drawn stroke by stroke on their painted lines.

    python3 docs/redesign/drawings/tools/oedipus_colonus.py plate-001.jpg \
        mdp.39015060089391-seq_6.tif mdp.39015060089391-seq_28.tif mdp.39015060089391-seq_31.tif [qa.png]
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
from oedipus_syracuse import centre_lines, drawn, join_gaps, pen  # noqa: E402  (shared helpers; that file is not changed)

OUT = Path(__file__).resolve().parent.parent / "oedipus-coloneus.svg"
BOX = (196, 150, 734, 584)  # plate crop around the group; points below are plate (x, y)
F = 4                       # enlargement
BLACK_L, WHITE_B = 60, 110  # glaze is darker than BLACK_L; the added white bluer than WHITE_B
# The borders of Ismene's mantle are dark brown bands, some with dots or
# crenellations: inside BORDERS (her mantle, below her hair) brown darker than
# SOLID_L and wider than 1.5 px is drawn solid. Antigone's veil has brown fold
# lines as dark, which stay lines.
SOLID_L = 120
PEEL_L, PEEL_R = 88, 16  # the brown band at an outline: darker than PEEL_L, within PEEL_R working px of the ground
FACE_BAND = 10           # working px: how far inside FACE the hairline's curls may reach
EDGE_W = 4               # working px: the outline, as heavy as the painted lines inside it
JOHN_NEAR = 5            # working px: within this of the outline, John's strokes give way to it
BORDERS = [(222, 268), (388, 268), (388, 495), (222, 495)]

# The cut, clockwise from the foot of the altar's left end. Loose through the
# glaze (it drops out by colour) round Ismene, her two head ribbons, the three
# heads and Antigone's veil; tight where something else is clay or white:
# Polynices' cloak against Antigone's hem and the altar's corner (x 705), the
# white dots of the platter beside the altar's left end (x 231), and the
# orange ground line under the altar's foot (measured column by column).
OUTLINE = [(202.5, 568.5), (202, 560), (203, 549), (204.5, 547), (226.5, 545), (226.5, 541), (229.5, 530),
           (231.5, 520), (233, 510), (234.5, 500), (235.5, 485), (235.5, 470), (234.5, 455), (233, 449),
           (228, 422), (221, 411.5), (219, 405), (221, 390), (223, 370), (225, 340), (228, 315), (233, 295),
           (238, 280), (241, 262), (242, 245), (246, 228), (254, 205), (257, 175), (262, 159), (281, 156),
           (299, 159), (304, 172), (303, 190), (330, 194), (370, 194), (400, 198), (430, 205), (452, 205),
           (470, 204), (490, 209), (500, 222), (506, 230), (520, 230), (530, 210), (540, 200), (565, 200),
           (585, 203), (600, 202), (616, 204), (630, 211), (640, 228), (646, 250), (651, 280), (657, 315),
           (666, 345), (676, 365), (689, 380), (700, 389), (704.5, 395), (705.5, 400), (705.5, 410),
           (705, 420), (705, 432), (709, 440), (710, 470), (710, 500), (709, 530), (709, 539), (712, 541),
           (726, 541.5), (728, 545), (728.5, 560), (727.5, 571.5), (724, 571.8), (700, 572.1), (680, 572.1),
           (660, 575.1), (640, 577.1), (600, 577.1), (560, 578.1), (520, 577.1), (480, 577.1), (440, 578.1),
           (400, 578.7), (364, 578.1), (344, 578.7), (324, 577.1), (304, 575.7), (284, 573.1), (264, 570.1),
           (244, 568.1), (224, 567.1), (206, 569)]
# The columns behind the group, from the cut down to the altar's top (y 414)
# or, on the left, to the border of Ismene's mantle: their white is ground.
COLUMNS = [[(325, 188), (361, 188), (361, 296), (355.5, 313), (350, 319), (342, 320.5), (334, 319), (329.5, 313),
            (326, 300)],
           [(526, 188), (567, 188), (567, 414), (526, 414)]]
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
    [(465.7, 273.3), (465.8, 275.3)],  # the parting of the moustache, between the nose and the mouth
]
# His mouth, under the moustache (John, 2026-10-03: "the mouth and beard need
# more detail"): both photos show this dark line at y 277. Drawn at full line
# weight, with no curl stroke touching it.
MOUTH = [(459.8, 277.2), (462.0, 277.3), (464.0, 277.0), (466.3, 276.4), (467.2, 276.0)]
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

# The daughters' faces follow John's trace of them (2026-10-03), drawn over
# the plate in a review sheet and mapped back onto it: his screenshot was
# matched to the sheet by SIFT features (556 matches, mean error 0.05 plate
# px), and each stroke carried to plate px through the sheet's crop origins.
# Antigone faces front: the face a long oval down to the chin, the neck below
# it to the necklace; brows, eyes, nose with its nostril, mouth, chin. Ismene
# is in profile: the band of her hair over the brow (with its white ribs), the
# lock in front of her ear, the face and neck, the neckline of her dress. The
# areas his lines close in round each face and neck (FACE_SEEDS) are skin:
# no hair or other marks are drawn there. Where a stroke runs along the
# outline, the outline stands for it. A 2-px tick above Antigone's hairline
# is left out as a slip of the pen.
JOHN_ANTIGONE = [
    [(598.7, 230.3), (597.6, 230.7), (596.4, 231.4), (595.2, 232.3), (593.9, 233), (592.6, 233.2), (591.3, 232.9), (590, 232.5), (588.8, 232.5), (587.5, 232.7), (586.3, 233.3), (585.1, 233.9), (583.9, 234.8), (582.8, 235.7), (581.8, 236.8), (580.9, 238), (580.4, 239.2), (580.4, 240.5), (580.9, 241.7), (581.5, 243.1), (581.8, 244.5), (582.1, 245.9), (582.2, 247.3), (582.2, 248.8), (582.3, 250.2), (582.4, 251.7), (582.7, 253), (583.1, 254.3), (583.7, 255.6), (584.3, 256.8), (585, 258), (585.6, 259.3), (586.1, 260.6), (586.4, 261.9), (586.7, 263.3), (587.1, 264.6), (587.2, 265.3)],  # outline: the hairline, the left cheek, to the jaw
    [(598.7, 230.3), (599.2, 231.4), (599.6, 232.8), (600.1, 234.2), (600.9, 235.3), (602.1, 236), (603.6, 236.4), (605.1, 236.7), (606.6, 237.1), (607.7, 237.7), (608.5, 238.6), (609.2, 239.8), (609.6, 241.1), (609.8, 242.5), (610, 243.9), (610, 245.4), (610, 246.9), (610, 248.4), (609.9, 249.8), (609.8, 251.3), (609.7, 252.7), (609.6, 254.2), (609.5, 255.6), (609.3, 257.1), (609.3, 258.6), (609.3, 260.1), (609.6, 261.5), (610.1, 262.8), (610.9, 264), (611.7, 265.1), (612.2, 266.4), (612.3, 267.8), (612.3, 269.3), (612.2, 270.8), (612.3, 272.4), (612.2, 273.9), (612.1, 275.4), (611.7, 276.7), (611.1, 277.9), (610.3, 279), (609.3, 280), (608.2, 280.8), (607, 281.6), (605.7, 282.2), (604.3, 282.6), (602.9, 283), (601.5, 283.3), (600.1, 283.4), (598.7, 283.4), (597.2, 283.3), (595.8, 283.1), (594.4, 282.7), (593.1, 282.3), (591.8, 281.7), (590.6, 280.9), (589.6, 279.9), (588.8, 278.8), (588, 277.6), (587.1, 276.8), (585.8, 276.5)],  # outline: the hairline, the right cheek and the neck, to the necklace
    [(585.6, 276.4), (585.2, 275), (585, 273.6), (584.9, 272.1), (585.1, 270.6), (585.4, 269.2), (585.8, 267.8), (586.4, 266.6), (587.1, 265.4)],  # the neck's left edge
    [(587.2, 244.6), (585.7, 244.6), (584.1, 244.7), (583.4, 244.9)],  # left brow
    [(593.8, 245.4), (595.2, 245.3), (596.5, 245.3), (597.9, 245.4), (598.5, 245.6)],  # right brow
    [(590.1, 247), (589.8, 248.3), (589.5, 249.6), (589.2, 251), (589, 252.5), (588.8, 254.1), (588.7, 255.6), (588.8, 257), (589.3, 258.1), (590.4, 258.6), (592.1, 258.5)],  # nose, and its base
    [(592, 255.5), (592.3, 257), (592.8, 257.6)],  # nostril
    [(600.6, 270.2), (599.3, 270.2), (597.8, 270.3), (596.3, 270.5), (594.8, 270.5), (593.3, 270.4), (592, 270.1), (590.8, 269.6), (589.7, 268.8), (588.9, 267.7), (588.2, 266.4), (587.6, 265)],  # chin
]
JOHN_ISMENE = [
    [(297.2, 238.8), (297.7, 237.6), (298.6, 236.5), (299.6, 235.6), (300.7, 234.6), (301.5, 233.5), (302.1, 232.2), (302.4, 230.8), (302.5, 229.2), (302.4, 227.7), (302.3, 226.2), (301.9, 225), (301, 224), (299.9, 223.3), (298.6, 222.5), (297.4, 221.8), (296.4, 220.9), (295.5, 219.9), (295, 218.6), (294.8, 217.2), (294.5, 215.7), (293.9, 214.4), (292.9, 213.5), (291.8, 213.3), (290.6, 213.5), (289.4, 214.3), (288.2, 215.2), (287.1, 216.3), (285.9, 217.4), (284.8, 218.4), (283.8, 219.4), (282.7, 220.2), (281.6, 221), (280.4, 221.7), (279.2, 222.4), (278, 222.9), (276.6, 223.4), (275.1, 223.8)],
    [(278.8, 258.9), (279, 257.6), (279.2, 256.2), (279.3, 254.8), (279.3, 253.3), (279.1, 251.8), (279, 250.4), (279, 249), (279.4, 247.7), (280.2, 246.6), (281.1, 245.4), (282.1, 244.3), (282.9, 243.2), (283.5, 241.9), (284, 240.6), (284.4, 239.2), (284.8, 237.9), (285.2, 236.6), (285.8, 235.4), (286.5, 234.1), (287.4, 232.9), (288.3, 231.8), (289.4, 230.7), (290.5, 230), (291.8, 229.7), (293.1, 229.9), (294.1, 230.7), (294.6, 232), (294.5, 233.4), (294.2, 234.9), (293.9, 236.4), (294, 237.9), (294.3, 238.6)],
    [(297.4, 238.9), (295.8, 238.6), (295, 238.8)],
    [(279.8, 259.1), (280, 257.7), (280.5, 256.4), (281.2, 255.2), (282.1, 254), (282.9, 252.9), (283.7, 251.8), (284.5, 250.6), (285.2, 249.4), (285.8, 248.2), (286.3, 246.9), (286.8, 245.5), (287.3, 244.2), (287.9, 242.9), (288.6, 241.8), (289.4, 240.7), (290.4, 239.9), (291.7, 239.2), (293.4, 238.9), (294.3, 238.8)],
    [(299, 240.2), (298.2, 239.2), (297.5, 239)],
    [(297, 238.9), (297, 240.3), (297, 241.7), (296.9, 243.2), (296.9, 244.6), (296.9, 246.1), (296.9, 247.5), (296.9, 249), (297.1, 250.4), (297.3, 251.8), (297.6, 253.1), (298.1, 254.4), (298.6, 255.7), (299.3, 256.9), (300.2, 258)],
    [(290, 271.9), (291.3, 271.9), (292.8, 272), (294.4, 271.9), (295.8, 271.6), (296.9, 270.9), (297.7, 270), (298, 268.8), (297.8, 267.5), (297.2, 266.1), (296.8, 264.7), (296.7, 263.3), (297.1, 262), (297.9, 260.8), (298.9, 259.7), (300, 258.8), (300.5, 258.3)],
    [(279.2, 267.9), (279.2, 266.4), (279.2, 264.9), (279.2, 263.4), (279.2, 261.9), (279.3, 260.4), (279.3, 259)],
    [(279.2, 267.9), (278.4, 268.7), (278.4, 269.3)],
    [(277.4, 279.9), (277.2, 278.3), (277.2, 276.8), (277.5, 275.4), (278, 274), (278.5, 272.7), (279, 271.4), (279.4, 270), (279.6, 268.6), (279.6, 267.8)],
    [(290, 272.2), (290.1, 273.7), (290.1, 275.2), (290.5, 276.7), (290.9, 277.3)],
    [(290.9, 277.4), (292.4, 277.5), (293.7, 278.1), (294.9, 278.9), (296.1, 279.9), (297.2, 280.7)],
    [(290.8, 277.4), (290.4, 278.7), (290, 280), (289.5, 281.3), (288.9, 282.6), (288.3, 283.8), (287.5, 285), (286.7, 286.1), (285.6, 287.1), (284.4, 288), (283.1, 288.7), (281.7, 289.1), (280.3, 289.2), (278.9, 289), (277.9, 288.3), (277.6, 286.9)],
    [(277.3, 279.8), (276.8, 281.3), (276.9, 282.6), (277.4, 283.9), (277.6, 285.2), (277.6, 285.8)],
    [(297.2, 280.8), (298.5, 281.1), (299.8, 281.6), (301.1, 282.1), (302.4, 282.6), (303.6, 283), (304.9, 283.4), (305.5, 283.6)],
    [(277.1, 296), (278.4, 295.7), (279.9, 295.5), (281.3, 295.4), (282.8, 295.3), (284.3, 295.3), (285.8, 295.1), (287, 294.6), (288, 293.8), (289, 292.8), (289.9, 291.7), (290.8, 290.6), (291.7, 289.5), (292.7, 288.4), (293.7, 287.4), (294.7, 286.4), (295.6, 285.4), (296.3, 284.3), (296.7, 282.9), (296.8, 281.4), (296.9, 280.7)],
    [(299.2, 283.3), (299.4, 284.8), (299.5, 286.2), (299.4, 287.7), (299.3, 289.2), (299, 290.6), (298.7, 292), (298.3, 293.4), (297.7, 294.7), (297.1, 296), (296.4, 297.2), (295.6, 298.3), (294.7, 299.4), (293.7, 300.4), (292.6, 301.3), (291.4, 302), (290.2, 302.7), (288.9, 303.3), (287.5, 303.7), (286, 304), (284.6, 304.2), (283.1, 304.3), (281.6, 304.3), (280.1, 304.2), (278.8, 303.9), (277.7, 303.2), (277.1, 301.9), (276.8, 300.4), (276.8, 298.9), (276.9, 297.4), (276.8, 295.9)],
    [(276.8, 286.4), (277.5, 285.9)],
    [(277.8, 286.7), (277.5, 285.9)],
    [(276.8, 295.8), (276.9, 294.3), (276.7, 292.9), (276.4, 291.4), (276.2, 290), (276.1, 288.5), (276.4, 287), (276.8, 286.3)],
    [(276.8, 286.4), (277.7, 286.8)],
]
# Antigone's eyes and mouth, redrawn after John's review of his trace
# (2026-10-03: "her eyes need adjusted", "I think she's smiling"), each placed
# on the marks the plate and the LIMC photo share: both eyes almonds with
# solid pupils (the near one a dark oval in both photos, the far one at the
# cheek's edge, moved in off her hair), and the mouth a short line whose ends
# rise a little.
ANTIGONE_FEATURES = [
    [(594.2, 248.9), (595.6, 248.1), (597.3, 247.7), (599.0, 247.9), (600.5, 248.6)],  # near eye, upper lid
    [(594.6, 249.3), (595.9, 250.3), (597.4, 250.8), (598.9, 250.4), (600.1, 249.2)],  # lower lid
    [(584.05, 248.85), (584.98, 248.15), (586.03, 247.95), (587.09, 248.35), (587.95, 249.15)],  # far eye, upper lid
    [(584.3, 249.45), (585.04, 250.65), (585.97, 251.05), (586.9, 250.55), (587.71, 249.55)],  # lower lid
    # (the near eye mirrored and narrowed to 0.62, as a farther eye is foreshortened, so that it fits the
    # 6.75 px between her hair and the nose line of John's trace without touching either; the paint puts
    # it about 1.5 px further left, against the hair, where it read as a dash; John, 2026-10-03: "Other
    # eye too")
    [(589.9, 262.3), (591.6, 263.1), (593.5, 263.4), (595.4, 263.1), (597.1, 262.2)],  # mouth, smiling
]
JOHN_EYES = [(586.0, 249.6, 0.6), (597.4, 249.3, 1.05)]  # Antigone's pupils: solid dots, (x, y, radius) in plate px
FACE_SEEDS = [(596, 252), (596, 277), (289, 251)]  # Antigone's face and neck; Ismene's face and neck
# Ismene's face marks, which his trace leaves to the painting: each stroke on
# a painted mark measured by local contrast.
FACE_MARKS = [
    [(287.0, 247.3), (289.0, 246.8), (291.6, 247.0)],  # brow
    [(287.8, 251.3), (289.5, 251.0), (291.8, 251.1)],  # eye
    [(293.6, 258.5), (295.0, 259.0), (296.2, 259.3)],  # nostril
    [(291.6, 262.3), (293.4, 263.2), (295.6, 264.8)],  # mouth
]
PUPILS = [(289.4, 251.1)]  # Ismene's pupil, a solid dot 1.6 plate px across
# Antigone's right hand at her chin, the fingers curled up towards it: the
# painted lines between the fingers, each finger closed at its tip.
ANTIGONE_HAND = [(577, 280), (600, 279), (602, 296), (594, 313), (588, 313), (577, 303)]
ANTIGONE_HAND_LINES = [
    [(580.6, 282.8), (580.3, 287.0), (579.6, 291.0), (579.0, 294.5), (578.5, 298.0), (578.2, 302.0)],  # outer edge
    [(584.4, 282.6), (584.1, 286.0), (583.4, 289.0), (583.1, 292.0), (583.0, 294.5)],
    [(587.4, 283.4), (587.1, 287.0), (586.8, 290.0), (586.3, 292.5), (586.0, 295.0)],
    [(591.6, 283.6), (591.2, 285.5), (590.6, 287.2)],
    [(596.0, 282.8), (594.3, 287.2), (592.5, 289.6), (590.6, 292.3), (589.3, 294.8)],
    [(580.6, 282.8), (581.8, 281.6), (583.3, 281.7), (584.4, 282.6)],  # the fingertips
    [(584.4, 282.6), (585.6, 281.9), (586.8, 282.3), (587.4, 283.4)],
    [(587.4, 283.4), (589.0, 282.2), (590.7, 282.6), (591.6, 283.6)],
    [(591.6, 283.6), (593.3, 281.9), (595.0, 281.9), (596.0, 282.8)],
    [(592.3, 296.0), (591.8, 300.0), (591.6, 304.0), (591.3, 308.0), (590.6, 312.0)],  # the wrist's inner edge
    [(600.2, 288.0), (599.2, 290.5), (598.2, 293.0)],  # the thumb
]
# The end of Antigone's veil hangs below her left arm in a column of S-shaped
# folds (both photos agree; LIMC's photo, aligned to the plate by ECC, shows
# them cleaner). Their lines are dark enough to fill solid and close enough
# to merge, so inside VEIL_END they are redrawn along the centres of the
# painted lines (STROKE_T: local-contrast hysteresis).
VEIL_END = [(567.5, 358), (588, 360), (595, 376), (596, 396), (567.5, 396)]
STROKE_T = (16, 32)
# The dark border along Ismene's arm, under the left column, measured in both
# photos: its centre runs from (332, 326) to (363, 314.5), about 5 px wide.
ARM_BAND = [(326, 321), (336, 321.5), (344, 319.3), (352, 316.5), (360, 311.5), (364, 309.5),
            (364, 319.5), (360, 320.5), (352, 325.5), (344, 328.3), (336, 330.5), (326, 331)]
# The hanging end of Ismene's mantle, by her raised hand, is a stack of the
# same folds; drawn the same way.
ISMENE_END = [(344, 334), (369, 334), (371, 360), (369, 395), (367, 412), (344, 412)]
# The daughters' hair is dark brown, a shade between the clay and the black
# ground, so inside HAIRS the ground is only the true black (below GROUND_L).
# Antigone's curls, and Ismene's crown and long lock, are drawn solid (as the
# Syracuse hair was), with the white beads and the larger clay curls in them
# left as holes. Ismene's is lighter, brown with pale curls, so its threshold
# is lower and fewer gaps are closed, which keeps the curls of her bun.
ISMENE_HAIR = [(242, 228), (256, 222), (268, 222), (280, 218), (292, 213), (302, 216), (304, 224), (302, 234),
               (299, 240), (294, 243), (289, 249), (286, 255), (284, 262), (283.5, 268), (283, 275),
               (282, 290), (281, 304), (270, 304), (266, 290), (262, 275), (254, 270), (245, 266), (240, 255),
               (240, 240)]
ANTIGONE_HAIR = [(572, 232), (576, 224), (586, 219), (600, 217), (612, 220), (620, 228), (623, 240), (622, 255),
                 (618, 270), (617, 288), (609, 288), (608, 270), (608, 255), (607, 245), (604, 237), (597, 234.5),
                 (590, 235), (585, 238), (583, 246), (582.5, 255), (583, 270), (583, 288), (576, 288), (575, 270),
                 (572, 258), (570, 245)]
HAIRS = [ISMENE_HAIR, ANTIGONE_HAIR]
HAIR_DARK_L, GROUND_L = (100, 115), 40  # hair darker than HAIR_DARK_L (Ismene's, Antigone's) is solid
LINE_W = 5  # working px: strokes drawn by hand, as wide as the painted lines found (their median)
FINE_W = 3  # faces and fingers, whose marks lie closer together
# Curls of his hair and beard: strokes of the white brighter than their
# surroundings by CURL_LOC (blue channel), each drawn as one stroke at least
# CURL_MIN px long. A fixed threshold found too few in the beard, whose white
# is dimmer (John, 2026-10-03: the beard needs more detail).
CURL_LOC, CURL_MIN = 7, 12
RIDGE_T, RIDGE_MIN = (3.0, 6.0), 24  # faint folds: Sato ridge hysteresis thresholds, and least length in px
# A thin grey line across the black ground between his beard and his raised
# hand, probably a scratch: left out with the ground.
SCRATCH = [(486, 270.5), (505.5, 271), (506, 275.5), (486, 275)]


def P(pts):
    """Plate (x, y) points -> working px of the 4x crop."""
    return [((x - BOX[0]) * F, (y - BOX[1]) * F) for x, y in pts]


def poly(shape, pts):
    return lw.polygon_mask(shape, np.array(P(pts), float))


def smooth_poly(shape, pts):
    """A closed shape through the points as a smooth curve, not a polygon."""
    from scipy.interpolate import splprep, splev
    q = np.array(P(pts) + P(pts[:1]), float).T
    tck, _ = splprep(q, k=3, s=0, per=1)
    x, y = splev(np.linspace(0, 1, 40 * len(pts)), tck)
    return lw.polygon_mask(shape, np.stack([x, y], 1))


def load(src):
    """The plate's crop, cleaned of JPEG noise and enlarged F times: the frame
    every point in this file is placed in, and the colours every threshold
    was set on."""
    a = np.asarray(Image.open(src).convert("RGB"))
    a = cv2.fastNlMeansDenoisingColored(a[:, :, ::-1].copy(), None, 3, 3, 5, 15)[:, :, ::-1]
    c = Image.fromarray(a).crop(BOX)
    c = c.resize((c.width * F, c.height * F), Image.LANCZOS)
    return np.asarray(c, dtype=np.float32)


# ---------------------------------------------------------------- Green's pages
# The photos drawn from are three pages of Green 2003 (HathiTrust
# mdp.39015060089391, seq 6, 28 and 31), downloaded by John (2026-10-03):
# p. 4, the whole vase (1.8x the plate's scale); p. 26, the right half of the
# scene (6.4x); p. 29, Oedipus's head and hand (12.8x). The two details are
# registered to the plate, warped into the working frame, colour-matched to
# the plate (so the thresholds above still hold), and laid over it: p. 29 over
# p. 26, feathered at the seams. p. 4 serves only to register p. 26: as
# pixels it gave Ismene no more than the plate, and its print noise traced as
# wiggles, so she and the altar's left end stay drawn from the plate. The
# plate stays the frame: every hand-placed point, John's traces included, is
# in its px. Per detail page: the photo's area in page px (the rest is paper,
# text or the scanner's watermark) and the blur against the print's dots.
PAGES = [("p26", (0, 0, 2410, 3290), 1.5), ("p29", (128, 1, 1761, 1962), 1.8)]
PAGE_FILES = ["p4", "p26", "p29"]  # the order of the page files on the command line
# Each link of the chain: (from, to, scale of from, scale of to, RANSAC px in
# the target page, spline smoothing). p. 26 is matched to p. 4 and p. 29 to
# p. 26, sharper partners than the plate.
CHAIN = [("plate", "p4", 2.0, 1.0, 3.0, 2000.0), ("p4", "p26", 2.0, 0.55, 6.0, 4000.0),
         ("p26", "p29", 0.55, 0.35, 8.0, 4000.0)]
SEAM = 24  # working px over which a sharper page fades in


def sift_matches(A, B, sa, sb, ratio=0.8):
    """SIFT matches between greyscale A and B, found at scales sa and sb;
    returned in each image's own px."""
    cv2.setRNGSeed(0)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    rs = lambda im, s: cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_LANCZOS4)
    sift = cv2.SIFT_create(nfeatures=40000, contrastThreshold=0.015)
    ka, da = sift.detectAndCompute(clahe.apply(rs(A, sa)), None)
    kb, db = sift.detectAndCompute(clahe.apply(rs(B, sb)), None)
    good = [m for m, n in cv2.BFMatcher(cv2.NORM_L2).knnMatch(da, db, k=2) if m.distance < ratio * n.distance]
    pa = np.float64([ka[g.queryIdx].pt for g in good]) / sa
    pb = np.float64([kb[g.trainIdx].pt for g in good]) / sb
    return pa, pb


class Mapping:
    """Points of one image to another: a RANSAC homography, with what it
    leaves taken up by a smooth thin-plate spline fitted on the matches (a
    page's photo is not the plate's: the vase is curved, the camera moved).
    Matches far off their neighbours' residual are dropped first."""

    def __init__(self, pa, pb, ransac_px, smoothing):
        from scipy.interpolate import RBFInterpolator
        from scipy.spatial import cKDTree
        cv2.setRNGSeed(0)
        H, inl = cv2.findHomography(pa.astype(np.float32), pb.astype(np.float32), cv2.RANSAC, ransac_px,
                                    maxIters=50000)
        inl = inl.ravel().astype(bool)
        self.H, P, Q = H, pa[inl], pb[inl]
        R = Q - self._h(P)
        tree, keep = cKDTree(P), np.ones(len(P), bool)
        for i, p in enumerate(P):
            idx = tree.query_ball_point(p, max(30.0, 0.05 * np.ptp(P[:, 0])))
            if len(idx) >= 5:
                med = np.median(R[idx], axis=0)
                spread = np.median(np.hypot(*(R[idx] - med).T))
                keep[i] = np.hypot(*(R[i] - med)) < 2.5 * max(1.0, spread)
        self.P, self.Q = P[keep], Q[keep]
        self.tps = RBFInterpolator(self.P, R[keep], kernel="thin_plate_spline", smoothing=smoothing, degree=1)
        self.error = float(np.median(np.hypot(*(self.Q - self(self.P)).T)))

    def _h(self, P):
        return cv2.perspectiveTransform(np.asarray(P, np.float64).reshape(1, -1, 2), self.H)[0]

    def __call__(self, P):
        P = np.asarray(P, np.float64).reshape(-1, 2)
        return self._h(P) + self.tps(P)


def warp_into_frame(img, mapping, shape, grid=8):
    """img sampled at the plate px of each working px (the mapping taken on a
    grid every `grid` px, interpolated between); and where it covers."""
    h, w = shape
    gx, gy = np.arange(0, w + grid, grid), np.arange(0, h + grid, grid)
    GX, GY = np.meshgrid(gx, gy)
    Q = mapping(np.c_[BOX[0] + GX.ravel() / F, BOX[1] + GY.ravel() / F])
    full = (gx[-1] + 1, gy[-1] + 1)
    mx = cv2.resize(Q[:, 0].reshape(GX.shape).astype(np.float32), full, interpolation=cv2.INTER_LINEAR)[:h, :w]
    my = cv2.resize(Q[:, 1].reshape(GX.shape).astype(np.float32), full, interpolation=cv2.INTER_LINEAR)[:h, :w]
    out = cv2.remap(img, mx, my, cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return out


def colour_match(src, ref, valid, s=6.0, n=300000):
    """src's colours mapped to ref's by a cubic in R, G, B, fitted on blurred
    pixel pairs (the blur hides detail the plate lacks and small misfits)."""
    def feats(x):
        r, g, b = x[..., 0] / 255, x[..., 1] / 255, x[..., 2] / 255
        return np.stack([np.ones_like(r), r, g, b, r * r, g * g, b * b, r * g, r * b, g * b, r ** 3, g ** 3, b ** 3], -1)
    A = np.stack([ndi.gaussian_filter(src[..., c], s) for c in range(3)], -1)
    B = np.stack([ndi.gaussian_filter(ref[..., c], s) for c in range(3)], -1)
    ys, xs = np.nonzero(ndi.binary_erosion(valid, iterations=int(3 * s)))
    i = np.random.default_rng(0).choice(len(ys), min(n, len(ys)), replace=False)
    coef, *_ = np.linalg.lstsq(feats(A[ys[i], xs[i]]), B[ys[i], xs[i]], rcond=None)
    return np.clip(feats(src) @ coef, 0, 255).astype(np.float32)


def load_green(plate_src, page_srcs):
    """The working frame drawn from Green's pages (see PAGES)."""
    ref = load(plate_src)
    shape = ref.shape[:2]
    grey = {"plate": np.asarray(Image.open(plate_src).convert("L"))}
    rgb = {}
    for name, src in zip(PAGE_FILES, page_srcs):
        rgb[name] = np.asarray(Image.open(src).convert("RGB"))
        grey[name] = cv2.cvtColor(rgb[name], cv2.COLOR_RGB2GRAY)
    maps, chain = {}, {"plate": lambda P: np.asarray(P, np.float64).reshape(-1, 2)}
    for a, b, sa, sb, rpx, smooth in CHAIN:
        m = Mapping(*sift_matches(grey[a], grey[b], sa, sb), rpx, smooth)
        print(f"  {a} -> {b}: {len(m.P)} matches, error {m.error:.2f} px of {b}")
        chain[b] = (lambda f, g: (lambda P: g(f(P))))(chain[a], m)
    out = ref.copy()
    for name, (x0, y0, x1, y1), blur in PAGES:
        im = cv2.GaussianBlur(rgb[name], (0, 0), blur)
        photo = np.zeros(im.shape[:2], np.float32)
        photo[y0:y1, x0:x1] = 1
        warped = warp_into_frame(np.dstack([im.astype(np.float32), photo]), chain[name], shape)
        valid = warped[..., 3] > 0.99
        page = colour_match(warped[..., :3], ref, valid)
        wgt = np.clip(ndi.distance_transform_edt(valid) / SEAM, 0, 1)[..., None]
        out = out * (1 - wgt) + page * wgt
    return out.astype(np.float32)


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


def ridge_lines(L, inside, avoid, w, min_len=RIDGE_MIN):
    """Faint folds the local-contrast pass misses, found as dark ridges (a Sato
    filter, sigmas 1.5-3.5): inside `inside`, away from `avoid`, at least
    min_len px long, each drawn as a smooth stroke along its centre."""
    from scipy.interpolate import splprep, splev
    from skimage import filters
    r = filters.sato(ndi.gaussian_filter(L, 0.8), sigmas=[1.5, 2.5, 3.5], black_ridges=True)
    cand = filters.apply_hysteresis_threshold(r, *RIDGE_T) & inside & ~avoid
    sk = morphology.skeletonize(cand)
    out = np.zeros(L.shape, bool)
    for path in curl_strokes(sk, min_len):
        q = np.array(path, float)
        q = q[np.r_[True, np.any(np.diff(q, axis=0) != 0, axis=1)]]
        if len(q) < 2:
            continue
        tck, _ = splprep(q.T, k=min(3, len(q) - 1), s=0.6 * len(q))
        x, y = splev(np.linspace(0, 1, 9 * len(q)), tck)
        out[np.clip(np.round(y).astype(int), 0, L.shape[0] - 1), np.clip(np.round(x).astype(int), 0, L.shape[1] - 1)] = True
    return ndi.distance_transform_edt(~out) <= w / 2


def centre_strokes(gL, zone, w, thresholds=STROKE_T, min_len=14):
    """The painted lines inside zone redrawn w px wide along their centres,
    every branch kept (local contrast, hysteresis; spurs under 6 px and
    pieces under min_len px dropped; pixel steps softened)."""
    from skimage.filters import apply_hysteresis_threshold
    th = ndi.grey_closing(gL, size=(13, 13)) - gL
    m = apply_hysteresis_threshold(th, *thresholds) & zone
    m = ndi.binary_closing(m, structure=morphology.disk(2)) & zone
    sk, _ = centre_lines(m, spur=6, min_len=min_len)
    sk = morphology.skeletonize(ndi.gaussian_filter(sk.astype(float), 1.5) > 0.12)
    return ndi.distance_transform_edt(~sk) <= w / 2


def main(plate_src: str, page_srcs: list) -> None:
    a = load_green(plate_src, page_srcs)
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    L = 0.2126 * R + 0.7152 * G + 0.0722 * B
    shape = L.shape
    inside = poly(shape, OUTLINE)
    gL = ndi.gaussian_filter(L, 1.0)
    hair_zones = poly(shape, HAIRS[0]) | poly(shape, HAIRS[1])
    # the dark brown of the daughters' hair is not ground: there only the true black is
    black = np.where(hair_zones, gL < GROUND_L, gL < BLACK_L)
    white = ndi.gaussian_filter(B, 1.0) > WHITE_B
    columns = poly(shape, COLUMNS[0]) | poly(shape, COLUMNS[1])
    staff, _, _ = rod(shape, STAFF, STAFF_W)

    # the ground: the glaze and the columns' white wherever they reach the
    # cut; everything else inside the cut is the group. The dark border along
    # Ismene's arm touches the left column; inside ARM_BAND it stays hers.
    orange = (ndi.gaussian_filter(G, 1.0) < 0.75 * ndi.gaussian_filter(R, 1.0)) & ~black & ~white
    rim = inside & ~ndi.binary_erosion(inside, iterations=2)

    def reaching(m):
        lab, _ = ndi.label(m)
        reach = np.unique(lab[rim & m])
        return np.isin(lab, reach[reach > 0])
    ground0 = reaching(inside & (black | (columns & ~orange) | poly(shape, SCRATCH)) & ~poly(shape, ARM_BAND))
    glaze = ground0 & black
    # The plate's blur leaves a brown band between a figure and the glaze,
    # which would trace as a second line just inside the outline: dark pixels
    # within PEEL_R px of the glaze, and joined to it, are ground too, so the
    # outline falls where the clay begins (about halfway between clay and
    # glaze). Not in the daughters' hair, which is as dark, nor in the
    # zigzag ends of the two mantles, whose folds run along the outline.
    ends = poly(shape, VEIL_END) | poly(shape, ISMENE_END)
    band = inside & (gL < PEEL_L) & (ndi.distance_transform_edt(~glaze) <= PEEL_R) & ~hair_zones & ~ends
    lab, _ = ndi.label(ground0 | band)
    reach = np.unique(lab[ground0])
    ground = np.isin(lab, reach[reach > 0])
    sil = ndi.binary_opening(inside & ~ground, structure=morphology.disk(2)) | staff
    sil = ndi.binary_fill_holes(morphology.remove_small_objects(sil, max_size=4000))
    sil = ndi.gaussian_filter(sil.astype(float), 1.0) > 0.5
    edge = sil & ~ndi.binary_erosion(sil, structure=morphology.disk(EDGE_W))

    # Oedipus' hair and beard: the yellower white inside HEAD_ZONE, one smooth mass
    head_zone = poly(shape, HEAD_ZONE)
    ratio = ndi.gaussian_filter(G, 1.5) / np.maximum(ndi.gaussian_filter(R, 1.5), 1)
    hair = (ratio > HAIR_GR) & ~black & head_zone
    hair = ndi.binary_closing(ndi.binary_opening(hair, structure=morphology.disk(2)), structure=morphology.disk(4))
    hair = morphology.remove_small_holes(morphology.remove_small_objects(hair, max_size=300), max_size=150)
    # the face is cut out of it, but its edge follows the curls of the
    # hairline within a band FACE_BAND px inside FACE
    face_core = ndi.binary_erosion(smooth_poly(shape, FACE), structure=morphology.disk(FACE_BAND))
    hair = (ndi.gaussian_filter(hair.astype(float), 2.0) > 0.5) & ~face_core

    # inside the group: clay, white and black. Black (hair, borders) is drawn
    # solid; where white meets a broad area of clay (a figure on the altar) the
    # edge is drawn; thin clay on the white (the altar's bands) is a painted
    # line, found below with the rest
    hand_zone = poly(shape, HAND)
    # John's strokes, and the skin they close in round each face
    john = drawn(shape, [P(s_) for s_ in JOHN_ANTIGONE + JOHN_ISMENE], FINE_W)
    regions, _ = ndi.label(ndi.binary_fill_holes(john) & ~john)
    seeds = [regions[int(round(y))][int(round(x))] for x, y in P(FACE_SEEDS)]
    face_zones = ndi.binary_dilation(np.isin(regions, [k for k in seeds if k]), iterations=2) & ~john
    ant_hand_zone = poly(shape, ANTIGONE_HAND)
    drawn_zone = head_zone | hand_zone | face_zones | ant_hand_zone | hair_zones | ends
    core = ndi.binary_erosion(sil, structure=morphology.disk(5))
    solid = ndi.binary_opening(black & core, structure=morphology.disk(2))
    solid |= ndi.binary_opening((gL < SOLID_L) & core & poly(shape, BORDERS) & ~ends, structure=morphology.disk(3))
    solid = morphology.remove_small_objects(solid & ~drawn_zone, max_size=60)
    solid = ndi.gaussian_filter(solid.astype(float), 1.0) > 0.5
    clay = sil & ~white & ~black
    broad = ndi.binary_opening(clay, structure=morphology.disk(6))
    whites = ndi.binary_opening(white & sil, structure=morphology.disk(1))
    meet = whites & ndi.binary_dilation(broad, iterations=2) | broad & ndi.binary_dilation(whites, iterations=2)
    meet &= ~drawn_zone & ~ndi.binary_dilation(staff, iterations=2)
    meet = pen(meet, LINE_W)

    # painted lines, dots and bands by local contrast, kept as the painter made
    # them (a bead stays a dot); thinned by the blur the enlargement adds, with
    # their centre lines kept so faint stretches stay joined. The head, the hand
    # and the staff are drawn below
    lines = lw.ink_lines(L, size=15, low=10, high=22, sigma=1.0)
    lines = ndi.binary_erosion(lines) | morphology.skeletonize(lines)
    lines &= ndi.binary_erosion(sil, structure=morphology.disk(3)) & ~solid
    lines &= ~(drawn_zone | ndi.binary_dilation(staff, iterations=2))
    lines = morphology.remove_small_objects(lines, max_size=30)

    # the head: the mass outlined, curls as single strokes along the brightest white
    hair_edge = hair & ~ndi.binary_erosion(hair, structure=morphology.disk(2))
    hair_edge &= ndi.binary_erosion(sil, structure=morphology.disk(5))  # its outer edge is the outline
    gB = ndi.gaussian_filter(B, 1.2)
    core = (gB - ndi.gaussian_filter(gB, 6) > CURL_LOC) & ndi.binary_erosion(hair, iterations=2) & (gB > 70)
    core = ndi.binary_opening(core, structure=morphology.disk(1))
    curls = drawn(shape, curl_strokes(core, CURL_MIN), FINE_W)
    mouth = drawn(shape, [P(MOUTH)], LINE_W)
    lab, n = ndi.label(curls)
    near_mouth = np.unique(lab[ndi.binary_dilation(mouth, iterations=2) & curls])
    curls &= ~np.isin(lab, near_mouth[near_mouth > 0])

    # the hand: only its strokes; the clay under them fills the closed fingers
    hand = drawn(shape, [P(s_) for s_ in HAND_LINES], FINE_W)
    edge &= ~hand_zone
    sil = (sil & ~hand_zone) | (ndi.binary_fill_holes(hand | (sil & ~hand_zone)) & hand_zone)

    # the daughters' hair: solid where it is dark, with beads and clay curls as
    # holes; Ismene's lighter bun keeps the painted lines found in it
    dark_hair = np.zeros(shape, bool)
    for zone_pts, thr, close, holes in ((ISMENE_HAIR, HAIR_DARK_L[0], 1, 12), (ANTIGONE_HAIR, HAIR_DARK_L[1], 2, 40)):
        zone = poly(shape, zone_pts)
        m = zone & sil & (gL < thr) & ~face_zones
        m = ndi.binary_closing(m, structure=morphology.disk(close)) & zone
        dark_hair |= morphology.remove_small_objects(morphology.remove_small_holes(m, max_size=holes), max_size=30)
    dark_hair = ndi.gaussian_filter(dark_hair.astype(float), 1.0) > 0.5
    bun = lw.ink_lines(L, size=15, low=10, high=22, sigma=1.0) & hair_zones & ~dark_hair & ~face_zones
    bun = morphology.remove_small_objects(ndi.binary_erosion(bun) | morphology.skeletonize(bun), max_size=30)

    marks = drawn(shape, [P(s_) for s_ in FACE_MARKS + ANTIGONE_FEATURES + ANTIGONE_HAND_LINES], FINE_W)
    Y, X = np.ogrid[0:shape[0], 0:shape[1]]
    for x, y, r in [(x, y, 0.8) for x, y in PUPILS] + JOHN_EYES:
        (px, py), = P([(x, y)])
        marks |= (X - px) ** 2 + (Y - py) ** 2 <= (r * F) ** 2
    # his strokes, except where the outline already runs; painted marks right
    # beside them give way
    marks |= john & ~ndi.binary_dilation(edge, iterations=JOHN_NEAR)
    lines &= ~ndi.binary_dilation(john, iterations=JOHN_NEAR)

    lines |= edge | solid | meet | hair_edge | curls | mouth | hand | dark_hair | bun | marks
    lines |= centre_strokes(gL, ends & ndi.binary_erosion(sil, structure=morphology.disk(3)), LINE_W)
    lines |= drawn(shape, [P(s_) for s_ in FACE_LINES], FINE_W)
    lines |= staff_lines(shape)
    # faint folds, then lines broken into dashes by wear joined where two ends face each other
    keep_out = ~ndi.binary_erosion(sil, structure=morphology.disk(6)) | drawn_zone | ndi.binary_dilation(staff, iterations=3)
    lines |= ridge_lines(L, ~keep_out, ndi.binary_dilation(lines, iterations=4), FINE_W)
    lines |= join_gaps(lines & ~keep_out & ~solid, keep_out | solid, max_gap=24)

    if "--masks" in sys.argv:  # diagnostic: the masks over the photo
        g = L * 0.55
        rgb = np.stack([g, g, g], -1)
        rgb[sil] = rgb[sil] * 0.5 + np.array([255, 60, 60]) * 0.5
        rgb[solid] = (40, 40, 255)
        rim = inside & ~ndi.binary_erosion(inside, iterations=2)
        rgb[rim] = (255, 255, 0)
        Image.fromarray(rgb.astype(np.uint8)).save(sys.argv[5])
        return

    info = lw.trace_svg(
        lines, OUT, body=sil,
        title="Blind Oedipus seated at an altar between his daughters, Ismene and Antigone",
        desc="Line drawing after the Apulian red-figure calyx-krater close to the De Schulthess Painter, "
             "340s BCE, Melbourne, Geddes collection A 5:8, read as a scene from Sophocles' Oedipus at "
             "Colonus (Taplin, Pots & Plays no. 27); traced from the plate in Pots & Plays: cut out, "
             "columns left out, redrawn as line.")
    print(OUT, info)
    if len(sys.argv) > 5:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(L, OUT, info["box"], Path(sys.argv[5]))
        lw.qa_dark(OUT, info["box"], Path(sys.argv[5]).with_suffix(".dark.png"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:5])
