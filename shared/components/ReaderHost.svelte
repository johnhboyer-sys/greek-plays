<script lang="ts">
  import { onMount } from 'svelte';
  import Reader from './Reader.svelte';
  import Plate from './Plate.svelte';
  import { fetchBook, fetchConcordance, type BookData } from '../lib/data';
  import { editionPlace } from '../lib/edition-place';
  import { getWork } from '../lib/works';
  import { assignSpeakerSlots } from '../lib/speaker-colors';
  import { playSigla } from '../lib/speakers';
  import { lastPrintedRef } from '../lib/citation';
  import { loadEdition, changeEdition, ownEdition, type EditionState, type ReaderView } from '../lib/edition-state';

  export let work: string;
  export let bookNum: number;
  export let bookData: BookData;
  export let serverEdition: string;
  export let chapterTitles: Record<string, string> = {};
  export let speakerRoster: string[] = [];
  export let authorName: string;
  const meta = getWork(work)!;
  const defaultTrans = meta.defaultTranslation ?? meta.translations.find(t => t.slot === 'english')?.id ?? meta.translations[0]?.id ?? '';
  let state: EditionState = { ed: serverEdition, trans: defaultTrans, view: 'both' };
  let shownBook = bookData;
  let anchor: string | null = null;
  let pending = false;
  let generation = 0;

  function syncUrl() {
    const url = new URL(location.href);
    if (state.ed === ownEdition(meta, state.trans)) url.searchParams.delete('ed');
    else url.searchParams.set('ed', state.ed);
    history.replaceState(history.state, '', `${url.pathname}${url.search}${url.hash}`);
  }
  async function show(next: EditionState, loc: string | null = null) {
    const old = state.ed;
    if (old !== next.ed) {
      pending = true;
      const id = ++generation;
      try {
        const data = await fetchBook(work, bookNum, next.ed);
        let oldMap: Record<string, string> = {};
        let newMap: Record<string, string> = {};
        const hasRef = data.segments.some(seg => seg.greek.some(line => line.ref === loc));
        if (loc && !hasRef) {
          if (old !== 'tlg') oldMap = await fetchConcordance(work, old);
          if (next.ed !== 'tlg') newMap = await fetchConcordance(work, next.ed);
        }
        if (id === generation) {
          anchor = editionPlace(loc, old, next.ed, data, oldMap, newMap);
          shownBook = data;
          state = next;
        }
      } finally { if (id === generation) pending = false; }
    } else state = next;
    document.documentElement.removeAttribute('data-ed-pending');
    syncUrl();
  }
  onMount(() => {
    const params = new URLSearchParams(location.search);
    const valid = new Set(meta.translations.map(t => t.id));
    let trans = params.get('trans') ?? localStorage.getItem(`reader-trans-${work}`) ?? defaultTrans;
    if (!valid.has(trans) && trans !== 'compare') trans = defaultTrans;
    let view = params.get('view') ?? localStorage.getItem('reader-view') ?? 'both';
    if (!['both', 'english', 'greek'].includes(view)) view = 'both';
    const next = loadEdition(meta, { trans, view: view as ReaderView, ed: params.get('ed'), loc: params.get('loc') });
    anchor = params.get('loc');
    void show(next, anchor);
  });
  function changed(event: CustomEvent<{ trans: string; view: ReaderView; loc: string | null }>) {
    const next = changeEdition(meta, state, event.detail);
    void show(next, event.detail.loc);
  }
  $: castRoster = shownBook.speakerRoster?.length ? shownBook.speakerRoster : speakerRoster;
  $: slots = assignSpeakerSlots(speakerRoster.length ? speakerRoster : castRoster);
  $: sigla = playSigla((shownBook.segments ?? []).flatMap(seg => seg.speakers ?? []));
  $: persons = castRoster.map(name => ({ name, slot: slots.get(name) ?? 0, siglum: sigla.get(name) ?? null }));
  $: shownSource = (() => {
    const source = meta.greekEditions?.find(e => e.id === state.ed);
    return source && state.ed !== 'tlg'
      ? source.full + (source.licence === 'cc-by-sa-4.0' ? ' · Perseus Digital Library, CC BY-SA 4.0' : '')
      : meta.greekSource.full;
  })();
</script>

{#if meta.citation?.scheme === 'play-line'}
  <Plate greekTitle={meta.greekTitle ?? null} title={meta.title} {authorName}
    argument={meta.argument ?? null} synopsis={meta.synopsis ?? null} production={meta.production ?? null}
    greekSource={shownSource} translations={meta.translations.filter(t => t.id === state.trans).map(t => t.name)}
    copyAbbr={meta.citation?.copyAbbr ?? null} lastLine={lastPrintedRef(shownBook.segments ?? [])}
    {persons} startHref={`#col-${shownBook.segments?.[0]?.column ?? '1'}`} />
{/if}
{#if pending}<div class="ed-pending" role="status" aria-label="Loading text">◌</div>{/if}
{#key state.ed}
  <div style:visibility={pending ? 'hidden' : 'visible'}>
    <Reader {work} {bookNum} bookData={shownBook} {chapterTitles} {speakerRoster}
      edition={state.ed} initialLocation={anchor} initialTranslation={state.trans} initialView={state.view}
      on:editionChange={changed} />
  </div>
{/key}
