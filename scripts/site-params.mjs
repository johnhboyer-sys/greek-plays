// The site's address as build parameters (HANDOFF-PORTABILITY.md, phase 2).
// Node 22+, no dependencies. Unset or empty, they give today's build: no
// canonical origin (and so no sitemap) and the root. app/astro.config.mjs,
// app/scripts/postbuild-robots.mjs and scripts/check-links.mjs read them
// here, so a build and its link check cannot disagree about the base.
//
//   PUBLIC_SITE_ORIGIN  the origin canonical links, cards and the sitemap
//                       name, like https://greekdrama.johnhboyer.com (the
//                       deploy sets it). Trailing slashes are dropped. A
//                       mirror keeps the primary's: its canonical links name
//                       the primary site.
//   SITE_BASE           the path the site is served under, like / or /plays/.
//
// The two the bundle itself reads are PUBLIC_DATA_ROOT (shared/lib/data.ts;
// unset, the data is under <base>/data on the site's own origin) and
// PUBLIC_GRAMMATA_LOOKUP (shared/lib/grammata.ts; unset, grammata.pages.dev).
export function siteParams(env = process.env) {
  const raw = env.PUBLIC_SITE_ORIGIN || '';
  let site;
  if (raw) {
    site = raw.replace(/\/+$/, '');
    const origin = URL.canParse(site) ? new URL(site) : null;
    if (!origin || !/^https?:$/.test(origin.protocol) || origin.origin !== site) {
      throw new Error(`PUBLIC_SITE_ORIGIN must be an origin like https://example.org, with no path: got ${JSON.stringify(raw)}`);
    }
  }
  const base = env.SITE_BASE || '/';
  if (!/^\/(?:[A-Za-z0-9_~-][A-Za-z0-9._~-]*\/)*$/.test(base)) {
    throw new Error(`SITE_BASE must start and end with "/", like / or /plays/: got ${JSON.stringify(base)}`);
  }
  return { site, base };
}

// Which pages the sitemap lists (app/astro.config.mjs): redirect shims
// (/texts/ aliases, /read/.../section-N/, /<author>/<work>/<line>/
// citations) and the client-only lexicon entry shell stay out (Codex
// pre-launch review, 2026-10-24). Paths are read below the base, so a
// mirror's sitemap lists the same pages (Grok's read of #18).
export function inSitemap(page, base = '/') {
  let path = new URL(page).pathname;
  if (base !== '/' && path.startsWith(base)) path = path.slice(base.length - 1);
  if (path.startsWith('/texts/') || /\/section-\d+\/?$/.test(path) || path.startsWith('/lemma/grc/entry')) return false;
  if (path.startsWith('/read/')) return true;
  const parts = path.split('/').filter(Boolean);
  return !(parts.length === 3 && parts[2] !== 'book');
}
