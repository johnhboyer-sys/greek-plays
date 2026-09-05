// Single source of truth for the site's display name — used in page titles,
// og:site_name, and JSON-LD across every page.
// app/public/manifest.webmanifest can't import this (it's static JSON, not
// JS) and duplicates SITE_NAME in its "name"/"short_name"/"description" —
// update it by hand whenever this changes.
export const SITE_NAME = 'The Greek Drama Reader';
