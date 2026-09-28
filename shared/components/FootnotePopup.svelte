<script lang="ts">
  import { afterUpdate, onDestroy } from 'svelte';
  import { fetchFootnotes } from '../lib/data';
  import { sanitizeHtml } from '../lib/html';

  export let work: string = 'EN';
  export let n: string;             // full label identity, e.g. "1", "2.3.1", "*"
  // §B4.3/4.4: which translation's footnote map `n` belongs to — set from the
  // marker's `data-fn-trans`. '' for legacy call sites that omit it (none in
  // this codebase after Phase 4B, but keeps the prop non-breaking).
  export let transId: string = '';
  export let anchor: { x: number; y: number };
  export let onClose: () => void;
  // Hover bridge: cancel/schedule the parent's close timer so the cursor can
  // move from the `[^N]` marker into the popup without it disappearing.
  export let onHoverIn: () => void = () => {};
  export let onHoverOut: () => void = () => {};
  export let takeFocus = false;
  export let returnFocus: HTMLElement | null = null;

  let html = '';
  let loading = true;
  let error = '';
  let dialogEl: HTMLDivElement;
  let focusedByActivation = false;
  let focusTimer: ReturnType<typeof setTimeout> | null = null;

  // §Phase-3 B5 / Reader.svelte's fnDisplay: the printed number to show in
  // the header — a scoped label's ("2.3.1") trailing component, a star/
  // dagger glyph verbatim, or (continuous scope, the pre-Phase-4B norm) the
  // label itself unchanged. Duplicated in Reader.svelte rather than shared
  // because it's a two-line pure function and this component must stay
  // import-free of Reader's internals.
  function fnDisplay(label: string): string {
    if (label === '*' || label === '†') return label;
    // "<running>.<printed>" (every drama translation's notes): the running
    // number, 1, 2, 3 through the play. The printed part is a line number in
    // Smyth ("4.107") and the edition's own count elsewhere, which read as a
    // jumbled sequence beside the margin numbers (John, 2026-09-28).
    const run = /^(\d+)\.\S/.exec(label); // also Smyth's "12.437ff."
    if (run) return run[1];
    const i = label.lastIndexOf('.');
    return i === -1 ? label : label.slice(i + 1);
  }
  $: display = fnDisplay(n);

  // Keep the popup inside the viewport (anchored below the marker).
  function clampedPos(x: number, y: number) {
    const W = 440, H = 360, vw = window.innerWidth, vh = window.innerHeight;
    return {
      left: Math.max(8, Math.min(x, vw - W - 16)) + 'px',
      top:  Math.min(y + 8, vh - H - 16) + 'px',
    };
  }

  $: pos = clampedPos(anchor.x, anchor.y);

  // §B4.4: an imported translation's footnote text is resolved through a
  // window-level hook installed by desktop/src/lib/imports.ts's
  // installHooks() — this component (app/src) is SHARED with the static
  // site build, which has no imports.ts and must not import desktop code, so
  // the established pattern (mirroring __READER_BOOK_HOOK__ /
  // __READER_EXTRA_TRANSLATIONS__) is a lazily-read global instead of a
  // direct import. On the site build neither hook is ever installed, so
  // `isImportedTrans()` is always false and every call falls through to the
  // original `fetchFootnotes(work)` path unchanged — inert, byte-identical.
  //
  // `isImportedTrans` is a SEPARATE hook from the note lookup itself so a
  // registered import with no definition for this label ("footnote-note-
  // unmatched") shows "not found" instead of silently falling through to
  // fetchFootnotes(work) — which could otherwise return a DIFFERENT
  // translation's note text for the same work if the labels happen to
  // collide (continuous scope on both sides uses plain digits).
  function isImportedTrans(): boolean {
    if (!transId) return false;
    const hook = (globalThis as {
      __READER_IMPORT_HAS_TRANS__?: (work: string, id: string) => boolean;
    }).__READER_IMPORT_HAS_TRANS__;
    return hook ? hook(work, transId) : false;
  }

  if (isImportedTrans()) {
    const hook = (globalThis as {
      __READER_IMPORT_FOOTNOTE_HOOK__?: (work: string, id: string, label: string) => string | null;
    }).__READER_IMPORT_FOOTNOTE_HOOK__;
    const note = hook ? hook(work, transId, n) : null;
    // Astra lane A, F4: every lookup path sanitizes before {@html}.
    html = sanitizeHtml(note ?? '');
    if (!html) error = `Footnote ${display} not found.`;
    loading = false;
  } else {
    fetchFootnotes(work)
      .then(map => { html = sanitizeHtml(map[n] ?? ''); if (!html) error = `Footnote ${display} not found.`; })
      .catch(e => { error = String(e); })
      .finally(() => { loading = false; });
  }

  function onKey(e: KeyboardEvent) {
    if (e.key === 'Escape') onClose();
  }

  function focusableEls(): HTMLElement[] {
    return dialogEl
      ? Array.from(dialogEl.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        )).filter((el) => !el.hasAttribute('disabled') && el.tabIndex !== -1)
      : [];
  }

  function onDialogKey(e: KeyboardEvent) {
    if (e.key !== 'Tab') return;
    const els = focusableEls();
    if (els.length === 0) {
      e.preventDefault();
      dialogEl?.focus();
      return;
    }
    const first = els[0];
    const last = els[els.length - 1];
    const active = document.activeElement;
    // Astra lane A, F12: mount focuses the dialog itself (tabindex=-1), which
    // is not in the descendant control list; wrap Tab/Shift-Tab from there too.
    if (e.shiftKey && (active === first || active === dialogEl)) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && (active === last || active === dialogEl)) {
      e.preventDefault();
      first.focus();
    }
  }

  afterUpdate(() => {
    if (takeFocus && !focusedByActivation) {
      focusedByActivation = true;
      focusTimer = setTimeout(() => { dialogEl?.focus(); focusTimer = null; }, 0);
    }
  });

  onDestroy(() => {
    if (focusTimer) clearTimeout(focusTimer);
    if (focusedByActivation) returnFocus?.focus();
  });
</script>

<svelte:window on:keydown={onKey} />

<div
  class="popup footnote-popup"
  bind:this={dialogEl}
  style="left:{pos.left};top:{pos.top}"
  role="dialog"
  aria-label="Footnote {display}"
  aria-modal={takeFocus ? 'true' : undefined}
  tabindex="-1"
  on:mouseenter={onHoverIn}
  on:mouseleave={onHoverOut}
  on:focus={onHoverIn}
  on:blur={onHoverOut}
  on:keydown={onDialogKey}
>
  <div class="popup-header">
    <span class="footnote-num">Note {display}</span>
    <button class="popup-close" on:click={onClose} aria-label="Close">✕</button>
  </div>

  <div class="popup-body">
    {#if loading}
      <div class="popup-loading">Loading…</div>
    {:else if error}
      <div class="popup-loading">{error}</div>
    {:else}
      <!-- eslint-disable-next-line svelte/no-at-html-tags -->
      <div class="footnote-text">{@html html}</div>
    {/if}
  </div>
</div>
