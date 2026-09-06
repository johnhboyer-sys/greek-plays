// WordPopup rendering — byte-shape regression lock for the common (single
// dictionary entry) Greek case, plus the homonym-fan-out ambiguity labeling
// added for Wave 2 Batch 1b (governing principle: THE READER MUST NEVER BE
// SHOWN A WRONG GLOSS AS IF CERTAIN — see stage5_lsj.py's homonym fan-out
// fix and app/src/lib/lemma-instance.ts's citation-pill fix, both landed
// alongside this). This locks in the shape entriesFor/lemmaRef/displayLemma
// (WordPopup.svelte) render, independent of the a11y test (which only
// checks for axe violations, not content).
import { cleanup, fireEvent, render, screen } from '@testing-library/svelte';
import { tick } from 'svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import WordPopup from '../components/WordPopup.svelte';

vi.mock('../lib/data', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/data')>();
  return {
    ...actual,
    fetchLemmata: vi.fn(async () => ({
      logos: { slug: 'logos', head: 'λόγος', count: 42 },
    })),
    lookupWord: vi.fn(),
  };
});

// 'de-officiis' stands in for a Latin work (the drama-corpus registry carries
// none), matching the fan-out test below, which mirrors the real Latin
// stage5_lsj "edo1"/"edo2" homonym case (HANDOFF-LSJ §1, aristotle-reader).
vi.mock('../lib/works', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/works')>();
  return {
    ...actual,
    getWork: (id: string) =>
      id === 'de-officiis'
        ? ({ language: 'lat' } as ReturnType<typeof actual.getWork>)
        : actual.getWork(id),
  };
});

// Grammata's T8 widget is the ONE renderer of a dictionary entry (CLAUDE.md,
// "Dictionary"); no test may reach the real network module for it — the load
// is mocked here and `mockLookup` stands in for the widget's own `lookup`.
const { mockLookup } = vi.hoisted(() => ({ mockLookup: vi.fn(async () => undefined) }));
vi.mock('../lib/grammata', () => ({
  loadGrammataLookup: vi.fn(async () => mockLookup),
}));

import { lookupWord } from '../lib/data';

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe('WordPopup — single dictionary entry (the common case)', () => {
  it('renders the Greek lemma, gloss, parse, dictionary entry, and the lemma-page link — no ambiguity note', async () => {
    vi.mocked(lookupWord).mockResolvedValue({
      analyses: [{ lemma: 'lo/gos', gloss: 'word, account', parse: 'noun nominative singular', lsj: ['logos'] }],
    });

    const { container } = render(WordPopup, {
      props: { work: 'EN', token: { t: 'λόγος', k: 'logos' }, anchor: { x: 0, y: 0 }, onClose: vi.fn() },
    });

    expect(await screen.findByText('word, account')).toBeTruthy();
    expect(screen.getByText('noun nominative singular')).toBeTruthy();
    expect(container.querySelector('.lemma')?.textContent).toBe('λόγος');
    // The dictionary entry itself is Grammata's T8 widget (mounted, not open
    // by default) — the site renders no local LSJ entry HTML.
    expect(container.querySelector('.grammata-mount')).toBeTruthy();
    expect(container.querySelector('.lsj-entry')).toBeNull();
    expect(container.querySelector('.lsj-ambiguous-note')).toBeNull();
    // Unambiguous (1 key) — the "Appears Nx" concordance link IS shown.
    const link = container.querySelector('.lemma-link');
    expect(link?.textContent).toContain('Appears 42');
    expect(link?.getAttribute('href')).toBe('/lemma/grc/entry/?w=logos');
  });
});

describe('WordPopup — homonym fan-out (multi-entry) ambiguity', () => {
  it('labels a multi-candidate lemma as an explicit group and suppresses the lemma-page link', async () => {
    // Mirrors stage5_lsj's real "est" -> edo#1 outcome (edo1 "to eat" +
    // edo2 "to publish" survive as a genuine residual ambiguity after
    // POS-filtering drops edo3).
    vi.mocked(lookupWord).mockResolvedValue({
      analyses: [{ lemma: 'edo#1', gloss: '', parse: 'pres ind act 3rd sg', lsj: ['e^do1', 'e_do2'] }],
    });

    const { container } = render(WordPopup, {
      props: { work: 'de-officiis', token: { t: 'est', k: 'est' }, anchor: { x: 0, y: 0 }, onClose: vi.fn() },
    });

    await screen.findAllByText('pres ind act 3rd sg');
    // One card per dictionary entry, each with its own Grammata mount; no
    // local LSJ entry HTML.
    expect(container.querySelectorAll('.analysis-card')).toHaveLength(2);
    expect(container.querySelectorAll('.grammata-mount')).toHaveLength(2);
    expect(container.querySelector('.lsj-entry')).toBeNull();
    // Never a silent, possibly-wrong pick of one: no lemma-page link when ambiguous.
    expect(container.querySelector('.lemma-link')).toBeNull();
    // Both candidates share the headword spelling "edo" (homographs by
    // definition), so the card shows that common head -- never the raw
    // Diogenes-internal "edo#1" marker.
    const heads = [...container.querySelectorAll('.lemma')].map((el) => el.textContent);
    expect(heads).toEqual(['edo', 'edo']);
  });
});

// Regression tests for the word-to-word jump fix ported from plato-reader
// (2026-07-29): with the panel open, clicking another word must swap the
// analysis in place — the old full-page backdrop swallowed that click and
// forced close/reopen with two page snaps, and the once-only lookup left
// stale data on swap.
describe('WordPopup — word-to-word jump (backdrop removal + reactive lookup)', () => {
  const swapMock = async (_work: string, k: string) => ({
    analyses: [
      k === 'logos'
        ? { lemma: 'lo/gos', gloss: 'word, account', parse: 'noun nom sg', lsj: [] }
        : { lemma: 'a)reth/', gloss: 'goodness, excellence', parse: 'noun nom sg', lsj: [] },
    ],
    lsj: [],
  });

  it('re-runs the lookup when the token changes (word-to-word jump)', async () => {
    vi.mocked(lookupWord).mockImplementation(swapMock as never);
    const { rerender } = render(WordPopup, {
      props: { work: 'EN', token: { t: 'λόγος', k: 'logos' }, anchor: { x: 0, y: 0 }, onClose: vi.fn() },
    });
    await screen.findByText('word, account');

    await rerender({ token: { t: 'ἀρετή', k: 'areth' } });
    await screen.findByText('goodness, excellence');
    expect(lookupWord).toHaveBeenCalledTimes(2);
    expect(lookupWord).toHaveBeenLastCalledWith('EN', 'areth');
  });

  it('shows the latest word when responses arrive out of order (request-id guard)', async () => {
    // First request resolves LAST — without the guard its stale payload
    // would overwrite the second word's analysis.
    let resolveFirst!: (v: Awaited<ReturnType<typeof swapMock>>) => void;
    vi.mocked(lookupWord).mockImplementation((async (_w: string, k: string) => {
      if (k === 'logos') return new Promise((res) => { resolveFirst = res; });
      return swapMock(_w, k);
    }) as never);

    const { rerender } = render(WordPopup, {
      props: { work: 'EN', token: { t: 'λόγος', k: 'logos' }, anchor: { x: 0, y: 0 }, onClose: vi.fn() },
    });
    await rerender({ token: { t: 'ἀρετή', k: 'areth' } });
    await screen.findByText('goodness, excellence');

    resolveFirst(await swapMock('EN', 'logos'));
    await new Promise((r) => setTimeout(r, 0));
    expect(screen.queryByText('word, account')).toBeNull();
    expect(screen.getByText('goodness, excellence')).toBeTruthy();
  });

  it('closes on click outside, but not on the panel or on a token', async () => {
    vi.mocked(lookupWord).mockImplementation(swapMock as never);
    const tok = document.createElement('span');
    tok.className = 'tok';
    document.body.appendChild(tok);

    const onClose = vi.fn();
    render(WordPopup, {
      props: { work: 'EN', token: { t: 'λόγος', k: 'logos' }, anchor: { x: 0, y: 0 }, onClose },
    });
    await screen.findByText('word, account');

    // On a token: the token's own handler swaps the word — no close.
    tok.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    await tick();
    expect(onClose).not.toHaveBeenCalled();

    // Inside the panel: no close.
    document.querySelector('.word-sidebar')!
      .dispatchEvent(new MouseEvent('click', { bubbles: true }));
    await tick();
    expect(onClose).not.toHaveBeenCalled();

    // Anywhere else: close.
    document.body.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    await tick();
    expect(onClose).toHaveBeenCalledTimes(1);

    tok.remove();
  });

  it('closes even when the outside click stops propagation (footnote marker)', async () => {
    // Reader's fn-marker / Bekker-info / print-menu handlers stopPropagation();
    // the close listener runs in the capture phase so it still sees the click
    // (John's ruling 2026-07-29: a footnote click closes the word panel).
    vi.mocked(lookupWord).mockImplementation(swapMock as never);
    const marker = document.createElement('button');
    marker.className = 'fn-marker';
    marker.addEventListener('click', (e) => e.stopPropagation());
    document.body.appendChild(marker);

    const onClose = vi.fn();
    render(WordPopup, {
      props: { work: 'EN', token: { t: 'λόγος', k: 'logos' }, anchor: { x: 0, y: 0 }, onClose },
    });
    await screen.findByText('word, account');

    marker.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    await tick();
    expect(onClose).toHaveBeenCalledTimes(1);

    marker.remove();
  });

  it('does NOT close on a bare pointerdown (touch pan / selection drag / right-click)', async () => {
    // A pan or drag produces pointerdown with no click; closing there would
    // dismiss the panel the moment a touch scroll starts (Sol review catch).
    vi.mocked(lookupWord).mockImplementation(swapMock as never);
    const onClose = vi.fn();
    render(WordPopup, {
      props: { work: 'EN', token: { t: 'λόγος', k: 'logos' }, anchor: { x: 0, y: 0 }, onClose },
    });
    await screen.findByText('word, account');

    document.body.dispatchEvent(new Event('pointerdown', { bubbles: true }));
    document.body.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, button: 2 }));
    await tick();
    expect(onClose).not.toHaveBeenCalled();
  });

  it('handles keyed→unkeyed→keyed swaps without stale data', async () => {
    vi.mocked(lookupWord).mockImplementation(swapMock as never);
    const { rerender } = render(WordPopup, {
      props: { work: 'EN', token: { t: 'λόγος', k: 'logos' }, anchor: { x: 0, y: 0 }, onClose: vi.fn() },
    });
    await screen.findByText('word, account');

    // Unkeyed token (defense-in-depth branch): clears, no lookup, no stale gloss.
    await rerender({ token: { t: '⟦Diels⟧' } });
    await screen.findByText('No analysis found for this form.');
    expect(screen.queryByText('word, account')).toBeNull();
    expect(lookupWord).toHaveBeenCalledTimes(1);

    // Back to a keyed token: looks up fresh.
    await rerender({ token: { t: 'ἀρετή', k: 'areth' } });
    await screen.findByText('goodness, excellence');
    expect(lookupWord).toHaveBeenCalledTimes(2);
  });

  it('renders no click-blocking backdrop', async () => {
    vi.mocked(lookupWord).mockImplementation(swapMock as never);
    render(WordPopup, {
      props: { work: 'EN', token: { t: 'λόγος', k: 'logos' }, anchor: { x: 0, y: 0 }, onClose: vi.fn() },
    });
    await screen.findByText('word, account');
    expect(document.querySelector('.popup-backdrop')).toBeNull();
  });
});

describe('WordPopup — Grammata T8 mount', () => {
  it('mounts a container per card, closed by default, with no local dictionary HTML', async () => {
    vi.mocked(lookupWord).mockResolvedValue({
      analyses: [{ lemma: 'lo/gos', gloss: 'word, account', parse: 'noun nominative singular', lsj: ['logos'] }],
    });

    const { container } = render(WordPopup, {
      props: { work: 'EN', token: { t: 'λόγος', k: 'logos' }, anchor: { x: 0, y: 0 }, onClose: vi.fn() },
    });

    await screen.findByText('word, account');
    expect(container.querySelector('.grammata-mount')).toBeTruthy();
    expect(container.querySelector('.card-entry')?.hasAttribute('hidden')).toBe(true);
    expect(container.querySelector('.lsj-entry')).toBeNull();
    // The lookup only runs once a card is opened.
    expect(mockLookup).not.toHaveBeenCalled();
  });

  it('opens the card and calls Grammata with the entry key, never a surface form', async () => {
    vi.mocked(lookupWord).mockResolvedValue({
      analyses: [{ lemma: 'lo/gos', gloss: 'word, account', parse: 'noun nominative singular', lsj: ['logos'] }],
    });

    const { container } = render(WordPopup, {
      props: { work: 'EN', token: { t: 'λόγος', k: 'logos' }, anchor: { x: 0, y: 0 }, onClose: vi.fn() },
    });

    await screen.findByText('word, account');
    await fireEvent.click(container.querySelector('.card-face') as HTMLElement);

    expect(container.querySelector('.card-entry')?.hasAttribute('hidden')).toBe(false);
    expect(mockLookup).toHaveBeenCalledTimes(1);
    expect(mockLookup).toHaveBeenCalledWith('', expect.any(HTMLElement), { lang: 'grc', key: 'logos' });
  });
});

describe('WordPopup — all-caps accent fallback', () => {
  it('quietly labels the complete supplied-accent reading group once', async () => {
    vi.mocked(lookupWord).mockResolvedValue({
      analyses: [
        { lemma: 'a)rxh/', gloss: 'rule', parse: 'genitive plural', lsj: [], foldedAccent: true },
        { lemma: 'a)/rxwn', gloss: 'ruler', parse: 'nominative singular', lsj: [], foldedAccent: true },
      ],
      lsj: [],
    });

    render(WordPopup, {
      props: { work: 'EN', token: { t: 'ΑΡΧΩΝ', k: 'arxwn' }, anchor: { x: 0, y: 0 }, onClose: vi.fn() },
    });

    expect(await screen.findByText('All-capitals form — accents supplied; readings listed are all matches.')).toBeTruthy();
    expect(screen.getAllByText(/rule|ruler/)).toHaveLength(2);
  });
});
