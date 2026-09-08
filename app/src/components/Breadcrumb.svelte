<script lang="ts">
  import { authorPath, workLanding } from '@shared/lib/works';
  import { SITE_NAME } from '../lib/site';

  // SITE NAME > AUTHOR (> WORK) — the site's one navigation breadcrumb, shared by
  // the author landing, work landing, and reader pages. Every crumb is a
  // plain link (the site name -> /, author name -> authorPath, work title ->
  // workLanding) — no work-switcher <select> (John's ruling: no play-switcher
  // inside the reader; the running head's/breadcrumb's author and work are
  // links back out, nothing more).
  //
  // Both option lists are computed by the calling page at build time (via
  // app/src/lib/built-works.ts's builtAuthors()/builtWorksOf()) and passed in
  // as plain data — this component never touches the filesystem.
  export let authorId: string;
  export let authors: { id: string; name: string }[];
  // P4 skin: the first crumb IS the site name (small uppercase letterspaced
  // sans, docs/mockups/2026-09-08-blend.html `.dir-b .head .site`), so the
  // header carries one link home, not a wordmark plus a "Home" crumb.
  // Omitted on the author landing page: SITE NAME > AUTHOR only, no WORK crumb.
  export let workId: string | undefined = undefined;
  export let works: { id: string; title: string }[] = [];
  // Reader pages: no crumb is aria-current (the current URL is a book page,
  // not a crumb).
  export let readerNav = false;

  const base = import.meta.env.BASE_URL.replace(/\/$/, '');

  $: authorName = authors.find((a) => a.id === authorId)?.name ?? authorId;
  $: workTitle = works.find((w) => w.id === workId)?.title ?? workId;
</script>

<nav class="header-title" aria-label="Breadcrumb">
  <ol class="breadcrumb-list" role="list">
    <li>
      <a class="home-link" href={`${base}/`}>{SITE_NAME}</a>
    </li>
    <li>
      <span class="title-sep" aria-hidden="true">·</span>
      <a class="bc-crumb" href={`${base}${authorPath(authorId)}`}
         aria-current={workId ? undefined : 'page'}>{authorName}</a>
    </li>
    {#if workId}
      <li>
        <span class="title-sep" aria-hidden="true">·</span>
        <a class="bc-crumb" href={`${base}${workLanding(workId)}`}
           aria-current={readerNav ? undefined : 'page'}>{workTitle}</a>
      </li>
    {/if}
  </ol>
</nav>

<style>
  /* Real ol/li structure styled as the flex row directly (no display:contents
     — Safari/VoiceOver drops list semantics from the AT tree for it). The ol
     is the single flex child of the nav (.header-title, global.css), so the
     row reads exactly like the markup it replaced. */
  .breadcrumb-list {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 0.4rem;
    list-style: none;
    margin: 0;
    padding: 0;
    min-width: 0;
    max-width: 100%;
  }
  .breadcrumb-list li {
    display: flex;
    align-items: baseline;
    gap: 0.4rem;
    min-width: 0;
  }
  /* The crumb text itself: AUTHOR · PLAY set in the reading face (Cardo) as
     plain links back out, on a quiet rule that takes the genre accent on
     hover (docs/mockups/2026-09-08-blend.html, `.dir-b .head .crumbs a`).
     Still ellipsizes rather than pushing the tools off the bar. */
  .bc-crumb {
    font-family: var(--font-english);
    font-weight: 400;
    font-size: 1rem;
    color: var(--text);
    text-decoration: none;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }
  .bc-crumb:hover { color: var(--accent); border-bottom-color: var(--accent); }
</style>
