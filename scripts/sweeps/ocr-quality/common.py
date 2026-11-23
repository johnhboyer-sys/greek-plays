"""Shared helpers for the Genie OCR quality sweep (2026-09-29). Read-only on
the repo; caches go to the session scratchpad."""
from __future__ import annotations

import json
import pickle
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path("/Users/johnboyer/Developer/greek-plays")
ED = ROOT / "build/genie/editions"
PERSEUS = ROOT / "sources/perseus"
P2C = ROOT / "build/p2c"
OUT = ROOT / "build/sweeps/genie-ocr"
SCRATCH = Path("/private/tmp/claude-501/-Users-johnboyer-Developer-greek-plays/"
               "6f899977-96bf-443d-adae-f941aef2e70e/scratchpad")
ANALYSES = Path("/Applications/Diogenes.app/Contents/dependencies/data/greek-analyses.txt")

sys.path.insert(0, str(ROOT / "pipeline"))
from drama_pipeline import beta  # noqa: E402

APOS = "'’᾽ʼ᾿`´"
GREEK_RE = re.compile(r"[Ͱ-Ͽἀ-῿]")
COMB = {"̀", "́", "̂", "̃", "̄", "̆", "̈",
        "̓", "̔", "͂", "ͅ", "̑", "̣", "̇"}


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def is_greek_char(ch: str) -> bool:
    return bool(GREEK_RE.match(ch))


def greek_share(s: str) -> float:
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if is_greek_char(c)) / len(letters)


# Latin capitals that OCR puts into Greek speaker abbreviations
LAT2GRK = str.maketrans({"A": "Α", "B": "Β", "E": "Ε", "Z": "Ζ", "H": "Η", "I": "Ι",
                         "K": "Κ", "M": "Μ", "N": "Ν", "O": "Ο", "P": "Ρ", "T": "Τ",
                         "Y": "Υ", "X": "Χ"})


def compare_form(tok: str) -> str:
    """Diacritic-level form used to judge a token: NFC, lowercase, grave->acute,
    unified apostrophe, koronis kept, punctuation stripped."""
    s = unicodedata.normalize("NFD", tok)
    out = []
    for ch in s:
        if ch in APOS:
            out.append("’")
        elif ch == "̀":
            out.append("́")
        elif ch in COMB:
            out.append(ch)
        elif ch.isalpha():
            out.append(ch.lower())
    r = unicodedata.normalize("NFC", "".join(out))
    r = r.replace("ς", "σ")
    # a dangling apostrophe-only token
    return r


def key_form(tok: str) -> str:
    """Letters only, no diacritics, lowercase, sigma unified: the alignment key."""
    s = unicodedata.normalize("NFD", tok)
    r = "".join(ch.lower() for ch in s if ch.isalpha() and ch not in COMB and ch not in APOS)
    return r.replace("ς", "σ")


TOKEN_SPLIT = re.compile(r"[\s—–\-]+")
EDGE_PUNCT = ".,·;:!?()[]⟨⟩<>{}†*|\"“”‘«»—–…·;·;"


def tokens(line: str) -> list[str]:
    out = []
    for raw in TOKEN_SPLIT.split(line):
        t = raw.strip(EDGE_PUNCT + " ")
        # keep trailing elision apostrophe, drop leading quotes
        t = t.lstrip("‘'’")
        if t and any(c.isalpha() for c in t):
            out.append(t)
    return out


def levenshtein(a, b) -> int:
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


# ---------------------------------------------------------------- Morpheus
_KEYS = None


def morpheus_keys() -> set:
    global _KEYS
    if _KEYS is not None:
        return _KEYS
    cache = SCRATCH / "morpheus_keys.pkl"
    if cache.exists():
        _KEYS = pickle.loads(cache.read_bytes())
        return _KEYS
    keys = set()
    with ANALYSES.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            k = line.split("\t", 1)[0]
            keys.add(k)
    cache.write_bytes(pickle.dumps(keys))
    _KEYS = keys
    return keys


def morpheus_valid(tok: str) -> bool:
    keys = morpheus_keys()
    t = tok.strip(APOS)
    elided = len(t) != len(tok)
    try:
        k = beta.to_beta_key(t)
    except ValueError:
        return False
    cap = t[:1].isupper()
    cands = beta.lookup_variants(k, True)
    if elided:
        cands = cands + [c + "'" for c in cands]
    return any(c in keys for c in cands)


# ---------------------------------------------------------------- Perseus
TEI = "{http://www.tei-c.org/ns/1.0}"


def _text_of(el) -> str:
    parts = []

    def walk(e):
        tag = e.tag.replace(TEI, "")
        if tag in ("note", "bibl", "milestone"):
            if e.tail:
                parts.append(e.tail)
            return
        if e.text:
            parts.append(e.text)
        for c in e:
            walk(c)
        if e.tail and e is not el:
            parts.append(e.tail)

    walk(el)
    return " ".join("".join(parts).split())


def perseus_lines(path: Path) -> list[dict]:
    """[{n, text, speaker}] with antilabe parts (I/M/F) merged into one line."""
    root = ET.parse(path).getroot()
    body = root.find(f".//{TEI}body")
    out: list[dict] = []
    for sp_or_l in body.iter():
        tag = sp_or_l.tag.replace(TEI, "")
        if tag != "l":
            continue
        if sp_or_l.get("style") == "hidden":
            continue
        n = sp_or_l.get("n") or ""
        part = sp_or_l.get("part")
        txt = _text_of(sp_or_l).replace("—", " ").strip()
        if part in ("M", "F") and out:
            out[-1]["text"] += " " + txt
            out[-1]["parts"] += 1
        else:
            out.append({"n": n, "text": txt, "parts": 1})
    return out


def tlg_lines(slug: str) -> list[dict]:
    d = json.loads((P2C / slug / "greek_spine.json").read_text(encoding="utf-8"))
    out = []
    for seg in d["segments"]:
        for ln in seg["lines"]:
            out.append({"n": ln.get("ref") or str(ln["n"]), "text": ln["text"]})
    return out


def corpus_vocab() -> set:
    cache = SCRATCH / "corpus_vocab.pkl"
    if cache.exists():
        return pickle.loads(cache.read_bytes())
    vocab = set()
    for f in PERSEUS.glob("tlg00*-grc2.xml"):
        if not f.name.startswith(("tlg0006", "tlg0011", "tlg0085", "tlg0019")):
            continue
        for ln in perseus_lines(f):
            for t in tokens(ln["text"]):
                vocab.add(compare_form(t))
    for d in P2C.iterdir():
        if (d / "greek_spine.json").exists():
            for ln in tlg_lines(d.name):
                for t in tokens(ln["text"]):
                    vocab.add(compare_form(t))
    cache.write_bytes(pickle.dumps(vocab))
    return vocab
