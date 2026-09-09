<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { dataRoot } from '@shared/lib/data';
  import { loadGrammataLookup } from '@shared/lib/grammata';
  import { getWork, workLanding, bookLabel, isBookless } from '@shared/lib/works';
  import { groupUnitNoun } from '@shared/lib/citation';
  import { tocGroupNoun } from '../lib/citation-copy';
  import { instHref, instLabel, type Instance } from '../lib/lemma-instance';

  export let lang: 'grc' | 'lat' = 'grc';

  interface ChapterInstances { chapter: string; bekker: string; instances: Instance[]; }
  interface BookInstances { book: number; chapters: ChapterInstances[]; }
  interface WorkInstances { work: string; title: string; count: number; shown: number; books: BookInstances[]; }
  interface LemmaData {
    slug: string; key: string; head: string; lemmaBeta: string;
    count: number; glosses: string[]; byWork: { work: string; title: string; count: number }[];
    instancesByWork: WorkInstances[]; truncated: boolean;
  }

  let data: LemmaData | null = null;
  let loading = true;
  let problem = '';
  let grammataEl: HTMLDivElement | undefined;
  const base = import.meta.env.BASE_URL.replace(/\/$/, '');
  $: langPath = lang;
  $: langLabel = lang === 'lat' ? 'Latin' : 'Greek';
  $: dictLabel = lang === 'lat' ? 'L&S' : 'LSJ';
  $: htmlLang = lang === 'lat' ? 'la' : 'grc';
  $: headFont = lang === 'lat' ? 'var(--font-latin)' : 'var(--font-greek)';
  $: maxWork = data?.byWork[0]?.count ?? 1;

  async function renderDictionary(el: HTMLElement, key: string) {
    try {
      const lookup = await loadGrammataLookup();
      await lookup('', el, { lang: langPath, key });
    } catch (cause) {
      el.textContent = 'The dictionary entry is not available here.';
      console.error('[grammata] lookup failed', cause);
    }
  }

  onMount(async () => {
    const slug = new URLSearchParams(window.location.search).get('w')?.trim();
    if (!slug) {
      problem = 'This entry has no word selected.';
      loading = false;
      return;
    }
    const dir = lang === 'lat' ? 'lemmata-lat' : 'lemmata';
    try {
      const response = await fetch(`${dataRoot()}/${dir}/${encodeURIComponent(slug)}.json`);
      if (!response.ok) {
        problem = 'That lexicon entry was not found.';
      } else {
        data = await response.json();
      }
    } catch {
      problem = 'This lexicon entry could not be loaded.';
    }
    loading = false;
    await tick();
    if (data?.key && grammataEl) await renderDictionary(grammataEl, data.key);
  });

  const workView = (w: WorkInstances) => {
    const work = getWork(w.work);
    return {
      ...w,
      bookless: work ? isBookless(work) : false,
      unit: groupUnitNoun(w.work),
      bookNoun: tocGroupNoun(w.work),
      flat: w.shown <= 30,
      capped: w.shown < w.count,
      barPct: Math.max(2, (w.count / maxWork) * 100),
      books: w.books.map((bk) => ({
        ...bk,
        label: work ? bookLabel(work, bk.book) : String(bk.book),
        bookCount: bk.chapters.reduce((n, ch) => n + ch.instances.length, 0),
      })),
    };
  };
</script>

<main class="lx-body">
  {#if loading}
    <p class="lx-note">Loading lexicon entry…</p>
  {:else if problem}
    <p class="lx-note">{problem} <a href={`${base}/lemma/${langPath}/`}>Browse the {langLabel.toLowerCase()} lexicon.</a></p>
  {:else if data}
    <h1 class="lx-head-gk" lang={htmlLang} style={`font-family:${headFont}`}>{data.head}</h1>
    <p class="lx-translit">{data.slug}</p>
    {#if data.glosses[0]}<p class="lx-gloss">{data.glosses.join('; ')}</p>{/if}
    <p class="lx-freq">Appears <b>{data.count.toLocaleString()}</b> times across the corpus.</p>

    <h2 class="lx-h">Frequency by work</h2>
    <p class="lx-note">Click a work to list every occurrence by citation — each links into the reader.</p>
    <ul class="lx-freqbars">
      {#each data.instancesByWork as raw}
        {@const w = workView(raw)}
        <li>
          <details class="fb-item">
            <summary>
              <span class="fb-name">{w.title}</span><span class="fb-track"><span class="fb-fill" style={`width:${w.barPct}%`}></span></span>
              <span class="fb-n">{w.count.toLocaleString()}</span><span class="fb-caret" aria-hidden="true">▸</span>
            </summary>
            <div class="fb-cites">
              <a class="fb-open" href={`${base}${workLanding(w.work)}`}>Open {w.title} ›</a>
              {#each w.books as bk}
                {#if w.bookless}
                  <div class="fb-book-group">
                    {#each bk.chapters as ch}
                      <div class="fb-chapter">
                        {#if ch.chapter !== '?'}<div class="fb-ch-head"><span class="fb-ch-label">{w.unit ? `${w.unit} ${ch.chapter}` : ch.chapter}</span>{#if ch.bekker}<span class="fb-ch-bekker">{ch.bekker}</span>{/if}</div>{/if}
                        <ul class="fb-citelist">{#each ch.instances as inst}<li><a href={instHref(base, w.work, bk.book, inst)}>{instLabel(w.work, inst)}</a></li>{/each}</ul>
                      </div>
                    {/each}
                  </div>
                {:else}
                  <details class="fb-book-d" open={w.flat}>
                    <summary><span class="fb-book">{w.bookNoun} {bk.label}</span><span class="fb-book-n">{bk.bookCount}</span><span class="fb-caret fb-book-caret" aria-hidden="true">▸</span></summary>
                    <div class="fb-book-body">
                      {#each bk.chapters as ch}
                        <div class="fb-chapter">
                          {#if ch.chapter !== '?'}<div class="fb-ch-head"><span class="fb-ch-label">{w.unit ? `${w.unit} ${ch.chapter}` : ch.chapter}</span>{#if ch.bekker}<span class="fb-ch-bekker">{ch.bekker}</span>{/if}</div>{/if}
                          <ul class="fb-citelist">{#each ch.instances as inst}<li><a href={instHref(base, w.work, bk.book, inst)}>{instLabel(w.work, inst)}</a></li>{/each}</ul>
                        </div>
                      {/each}
                    </div>
                  </details>
                {/if}
              {/each}
              {#if w.capped}<p class="lx-note">Showing {w.shown.toLocaleString()} of {w.count.toLocaleString()} (list capped).</p>{/if}
            </div>
          </details>
        </li>
      {/each}
    </ul>

    {#if data.key}
      <h2 class="lx-h">Dictionary ({dictLabel})</h2>
      <div class="grammata-mount" data-key={data.key} lang={htmlLang} bind:this={grammataEl}>
        Loading the dictionary entry…
      </div>
    {/if}
  {/if}
  <a class="lx-back" href={`${base}/lemma/${langPath}/`}>‹ All lexicon entries</a>
</main>

