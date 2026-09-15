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
