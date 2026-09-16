"""Turn pairing as a global affine alignment.

Replaces the name-LCS objective (``stage1_turn_english._pair_turns``, deleted)
with a minimum-cost monotone alignment between Greek speaker-share nodes and
English speech nodes, following
``build/review/turn-pairing-design-2026-09-15.md`` section 3 (the DP shape,
Gotoh three-layer affine gaps) and section 7 (this module's contract). The
design's banded variant was removed in round 9: its completeness test was not
sound and the full matrix is inside the per-play budget (`_region_align`).

Pure: no I/O, no manifest knowledge, no knowledge of segments or slots. The
caller (``stage1_turn_english.py``) builds ``GreekNode``/``EnglishNode`` lists
from its own data and reads the result back into its own report shape.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

INF = float("inf")

# The speaker name a scanned bench column carries when the OCR could not read
# its printed cue. `stage1_turn_english` puts this sentinel on the speech (a
# sentinel, not `None`, so the reader shows the speech unattributed rather
# than crediting "WOU"), and design 3.2 prices it like an unattributed
# speech -- `S = 0.35`, not the 1.0 of two names that genuinely differ.
OCR_JUNK = "\x00ocr-junk"

_WORD = re.compile(r"[A-Za-z]+")
_CAP_WORD = re.compile(r"[A-Z][a-z]+")
_GREEK_CAP_RUN = re.compile(r"[Α-Ω][α-ωΑ-Ω]*")  # tokens STARTING capitalised

# Transliteration folds (design 3.2, term A): romanize the Greek run's
# capitalised-looking token, fold the usual digraphs, take a 3-letter stem.
_DIGRAPHS = [
    ("ει", "i"), ("αι", "e"), ("οι", "e"), ("ου", "u"),
    ("θ", "t"), ("φ", "f"), ("χ", "c"), ("ψ", "ps"),
    ("β", "b"), ("γ", "g"), ("δ", "d"), ("ζ", "z"), ("κ", "c"),
    ("λ", "l"), ("μ", "m"), ("ν", "n"), ("ξ", "x"), ("π", "p"),
    ("ρ", "r"), ("σ", "s"), ("ς", "s"), ("τ", "t"), ("υ", "u"),
    ("ω", "o"), ("ο", "o"), ("ε", "e"), ("η", "e"), ("ι", "i"),
    ("α", "a"),
]


def _translit_stem(token: str) -> str:
    t = token.lower()
    for grc, lat in _DIGRAPHS:
        t = t.replace(grc, lat)
    return t[:3]


def _anchor_stems(greek_text: str) -> set[str]:
    return {_translit_stem(w) for w in _GREEK_CAP_RUN.findall(greek_text) if len(w) >= 2}


def _english_stems(text: str) -> set[str]:
    return {w[:3].lower() for w in _CAP_WORD.findall(text)}


@dataclass(frozen=True)
class GreekNode:
    """One Greek speaker share (``_greek_event_slots``' unit)."""

    name: str | None
    chars: int
    # Nodes on the same physical Greek line share this key (antilabe shares
    # are always adjacent indices, per `_greek_event_slots`); None if unknown.
    line_key: object = None
    text: str = ""  # only used by the (off-by-default) transliteration term
    # P1 (turn-pairing-round4-2026-09-15.md, defect 1): True when this node's
    # `name` was INHERITED from the preceding named slot by the caller
    # (`stage1_turn_english.run()`'s `dp_names`), not read off its own
    # speaker event. Charged `weights.w_cont` in `_match_cost` so a
    # continuation, otherwise tied with the named node of the same speaker
    # that follows it, loses the tie -- without making it dearer than a
    # cross-name match (`w_cont` stays well below `w_spk`).
    inherited: bool = False


@dataclass(frozen=True)
class EnglishNode:
    """One English speech."""

    name: str | None
    chars: int
    text: str = ""


@dataclass(frozen=True)
class Weights:
    open_g: float = 1.60
    # P2 (turn-pairing-round4-2026-09-15.md): the extension rates are priced
    # PER EVENT, not swept. Round 3's inequality 2 was checked at n=3 and
    # fails asymptotically (n -> infinity gives w_spk < ext_g + ext_e, not
    # the n=3 statement); round 4 replaces it with the asymptotic form. Four
    # inequalities the design's own cases require -- the lane may move the
    # numbers but must keep all four:
    #   1. open_e < w_spk             -- a single surplus English turn is
    #      skipped, not cross-matched (design 5.4, Frogs 57-87).
    #   2. w_spk < ext_g + ext_e      -- a run of label disagreements is
    #      matched-with-flags at EVERY length, not tunnelled through a
    #      parallel two-sided gap (round4 defect 2: 2.50 < 2.75).
    #   3. w_bridge < open_g          -- round 3's P2, the bridge is a
    #      tie-breaker only.
    #   4. ext_g < w_spk              -- a one-sided Greek hole (a lost Loeb
    #      page) stays far cheaper than carrying a cross-name offset.
    ext_g: float = 0.55
    # P3 (turn-pairing-round4-2026-09-15.md, defect 3): must cost MORE than
    # an agreeing-name match (so a share whose own English exists is matched,
    # not dropped for a flat 0.05 that lets the DP carry a one-speech offset
    # forward) and LESS than w_spk (so a genuinely merged antilabe -- one
    # English speech for k shares of one physical line, design 3.2 -- is
    # still skipped rather than cross-matched). 0.1 < 0.60 < 2.50.
    ext_g_same_line: float = 0.60
    open_e: float = 2.20
    ext_e: float = 2.20
    w_cohere: float = 1.20
    # P2: 2.5, not 3.0 -- see the inequalities above.
    w_spk: float = 2.5
    w_len: float = 0.45
    w_pos: float = 0.60
    # P2 (round 3): a tie-breaker, not a bonus that can buy a hole or a
    # cross-name match on its own -- the invariant is w_bridge < open_g.
    w_bridge: float = 0.8
    w_anch: float = 0.0  # off by default (design 3.2: cut first if it doesn't help)
    # P1 (turn-pairing-round4-2026-09-15.md, defect 1): charged in
    # `_match_cost` when the GREEK node is `inherited` (a continuation, not
    # its own speaker event). Must exceed the typical length/position
    # difference between adjacent nodes (measured 0.02-0.30) and stay well
    # below `w_spk`, so a continuation never becomes dearer than a
    # cross-name match.
    w_cont: float = 0.80
    covered_length_threshold: float = 0.7  # L at which a SKIP_G run after a
    # MATCH is emitted as derived_covered ("the English is long for its Greek")


DEFAULTS = Weights()


@dataclass
class Alignment:
    pairs: list[tuple[int, int]] = field(default_factory=list)
    greek_skips: list[tuple[int, int]] = field(default_factory=list)  # half-open
    english_skips: list[int] = field(default_factory=list)
    margins: dict[tuple[int, int], float] = field(default_factory=dict)
    derived_covered: dict[int, int] = field(default_factory=dict)
    cost: float = 0.0
    # Dead since round 9: the DP is unbanded, so nothing is ever widened. The
    # field and its report/scan column stay so the round-by-round baselines
    # still line up (`pairing_scan.py`'s `band_widened`).
    band_widened: bool = False


def _match_cost(
    g: GreekNode, e: EnglishNode, *, rho: float, gi: int, ei: int, G: int, E: int,
    bridge_cos: float, weights: Weights,
) -> float:
    if (
        g.name is not None and g.name != OCR_JUNK
        and e.name is not None and e.name != OCR_JUNK
    ):
        s = 0.0 if g.name == e.name else 1.0
    else:
        # One side unattributed or unreadable: the discount, not a full
        # cross-name charge (design 3.2, term S).
        s = 0.0 if g.name == e.name else 0.35
    g_chars = max(g.chars, 1)
    length_ratio = (e.chars + 20) / (rho * g_chars + 20) if rho > 0 else 1.0
    length_term = min(max(abs(math.log(max(length_ratio, 1e-9))), 0.0), 3.0)
    pos_term = min(2.0 * abs((ei / E if E else 0.0) - (gi / G if G else 0.0)), 1.0)
    cost = weights.w_spk * s + weights.w_len * length_term + weights.w_pos * pos_term
    if g.inherited:
        cost += weights.w_cont
    if weights.w_bridge and bridge_cos:
        cost -= weights.w_bridge * bridge_cos
    if weights.w_anch:
        shared = len(_anchor_stems(g.text) & _english_stems(e.text))
        cost -= weights.w_anch * min(1.0, shared / 2.0)
    return cost


def _bridge_lookup(bridge: list[str | None], english: list["EnglishNode"], weights: Weights):
    """A once-built banded cosine table over this region's bridge texts and
    English speeches (design section 4: additive to ``align/similarity.py``,
    never the full matrix). ``None`` when the bridge term is off or nothing
    to bridge against."""
    if not weights.w_bridge or not any(bridge):
        return None
    from .align.similarity import banded_cosine

    return banded_cosine([b or "" for b in bridge], [e.text for e in english])


def _median_ratio(greek: list[GreekNode], english: list[EnglishNode]) -> float:
    """Median English-chars-per-Greek-char over a first-pass diagonal
    (design 3.2, term L): each English node against the Greek node at the
    same relative position."""
    if not greek or not english:
        return 1.0
    ratios = []
    for ei, e in enumerate(english):
        gi = min(len(greek) - 1, round(ei * len(greek) / len(english)))
        g_chars = max(greek[gi].chars, 1)
        ratios.append(e.chars / g_chars)
    ratios.sort()
    n = len(ratios)
    mid = n // 2
    return ratios[mid] if n % 2 else (ratios[mid - 1] + ratios[mid]) / 2.0


def _region_align(
    greek: list[GreekNode],
    english: list[EnglishNode],
    *,
    bridge: list[str | None],
    weights: Weights,
    rho: float,
    prev_line_key: object = None,
) -> tuple[list[tuple[int, int]], list[tuple[int, int]], list[int], dict[tuple[int, int], float], bool, float]:
    """Affine (Gotoh) DP over one pin-free region. Returns
    (pairs, greek_skip_runs, english_skip_indices, margins, band_widened,
    total_cost), all indices LOCAL to this region.

    ``prev_line_key`` is the ``line_key`` of the PINNED Greek node just
    before this region (``None`` at the head of the play). Without it the
    region's first share can never be recognised as the second share of a
    physical line the pin already matched -- round 6, finding 2."""
    G, E = len(greek), len(english)
    if G == 0 and E == 0:
        return [], [], [], {}, False, 0.0
    if G == 0:
        cost = weights.open_e + max(0, E - 1) * weights.ext_e if E else 0.0
        return [], [], list(range(E)), {}, False, cost
    if E == 0:
        cost = weights.open_g + max(0, G - 1) * weights.ext_g if G else 0.0
        return [], [(0, G)], [], {}, False, cost

    bridge_table = _bridge_lookup(bridge, english, weights)

    def bcos(gi: int, ej: int) -> float:
        return bridge_table.cos(gi, ej) if bridge_table else 0.0

    def same_line(i: int) -> bool:
        """Is the share about to be SKIPPED (``greek[i - 1]``) on the same
        physical Greek line as the node before it? At ``i == 1`` that node is
        the pin that opened this region, not a node of the slice."""
        key = greek[i - 1].line_key
        if key is None:
            return False
        before = greek[i - 2].line_key if i >= 2 else prev_line_key
        return before is not None and key == before

    # Round 9, Codex merge-gate finding 1: the band is gone. It pruned cells
    # to a half-width of `max(40, 0.12 * max(G, E))` and retried wider when
    # the returned path touched a band-imposed edge or held ONE gap run
    # longer than the half-width -- neither of which is a sound completeness
    # test. A cheaper path can leave the band through several SHORTER gap
    # runs while the constrained path stays comfortably inside, and nothing
    # would notice. Measured over the three widest comedies the unbanded DP
    # costs 4.76 / 4.03 / 4.18 s a play (Birds / Frogs / Clouds) against
    # 2.94 / 2.65 / 2.71 s banded, on a 10 s per-play budget: the
    # optimisation bought under two seconds for a soundness argument nobody
    # had written. `band_lo_hi` stays only as the full-width row bounds the
    # forward pass and the margin sweep both read.
    W = max(G, E) + 1

    def band_lo_hi(i: int, w: int) -> tuple[int, int]:
        center = i * E / G if G else 0.0
        lo = max(0, math.floor(center - w))
        hi = min(E, math.ceil(center + w))
        return lo, hi

    def run(w: int) -> tuple[list[list[float]], list[list[float]], list[list[float]], list[tuple[int, int]]]:
        lohi = [band_lo_hi(i, w) for i in range(G + 1)]
        M = [{} for _ in range(G + 1)]
        Ig = [{} for _ in range(G + 1)]
        Ie = [{} for _ in range(G + 1)]
        M[0][0] = 0.0
        for i in range(G + 1):
            lo, hi = lohi[i]
            for j in range(lo, hi + 1):
                if i == 0 and j == 0:
                    continue
                best_m = INF
                if i >= 1 and j >= 1:
                    prev_lo, prev_hi = lohi[i - 1]
                    if prev_lo <= j - 1 <= prev_hi:
                        base = min(
                            M[i - 1].get(j - 1, INF),
                            Ig[i - 1].get(j - 1, INF),
                            Ie[i - 1].get(j - 1, INF),
                        )
                        if base < INF:
                            c = _match_cost(
                                greek[i - 1], english[j - 1], rho=rho,
                                gi=i - 1, ei=j - 1, G=G, E=E,
                                bridge_cos=bcos(i - 1, j - 1),
                                weights=weights,
                            )
                            best_m = base + c
                    M[i][j] = best_m
                best_g = INF
                if i >= 1:
                    # A share on the SAME physical Greek line as the node
                    # before it costs the flat reduced rate whether this is
                    # the first skip of a run or a continuation (design 3.2:
                    # "those shares live inside the same physical line and
                    # the reader shows the whole line beside that one speech
                    # regardless") -- it never pays the ordinary opening cost.
                    m_prev = M[i - 1].get(j, INF)
                    ie_prev = Ie[i - 1].get(j, INF)
                    ig_prev = Ig[i - 1].get(j, INF)
                    if same_line(i):
                        best_g = min(
                            m_prev + weights.ext_g_same_line if m_prev < INF else INF,
                            ie_prev + weights.ext_g_same_line if ie_prev < INF else INF,
                            ig_prev + weights.ext_g_same_line if ig_prev < INF else INF,
                        )
                    else:
                        best_g = min(
                            m_prev + weights.open_g if m_prev < INF else INF,
                            ie_prev + weights.open_g if ie_prev < INF else INF,
                            ig_prev + weights.ext_g if ig_prev < INF else INF,
                        )
                    Ig[i][j] = best_g
                best_e = INF
                if j >= 1:
                    m_prev = M[i].get(j - 1, INF)
                    ig_prev = Ig[i].get(j - 1, INF)
                    ie_prev = Ie[i].get(j - 1, INF)
                    opening_cost = min(
                        m_prev + weights.open_e if m_prev < INF else INF,
                        ig_prev + weights.open_e if ig_prev < INF else INF,
                    )
                    # A fresh open pays `w_cohere` when the skip falls
                    # strictly between two shares of one physical Greek line.
                    # It is part of the price of OPENING, so it goes inside
                    # the minimum: added after it (round 6, finding 4), a
                    # cell could store a cost dearer than the extend path the
                    # traceback then reconstructs.
                    if opening_cost < INF and (
                        0 < i < G
                        and greek[i - 1].line_key is not None
                        and greek[i - 1].line_key == greek[i].line_key
                    ):
                        opening_cost += weights.w_cohere
                    extending_cost = ie_prev + weights.ext_e if ie_prev < INF else INF
                    Ie[i][j] = min(opening_cost, extending_cost)
        return M, Ig, Ie, lohi

    def solve(
        M: list[dict], Ig: list[dict], Ie: list[dict], lohi: list[tuple[int, int]],
    ):
        """Pick the cheapest final layer and trace back.

        Returns ``None`` when no finite path reaches the end cell (caller
        decides how to react). Before round 9 this also reported whether the
        band may have distorted the path; with no band there is nothing to
        report.
        """
        end = (G, E)
        layer_costs = {
            "M": M[end[0]].get(end[1], INF),
            "Ig": Ig[end[0]].get(end[1], INF),
            "Ie": Ie[end[0]].get(end[1], INF),
        }
        layer = min(layer_costs, key=layer_costs.get)
        total_cost = layer_costs[layer]
        if total_cost == INF:
            return None

        pairs: list[tuple[int, int]] = []
        skip_g_marks: list[int] = []
        skip_e_marks: list[int] = []
        i, j = end
        cur = layer
        while (i, j) != (0, 0):
            if cur == "M":
                pairs.append((i - 1, j - 1))
                base_candidates = {
                    "M": M[i - 1].get(j - 1, INF),
                    "Ig": Ig[i - 1].get(j - 1, INF),
                    "Ie": Ie[i - 1].get(j - 1, INF),
                }
                cur = min(base_candidates, key=base_candidates.get)
                i, j = i - 1, j - 1
            elif cur == "Ig":
                skip_g_marks.append(i - 1)
                m_prev = M[i - 1].get(j, INF)
                ie_prev = Ie[i - 1].get(j, INF)
                ig_prev = Ig[i - 1].get(j, INF)
                if same_line(i):
                    cand = {
                        "M": m_prev + weights.ext_g_same_line if m_prev < INF else INF,
                        "Ie": ie_prev + weights.ext_g_same_line if ie_prev < INF else INF,
                        "Ig": ig_prev + weights.ext_g_same_line if ig_prev < INF else INF,
                    }
                else:
                    cand = {
                        "M": m_prev + weights.open_g if m_prev < INF else INF,
                        "Ie": ie_prev + weights.open_g if ie_prev < INF else INF,
                        "Ig": ig_prev + weights.ext_g if ig_prev < INF else INF,
                    }
                cur = min(cand, key=cand.get)
                i = i - 1
            else:  # Ie
                skip_e_marks.append(j - 1)
                m_prev = M[i].get(j - 1, INF)
                ig_prev = Ig[i].get(j - 1, INF)
                ie_prev = Ie[i].get(j - 1, INF)
                cohere = (
                    0 < i < G
                    and greek[i - 1].line_key is not None
                    and greek[i - 1].line_key == greek[i].line_key
                )
                open_cost = min(
                    m_prev + weights.open_e if m_prev < INF else INF,
                    ig_prev + weights.open_e if ig_prev < INF else INF,
                )
                if cohere:
                    open_cost_display = open_cost + weights.w_cohere
                else:
                    open_cost_display = open_cost
                extend_cost = ie_prev + weights.ext_e if ie_prev < INF else INF
                cand = {"open": open_cost_display, "extend": extend_cost}
                choice = min(cand, key=cand.get)
                if choice == "extend":
                    cur = "Ie"
                else:
                    cur = min(
                        {"M": m_prev, "Ig": ig_prev},
                        key=lambda k: {"M": m_prev, "Ig": ig_prev}[k],
                    )
                j = j - 1

        pairs.reverse()
        skip_g_marks.sort()
        skip_e_marks.sort()

        greek_skip_runs: list[tuple[int, int]] = []
        for idx in skip_g_marks:
            if greek_skip_runs and greek_skip_runs[-1][1] == idx:
                greek_skip_runs[-1] = (greek_skip_runs[-1][0], idx + 1)
            else:
                greek_skip_runs.append((idx, idx + 1))

        return pairs, greek_skip_runs, skip_e_marks, total_cost

    widened = False
    M, Ig, Ie, lohi = run(W)
    solved = solve(M, Ig, Ie, lohi)

    if solved is None:
        # No path at all (should not happen for finite costs over the full
        # matrix); fall back to skip-everything.
        fallback_cost = weights.open_g + max(0, G - 1) * weights.ext_g
        fallback_cost += weights.open_e + max(0, E - 1) * weights.ext_e
        return [], [(0, G)], list(range(E)), {}, widened, fallback_cost

    pairs, greek_skip_runs, skip_e_marks, total_cost = solved

    # Margins: for each matched pair, how much cheaper the chosen match is
    # than the best DIFFERENTLY-NAMED candidate in that row (or skipping the
    # node outright) -- the alternative a reviewer would actually worry
    # about. A same-name candidate a few slots away is not that: in a
    # two-hander stichomythia every such candidate reads identically, so
    # comparing against it would make "margin" near zero for ordinary
    # correct dialogue (exactly the LCS-carries-no-information regime
    # design section 1 describes) rather than flag genuine ambiguity.
    margins: dict[tuple[int, int], float] = {}
    for gi, ej in pairs:
        chosen = _match_cost(
            greek[gi], english[ej], rho=rho, gi=gi, ei=ej, G=G, E=E,
            bridge_cos=bcos(gi, ej), weights=weights,
        )
        # `lohi[gi + 1]` holds valid DP *j* values (english-consumed counts,
        # 1-indexed) for the row matching greek[gi]; the node index is j - 1.
        lo, hi = lohi[gi + 1] if gi + 1 < len(lohi) else band_lo_hi(gi + 1, W)
        chosen_name = english[ej].name
        best_alt = INF
        for j2 in range(max(1, lo), min(E, hi) + 1):
            ej2 = j2 - 1
            if ej2 == ej or english[ej2].name == chosen_name:
                continue
            c2 = _match_cost(
                greek[gi], english[ej2], rho=rho, gi=gi, ei=ej2, G=G, E=E,
                bridge_cos=bcos(gi, ej2), weights=weights,
            )
            best_alt = min(best_alt, c2)
        no_match_alt = weights.open_g + weights.open_e
        best_alt = min(best_alt, no_match_alt)
        margins[(gi, ej)] = best_alt - chosen

    return pairs, greek_skip_runs, skip_e_marks, margins, widened, total_cost


def align(
    greek: list[GreekNode],
    english: list[EnglishNode],
    *,
    pins: list[tuple[int, int]],
    bridge: list[str | None] | None = None,
    weights: Weights = DEFAULTS,
) -> Alignment:
    """Minimum-cost monotone alignment of Greek shares to English speeches.

    Pins are hard constraints: the DP runs independently in each region
    between consecutive pinned cells (design 3.3), exactly as the deleted
    ``_pair_turns`` split regions at its anchors.
    """
    G, E = len(greek), len(english)
    bridge = bridge or [None] * G
    pinned = sorted(pins or [])
    for (agi, aej), (bgi, bej) in zip(pinned, pinned[1:]):
        if bgi <= agi or bej <= aej:
            raise ValueError(f"pins must run forward in both texts: {(agi, aej)} then {(bgi, bej)}")

    rho = _median_ratio(greek, english)

    result = Alignment()
    boundaries = [(-1, -1)] + pinned + [(G, E)]
    all_pairs = list(pinned)
    band_widened = False
    pin_bridge = _bridge_lookup(bridge, english, weights)
    total_cost = sum(
        _match_cost(
            greek[gi], english[ej], rho=rho, gi=gi, ei=ej, G=G, E=E,
            bridge_cos=(pin_bridge.cos(gi, ej) if pin_bridge else 0.0), weights=weights,
        )
        for gi, ej in pinned
    )
    for (agi, aej), (bgi, bej) in zip(boundaries, boundaries[1:]):
        g_slice = greek[agi + 1 : bgi]
        e_slice = english[aej + 1 : bej]
        b_slice = bridge[agi + 1 : bgi]
        sub_pairs, sub_greek_skips, sub_english_skips, sub_margins, widened, sub_cost = _region_align(
            g_slice, e_slice, bridge=b_slice, weights=weights, rho=rho,
            # The pinned share this region opens after: its physical line is
            # what makes the region's first share a same-line skip (finding 2).
            prev_line_key=greek[agi].line_key if agi >= 0 else None,
        )
        band_widened = band_widened or widened
        total_cost += sub_cost
        off_g, off_e = agi + 1, aej + 1
        for gi, ej in sub_pairs:
            all_pairs.append((gi + off_g, ej + off_e))
        for lo, hi in sub_greek_skips:
            result.greek_skips.append((lo + off_g, hi + off_g))
        for ej in sub_english_skips:
            result.english_skips.append(ej + off_e)
        for (gi, ej), m in sub_margins.items():
            result.margins[(gi + off_g, ej + off_e)] = m

    all_pairs.sort()
    result.pairs = all_pairs
    result.band_widened = band_widened

    # Derived covered: a SKIP_G run immediately after a MATCH whose length
    # ratio is high (design 3.5's `covered` sibling).
    pairs_by_g = {gi: ej for gi, ej in all_pairs}
    for lo, hi in result.greek_skips:
        prev_g = lo - 1
        if prev_g in pairs_by_g:
            ej = pairs_by_g[prev_g]
            g_chars = max(greek[prev_g].chars, 1)
            length_ratio = (english[ej].chars + 20) / (rho * g_chars + 20) if rho > 0 else 1.0
            l_term = math.log(max(length_ratio, 1e-9))
            if l_term >= weights.covered_length_threshold:
                for gi in range(lo, hi):
                    result.derived_covered[gi] = prev_g

    result.cost = total_cost
    return result
