import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import BekkerJump from '../components/BekkerJump.svelte';

// BekkerJump is scheme-aware (shared/lib/citation.ts): its placeholder, label,
// and parse behavior all come from the work's citation scheme, not a
// hardcoded Bekker grammar. No stephanus work is in the registry yet (Plato
// works land in a later phase), so a fake work id + a mocked getWork stands in
// for one here.
// 'DottedWork' is a book-section-scheme fixture (12 books, mirroring the real
// Marcus Aurelius registry entry) for the out-of-range-book regression tests
// below — bookFromColumn derives its book straight from the dotted column, so
// no fetchColumns/resolveBekker lookup is involved for it. 'EN' is not a real
// registry id either (no bekker-scheme work happens to be registered under
// it), so it needs its own minimal fixture too — the out-of-range check below
// (BekkerJump.svelte's go()) reads getWork(work).books, which a truly
// unregistered id can't supply. 'VerseWork' is a verse-line-scheme fixture
// (mirroring Lucretius' DRN registry entry) for the lacuna-range acceptance
// tests below — its citation.scheme is 'verse-line', the only scheme whose
// parseLocation can set `isRange`. 'DkWork'/'DkWork2' are dk-scheme fixtures
// (the zero-works registry, drama fork P0, carries no real dk work) —
// workByDkCitation/workByDkChapterNoSeries/workPath are overridden directly
// (not just getWork) so citation.ts's parseDkFullCitation, which resolves
// against those named exports rather than this file's getWork mock, finds
// them too.
vi.mock('../lib/works', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/works')>();
  const DK_WORKS: Record<string, ReturnType<typeof actual.getWork>> = {
    DkWork: { id: 'DkWork', title: 'Test Fragments', books: 1, citation: { scheme: 'dk', dkChapter: 22, series: 'B' } } as ReturnType<typeof actual.getWork>,
    DkWork2: { id: 'DkWork2', title: 'Test Fragments 2', books: 1, citation: { scheme: 'dk', dkChapter: 68, series: 'B' } } as ReturnType<typeof actual.getWork>,
  };
  return {
    ...actual,
    getWork: (id: string) =>
      id === 'StephWork'
        ? ({ id: 'StephWork', title: 'Test Dialogue', citation: { scheme: 'stephanus' } } as ReturnType<typeof actual.getWork>)
        : id === 'DottedWork'
        ? ({ id: 'DottedWork', title: 'Test Notebook', books: 12, citation: { scheme: 'book-section' } } as ReturnType<typeof actual.getWork>)
        : id === 'VerseWork'
        ? ({ id: 'VerseWork', title: 'Test Poem', books: 6, citation: { scheme: 'verse-line' } } as ReturnType<typeof actual.getWork>)
        : id === 'EN'
        ? ({ id: 'EN', title: 'Test Treatise', books: 1 } as ReturnType<typeof actual.getWork>)
        : id in DK_WORKS
        ? DK_WORKS[id]
        : actual.getWork(id),
    workByDkCitation: (dkChapter: number, series: 'A' | 'B') =>
      Object.values(DK_WORKS).find((w) => w?.citation?.dkChapter === dkChapter && w.citation.series === series),
    workByDkChapterNoSeries: () => undefined,
    workPath: (workId: string, book = 1) =>
      workId in DK_WORKS ? `/dk-author/${workId.toLowerCase()}/book/${book}` : actual.workPath(workId, book),
  };
});

vi.mock('../lib/data', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/data')>();
  return {
    ...actual,
    fetchColumns: vi.fn(async (work: string) =>
      work === 'StephWork'
        ? { '34b': [{ book: 1, lo: 1, hi: 20 }] }
        : work === 'VerseWork'
        // Only the declared-lacuna column exists in the index — a
        // syntactically valid but undeclared range ("1.1-2") must be
        // absent here, exactly as it would be from the real corpus.
        ? { '1.1094-1101': [{ book: 1, lo: 1094, hi: 1101 }] }
        // 'DkWork' is the dk-scheme fixture above (chapter 22, series 'B')
        // used below for the DK full-citation-form jump tests ("DK 22 B30").
        : work === 'DkWork'
        ? { B30: [{ book: 1, lo: 1, hi: 1 }] }
        : { '1097a': [{ book: 1, lo: 1, hi: 20 }] },
    ),
  };
});

describe('BekkerJump — scheme-aware citation entry', () => {
  it('shows the Bekker placeholder/label for a bekker work (default scheme)', async () => {
    render(BekkerJump, { props: { work: 'EN', inputId: 'bk-en' } });
    await fireEvent.click(screen.getByRole('button', { name: /Go to a Bekker citation/ }));
    expect(screen.getByPlaceholderText('e.g. 1097a15')).toBeInTheDocument();
    expect(screen.getByLabelText('Bekker citation')).toBeInTheDocument();
  });

  it('shows the Stephanus placeholder/label and accepts a bare column, calling onJump with a null line', async () => {
    const onJump = vi.fn();
    render(BekkerJump, { props: { work: 'StephWork', inputId: 'bk-steph', onJump } });
    await fireEvent.click(screen.getByRole('button', { name: /Go to a Stephanus page/ }));
    expect(screen.getByPlaceholderText('e.g. 34b')).toBeInTheDocument();

    const input = screen.getByLabelText('Jump to a Stephanus page');
    await fireEvent.input(input, { target: { value: '34b' } });
    await fireEvent.click(screen.getByRole('button', { name: 'Go' }));

    expect(onJump).toHaveBeenCalledWith(1, '34b', null);
  });

  it('rejects a trailing-digits citation for a lineless (stephanus) scheme', async () => {
    const onJump = vi.fn();
    render(BekkerJump, { props: { work: 'StephWork', inputId: 'bk-steph-bad', onJump } });
    await fireEvent.click(screen.getByRole('button', { name: /Go to a Stephanus page/ }));

    const input = screen.getByLabelText('Jump to a Stephanus page');
    await fireEvent.input(input, { target: { value: '34b12' } });
    await fireEvent.click(screen.getByRole('button', { name: 'Go' }));

    expect(onJump).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toHaveTextContent('Stephanus page');
  });

  it('still resolves a full bekker citation (column + line) via onJump', async () => {
    const onJump = vi.fn();
    render(BekkerJump, { props: { work: 'EN', inputId: 'bk-en-full', onJump } });
    await fireEvent.click(screen.getByRole('button', { name: /Go to a Bekker citation/ }));

    const input = screen.getByLabelText('Jump to a Bekker citation');
    await fireEvent.input(input, { target: { value: '1097a15' } });
    await fireEvent.click(screen.getByRole('button', { name: 'Go' }));

    expect(onJump).toHaveBeenCalledWith(1, '1097a', 15);
  });

  // Regression test for the adversarial-review finding: bookFromColumn only
  // validates a dotted column's SYNTAX ("99.99" parses fine), not corpus
  // membership. 'DottedWork' has 12 books, so book 99 is out of range — the
  // jump box must show the existing not-found message rather than navigating
  // to a book that workPath would silently clamp to (book 12) with an
  // unresolvable ?loc=99.99.
  it('shows the not-found error for a book-section citation whose book is out of range', async () => {
    const onJump = vi.fn();
    render(BekkerJump, { props: { work: 'DottedWork', inputId: 'bk-dotted-oob', onJump } });
    await fireEvent.click(screen.getByRole('button', { name: /Go to a book and section/ }));

    const input = screen.getByLabelText('Jump to a book and section');
    await fireEvent.input(input, { target: { value: '99.99' } });
    await fireEvent.click(screen.getByRole('button', { name: 'Go' }));

    expect(onJump).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toHaveTextContent('99.99 is not in the Test Notebook');
  });

  // A citation in the last real book (12 of 12) still resolves — the
  // out-of-range guard must not reject an in-range book at the boundary.
  it('still resolves a book-section citation in the last real book', async () => {
    const onJump = vi.fn();
    render(BekkerJump, { props: { work: 'DottedWork', inputId: 'bk-dotted-last', onJump } });
    await fireEvent.click(screen.getByRole('button', { name: /Go to a book and section/ }));

    const input = screen.getByLabelText('Jump to a book and section');
    await fireEvent.input(input, { target: { value: '12.36' } });
    await fireEvent.click(screen.getByRole('button', { name: 'Go' }));

    expect(onJump).toHaveBeenCalledWith(12, '12.36', null);
  });

  // Adversarial-review blocker: any syntactically valid verse-line range was
  // being accepted as a location and routed, regardless of whether it
  // matched a real, declared lacuna. A range is valid jump input only when
  // it exactly matches a lacuna column that actually exists in the corpus
  // (design memo §3.4) — "1.1-2" is well-formed range syntax but not a
  // declared gap, so it must be rejected like any other unknown citation.
  it('rejects a verse-line range that does not match a declared lacuna', async () => {
    const onJump = vi.fn();
    render(BekkerJump, { props: { work: 'VerseWork', inputId: 'bk-verse-bad-range', onJump } });
    await fireEvent.click(screen.getByRole('button', { name: /Go to a line/ }));

    const input = screen.getByLabelText('Jump to a line');
    await fireEvent.input(input, { target: { value: '1.1-2' } });
    await fireEvent.click(screen.getByRole('button', { name: 'Go' }));

    expect(onJump).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toHaveTextContent('1.1-2 is not in the Test Poem');
  });

  // The counterpart: a range that IS a declared lacuna (present in
  // columns.json, the corpus's own record of real columns) still resolves.
  it('accepts a verse-line range that matches a declared lacuna', async () => {
    const onJump = vi.fn();
    render(BekkerJump, { props: { work: 'VerseWork', inputId: 'bk-verse-good-range', onJump } });
    await fireEvent.click(screen.getByRole('button', { name: /Go to a line/ }));

    const input = screen.getByLabelText('Jump to a line');
    await fireEvent.input(input, { target: { value: '1.1094-1101' } });
    await fireEvent.click(screen.getByRole('button', { name: 'Go' }));

    expect(onJump).toHaveBeenCalledWith(1, '1.1094-1101', null);
  });

  // A non-range verse-line citation never triggers the new lacuna check —
  // it still resolves straight from the dotted column's own book prefix,
  // with no columns.json lookup involved (same fast path as book-section).
  // Regression for the reported bug: the jump box's own generic error
  // ("Enter a Diels-Kranz citation, e.g. B30") fired for the full scholarly
  // citation form even though REVIEW-CHECKLIST.md advertises it as valid
  // input here — `parseLocation` alone never accepted a "DK <chapter>"
  // prefix; only the ⌘K palette's separate `parseDkFullCitation` call did.
  // 'DkWork' is the dk-scheme fixture above (citation.dkChapter: 22).
  it('accepts the full "DK 22 B30" citation form for its own dk work', async () => {
    const onJump = vi.fn();
    render(BekkerJump, { props: { work: 'DkWork', inputId: 'bk-dk-full', onJump } });
    await fireEvent.click(screen.getByRole('button', { name: /Go to a Diels–Kranz citation/ }));

    const input = screen.getByLabelText('Jump to a Diels–Kranz citation');
    await fireEvent.input(input, { target: { value: 'DK 22 B30' } });
    await fireEvent.click(screen.getByRole('button', { name: 'Go' }));

    expect(onJump).toHaveBeenCalledWith(1, 'B30', null);
  });

  // The "DK" word itself is optional in the scholarly form — "22 B30" means
  // the same thing (see citation.ts's parseDkFullCitation doc comment).
  it('accepts the "22 B30" form (no leading "DK") for its own dk work', async () => {
    const onJump = vi.fn();
    render(BekkerJump, { props: { work: 'DkWork', inputId: 'bk-dk-nodk', onJump } });
    await fireEvent.click(screen.getByRole('button', { name: /Go to a Diels–Kranz citation/ }));

    const input = screen.getByLabelText('Jump to a Diels–Kranz citation');
    await fireEvent.input(input, { target: { value: '22 B30' } });
    await fireEvent.click(screen.getByRole('button', { name: 'Go' }));

    expect(onJump).toHaveBeenCalledWith(1, 'B30', null);
  });

  // Plain "B30" (no chapter prefix at all) must keep working exactly as
  // before — the bug fix must not regress the existing bare-column path.
  it('still accepts a plain "B30" for a dk work', async () => {
    const onJump = vi.fn();
    render(BekkerJump, { props: { work: 'DkWork', inputId: 'bk-dk-plain', onJump } });
    await fireEvent.click(screen.getByRole('button', { name: /Go to a Diels–Kranz citation/ }));

    const input = screen.getByLabelText('Jump to a Diels–Kranz citation');
    await fireEvent.input(input, { target: { value: 'B30' } });
    await fireEvent.click(screen.getByRole('button', { name: 'Go' }));

    expect(onJump).toHaveBeenCalledWith(1, 'B30', null);
  });

  // A full citation naming a DIFFERENT work than the one currently open
  // (DkWork2 is chapter 68; this box is open on DkWork, chapter 22) is a
  // real citation for a real, registered work — jumping there directly is
  // the chosen UX (matching the ⌘K palette's own cross-work handling of the
  // same "DK <chapter> <series><n>" grammar in CommandPalette.svelte), not
  // an error. `onJump` has no way to name a different work, so this always
  // navigates via `window.location.href` rather than the callback.
  it('navigates cross-work for a full citation naming a different dk work', async () => {
    render(BekkerJump, { props: { work: 'DkWork', inputId: 'bk-dk-cross' } });
    await fireEvent.click(screen.getByRole('button', { name: /Go to a Diels–Kranz citation/ }));

    const input = screen.getByLabelText('Jump to a Diels–Kranz citation');
    await fireEvent.input(input, { target: { value: 'DK 68 B1' } });
    await fireEvent.click(screen.getByRole('button', { name: 'Go' }));

    expect(window.location.href).toContain('/dk-author/dkwork2/book/1');
    expect(window.location.href).toContain('loc=B1');
  });

  it('leaves a non-range verse-line citation unaffected', async () => {
    const onJump = vi.fn();
    render(BekkerJump, { props: { work: 'VerseWork', inputId: 'bk-verse-plain', onJump } });
    await fireEvent.click(screen.getByRole('button', { name: /Go to a line/ }));

    const input = screen.getByLabelText('Jump to a line');
    await fireEvent.input(input, { target: { value: '1.101' } });
    await fireEvent.click(screen.getByRole('button', { name: 'Go' }));

    expect(onJump).toHaveBeenCalledWith(1, '1.101', null);
  });
});
