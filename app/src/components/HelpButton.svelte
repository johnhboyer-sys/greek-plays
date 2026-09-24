<script lang="ts">
  // A small "?" button for the reader header that opens a Help modal explaining
  // the reader's features, plus a one-time tip (first reader visit only) that
  // surfaces the otherwise-invisible click-a-word-to-parse feature.
  //
  // The button renders inline in the header; the modal and tip are position:fixed
  // overlays, so where this component sits in the DOM doesn't affect layout.
  import { onMount, onDestroy, tick } from 'svelte';

  const SEEN_KEY = 'ar-help-seen';

  let showHelp = false;
  let showTip = false;
  let helpModal: HTMLDivElement;
  let helpTrigger: HTMLElement | null = null;

  function markSeen() {
    try { localStorage.setItem(SEEN_KEY, '1'); } catch {}
  }

  async function openHelp(e?: Event) {
    helpTrigger = e?.currentTarget instanceof HTMLElement
      ? e.currentTarget
      : document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    showHelp = true;
    showTip = false;
    markSeen();
    await tick();
    helpModal?.focus();
  }
  function closeHelp() {
    showHelp = false;
    helpTrigger?.focus();
    helpTrigger = null;
  }

  function dismissTip() {
    showTip = false;
    markSeen();
  }

  function onKeydown(e: KeyboardEvent) {
    if (!showHelp) return;
    if (e.key === 'Escape') {
      closeHelp();
      return;
    }
    if (e.key !== 'Tab') return;
    const els = helpModal
      ? Array.from(helpModal.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        )).filter((el) => !el.hasAttribute('disabled') && el.tabIndex !== -1)
      : [];
    if (els.length === 0) {
      e.preventDefault();
      helpModal?.focus();
      return;
    }
    const first = els[0];
    const last = els[els.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }

  onMount(() => {
    window.addEventListener('keydown', onKeydown);
    // The Contents sidebar (mobile) opens this same modal via a custom event,
    // since its own "?" trigger is hidden on mobile.
    window.addEventListener('open-help', openHelp);
    let seen = false;
    try { seen = !!localStorage.getItem(SEEN_KEY); } catch {}
    if (!seen) showTip = true;
  });
  onDestroy(() => {
    if (typeof window !== 'undefined') {
      window.removeEventListener('keydown', onKeydown);
      window.removeEventListener('open-help', openHelp);
    }
  });
</script>

<button
  type="button"
  class="help-trigger"
  on:click={openHelp}
  aria-haspopup="dialog"
  aria-label="How to use this reader"
  title="How to use this reader"
>?</button>

{#if showTip}
  <div class="reader-tip" role="status">
    <span class="tip-text">Click a Greek word to see its meaning and grammar.</span>
    <span class="tip-actions">
      <button type="button" class="tip-more" on:click={openHelp}>More tips →</button>
      <button type="button" class="tip-got" on:click={dismissTip}>Got it</button>
    </span>
  </div>
{/if}

{#if showHelp}
  <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
  <div class="help-backdrop" on:click={closeHelp}>
    <div
      class="help-modal"
      bind:this={helpModal}
      role="dialog"
      aria-modal="true"
      aria-label="How to use this reader"
      tabindex="-1"
      on:click|stopPropagation
      on:keydown={onKeydown}
    >
      <!-- DRAFT copy: John approves. -->
      <div class="help-head">
        <h2>How to use the reader</h2>
        <button type="button" class="help-close" on:click={closeHelp} aria-label="Close">×</button>
      </div>

      <p class="help-intro">
        Read Greek plays with English translations, word help, and line citations.
      </p>

      <ul class="help-feature">
        <li>
          <span class="feat-name">Look up any word</span>
          <span class="feat-desc">Click a Greek word to see its lemma, meaning, grammar, and LSJ entry.</span>
        </li>
        <li>
          <span class="feat-name">Cite and share a line</span>
          <span class="feat-desc">As you scroll, the address bar shows the current line. Copy the link to share it.</span>
        </li>
        <li>
          <span class="feat-name">Views and translations</span>
          <span class="feat-desc">Choose <strong>Greek</strong>, <strong>Both</strong>, or <strong>English</strong> with the view buttons. Use the translation picker to choose the English text. In <strong>Settings</strong>, choose <strong>Compare two translations</strong> to see two side by side. On a phone, Settings also has the view buttons, translation picker, Print, text size, and line spacing.</span>
        </li>
        <li>
          <span class="feat-name">Search</span>
          <span class="feat-desc">Open <strong>Search</strong> to find Greek or English words across the plays.</span>
        </li>
        <li>
          <span class="feat-name">Jump to a line or play</span>
          <span class="feat-desc">Press <strong>⌘K</strong> or <strong>Ctrl-K</strong>. Type a line number to jump within this play, a play title to open it, or a Greek word to find its lexicon entry.</span>
        </li>
        <li>
          <span class="feat-name">Color the speakers</span>
          <span class="feat-desc">Each speaker's name has its own color. To turn this off, clear <strong>Color speaker names</strong> in <strong>Settings</strong>.</span>
        </li>
        <li>
          <span class="feat-name">Night mode</span>
          <span class="feat-desc">The moon button in the header switches to the dark theme; the sun button switches back.</span>
        </li>
      </ul>
    </div>
  </div>
{/if}

<style>
  /* Trigger button — mirrors .theme-toggle so it sits naturally beside it. */
  .help-trigger {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2rem;
    height: 2rem;
    flex-shrink: 0;
    font-family: var(--font-ui);
    font-size: 1.05rem;
    font-weight: 600;
    line-height: 1;
    cursor: pointer;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--col-bg);
    color: var(--text-mid);
  }
  .help-trigger:hover {
    border-color: var(--accent);
    color: var(--accent);
  }
  /* The mobile header (title + Contents/Menu) is already tight; the "?" is
     desktop-only. Mobile discovery is carried by the first-visit tip below. */
  @media (max-width: 680px) {
    .help-trigger { display: none; }
  }

  /* First-visit tip — a small dismissible toast at the bottom of the viewport. */
  .reader-tip {
    position: fixed;
    left: 50%;
    bottom: 1.25rem;
    transform: translateX(-50%);
    /* Rise gently into view rather than snapping in. One-shot entrance ⇒
       keyframe; the X-centring is preserved by animating from a lower Y. */
    animation: tip-in 0.24s cubic-bezier(0.2, 0, 0, 1);
    z-index: 60;
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
    justify-content: center;
    max-width: min(34rem, calc(100vw - 2rem));
    padding: 0.7rem 1rem;
    background: var(--popup-bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    box-shadow: var(--popup-shadow);
    font-family: var(--font-ui);
    font-size: 0.9rem;
    color: var(--text);
  }
  .tip-text { line-height: 1.4; }
  .tip-actions {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-shrink: 0;
  }
  .tip-more {
    background: none;
    border: none;
    font: inherit;
    color: var(--accent);
    cursor: pointer;
    padding: 0.2rem 0.2rem;
  }
  .tip-more:hover { text-decoration: underline; }
  .tip-got {
    font: inherit;
    cursor: pointer;
    padding: 0.3rem 0.7rem;
    border: 1px solid var(--accent);
    border-radius: 4px;
    background: var(--accent);
    color: var(--on-accent);
  }
  .tip-got:hover { filter: brightness(1.08); }

  /* Modal — adapted from the "How to type Greek" modal in Search.svelte so the
     two help surfaces look identical (those styles are component-scoped there). */
  .help-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding: 2rem 1rem;
    overflow-y: auto;
    z-index: 50;
    animation: backdrop-in 0.18s ease-out;
  }
  .help-modal {
    background: var(--popup-bg);
    border-radius: 8px;
    max-width: 540px;
    width: 100%;
    padding: 1.25rem 1.5rem 1.75rem;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.25);
    font-family: var(--font-ui);
    color: var(--text);
    /* Soft rise + fade as it opens (one-shot ⇒ keyframe). */
    animation: modal-in 0.2s cubic-bezier(0.2, 0, 0, 1);
  }
  @keyframes tip-in {
    from { opacity: 0; transform: translate(-50%, 12px); }
    to   { opacity: 1; transform: translate(-50%, 0); }
  }
  @keyframes backdrop-in {
    from { opacity: 0; }
    to   { opacity: 1; }
  }
  @keyframes modal-in {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  @media (prefers-reduced-motion: reduce) {
    .reader-tip, .help-backdrop, .help-modal { animation: none; }
  }
  .help-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.5rem;
  }
  .help-head h2 {
    font-size: 1.1rem;
    margin: 0;
    color: var(--text);
  }
  .help-close {
    background: none;
    border: none;
    font-size: 1.6rem;
    line-height: 1;
    color: var(--text-light);
    cursor: pointer;
    padding: 0 0.25rem;
  }
  .help-close:hover { color: var(--text); }
  .help-intro {
    font-size: 0.85rem;
    color: var(--text-mid);
    line-height: 1.5;
    margin: 0 0 0.9rem;
    text-wrap: pretty;
  }

  .help-feature {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
  }
  .help-feature li {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }
  .feat-name {
    font-size: 0.9rem;
    font-weight: 700;
    color: var(--accent);
  }
  .feat-desc {
    font-size: 0.85rem;
    color: var(--text-mid);
    line-height: 1.5;
    text-wrap: pretty;
  }
  .feat-desc strong { color: var(--text); font-weight: 600; }
  .feat-grk { font-family: var(--font-english); color: var(--text); }
</style>
