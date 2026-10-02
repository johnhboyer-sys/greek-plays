"""Euripides: Iphigenia, priestess of Artemis, handing her letter to Pylades
(Iphigenia in Tauris 727 ff.), from the 1849 lithograph of the Duke of
Buckingham's vase: Archäologische Zeitung 7 (1849), Denkmäler und
Forschungen Taf. XII (lith. R. Jaene). Internet Archive scan:
https://archive.org/download/archaologischez07deut/page/n156.jpg

Lithograph -> drawing, as for the Pythia (see pythia.py), except that the
lines are fine and grey, so ink is found by local contrast (ink_hairlines)
rather than one threshold; then a guided cut along her own lines (Pylades' hand on the tablet, the temple door
and steps behind her, Artemis' foot and the attendant's tray are left out),
then the house line weight and potrace.

    python3 docs/redesign/drawings/tools/iphigenia_tauris.py path/to/n156.jpg [overlay.png]
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "euripides-iphigenia.svg"

# Points on her outline in px of the plate scan, clockwise from the veil's top
# left corner; the guided path snaps them onto her own lines. The cut takes in
# the key's chain and knob. The tablet she and Pylades both hold is cut at its
# middle: this scan is too coarse to show where her fingers end and his begin.
OUTLINE = [
    (1208, 976), (1219, 966), (1234, 956), (1290, 948), (1346, 952), (1370, 972), (1394, 1012), (1401, 1040),
    (1406, 1076), (1402, 1108), (1414, 1132), (1426, 1164), (1422, 1204), (1434, 1244), (1454, 1284), (1474, 1332),
    (1494, 1348), (1510, 1364), (1516, 1392), (1530, 1402), (1545, 1400), (1558, 1410), (1557, 1430), (1540, 1435),
    (1527, 1428), (1525, 1450), (1526, 1540), (1526, 1620), (1518, 1640), (1516, 1690), (1505, 1698), (1488, 1690),
    (1486, 1650), (1490, 1632), (1496, 1600), (1497, 1540), (1497, 1460), (1499, 1425), (1426, 1380), (1430, 1460),
    (1418, 1492), (1402, 1508), (1406, 1588), (1414, 1660), (1434, 1684), (1438, 1700), (1402, 1704), (1386, 1688),
    (1314, 1668), (1282, 1680), (1242, 1688), (1194, 1684), (1186, 1668), (1170, 1652), (1178, 1580), (1190, 1508),
    (1166, 1440), (1183, 1462), (1154, 1348), (1178, 1316), (1210, 1236), (1170, 1252), (1138, 1252), (1112, 1258), (1101, 1242),
    (1103, 1214), (1128, 1206), (1170, 1228), (1210, 1212), (1234, 1164), (1226, 1140), (1210, 1100), (1206, 1036),
]
X0, Y0, X1, Y1 = 1040, 920, 1560, 1730  # working crop around her
F = 4


def main(src: str) -> None:
    g = np.asarray(Image.open(src).convert("L"), dtype=np.float32)
    ink = lw.ink_hairlines(g, size=9, t=16)
    soft = ndi.gaussian_filter(ink.astype(float), 1.5)
    cost = 1 + 30 * (1 - np.clip(soft * 2, 0, 1))
    path = lw.livewire(cost, OUTLINE, closed=True)
    ring = np.zeros_like(ink)
    ring[(path[:, 1] - 0.5).astype(int), (path[:, 0] - 0.5).astype(int)] = True
    keep = lw.polygon_mask(ink.shape, path) | ndi.binary_dilation(ring, iterations=2)

    crop = Image.fromarray(g[Y0:Y1, X0:X1].astype(np.uint8))
    g4 = np.asarray(crop.resize((crop.width * F, crop.height * F), Image.LANCZOS), dtype=np.float32)
    ink4 = lw.ink_hairlines(g4, size=9 * F, t=16)
    m = Image.fromarray(keep[Y0:Y1, X0:X1].astype(np.uint8) * 255)
    keep4 = np.asarray(m.resize((m.width * F, m.height * F), Image.NEAREST)) > 0
    fig = morphology.remove_small_objects(ink4 & ndi.binary_dilation(keep4, iterations=2), max_size=30)
    info = lw.trace_svg(
        fig, OUT,
        title="Iphigenia, priestess of Artemis, holding out a letter tablet and the temple key",
        desc="Line drawing after R. Jaene's 1849 lithograph of the Buckingham vase "
             "(Archäologische Zeitung 7, Taf. XII); cut out and retraced.")
    print(OUT, info)
    if len(sys.argv) > 2:
        rgb = np.stack([g] * 3, -1).astype(np.uint8)
        rgb[keep & ink] = (200, 0, 0)
        rgb[ring] = (0, 160, 0)
        Image.fromarray(rgb[Y0:Y1, X0:X1]).save(sys.argv[2])


if __name__ == "__main__":
    main(sys.argv[1])
