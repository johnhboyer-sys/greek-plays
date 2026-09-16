"""Golden cases for the turn-pairing DP (turn-pairing-design-2026-09-15.md
section 7, acceptance A). Each reproduces a SHAPE from the corpus, not the
text: a small synthetic Greek-share / English-speech spine standing in for
Persians' Salamis scene, Alcestis' kommos, Ajax's lost pages, Frogs' antilabe
and refrains, and the antilabe line-merge rule.

The round-7 cases at the foot go through ``_align_speech_runs``, the caller's
front door onto ``align``: it is the node set, not the weights, that had to
change for them, and the shape they reproduce (one Greek SPEECH cut across
several segments) only exists once slots are grouped into speeches.
"""

from __future__ import annotations

from drama_pipeline.pair_dp import OCR_JUNK, EnglishNode, GreekNode, Weights, align
from drama_pipeline.stage1_turn_english import _align_speech_runs


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


def test_unreadable_cue_is_a_discount_not_a_cross_name_match():
    """Round 6, finding 8. A scanned bench column whose speaker cue the OCR
    could not read carries `stage1_turn_english`'s `_OCR_JUNK` sentinel as
    its name, and design 3.2 prices that at `S = 0.35` -- the same as an
    unattributed speech -- not at the full 1.0 of two names that genuinely
    differ. `pair_dp` did not know the sentinel, so the junk-cued speech was
    charged `w_spk` in full and the DP preferred to leave it unplaced. Here
    the three junk cues sit in an otherwise identity-aligned scan."""
    names = ["Lysistrata", "Magistrate", "Calonice", "Magistrate", "Lysistrata"]
    greek = [GreekNode(name=n, chars=60) for n in names]
    english = [
        EnglishNode(name=OCR_JUNK if k in (1, 2, 3) else names[k], chars=60)
        for k in range(len(names))
    ]

    result = align(greek, english, pins=[])

    assert result.pairs == [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4)]
    assert result.english_skips == []
    assert result.greek_skips == []




def _run_align(slot_names, greek_chars, english, forced=()):
    """The caller's node build, reduced to what these cases need: one Greek
    node per slot, `inherited` where the slot has no speaker event of its
    own and a named slot precedes it (``run()``'s ``dp_names``), and no
    primary bridge (the bench columns of a play whose primary is turn-text,
    and the shape has to come out right without it).  ``forced`` is what
    ``_resolve_pins`` hands the aligner: (slot, speech) pairs."""
    last = None
    nodes = []
    for name, chars in zip(slot_names, greek_chars):
        inherited = name is None and last is not None
        nodes.append(
            GreekNode(name=name if name is not None else last, chars=chars, inherited=inherited)
        )
        if name is not None:
            last = name
    spans = [(c, "") for c in greek_chars]
    return _align_speech_runs(nodes, english, slot_names, list(forced), None, spans)


def test_persians_353_narrative_pairs_with_its_own_speech_not_the_continuation():
    """Round 7, defect 1 (`play-persians-recheck-2026-09-16.md` finding 1).

    Persians 348-432 with Morshead's own character counts, inside ordinary
    stichomythia on either side. The Greek is Atossa(348) / Messenger(349) /
    Atossa(350-352) / Messenger(353-394, the 42-line Salamis rhesis) and then
    that same speech CONTINUED at 395-432 -- 38 lines the segmenter cut out
    of the middle of one speech, carrying no speaker event, so the caller
    marks it `inherited`. Morshead prints two turns the edition does not
    (his 345-346 and 347, which belong with the Messenger's 337-347 above),
    so six English turns of 2, 1, 1, 1, 3 and 40 lines, named A M A M A M,
    stand against five Greek nodes named A M A M M(cont).

    Shipped, the 3,882-character narrative went onto the CONTINUATION and
    the speech itself held a 46-character stub. Traced, the right path lost
    by 0.024: it pays `open_g` (1.60) to skip the continuation on top of two
    English skips, and the length term cannot make that back -- it clips at
    3.0 and weighs 0.45, so the worst length pairing possible costs 1.35,
    less than one `open_e`. No weight fixes that; the node set does. A
    continuation is not a speech of its own, so it is not a node of its
    own."""
    # Ordinary exchanges, closing on the Messenger's 337-347 -- the speech
    # Morshead's two surplus turns actually belong inside.
    lead = ["Atossa", "Messenger"] * 4 + ["Atossa", "Messenger"]
    slot_names = lead + ["Atossa", "Messenger", "Atossa", "Messenger", None]
    greek_chars = [36] * 9 + [403] + [36, 37, 113, 1497, 1374]
    english = [EnglishNode(name=n, chars=47, text="line") for n in lead[:9]]
    english.append(
        EnglishNode(name="Messenger", chars=391, text="Know, if mere count of ships could win the day")
    )
    english += [
        EnglishNode(name="Atossa", chars=84, text="Nay, we were worsted by an unseen power"),
        EnglishNode(name="Messenger", chars=42, text="In ward of heaven doth Pallas' city stand."),
        EnglishNode(name="Atossa", chars=34, text="How then? is Athens yet inviolate?"),
        EnglishNode(name="Messenger", chars=46, text="While her men live, her bulwark standeth firm!"),
        EnglishNode(name="Atossa", chars=125, text="Say, how began the struggle of the ships?"),
        EnglishNode(name="Messenger", chars=3882, text="O queen, our whole disaster thus befell"),
    ]

    result = _run_align(slot_names, greek_chars, english)

    by_g = dict(result.pairs)
    # The narrative stands beside the speech it translates, read by its text
    # -- not beside the continuation, and not as a 46-character stub.
    assert english[by_g[13]].text == "O queen, our whole disaster thus befell"
    assert english[by_g[10]].text == "How then? is Athens yet inviolate?"
    assert english[by_g[11]].text == "While her men live, her bulwark standeth firm!"
    assert english[by_g[12]].text == "Say, how began the struggle of the ships?"
    # The two turns the edition does not have are skipped, not carried.
    assert result.english_skips == [10, 11]
    # The continuation is never matched; it is translated with the speech
    # above, which is what the reader is shown.
    assert 14 not in by_g
    assert result.derived_covered[14] == 13


def test_english_cued_inside_one_greek_speech_stays_on_that_speech():
    """Round 7, defect 2 (Persians 623-680, Johnston, `1:623`/`1:664`).

    One Greek speech, cut by the segmenter at 663: a 41-line head and a
    17-line continuation. Johnston cues it as two speeches, but his break
    falls at Greek 632 -- inside the head -- so no monotone one-to-one
    pairing over two nodes can be right. Shipped, the DP took the obvious
    one and put his 1,620-character kommos on the 17-line continuation,
    leaving Greek 633-663 with nothing beside it. Merged, the speech is one
    node: the kommos pairs with it, the leader's five lines are left to
    `_assign_speeches`' residual park (which puts them on the same speech,
    ahead of the kommos), and `_spread_long_speeches` distributes the block
    over both segments -- the shape yesterday's review passed."""
    lead = ["Atossa", "Chorus"] * 4
    slot_names = lead + ["Chorus", None, "Ghost of Darius"]
    greek_chars = [600] * 8 + [975, 295, 475]
    english = [EnglishNode(name=n, chars=900, text="line") for n in lead]
    english += [
        EnglishNode(name="Chorus", chars=517, text="O royal lady, whom Persians all revere"),
        EnglishNode(name="Chorus", chars=1620, text="Our sacred, godlike king"),
        EnglishNode(name="Ghost of Darius", chars=774, text="You loyal men in whom I placed my trust"),
    ]

    result = _run_align(slot_names, greek_chars, english)

    by_g = dict(result.pairs)
    assert english[by_g[8]].text == "Our sacred, godlike king"
    assert 9 not in by_g                      # the continuation takes nothing
    assert result.derived_covered[9] == 8
    assert result.english_skips == [8]        # the leader's lines, parked later
    assert english[by_g[10]].text.startswith("You loyal men")


def test_a_speech_split_five_ways_takes_one_english_at_its_head():
    """Round 7, defect 3 (Persians 1-158, Johnston, the parodos, per-play
    finding 13).

    The parodos and the anapaests are ONE Greek speech across six segments:
    a head and five continuations. Johnston cues three stanzas inside it,
    and his breaks fall at Greek 64 and 139 -- neither on a segment
    boundary. Shipped, each of his first two stanzas took a continuation
    node by position, his stanza for Greek 140 landed on the segment for
    111-139, and the last three segments stood bare. Merged, the speech
    takes one English node at its head and the other two park there too, so
    the spread carries all three across the whole speech."""
    slot_names = ["Chorus", None, None, None, None, None, "Atossa"]
    greek_chars = [1761, 975, 628, 243, 139, 176, 636]
    english = [
        EnglishNode(name="Chorus", chars=2422, text="We are here as trustworthy delegates"),
        EnglishNode(name="Chorus", chars=2424, text="Obliterating cities as it moves"),
        EnglishNode(name="Chorus", chars=824, text="Come now, Persians, let us take our seats"),
        EnglishNode(name="Atossa", chars=871, text="That is why I have left my gold-decked home"),
    ]

    result = _run_align(slot_names, greek_chars, english)

    by_g = dict(result.pairs)
    # Exactly one English lands inside the speech, and it lands on the head.
    assert set(by_g) == {0, 6}
    assert by_g[0] in (0, 1, 2)
    assert english[by_g[6]].text.startswith("That is why")
    # No continuation is given a stanza of its own -- least of all the one
    # for Greek 140, which the shipped build put beside 111-139.
    for k in range(1, 6):
        assert result.derived_covered[k] == 0
    assert len(result.english_skips) == 2


# --- Round 8 (build/review/turn-pairing-round8-2026-09-16.md) -------------
#
# Both cases below are Frogs, Murray overlay, and neither is a defect in the
# DP's own reasoning: the objective prefers the wrong answer because the only
# local evidence it has is the speaker name, and Murray's cues are not this
# Greek edition's.  The primary bridge -- the one content signal the design
# gives the aligner -- is off for the eleven comedies, whose primary is
# itself turn-text.  These tests record the arithmetic that says so, and
# assert that the pin puts each scene right.  If a later weighting makes the
# unpinned assertion fail, that is the signal to drop the pins in
# `manifests/frogs.yaml`, not to appease the test.

_FROGS_LEAD_NAMES = ["Dionysus", "Xanthias"] * 6
_FROGS_LEAD_GREEK = [50] * 12
_FROGS_LEAD_ENGLISH = [
    EnglishNode(name=n, chars=58, text="line") for n in _FROGS_LEAD_NAMES
]


def test_a_relabelled_run_slides_by_one_and_only_a_pin_holds_it():
    """Frogs 568-579, Murray (`play-frogs-recheck-2026-09-16.md` N2).

    Murray follows the modern distribution of the innkeepers' lines: 574
    PLATHANE, 575 LANDLADY, 577 PLATHANE.  This Greek gives 574 to Xanthias,
    575 to the second innkeeper (= Plathane) and 577 to the first (= the
    Landlady).  Over those three turns Murray's names are exactly the
    edition's shifted by one, so the DP can buy three agreeing pairs for one
    Greek gap and one English gap: `open_g` (1.60) + `open_e` (2.20) = 3.80
    against three cross-name matches at `w_spk` (2.50) = 7.50.  Measured on
    the real nodes the two paths cost 4.34 and 7.89.

    No weight closes that.  It would need `w_spk < (open_g + open_e) / n`
    for a relabelled run of length n -- below 1.90 at n = 2 and below 1.27 at
    n = 3 -- which is far under design 3.2's own floor (inequality 1,
    `open_e < w_spk`, is what keeps a single surplus English turn from being
    cross-matched).  Nor does the length term: the true path's length
    advantage here is 0.24 against a name deficit of 3.70.
    """
    slot_names = _FROGS_LEAD_NAMES + [
        "Xanthias", "First Innkeeper", "Second Innkeeper", "First Innkeeper",
        "Xanthias", "Second Innkeeper", "First Innkeeper", "Dionysus",
    ]
    greek_chars = _FROGS_LEAD_GREEK + [26, 59, 39, 112, 39, 78, 75, 38]
    english = _FROGS_LEAD_ENGLISH + [
        EnglishNode(name="Xanthias", chars=16, text="Like him, again."),
        EnglishNode(name="Second Innkeeper", chars=27, text="But something must be done!"),
        EnglishNode(name="First Innkeeper", chars=43, text="Run, you, and fetch me my protector, Cleon."),
        EnglishNode(name="Second Innkeeper", chars=76, text="And you fetch me Hyperbolus"),
        EnglishNode(name="First Innkeeper", chars=109, text="Oh, that ugly jaw!"),
        EnglishNode(name="Second Innkeeper", chars=42, text="And I should like to fling you in the pit!"),
        EnglishNode(name="First Innkeeper", chars=86, text="And I should like to get a scythe, and cut"),
        EnglishNode(name="Second Innkeeper", chars=101, text="Well, I'll go straight to Cleon"),
        EnglishNode(name="Dionysus", chars=74, text="Plague take me!"),
    ]
    pit, scythe, cleon = 17, 18, 19
    g574, g575, g577 = 16, 17, 18

    # Unpinned: the objective slides.  Greek 574 takes nothing and the pit
    # goes to 575 -- the shape the re-review found.
    loose = _run_align(slot_names, greek_chars, english)
    by_g = dict(loose.pairs)
    assert g574 not in by_g
    assert by_g[g575] == pit

    # Pinned at the head of the run, three turns long: every speech stands
    # beside the Greek it translates, each pair flagged `speakerMismatch`
    # downstream because the editions really do disagree.
    held = _run_align(
        slot_names, greek_chars, english,
        forced=[(g574, pit), (g575, scythe), (g577, cleon)],
    )
    by_g = dict(held.pairs)
    assert english[by_g[g574]].text == "And I should like to fling you in the pit!"
    assert english[by_g[g575]].text == "And I should like to get a scythe, and cut"
    assert english[by_g[g577]].text == "Well, I'll go straight to Cleon"
    assert held.english_skips == [13]  # Murray's extra turn inside Greek 568


def test_a_translator_gap_needs_a_pin_on_both_of_its_sides():
    """Frogs 1443-1457, Murray (`play-frogs-recheck-2026-09-16.md` N3).

    Murray has no rendering of Greek 1451-1453 (the Palamedes / Cephisophon
    exchange) and two extra turns inside 1455.  Closing the gap honestly
    costs `open_g` + `ext_g` for the two Greek speeches plus `open_e` twice
    for the two surplus English turns -- about 6.55 -- where sliding the
    whole block back two nodes costs one cross-name match, 2.50.  So the DP
    slides, and 1454's English prints beside 1451.

    A pin after the gap alone does not hold it: the DP simply slides the
    block before the pin instead, which is what the first assertion records.
    A gap wants a pin on BOTH sides, so that the Greek speeches between them
    have no English left to take.
    """
    slot_names = _FROGS_LEAD_NAMES + [
        "Euripides", "Dionysus", "Euripides",
        "Dionysus", "Euripides",
        "Dionysus", "Aeschylus", "Dionysus", "Aeschylus",
    ]
    greek_chars = _FROGS_LEAD_GREEK + [58, 52, 189, 74, 35, 22, 66, 45, 113]
    english = _FROGS_LEAD_ENGLISH + [
        EnglishNode(name="Euripides", chars=95, text="Where Mistrust now has sway"),
        EnglishNode(name="Dionysus", chars=86, text="I don't quite follow"),
        EnglishNode(name="Euripides", chars=129, text="If we count all the men whom now we trust"),
        EnglishNode(name="Dionysus", chars=17, text="And what say you?"),
        EnglishNode(name="Aeschylus", chars=70, text="First tell me about the City"),
        EnglishNode(name="Dionysus", chars=32, text="Great Heavens, She loathes them!"),
        EnglishNode(name="Aeschylus", chars=31, text="And takes pleasure in the vile?"),
        EnglishNode(name="Dionysus", chars=48, text="Not she, but has perforce to let them serve her!"),
        EnglishNode(name="Aeschylus", chars=90, text="What hope of comfort is there for a City"),
    ]
    g1446, g1451, g1453, g1454 = 14, 15, 16, 17
    e1446, e1454 = 14, 15

    loose = _run_align(slot_names, greek_chars, english)
    by_g = dict(loose.pairs)
    assert english[by_g[g1451]].text == "And what say you?"  # two nodes early

    # The pin after the gap alone: the slide moves back, it does not stop.
    one_sided = _run_align(slot_names, greek_chars, english, forced=[(g1454, e1454)])
    by_g = dict(one_sided.pairs)
    assert english[by_g[g1451]].text == "I don't quite follow"

    both = _run_align(
        slot_names, greek_chars, english, forced=[(g1446, e1446), (g1454, e1454)]
    )
    by_g = dict(both.pairs)
    assert g1451 not in by_g and g1453 not in by_g
    assert english[by_g[g1454]].text == "And what say you?"
    assert english[by_g[g1446]].text == "If we count all the men whom now we trust"
