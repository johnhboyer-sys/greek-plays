// Appends a Sitemap: line to dist/robots.txt, but only when the build has a
// real canonical origin (PUBLIC_SITE_ORIGIN), under the site's base
// (SITE_BASE). Staging (*.pages.dev) builds must never bake in a sitemap
// URL — see astro.config.mjs.
import { appendFileSync, existsSync } from 'node:fs';

import { siteParams } from '../../scripts/site-params.mjs';

const { site, base } = siteParams();
if (site) {
  const dist = 'dist/robots.txt';
  if (!existsSync(dist)) {
    console.error(`postbuild-robots: ${dist} not found`);
    process.exit(1);
  }
  appendFileSync(dist, `\nSitemap: ${site}${base}sitemap-index.xml\n`);
}
