#!/usr/bin/env python3
"""S15: speaker-roster audit across every translation column (read-only).

Run:  pipeline/.venv/bin/python scripts/sweeps/s15-roster-audit.py
Writes build/sweeps/roster-audit-2026-09-29.{md,tsv}.

Sources
  manifests/<play>.yaml   speakers.{english,english_secondary,english_third,
                          english_<translation id>,english_overrides,overrides}
                          and registry.translations (id -> slot)
  build/dist/<play>/book-*.json   (read only; never rebuilt)
      Greek side   segments[].speakers[].display, book.speakerRoster
      primary      segments[].english.turns[].{speaker (canonical), display (printed)}
      secondary    segments[].ross[].text      (printed cues prefixed into text)
      third        segments[].third[].text
      overlays     segments[].overlays.<id>[].text

Comparison columns carry no canonical name in dist: stage1's chunks_as_overlay
writes only the PRINTED cue ("DEMOSTHENES. ...") into the text. So for
secondary/third/overlay columns this script recovers the cues with the same
regex Reader.svelte uses (extractPrefixedEnglishTurns), then maps each cue to a
canonical display the way stage1 does (stage1_turn_english._aliases_for_slot +
_canonical_english + _apply_english_overrides). A-D use that manifest mapping.

Finding E is extra: it tests what the reader itself does with a printed cue.
Reader.svelte matches the cue, lower-cased with punctuation stripped, against
the Greek roster; only on a miss does it fall back to the primary column's
turn at the same index, then to the raw label. A manifest alias is never
consulted at render time. A cue whose normalised form is not a Greek display
therefore has no reliable colour key, whatever the manifest says.
"""
from __future__ import annotations

import collections
import difflib
import glob
import json
import re
import subprocess
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
DIST = REPO / "build" / "dist"
OUT = REPO / "build" / "sweeps"
STAMP = "2026-09-29"

ORDINALS = {"first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth",
            "1st", "2nd", "3rd", "one", "two", "three"}


# ── name normalisers ────────────────────────────────────────────────────────
def reader_norm(s: str) -> str:
    """Reader.svelte / speakers.ts extractPrefixedEnglishTurns `norm`."""
    return re.sub(r"[^\w]+", " ", s.lower()).replace("_", " ").strip()


def strip_article(s: str) -> str:
    return re.sub(r"^(a|an|the)\s+", "", s.strip(), flags=re.I)


def skel(s: str) -> str:
    """Spelling skeleton: case, diacritics, articles, punctuation and the usual
    Greek-to-Latin transliteration variants removed."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = strip_article(s.lower())
    s = re.sub(r"[^a-z0-9]", "", s)
    for a, b in (("ph", "f"), ("th", "t"), ("ch", "c"), ("kh", "c"), ("ae", "e"),
                 ("ai", "e"), ("oe", "e"), ("oi", "e"), ("ei", "i"), ("ou", "u"),
                 ("y", "i"), ("k", "c"), ("w", "u"), ("j", "i"), ("v", "u")):
        s = s.replace(a, b)
    s = re.sub(r"os$", "us", s)
    return re.sub(r"([a-z])\1+", r"\1", s)


def lev(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def has_ordinal(s: str) -> bool:
    return bool(ORDINALS & set(reader_norm(s).split())) or bool(re.search(r"\d", s))


# Latin or anglicised forms of a Greek name that a translator may print.
LATIN = {"hercules": "heracles", "neptune": "poseidon", "jupiter": "zeus", "jove": "zeus",
         "mercury": "hermes", "bacchus": "dionysus", "minerva": "athena", "juno": "hera",
         "pluto": "hades", "ceres": "demeter", "diana": "artemis", "venus": "aphrodite"}


def _short_token_differs(a: str, b: str) -> bool:
    ta, tb = reader_norm(a).split(), reader_norm(b).split()
    if len(ta) != len(tb):
        return False
    return any(x != y and (len(x) <= 2 or len(y) <= 2) for x, y in zip(ta, tb))


def mechanical_pair(a: str, b: str) -> bool:
    """Same person beyond doubt: spelling, case, article, punctuation,
    transliteration, a Latin form of a god's name, or a slip of one or two
    letters in a long name.  Never numbers, ordinals, letters (Semichorus A/B)
    or a plural against its singular."""
    if not a or not b:
        return False
    sa, sb = skel(a), skel(b)
    if sa and sa == sb:
        return True
    if LATIN.get(reader_norm(strip_article(a))) == reader_norm(strip_article(b)) or \
       LATIN.get(reader_norm(strip_article(b))) == reader_norm(strip_article(a)):
        return True
    if has_ordinal(a) or has_ordinal(b) or _short_token_differs(a, b):
        return False
    if sa + "s" == sb or sb + "s" == sa or sa + "es" == sb or sb + "es" == sa:
        return False
    n = min(len(sa), len(sb))
    one_word = len(reader_norm(a).split()) == 1 and len(reader_norm(b).split()) == 1
    if n >= (6 if one_word else 8) and lev(sa, sb) <= 1:
        return True
    if n >= 12 and lev(sa, sb) <= 2:
        return True
    return False


def propose(name: str, greek: set[str]) -> tuple[str, str]:
    """(proposed Greek display or '', class MECHANICAL|JUDGMENT)."""
    if not greek:
        return "", "JUDGMENT"
    if name in greek:
        return name, "MECHANICAL"
    for g in sorted(greek):
        if mechanical_pair(name, g):
            return g, "MECHANICAL"
    n = reader_norm(name)
    # Role family: Chorus Leader / Semichorus / Coryphaeus -> Chorus...
    fam = None
    if re.search(r"chor|coryph|leader|semi|half", n):
        fam = sorted(g for g in greek if g.lower().startswith("chorus"))
    if fam:
        return " | ".join(fam[:3]), "JUDGMENT"
    toks = set(n.split())
    best, score = "", 0.0
    for g in sorted(greek):
        gt = set(reader_norm(g).split())
        j = len(toks & gt) / max(1, len(toks | gt))
        r = difflib.SequenceMatcher(None, skel(name), skel(g)).ratio()
        sc = max(j, r if r >= 0.75 else 0)
        if sc > score:
            best, score = g, sc
    if score >= 0.5:
        return best, "JUDGMENT"
    return "", "JUDGMENT"


# ── manifest side ───────────────────────────────────────────────────────────
def load_manifest(path: Path) -> dict:
    return yaml.load(path.read_text(encoding="utf-8"), Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader))


def aliases_for(speakers: dict, slot: str, tid: str | None) -> tuple[dict, str]:
    """Mirror stage1_turn_english._aliases_for_slot; also say which block."""
    if slot == "primary":
        return speakers.get("english") or {}, "english"
    if slot == "secondary":
        for k in ("english_secondary", "english"):
            if speakers.get(k):
                return speakers[k], k
        return {}, "none"
    if slot == "third":
        for k in ("english_third", "english_secondary", "english"):
            if speakers.get(k):
                return speakers[k], k
        return {}, "none"
    k = f"english_{tid}"
    if tid and speakers.get(k):
        return speakers[k], k
    return speakers.get("english") or {}, "english"


def alias_lookup(alias: dict, printed: str):
    """stage1 looks the printed cue up as printed; Hickie and Lindsay keys keep
    the cue's full stop ("Phidippides."), which dist's display drops."""
    for k in (printed, printed + "."):
        if k in alias:
            return alias[k]
    return None


def pin_norm(t: str) -> str:
    t = re.sub(r"\[\^[^\]]*\]", " ", t)
    t = re.sub(r"^\s*\([^)]*\)", " ", t)
    t = re.sub(r"[^\w\s]", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()


CUE_RE = re.compile(r"(^|\n{2,})([^.\n]{1,80})\.\s+")


def parse_cues(text: str, known_norm: set[str]) -> list[dict]:
    """Same candidate rule as extractPrefixedEnglishTurns: a known name, or an
    all-caps label."""
    hits = []
    for m in CUE_RE.finditer(text):
        label = m.group(2).strip()
        if reader_norm(label) in known_norm or (re.search(r"[^\W\d_]", label) and label == label.upper()):
            hits.append((m.start(), m.end(), label))
    out = []
    for i, (s, e, label) in enumerate(hits):
        nxt = hits[i + 1][0] if i + 1 < len(hits) else len(text)
        out.append({"printed": label, "body": text[e:nxt], "k": i})
    return out


class OverrideState:
    """stage1 _apply_english_overrides for one column: an entry fires at the
    first speech whose printed cue and opening words match, then holds."""

    def __init__(self, overrides: list[dict], slot_kind: str):
        self.pending = [o for o in overrides if o.get("slot") == slot_kind]
        self.active: dict[str, str] = {}
        self.labels = {o["label"]: o["display"] for o in overrides
                       if o.get("slot") == slot_kind and o.get("label")}

    def canonical(self, printed: str, body: str, base: str) -> str:
        if printed in self.labels:
            return self.labels[printed]
        for o in list(self.pending):
            if printed.rstrip(".") == o["cue"].rstrip(".") and pin_norm(body).startswith(pin_norm(o["from_text"])):
                self.active[printed] = o["display"]
                self.pending.remove(o)
                break
        return self.active.get(printed, base)


# ── audit one play ──────────────────────────────────────────────────────────
def audit_play(mpath: Path) -> dict:
    m = load_manifest(mpath)
    play = m["work"]["id"]
    sp = m.get("speakers") or {}
    overrides = sp.get("english_overrides") or []
    trans = {t["slot"] + (":" + t["id"] if t["slot"] == "overlay" else ""): t["id"]
             for t in (m.get("registry") or {}).get("translations", [])}
    tid_of = {"primary": None, "secondary": None, "third": None}
    for t in (m.get("registry") or {}).get("translations", []):
        s = {"english": "primary"}.get(t["slot"], t["slot"])
        if s in tid_of:
            tid_of[s] = t["id"]

    books = sorted(glob.glob(str(DIST / play / "book-*.json")))
    segs, roster = [], []
    for b in books:
        d = json.loads(Path(b).read_text(encoding="utf-8"))
        segs += d.get("segments") or []
        roster += d.get("speakerRoster") or []

    greek_ct: collections.Counter = collections.Counter()
    for s in segs:
        for ev in s.get("speakers") or []:
            if ev.get("display"):
                greek_ct[ev["display"]] += 1
    greek = set(greek_ct) | set(roster)
    known_base = {reader_norm(g) for g in greek}

    # column -> Counter[(printed, canonical)]
    cols: dict[str, collections.Counter] = {}
    col_alias: dict[str, tuple[dict, str, str]] = {}  # slot -> (alias map, block, slot_kind)

    def add_col(slot: str, kind: str, tid: str | None):
        alias, block = aliases_for(sp, kind, tid)
        col_alias[slot] = (alias, block, kind)
        cols.setdefault(slot, collections.Counter())

    # primary: dist carries canonical + printed
    add_col(f"primary:{tid_of['primary']}", "primary", None)
    pslot = f"primary:{tid_of['primary']}"
    for s in segs:
        for t in (s.get("english") or {}).get("turns") or []:
            printed, canon = t.get("display"), t.get("speaker")
            if printed or canon:
                cols[pslot][(printed or canon, canon or printed)] += 1

    def comparison(slot_kind: str, key: str, tid: str, getter):
        slot = f"{slot_kind}:{tid}"
        add_col(slot, slot_kind, tid)
        alias = col_alias[slot][0]
        known = known_base | {reader_norm(k) for k in alias} | {reader_norm(v) for v in alias.values() if v}
        st = OverrideState(overrides, slot_kind)
        for s in segs:
            for piece in getter(s) or []:
                text = piece.get("text") or ""
                added = set(piece.get("cueAddedTurns") or ([0] if piece.get("cueAdded") else []))
                for c in parse_cues(text, known):
                    if c["k"] in added:
                        continue  # editor-added cue, not printed
                    printed = c["printed"]
                    hit = alias_lookup(alias, printed)
                    base = hit if hit is not None else printed
                    canon = st.canonical(printed, c["body"], base)
                    cols[slot][(printed, canon)] += 1

    if tid_of["secondary"]:
        comparison("secondary", "ross", tid_of["secondary"], lambda s: s.get("secondary") or s.get("ross"))
    if tid_of["third"]:
        comparison("third", "third", tid_of["third"], lambda s: s.get("third"))
    for t in (m.get("registry") or {}).get("translations", []):
        if t["slot"] == "overlay":
            comparison("overlay", "overlays", t["id"], lambda s, i=t["id"]: (s.get("overlays") or {}).get(i))

    rows: list[dict] = []

    def row(slot, cue, cur, prop, cls, typ, n="", note=""):
        rows.append(dict(play=play, slot=slot, cue=cue, current=cur, proposed=prop,
                         cls=cls, type=typ, n=n, note=note))

    all_canon: dict[str, set] = {}
    used_canon: set[str] = set()
    for slot, ct in cols.items():
        alias, block, kind = col_alias[slot]
        label_set = {o["label"] for o in overrides if o.get("label") and o.get("slot") == kind}
        # A: printed cue with no roster mapping
        a_cues = set()
        for (printed, canon), n in sorted(ct.items()):
            if alias_lookup(alias, printed) is not None or printed in label_set:
                continue
            if kind == "primary" and canon != printed:
                continue  # primary canonical was set by an override / gate
            a_cues.add(printed)
            prop, cls = propose(printed, greek)
            harmless = printed in greek
            note = f"alias block used: {block}"
            if harmless:
                note += "; raw name is itself a Greek display (harmless)"
            if len(printed) <= 2:
                note += "; one or two letters: likely a part-chorus letter, not a speaker"
            row(slot, printed, printed, prop, cls, "A", n, note)
        # B: canonical names not on the Greek side
        by_canon: dict[str, list] = collections.defaultdict(list)
        for (printed, canon), n in ct.items():
            by_canon[canon].append((printed, n))
            used_canon.add(canon)
        all_canon[slot] = set(by_canon)
        for canon, lst in sorted(by_canon.items()):
            if canon in greek:
                continue
            if all(p in a_cues for p, _ in lst):
                continue  # already listed under A with the same proposal
            prop, cls = propose(canon, greek)
            cues = "; ".join(p for p, _ in sorted(lst, key=lambda x: -x[1])[:4])
            row(slot, cues, canon, prop, cls, "B", sum(n for _, n in lst), f"alias block used: {block}")
        # E: the reader cannot resolve the printed cue by name (comparison columns)
        if kind != "primary":
            for (printed, canon), n in sorted(ct.items()):
                if reader_norm(printed) in known_base:
                    continue
                target = canon if canon in greek else ""
                if target:
                    cls = "MECHANICAL" if mechanical_pair(printed, target) else "JUDGMENT"
                    prop = target
                else:
                    prop, cls = propose(canon, greek)
                    if not prop:
                        prop, cls = propose(printed, greek)
                row(slot, printed, printed, prop, cls, "E", n,
                    f"manifest maps to {canon!r}" + ("" if canon in greek else " (not a Greek display)"))

    # C: one character, two spellings, across Greek + every column
    variants = collections.defaultdict(set)
    where = collections.defaultdict(lambda: collections.defaultdict(set))
    for g in greek:
        variants[skel(g)].add(g)
        where[skel(g)][g].add("greek")
    for slot, names in all_canon.items():
        for nme in names:
            variants[skel(nme)].add(nme)
            where[skel(nme)][nme].add(slot.split(":")[0] + ":" + slot.split(":")[1])
    names_all = sorted({n for v in variants.values() for n in v})
    parent = {n: n for n in names_all}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, a in enumerate(names_all):
        for b in names_all[i + 1:]:
            if mechanical_pair(a, b):
                parent[find(a)] = find(b)
    groups = collections.defaultdict(set)
    for n in names_all:
        groups[find(n)].add(n)
    for _, names in sorted(groups.items()):
        if len(names) < 2:
            continue
        gnames = sorted(n for n in names if n in greek)
        canon_pick = gnames[0] if gnames else sorted(names)[0]
        for nme in sorted(names):
            if nme == canon_pick:
                continue
            slots = sorted(where[skel(nme)][nme])
            row(", ".join(slots), "", nme, canon_pick, "MECHANICAL", "C", "",
                "variants of one name: " + " / ".join(sorted(names)))

    # C, reader-effective: printed spellings of one Greek name that the reader
    # cannot match (PISTHETAERUS / PISTHETAIROS / Peisthetaerus). These are the
    # MECHANICAL E rows, listed again by type so the count answers "C".
    for r in [r for r in rows if r["type"] == "E" and r["cls"] == "MECHANICAL"]:
        row(r["slot"], r["cue"], r["current"], r["proposed"], "MECHANICAL", "C", r["n"],
            "printed spelling differs from the Greek display (same rows as E)")

    # D: Greek displays no English column uses
    for g in sorted(greek - used_canon):
        row("all", "", g, "", "INFO", "D", greek_ct.get(g, 0), "no English column uses this display")

    return dict(play=play, rows=rows, greek=greek, cols={k: dict(v) for k, v in cols.items()},
                col_alias={k: v[1] for k, v in col_alias.items()})


# ── freshness ───────────────────────────────────────────────────────────────
def freshness() -> dict:
    files = [Path(p) for p in glob.glob(str(DIST / "*" / "book-*.json"))]
    mt = [p.stat().st_mtime for p in files]
    ct = subprocess.run(["git", "log", "-1", "--format=%ct|%h|%s", "--", "manifests",
                         "pipeline/drama_pipeline/stage7_emit.py"],
                        cwd=REPO, capture_output=True, text=True).stdout.strip().split("|", 2)
    newest = int(ct[0])
    # every commit since the oldest book file, touching either path
    since = subprocess.run(["git", "log", f"--since=@{int(min(mt))}", "--format=%h %s", "--",
                            "manifests", "pipeline/drama_pipeline/stage7_emit.py"],
                           cwd=REPO, capture_output=True, text=True).stdout.strip().splitlines()
    return dict(n=len(files), oldest=min(mt), newest_file=max(mt), commit_ts=newest,
                commit=f"{ct[1]} {ct[2]}", stale=min(mt) < newest, since=since)


def fmt(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


# ── main ────────────────────────────────────────────────────────────────────
def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    plays = []
    for p in sorted((REPO / "manifests").glob("*.yaml")):
        if p.name == "authors.yaml":
            continue
        plays.append(audit_play(p))
    n_plays = len(plays)
    fr = freshness()

    ORDER = {"MECHANICAL": 0, "JUDGMENT": 1, "INFO": 2}
    TORDER = {"A": 0, "B": 1, "C": 2, "E": 3, "D": 4}
    allrows = [r for pl in plays for r in pl["rows"]]

    # TSV
    with open(OUT / f"roster-audit-{STAMP}.tsv", "w", encoding="utf-8") as f:
        f.write("\t".join(["play", "slot", "cue", "current", "proposed", "class", "finding_type", "count", "note"]) + "\n")
        for r in allrows:
            f.write("\t".join(str(r[k]).replace("\t", " ").replace("\n", " ") for k in
                              ("play", "slot", "cue", "current", "proposed", "cls", "type", "n", "note")) + "\n")

    # report
    L: list[str] = []
    L.append(f"# Roster audit, {STAMP}\n")
    L.append(f"Plays audited: {n_plays}. Script: `scripts/sweeps/s15-roster-audit.py`. "
             f"Data: `build/dist/<play>/book-*.json` and `manifests/*.yaml`. Read only.\n")
    L.append("## build/dist freshness\n")
    L.append(f"{fr['n']} book files, modified {fmt(fr['oldest'])} to {fmt(fr['newest_file'])}. "
             f"Newest commit touching `manifests/` or `stage7_emit.py`: {fr['commit']} ({fmt(fr['commit_ts'])}). "
             + ("**dist is older than that commit.** " if fr["stale"] else "dist is current. "))
    if fr["since"]:
        L.append("Commits since the oldest book file: " + "; ".join(fr["since"]) + ".")
    L.append("\n")
    L.append("## How the data is read\n")
    L.append("- Greek side: `segments[].speakers[].display` and `speakerRoster`.")
    L.append("- Primary English: `segments[].english.turns[].speaker` (canonical) and `.display` (printed cue).")
    L.append("- Secondary, third, overlay columns: dist holds only the printed cue, prefixed into `segments[].ross[].text`, "
             "`segments[].third[].text`, `segments[].overlays.<id>[].text`. The script recovers cues with the reader's own regex, "
             "then maps them through the manifest as stage1 does (`english_secondary`, `english_third`, `english_<id>`, "
             "`english_overrides`). Slot fallbacks follow `_aliases_for_slot`: third falls back to `english_secondary`, then `english`; "
             "an overlay without its own block uses `english`.")
    L.append("- This is a play-line corpus: there is no `turns[].d`, `et`, or `sub` in these files.")
    L.append("- Editor-added cues (`cueAdded`) are skipped: no translator printed them.\n")
    L.append("## Finding types\n")
    L.append("- **A** printed cue with no alias in the column's block (falls through to the raw name).")
    L.append("- **B** canonical display used in an English column that never occurs on the Greek side (A cases are listed once, under A).")
    L.append("- **C** one name under two spellings across Greek and the columns (always MECHANICAL). Manifest canonicals give no such case; every C row is a printed cue whose spelling differs from the Greek display, and repeats an E row.")
    L.append("- **D** Greek display no English column uses (class INFO).")
    L.append("- **E** (added) printed cue the reader cannot match by name to a Greek display. The reader never consults manifest aliases for "
             "comparison columns: it matches the cue, lower-cased and stripped of punctuation, against the Greek roster, then falls back to "
             "the primary column's turn at the same index, then to the raw label. This is what produced the parked experiment's "
             "\"Demosthenes vs First Slave\", \"PISTHETAERUS vs Peisthetaerus\" and \"Chorus Leader vs Chorus\" marks. "
             "The manifest is usually right for these; the reader ignores it.")
    L.append("- Class MECHANICAL: spelling, case, article, transliteration, one-letter slip in a long name. JUDGMENT: a different role name; John rules.\n")

    # summary
    L.append("## Summary\n")
    L.append("| play | A | B | C | D | E |")
    L.append("|---|---|---|---|---|---|")
    tot = collections.Counter()
    for pl in plays:
        c = collections.Counter(r["type"] for r in pl["rows"])
        tot.update(c)
        L.append(f"| {pl['play']} | {c['A']} | {c['B']} | {c['C']} | {c['D']} | {c['E']} |")
    L.append(f"| **total** | {tot['A']} | {tot['B']} | {tot['C']} | {tot['D']} | {tot['E']} |\n")
    L.append("By class and type (rows in the TSV):\n")
    L.append("| type | MECHANICAL | JUDGMENT | INFO |")
    L.append("|---|---|---|---|")
    for t in "ABCDE":
        cc = collections.Counter(r["cls"] for r in allrows if r["type"] == t)
        L.append(f"| {t} | {cc['MECHANICAL']} | {cc['JUDGMENT']} | {cc['INFO']} |")
    L.append("")

    # findings by play
    L.append("## Findings by play\n")
    for pl in plays:
        rs = sorted(pl["rows"], key=lambda r: (ORDER[r["cls"]], TORDER[r["type"]], r["slot"], r["cue"], r["current"]))
        if not rs:
            continue
        L.append(f"### {pl['play']}\n")
        L.append("| class | type | slot | printed cue | current | proposed | n | note |")
        L.append("|---|---|---|---|---|---|---|---|")
        for r in rs:
            L.append("| " + " | ".join(str(x).replace("|", "\\|") for x in
                                        (r["cls"], r["type"], r["slot"], r["cue"], r["current"], r["proposed"], r["n"], r["note"])) + " |")
        L.append("")
    (OUT / f"roster-audit-{STAMP}.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    print(f"plays covered: {n_plays}")
    print(f"rows: {len(allrows)}  by type: {dict(tot)}")
    print(f"dist stale: {fr['stale']}")
    return 0 if n_plays == 44 else 1


if __name__ == "__main__":
    sys.exit(main())
