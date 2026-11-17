"""The search port's corpus files (John, 2026-11-16: the plays count by
speech): speech bounds as chapters, the per-translation English indexes,
eng-chapters.json, the running text and the shard sources, in the shapes the
Aristotle reader's search code reads."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

import pytest  # noqa: E402

from drama_pipeline import speeches as speeches_mod  # noqa: E402
from drama_pipeline import stage6_search  # noqa: E402
from drama_pipeline.config import Manifest  # noqa: E402
from drama_pipeline.running_text import build_running_text, check_alignment, token_spans  # noqa: E402
from drama_pipeline.stage2_validate import check_offsets  # noqa: E402
from drama_pipeline.stage3_tokenize import tokenize  # noqa: E402
from drama_pipeline.stage6_search import emit_translation_indexes, english_words  # noqa: E402
from drama_pipeline.stage9_search_shards import run as stage9  # noqa: E402

# A play in three segments. 1:1 opens on a cue, and line 2 is an antilabe:
# the Chorus speaks first, the Herald takes over mid-line. 1:3 is a cap
# continuation (no cue at its head) with a speech starting mid-line 4. 1:5
# repeats the printed ref "2" (citation.repeated_refs) and opens with the
# edition's dash, which names no one.
_SPINE = {
    "work": "TST",
    "segments": [
        {"id": "1:1", "book": 1, "column": "1", "lines": [
            {"n": 1, "ref": "1", "text": "θεοὺς μὲν αἰτῶ"},
            {"n": 2, "ref": "2", "text": "τί φής; ἀκούω δή."},
        ], "speakers": [
            {"line": 1, "offset": 0, "label": "ΚΗ.", "display": "Herald"},
            {"line": 2, "offset": 0, "label": "ΧΟ.", "display": "Chorus"},
            {"line": 2, "offset": 7, "label": "ΚΗ.", "display": "Herald"},
        ]},
        {"id": "1:3", "book": 1, "column": "3", "lines": [
            {"n": 3, "ref": "3", "text": "λόγον λέγω σοι"},
            {"n": 4, "ref": "4", "text": "καλῶς. πάνυ μὲν οὖν"},
        ], "speakers": [
            {"line": 4, "offset": 7, "label": "ΧΟ.", "display": "Chorus"},
        ]},
        {"id": "1:2", "book": 1, "column": "2", "lines": [
            {"n": 5, "ref": "2", "text": "ἔα ἔα"},
        ], "speakers": [
            {"line": 5, "offset": 0, "label": "—", "display": None},
        ]},
    ],
}


def _tokens(spine=None):
    tokens, _, failures = tokenize(spine or _SPINE)
    assert not failures
    base, run = [], 0
    for seg in tokens["segments"]:
        base.append(run)
        run += sum(len(l["tokens"]) for l in seg["lines"])
    return tokens, base, run


def _speeches(spine=None):
    spine = spine or _SPINE
    tokens, base, total = _tokens(spine)
    return speeches_mod.build_speeches(tokens["segments"], spine["segments"], base), tokens, base, total


# -- Speech bounds -----------------------------------------------------------

def test_every_cue_starts_a_speech_at_its_first_token():
    speeches, tokens, base, total = _speeches()
    assert speeches_mod.chapter_bounds(speeches) == [
        {"book": 1, "chapter": "1", "start": 0, "accuracy": "exact"},
        # Antilabe: both speeches start on printed line 2; the later is 2b.
        {"book": 1, "chapter": "2", "start": 3, "accuracy": "exact"},
        {"book": 1, "chapter": "2b", "start": 5, "accuracy": "exact"},
        # Mid-line 4, after "καλῶς." (the cap continuation 1:3 has no bound
        # of its own: it continues the Herald's speech).
        {"book": 1, "chapter": "4", "start": 11, "accuracy": "exact"},
        # The repeated ref "2" is taken: suffix, skipping nothing reserved.
        {"book": 1, "chapter": "2c", "start": 14, "accuracy": "exact"},
    ]
    stream = [t["t"] for s in tokens["segments"] for l in s["lines"] for t in l["tokens"]]
    assert [stream[sp["start"]] for sp in speeches] == ["θεοὺς", "τί", "ἀκούω", "πάνυ", "ἔα"]


def test_turns_name_the_display_and_the_dash_names_no_one():
    speeches, *_ = _speeches()
    assert [(t["speaker"], t["start"]) for t in speeches_mod.turn_bounds(speeches)] == [
        ("Herald", 0), ("Chorus", 3), ("Herald", 5), ("Chorus", 11), ("", 14)]
    assert [sp["title"] for sp in speeches] == ["Herald", "Chorus", "Herald", "Chorus", "—"]
    assert [sp["bekker"] for sp in speeches] == ["1", "2", "2–4", "4", "2"]


def test_a_play_opening_with_no_cue_still_starts_a_speech():
    spine = json.loads(json.dumps(_SPINE))
    spine["segments"][0]["speakers"] = spine["segments"][0]["speakers"][1:]
    speeches, *_ = _speeches(spine)
    assert [(sp["name"], sp["start"], sp["cued"], sp["speaker"]) for sp in speeches[:3]] == [
        ("1", 0, False, ""), ("2", 3, True, "Chorus"), ("2b", 5, True, "Herald")]
    # The uncued opening is a chapter but not a turn: speakerAt() is null there.
    assert speeches_mod.turn_bounds(speeches)[0]["start"] == 3


def test_suffixes_skip_a_ref_that_starts_a_speech_of_its_own():
    spine = json.loads(json.dumps(_SPINE))
    spine["segments"][1]["lines"][1]["ref"] = "2b"
    names = [sp["name"] for sp in _speeches(spine)[0]]
    assert names == ["1", "2", "2c", "2b", "2d"]
    assert len(set(names)) == len(names)


def test_a_cue_with_no_greek_after_it_in_the_book_is_dropped():
    spine = json.loads(json.dumps(_SPINE))
    spine["segments"][2]["speakers"].append({"line": 5, "offset": 6, "label": "ΚΗ.", "display": "Herald"})
    speeches, *_ = _speeches(spine)
    assert speeches[-1]["name"] == "2c"


def test_offsets_check_refuses_bad_speech_bounds():
    speeches, tokens, base, total = _speeches()
    offsets = {"token_count": total, "seg_base_offset": base, "book_bounds": [{"book": 1, "start": 0}],
               "segments": [{"line_runs": [[l["n"], len(l["tokens"])] for l in s["lines"]]}
                            for s in tokens["segments"]],
               "chapter_bounds": speeches_mod.chapter_bounds(speeches),
               "turn_bounds": speeches_mod.turn_bounds(speeches)}
    assert check_offsets(offsets, tokens["segments"])["ok"]
    bad = json.loads(json.dumps(offsets))
    bad["chapter_bounds"][2]["chapter"] = "2"
    bad["chapter_bounds"][0]["start"] = 1
    bad["chapter_bounds"][4]["start"] = 2
    problems = check_offsets(bad, tokens["segments"])["problems"]
    assert any("name used twice" in p for p in problems)
    assert any("before the bound above" in p for p in problems)
    assert any("not the book's first token" in p for p in problems)


# -- Stage 6 end to end ------------------------------------------------------

def _stage6(tmp_path, monkeypatch, spine=None, work=None):
    build = tmp_path / "build"
    for stage in ("stage1", "stage3", "stage4"):
        (build / stage).mkdir(parents=True)
    spine = spine or _SPINE
    tokens, _, _ = _tokens(spine)
    (build / "stage1" / "greek_spine.json").write_text(json.dumps(spine, ensure_ascii=False), encoding="utf-8")
    (build / "stage3" / "tokens.json").write_text(json.dumps(tokens, ensure_ascii=False), encoding="utf-8")
    keys = {t["k"] for s in tokens["segments"] for l in s["lines"] for t in l["tokens"] if "k" in t}
    (build / "stage4" / "key_map.json").write_text(json.dumps({k: k for k in keys}), encoding="utf-8")
    (build / "stage4" / "analyses.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(stage6_search, "BUILD_DIR", build)
    return stage6_search.run(Manifest({"work": work or {"id": "TST", "edition_id": "x"}}, build / "TST.yaml"))


def test_stage6_writes_speech_bounds_running_text_and_aristotles_greek_names(tmp_path, monkeypatch):
    out = _stage6(tmp_path, monkeypatch)
    offsets = json.loads((out / "offsets.json").read_text())
    assert [c["chapter"] for c in offsets["chapter_bounds"]] == ["1", "2", "2b", "4", "2c"]
    assert [t["speaker"] for t in offsets["turn_bounds"]] == ["Herald", "Chorus", "Herald", "Chorus", ""]
    assert (out / "greek_lemma.json").exists() and (out / "greek_form.json").exists()
    assert not (out / "lemma.json").exists() and not (out / "form.json").exists()
    running = json.loads((out / "running.json").read_text())
    assert running["token_count"] == offsets["token_count"] == len(token_spans(running["text"]))
    assert running["text"].startswith("qeou\\s me\\n ai)tw=")
    speeches = json.loads((out / "speeches.json").read_text())
    assert [(s["name"], s["start"]) for s in speeches] == [
        (c["chapter"], c["start"]) for c in offsets["chapter_bounds"]]


def test_an_edition_with_a_letterless_token_has_no_running_text(tmp_path, monkeypatch):
    # An OCR edition's ellipsis is a token with no letter: it has no run in
    # the running text, so the edition goes without one; a reference work
    # with such a token is an error.
    spine = json.loads(json.dumps(_SPINE))
    spine["segments"][1]["lines"][0]["text"] = "λόγον … σοι"
    out = _stage6(tmp_path, monkeypatch, spine)
    assert not (out / "running.json").exists() and (out / "offsets.json").exists()
    with pytest.raises(ValueError, match="no Greek letter"):
        _stage6(tmp_path / "ref", monkeypatch, spine, work={"id": "TST"})


# -- Running text ------------------------------------------------------------

def test_running_text_keeps_the_plays_tokens_and_the_printed_punctuation():
    # Aristotle's shared fixture spine (pipeline/tests/fixtures/running_text.json
    # there). The plays' stage 3 peels a closing ’ after a stop as a quote,
    # where Aristotle's keeps it in the word: "le/geis;\"" not "le/geis'".
    spine = {"work": "Test", "segments": [
        {"id": "1:17a", "book": 1, "column": "17a", "lines": [
            {"n": 1, "text": "Ὅτι μὲν ὑμεῖς, ὦ ἄνδρες Ἀθηναῖοι, πεπόνθατε"},
            {"n": 2, "text": "ὑπὸ τῶν ἐμῶν κατηγόρων, οὐκ οἶδα· ἐγὼ δ' οὖν"}]},
        {"id": "1:17b", "book": 1, "column": "17b", "lines": [
            {"n": 1, "text": "[καὶ] ἀ<μφι>γνοεῖν — \"Τί δή;\" ᾧ (ὡς) δοκεῖ."},
            {"n": 2, "text": ""}, {"n": 3, "text": "—"},
            {"n": 4, "text": "τί λέγεις;’ ἔφη."}]},
    ]}
    tokens, _, total = _tokens(spine)
    text = build_running_text(tokens["segments"], spine)
    check_alignment("Test", text, tokens["segments"], total)
    assert total == 26
    assert text == (
        "o(/ti me\\n u(mei=s, w)= a)/ndres a)qhnai=oi, pepo/nqate u(po\\ tw=n e)mw=n "
        "kathgo/rwn, ou)k oi)=da: e)gw\\ d' ou)=n kai\\ a)mfignoei=n - \"ti/ dh/;\" "
        "w(=| w(s dokei=. - ti/ le/geis;\" e)/fh."
    )


def test_running_text_refuses_a_token_out_of_place():
    tokens, _, _ = _tokens()
    tokens["segments"][0]["lines"][0]["tokens"][1]["o"] += 1
    with pytest.raises(ValueError, match="not at offset"):
        build_running_text(tokens["segments"], _SPINE)


# -- English indexes and eng-chapters ----------------------------------------

def _work(tmp_path, segments):
    """An emitted play: book-01.json, search/meta.json and offsets.json, and
    the speeches stage 6 would write for _SPINE."""
    speeches, tokens, base, total = _speeches()
    work = tmp_path / "dist" / "TST"
    (work / "search").mkdir(parents=True)
    (work / "book-01.json").write_text(json.dumps(
        {"book": 1, "segments": segments, "speakerRoster": ["Herald", "Chorus"]}, ensure_ascii=False),
        encoding="utf-8")
    (work / "search" / "meta.json").write_text(json.dumps(
        [{"id": s["id"], "book": 1, "column": s["column"]} for s in _SPINE["segments"]]), encoding="utf-8")
    (work / "search" / "offsets.json").write_text(json.dumps(
        {"token_count": total, "seg_base_offset": base,
         "chapter_bounds": speeches_mod.chapter_bounds(speeches)}), encoding="utf-8")
    return work, speeches


_SEGMENTS = [
    {"id": "1:1", "column": "1",
     "english": {"text": "I pray the gods.\n\nWhat say you? I hear [^1.2] it, truly.",
                 "turns": [{"offset": 0, "speaker": "Herald"}, {"offset": 18, "speaker": "Chorus"},
                           {"offset": 32, "speaker": "Herald"}]},
     # Three cues, as the Greek has: split (the second cue is a different
     # speaker from the Greek's, and still pairs by order).
     "ross": [{"chapter": "1", "text": "HERALD. Gods, release me.\n\nLEADER. What?\n\nHERALD. I hear."}],
     # Two cues for three speeches: left to the fallback.
     "third": [{"chapter": "1", "text": "HERALD. Gods.\n\nCHORUS. What? I hear."}],
     "overlays": {"murray-verse": [
         {"chapter": "1", "text": "HERALD. O gods,", "cueSpeakers": ["Herald"]},
         {"chapter": "1", "text": "Chorus. Speak!\n\nHERALD. I hear.", "cueSpeakers": ["Chorus", "Herald"]}]}},
    {"id": "1:3", "column": "3",
     "english": {"text": "A word I say. Well. Yes indeed.", "turns": [{"offset": 20, "speaker": "Chorus"}]},
     "ross": [{"chapter": "3", "text": "A word. Well said, Yes."}]},
    {"id": "1:2", "column": "2", "english": {"text": "Ah, ah!", "turns": [{"offset": 0, "speaker": None}]}},
]


def test_english_positions_count_words_as_the_reader_does(tmp_path):
    work, speeches = _work(tmp_path, _SEGMENTS)
    emit_translation_indexes(work, speeches)
    search = work / "search"
    files = sorted(p.name for p in search.glob("english*.json"))
    assert files == ["english-overlay-murray-verse.json", "english-secondary.json",
                     "english-third.json", "english.json"]
    for name, slot in (("english.json", "english"), ("english-secondary.json", "ross"),
                       ("english-overlay-murray-verse.json", "murray-verse")):
        index = json.loads((search / name).read_text())
        for si, seg in enumerate(_SEGMENTS):
            if slot == "english":
                texts = [seg["english"]["text"]]
            elif slot == "ross":
                texts = [p["text"] for p in seg.get("ross", [])]
            else:
                texts = [p["text"] for p in seg.get("overlays", {}).get(slot, [])]
            # Pieces run on with no reset, as the reader counts them.
            words = [w for t in texts for w in english_words(t)]
            for pos, word in enumerate(words):
                assert [si, pos] in index[word], (name, word)
    english = json.loads((search / "english.json").read_text())
    assert english["hear"] == [[0, 8]]  # the footnote marker is no word
    assert "1" not in english and "2" not in english


def test_eng_chapters_split_a_shared_segment_only_where_the_cues_pair(tmp_path):
    work, speeches = _work(tmp_path, _SEGMENTS)
    summary = emit_translation_indexes(work, speeches)
    chapters = json.loads((work / "search" / "eng-chapters.json").read_text())
    assert chapters["english"] == {"0": [[0, "1"], [4, "2"], [7, "2b"]], "1": [[5, "4"]]}
    assert chapters["secondary"] == {"0": [[0, "1"], [4, "2"], [6, "2b"]]}
    assert chapters["overlay-murray-verse"] == {"0": [[0, "1"], [3, "2"], [5, "2b"]]}
    assert "third" not in chapters  # two cues for three speeches
    assert summary["english"]["split"] == 2 and summary["english"]["fallback"] == 0
    # 1:3's secondary has no cue for its mid-segment speech.
    assert summary["secondary"]["split"] == 1 and summary["secondary"]["fallback"] == 1
    assert summary["third"] == {"words": 6, "segments": 1, "split": 0, "fallback": 1}


def test_a_private_slot_is_not_indexed_and_a_stale_index_goes(tmp_path):
    work, speeches = _work(tmp_path, _SEGMENTS)
    (work / "search" / "english-old.json").write_text("{}")
    emit_translation_indexes(work, speeches, {"third"})
    names = {p.name for p in (work / "search").glob("english*.json")}
    assert "english-third.json" not in names and "english-old.json" not in names


def test_stale_speeches_are_refused(tmp_path):
    work, speeches = _work(tmp_path, _SEGMENTS)
    speeches[1]["start"] += 1
    with pytest.raises(ValueError, match="stale stage 6"):
        emit_translation_indexes(work, speeches)


# -- Stage 9 -----------------------------------------------------------------

def test_shards_take_aristotles_sources_vocab_and_accents(tmp_path):
    work, speeches = _work(tmp_path, _SEGMENTS)
    emit_translation_indexes(work, speeches)
    search = work / "search"
    (search / "greek_lemma.json").write_text(json.dumps({"qeos": [[0, 0]]}))
    (search / "greek_form.json").write_text(json.dumps({"qeous": [[0, 0]], "ea": [[2, 0], [2, 1]]}))
    book = json.loads((work / "book-01.json").read_text())
    book["segments"][0]["greek"] = [{"n": 1, "tokens": [{"t": "θεοὺς", "k": "qeou\\s"}]}]
    book["segments"][2]["greek"] = [{"n": 5, "tokens": [{"t": "ἔα", "k": "e)/a"}, {"t": "<ἔα>", "k": "e)/a"}]}]
    (work / "book-01.json").write_text(json.dumps(book, ensure_ascii=False), encoding="utf-8")
    out = stage9(tmp_path / "dist")
    index = json.loads((out / "index.json").read_text())
    assert sorted(index["streams"]["english"]["sources"]) == [
        "TST/english", "TST/overlay-murray-verse", "TST/secondary", "TST/third"]
    assert sorted(index["streams"]["lemma"]["sources"]) == ["TST"]
    shard = json.loads((out / "english" / "he.json").read_text())
    english = json.loads((search / "english.json").read_text())
    assert shard["hear"]["TST/english"] == english["hear"]
    assert json.loads((out / "vocab.json").read_text()) == {"forms": ["ea", "qeous"], "lemmas": ["qeos"]}
    assert index["streams"]["accents"]["shards"] == ["ea", "qe"]
    assert json.loads((out / "accents" / "qe.json").read_text()) == {"qeous": ["θεούς"]}
    assert json.loads((out / "accents" / "ea.json").read_text()) == {"ea": ["ἔα"]}
