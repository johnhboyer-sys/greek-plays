r"""W. J. Hickie's Bohn Aristophanes, both volumes (1853) -- History Genie's
OCR of the vendored scans, rebuilt as the comparison bench for ten comedies
whose old archive.org/ABBYY-OCR Hickie bench was retired 2026-09-14 (commit
46a4bfa, "carried scan junk or leaked footnotes in 1,095 of 2,912 pieces"):

- Vol. II (``in.ernet.dli.2015.515630``, 2026-09-17, commit cdd81e6):
  Lysistrata (``third``), Thesmophoriazusae, Frogs, Ecclesiazusae and Wealth
  (``secondary`` on each -- Rogers's own Genie rebuild now holds ``third`` on
  those four).
- Vol. I (``in.ernet.dli.2015.515629``, 2026-09-22): Acharnians, Knights,
  Wasps, Peace and Birds (``secondary`` on each -- none of the five held a
  ``secondary`` slot before).

Clouds prints in vol. I too, between Knights and Wasps, but keeps Hickie from
the Perseus TEI untouched; this converter never emits a bench for it (it is
still needed as a placeholder in vol. I's own print order, ``_VOLUME_I``
below, so the boundary search for Wasps knows where Clouds's own footnotes
end).

Genie's own export of this volume is markdown-flavoured prose (see
``genie_text.py``): a bold or plain ``NAME.`` cue opens each speech inline
with its own text (Hickie is prose, unlike the Way/Storr/Rogers verse
volumes, so one Genie paragraph is usually one whole speech already), a
``[...]`` line is a stage direction, and a footnote call is a bare
superscript digit run, ``$^N$``/``$^{N}$``, or ``<sup>N</sup>`` -- all three
already normalised to ``[N]`` by ``genie_text._clean_line`` before this
module ever sees the text. Two things this volume needs beyond that:

- A handful of pages render a printed small-caps cue (the typeface Bohn uses
  for a speaker's name) as actual Unicode small-capital letters rather than
  plain bold uppercase (``Cʜʀ.`` for ``CHR.``) -- ~280 characters scattered
  from page 43 to the end of the volume, confirmed by grep, not a per-page
  style. Normalised back to ASCII uppercase here (``_fix_smallcaps``) before
  anything else runs, since ``genie_text.py``'s own cleaning has no reason to
  know about a typeface only this volume uses this way.
- A few of Wealth's inline footnote calls print as ``${}^N$`` -- an empty
  brace group before the caret that ``genie_text._DOLLAR_FOOTNOTE_RE``
  (``$^N$``/``$^{N}$``) does not match -- normalised the same way locally
  (``_DOLLAR_FOOTNOTE2_RE``).
- This volume also uses a literal underscore pair for a handful of italic
  asides (``(_aside_)``, ``[_Exit._]``) where every other page uses
  asterisks; ``genie_text.py`` only strips ``*...*``, so underscores are
  stripped here too (they never appear in this text for any other reason).

Footnote calls are numeric and reset every page (Bohn's own convention, not
a running count), so they are resolved per page exactly like Rogers's own
lettered calls: checked on their own page first, then the pages immediately
around it, since Genie occasionally attributes a page-foot definition to the
following page's paragraph run. Once a page prints its first footnote
definition (or a bare ``*``/``***`` divider), every remaining paragraph on
that SAME page is footnote apparatus, not dialogue -- Bohn always prints all
of a page's body text before any of its notes, so this is a safe, page-local
switch, not a guess (``_collect_footnotes``); it is what keeps a footnote's
own internal quotation, with its own embedded speaker-shaped abbreviation
(Thesm. p. 121's Plautus quotation, "TH. Quid valeam?", inside footnote 7),
out of the dialogue stream without a dedicated rule for that one line.

A handful of paragraphs are Hickie's own choice not to translate a passage
at all -- a Latin citation standing in for the English (Thesm.'s Echo scene,
mirroring Rogers's own declined 643-648 in the same scene) -- dropped by
exact text, logged, never spliced from anywhere (there is no earlier good
Hickie bench for these five plays to splice from, and the brief is explicit
that a genuine Genie-side gap is left bare rather than patched).

Genie drops a few physical pages outright in this volume; detected here from
a jump in the running head's own printed Greek line range (``_extract_range``
/ ``prev_hi``), exactly like the sibling Rogers lane, but -- per the brief --
never spliced from anything: only logged, and the stretch is left with no
Hickie text at all.

Vol. I (2026-09-22) needs three things beyond vol. II's own shapes, all
gated on ``cfg.genie is GENIE_TEXT_I`` so admitting them can never change
vol. II's already-shipped bench text (checked directly: regenerating vol.
II's five benches with this module produces no diff):

- A first entrance printed as a bare cue -- with or without a parenthetical
  direction -- on its OWN paragraph, the speech itself a separate paragraph
  right after (Acharnians's own ``DICÆOPOLIS (solus).``; Knights's own
  ``DEMUS.`` before Demus's first line). ``_BARE_CUE_PAREN_RE``/
  ``_BARE_CUE_RE`` set the pending cue and let the next paragraph's own
  ``writer.line`` call attach to it exactly as it would a same-line cue.
- A paren-wrapped SCENE direction (Knights's own ``(SCENE—the front of a
  large house.)``, where every vol. II play either brackets it or, once
  (Wealth), prints it bare) -- ``_PAREN_STAGE_RE``.
- A "### "-heading structural label Genie reads the same way as any other
  markdown heading (``genie_text._clean_line`` strips every ``#`` marker
  regardless of level): vol. I's own ``PARABASIS.`` (one per play, all
  five). Indistinguishable at the text level from a genuine bare cue once
  the shape above is admitted, so it is dropped as furniture by name
  (``_SECTION_LABEL_RE``) rather than risk a phantom "PARABASIS" speaker
  stealing the parabasis's own opening lines from the CHORUS cue that
  should get them.

Knights also reuses one abbreviation, "Dem.", for two different characters
at different points in the same play -- Demosthenes for the cold open,
before Demus is even named, then Demus himself once he enters (67 lines
before the switch, 85 after: neither name alone is an acceptable
approximation). ``_Play.split_cues`` flips the resolution once the
``DEMUS.`` marker paragraph is reached.

    python -m drama_pipeline.hickie_clean   # rewrite sources/bench/hickie/*.txt
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

from .config import SOURCES_DIR
from . import genie_text as gt
from .stage1_turn_english import parse_play_speeches

# History Genie's OCR of the vendored Bohn scans (John's own upload). Lives
# only in the main checkout's build/ scratch, never vendored into sources/,
# so these are absolute paths rather than SOURCES_DIR/BUILD_DIR -- the same
# posture as the sibling rogers_clean.py lane's own Genie input. ``GENIE_TEXT``
# keeps its original name (vol. II) for backward compatibility -- it is the
# default a bare `_Play(...)` gets when it does not name a volume.
GENIE_TEXT_II = Path("/Users/johnboyer/Developer/greek-plays/build/genie/in.ernet.dli.2015.515630.txt")
GENIE_TEXT_I = Path("/Users/johnboyer/Developer/greek-plays/build/genie/in.ernet.dli.2015.515629.txt")
GENIE_TEXT = GENIE_TEXT_II


class Converted(NamedTuple):
    text: str  # loeb-ocr turn-text
    speeches: int  # speaker cues written
    footnotes: int  # Footnotes: block entries written
    log: list[str]  # drops, gaps, uncertain footnote calls


@dataclass(frozen=True)
class _Play:
    title: str  # manifest `play:` heading, e.g. "THE THESMOPHORIAZUSAE"
    word: str  # bare printed heading word(s), AS GENIE PRINTS THEM (ligatures
    # and all -- "THESMOPHORIAZUSÆ", not "THESMOPHORIAZUSAE"), for matching
    # this volume's own running heads and page-range furniture.
    bench: str  # sources/bench/hickie/<bench>.txt
    # Genie's printed cue -> the full form a `speakers.*` alias key
    # recognises. An "Æ"/"æ" in the printed cue is ASCII-normalised (Æ->AE)
    # before this lookup, so keys here are always plain ASCII.
    abbrev: dict[str, str]
    # Paragraphs dropped outright, by exact (normalised) text: Hickie's own
    # editorial choice not to translate a passage (a Latin citation standing
    # in for lines he declined to render in English), never an OCR gap.
    drop_exact: tuple[str, ...] = field(default_factory=tuple)
    # Which volume's Genie export this play is printed in. Defaults to vol.
    # II so the five original records need no change (byte-identical rebuild).
    genie: Path = GENIE_TEXT_II
    # An abbreviation Bohn reuses for two different characters at different
    # points in the SAME play (Knights's own "Dem." -- Demosthenes for the
    # cold open, before Demus is even named, then Demus himself once he
    # enters and Demosthenes drops out; 67 lines before the switch, 85
    # after, 2026-09-22 count, so neither name alone is an acceptable
    # approximation): {abbrev_key: (name_before, name_after, marker_text)}.
    # `marker_text` is the exact (normalised) paragraph text that flips the
    # resolution -- every occurrence of `abbrev_key` up to it resolves to
    # `name_before`, every one from it on (inclusive) to `name_after`.
    split_cues: dict[str, tuple[str, str, str]] = field(default_factory=dict)


_LYSISTRATA = _Play(
    title="LYSISTRATA",
    word="LYSISTRATA",
    bench="lysistrata",
    abbrev={
        "LYS": "LYSISTRATA",
        "LRS": "LYSISTRATA",  # Genie's OCR of "Lys." (H1, 2026-09-17 round 2)
        "CALON": "CALONICE",
        "MYRRH": "MYRRHINA",  # Hickie's own dramatis-personae spelling
        "CIN": "CINESIAS",
        "COM": "COMMITTEE-MAN",  # Hickie's own name for the Magistrate
        "CHO. OF MEN": "CHORUS OF OLD MEN",
        "CHO. OF WOM": "CHORUS OF OLD WOMEN",
        "ATHEN": "ATHENIAN",  # the reconciliation-scene Athenian voice
        "SPART": "SPARTAN",  # the reconciliation-scene Spartan voice
        "LAMP": "LAMPITO",
        "HER": "HERALD",  # the Spartan herald announcing the peace embassy
        "MARK": "MARKET-LOUNGER",
        "SERV": "SERVANT",
    },
)

_THESMOPHORIAZUSAE = _Play(
    title="THE THESMOPHORIAZUSAE",
    word="THESMOPHORIAZUSÆ",
    bench="thesmophoriazusae",
    abbrev={
        "MNES": "MNESILOCHUS",
        "EUR": "EURIPIDES",
        "POL": "POLICEMAN",  # the Scythian archer, "POLICEMAN" in Hickie's own cast list
        "AGATH": "AGATHON",
        "CLISTH": "CLISTHENES",
        "CHO": "CHORUS",
        "SERV": "SERVANT OF AGATHON",
        "HER": "HERALD",  # the Female Herald opening the women's assembly
        "PRYT": "PRYTANIS",
    },
    # Hickie's Echo/Andromeda burlesque (mirroring Rogers's own declined
    # 643-648 in the same scene): an Ennius-Latin "invocation to night"
    # (footnote 3524, "taken verbatim from the prologue to the Andromeda...
    # rendered by Ennius") standing in for the English at this point, plus
    # a further, shorter Latin tercet a few lines on. Not an OCR gap --
    # Hickie himself never rendered these lines into English.
    drop_exact=(
        "Quæ cava cœli signi tenentibus",
        "O nox, sacra nox, quam tu longos",
        "Agitas cursus super astrigerum",
        "Vecta ætherii dorsum templi",
        "Et per Olympi veneranda loca.",
    ),
)

_FROGS = _Play(
    title="THE FROGS",
    word="FROGS",
    bench="frogs",
    abbrev={
        "BAC": "BACCHUS",
        "XAN": "XANTHIAS",
        "EUR": "EURIPIDES",
        "AESCH": "AESCHYLUS",  # printed "ÆSCH."; Æ->AE applied before lookup
        "AEAC": "AEACUS",  # printed "ÆAC."
        "HER": "HERCULES",
        "CHO": "CHORUS",
        "CHO. OF THE INITIATED": "CHORUS OF INITIATES",
        "CHA": "CHARON",
        "D. M": "DEAD MAN",
        "SER": "SERVANT OF PROSERPINE",
        "AESCH. AND EUR": "AESCHYLUS AND EURIPIDES",  # printed "ÆSCH. AND EUR."
        "PLU": "PLUTO",
        "PLUT": "PLUTO",
    },
)

_ECCLESIAZUSAE = _Play(
    title="THE ECCLESIAZUSAE",
    word="ECCLESIAZUSÆ",
    bench="ecclesiazusae",
    abbrev={
        "BLEP": "BLEPYRUS",
        "PRAX": "PRAXAGORA",
        "CHREM": "CHREMES",
        "YOUNG WOM": "YOUNG WOMAN",
        "NEIGH": "NEIGHBOUR",
        "MAID-SER": "MAID-SERVANT",
        "CHO": "CHORUS",
        "MAST": "MASTER",
        "FIRST SEMICHORUS": "CHORUS",  # "1st Semichorus."/"2nd Semichorus." -- the roster folds both into Chorus
        "SECOND SEMICHORUS": "CHORUS",
    },
)

_WEALTH = _Play(
    title="PLUTUS",
    word="PLUTUS",
    bench="wealth",
    abbrev={
        "CHR": "CHREMYLUS",
        "CA": "CARIO",
        "BL": "BLEPSIDEMUS",
        "PLU": "PLUTUS",
        "OLD WOM": "OLD WOMAN",
        "MER": "MERCURY",
        "J. M": "JUST MAN",
        "INF": "INFORMER",
        "CHO": "CHORUS",
        "YOU": "YOUTH",
        "POV": "POVERTY",
    },
)

_ACHARNIANS = _Play(
    title="THE ACHARNIANS",
    word="ACHARNIANS",
    bench="acharnians",
    genie=GENIE_TEXT_I,
    abbrev={
        "DIC": "DICAEOPOLIS",
        "LAM": "LAMACHUS",
        "CHO": "CHORUS",
        "CHOR": "CHORUS",
        "AMP": "AMPHITHEUS",
        "HER": "HERALD",
        "HUSB": "HUSBANDMAN",
        "SERV. OF EUR": "SERVANT",
        "MEG": "MEGARIAN",
        "EUR": "EURIPIDES",
        "AMB": "AMBASSADOR",
        "INF": "INFORMER",
        "BOEOT": "BOEOTIAN",
        "BAEOT": "BOEOTIAN",  # printed "Bæot." -- Æ->AE, ascii_cue
        "THEOR": "THEORUS",
        "NIC": "NICARCHUS",
        "DAUGH": "DAUGHTER OF DICAEOPOLIS",
        "WIFE": "WIFE OF DICAEOPOLIS",
        "PAR": "PARANYMPH",  # the groomsman at the wedding-feast scene
        "MESS": "MESSENGER",
    },
)

_KNIGHTS = _Play(
    title="THE KNIGHTS",
    word="KNIGHTS",
    bench="knights",
    genie=GENIE_TEXT_I,
    abbrev={
        "DEM. AND NIC": "DEMOSTHENES AND NICIAS",
        "DEM": "DEMOSTHENES",  # `split_cues` below switches this to DEMUS
        # once Demus himself enters.
        "NIC": "NICIAS",
        "CLEON": "PAPHLAGONIAN",
        "S. S": "SAUSAGE-SELLER",
        "S S": "SAUSAGE-SELLER",  # a scan without the internal period, once
        "AGOR": "SAUSAGE-SELLER",
        "CLE": "PAPHLAGONIAN",
        "CHO": "CHORUS",
        "DEMOSTH": "DEMOSTHENES",  # the closing scene's own longer-printed form
    },
    split_cues={"DEM": ("DEMOSTHENES", "DEMUS", "DEMUS.")},
)

_WASPS = _Play(
    title="THE WASPS",
    word="WASPS",
    bench="wasps",
    genie=GENIE_TEXT_I,
    abbrev={
        "PHIL": "PHILOCLEON",
        "BDEL": "BDELYCLEON",
        "CHO": "CHORUS",
        "XAN": "XANTHIAS",
        "BOY": "BOY",
        "ACCUS": "ACCUSER",
        "SOS": "SOSIAS",
        "PLAIN": "ACCUSER",  # Hickie's own "Plaintiff" for the dog-trial's accuser
        # -- the same role the roster already calls "Accuser" elsewhere.
        "CYD. DOG": "DOG",  # "the Cydathenian dog" (Bdel.'s own line just
        # before it) -- Bohn's printed cue names him by his epithet, not his
        # role; the roster has no "Cydathenian Dog" character of its own.
        "B. WOM": "BAKING-WOMAN",  # Hickie's own dramatis-personae name for
        # the bread-seller (roster: "Bread-seller").
    },
)

_PEACE = _Play(
    title="PEACE",
    word="PEACE",
    bench="peace",
    genie=GENIE_TEXT_I,
    abbrev={
        "TRY": "TRYGAEUS",
        "MER": "MERCURY",  # Hickie's own Latin name for Hermes (as Wealth's
        # own "MER": "MERCURY" already does in vol. II).
        "CHO": "CHORUS",
        "SER": "SERVANT",
        "1ST SER": "FIRST SERVANT",
        "2ND SER": "SECOND SERVANT",
        "1ST SERVANT": "FIRST SERVANT",
        "2ND SERVANT": "SECOND SERVANT",
        "HIER": "HIEROCLES",
        "WAR": "WAR",
        "TUM": "TUMULT",
        "DAUGH": "LITTLE DAUGHTER",
        "SON OF L": "SON OF LAMACHUS",
        "SON OF CL": "SON OF CLEONYMUS",
        "BREASTPL": "BREASTPLATE-MAKER",
        "SICKL": "SICKLE-MAKER",
        "CREST": "CREST-MAKER",
        "TRUMP": "TRUMPET-MAKER",
        "SPEAR": "SPEAR-MAKER",
        "HELM": "HELMET-MAKER",
    },
)

_BIRDS = _Play(
    title="THE BIRDS",
    word="BIRDS",
    bench="birds",
    genie=GENIE_TEXT_I,
    abbrev={
        "PISTH": "PISTHETAERUS",
        "PEISTH": "PISTHETAERUS",  # scan variants of the same abbreviation
        "PISHT": "PISTHETAERUS",
        "PIIS": "PISTHETAERUS",
        "EUEL": "EUELPIDES",
        "EP": "EPOPS",
        "CHO": "CHORUS",
        "HER": "HERALD",
        "HERC": "HERACLES",
        "PROM": "PROMETHEUS",
        "IR": "IRIS",
        "INF": "INFORMER",
        "NEPT": "NEPTUNE",  # Hickie's own Latin name for Poseidon (as
        # Peace's own "MER": "MERCURY" for Hermes)
        "TROCH": "TROCHILUS",
        "PROPH": "PROPHET",
        "MET": "METON",
        "CIN": "CINESIAS",
        "MESS": "MESSENGER",
        "FIRST MESS": "FIRST MESSENGER",
        "SECOND MESS": "SECOND MESSENGER",
        "POET": "POET",
        "COM": "COMMISSIONER",  # Hickie's own dramatis-personae name for
        # the Inspector (roster: "Inspector")
        "PRIEST": "PRIEST",
        "TRIB": "TRIBALLUS",
        "PAR": "PARRICIDE",
        "HAWK": "HAWKER OF DECREES",  # Hickie's own name for the Dealer
        # in Decrees (roster: "Decree-seller")
        "PHOE": "PHOENICOPTERUS",  # a non-speaking-role bird in the roster's
        # own dramatis personae -- folded into the generic "Bird" the roster
        # already uses for an unnamed bird cue (never a new character).
    },
)

PLAYS: dict[str, _Play] = {
    "lysistrata": _LYSISTRATA,
    "thesmophoriazusae": _THESMOPHORIAZUSAE,
    "frogs": _FROGS,
    "ecclesiazusae": _ECCLESIAZUSAE,
    "wealth": _WEALTH,
    "acharnians": _ACHARNIANS,
    "knights": _KNIGHTS,
    "wasps": _WASPS,
    "peace": _PEACE,
    "birds": _BIRDS,
}


@dataclass(frozen=True)
class _Volume:
    """One Genie-exported volume's own print order, used only to find where
    a play's footnotes/endnotes stop and the next play's front matter (or the
    volume's own back matter) begins (`_play_bounds`). ``order`` names every
    play printed in the volume in order, including one this converter never
    emits a bench for (vol. I's own Clouds, kept on the Perseus TEI) -- it
    still needs a place in the order and a heading word so the boundary
    search for its neighbours (Knights, Wasps) knows where to stop.
    """

    order: tuple[str, ...]
    # work_id -> bare printed heading word, for an `order` entry with no
    # `_Play` record of its own (only vol. I's "clouds"); a `PLAYS[work_id]`
    # entry's own `.word` is used instead when one exists.
    words: dict[str, str]
    # Where the LAST play's own footnotes/endnotes stop and the volume's own
    # cross-play back matter begins (an errata appendix, an "END OF VOL." --
    # never dialogue, never play-specific).
    end_sentinel: str


_VOLUME_II = _Volume(
    order=("lysistrata", "thesmophoriazusae", "frogs", "ecclesiazusae", "wealth"),
    words={},
    # Where Wealth's own footnotes/endnotes stop and the volume's cross-play
    # errata appendix begins (references plays in other volumes too -- never
    # Wealth-specific content, never dialogue).
    end_sentinel="SUPPLEMENTARY EMENDATIONS.",
)
_VOLUME_I = _Volume(
    order=("acharnians", "knights", "clouds", "wasps", "peace", "birds"),
    words={"clouds": "CLOUDS"},
    end_sentinel="END OF VOL. I.",
)


def _volume_for(work_id: str) -> _Volume:
    return _VOLUME_I if work_id in _VOLUME_I.order else _VOLUME_II


# ---------------------------------------------------------------------------
# Normalisation out of genie_text.py's own blast radius (Way/Storr shaped;
# this volume's own quirks, confirmed 2026-09-17).

# A printed small-caps cue rendered as actual Unicode small-capital letters
# rather than plain bold uppercase -- ~280 characters scattered from page 43
# to the end of the volume (grep confirmed, not a per-page style).
_SMALLCAPS = {
    "ᴀ": "A", "ʙ": "B", "ᴄ": "C", "ᴅ": "D", "ᴇ": "E", "ꜰ": "F", "ɢ": "G",
    "ʜ": "H", "ɪ": "I", "ᴊ": "J", "ᴋ": "K", "ʟ": "L", "ᴍ": "M", "ɴ": "N",
    "ᴏ": "O", "ᴘ": "P", "ǫ": "Q", "ʀ": "R", "ꜱ": "S", "ᴛ": "T", "ᴜ": "U",
    "ᴠ": "V", "ᴡ": "W", "ʏ": "Y", "ᴢ": "Z",
}
_SMALLCAPS_RE = re.compile("|".join(_SMALLCAPS))
# A run of Genie's OCR mistaking a bold small-caps "CHO. OF WOM./MEN." (and
# a bare "CHO.") for visually similar CYRILLIC letters instead of Latin ones
# -- confined to 4 letters, ~140 characters total (grep confirmed 2026-09-17):
# С (U+0421) for C, н (U+043D) for H, о (U+043E) for O, ғ (U+0493) for F.
_CYRILLIC_HOMOGLYPHS = {"С": "C", "н": "H", "о": "O", "ғ": "F"}
_CYRILLIC_RE = re.compile("|".join(_CYRILLIC_HOMOGLYPHS))
# Wealth's own rendering of a handful of inline footnote calls: an empty
# brace group before the caret, which genie_text._DOLLAR_FOOTNOTE_RE
# (`$^N$`/`$^{N}$`) does not match.
_DOLLAR_FOOTNOTE2_RE = re.compile(r"\$\{\}\^(\d+)\$")
# A joint cue printed with a lower-case "and" between its two abbreviated
# names (Knights p. 1, "DEM. and NIC."), where every other joint cue in
# either volume prints it upper-case ("ÆSCH. AND EUR."). `_CUE_RE`'s all-caps
# charset cannot match a lower-case "and" mid-name, so the first name alone
# would be read as the cue and "and NIC. Mumu..." would sit as its spoken
# text; anchored to the very start of a paragraph, where a cue prints, so it
# can never fire on a genuine sentence's own "X. and Y." (never seen upper-
# case in vol. II, so this is a no-op there).
_LOWER_AND_CUE_RE = re.compile(r"^([A-ZÆŒ]{1,15})\. and ([A-ZÆŒ]{1,15})\.")


def _normalize(text: str) -> str:
    text = _SMALLCAPS_RE.sub(lambda m: _SMALLCAPS[m.group(0)], text)
    text = _CYRILLIC_RE.sub(lambda m: _CYRILLIC_HOMOGLYPHS[m.group(0)], text)
    text = _DOLLAR_FOOTNOTE2_RE.sub(lambda m: f"[{m.group(1)}]", text)
    text = _LOWER_AND_CUE_RE.sub(lambda m: f"{m.group(1)}. AND {m.group(2)}.", text)
    # A stray acute accent OCR reads into a running head's own title word
    # ("THE ECCLÉSIAZUSÆ." for "THE ECCLESIAZUSÆ.", 2026-09-17 check) --
    # `_is_running_head_line`'s exact-substring check would otherwise miss
    # the whole line, which reads as a false Genie gap the same way an
    # unrecognised heading shape does.
    text = text.replace("É", "E")
    # A literal `<br>` tag, printed alone right before Lysistrata's own
    # "END OF..." marker -- genie_text.py strips `<span>`/`<center>`/
    # `<small>`/`<p>`, never `<br>` (two occurrences total in this volume).
    text = re.sub(r"<br\s*/?>", "", text, flags=re.I)
    # This volume's own literal-underscore italics ("(_aside_)", "[_Exit._]")
    # -- genie_text.py only strips `*...*`; underscores never appear here
    # for any other reason.
    text = text.replace("_", "")
    return re.sub(r" {2,}", " ", text).strip()


def _ascii_cue(printed: str) -> str:
    return printed.replace("Æ", "AE").replace("æ", "ae").replace("Œ", "OE").replace("œ", "oe")


# ---------------------------------------------------------------------------
# Furniture: running heads, page numbers, dividers -- never dialogue. This
# volume prints a page's running head in several shapes: three separate
# physical lines ("302" / "LYSISTRATA." / "52--71."), page-and-title-first on
# one line ("390 LYSISTRATA. 14—33."), range-first ("34—51. LYSISTRATA.
# 391"), or -- where Genie read the head as a markdown table row -- pipe-
# delimited in either order ("1224—1238. | LYSISTRATA. | 445", "448 |
# LYSISTRATA. | 1313—1321."), each usually followed by the table's own
# separator row ("--- | --- | ---", "- | - | -"). A recognised-heading check
# that misses one of these shapes does not just drop a line: it leaves
# `prev_hi` stale, so the NEXT (recognised) heading looks like a jump and
# gets logged as a Genie-side gap that is not real -- and the false gap
# closes whatever speech was open, dropping the real dialogue that follows
# it (2026-09-17 regression, confirmed against every "gap" this converter
# first reported; the pipe-table shape alone accounts for most of them).

_PAGE_NUM_RE = re.compile(r"^\d{1,4}$")
_STAR_RE = re.compile(r"^\*+$")
# A markdown table's own separator row, or a run of nothing but dashes: never
# dialogue, whatever the exact dash/pipe count Genie prints.
_DIVIDER_RE = re.compile(r"^[\-|\s]+$")
_END_OF_RE = re.compile(r"^END OF (?:THE )?[A-ZÆŒ ]+\.?$")
_RANGE_RE = re.compile(r"(\d{1,4})\s*[–—\-]{1,4}\s*(\d{1,4})")
_BARE_RANGE_RE = re.compile(rf"^{_RANGE_RE.pattern}\.?$")
# A structural section label Genie read as a markdown ``### `` heading, never
# a speaker -- ``genie_text._clean_line`` strips every ``#`` heading marker
# regardless of level, so by the time this module sees the text a section
# label like "### PARABASIS." is indistinguishable from a genuine bare cue's
# own paragraph (`_BARE_CUE_RE` below, added for vol. I's own first-entrance
# shape). Confirmed as the only such label vol. I actually uses (five
# occurrences, one per play: Acharnians, Knights, Wasps, Peace, Birds);
# dropped as furniture there, rather than risk a phantom "PARABASIS" speaker
# picking up the parabasis's own opening lines instead of the CHORUS cue
# that should get them (Acharnians, 2026-09-22 check). Vol. II ALSO prints
# one (Thesm. p. 161) but is left untouched -- `_BARE_CUE_RE` did not exist
# when vol. II was built (commit cdd81e6), so it never became a phantom cue
# there in the first place (the paragraph fell through to a plain
# `writer.line` append, already in the committed bench, and stays that way:
# regenerating vol. II must stay byte-identical, so this fix is vol. I only).
_SECTION_LABEL_RE = re.compile(r"^PARABASIS\.(?:\[\d+\])?$")


def _bare_heading_re(word: str) -> re.Pattern[str]:
    """An EXACT bare title heading (its own page, optionally prefixed by a
    clean page number) -- used only to locate a specific occurrence
    (`_real_start`/`_play_bounds`), where matching the wrong, noisier line
    would pick the wrong boundary. Furniture-skipping in the main convert
    loop uses the far more tolerant `_is_running_head_line` below instead,
    since a running head survives OCR in too many damaged shapes to match
    exactly and skipping one wrongly is the costlier mistake there (a
    missed heading looks like a real Genie gap and drops the dialogue after
    it -- 2026-09-17 regression)."""
    return re.compile(rf"^(?:\d{{1,4}}\s+)?(?:THE\s+)?{re.escape(word)}\.?$")


def _is_running_head_line(text: str, word: str) -> bool:
    """A running head/page-furniture line, in ANY of the shapes this volume
    prints one -- three separate physical lines, page-and-title-first,
    range-first, a markdown table row (pipe-delimited, either column
    order) -- and in any of the ways OCR further damages it (a garbled
    leading page number, three dashes instead of one or two, a stray
    bracket or comma, a trailing period after the trailing page number).
    Rather than enumerate every shape exactly (this module tried; new ones
    kept surfacing), this checks the one invariant every one of them
    shares and no real prose paragraph ever does: it carries the play's own
    title word and NOT ONE lower-case letter anywhere -- a genuine
    speech, stage direction, or footnote (even one quoting Latin) always
    has at least one. `_extract_range` below still needs the play's own
    Greek line range out of a heading recognised this way; it re-derives
    that by just finding the first ``NNN-NNN``-shaped run inside it,
    wherever the OCR-damaged punctuation around it landed."""
    if any(c.islower() for c in text):
        return False
    return word in text


def _extract_range(text: str, word: str) -> tuple[int, int] | None:
    """The Greek line range printed on a running head, wherever it landed in
    the line -- or on a bare range-only fragment (the three-physical-line
    heading shape, whose title sits on its own, separate paragraph, so
    `_is_running_head_line` would not itself recognise this line as one)."""
    m = _BARE_RANGE_RE.match(text)
    if not m:
        if not _is_running_head_line(text, word):
            return None
        m = _RANGE_RE.search(text)
        if not m:
            return None
    lo, hi = int(m.group(1)), int(m.group(2))
    # The printer's own running head is sometimes reversed on the page
    # itself, not just OCR-damaged ("126—113. THE THESMOPHORIAZUSÆ.",
    # "1229—1214. THE FROGS." -- both confirmed 2026-09-17 against
    # continuous, un-gapped dialogue either side): a real range only ever
    # increases, so a reversed pair is swapped back rather than read as a
    # (backwards) jump.
    return (lo, hi) if lo <= hi else (hi, lo)


def _is_furniture(text: str, word: str) -> bool:
    return bool(
        _DIVIDER_RE.match(text)
        or _PAGE_NUM_RE.match(text)
        or _END_OF_RE.match(text)
        or _is_running_head_line(text, word)
        or _BARE_RANGE_RE.match(text)
    )


# ---------------------------------------------------------------------------
# Cues and directions.

_CUE_RE = re.compile(r"^([A-ZÆŒ][A-ZÆŒ .'’\-]{0,30})\.\s+(\S.*)$")
# "NAME (direction). text" / "NAME. (direction). text" -- a first entrance
# spelled in full, with or without a period between the name and its
# parenthetical (B round 3 item 3, 2026-09-17: "PRAXAGORA. (coming forward
# out of her hiding-place). I was lying awake..." used to match `_CUE_RE`
# first -- checked before this pattern -- leaving the whole parenthetical
# sitting in the speech text instead of becoming its own direction; this
# pattern is now tried first).
_CUE_PAREN_RE = re.compile(r"^([A-ZÆŒ][A-ZÆŒ .'’\-]{0,30})\.?\s*\(([^)]*)\)\.?\s+(\S.*)$")
# A cue with no text of its own on the same paragraph -- vol. I's own first
# entrance shape (Acharnians opens "**DICÆOPOLIS (*solus*).**" as its own
# printed line, the speech itself a SEPARATE paragraph right after; vol. II
# never prints a first entrance this way, so this never fires there). Tried
# only once `_CUE_PAREN_RE`/`_CUE_RE` (which both require trailing text on
# the SAME line) have already missed -- a cue this shaped just sets the
# pending cue and/or prints its direction; the next paragraph's `writer.line`
# call attaches to it exactly as it would a same-line cue.
_BARE_CUE_PAREN_RE = re.compile(r"^([A-ZÆŒ][A-ZÆŒ .'’\-]{0,30})\.?\s*\(([^)]*)\)\.?$")
_BARE_CUE_RE = re.compile(r"^([A-ZÆŒ][A-ZÆŒ .'’\-]{0,30})\.$")
# A "characters present" cast list opening a scene (Birds's own
# "EUELPIDES, PISTHETAIRUS." -- no SCENE direction of its own precedes it,
# unlike every other play in either volume): used only by `_real_start`, to
# recognise the title heading right before it as the play's real start (the
# main body loop already drops a line shaped like this as pre-speech
# furniture once it is inside the converted range, via the final
# `writer._pending_cue is None` check -- this regex is not needed there).
_CAST_LIST_RE = re.compile(r"^[A-ZÆŒ][A-ZÆŒ, .'’\-]*,[A-ZÆŒ, .'’\-]*\.(?:\[\d+\])?$")
# A whole-line direction Genie prints without its outer brackets: this
# volume's own "SCENE—..." openers and one bare "Enter ..." (2026-09-17
# check finds both in Wealth).
_STAGE_VERB_RE = re.compile(r"^(?:SCENE[—:]|Enter\b|Exit\b|Exeunt\b|Re-enters?\b|Enters\b)", re.I)
# The same opening SCENE direction, but paren-wrapped rather than bracketed
# or bare (Knights's own "(SCENE—the front of a large house.)" -- vol. II
# always uses brackets or nothing; only Knights, in either volume, wraps it
# in parens). A whole match (not `_STAGE_VERB_RE` on the inner text alone)
# so it is never confused with `_CUE_PAREN_RE`'s "NAME (direction). text"
# shape, which always has a name before the "(".
_PAREN_STAGE_RE = re.compile(r"^\((SCENE[—:].*)\)$", re.I)

# A numbered or adjective-qualified chorus-member cue ("2nd Wom.", "5TH WOM.",
# "1ST OLD WOM.", "Young Man.", "1st Innk.", "2nd Cit.", "1st Semichorus."):
# printed in a mix of case and abbreviation Genie does not always render as
# plain bold uppercase the way a main character's cue is (2026-09-17 check,
# ~280 such lines across Lysistrata/Thesm./Ecclesiazusae/Frogs -- none in
# Wealth). `_CUE_RE`'s all-uppercase-letters charset cannot match a leading
# digit or a lower-case word at all, so this is a dedicated fallback,
# restricted to this specific closed vocabulary rather than opened up to any
# case -- a real prose sentence never opens with nothing but these words.
_MIXED_TOKEN = r"(?:[1-9](?:ST|ND|RD|TH)|OLD|YOUNG|WOM(?:AN)?|MAN|CHO(?:RUS)?|INNK(?:EEPER)?|CIT(?:IZEN)?|SEMICHORUS)"
_MIXED_CUE_RE = re.compile(rf"^((?:{_MIXED_TOKEN})(?:\s+{_MIXED_TOKEN})*)\.\s+(\S.*)$", re.I)
# The same numbered/mixed-case cue, immediately followed by a parenthetical
# direction ("1ST WOMAN (entering with a lamp).", "Young Woman (looking out
# from an opposite window)."): ecclesiazusae findings 2 and 7 (B round 3
# item 3, 2026-09-17) -- `_MIXED_CUE_RE` needs a bare "." right after the
# name, so a name followed instead by "(" never matched at all and fell
# through as a continuation of whatever speech was already open.
_MIXED_CUE_PAREN_RE = re.compile(
    rf"^((?:{_MIXED_TOKEN})(?:\s+{_MIXED_TOKEN})*)\.?\s*\(([^)]*)\)\.?\s+(\S.*)$", re.I
)
_ORDINAL_WORDS = {
    1: "FIRST", 2: "SECOND", 3: "THIRD", 4: "FOURTH", 5: "FIFTH",
    6: "SIXTH", 7: "SEVENTH", 8: "EIGHTH", 9: "NINTH",
}
_ORDINAL_RE = re.compile(r"[1-9](?:ST|ND|RD|TH)", re.I)


def _normalize_mixed_cue(raw: str) -> str:
    raw = raw.upper()
    raw = _ORDINAL_RE.sub(lambda m: _ORDINAL_WORDS[int(m.group(0)[0])], raw)
    raw = re.sub(r"\bWOM\b", "WOMAN", raw)
    raw = re.sub(r"\bINNK\b", "INNKEEPER", raw)
    raw = re.sub(r"\bCIT\b", "CITIZEN", raw)
    return raw


class _Writer:
    def __init__(self, title: str) -> None:
        self.out: list[str] = [title, ""]
        self._pending_cue: str | None = None
        self._open = False
        self.speeches = 0

    def cue(self, name: str) -> None:
        if self._open:
            self.out.append("")
            self._open = False
        self._pending_cue = name

    def line(self, text: str) -> None:
        if not text:
            return
        if self._pending_cue is not None:
            self.out.append(f"{self._pending_cue}. {text}")
            self._pending_cue = None
            self._open = True
            self.speeches += 1
        else:
            self.out.append(text)

    def direction(self, text: str) -> None:
        text = text.strip()
        if self._pending_cue is not None:
            # A direction between a cue and its own first line of words --
            # print it as its own line; the cue stays pending across it.
            self.out.append(f"[{text}]")
            return
        if self._open:
            self.out.append(f"[{text}]")
        else:
            self.out.append(f"[{text}]")
            self.out.append("")

    def gap_marker(self) -> int:
        """The index `out` a Genie-caused gap opens at -- logged only (the
        brief is explicit: a gap is never spliced), so the writer's own cue
        state is left exactly as it was. In every gap checked by hand
        (2026-09-17), the paragraph right after the gap is the plain
        continuation of the speech the gap interrupted -- Genie missing a
        page does not usually land on a speaker change -- so leaving
        `_pending_cue`/`_open` untouched lets that continuation keep its
        speaker instead of falling out as unattributed, silently dropped
        text (the earlier behaviour, which closed the speech here)."""
        return len(self.out)

    def finish(self, footnotes: list[tuple[int, str]]) -> str:
        if self._open:
            self.out.append("")
        if footnotes:
            self.out.append("Footnotes:")
            for k, text in footnotes:
                self.out.append(f"[{k}] {text}")
        return "\n".join(self.out).rstrip("\n") + "\n"


# ---------------------------------------------------------------------------

_FN_DEF = re.compile(r"^\[(\d{1,3})\]\s*(.*)$")
_EMBEDDED_FN = re.compile(r"\[(\d{1,3})\]")


def _split_definitions(text: str) -> list[tuple[str, str]] | None:
    """``[(num, note_text), ...]`` if ``text`` opens with a footnote call
    (one or more, run together on a single printed line -- a very short
    note packed with the next), else ``None``."""
    if not _FN_DEF.match(text):
        return None
    matches = list(_EMBEDDED_FN.finditer(text))
    out = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out.append((m.group(1), text[m.end() : end].strip()))
    return out


def _count_speeches(text: str, title: str) -> int:
    speeches, _notes = parse_play_speeches(text, title, format="loeb-ocr", verse=False)
    return len(speeches)


def _load_genie(cfg: _Play) -> list[gt.Paragraph]:
    return gt.paragraphs(cfg.genie)


def _real_start(paras: list[gt.Paragraph], cfg: _Play) -> int:
    """The play's own title page: the LAST heading occurrence immediately
    followed by a real cue+text line, a paren-cue line, or a bracket/SCENE
    direction (the volume's own contents-adjacent running heads and the
    ARGUMENT's italic-quoted title never precede one of these). Vol. I's own
    extra first-entrance shapes -- a bare (text-of-its-own-paragraph) cue, a
    "characters present" cast list, a paren-wrapped SCENE direction -- are
    checked only for a vol. I play (`cfg.genie is GENIE_TEXT_I`): vol. II's
    own five plays never need them, and admitting them unconditionally would
    also let them fire deeper in the main body loop (`_convert_body`) on a
    vol. II paragraph that already converts correctly a different way,
    changing its already-shipped bench text (checked 2026-09-22: it did,
    for Thesm.'s "FEMALE HERALD."/"PARABASIS." lines) -- regenerating vol.
    II must stay byte-identical."""
    word = cfg.word
    heading = _bare_heading_re(word)
    vol_i = cfg.genie is GENIE_TEXT_I
    start: int | None = None
    for i, p in enumerate(paras):
        if not heading.match(p.text.strip()):
            continue
        if i + 1 >= len(paras):
            continue
        nxt = _normalize(paras[i + 1].text)
        if (
            nxt.startswith("[")
            or _STAGE_VERB_RE.match(nxt)
            or _CUE_RE.match(nxt)
            or _CUE_PAREN_RE.match(nxt)
            or (
                vol_i
                and (
                    _PAREN_STAGE_RE.match(nxt)
                    or _BARE_CUE_PAREN_RE.match(nxt)
                    or _CAST_LIST_RE.match(nxt)
                )
            )
        ):
            start = i
    if start is None:
        raise ValueError(f"play heading {word!r} never precedes a speech")
    return start


def _play_bounds(paras: list[gt.Paragraph], work_id: str) -> tuple[int, int]:
    """(start, end): `start` is the title page the first speech follows;
    `end` is the NEXT play's own bare-heading front-matter marker (its
    footnotes/endnotes run right up to that point), or the volume's own
    back-matter sentinel for the last play in its volume."""
    cfg = PLAYS[work_id]
    volume = _volume_for(work_id)
    i = volume.order.index(work_id)
    start = _real_start(paras, cfg)
    if i + 1 < len(volume.order):
        next_id = volume.order[i + 1]
        next_word = PLAYS[next_id].word if next_id in PLAYS else volume.words[next_id]
        next_heading = _bare_heading_re(next_word)
        end = next(j for j, p in enumerate(paras) if j > start and next_heading.match(p.text.strip()))
    else:
        end = next(j for j, p in enumerate(paras) if p.text.strip() == volume.end_sentinel and j > start)
    return start, end


def _looks_like_cue(text: str) -> bool:
    return bool(
        _CUE_RE.match(text)
        or _CUE_PAREN_RE.match(text)
        or _MIXED_CUE_RE.match(text)
        or _MIXED_CUE_PAREN_RE.match(text)
    )


# ---------------------------------------------------------------------------
# H1 (2026-09-17 round 2 brief, lysistrata findings 1, 3, 5, 10): Bohn's
# critical apparatus, and abbreviated inline cues, both defeat the cue
# matchers above.

# A page-foot critical-apparatus block Genie kept as running prose -- an
# editor's own note, quoted or summarised, continuing onto a fresh page with
# no leading `[N]` of its own to be caught by `_collect_footnotes` (its call
# was embedded mid-sentence in the SPEECH before it, not at the head of a
# paragraph): editors' surnames together with a citation-shaped fragment
# (`Gr. Gr.`, `Vig. n.`, a play abbreviation + line numbers, a page
# reference, a bare run of comma-separated numbers). A real speech never
# carries either signal, so both are required (finding 3: nine places in
# Lysistrata alone, checked by hand against every hit this pair catches).
_APPARATUS_EDITOR = re.compile(
    r"\b(?:Kr[uü]ger|Hermann|Dindorf|Enger|Meineke|Bekker|Elmsley|Brunck|"
    r"Bergk|Reisig|Fritzsche|Blaydes|Bothe|Dobree|Lobeck|Porson)\b"
)
# `vs\.\s*\d` (a bare verse-number citation, "vs. 35") and `Acharn\.` (the
# one play abbreviation the original list left out) were still missing, so a
# note that cites only by verse number or only in the Acharnians never had
# its citation half recognised (Grok's read of Lane B round 2,
# `review-lane-b-r2-grok-findings.md`, 2026-09-17): lysistrata bench 57
# ("...Βοιωτίους τε in vs. 35 corresponds..."), 505, 1096; ecclesiazusae
# 524, 547; thesmophoriazusae 165, 169, 592, 682, 954.
_APPARATUS_CITATION = re.compile(
    r"\b(?:Gr\.\s*Gr\.|Vig\.\s*n\.|Frag(?:m)?\.|Eccles\.|Aves,|Vesp\.|Nub\.|"
    r"Equit\.|Thesm\.|Ran\.|Pax,|Av\.|Plut\.|Acharn\.|vs\.\s*\d|p\.\s*\d|§\s*\d|"
    r"\d+,\s*\d+,\s*\d+)"
)
# A paragraph that OPENS on a bare editor surname ("Brunck. "This passage
# has been misunderstood..."") is apparatus even when it carries no
# citation-shaped fragment of its own -- Aristophanes never opens a speech
# by naming a 19th-century German philologist. Anchored to the paragraph's
# own start (after any leading OCR junk) so it cannot fire on an editor's
# name appearing inside a genuine sentence.
_APPARATUS_OPENING_EDITOR = re.compile(
    r"^[\s*'’\"“”.,]*(?:Kr[uü]ger|Hermann|Dindorf|Enger|Meineke|Bekker|Elmsley|"
    r"Brunck|Bergk|Reisig|Fritzsche|Blaydes|Bothe|Dobree|Lobeck|Porson)\.\s"
)


def _is_apparatus_paragraph(text: str) -> bool:
    if _APPARATUS_OPENING_EDITOR.match(text):
        return True
    return bool(_APPARATUS_EDITOR.search(text)) and bool(_APPARATUS_CITATION.search(text))


# A sentence-final mark: an embedded abbreviated cue only opens a new speech
# right after one (or at the very start of the paragraph) -- never mid-clause
# (a footnote's own "Cf. Lys. p. 213" is inside a `[N]`-headed definition
# already consumed by `_collect_footnotes` before this ever runs, but the
# guard costs nothing and documents the intent).
_SENTENCE_END = re.compile(r"[.!?]$")

# OCR furniture Genie sometimes glues onto the very front of a paragraph
# ahead of its own opening cue: a stray quote or apostrophe carried over
# from the line above (lysistrata.txt "' LYS.."), or Bohn's own unnumbered
# footnote asterisk (lysistrata.txt "* CHO. OF WOM.", the Beetle/Eagle
# taunt -- swallowed whole into the previous speaker's turn before this,
# 2026-09-17 round 2 rebuild check). None of it is spoken text; a cue
# right after it is still the paragraph's own opening cue, not a mid-clause
# one, so it needs no preceding sentence-final punctuation of its own.
_LEADING_JUNK = re.compile(r"^[\s*'’\"“”.,]+")


def _abbrev_cue_pattern(abbrev: dict[str, str]) -> re.Pattern[str]:
    """A Bohn abbreviated speaker cue in whatever case Genie's OCR kept it.

    Genie only bolds/capitalises a paragraph's OPENING speaker; a quick
    interjecting cue -- or one whose own paragraph never got the small-caps
    treatment -- survives as ordinary running-text case (`Lys.`, `Com.`,
    `Cho. of Wom.`), which `_CUE_RE`'s ALL-CAPS charset cannot match, or
    (worse) partially matches and mis-splits (finding 5: `_CUE_RE` reads
    `CHO. OF Wom.` as cue "CHO", leaving "OF Wom." as the first words of the
    speech). Built from the same `abbrev` map the paragraph-head cue already
    resolves through, longest key first, so a multi-word key is matched
    whole before a shorter one inside it gets the chance to.
    """
    alts = sorted((re.escape(key) for key in abbrev), key=len, reverse=True)
    return re.compile(r"(?P<name>" + "|".join(alts) + r")\.(?=\s)", re.IGNORECASE)


def _split_abbrev_cues(
    text: str, abbrev: dict[str, str]
) -> list[tuple[str | None, str]]:
    """``[(cue_or_None, piece), ...]``: ``text`` cut at every embedded Bohn
    abbreviated cue that opens a new sentence, ``cue`` resolved to the full
    roster name. A piece with ``cue is None`` is text with no cue of its own
    -- continuation of whatever speech was already open (Bohn never opens a
    paragraph on plain text before its first embedded cue, but the caller
    treats this exactly as it always has: appended to the open speech, or
    logged and dropped if none is open). Returns ``[(None, text)]``
    unchanged if ``text`` carries no recognised embedded cue at all."""
    pattern = _abbrev_cue_pattern(abbrev)
    lead = _LEADING_JUNK.match(text)
    lead_end = lead.end() if lead else 0
    cuts: list[tuple[int, int, str]] = []
    for m in pattern.finditer(text):
        start = m.start()
        if start > lead_end:
            preceding = text[:start].rstrip()
            if not preceding or not _SENTENCE_END.search(preceding[-1:]):
                continue
        key = m.group("name").upper()
        if key not in abbrev:
            continue
        cuts.append((start, m.end(), abbrev[key]))
    if not cuts:
        return [(None, text)]
    pieces: list[tuple[str | None, str]] = []
    if cuts[0][0] > 0:
        leading = text[: cuts[0][0]].strip()
        if leading and re.search(r"\w", leading):
            pieces.append((None, leading))
    for idx, (_start, cue_end, cue) in enumerate(cuts):
        piece_end = cuts[idx + 1][0] if idx + 1 < len(cuts) else len(text)
        pieces.append((cue, text[cue_end:piece_end].strip()))
    return [(cue, piece) for cue, piece in pieces if piece]


def _collect_footnotes(
    paras: list[gt.Paragraph], start: int, end: int, word: str
) -> tuple[dict[int, dict[str, str]], set[int], list[str]]:
    """Page-local footnote definitions and the set of paragraph indices they
    (and their continuations) consume. Once a page prints its first
    definition or a bare divider, every remaining paragraph is footnote
    apparatus, not dialogue, until a running head or a real cue is seen --
    Bohn always prints a page's whole body before any of its own notes, but
    a note too long for its own page runs on, uninterrupted, straight into
    the TOP of the next one, before that page's own running head or body
    even starts (Frogs p. 207/208, 2026-09-17 check: a page-only reset here
    left a genuine note continuation, quoting Greek in the middle of a
    grammatical point, sitting as if it were BACCHUS's own next line of
    dialogue). This is what also keeps a footnote's own embedded,
    speaker-shaped abbreviation (a Latin play quoted inside a note) out of
    the dialogue stream with no dedicated rule for that one line."""
    page_notes: dict[int, dict[str, str]] = {}
    consumed: set[int] = set()
    log: list[str] = []
    footnote_mode = False
    current_key: tuple[int, str] | None = None
    for i in range(start, end):
        p = paras[i]
        text = _normalize(p.text)
        if not text:
            continue
        if _DIVIDER_RE.match(text) or _END_OF_RE.match(text) or _PAGE_NUM_RE.match(text):
            # Furniture, not a definition and not a continuation, however
            # deep into a page's footnote block it turns up -- an "END OF
            # THE X." marker (and the stray "<br>" pair Lysistrata's own
            # prints right before it) would otherwise glue onto the last
            # open note's own text (2026-09-17 check).
            continue
        if footnote_mode and (
            _is_running_head_line(text, word) or _looks_like_cue(text) or _BARE_RANGE_RE.match(text)
        ):
            # Real body content resumes -- the ONLY thing (besides a fresh
            # definition, checked below) allowed to end a run of footnote
            # apparatus, since a page change alone does not.
            footnote_mode = False
            current_key = None
        if _STAR_RE.match(text):
            footnote_mode = True
            consumed.add(i)
            continue
        # A footnote definition is checked BEFORE the Greek-paragraph drop,
        # not after: several of this volume's own shortest notes are almost
        # entirely a quoted Greek phrase ("[3] Eur. El. 231, ποῦ γῆς ὁ
        # τλήμων..."), Greek-majority by letter count -- read as "just a
        # Greek quote" by the same check that rightly drops a bare inline
        # scholion, a definition this shaped was silently skipped instead of
        # registered, so its own call resolved to nothing AND the page's
        # next real definition's number never got read as a fresh one
        # either (2026-09-17 regression).
        defs = _split_definitions(text)
        if defs is not None:
            footnote_mode = True
            for num, body in defs:
                if body:
                    page_notes.setdefault(p.page, {})[num] = body
                    current_key = (p.page, num)
            consumed.add(i)
            continue
        if footnote_mode:
            # A continuation is swallowed regardless of Greek content too
            # (the same short-note shape above can run its Greek quote onto
            # a second printed line before the citation that follows it).
            if current_key is not None:
                pg, num = current_key
                page_notes[pg][num] = f"{page_notes[pg][num]} {text}".strip()
            else:
                log.append(
                    f"uncertain\tfootnote-area text on page {p.page} with no open note, dropped: {text[:60]!r}"
                )
            consumed.add(i)
            continue
        if gt.is_greek_paragraph(text):
            # A free-standing Greek quotation in the dialogue area itself
            # (a scholion quoted inline, never Hickie's own English) --
            # dropped only here, once a footnote shape and footnote_mode
            # have both been ruled out.
            continue
    return page_notes, consumed, log


def _convert_body(
    paras: list[gt.Paragraph], start: int, end: int, cfg: _Play
) -> tuple[str, int, int, list[str], list[tuple[int, int, int]]]:
    page_notes, consumed, log = _collect_footnotes(paras, start, end, cfg.word)

    def _resolve(page: int, num: str) -> str | None:
        for pg in (page, page - 1, page + 1, page - 2, page + 2):
            if pg in page_notes and num in page_notes[pg]:
                return page_notes[pg][num]
        return None

    # Every one of these five comedies renders Hickie with `footnotes: false`
    # (explicit in the manifest for lysistrata, implicit elsewhere -- only
    # `slot: primary` defaults true, and Hickie never holds that slot): the
    # reader loads one `footnotes.json` per play, and the primary already
    # carries its own. A renumbered `[N]` marker written into this bench
    # text would therefore resolve to no popup at all and print as a dead
    # bracketed digit in the reader (H1, 2026-09-17 round 2 brief: 465 raw
    # markers in Lysistrata alone, corpus-wide across the five). `footnotes`
    # stays empty and unused below on purpose -- kept only so this
    # function's shape matches the sibling Rogers/Way lanes that DO render a
    # column's own notes, should this column's footnotes ever be turned on.
    footnotes: list[tuple[int, str]] = []

    def _resolve_calls(text: str, page: int) -> str:
        def repl(m: "re.Match[str]") -> str:
            num = m.group(1)
            if _resolve(page, num) is None:
                log.append(f"uncertain\tfootnote call [{num}] on page {page} has no definition nearby")
            return ""

        # Genie's own digit-footnote cleaning already prints the call
        # attached tight against its word with no space of its own
        # ("Bacchus,[1]"); no leading space needed to protect against the
        # all-caps-cue-swallows-the-call risk Rogers's own lettered-call
        # rebuild had to guard against (Hickie's cues are never long
        # shouted lines ending right at a call).
        resolved = _EMBEDDED_FN.sub(repl, text)
        return re.sub(r" {2,}", " ", resolved).strip()

    writer = _Writer(cfg.title)
    prev_hi: int | None = None
    gaps: list[tuple[int, int, int]] = []

    # `cfg.split_cues`: a mutable working copy of the abbreviation table,
    # flipped in place once each marker paragraph is reached (see `_Play`).
    abbrev = dict(cfg.abbrev)
    split_markers: dict[int, tuple[str, str]] = {}
    for key, (_before, after, marker_text) in cfg.split_cues.items():
        for i in range(start, end):
            if _normalize(paras[i].text).strip() == marker_text:
                split_markers[i] = (key, after)
                break

    for i in range(start, end):
        if i in split_markers:
            key, after = split_markers[i]
            abbrev[key] = after
        if i in consumed:
            continue
        p = paras[i]
        text = _normalize(p.text)
        if not text:
            continue
        if gt.is_greek_paragraph(text):
            continue

        rng = _extract_range(text, cfg.word)
        if rng is not None:
            lo, hi = rng
            if prev_hi is not None and lo > prev_hi + 1:
                gaps.append((writer.gap_marker(), prev_hi + 1, lo - 1))
                log.append(
                    f"gap\tGreek {prev_hi + 1}-{lo - 1} has no Genie text (heading jumps {prev_hi}->{lo})"
                )
            prev_hi = hi
            continue
        if _is_furniture(text, cfg.word):
            continue
        if cfg.genie is GENIE_TEXT_I and _SECTION_LABEL_RE.match(text):
            continue
        if text in cfg.drop_exact:
            log.append(f"dropped\tHickie's own Latin substitution, not English: {text[:60]!r}")
            continue
        if _is_apparatus_paragraph(text):
            log.append(f"dropped\tcritical-apparatus text, not dialogue: {text[:60]!r}")
            continue

        resolved = _resolve_calls(text, p.page)

        if resolved.startswith("[") and resolved.endswith("]"):
            writer.direction(resolved[1:-1])
            continue
        if _STAGE_VERB_RE.match(resolved):
            writer.direction(resolved)
            continue
        # Vol. I only (Knights's own paren-wrapped SCENE direction): admitting
        # this for vol. II too changes nothing there today (vol. II never
        # prints one), but is gated anyway for the same reason the bare-cue
        # checks below are -- this module's contract is that regenerating
        # vol. II stays byte-identical, not just that it happens to today.
        if cfg.genie is GENIE_TEXT_I:
            m = _PAREN_STAGE_RE.match(resolved)
            if m:
                writer.direction(m.group(1))
                continue

        abbrev_pieces = _split_abbrev_cues(resolved, abbrev)
        if len(abbrev_pieces) > 1 or abbrev_pieces[0][0] is not None:
            for cue, piece in abbrev_pieces:
                if cue is not None:
                    writer.cue(cue)
                    writer.line(piece)
                elif writer._pending_cue is not None or writer._open:
                    writer.line(piece)
                else:
                    log.append(f"dropped\tpre-speech text, not dialogue: {piece[:60]!r}")
            continue

        # The paren-direction shapes are tried before their bare-cue
        # siblings: "PRAXAGORA. (coming forward...)." and "1ST WOMAN
        # (entering with a lamp)." both also satisfy `_CUE_RE`'s looser
        # "name, period, rest" shape, which would otherwise swallow the
        # parenthetical whole as spoken text (B round 3 item 3, 2026-09-17).
        m = _CUE_PAREN_RE.match(resolved)
        if m:
            # `_CUE_PAREN_RE`'s own name charset admits a literal "." (an
            # abbreviated form's own dot, matched elsewhere), so a name
            # followed directly by "." then "(" -- "PRAXAGORA. (coming
            # forward...)" -- captures that period into group(1) itself; it
            # is not part of the name and must not print as a second period.
            printed = _ascii_cue(m.group(1).strip().rstrip("."))
            cue = abbrev.get(printed, printed)
            writer.cue(cue)
            writer.direction(m.group(2))
            writer.line(m.group(3))
            continue

        m = _MIXED_CUE_PAREN_RE.match(resolved)
        if m:
            printed = _normalize_mixed_cue(m.group(1).strip().rstrip("."))
            cue = abbrev.get(printed, printed)
            writer.cue(cue)
            writer.direction(m.group(2))
            writer.line(m.group(3))
            continue

        m = _CUE_RE.match(resolved)
        if m:
            printed = _ascii_cue(m.group(1).strip())
            cue = abbrev.get(printed, printed)
            writer.cue(cue)
            writer.line(m.group(2))
            continue

        m = _MIXED_CUE_RE.match(resolved)
        if m:
            printed = _normalize_mixed_cue(m.group(1).strip())
            cue = abbrev.get(printed, printed)
            writer.cue(cue)
            writer.line(m.group(2))
            continue

        # A cue with no text of its own on this paragraph (`_BARE_CUE_PAREN_RE`
        # /`_BARE_CUE_RE`): the speech itself is the NEXT paragraph. Vol. I
        # only (a first entrance printed "NAME (direction)." as its own
        # line, or a lone "NAME." before Demus's Knights entrance) -- gated
        # the same way as `_PAREN_STAGE_RE` above: unconditionally admitting
        # either pattern silently swallows a vol. II structural heading this
        # module previously left as plain (if stray) text -- e.g. Thesm.'s
        # "FEMALE HERALD."/"PARABASIS." lines -- changing its already-shipped
        # bench (checked 2026-09-22). Checked last, since every shape above
        # needs its own trailing text and would already have matched if this
        # paragraph had any.
        if cfg.genie is GENIE_TEXT_I:
            m = _BARE_CUE_PAREN_RE.match(resolved)
            if m:
                printed = _ascii_cue(m.group(1).strip().rstrip("."))
                cue = abbrev.get(printed, printed)
                writer.cue(cue)
                writer.direction(m.group(2))
                continue

            m = _BARE_CUE_RE.match(resolved)
            if m:
                printed = _ascii_cue(m.group(1).strip().rstrip("."))
                cue = abbrev.get(printed, printed)
                writer.cue(cue)
                continue

        if writer._pending_cue is None and not writer._open:
            # Pre-speech furniture (a "characters present" list before the
            # first real cue -- Thesm.'s "MNESILOCHUS, EURIPIDES.", Frogs's
            # "BACCHUS, XANTHIAS—[...]"): not a cue, no speech open yet to
            # extend, and not worth inventing a bracket for -- the SCENE
            # direction right before it already sets the stage.
            log.append(f"dropped\tpre-speech text, not dialogue: {resolved[:60]!r}")
            continue
        writer.line(resolved)

    text_out = writer.finish(footnotes)
    return text_out, _count_speeches(text_out, cfg.title), len(footnotes), log, gaps


def convert_play(work_id: str) -> Converted:
    cfg = PLAYS[work_id]
    paras = _load_genie(cfg)
    start, end = _play_bounds(paras, work_id)
    text, speeches, n_footnotes, log, gaps = _convert_body(paras, start, end, cfg)
    for _idx, lo, hi in gaps:
        log.append(f"gap\tGreek {lo}-{hi} left bare (no splice source for this bench)")
    return Converted(text, speeches, n_footnotes, log)


def main() -> int:
    out_dir = SOURCES_DIR / "bench" / "hickie"
    out_dir.mkdir(parents=True, exist_ok=True)
    for work_id in PLAYS:
        result = convert_play(work_id)
        (out_dir / f"{PLAYS[work_id].bench}.txt").write_text(result.text, encoding="utf-8")
        print(f"{work_id}: speeches={result.speeches} footnotes={result.footnotes} log_lines={len(result.log)}")
        for line in result.log:
            print(f"  {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
