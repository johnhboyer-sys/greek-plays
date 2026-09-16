"""Golden cases for the turn-pairing DP (turn-pairing-design-2026-09-15.md
section 7, acceptance A). Each reproduces a SHAPE from the corpus, not the
text: a small synthetic Greek-share / English-speech spine standing in for
Persians' Salamis scene, Alcestis' kommos, Ajax's lost pages, Frogs' antilabe
and refrains, and the antilabe line-merge rule.
"""

from __future__ import annotations

from drama_pipeline.pair_dp import EnglishNode, GreekNode, Weights, align


def _names(nodes):
    return [n.name for n in nodes]


def _paired_ordinal_deltas(pairs, greek, english):
    """For each pair in document order, its 0-based position among the PAIRS
    sharing that name so far, on each side -- the drift signal restricted to
    what was actually matched (an English speech the DP skipped, e.g. a
    genuine extra head turn with no Greek counterpart, must not leave a
    phantom offset on every later pair of that name)."""
    seen_g: dict[str, int] = {}
    seen_e: dict[str, int] = {}
    out = {}
    for gi, ej in sorted(pairs):
        name = greek[gi].name
        go = seen_g.get(name, 0)
        eo = seen_e.get(name, 0)
        seen_g[name] = go + 1
        seen_e[name] = eo + 1
        out[(gi, ej)] = (go, eo)
    return out


def test_persians_salamis_long_speech_and_head_extras():
    """30 Greek events over three speakers; the English carries two extra
    head turns (Morshead's two turns Murray does not have) and one speech
    25x the median length (his battle rhesis). The long speech must pair
    with the Greek node of the largest line count, the two extras must show
    up as english_skips, and once past them, no pair should carry a
    same-name ordinal delta (the LCS-era bug: the offset never resets)."""
    names = ["Chorus"] + ["Atossa", "Messenger"] * 14 + ["Chorus"]  # 30
    greek = [GreekNode(name=n, chars=60) for n in names]
    # The Messenger's battle narrative: one Greek node much longer than the rest.
    long_gi = 16
    assert names[long_gi] == "Messenger"
    greek[long_gi] = GreekNode(name="Messenger", chars=900)

    english_names = ["Atossa", "Messenger"] + names  # two extra head turns
    english = [EnglishNode(name=n, chars=60) for n in english_names]
    long_ei = 2 + long_gi
    english[long_ei] = EnglishNode(name="Messenger", chars=60 * 25)

    result = align(greek, english, pins=[])

    assert (long_gi, long_ei) in result.pairs
    assert 0 in result.english_skips and 1 in result.english_skips

    # Once past the long speech, a pair's same-name ordinal among what was
    # actually PAIRED must agree on both sides -- the two extras were
    # skipped, not paired, so they must not leave a phantom offset behind.
    deltas = _paired_ordinal_deltas(result.pairs, greek, english)
    for gi, ej in result.pairs:
        if gi > long_gi and ej > long_ei:
            go, eo = deltas[(gi, ej)]
            assert go == eo, (gi, ej, go, eo)


def test_alcestis_kommos_stasimon_pairs_with_last_long_block():
    """20 Greek events, 8 English speeches, one 40-line English stasimon
    (Murray's). It must pair with the LAST long Greek block, not the first
    small event it reaches, and every Greek event between the two matches
    (the antiphonal kommos neither column really translates) must show up
    as a skip or a derived cover -- never silently absorbed."""
    head_names = ["Admetus", "Chorus", "Admetus", "Chorus", "Admetus", "Chorus", "Admetus"]
    greek = [GreekNode(name=n, chars=30) for n in head_names]
    greek += [GreekNode(name="Chorus", chars=15) for _ in range(12)]  # bare kommos
    greek.append(GreekNode(name="Chorus", chars=900))  # the last long block

    english = [EnglishNode(name=n, chars=30) for n in head_names]
    english.append(EnglishNode(name="Chorus", chars=1800))  # the stasimon

    result = align(greek, english, pins=[])

    last_gi = len(greek) - 1
    last_ei = len(english) - 1
    assert (last_gi, last_ei) in result.pairs

    prev_gi = max(gi for gi, ej in result.pairs if ej < last_ei)
    between = set(range(prev_gi + 1, last_gi))
    covered = set(result.derived_covered) | {
        i for lo, hi in result.greek_skips for i in range(lo, hi)
    }
    assert between <= covered, between - covered
    assert all(ej != last_ei for gi, ej in result.pairs if gi != last_gi)


def test_ajax_three_lost_pages_leave_the_greek_bare():
    """30 Greek events; the English is missing the ten events 10-19 (a lost
    Loeb page). Pairs must stay identity on both surviving stretches, the
    hole must appear as one greek_skip_run, and the DP must NOT carry the
    offset forward by matching a mismatched name across the gap."""
    names = ["Teucer", "Agamemnon"] * 15  # 30
    greek = [GreekNode(name=n, chars=50) for n in names]
    kept = names[:10] + names[20:]  # the missing page's ten events dropped
    english = [EnglishNode(name=n, chars=50) for n in kept]

    result = align(greek, english, pins=[])

    pairs = dict(result.pairs)
    for i in range(10):
        assert pairs[i] == i
    for i in range(20, 30):
        assert pairs[i] == i - 10
    assert result.greek_skips == [(10, 20)]
    for gi, ej in result.pairs:
        assert greek[gi].name == english[ej].name


def test_frogs_antilabe_no_crossed_pairs():
    """Four packed Greek segments of two shares each (A/B antilabe), and the
    English carries one extra B at the head -- the shape that used to hold
    Frogs 83-87 one exchange out via the deleted disagreeing zip. The DP
    must skip the lone extra, never buy a mismatched A/B pair to avoid it."""
    line_pattern = ["A", "B"] * 4  # 8 shares, 4 physical lines
    greek = [
        GreekNode(name=n, chars=30, line_key=k // 2)
        for k, n in enumerate(line_pattern)
    ]
    english_names = ["B"] + line_pattern
    english = [EnglishNode(name=n, chars=30) for n in english_names]

    result = align(greek, english, pins=[])

    for gi, ej in result.pairs:
        assert greek[gi].name == english[ej].name
    assert result.english_skips == [0]


def test_frogs_refrain_matches_by_position_not_just_name():
    """Three identical one-line Chorus refrains separated by long strophes,
    every node the SAME name -- so only length and position can tell them
    apart. Refrain k must pair with refrain k, strophe with its own strophe."""
    greek = [
        GreekNode(name="Chorus", chars=15),
        GreekNode(name="Chorus", chars=300),
        GreekNode(name="Chorus", chars=15),
        GreekNode(name="Chorus", chars=300),
        GreekNode(name="Chorus", chars=15),
    ]
    english = [
        EnglishNode(name="Chorus", chars=15),
        EnglishNode(name="Chorus", chars=310),
        EnglishNode(name="Chorus", chars=15),
        EnglishNode(name="Chorus", chars=305),
        EnglishNode(name="Chorus", chars=15),
    ]
    result = align(greek, english, pins=[])
    assert result.pairs == [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4)]


def test_speakerless_continuation_inherits_speaker_not_a_magnet():
    """Round 3 (turn-pairing-round3-2026-09-15.md, P1). A Greek share with no
    speaker event of its own is fed to the DP with its preceding named
    speaker's name INHERITED (the caller's job, `stage1_turn_english.py`'s
    `dp_names`) rather than `None` -- so a speakerless continuation node
    sitting between two named ones must NOT act as a cheap magnet for the
    following named speaker's English (the shape of Bacchae 1:1125's
    Messenger continuation absorbing the Chorus's dance ode meant for
    1:1153): with the name inherited, the continuation keeps its own
    speaker's long English and the next Greek node keeps its own."""
    greek = [
        GreekNode(name="Messenger", chars=40),
        GreekNode(name="Messenger", chars=400),  # the continuation, INHERITED
        GreekNode(name="Chorus", chars=60),  # the dance ode's own Greek
    ]
    english = [
        EnglishNode(name="Messenger", chars=40),
        EnglishNode(name="Messenger", chars=420),  # the battle narrative
        EnglishNode(name="Chorus", chars=60),  # "Weave ye the dance"
    ]

    result = align(greek, english, pins=[])

    assert (1, 1) in result.pairs  # the continuation keeps its own speaker's text
    assert (2, 2) in result.pairs  # the ode lands on its own Greek


def test_disagreeing_run_is_matched_not_double_gapped():
    """Round 3, P3 (the Lysistrata 1:439-1:447 oath stichomythia shape): a
    five-turn run where two of the five names agree (both "Magistrate") and
    three differ must be matched pair by pair -- the three disagreements
    flagged, not swallowed into a parallel two-sided gap. P3's inequality 2
    is exactly what keeps a run this long from tunnelling."""
    greek_names = ["Calonice", "Magistrate", "Myrrhine", "Magistrate", "Lysistrata"]
    english_names = ["First Woman", "Magistrate", "Second Woman", "Magistrate", "Third Woman"]
    greek = [GreekNode(name=n, chars=40) for n in greek_names]
    english = [EnglishNode(name=n, chars=40) for n in english_names]

    result = align(greek, english, pins=[])

    assert len(result.pairs) == 5
    pairs = dict(result.pairs)
    for gi in range(5):
        assert pairs[gi] == gi


def test_antilabe_merge_reduced_extend_cost():
    """One Greek line, two shares, one English speech (the Ecclesiazusae
    shape): the second share is a SKIP_G at the REDUCED same-line rate, not
    the ordinary opening cost, and the segment still gets the English."""
    greek = [
        GreekNode(name="Alpha", chars=20, line_key="L1"),
        GreekNode(name="Beta", chars=20, line_key="L1"),
    ]
    english = [EnglishNode(name="Alpha", chars=40)]

    w = Weights()
    result = align(greek, english, pins=[])

    assert result.pairs == [(0, 0)]
    assert result.greek_skips == [(1, 2)]
    # The skip must have cost the flat same-line rate, not open_g + ext_g.
    match_cost = result.cost
    assert match_cost < w.open_g  # the whole alignment is cheaper than one
    # ordinary opened skip would have been on its own, proving the reduced
    # rate (not the standard affine open) was charged.


def test_continuation_node_does_not_take_its_speakers_next_english():
    """Round 4 (turn-pairing-round4-2026-09-15.md, P1, defect 1). A
    continuation node (`inherited=True`, the caller's `dp_names` name)
    sitting between two named nodes of the same speaker must not out-bid the
    later NAMED node for the English that starts there, even when the
    continuation is closer in length -- the shape of Kosmos' Chorus
    continuations absorbing English meant for the named node that follows
    (libation-bearers, third). Without `w_cont` the DP prefers the
    continuation here; with it, the named node wins."""
    greek = [
        GreekNode(name="Chorus", chars=200),
        GreekNode(name="Chorus", chars=5),  # the named node the English is for
        GreekNode(name="Chorus", chars=60, inherited=True),  # the continuation
        GreekNode(name="Chorus", chars=200),
    ]
    english = [
        EnglishNode(name="Chorus", chars=2000),
        EnglishNode(name="Chorus", chars=300),
        EnglishNode(name="Chorus", chars=2000),
    ]

    result = align(greek, english, pins=[])

    assert (1, 1) in result.pairs  # the named node keeps its own English
    assert all(gi != 2 for gi, _ej in result.pairs)  # the continuation does not


def test_disagreeing_run_of_twelve_is_matched_not_tunnelled():
    """Round 4, P2 (the Agamemnon 1348-1371 shape: twelve separate Elders
    against twelve Chorus speeches in Morshead). Round 3's inequality 2 held
    only at n=3; its asymptotic form (`w_spk < ext_g + ext_e`) must hold at
    any length, so a run this long is matched pair by pair, not swallowed by
    a cheaper parallel two-sided gap."""
    greek = [GreekNode(name=f"Elder{i}", chars=60) for i in range(12)]
    english = [EnglishNode(name="Chorus", chars=60) for _ in range(12)]

    result = align(greek, english, pins=[])

    assert len(result.pairs) == 12
    pairs = dict(result.pairs)
    for gi in range(12):
        assert pairs[gi] == gi


def test_two_share_line_whose_english_is_two_turns_gets_both():
    """Round 4, P3 (defect 3): when the translator renders an antilabe's two
    shares as TWO separate speeches -- the normal case (design 2(c)) -- both
    shares must be matched to their own English, not one dropped at the
    reduced same-line rate to carry a one-speech offset forward (the
    Acharnians 1:1117, Ecclesiazusae 1:328, and Wasps 1:145 shape)."""
    greek = [
        GreekNode(name="Alpha", chars=20, line_key="L1"),
        GreekNode(name="Beta", chars=20, line_key="L1"),
    ]
    english = [
        EnglishNode(name="Alpha", chars=20),
        EnglishNode(name="Beta", chars=20),
    ]

    result = align(greek, english, pins=[])

    assert result.pairs == [(0, 0), (1, 1)]
    assert result.greek_skips == []
    assert result.english_skips == []


def test_band_falls_back_to_the_unbanded_dp_when_the_band_has_no_path():
    """Round 6, finding 1 (grok static review 2026-09-16). The band's rows are
    centred on `i*E/G` with no predecessor closure, so when `E/G > 2W`
    consecutive rows are DISJOINT and no path reaches the end cell at either
    `W` or `2W`. One Greek share against 200 English speeches is that shape
    (`W = 40`, row 0 reaches j <= 40, row 1 starts at j >= 160). The old code
    fell back to "skip everything", losing a pair the unbanded DP finds."""
    greek = [GreekNode(name="A", chars=50)]
    english = [
        EnglishNode(name="A" if j == 0 else "B", chars=50) for j in range(200)
    ]

    banded = align(greek, english, pins=[])
    unbanded = align(greek, english, pins=[], band=False)

    assert banded.pairs == unbanded.pairs == [(0, 0)]
    assert banded.greek_skips == []
    assert banded.cost == unbanded.cost


def test_band_edge_on_row_zero_widens():
    """Round 6, finding 1, second clause. `band_lo_hi` clamps `lo` to 0 at
    row 0 and `hi` to E at row G, but row 0's `hi` is NOT clamped: an English
    skip run longer than W at the head of a region runs along a real band
    edge, and the old test (`0 < i < G` only) never saw it. Sixty surplus
    English speeches before the first Greek's own English is that shape --
    the banded run matched the first Greek to the wrong speech."""
    greek = [GreekNode(name="A", chars=50) for _ in range(3)]
    english = [EnglishNode(name="X", chars=50) for _ in range(60)]
    english += [EnglishNode(name="A", chars=50) for _ in range(3)]

    banded = align(greek, english, pins=[])
    unbanded = align(greek, english, pins=[], band=False)

    assert banded.pairs == unbanded.pairs == [(0, 60), (1, 61), (2, 62)]
    assert banded.band_widened is True


def test_pinned_predecessor_keeps_the_same_line_rate_for_the_regions_first_share():
    """Round 6, finding 2. `same_line` compares `greek[i-1]` with `greek[i-2]`
    INSIDE the region slice, so the first share of a region can never take
    the reduced same-line rate -- even when the pin immediately before it is
    the other share of its own physical line. Here Alpha's pinned speech
    carries the whole of line L1 (Beta's share merged into it) and Beta's own
    next speech follows: with the reduced rate the merged share is skipped
    and Beta's speech lands on Beta's own Greek; at the ordinary `open_g` the
    merged share outbids it and steals it, leaving the real Greek bare. The
    unpinned run of the same data already gets this right, so a pin must not
    change the answer on nodes it does not touch."""
    greek = [
        GreekNode(name="Alpha", chars=100, line_key="L1"),
        GreekNode(name="Beta", chars=40, line_key="L1"),  # merged into Alpha's speech
        GreekNode(name="Beta", chars=180, line_key="L2"),  # Beta's own next speech
        GreekNode(name="Gamma", chars=100, line_key="L3"),
    ]
    english = [
        EnglishNode(name="Alpha", chars=140),  # the whole of L1
        EnglishNode(name="Beta", chars=90),
        EnglishNode(name="Gamma", chars=100),
    ]

    pinned = align(greek, english, pins=[(0, 0)])
    unpinned = align(greek, english, pins=[])

    assert unpinned.pairs == [(0, 0), (2, 1), (3, 2)]
    assert pinned.pairs == unpinned.pairs
    assert pinned.greek_skips == [(1, 2)]


def test_cohere_is_inside_the_ie_minimum_not_added_after_it():
    """Round 6, finding 4. `Ie` took `min(opening, extending)` and THEN added
    `w_cohere` when opening won the comparison -- so whenever extending cost
    between 0 and `w_cohere` more than opening, the cell stored a value
    dearer than a real path, and the traceback (which compares
    `opening + w_cohere` against extending) could reconstruct the other one.
    A run of English skips beside an antilabe line is that shape: here the
    overcharge pushed the DP off the alignment that matches the second share
    to its own English and onto one that leaves it bare. The reported cost
    must also be the cost of the path actually returned."""
    greek = [
        GreekNode(name=None, chars=20, line_key="L1", inherited=True),
        GreekNode(name="Alpha", chars=20, line_key="L1"),
    ]
    english = [
        EnglishNode(name=None, chars=400),
        EnglishNode(name="Beta", chars=400),
        EnglishNode(name="Gamma", chars=20),
        EnglishNode(name="Alpha", chars=60),
    ]

    result = align(greek, english, pins=[])

    assert result.pairs == [(0, 0), (1, 3)]
    assert result.greek_skips == []
    assert result.english_skips == [1, 2]
    assert result.cost == align(greek, english, pins=[], band=False).cost
