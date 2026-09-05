// @ts-check
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'astro/config';
import svelte from '@astrojs/svelte';

import sitemap from '@astrojs/sitemap';

// Deploys at the domain root (Cloudflare Pages) — no `base`. No real domain
// is registered yet, so `site` (the canonical origin, needed for
// @astrojs/sitemap's absolute URLs and for pages' Astro.site-derived
// canonical/og tags) is only set from PUBLIC_SITE_ORIGIN, and the sitemap
// integration is only included when it's set. This keeps any staging
// *.pages.dev origin out of the build entirely by default; pages already
// treat `Astro.site` as optional and omit the tags that need it.
// Trailing slash(es) stripped for consistency with data.ts and
// postbuild-robots.mjs's origin-concatenation idiom — an origin like
// "https://example.com/" would otherwise double up when Astro's sitemap
// integration (or a page) appends a path.
const siteOrigin = process.env.PUBLIC_SITE_ORIGIN?.replace(/\/+$/, '');

export default defineConfig({
  ...(siteOrigin ? { site: siteOrigin } : {}),
  integrations: [
    svelte(),
    ...(siteOrigin ? [sitemap()] : []),
  ],
  vite: {
    server: {
      fs: { allow: ['..'] },
    },
    resolve: {
      // The reader core (components, libs, global.css) lives in ../shared and
      // is consumed by both this site and the desktop app. See shared/README.md.
      alias: {
        '@shared': fileURLToPath(new URL('../shared', import.meta.url)),
      },
    },
  },
});