"""Where a strophe div of an OCR edition's TEI ends (way_to_tei, paley_to_tei).

Jebb's writer leaves a div open to the next strophe mark, so the last stanza
of an ode takes in the dialogue after it. Way's and Paley's writers close a
stanza at the next mark, or at a change of voice (the speaker named last,
carried into an unlabelled stanza) whose new speech is not in the stanza of
Murray's text that the stanza's first line aligns with: the Paedagogus at
Medea 1002 is spoken, so the antistrophe at 996 closes before him, while the
sons' cries inside a strophe that Murray prints as one stanza (1271-1278)
stay in it.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

TEI_NS = "{http://www.tei-c.org/ns/1.0}"
LYRIC = {"strophe", "antistrophe", "epode", "mesode", "ephymn", "lyric"}


def murray_stanzas(path: Path) -> dict[str, str]:
    """{Murray's ref: the lyric stanza of his Perseus TEI that holds it}
    (a strophe, antistrophe, epode, mesode, or astrophic lyric div)."""
    root = ET.parse(path).getroot()
    out = {}
    for k, div in enumerate(root.iter(f"{TEI_NS}div")):
        if div.get("subtype") in LYRIC:
            for el in div.iter(f"{TEI_NS}l"):
                out[el.get("n")] = f"{div.get('subtype')} {div.get('n') or ''} #{k}"
    return out


def lyric_ends(voice: str | None, speaker: str, opens_here: bool,
               div_stanza: str | None, line_stanza: str | None) -> bool:
    """Whether an open stanza closes before a speech by speaker: a new voice
    (not the one named last), on a line that does not itself open the
    stanza, whose line is outside the Murray stanza the div began in (any
    new voice closes a div that began outside Murray's stanzas)."""
    return (voice is not None and speaker != voice and not opens_here
            and (div_stanza is None or line_stanza != div_stanza))
