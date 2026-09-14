// Speaker-turn rendering model for Stephanus dialogues (Plato). The pipeline
// emits, per Greek segment, a `speakers` array of turn events — {line, offset,
// label} — where `offset` is the char position in that line's rejoined text at
// which the interlocutor's speech begins, and `label` is the siglum ("ΕΥΘ.",
// "ΣΩ.") or the dialectic dash ("—"). Crucially, the label text itself is NOT
// present in the line text: it is rendered as a separate inline lead-in span so
// the clickable Greek tokens keep their exact char offsets (the word popup and
// every offset walker must see an unshifted token stream).
//
// This module owns the position math: given a line's verbatim text, its tokens,
// and the events that belong to that line, it produces an ordered list of
// render parts — plain text gaps, clickable tokens, and speaker lead-ins spliced
// in at each turn boundary — WITHOUT mutating the line text. It generalizes the
// reader's old `lineParts` (a text→tokens splitter): with no events it returns
// exactly the same token/gap sequence, so non-stephanus works are byte-identical.

import type { Token, GreekLine, Segment, TurnFlow, EnglishTurn } from './data';

// A single speaker-turn event, as emitted in a segment's `speakers` array.
export interface SpeakerEvent {
  line: number;    // the Greek line `n` the turn begins on
  offset: number;  // char offset in that line's text where the speech begins
  label: string;   // the interlocutor siglum ("ΕΥΘ.") or the dialectic dash "—"
  display?: string | null; // canonical English name; null for the dash
}

// One render part for a Greek line: a verbatim text gap (sigla / punctuation),
// a clickable token, or a speaker lead-in label inserted at a turn boundary.
export type LineRenderPart =
  | { kind: 'text'; text: string }
  | { kind: 'token'; text: string; tok: Token }
  | { kind: 'speaker'; label: string; display?: string | null; dash: boolean };

// The dialectic dash ("—", used e.g. in Parmenides for unattributed turns)
// renders as a plain em-dash lead-in, not a small-caps siglum.
const DASH = '—';

// Editorial sigla an edition prints INSIDE a word: angle brackets for a
// supplement (Plato Letters 362a "ἔπει<τα>") and square brackets for a deletion
// (Philebus 52d "[προς]θῶμεν"). The token text is the bare word, so it does not
// occur verbatim in the line and a plain indexOf misses it. No line in this
// repo's corpus currently does this — the guard is here because the same
// shared machinery serves plato-reader and aristotle-reader, where 20 and 23
// lines respectively printed the word twice, and because the next edition
// ingested could bring one in.
const SIGLUM = /[<>[\]]/;
const OPENER = /[<[]/;
const CLOSER = /[>\]]/;

// Locate `t` in `text` at or after `from`, tolerating sigla printed inside the
// word, and return its VERBATIM span (sigla included) so the rendered line
// stays byte-identical to the source. Null when the word really isn't there.
function locateToken(text: string, t: string, from: number): { start: number; end: number } | null {
  const plain = text.indexOf(t, from);
  if (plain >= 0) return { start: plain, end: plain + t.length };
  for (let s = from; s < text.length; s += 1) {
    if (text[s] !== t[0]) continue;
    let i = s;
    let k = 0;
    let open = 0; // brackets opened inside the word, still to be closed
    while (i < text.length && k < t.length) {
      if (text[i] === t[k]) { i += 1; k += 1; }
      else if (SIGLUM.test(text[i])) { open += OPENER.test(text[i]) ? 1 : -1; i += 1; }
      else break;
    }
    if (k !== t.length) continue;
    // A bracket still OPEN at the end of the word closes just past it
    // ("ἔπει<τα>"): pull the closer in, or it would render as a gap detached
    // from its word. One that already closed mid-word ("ἀ<μφι>γνοεῖν") leaves
    // nothing owing, so a following closer belongs to the phrase, not the word.
    while (open > 0 && i < text.length && CLOSER.test(text[i])) { open -= 1; i += 1; }
    return { start: s, end: i };
  }
  return null;
}

// Build the render parts for a Greek line. `text` is the line's verbatim text
// (with OCT sigla and punctuation); `tokens` are its clickable words; `events`
// are the speaker turns that begin on this line (already filtered to it).
//
// The token/gap split is identical to the reader's historical `lineParts`: each
// token is located in `text` from a moving pointer, and the verbatim spans
// between tokens become plain-text parts. Speaker lead-ins are then spliced in
// at their char offsets — at a token boundary they sit immediately before the
// token; inside a verbatim gap the gap is split around them. The line text is
// never altered, so token char-offsets never move.
export function lineRenderParts(
  text: string,
  tokens: readonly Token[],
  events: readonly SpeakerEvent[] = [],
): LineRenderPart[] {
  // Atoms: the token/gap sequence, each tagged with its [start, end) char span.
  // A token with no `k` (non-lexical: no Greek letters at all — inline
  // apparatus, editor names, bare numerals) has no lexicon entry to link to,
  // so it renders as plain text, not a clickable token — same char span
  // either way, so this doesn't move any offsets.
  type Atom = { part: LineRenderPart; start: number; end: number };
  const atoms: Atom[] = [];
  let ptr = 0;
  for (const tok of tokens) {
    const at = locateToken(text, tok.t, ptr);
    // Shouldn't happen. Emit nothing: the verbatim text still prints the word
    // in a later gap, so a phantom atom here would print it TWICE. The word
    // just loses its click target.
    if (!at) continue;
    const { start: i, end } = at;
    if (i > ptr) atoms.push({ part: { kind: 'text', text: text.slice(ptr, i) }, start: ptr, end: i });
    // `text` is the verbatim slice (sigla and all); `tok` carries the bare word
    // for the popup, the search-hit test and the aria-label.
    const surface = text.slice(i, end);
    const part: LineRenderPart = tok.k
      ? { kind: 'token', text: surface, tok }
      : { kind: 'text', text: surface };
    atoms.push({ part, start: i, end });
    ptr = end;
  }
  if (ptr < text.length) atoms.push({ part: { kind: 'text', text: text.slice(ptr) }, start: ptr, end: text.length });

  if (events.length === 0) return atoms.map((a) => a.part);

  const evs = [...events].sort((a, b) => a.offset - b.offset);
  const out: LineRenderPart[] = [];
  let ei = 0;
  const pushSpeaker = (e: SpeakerEvent) =>
    out.push({ kind: 'speaker', label: e.label, display: e.display, dash: e.label === DASH });

  for (const a of atoms) {
    // Any events landing at or before this atom's start lead it in.
    while (ei < evs.length && evs[ei].offset <= a.start) { pushSpeaker(evs[ei]); ei += 1; }
    // An event falling strictly inside a verbatim gap splits the gap around it;
    // tokens are never split (an interior offset attaches before the next atom).
    if (a.part.kind === 'text' && ei < evs.length && evs[ei].offset < a.end) {
      let cur = a.start;
      while (ei < evs.length && evs[ei].offset < a.end) {
        const off = evs[ei].offset;
        if (off > cur) out.push({ kind: 'text', text: text.slice(cur, off) });
        pushSpeaker(evs[ei]);
        ei += 1;
        cur = off;
      }
      if (cur < a.end) out.push({ kind: 'text', text: text.slice(cur, a.end) });
    } else {
      out.push(a.part);
    }
  }
  // Trailing events (offset at/after the line end) close out the line.
  while (ei < evs.length) { pushSpeaker(evs[ei]); ei += 1; }
  return out;
}

// Lined-source only (Discourses, docs/lined-source-plan.md Q2; wrapO
// deviation 2026-08-29, §3): split a wrapped line's already-built render
// parts (from lineRenderParts above) at the WRAPPED token -- the one whose
// `tok.o === wrapO` -- into the parts THIS line keeps (`head`, the wrapped
// token repainted as `t.slice(0, wrap) + '-'`) and the parts that move to
// the NEXT line's leading edge (`carried`: the wrapped token's own
// remainder `t.slice(wrap)`, bound to that SAME token object, followed by
// every render part that came after it unchanged). Hovering/clicking either
// half of the wrapped word opens the same popup, since both pieces share
// one token object; a carried FULL token (e.g. "πολλὴν" in the em-dash glob
// case below) keeps its own separate token binding, so it stays
// independently clickable.
//
// `wrapO` names the wrapped token explicitly rather than leaving the caller
// to infer "the last token": `joined` absorbs the WHOLE whitespace-
// delimited continuation fragment (I4), which can glue MORE than the
// wrapped word onto this line when the source glues an em dash straight
// onto the next word with no space (epicurus-letter-to-herodotus §53/§69:
// "…σχηματίζε-" / "σθαι—πολλὴν…" absorbs "σθαι—πολλὴν" whole, so this
// line's LAST token is "πολλὴν", not the wrapped "σχηματίζεσθαι"). Finding
// the part by `tok.o` rather than by array position also means a preceding
// speaker lead-in (never possible to insert one AFTER a token, per
// lineRenderParts' own contract) cannot desync the lookup.
//
// I3's 2026-08-29 amendment (docs/lined-source-plan.md §3): the absorbed
// continuation fragment usually carries attached punctuation (a section
// starts after a sentence ends), so a render part right after the wrapped
// token is often a letterless TEXT tail (e.g. the "." atom `lineRenderParts`
// emits after the token) rather than another token. That tail rides along
// in `carried` exactly like any other trailing part -- never painted after
// this line's repainted hyphen (Schenkl prints "κιμαστικήν." on the
// following line, not "ἀποδο-." on this one).
//
// If no part matches `wrapO` at all (a defensive fail-safe only -- the data
// invariant I3 requires it), `head` is the parts unchanged and `carried` is
// empty, rather than guessing which atom to split.
//
// Sigma-fold correction (docs/lined-source-plan.md §3, 2026-08-29): Greek
// print sets the LINE-FINAL form of sigma (ς) immediately before a wrap
// hyphen even when it sits in MEDIAL position once rejoined -- Schenkl
// prints "προς-" / "ήκει" for προσήκει. Because no Greek word contains a
// medial ς, stage1_greek.py's rejoin (`_fold_hyphen_final_sigma`) folds
// that character back to the ordinary σ in the STORED surface, so `t`
// always carries the correct medial σ there. Repainting the split must undo
// the fold for DISPLAY ONLY, reproducing what Schenkl's page actually
// printed: a trailing σ in the head fragment becomes ς before the hyphen is
// appended, looking back through any trailing `>`/`]` closing sigla.
function foldTrailingSigmaForDisplay(fragment: string): string {
  return fragment.replace(/σ(?=[>\]]*$)/u, 'ς');
}

export function splitWrapLine(
  parts: readonly LineRenderPart[],
  wrapO: number,
  wrap: number,
): { head: LineRenderPart[]; carried: LineRenderPart[] } {
  const i = parts.findIndex((p) => p.kind === 'token' && p.tok.o === wrapO);
  if (i < 0) return { head: [...parts], carried: [] };
  const wrapped = parts[i] as Extract<LineRenderPart, { kind: 'token' }>;
  const headText = foldTrailingSigmaForDisplay(wrapped.text.slice(0, wrap));
  const head: LineRenderPart = { kind: 'token', text: headText + '-', tok: wrapped.tok };
  const carriedHead: LineRenderPart = { kind: 'token', text: wrapped.text.slice(wrap), tok: wrapped.tok };
  return {
    head: [...parts.slice(0, i), head],
    carried: [carriedHead, ...parts.slice(i + 1)],
  };
}

// ── Turn-flow row model (Stephanus dialogues) ────────────────────────────────
// John's Tier-0 requirement: each speaker's statement is the aligned ROW — the
// first Greek line of a turn sits level with the first English line of its
// translation, for the WHOLE BOOK (the pipeline pairs turns globally, so
// Stephanus section boundaries never break a row). Sections dissolve into the
// continuous flow; each section's first Greek line carries a gutter TICK (the
// column token, e.g. "2b") which is also the `col-{token}` citation anchor.
// `buildFlowRows` is a pure function of (segments, turnFlow) so it can be
// unit-tested independently of the reader.

// One Greek line (or a slice of one) inside a flow row. `col` + `n` identify
// the line (`L{col}-{n}` DOM id); `cont` marks a partial tail of a line opened
// in an earlier row (no repeated id — the reader emits `-c`); `tick` carries
// the section token when this line opens a Stephanus section (the reader
// floats it in the gutter and anchors `col-{tick}` on it).
export interface FlowLine {
  col: string;
  n: number;
  cont: boolean;
  tick: string | null;
  parts: LineRenderPart[];
}

// One row of the turn flow: a paired turn (Greek beside English), a one-sided
// residual (greek/english empty on the other side), or the leading
// continuation row before the first turn.
export interface FlowRow {
  lead: boolean;
  paired: boolean;
  // The printed English lead-in ("Soc."); null for an unattributed dash turn
  // (rendered as an em-dash) and for Greek-only residuals (the Greek cell
  // shows its own siglum inline).
  display: string | null;
  speaker: string | null;
  greek: FlowLine[];
  english: string | null;
  // Continuation paragraphs merged into this row's English cell: an unpaired
  // English residual whose speaker matches this row (or is unattributed) is
  // the SAME speech split by Perseus where the OCT has one turn — it flows
  // under this row as a sub-paragraph (print convention: no repeated label)
  // instead of rendering as a one-sided row beside blank Greek. A residual
  // whose speaker DIFFERS still gets its own one-sided row (never
  // mis-attribute). Each continuation keeps its own `ep` paragraph breaks
  // (Timaeus/Phaedo long residual speeches carry them — B2).
  englishCont: { text: string; ep?: number[] | null }[];
  // Section tokens whose ticks fall inside this row's Greek — the reader
  // renders row-level gutter markers from these in English-only view (where
  // the Greek cells, and so the exact tick lines, are hidden).
  ticks: string[];
  // ── Flow-extension passthrough, carried verbatim from the FlowTurn (see
  // data.ts FlowTurn for semantics; `T[] | null` because the pipeline emits
  // explicit nulls, undefined on old JSON / synthetic rows). `ep` are the
  // paragraph-break offsets inside this row's English (para flows and long
  // dialogue speeches); `et` embeds english.turns as intra-row speech blocks
  // (para flows); `sub` stacks one-sided English speeches folded under this
  // row (B4 residual rows — usually `english` is null).
  ep?: number[] | null;
  et?: { o: number; s: string | null; d: string | null }[] | null;
  sub?: { s: string | null; d: string | null; e: string; ep?: number[] | null }[] | null;
  // Alternate-translation slices for this row, keyed by translation id (carried
  // verbatim from the FlowTurn; see data.ts). The reader's turn-by-turn compare
  // renders `alt[id].e` in the second column beside this row's primary English.
  alt?: Record<string, { e: string | null; ep?: number[] | null }> | null;
}

// The whole book's Greek lines in document order, each carrying its column and
// (for the first line of each section) its tick token.
interface BookLine {
  col: string;
  tick: string | null;
  line: GreekLine;
  events: SpeakerEvent[];
}

function bookLines(segments: readonly Segment[]): BookLine[] {
  const out: BookLine[] = [];
  for (const seg of segments) {
    seg.greek.forEach((line, i) => {
      out.push({
        col: seg.column,
        tick: i === 0 ? seg.column : null,
        line,
        events: (seg.speakers ?? []).filter((s) => s.line === line.n),
      });
    });
  }
  return out;
}

// The Greek render-lines covering [from, to) over the book's line list, where a
// bound is a line index + char offset. Tokens whose start falls in the slice
// stay clickable (ORIGINAL Token objects — lineRenderParts locates each by its
// surface text, never by `o`, so popup identity and Beta Code keys survive);
// speaker events in the slice are spliced in as lead-ins. A line opened at
// offset 0 keeps its id and its section tick; a partial tail is `cont`.
function sliceBook(
  lines: readonly BookLine[],
  from: { i: number; o: number },
  to: { i: number; o: number },
): FlowLine[] {
  const out: FlowLine[] = [];
  for (let i = from.i; i <= to.i && i < lines.length; i += 1) {
    const B = lines[i];
    const s = i === from.i ? from.o : 0;
    const e = i === to.i ? to.o : B.line.text.length;
    if (s >= e) continue; // empty slice (a boundary on a line edge)
    const text = B.line.text.slice(s, e);
    const tokens: Token[] = B.line.tokens.filter((t) => t.o >= s && t.o < e);
    const evs = B.events
      .filter((ev) => ev.offset >= s && ev.offset < e)
      .map((ev) => ({ ...ev, offset: ev.offset - s }));
    out.push({
      col: B.col,
      n: B.line.n,
      cont: s > 0,
      tick: s === 0 ? B.tick : null,
      parts: lineRenderParts(text, tokens, evs),
    });
  }
  return out;
}

export function buildFlowRows(
  segments: readonly Segment[],
  flow: TurnFlow,
): FlowRow[] {
  const lines = bookLines(segments);
  if (!lines.length || !flow.turns.length) return [];
  // Line index of each (column, n) ref. Line numbers restart per section, so
  // the key needs both.
  const idx = new Map<string, number>();
  lines.forEach((b, i) => idx.set(`${b.col} ${b.line.n}`, i));
  // Bound of each Greek-bearing turn; null for English-only residuals and for
  // an unresolvable ref (which then contributes no Greek slice).
  const bounds: ({ i: number; o: number } | null)[] = flow.turns.map((t) => {
    if (!t.g) return null;
    const i = idx.get(`${t.g.c} ${t.g.n}`);
    return i === undefined ? null : { i, o: t.g.o };
  });
  const end = { i: lines.length - 1, o: lines[lines.length - 1].line.text.length };
  // For each Greek-bearing turn, its slice runs to the NEXT Greek-bearing
  // turn's start (residual English turns in between don't cut the Greek).
  const nextG: ({ i: number; o: number } | null)[] = new Array(flow.turns.length).fill(null);
  let nxt: { i: number; o: number } = end;
  for (let ti = flow.turns.length - 1; ti >= 0; ti -= 1) {
    nextG[ti] = nxt;
    if (bounds[ti]) nxt = bounds[ti]!;
  }
  const ticksOf = (greek: FlowLine[]) =>
    greek.filter((l) => l.tick !== null).map((l) => l.tick!);

  const rows: FlowRow[] = [];
  // Leading row: Greek before the first Greek turn + English before the first
  // English turn (both are tails of speech begun before this book/section span).
  const firstG = bounds.find((b) => b !== null) ?? end;
  const leadGreek = sliceBook(lines, { i: 0, o: 0 }, firstG);
  if (leadGreek.length || flow.leadE) {
    rows.push({
      lead: true, paired: false, display: null, speaker: null,
      greek: leadGreek, english: flow.leadE, englishCont: [],
      ticks: ticksOf(leadGreek),
    });
  }
  flow.turns.forEach((t, ti) => {
    const greek = bounds[ti] ? sliceBook(lines, bounds[ti]!, nextG[ti]!) : [];
    // An unpaired English residual continuing the PREVIOUS row's speaker (or
    // unattributed) merges into that row's English cell as a sub-paragraph —
    // Perseus split one OCT turn into several <said>. A different speaker
    // keeps its own one-sided row. A residual CARRYING sub-speeches (pipeline
    // B4's column-grouped rows, e.g. Lysis's opening narration) never merges:
    // englishCont can't hold the stacked speeches, so folding the text into
    // the previous row would silently drop them.
    const prev = rows[rows.length - 1];
    if (!t.p && greek.length === 0 && t.e && prev && !t.sub?.length
        && (t.s === null || t.s === prev.speaker)) {
      // Preserve the residual's paragraph breaks: as a continuation they ride
      // the englishCont entry; as the row's main English they become row.ep.
      if (prev.english) prev.englishCont.push({ text: t.e, ep: t.ep });
      else { prev.english = t.e; prev.ep = t.ep; }
      return;
    }
    // A GREEK-BEARING residual whose English is entirely folded sub-speeches by
    // the SAME speaker as the previous row is that speaker continuing across a
    // Stephanus SECTION boundary: Perseus/OCT open the section mid-speech (Meno
    // 70c starts at εἰδότας), but the translation's paragraph break comes a
    // clause later — so rendering the residual as its own row pushes that Greek
    // down beside the NEXT sentence's English. Merge it into the previous row so
    // the Greek flows beside the English it translates, with the section tick
    // inline; each sub becomes a continuation paragraph (no repeated label). Only
    // for dialogue flows, and only when every folded speech is the previous
    // speaker REPEATING THE SAME PRINTED LABEL (or unlabeled) — a redundant
    // "Soc." over an unbroken speech. A folded speech that carries a different
    // printed display (a section rubric like "The Speech of Pausanias" in a
    // narrated frame, whose canonical speaker is the narrator) is a real
    // heading, not a redundant label, so it keeps its own row; likewise a
    // differing/unattributed speaker (never mis-attribute) and a mixed stack.
    if (flow.kind !== 'para' && !t.p && greek.length > 0 && !t.e
        && prev && prev.speaker != null
        && t.sub?.length
        && t.sub.every((s) => s.s === prev.speaker && (s.d == null || s.d === prev.display))) {
      prev.greek.push(...greek);
      prev.ticks.push(...ticksOf(greek));
      for (const s of t.sub) prev.englishCont.push({ text: s.e, ep: s.ep });
      return;
    }
    rows.push({
      lead: false,
      paired: t.p,
      display: t.d,
      speaker: t.s,
      greek,
      english: t.e,
      englishCont: [],
      ticks: ticksOf(greek),
      // Paragraph-flow passthrough (undefined for dialogue turns).
      ep: t.ep,
      et: t.et,
      sub: t.sub,
      // Alternate-translation slices (undefined until the turn aligner runs).
      alt: t.alt,
    });
  });
  return rows;
}

// Redundant-label suppression, per flow row (aligned with the rows array). A
// lead-in / folded-sub label is hidden when it REPEATS the current speaker's
// SAME printed display — the pipeline re-emits "Soc." when one unbroken speech
// is split across a section boundary (Meno 70b→c). It is KEPT when the display
// differs (a section rubric like "The Speech of Pausanias", whose canonical
// speaker is the narrator, is a heading, not a redundant label). An em-dash
// turn (no display) is a genuine break that resets the floor, so a same-speaker
// turn after it keeps its label. Pure, so the reader can drive rendering from
// it and it stays unit-testable. The floor advances in render order: each row's
// lead-in (shown only when it has English) then its folded sub-speeches.
export interface RowLabelMeta { hideLead: boolean; hideSub: boolean[]; }

export function labelSuppression(rows: readonly FlowRow[]): RowLabelMeta[] {
  let floor: string | null = null;      // canonical speaker holding the floor
  let floorDisp: string | null = null;  // and their printed display
  return rows.map((row) => {
    let hideLead = false;
    if (!row.lead && row.english) {
      if (row.display) {
        hideLead = row.speaker != null && row.speaker === floor && row.display === floorDisp;
        floor = row.speaker;
        floorDisp = row.display;
      } else {
        floor = row.speaker; // em-dash turn: a real break
        floorDisp = null;
      }
    }
    const hideSub = (row.sub ?? []).map((s) => {
      let hide = false;
      if (s.d) {
        hide = s.s != null && s.s === floor && s.d === floorDisp;
        floor = s.s;
        floorDisp = s.d;
      } else {
        floor = s.s;
        floorDisp = null;
      }
      return hide;
    });
    return { hideLead, hideSub };
  });
}

// ── English turn blocks (narrated fallback) ─────────────────────────────────
// A narrated work's chunk that carries English <said> turns with no Greek
// events (Republic, Apology…) gets no turn flow, but its speeches still owe
// the reader per-turn structure: print editions set each speech as its own
// paragraph with its lead-in. This helper
// slices the chunk prose at the turn offsets into a stack of blocks — never an
// inline splice, so a label can never end up glued to the tail of the previous
// sentence ("…as I have.SOCRATES. Our…").

// One block of a fallback English stack. `lead` marks the unlabeled leading
// block (text before the first turn — the tail of a speech begun in an earlier
// section); `display` is the printed lead-in, null for an unattributed turn
// (rendered as an em-dash, mirroring the Greek dash); `speaker` is the
// canonical roster display (the colour key — same string as the Greek
// roster entry for that character), null when the turn carries none (older
// data, or an unattributed turn) — callers fall back to `display` for the
// `spkSlots` lookup so play-line English gets the same data-spk as the
// Greek lead-in of that character.
export interface EnglishTurnBlock {
  lead: boolean;
  display: string | null;
  speaker: string | null;
  text: string;
  // Carried from the turn (play-line, P2h): this turn's English speaker
  // disagrees with the Greek speech that prints the line. Only the lead-in of
  // this block is marked, never its neighbours in the same chunk.
  speakerMismatch?: { english: string; greek: string };
  // Index of the `turns[]` entry this block came from; -1 for the leading
  // pre-turn continuation. P4's per-line row model maps the k-th English turn
  // onto the k-th Greek speaker event, and an empty unlabeled turn is dropped
  // below — so a block's position in this array is NOT its turn index.
  turnIndex: number;
  // Carried from the turn: stage directions printed before this speech
  // (Arrowsmith). A row of their own where splitAtDirections can cut the
  // rows; otherwise printed inline above the speech.
  directionsBefore?: string[];
}

export function buildEnglishTurnBlocks(
  text: string,
  turns: readonly EnglishTurn[],
): EnglishTurnBlock[] {
  if (!turns.length) return [{ lead: true, display: null, speaker: null, text, turnIndex: -1 }];
  const blocks: EnglishTurnBlock[] = [];
  const lead = text.slice(0, turns[0].offset).trim();
  if (lead) blocks.push({ lead: true, display: null, speaker: null, text: lead, turnIndex: -1 });
  for (let i = 0; i < turns.length; i += 1) {
    const end = i + 1 < turns.length ? turns[i + 1].offset : text.length;
    const t = text.slice(turns[i].offset, end).trim();
    // An empty UNLABELED slice (two adjacent boundaries with nothing between,
    // e.g. a reported turn whose text the walker filed elsewhere) would render
    // as a bare em-dash paragraph — drop it. A labeled turn keeps its block
    // even when empty, so the attribution itself is never lost.
    if (!t && turns[i].display == null) continue;
    const mismatch = turns[i].speakerMismatch;
    const directions = turns[i].directionsBefore;
    blocks.push({
      lead: false,
      display: turns[i].display,
      speaker: turns[i].speaker ?? null,
      text: t,
      turnIndex: i,
      ...(mismatch ? { speakerMismatch: mismatch } : {}),
      ...(directions?.length ? { directionsBefore: directions } : {}),
    });
  }
  return blocks;
}

export interface EnglishTurnSource {
  text: string;
  turns: EnglishTurn[];
  // play-line, line-keyed translations (Smyth, Jebb, Coleridge): the chunk's
  // real line anchors, each the char offset where the translator's text for
  // that Greek line begins. The reader keys rows on them (REVIEW-CHECKLIST 15).
  ticks?: { n: number; offset: number; real: boolean }[];
}

// The first play-line comparison data stored speaker lead-ins in overlay text
// (`CHORUS. ...`) rather than in `turns`. Recover that standoff shape so old
// data uses the same turn-stack and colour path as newer structured overlays.
export function extractPrefixedEnglishTurns(
  text: string,
  roster: readonly string[],
  fallbackTurns: readonly EnglishTurn[] = [],
): EnglishTurnSource {
  const known = [...roster];
  for (const turn of fallbackTurns) {
    if (turn.speaker) known.push(turn.speaker);
    if (turn.display) known.push(turn.display);
  }
  const norm = (value: string): string => value
    .toLocaleLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, ' ')
    .trim();
  const knownByNorm = new Map<string, string>();
  for (const name of known) {
    const key = norm(name);
    if (!knownByNorm.has(key)) knownByNorm.set(key, name);
  }
  const candidates = [...text.matchAll(/(^|\n{2,})([^.\n]{1,80})\.\s+/g)].filter((match) => {
    const label = match[2].trim();
    return knownByNorm.has(norm(label))
      || (/\p{L}/u.test(label) && label === label.toLocaleUpperCase());
  });
  if (!candidates.length) return { text, turns: [] };

  let clean = '';
  let cursor = 0;
  const turns: EnglishTurn[] = [];
  candidates.forEach((match, index) => {
    const start = match.index ?? 0;
    clean += text.slice(cursor, start) + match[1];
    const label = match[2].trim();
    const fallback = fallbackTurns[index];
    turns.push({
      offset: clean.length,
      speaker: knownByNorm.get(norm(label)) ?? fallback?.speaker ?? fallback?.display ?? label,
      display: label,
    });
    cursor = start + match[0].length;
  });
  clean += text.slice(cursor);
  return { text: clean, turns };
}

// ── Section-paragraph split (Discourses' `sections` channel) ────────────────
// Splits a Greek line carrying a `sections` standoff channel (Discourses/
// Enchiridion only — see GreekLine.sections and stage1_greek._chapter_sections)
// into one piece per kept TLG section, each tagged `paraN` with that section's
// number (Reader.svelte renders it as a small muted label before the piece).
// A line with no `sections` (or fewer than 2 entries — the pipeline never
// emits that shape, but this stays defensive) passes through UNCHANGED — the
// exact same object, not a copy — so every work that never opts into this
// channel renders byte-identically to before this feature existed.

// A GreekLine piece produced by a split: `cont` marks every piece after the
// first (so its line number/id isn't repeated, matching an ordinary mid-line
// chapter-split continuation); `paraN` is the TLG section number the piece
// opens.
export type SectionedGreekLine = GreekLine & { cont?: boolean; paraN?: number };

// A GPT-5.6-Sol-High adversarial review found the original implementation
// (word-index based: converting each `sections[i].o` char offset to a token
// index, then slicing by token index) dropped a section whenever its
// boundary fell in an INTER-TOKEN GAP rather than exactly on a token start —
// e.g. a section opening with punctuation (an opening quote). `o` is only
// guaranteed to land on an inter-word boundary (never inside a token — see
// GreekLine.sections' doc comment, and pipeline/drama_pipeline/preflight.py's
// matching FATAL gate), NOT on a token start, so a token-index detour is the
// wrong tool. This version cuts `line.text` DIRECTLY by char offset instead:
// each piece covers exactly [secs[i].o, secs[i+1].o) (the last piece runs to
// line.text.length). `secs[0].o` is always 0 (stage1_greek._chapter_sections
// anchors the first section at the chapter's start), so concatenating every
// piece's text reproduces `line.text` byte-exactly — nothing dropped, nothing
// duplicated, regardless of what a boundary's leading character is. Each
// token is bucketed into whichever piece its own start offset falls in — a
// single left-to-right pass over the line's tokens (never revisited across
// pieces), safe because tokens never straddle a section boundary (the same
// "never inside a token" invariant). `lineRenderParts` (above) re-derives
// token positions from scratch per call via `text.indexOf(tok.t, ptr)`, so a
// piece's sliced `text`/`tokens` pair renders correctly on its own — the
// token-walk contract only needs to hold WITHIN each piece, not against the
// original line's global offsets.
export function splitGreekSections(lines: readonly GreekLine[]): SectionedGreekLine[] {
  const out: SectionedGreekLine[] = [];
  for (const line of lines) {
    const secs = line.sections;
    if (!secs || secs.length < 2) { out.push(line); continue; }
    // Every token's start offset in `line.text`, walked once (not per
    // piece) — the same left-to-right find-from-ptr walk lineRenderParts
    // performs, so a token's bucket always matches what the renderer sees.
    const starts: number[] = [];
    {
      let ptr = 0;
      for (const tok of line.tokens) {
        // Same locateToken walk lineRenderParts performs (sigla inside a word
        // included), so a token's bucket always matches what the renderer
        // sees. A token the walk can't place keeps its bucket at `ptr` — it
        // must stay in SOME piece here (the pieces partition line.tokens),
        // even though the renderer will decline to make it clickable.
        const at = locateToken(line.text, tok.t, ptr);
        const pos = at ? at.start : ptr;
        starts.push(pos);
        ptr = at ? at.end : pos + tok.t.length;
      }
    }
    let w = 0;
    for (let i = 0; i < secs.length; i += 1) {
      const from = secs[i].o;
      const to = i + 1 < secs.length ? secs[i + 1].o : line.text.length;
      const fromW = w;
      while (w < starts.length && starts[w] < to) w += 1;
      out.push({
        n: line.n,
        text: line.text.slice(from, to),
        tokens: line.tokens.slice(fromW, w),
        cont: i > 0,
        paraN: secs[i].n,
      });
    }
  }
  return out;
}

// ── Greek speaker sigla (P4 Lane C) ──────────────────────────────────────
// The editions print a speaker's FULL name at the first appearance (Murray:
// ΦΥΛΑΞ, ΚΛΥΤΑΙΜΗΣΤΡΑ; Coulon: ΞΑΝΘΙΑΣ, ΔΙΟΝΥΣΟΣ) and a short siglum after
// it (Χο., ΞΑ.), sometimes with an editorial supplement or a stage note
// attached ("<ΠΑΙΣ> (ἔσωθεν)", "ΕΥ. (ὡς Μενέλαος.)"). The Greek speaker
// gutter is sized for sigla (John's ruling, --pl-spk-w-greek), so a printed
// full name breaks across lines in it. `playSigla` derives ONE siglum per
// canonical speaker for the whole play, from the labels that play actually
// prints; the full printed label survives in the label's `title`/aria-label,
// and the English column is untouched.

// The width the gutter can hold, in characters — a label this short is used
// exactly as the edition prints it.
const SIGLUM_MAX = 4;

// A printed label reduced to its name: editorial angle brackets dropped
// (they mark a supplied label, not part of it) and any parenthesised stage
// note removed. "<ΠΑΙΣ> (ἔσωθεν)" → "ΠΑΙΣ"; "(ὡς Χορός.)" → "" (a bare note
// names nobody, so callers skip it).
function cleanSpeakerLabel(label: string): string {
  return label.replace(/\([^)]*\)/g, '').replace(/[<>]/g, '').replace(/\s+/g, ' ').trim();
}

// A trailing enumerator: the Greek numeral (Αʹ, Βʹ) or bare letter (α, β, Β)
// an edition hangs on a role it uses twice — ΗΜΙΧΟΡΙΟΝ Αʹ, ΠΑΝΔΟΚΕΥΤΡΙΑ Βʹ,
// ΑΓΓΕΛΟΣ Β. It is the WHOLE distinction between two such speakers, so an
// abbreviation keeps it.
const ENUMERATOR = /^\p{L}[ʹʹ′']?$/u;
const GLUED_ENUMERATOR = new RegExp(`(?:[ΑΒΓ][ʹʹ′']|[ΒΓ])$`, 'u');

// The first `n` letters of a label's first word, Greek title case, plus the
// abbreviation point, plus any trailing enumerator: ΦΥΛΑΞ → Φυ., ΑΙΣΧΥΛΟΣ
// (n=3) → Αισ., ΗΜΙΧΟΡΙΟΝ Αʹ → Ημ. Αʹ. A label with fewer letters than `n`
// yields all it has; one with none is returned unchanged.
function abbreviateLabel(label: string, n: number): string {
  const words = label.split(' ');
  let stem = words[0] ?? '';
  let glued = '';
  // The same enumerator GLUED to the name, with no space: the export prints
  // Phoenissae's second messenger ΑΓΓΕΛΟΣΒ and Helen's second servant
  // ΘΕΡΑΠΩΝΒ, so the two messengers shared one siglum (Grok P4CE finding 3).
  // Peeled only when there is no spaced enumerator and at least two letters
  // of the name survive. A BARE letter is peeled only when it is Β or Γ,
  // which no Greek word ends in; a bare final Α is the ordinary feminine
  // ending (ΚΑΣΣΑΝΔΡΑ, ΗΛΕΚΤΡΑ — 37 such labels in the corpus against two
  // real glued enumerators, both Β), so Α counts only with its numeral mark.
  if (words.length === 1) {
    const m = GLUED_ENUMERATOR.exec(stem);
    const kept = m ? stem.slice(0, m.index) : '';
    if (m && Array.from(kept).filter((c) => /\p{L}/u.test(c)).length >= 2) {
      glued = ` ${m[0]}`;
      stem = kept;
    }
  }
  const letters = Array.from(stem).filter((c) => /\p{L}/u.test(c)).slice(0, n).join('');
  if (!letters) return label;
  const last = words[words.length - 1];
  const tail = words.length > 1 && ENUMERATOR.test(last) ? ` ${last}` : glued;
  // Medial sigma, never final: the prefix is a word CUT SHORT, and Unicode's
  // default lowercasing would end it with ς (ΑΙΣΧΥΛΟΣ → Αις.), which reads as
  // a whole word. Abbreviations print σ.
  const rest = letters.slice(1).toLowerCase().replace(/ς/g, 'σ');
  return `${letters[0].toUpperCase()}${rest}.${tail}`;
}

// Displays whose sigla collide, grouped. Case-insensitive: "ΑΙ." and "Αι."
// would read as the same abbreviation on the page.
function siglaCollisions(sigla: Map<string, string>): string[][] {
  const byKey = new Map<string, string[]>();
  for (const [display, siglum] of sigla) {
    const key = siglum.toUpperCase();
    byKey.set(key, [...(byKey.get(key) ?? []), display]);
  }
  return [...byKey.values()].filter((g) => g.length > 1);
}

// One siglum per canonical speaker `display`, for a whole play. Rules (P4
// Lane C brief): (a) collect that speaker's printed labels, cleaned; (b) if
// the shortest is ≤ 4 characters, it IS the siglum, as printed (Χο., ΞΑ.);
// (c) otherwise abbreviate the fullest label to two letters (Φυ., Κλ.); (d)
// if two speakers collide, re-abbreviate both to three letters, then four,
// until distinct (Frogs: ΑΙΑΚΟΣ and ΑΙΣΧΥΛΟΣ both print "ΑΙ." → Αια., Αισ.).
// A pair still colliding at four letters falls back to each speaker's own
// shortest printed label, which the edition itself keeps distinct (Frogs'
// two innkeepers, "ΠΑ. Αʹ" / "ΠΑ. Βʹ") — two identical sigla in one play
// would be worse than one that overflows the gutter.
// Unattributed turns (the dialectic dash, `display` null) get no entry.
export function playSigla(
  events: readonly Pick<SpeakerEvent, 'label' | 'display'>[],
): Map<string, string> {
  const printed = new Map<string, string[]>();
  for (const e of events) {
    if (!e.display) continue;
    const label = cleanSpeakerLabel(e.label);
    if (!label) continue;
    const seen = printed.get(e.display) ?? [];
    if (!seen.includes(label)) seen.push(label);
    printed.set(e.display, seen);
  }
  const shortest = (labels: string[]) => labels.reduce((a, b) => (b.length < a.length ? b : a));
  const fullest = (labels: string[]) => labels.reduce((a, b) => (b.length > a.length ? b : a));

  const sigla = new Map<string, string>();
  for (const [display, labels] of printed) {
    const short = shortest(labels);
    // A joint label ("ΑΙ. κ. ΕΥ.", Aeschylus and Euripides speaking together
    // in Frogs) prints in full: the κ. is the point, and an abbreviation
    // would name only the first speaker (John, 2026-09-09). It stacks in
    // the gutter (Reader's .spk-long) rather than widening it.
    if (isJointSiglum(short)) { sigla.set(display, short); continue; }
    sigla.set(display, short.length <= SIGLUM_MAX ? short : abbreviateLabel(fullest(labels), 2));
  }
  for (let n = 3; n <= SIGLUM_MAX; n += 1) {
    const groups = siglaCollisions(sigla);
    if (!groups.length) break;
    for (const group of groups) {
      for (const display of group) {
        sigla.set(display, abbreviateLabel(fullest(printed.get(display)!), n));
      }
    }
  }
  // Four letters is the ceiling (the gutter is sized for sigla). A pair still
  // colliding there falls back to what the EDITION itself prints: each
  // speaker's shortest printed label when that is shorter than the
  // abbreviation (Hecuba's Polyxena and Polymestor, who never share a scene,
  // are BOTH "Πο." in Murray — printing them so is faithful, and the full name
  // rides in the label's title), and then, where those printed labels are
  // pairwise distinct, they win outright even if longer (Frogs' two
  // innkeepers, "ΠΑ. Αʹ" / "ΠΑ. Βʹ" — the numeral is the whole distinction).
  for (const group of siglaCollisions(sigla)) {
    for (const display of group) {
      const short = shortest(printed.get(display)!);
      if (short.length < sigla.get(display)!.length) sigla.set(display, short);
    }
  }
  for (const group of siglaCollisions(sigla)) {
    const alt = new Map(group.map((d) => [d, shortest(printed.get(d)!)] as const));
    const distinct = new Set([...alt.values()].map((s) => s.toUpperCase())).size === group.length;
    if (distinct) for (const display of group) sigla.set(display, alt.get(display)!);
  }
  // John, 2026-09-09: "none of this shouty all caps" — every siglum reads in
  // title case whatever the edition's own casing (Coulon's ΞΑ. → Ξα.); the
  // small-caps face does the rest. An enumerator tail (Αʹ) is left alone.
  for (const [display, s] of sigla) sigla.set(display, normalizeSiglumCase(s));
  return sigla;
}

/** Two sigla joined by κ. (καί): "ΑΙ. κ. ΕΥ.". */
export function isJointSiglum(label: string): boolean {
  return /\sκ\.?\s/.test(label);
}

/** First word in title case, medial sigma before the stop, tail untouched. */
export function normalizeSiglumCase(s: string): string {
  // A joint siglum title-cases each name and leaves the κ. as printed.
  if (isJointSiglum(s)) return s.split(' ').map((w) => (/^κ\.?$/.test(w) ? w : normalizeSiglumCase(w))).join(' ');
  const sp = s.indexOf(' ');
  const head = sp < 0 ? s : s.slice(0, sp);
  const tail = sp < 0 ? '' : s.slice(sp);
  if (head.length < 2) return s;
  const cased = head[0]!.toUpperCase() + head.slice(1).toLowerCase();
  return cased.replace(/ς(?=\.)/g, 'σ') + tail;
}

// ── P4 follow-ups from John's review of the built site (2026-09-09) ──────────

/** A printed English lead-in that the source set in capitals (Loeb / Gutenberg
 *  scans: THEOCLYMENUS, (A SECOND ELDER)) reads in title case; small caps of
 *  capitals is full caps and wraps mid-word. The words never change — only
 *  the casing the scan imposed. Mixed-case labels are returned untouched
 *  (John, REVIEW-CHECKLIST 2: each side keeps its printed label). */
export function leadInCase(display: string): string {
  const small = new Set(['of', 'the', 'and', 'a', 'an', 'to', 'in', 'for', 'or', 'at', 'on', 'by']);
  const letters = display.replace(/[^\p{L}]/gu, '');
  if (letters.length < 2 || letters !== letters.toUpperCase()) {
    // Mixed case stays as printed, except a capitalised small word mid-label
    // ("Leader Of The Chorus" -> "Leader of the Chorus"; John, 2026-09-09).
    let first = true;
    return display.replace(/\p{L}+/gu, (w) => {
      const out = !first && small.has(w.toLowerCase()) ? w.toLowerCase() : w;
      first = false;
      return out;
    });
  }
  let first = true;
  return display.replace(/\p{L}+/gu, (w) => {
    const lower = w.toLowerCase();
    const out = !first && small.has(lower) ? lower : lower[0]!.toUpperCase() + lower.slice(1);
    first = false;
    return out;
  });
}

/** The `n` of every play-line Greek line whose printed ref breaks the ascending
 *  sequence — a transposed line (Ag. 1290 printed before 1284) and the line
 *  that resumes after it (1284) — so the gutter can print its number where
 *  the edition does (John, 2026-09-09: "when an editor transposes a line,
 *  have the number by the transposed line"). Ranges ("40-41") advance the
 *  sequence to their end; suffixed refs ("47a") count as their integer; the
 *  `post N` lacuna refs and headings are skipped. */
export function playOutOfSequence(
  segments: { greek: { n: number; ref?: string; role?: string }[] }[],
): Set<number> {
  const out = new Set<number>();
  let prev: number | null = null;
  for (const seg of segments) {
    for (const line of seg.greek) {
      const ref = line.ref ?? '';
      if (line.role === 'lacuna' || line.role === 'heading') continue;
      const range = /^([0-9]+)-([0-9]+)$/.exec(ref);
      const plain = /^([0-9]+)([a-z]?)$/.exec(ref);
      let start: number; let end: number;
      if (range) { start = Number(range[1]); end = Number(range[2]); }
      else if (plain) { start = Number(plain[1]); end = start; }
      else continue;
      if (prev != null && start !== prev && start !== prev + 1) out.add(line.n);
      prev = end;
    }
  }
  return out;
}

/** Lines the edition prints out of numerical order (Ag. 1290 before 1284):
 * the lines NOT on a longest non-decreasing run of printed numbers, so a
 * single moved line is flagged and the lines around it are not, and a plain
 * gap in the numbering (7 then 10) flags nothing. playOutOfSequence, which
 * decides which gutter numbers to print, keeps its looser "number changed
 * unexpectedly" rule; this set drives the editor note. */
export function playTransposed(
  segments: { greek: { n: number; ref?: string; role?: string }[] }[],
): Set<number> {
  const seq: { n: number; v: number }[] = [];
  const seen = new Set<string>();
  for (const seg of segments) {
    for (const line of seg.greek) {
      if (line.role === 'lacuna' || line.role === 'heading') continue;
      const m = /^([0-9]+)/.exec(line.ref ?? '');
      if (!m) continue;
      // A doublet's later copy is playRepeatedRefs' business, not a transposition.
      if (seen.has(line.ref!)) continue;
      seen.add(line.ref!);
      seq.push({ n: line.n, v: Number(m[1]) });
    }
  }
  // Longest non-decreasing subsequence, O(n log n) with parent links.
  const tails: number[] = []; const tailIdx: number[] = []; const parent = new Array<number>(seq.length).fill(-1);
  for (let i = 0; i < seq.length; i++) {
    const v = seq[i].v;
    let lo = 0, hi = tails.length;
    while (lo < hi) { const mid = (lo + hi) >> 1; if (tails[mid] <= v) lo = mid + 1; else hi = mid; }
    tails[lo] = v; tailIdx[lo] = i; parent[i] = lo > 0 ? tailIdx[lo - 1] : -1;
  }
  const keep = new Set<number>();
  for (let i = tails.length ? tailIdx[tails.length - 1] : -1; i >= 0; i = parent[i]) keep.add(i);
  const out = new Set<number>();
  seq.forEach((x, i) => { if (!keep.has(i)) out.add(x.n); });
  return out;
}

/** Lines whose printed ref the edition gives to more than one line (Septem's
 * 803 doublet, Helen's two lacunae at 1226): every line carrying a duplicated
 * plain or range ref, so the gutter can mark each copy. Lacunae and headings
 * are skipped, as in playOutOfSequence. (John, 2026-09-09: repeated and
 * transposed numbers are clickable, with a note that the editor did it.) */
export function playRepeatedRefs(
  segments: { greek: { n: number; ref?: string; role?: string }[] }[],
): Set<number> {
  const byRef = new Map<string, number[]>();
  for (const seg of segments) {
    for (const line of seg.greek) {
      if (line.role === 'lacuna' || line.role === 'heading') continue;
      const ref = line.ref ?? '';
      if (!/^[0-9]+(?:[a-z]|-[0-9]+)?$/.test(ref)) continue;
      const ns = byRef.get(ref);
      if (ns) ns.push(line.n); else byRef.set(ref, [line.n]);
    }
  }
  const out = new Set<number>();
  for (const ns of byRef.values()) if (ns.length > 1) for (const n of ns) out.add(n);
  return out;
}

/** The English speaker gutter's width for a play, from its longest name
 * (SAUSAGE-SELLER overhung the 7.5rem default into the text; John,
 * 2026-09-09). Small caps in Alegreya Sans SC run ~0.56rem a character at
 * the lead-in size; 1rem of air; never narrower than the default. */
export function playEnglishGutterWidth(names: Iterable<string>): string {
  let longest = 0;
  // A joint or descriptive name ("Sausage-seller and Paphlagonian", "Ghost
  // of Clytaemestra") must not widen the gutter for the whole play: past 16
  // characters a lead-in takes its own line above the text instead
  // (Reader.svelte longLabel / .spk-long).
  for (const n of names) if (n.length <= 16) longest = Math.max(longest, n.length);
  return `${Math.max(7.5, longest * 0.56 + 1.0).toFixed(2)}rem`;
}

/** The Greek speaker gutter's width for a play, from its longest siglum
 *  (Helen's Θεοκ. / Θεον. need more than Χο.): never below the 3.4rem
 *  design width, about 0.62rem per glyph plus room for the gap. */
export function playGreekGutterWidth(sigla: Map<string, string>): string {
  let longest = 0;
  // A joint siglum stacks inside the gutter (.spk-long) instead of sizing it.
  for (const s of sigla.values()) if (!isJointSiglum(s)) longest = Math.max(longest, s.length);
  const rem = Math.max(3.4, longest * 0.62 + 0.9);
  return `${rem.toFixed(2)}rem`;
}

/** Facing-page flow for play-line rows (John, 2026-09-09: the Greek column
 *  must never open a gap for a long English paragraph). Each row gives the
 *  Greek cell's top and height and the English content's natural height, all
 *  in px relative to the grid. The English of row k starts level with its
 *  Greek (push 0) unless the English above it runs past that point, in which
 *  case it is pushed down to follow, `gap` px after it; the grid's own bottom
 *  padding grows by whatever the last English overruns the last Greek. */
export function englishFlow(
  rows: readonly { greekTop: number; greekHeight: number; englishHeight: number }[],
  gap: number,
): { pushes: number[]; paddingBottom: number } {
  const pushes: number[] = [];
  let englishEnd = -Infinity;
  let greekEnd = 0;
  for (const r of rows) {
    // Pushed only when the English above actually runs past this row's Greek
    // (more than a pixel), and only then by the gap as well: a one-line speech
    // is as tall as its one Greek line, and adding the gap to every such row
    // walked stichomythia down the page 8px a turn (John, 2026-09-11, Birds 48-53).
    const over = englishEnd - r.greekTop;
    const push = over > 1 ? over + gap : 0;
    pushes.push(r.englishHeight > 0 ? push : 0);
    if (r.englishHeight > 0) englishEnd = r.greekTop + push + r.englishHeight;
    greekEnd = Math.max(greekEnd, r.greekTop + r.greekHeight);
  }
  return { pushes, paddingBottom: Math.max(0, englishEnd - greekEnd) };
}

// Arrowsmith's stage directions (John, 2026-09-12: "have a break in the
// Greek where the stage directions are so english stays aligned with its
// Greek"). One inside a speech sits in the English text on a line of its
// own, `_..._`; one between speeches rides the piece as `directionsBefore`.
const STAGE_DIRECTION = /^_([^_\n]+)_$/gm;

/** A direction inside a speech: its own line, in italics. */
export function markStageDirections(html: string): string {
  return html.replace(/\n?^_([^_\n]+)_$\n?/gm, '<span class="stage-dir">$1</span>');
}

/** The rows a segment's between-speech directions take before it: one per
 *  direction, one cell per English column on screen (null where that
 *  column's translation has none), and an empty Greek cell. None in the
 *  Greek-only view, or when no column on screen carries a direction. */
export function directionRows(
  columns: readonly (readonly string[] | undefined)[],
  view: 'both' | 'greek' | 'english',
): (string | null)[][] {
  if (view === 'greek') return [];
  const n = Math.max(0, ...columns.map((c) => c?.length ?? 0));
  return Array.from({ length: n }, (_, i) => columns.map((c) => c?.[i] ?? null));
}

/** A direction before a later speech of a segment split into play rows
 *  (Clouds 1:866; Codex review of 7a9a16d): the rows are cut where that
 *  speech's row starts, and the direction becomes a run of its own between
 *  the two, rendered as a row with an empty Greek cell, so the speech after
 *  it starts level with its Greek. The block that gave its directions to a
 *  row no longer carries them. A speech that shares a row with the one
 *  before it keeps its directions and prints them inline. None in the
 *  Greek-only view. */
export function splitAtDirections<R extends { blocks: EnglishTurnBlock[] }>(
  rows: readonly R[],
  view: 'both' | 'greek' | 'english',
): ({ rows: R[] } | { directions: string[] })[] {
  const out: ({ rows: R[] } | { directions: string[] })[] = [];
  let run: R[] = [];
  for (const row of rows) {
    const first = row.blocks[0];
    if (view !== 'greek' && first && first.turnIndex >= 0 && first.directionsBefore?.length) {
      if (run.length) out.push({ rows: run });
      out.push({ directions: first.directionsBefore });
      const { directionsBefore: _moved, ...rest } = first;
      run = [{ ...row, blocks: [rest, ...row.blocks.slice(1)] }];
    } else {
      run.push(row);
    }
  }
  if (run.length) out.push({ rows: run });
  return out;
}

/** Where a line-keyed translation's English is cut into rows (John,
 *  2026-09-10). The prose translations (Smyth, Jebb, Coleridge) mark a Greek
 *  line only every five lines or so, and a marker often falls mid-sentence
 *  ("Where does Hector ‖ take his rest"); cutting there broke the sentence
 *  across a gap. Instead: cut only where a sentence or a speech begins, and
 *  give each such start the Greek line it most likely renders, interpolated
 *  by its place in the text between the markers either side (the last marker
 *  runs to `endN`, the line after the segment's last). A marker that falls
 *  exactly on a sentence start keeps its own line; one mid-sentence cuts
 *  nothing but still steers the estimate. For now: a real line-by-line
 *  alignment would replace this.
 *  John, 2026-09-12 (the Agamemnon audit): given the segment's Greek lines,
 *  an interpolated start moves to the nearest Greek line that begins a
 *  sentence -- the line after a full stop (. ; · !), or a line with such a
 *  stop inside it, counted from halfway through -- when one lies within
 *  1.5 lines. And a one-word sentence ("Hallo!") is no piece of its own: it
 *  stays with the piece before it. */
export function sentenceTicks(
  text: string,
  ticks: readonly { n: number; offset: number }[],
  turnOffsets: readonly number[],
  endN: number,
  greek: readonly { n: number; text: string }[] = [],
): { n: number; offset: number }[] {
  if (!ticks.length) return [];
  const skipSpace = (o: number) => { while (o < text.length && /\s/.test(text[o]!)) o += 1; return o; };
  const anchors = [...ticks]
    .map((t) => ({ n: t.n, off: skipSpace(t.offset) }))
    .sort((a, b) => a.off - b.off);
  const last = anchors[anchors.length - 1]!;
  const span = endN > last.n ? [...anchors, { n: endN, off: text.length }] : anchors;
  // Where Greek sentences begin: at a line after a full stop, or partway
  // into a line with one inside it. On Agamemnon's 473 hand-checked starts
  // a window of 1.0, 1.5, 2.0 or 2.5 lines gives 88.3%, 89.6%, 89.6% and
  // 88.9% exact; 1.5 has the fewest pieces two lines out.
  const SNAP = 1.5;
  // Full stop, question mark (; and U+037E), raised dot (U+00B7, U+0387), !.
  const ENDS = /[.;;··!]\s*[\]’'"†]*\s*$/u;
  const breaks = greek.flatMap((g, i) => {
    if (i > 0 && ENDS.test(greek[i - 1]!.text)) return [{ n: g.n, at: g.n }];
    if (/[.;;··!]\s*\S/u.test(g.text.replace(ENDS, ''))) return [{ n: g.n, at: g.n + 0.5 }];
    return [];
  });
  // A speech starts where its turn says, whitespace and all: sliceBlocks trims
  // it, and a cut moved past the turn would leave the lead-in on the row above.
  const speechStarts = new Set<number>([skipSpace(0), ...turnOffsets.filter((o) => o > 0 && o < text.length)]);
  const starts = new Set<number>(speechStarts);
  // A sentence ends at . ! ? or … -- never the stop after a lone capital
  // initial ("H. W. Wilson") or a title ("Mr.", "St.") -- then any closing
  // quote or bracket, and space or a dash ("stopped.—She"); it starts with a
  // capital, a digit, or a Greek letter (Grok review of 1219ece).
  const END = /(?<!(?:^|[\s(])(?:\p{Lu}|Mr|Mrs|Dr|St|Mt))[.!?…]["'’”»)\]]*(?:\s+|[—–]\s*)(?=["'‘“«(\[]?(?:\p{Lu}|\p{Nd}|\p{Script=Greek}))/gu;
  // Never cut inside a stage direction (John, 2026-09-12).
  const inside = [...text.matchAll(STAGE_DIRECTION)].map((m) => [m.index!, m.index! + m[0].length]);
  for (const m of text.matchAll(END)) {
    const s = m.index! + m[0].length;
    if (!inside.some(([a, b]) => a! < s && s < b!)) starts.add(s);
  }
  const out: { n: number; offset: number }[] = [];
  const sorted = [...starts].sort((a, b) => a - b);
  sorted.forEach((s, i) => {
    const exact = anchors.find((a) => a.off === s);
    if (exact) { out.push({ n: exact.n, offset: s }); return; }
    // One word to the next start: it stays with the piece before it.
    const piece = text.slice(s, sorted[i + 1] ?? text.length).replace(/\[\^[^\]]*\]/g, '');
    const words = piece.match(/[\p{L}\p{N}][\p{L}\p{N}\p{M}’',-]*/gu) ?? [];
    if (!speechStarts.has(s) && words.length < 2) return;
    const k = span.findIndex((a, j) => a.off <= s && (span[j + 1]?.off ?? Infinity) > s);
    const a = span[k];
    const b = span[k + 1];
    if (!a || !b || b.off === a.off) return; // before the first marker, or past the text
    // Markers that run backwards (a transposed line printed early) give no
    // span to interpolate across: hold the earlier marker's line. Never past
    // the segment's last line (endN is the line after it).
    let n = a.n;
    if (b.n >= a.n) {
      const x = a.n + ((s - a.off) / (b.off - a.off)) * (b.n - a.n);
      const top = b.n === endN ? endN - 1 : b.n;
      const near = breaks
        .filter((g) => Math.abs(g.at - x) <= SNAP && g.n >= a.n && g.n <= top)
        .sort((p, q) => Math.abs(p.at - x) - Math.abs(q.at - x))[0];
      n = near ? near.n : Math.round(x);
    }
    out.push({ n: Math.min(n, Math.max(a.n, endN - 1)), offset: s });
  });
  return out;
}

