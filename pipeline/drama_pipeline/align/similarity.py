"""Pluggable sentence-similarity backends for the translation aligner.

Both sides of the match are *English* (the Rackham reference vs. the unmarked
Ross target), so a zero-dependency lexical (TF-IDF cosine) backend already
aligns them well and runs with nothing installed. A `sentence-transformers`
backend is available for higher quality when the lexical scores are marginal;
it is imported lazily so the normal pipeline never needs torch.

Every backend exposes the same call:

    cos_matrix(refs, tgts) -> list[list[float]]   # len(refs) x len(tgts)

rows = reference segments (one Bekker anchor each), cols = target sentences.
"""

from __future__ import annotations

import math
import re
from collections import Counter

_WORD = re.compile(r"[A-Za-z]+")


def _tokens(text: str) -> list[str]:
    return _WORD.findall(text.lower())


# ---- lexical (TF-IDF cosine), no dependencies -----------------------------
def _tfidf_vectors(docs: list[list[str]]) -> list[dict[str, float]]:
    n = len(docs)
    df: Counter[str] = Counter()
    for d in docs:
        df.update(set(d))
    idf = {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}
    vecs = []
    for d in docs:
        tf = Counter(d)
        v = {t: (c / len(d)) * idf[t] for t, c in tf.items()} if d else {}
        norm = math.sqrt(sum(w * w for w in v.values())) or 1.0
        vecs.append({t: w / norm for t, w in v.items()})
    return vecs


def _cos(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(w * b.get(t, 0.0) for t, w in a.items())


def _lexical_matrix(refs: list[str], tgts: list[str]) -> list[list[float]]:
    vecs = _tfidf_vectors([_tokens(t) for t in refs + tgts])
    rv, tv = vecs[: len(refs)], vecs[len(refs):]
    return [[_cos(r, t) for t in tv] for r in rv]


# ---- sentence-transformers (optional, better) -----------------------------
_MODELS = {
    "fast": "all-MiniLM-L6-v2",
    "quality": "all-mpnet-base-v2",
}
_st_cache: dict[str, object] = {}


def _sbert_matrix(refs: list[str], tgts: list[str], model: str) -> list[list[float]]:
    from sentence_transformers import SentenceTransformer, util  # lazy

    name = _MODELS.get(model, model)
    enc = _st_cache.get(name)
    if enc is None:
        enc = _st_cache[name] = SentenceTransformer(name)
    rv = enc.encode(refs, convert_to_tensor=True)
    tv = enc.encode(tgts, convert_to_tensor=True)
    return util.cos_sim(rv, tv).cpu().tolist()


class BandedCosine:
    """TF-IDF vectors built once over both sides, with a cheap pairwise
    ``cos(i, j)`` lookup -- for a caller (the turn-pairing DP's bridge term,
    ``pair_dp.py``) that only ever asks for a handful of cells per row and
    would otherwise pay for the full ``refs`` x ``tgts`` matrix it never
    reads. Additive: ``cos_matrix`` and its ``align_turns.py`` caller are
    unchanged."""

    def __init__(self, refs: list[str], tgts: list[str]):
        vecs = _tfidf_vectors([_tokens(t) for t in refs] + [_tokens(t) for t in tgts])
        self._refs = vecs[: len(refs)]
        self._tgts = vecs[len(refs):]

    def cos(self, i: int, j: int) -> float:
        if not (0 <= i < len(self._refs)) or not (0 <= j < len(self._tgts)):
            return 0.0
        return _cos(self._refs[i], self._tgts[j])


def banded_cosine(refs: list[str], tgts: list[str]) -> BandedCosine:
    """Build the once-computed vectors for a ``BandedCosine`` lookup."""
    return BandedCosine(refs, tgts)


def cos_matrix(refs: list[str], tgts: list[str], backend: str = "lexical") -> list[list[float]]:
    """Cosine-similarity matrix, refs (rows) x tgts (cols).

    backend: "lexical" (default, zero-dep TF-IDF) | "fast" / "quality"
    (sentence-transformers MiniLM / mpnet) | any sentence-transformers model id.
    """
    if not refs or not tgts:
        return [[0.0] * len(tgts) for _ in refs]
    if backend == "lexical":
        return _lexical_matrix(refs, tgts)
    return _sbert_matrix(refs, tgts, backend)
