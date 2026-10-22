<script lang="ts">
  import { onDestroy, onMount, tick } from 'svelte';
  import { fly } from 'svelte/transition';
  import {
    lookupWord,
    fetchLemmata,
    fetchLsjHeads,
    lemmaEntryHref,
    type Analysis,
    type LemmaRef,
    type LsjHead,
  } from '../lib/data';
  import { betaToGreek } from '../lib/betacode';
  import { parseInWords } from '../lib/parse-words';
  import { loadGrammataLookup } from '../lib/grammata';
  import { orderBySurface } from '../lib/name-order';
  import { getWork } from '../lib/works';

  export let work: string = 'EN';
  export let edition: string | null = null;
  // The drama corpus is Greek, but retaining the existing Latin labels costs
  // no extra data path and keeps this shared component safe for a Latin host.
  const isLat = getWork(work)?.language === 'lat';
  const sourceLang = isLat ? 'la' : 'grc';
  const langPath: 'grc' | 'lat' = isLat ? 'lat' : 'grc';
  export let token: { t: string; k?: string };
  export const anchor: { x: number; y: number } = { x: 0, y: 0 };
  export let onClose: () => void;
  export let asSheet: boolean = false;

  let dialogEl: HTMLDivElement;
  let previousFocus: HTMLElement | null = null;
  let analyses: Analysis[] = [];
  let loading = true;
  let error = '';
  const isMobile = typeof window !== 'undefined'
    && window.matchMedia('(max-width: 680px)').matches;
  const asSheetHere = typeof window !== 'undefined'
    && (isMobile || (asSheet && window.matchMedia('(min-width: 681px) and (max-width: 1100px)').matches));
  const reduceMotion = typeof window !== 'undefined'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Reader swaps the token without remounting this component. The request id
  // stops a slow prior lookup from replacing the current word.
  let reqId = 0;
  $: loadWord(work, token.k, edition);
  function loadWord(w: string, k: string | undefined, ed: string | null) {
    const id = ++reqId;
    lexId++;
    if (!k) {
      analyses = [];
      error = '';
      loading = false;
      return;
    }
    loading = true;
    error = '';
    analyses = [];
    (ed ? lookupWord(w, k, ed) : lookupWord(w, k))
      .then((result) => { if (id === reqId) analyses = orderBySurface(result.analyses, token.t); })
      .catch((cause) => { if (id === reqId) error = String(cause); })
      .finally(() => { if (id === reqId) { loading = false; void openFirst(id); } });
  }

  // The page manifest drives concordance links. The small heads manifest gives
  // each keyed card its Unicode headword and LSJ's own homograph letter without
  // downloading any LSJ shard.
  const base = import.meta.env.BASE_URL.replace(/\/$/, '');
  let lemmata: Record<string, LemmaRef> = {};
  fetchLemmata(langPath).then((manifest) => { lemmata = manifest; }).catch(() => {});
  let heads: Record<string, LsjHead> = {};
  fetchLsjHeads().then((manifest) => { heads = manifest; }).catch(() => {});

  // Cards are keyed by dictionary entry, not by morphological analysis. An
  // analysis may name several entries; each entry gets its own card and shares
  // only the parses that point to it.
  const DIALECTS = ['attic', 'epic', 'doric', 'ionic', 'aeolic', 'homeric'];

  function splitParse(parse: string): { text: string; dialect: string } {
    const match = /\(([^)]*)\)\s*$/.exec(parse ?? '');
    if (!match) return { text: (parse ?? '').trim(), dialect: '' };
    const named = match[1].split(/\s+/).filter((word) => DIALECTS.includes(word));
    if (!named.length) return { text: (parse ?? '').trim(), dialect: '' };
    const text = parse.slice(0, match.index).trim();
    if (named.includes('attic')) return { text, dialect: '' };
    return { text, dialect: named.length === 1 ? `${named[0]} only` : named.join(' ') };
  }

  interface EntryCard {
    id: string;
    lsjKey: string;
    head: string;
    hom: string;
    gloss: string;
    glossExact: boolean;
    rows: { text: string; dialect: string }[];
    ref: LemmaRef | null;
  }

  $: cards = (() => {
    const out: EntryCard[] = [];
    const byId = new Map<string, EntryCard>();
    for (const analysis of analyses) {
      const keys = analysis.lsj?.length ? analysis.lsj : [''];
      const exact = keys.length === 1;
      for (const key of keys) {
        const id = key || `lemma:${analysis.lemma}`;
        let card = byId.get(id);
        if (!card) {
          const meta = key ? heads[key] : undefined;
          card = {
            id,
            lsjKey: key,
            head: meta?.head || (isLat ? analysis.lemma.replace(/#\d+$/, '') : betaToGreek(analysis.lemma)),
            hom: meta?.hom ?? '',
            gloss: analysis.gloss,
            glossExact: exact,
            rows: [],
            ref: (key && lemmata[key]) || null,
          };
          byId.set(id, card);
          out.push(card);
        }
        // An exact gloss belongs to this entry. A fan-out gloss can fill a
        // blank, but it cannot label a different homograph as certain.
        if (exact) {
          if (analysis.gloss) card.gloss = analysis.gloss;
          else if (!card.glossExact) card.gloss = '';
          card.glossExact = true;
        } else if (!card.glossExact && !card.gloss && analysis.gloss) {
          card.gloss = analysis.gloss;
        }
        const row = splitParse(analysis.parse);
        if (!card.rows.some((existing) => existing.text === row.text && existing.dialect === row.dialect)) {
          card.rows.push(row);
        }
      }
    }
    return out;
  })();

  let openId = '';
  $: if (token) openId = '';

  function toggleCard(card: EntryCard, el: HTMLElement | undefined) {
    openId = openId === card.id ? '' : card.id;
    if (openId && el) renderLexicon(el, card.head, card.lsjKey);
  }

  // The first entry opens with the parse, so the dictionary stands under it
  // (the drama site's word panel, UI pass 2); a word with several entries
  // keeps the toggle on the others. Every completed lookup renders it again:
  // a repeated lookup of the same word cancels the render before it (lexId).
  async function openFirst(id: number) {
    await tick();
    const mount = dialogEl?.querySelector<HTMLElement>('.analysis-card .grammata-mount');
    if (id !== reqId || !cards.length || !mount) return;
    openId = cards[0].id;
    renderLexicon(mount, cards[0].head, cards[0].lsjKey);
  }

  // A slow entry render must not land after the reader has opened another card
  // or moved to another word.
  let lexId = 0;
  async function renderLexicon(el: HTMLElement, word: string, key: string) {
    const id = ++lexId;
    try {
      const lookup = await loadGrammataLookup();
      if (id !== lexId) return;
      await lookup(key ? '' : word, el, key ? { lang: langPath, key } : { lang: langPath });
      if (id !== lexId) return;
    } catch (cause) {
      if (id === lexId) el.textContent = 'Word data is not available here.';
      console.error('[grammata] lookup failed', cause);
    }
  }

  function onKey(event: KeyboardEvent) {
    if (event.key === 'Escape') onClose();
  }

  function onOutsideClick(event: MouseEvent) {
    const target = event.target as HTMLElement | null;
    if (!target || target.closest('.word-sidebar') || target.closest('.tok')) return;
    onClose();
  }

  onMount(() => {
    previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setTimeout(() => dialogEl?.focus({ preventScroll: true }), 0);
  });

  onDestroy(() => {
    previousFocus?.focus({ preventScroll: true });
  });
</script>

<svelte:window on:keydown={onKey} on:click|capture={onOutsideClick} />

<div
  class="word-sidebar"
  class:as-sheet={asSheet}
  bind:this={dialogEl}
  transition:fly={reduceMotion ? { duration: 0 } : asSheetHere ? { y: 600, duration: 260, opacity: 1 } : { x: 420, duration: 220, opacity: 1 }}
  role="dialog"
  aria-label="Word analysis"
  tabindex="-1"
>
  <div class="word-sidebar-head">
    <span class="popup-surface" lang={sourceLang}>{token.t}</span>
    <button class="settings-close" on:click={onClose} aria-label="Close">×</button>
  </div>
  <div class="word-sidebar-body">
    {#if loading}
      <div class="popup-loading">Looking up…</div>
    {:else if error}
      <div class="popup-loading">Error: {error}</div>
    {:else if analyses.length === 0}
      <div class="popup-loading">No analysis found for this form.</div>
    {:else}
      {#if analyses.some((analysis) => analysis.foldedAccent)}
        <div class="lsj-ambiguous-note">
          All-capitals form — accents supplied; readings listed are all matches.
        </div>
      {/if}
      {#each cards as card (card.id)}
        <div class="analysis-card" class:card-open={openId === card.id}>
          <button
            type="button"
            class="card-face"
            aria-expanded={openId === card.id}
            on:click={(event) => toggleCard(card, (event.currentTarget as HTMLElement)
              .parentElement?.querySelector('.grammata-mount') as HTMLElement)}
          >
            <span class="lemma" lang={sourceLang}>{card.head}{#if card.hom}<span class="lemma-hom" lang="en"> ({card.hom})</span>{/if}</span>
            <span class="gloss">{card.gloss}</span>
            <dl class="parse-rows">
              {#each card.rows as row}
                <dt>{parseInWords(row.text)}</dt>
                <dd>{row.dialect}</dd>
              {/each}
            </dl>
            <span class="card-open-hint">
              <span class="card-arrow" aria-hidden="true">▸</span>
              {openId === card.id ? 'Hide dictionary definition' : 'Show dictionary definition'}
            </span>
          </button>

          {#if card.ref}
            <a class="lemma-link" href={lemmaEntryHref(base, langPath, card.ref.slug)}>
              {card.ref.count.toLocaleString()} place{card.ref.count === 1 ? '' : 's'} in the plays
            </a>
          {/if}

          <div class="card-entry" hidden={openId !== card.id}>
            <div class="grammata-mount"></div>
          </div>
        </div>
      {/each}
    {/if}
  </div>
</div>
