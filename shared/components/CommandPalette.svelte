<script lang="ts">
  import { tick } from 'svelte';
  import { fetchColumns, fetchLemmata, lemmaEntryHref, resolveBekker, type LemmaRef } from '../lib/data';
  import { workPath, getWork } from '../lib/works';
  import { schemeFor, formatLocValue, parseDkFullCitation } from '../lib/citation';
  import { resumeFor } from '../lib/resume';
  import { hasGreek, rankLemmata, rankWorks } from '../lib/palette';

  // The work currently open in the reader (enables citation jumps); null on
  // pages with no work context (home, landings).
  export let work: string | null = null;
  // Hosts with their own routing pass a callback; the site default navigates
  // the tab (same contract as BekkerJump's onJump).
  export let onNavigate: ((href: string) => void) | null = null;

  const base = import.meta.env.BASE_URL.replace(/\/$/, '');

  interface Item {
    kind: 'cite' | 'work' | 'lemma' | 'search';
    label: string;
    detail: string;
    href: string;
  }

  let open = false;
  let query = '';
  let items: Item[] = [];
  let selected = 0;
  let inputEl: HTMLInputElement | undefined;
  let lemmata: Record<string, LemmaRef> | null = null;
  let seq = 0; // stale-async guard
  let boxEl: HTMLDivElement | undefined;
  let restoreEl: HTMLElement | null = null; // focus to give back on close

  function navigate(href: string) {
    close();
    if (onNavigate) onNavigate(href);
    else window.location.href = href;
  }

  export async function openPalette() {
    restoreEl = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    open = true;
    query = '';
    items = [];
    selected = 0;
    await tick();
    inputEl?.focus();
  }

  function close() {
    open = false;
    query = '';
    items = [];
    restoreEl?.focus();
    restoreEl = null;
  }

  function onWindowKey(e: KeyboardEvent) {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      if (open) close();
      else openPalette();
      return;
    }
    if (open && e.key === 'Escape') { e.preventDefault(); close(); }
  }

  async function compute(q: string) {
    const mySeq = ++seq;
    const out: Item[] = [];
    const trimmed = q.trim();
    if (!trimmed) { items = []; selected = 0; return; }

    // 1. A citation (Stephanus page, e.g. "34b") jumps within the current work.
    //    Parsing dispatches on the work's own scheme, so a line-bearing scheme
    //    (Bekker/Busse, were this shared reader mounted on one) still works.
    const cite = work ? schemeFor(work).parseLocation(trimmed) : null;
    if (cite && work) {
      // A dotted-scheme column (book-section: "4.23") carries its book as a
      // literal prefix, so it never needs the columns.json/resolveBekker
      // lookup below — see citation.ts's bookFromColumn doc comment.
      const direct = schemeFor(work).bookFromColumn(cite.column);
      let book: number | null;
      // Astra lane A, F9: a play-line printed range (Ag. 106-107) is a real
      // lineref, not a verse-line lacuna column. ?loc= already accepts it;
      // keep the columns-map membership check for every other scheme.
      if (direct != null && (!cite.isRange || schemeFor(work).id === 'play-line')) {
        book = direct;
      } else {
        // A verse-line range ("1.1094-1101") is valid jump input only when
        // it exactly matches a declared lacuna — a real column in the
        // corpus — never merely well-formed range syntax (design memo
        // §3.4, same policy BekkerJump.svelte's go() applies). Reuses the
        // same columns.json channel every other scheme's citation-
        // membership check reads, rather than trusting bookFromColumn's
        // syntax-only book derivation.
        const cols = await fetchColumns(work).catch(() => null);
        if (mySeq !== seq) return; // a newer keystroke superseded this pass
        book = cols
          ? cite.isRange
            ? (cols[cite.column] ? direct : null)
            : resolveBekker(cols, cite.column, cite.line ?? 1)
          : null;
      }
      // bookFromColumn/resolveBekker validate the column's own grammar but
      // not corpus membership — a dotted column like "99.99" derives book 99
      // from syntax alone. Reject an out-of-range book here rather than
      // offering a jump that workPath would silently clamp to the work's
      // last book with an unresolvable ?loc (see citation.ts's bookFromColumn
      // doc comment). Section-level existence (is "36" a real section of book
      // 12?) still can't be checked client-side — landing on a real book with
      // a no-op loc is tolerable; landing on the wrong book is not.
      const w = getWork(work);
      if (book != null && w && book >= 1 && book <= w.books) {
        out.push({
          kind: 'cite',
          label: `Go to ${schemeFor(work).formatCitation(cite.column, cite.line)}`,
          detail: w.title,
          href: `${base}${workPath(work, book)}?loc=${formatLocValue(work, cite.column, cite.line)}`,
        });
      }
    }

    // 1.5. A site-wide dk full citation ("DK 22 B30" / "22 B30") resolves
    //      which WORK to jump to from the cited chapter+series itself —
    //      unlike step 1 above (which only ever jumps within the work
    //      already open), this fires regardless of the current page. See
    //      citation.ts's parseDkFullCitation doc comment.
    const dkFull = parseDkFullCitation(trimmed);
    if (dkFull) {
      const w = getWork(dkFull.workId);
      if (w) {
        out.push({
          kind: 'cite',
          label: `Go to ${schemeFor(dkFull.workId).formatCitation(dkFull.column, dkFull.line)}`,
          detail: w.title,
          href: `${base}${workPath(dkFull.workId)}?loc=${formatLocValue(dkFull.workId, dkFull.column, dkFull.line)}`,
        });
      }
    }

    // 2. Works by name/abbreviation — resuming a saved position when one exists.
    for (const w of rankWorks(trimmed)) {
      const pos = resumeFor(w.id);
      const book = pos ? Math.min(Math.max(1, pos.book), w.books) : 1;
      // Astra lane A, F8: a later occurrence is saved as "803--2" so the
      // hash lands on the second 803; drop that suffix from the displayed
      // resume text. The href keeps the full cite.
      const displayCite = pos?.cite ? pos.cite.replace(/--\d+$/, '') : null;
      out.push({
        kind: 'work',
        label: w.title,
        detail: displayCite ? `resumes at ${displayCite}` : w.blurb,
        href: `${base}${workPath(w.id, book)}${pos?.cite ? `#${pos.cite}` : ''}`,
      });
    }

    // 3. Greek input also matches lemma pages (concordance + LSJ).
    if (hasGreek(trimmed)) {
      lemmata ??= await fetchLemmata().catch(() => ({}));
      if (mySeq !== seq) return;
      for (const ref of rankLemmata(trimmed, lemmata)) {
        out.push({
          kind: 'lemma',
          label: ref.head,
          detail: `lexicon · ${ref.count.toLocaleString()} occurrences`,
          href: lemmaEntryHref(base, 'grc', ref.slug),
        });
      }
    }

    // 4. Always offer the full corpus search.
    out.push({
      kind: 'search',
      label: `Search the corpus for “${trimmed}”`,
      detail: 'Greek & English · all works',
      href: `${base}/search?${hasGreek(trimmed) ? 'g' : 'e'}=${encodeURIComponent(trimmed)}`,
    });

    items = out;
    selected = 0;
  }

  $: if (open) compute(query);

  // aria-modal promises focus stays inside: wrap Tab within the dialog's
  // focusable controls (the input + result buttons).
  function onBoxKey(e: KeyboardEvent) {
    if (e.key !== 'Tab' || !boxEl) return;
    const focusables = boxEl.querySelectorAll<HTMLElement>('input, button');
    if (!focusables.length) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }

  function onInputKey(e: KeyboardEvent) {
    if (e.key === 'ArrowDown') { e.preventDefault(); selected = Math.min(selected + 1, items.length - 1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); selected = Math.max(selected - 1, 0); }
    else if (e.key === 'Enter') {
      e.preventDefault();
      const item = items[selected];
      if (item) navigate(item.href);
    }
  }
</script>

<svelte:window on:keydown={onWindowKey} />

{#if open}
  <div class="cp-backdrop" on:click={(e) => { if (e.target === e.currentTarget) close(); }} role="presentation">
    <div class="cp-box" role="dialog" aria-modal="true" aria-label="Jump to a work, citation, or lemma" tabindex="-1"
         bind:this={boxEl} on:keydown={onBoxKey}>
      <input
        class="cp-input"
        type="text"
        bind:this={inputEl}
        bind:value={query}
        on:keydown={onInputKey}
        placeholder="Play, line number, or Greek word…"
        aria-label="Jump to a play, line number, or Greek word"
        role="combobox"
        aria-expanded={items.length > 0}
        aria-controls="cp-list"
        aria-activedescendant={items.length ? `cp-item-${selected}` : undefined}
        spellcheck="false"
        autocapitalize="off"
        autocomplete="off"
      />
      {#if items.length}
        <ul class="cp-list" id="cp-list" role="listbox">
          {#each items as item, i}
            <li
              id={`cp-item-${i}`}
              role="option"
              aria-selected={i === selected}
              class="cp-item"
              class:active={i === selected}
            >
              <button type="button" on:click={() => navigate(item.href)} on:mousemove={() => (selected = i)}>
                <span class="cp-kind">{item.kind === 'cite' ? '§' : item.kind === 'work' ? '📖' : item.kind === 'lemma' ? 'λ' : '🔍'}</span>
                <span class="cp-label" class:gk={item.kind === 'lemma'}>{item.label}</span>
                <span class="cp-detail">{item.detail}</span>
              </button>
            </li>
          {/each}
        </ul>
      {:else if query.trim()}
        <p class="cp-empty">Keep typing — a play, line number, or Greek word.</p>
      {/if}
      <p class="cp-hint"><kbd>↑↓</kbd> select · <kbd>⏎</kbd> open · <kbd>esc</kbd> close</p>
    </div>
  </div>
{/if}
