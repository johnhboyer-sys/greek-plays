#!/usr/bin/env node
// Deploy a build of the plays to the Cloudflare Worker `greek-drama-reader`
// (app/wrangler.jsonc; docs/cloudflare.md). Node 22+, no dependencies beyond
// `npx wrangler@4`, which must be logged in to John's account for --deploy.
//
//   DRAMA_EDITIONS=1 PUBLIC_EDITIONS=1 PUBLIC_SITE_ORIGIN=https://greekdrama.johnhboyer.com npm run build:public
//   npm run deploy:cloudflare            — a rehearsal: every gate, then `wrangler deploy --dry-run`
//   npm run deploy:cloudflare -- --deploy — the gates, then the deploy, then the deploy tag
//
// Flags: --deploy  --dry-run (the default; refused beside --deploy)
//        --site=<url>  --min-pages-ratio=<0..1>  --skip-link-check  --no-tag  --help
//
// The site and its data are one folder, app/dist, served from the Worker's
// assets; the Worker's script answers /api/* (the feedback form). So the
// gates hold the folder to what the Worker can take and must serve: a
// same-origin build (no data root in sw.js), its data in the folder and not
// excluded from the upload, the feedback form's marker present, at most
// 20,000 files of at most 25 MiB each (the free plan's limits), at least
// --min-pages-ratio of live's sitemap pages, 0 broken links, and the data
// gates the mirror bundle runs (scripts/make-bundle.mjs dataGates: preflight
// --public --editions, the data contracts, the LSJ headwords, the lemma
// pages, JSON). After a deploy that succeeded, the commit is tagged
// deploy/<date> and the tag pushed to origin (release.yml builds that tag's
// bundle). A rehearsal never deploys and never tags.
//
// Nothing here has deployed for real yet (HANDOFF-PORTABILITY.md, phase 3):
// its every branch is tested with fakes (scripts/__tests__/deploy-cloudflare.test.mjs).
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import { HOST_FILES, builtDataRoot, dataGates } from './make-bundle.mjs';
import { parseLsRemote } from './mirror-check.mjs';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
export const ACCOUNT_ID = '6ff75c6d6c06d1092df2c7efd42077ba';
export const SITE = 'https://greekdrama.johnhboyer.com';
// Workers static assets, free plan (developers.cloudflare.com/workers/static-assets/).
export const MAX_FILES = 20000;
export const MAX_FILE_BYTES = 25 * 1024 * 1024;
// macOS Finder litter; never shipped.
export const SKIPPED_NAMES = new Set(['.DS_Store']);

export function parseArgs(argv) {
  const options = { deploy: false, dryRun: false, site: SITE, minPagesRatio: 0.9, skipLinkCheck: false, noTag: false, help: false };
  for (const arg of argv) {
    const [flag, value] = arg.split(/=(.*)/s);
    if (flag === '--deploy' && value === undefined) options.deploy = true;
    else if (flag === '--dry-run' && value === undefined) options.dryRun = true;
    else if (flag === '--skip-link-check' && value === undefined) options.skipLinkCheck = true;
    else if (flag === '--no-tag' && value === undefined) options.noTag = true;
    else if (flag === '--help' && value === undefined) options.help = true;
    else if (flag === '--site' && value) options.site = value.replace(/\/+$/, '');
    else if (flag === '--min-pages-ratio' && value !== undefined && value !== '' && !Number.isNaN(Number(value))) options.minPagesRatio = Number(value);
    else throw new Error(`unknown or incomplete flag: ${arg}`);
  }
  if (options.deploy && options.dryRun) throw new Error('--deploy and --dry-run together: say one');
  return options;
}

export function countSitemapPages(xml) {
  return (xml.match(/<loc>/g) ?? []).length;
}

// The build must carry at least `floor` of live's pages: a partial build
// would take most of the site down.
export function auditDistScale(distPages, livePages, floor) {
  if (!livePages || floor <= 0) return { ok: true };
  const minimum = Math.ceil(livePages * floor);
  if (distPages >= minimum) return { ok: true };
  return {
    ok: false,
    reason: `the dist has ${distPages} page(s) against ${livePages} live, below the ${Math.round(floor * 100)}% floor (${minimum}). Rebuild, or pass --min-pages-ratio=<0..1> if the shrink is deliberate.`,
  };
}

// Every file under `dir`, as { path, file, bytes } with `path` relative to
// `dir` and POSIX-separated. SKIPPED_NAMES never appear.
export function* walk(dir, base = dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (SKIPPED_NAMES.has(entry.name)) continue;
    const file = path.join(dir, entry.name);
    if (entry.isDirectory()) yield* walk(file, base);
    else yield { path: path.relative(base, file).split(path.sep).join('/'), file, bytes: statSync(file).size };
  }
}

// What app/dist must be for the Worker to serve the whole site: problems,
// empty when it is fit. `files` from walk(dist).
export function distProblems(dist, files) {
  const problems = [];
  const has = new Set(files.map((f) => f.path));
  if (!has.has('index.html')) return [`${dist} has no index.html; build first`];
  if (!has.has('sw.js')) problems.push('no sw.js in the build');
  else {
    const root = builtDataRoot(readFileSync(path.join(dist, 'sw.js'), 'utf8'));
    if (root === null) problems.push('sw.js has no DATA_ROOT line; app/public/sw.js has drifted');
    else if (root) problems.push(`the build reads its data from ${root}; the plays serve their data from the Worker itself. Rebuild with PUBLIC_DATA_ROOT unset`);
  }
  if (!files.some((f) => f.path.startsWith('data/'))) problems.push('no data/ in the build: the Worker serves the data');
  if (has.has('.assetsignore') && /^\/?data\/?$/m.test(readFileSync(path.join(dist, '.assetsignore'), 'utf8'))) {
    problems.push('.assetsignore leaves data/ out of the upload; the Worker serves the data');
  }
  for (const name of HOST_FILES) if (!has.has(name)) problems.push(`no ${name}: the feedback form would stay hidden on the primary`);
  if (files.length > MAX_FILES) problems.push(`${files.length} files, over the ${MAX_FILES} a Worker version may hold`);
  const big = files.filter((f) => f.bytes > MAX_FILE_BYTES);
  if (big.length) problems.push(`${big.length} file(s) over 25 MiB, which a Worker will not serve, first: ${big[0].path}`);
  return problems;
}

// Returns { tag } or { skip: why }. A second deploy on one day is <date>.2,
// then .3: one past the highest number either side holds.
// What it cannot know: that app/dist was built from `head`. A build made at
// one commit and deployed after a checkout of another is tagged at the other.
export function tagPlan({ unclean, noTag, head, tags, local = [], date }) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) throw new Error(`not a date: ${JSON.stringify(date)}`);
  if (noTag) return { skip: '--no-tag' };
  if (unclean.length) {
    return { skip: `the working tree had files git does not hold as committed (${unclean.slice(0, 3).join(', ')}${unclean.length > 3 ? `, and ${unclean.length - 3} more` : ''}), so no commit is known to be what was deployed` };
  }
  const already = [...tags].find(([name, commit]) => name.startsWith('deploy/') && commit === head);
  if (already) return { skip: `this commit is already tagged ${already[0]}` };
  const base = `deploy/${date}`;
  const today = [...tags.keys(), ...local].filter((name) => name === base || name.startsWith(`${base}.`));
  if (!today.length) return { tag: base };
  const last = Math.max(1, ...today.map((name) => Number(name.slice(base.length + 1)) || 1));
  return { tag: `${base}.${last + 1}` };
}

// `git ls-remote --tags` output to a Map of tag -> commit. An annotated tag
// has two lines, its own object and "<commit>\trefs/tags/<name>^{}"; the
// second is the commit.
export function tagCommits(lsRemote) {
  const tags = new Map();
  for (const [ref, object] of parseLsRemote(lsRemote)) {
    const peeled = ref.endsWith('^{}');
    const name = (peeled ? ref.slice(0, -3) : ref).replace(/^refs\/tags\//, '');
    if (peeled || !tags.has(name)) tags.set(name, object);
  }
  return tags;
}

// ---------------------------------------------------------------------------

export class Refusal extends Error {}
const fail = (message) => { throw new Refusal(message); };

function run(command, args, { cwd = ROOT, capture = false, env = {} } = {}) {
  const result = spawnSync(command, args, {
    cwd, env: { ...process.env, ...env }, encoding: 'utf8',
    stdio: capture ? ['ignore', 'pipe', 'pipe'] : 'inherit', maxBuffer: 256 * 1024 * 1024,
  });
  if (result.error) throw new Error(`${command} ${args.join(' ')}: ${result.error.message}`);
  if (result.status !== 0) throw new Error(`${command} ${args.join(' ')} failed with status ${result.status}${capture ? `\n${result.stderr}` : ''}`);
  return capture ? result.stdout : '';
}

// The files a deploy from `cwd` would carry that git does not hold as
// committed: changed tracked files and untracked ones alike (an untracked page
// is built and deployed). Untracked files are asked for by name, so a
// status.showUntrackedFiles setting cannot hide them; ignored build output
// (app/dist, build/) stays out.
export function uncleanFiles(cwd = ROOT, exec = run) {
  return exec('git', ['status', '--porcelain', '--untracked-files=all'], { cwd, capture: true })
    .split('\n').filter(Boolean).map((line) => line.slice(3));
}

// Tag `head` as tagPlan says and push the tag to origin. origin's tags are
// read with ls-remote, which writes nothing here, so a name another machine
// used today is not used again and no local tag can stand in the way of the
// read. A tag whose push fails is removed here, so the next deploy tries
// again; the error is thrown on.
export function tagDeploy({ cwd = ROOT, head, unclean, noTag, date, exec = run }) {
  const none = tagPlan({ unclean, noTag, head, tags: new Map(), date });
  if (none.skip) return none;   // nothing to ask origin
  const tags = tagCommits(exec('git', ['ls-remote', '--tags', 'origin', 'refs/tags/deploy/*'], { cwd, capture: true }));
  const local = exec('git', ['tag', '--list', 'deploy/*'], { cwd, capture: true }).split('\n').filter(Boolean);
  const plan = tagPlan({ unclean, noTag, head, tags, local, date });
  if (plan.tag) {
    exec('git', ['tag', plan.tag, head], { cwd, capture: true });
    try {
      exec('git', ['push', '--quiet', 'origin', `refs/tags/${plan.tag}`], { cwd, capture: true });
    } catch (error) {
      exec('git', ['tag', '--delete', plan.tag], { cwd, capture: true });
      throw error;
    }
  }
  return plan;
}

async function fetchText(url) {
  const r = await fetch(url, { redirect: 'follow' });
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  return r.text();
}

// The deploy, with every effect passed in so the tests can run each branch
// with fakes: `exec` runs a program (git, node, npx), `getText` fetches a
// page, `gates` runs the data gates, `log` prints, `today` names the day.
// Returns { deployed, tag?, skip? }; a gate that fails throws a Refusal.
export async function deploy(options, {
  root = ROOT, exec = run, getText = fetchText, gates = dataGates, log = console.log,
  today = () => new Date().toLocaleDateString('sv-SE'),
} = {}) {
  const heading = (text) => log(`\n== ${text}`);
  // Always app/dist: app/wrangler.jsonc deploys that folder and no other.
  const dist = path.join(root, 'app', 'dist');
  const wranglerEnv = { CLOUDFLARE_ACCOUNT_ID: ACCOUNT_ID };
  const real = options.deploy;

  heading('The build');
  if (!existsSync(path.join(dist, 'index.html'))) fail(`${dist} has no index.html; build first`);
  const files = [...walk(dist)];
  const problems = distProblems(dist, files);
  if (problems.length) fail(problems.join('; '));
  const head = exec('git', ['rev-parse', 'HEAD'], { cwd: root, capture: true }).trim();
  const unclean = uncleanFiles(root, exec);
  log(`  source ${head.slice(0, 10)}${unclean.length ? ` (${unclean.length} file(s) not as committed)` : ''}; ${files.length} files`);

  heading(`Scale: the build against ${options.site}`);
  const distPages = files.filter((f) => path.posix.basename(f.path) === 'index.html').length;
  const livePages = countSitemapPages(await getText(`${options.site}/sitemap-0.xml`));
  if (!livePages) fail(`${options.site}/sitemap-0.xml lists no pages; the scale check would examine nothing`);
  log(`  pages: ${distPages} index.html files in the build, ${livePages} in the live sitemap`);
  const scale = auditDistScale(distPages, livePages, options.minPagesRatio);
  if (!scale.ok) fail(scale.reason);

  if (!options.skipLinkCheck) {
    heading('Link integrity (must be 0 broken)');
    try { exec('node', [path.join(root, 'scripts', 'check-links.mjs'), dist], { cwd: root }); }
    catch (error) { fail(`link check did not pass: ${error.message}`); }
  }

  heading('Data gates (as the mirror bundle runs them)');
  const data = files.filter((f) => f.path.startsWith('data/'));
  const served = function* (filter) {
    for (const f of data) if (filter(path.posix.basename(f.path))) yield { path: f.path, text: readFileSync(f.file, 'utf8') };
  };
  const reports = gates(served, { dataDir: path.join(dist, 'data'), files: data.map((f) => f.path) });
  if (!reports.length) fail('no data gate ran');
  for (const [name, report] of reports) {
    if (!report.ok) fail(`${name} did not pass: ${report.problems.slice(0, 5).join('; ')}`);
    log(`  ${name}: ok`);
  }

  if (!real) {
    heading('Rehearsal: wrangler deploy --dry-run (nothing is uploaded, nothing tagged)');
    try { exec('npx', ['-y', 'wrangler@4', 'deploy', '--dry-run'], { cwd: path.join(root, 'app'), env: wranglerEnv }); }
    catch (error) { fail(`the rehearsal did not pass: ${error.message}`); }
    log('\n  Every gate passed. Run with --deploy to deploy.');
    return { deployed: false };
  }

  heading('Deploying to the Worker');
  exec('npx', ['-y', 'wrangler@4', 'deploy'], { cwd: path.join(root, 'app'), env: wranglerEnv });
  log(`\n  Deployed ${head.slice(0, 10)}. Check ${options.site}/ and a play's page.`);

  // The deploy is done; a tag that fails must not read as a deploy that failed.
  heading('Tagging the deploy');
  try {
    const plan = tagDeploy({ cwd: root, head, unclean, noTag: options.noTag, date: today(), exec });
    if (plan.skip) log(`  NOT TAGGED: ${plan.skip}. Releases and mirrors do not follow this deploy.`);
    else log(`  ${plan.tag} at ${head.slice(0, 10)}, pushed to origin`);
    return { deployed: true, ...plan };
  } catch (error) {
    log(`  NOT TAGGED: ${error.message}\n  The deploy itself succeeded. Releases and mirrors do not follow it until ${head.slice(0, 10)} has a deploy/<date> tag on origin:\n    git tag deploy/<date> ${head} && git push origin refs/tags/deploy/<date>`);
    return { deployed: true, skip: error.message };
  }
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    console.log(readFileSync(fileURLToPath(import.meta.url), 'utf8').split('\n').slice(1, 12).join('\n'));
    return;
  }
  await deploy(options);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    if (error instanceof Refusal) console.error(`\nDEPLOY REFUSED: ${error.message}`);
    else console.error(`\nDeploy failed: ${error.stack || error}`);
    process.exit(1);
  });
}
