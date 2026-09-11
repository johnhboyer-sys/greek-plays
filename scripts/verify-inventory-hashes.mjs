#!/usr/bin/env node
// Hard gate: every unambiguous SHA-256 declaration in sources/INVENTORY.md
// must match the file bytes currently on disk. Catches silent regeneration
// drift of translation JSON, patch files, and other pinned source artifacts.
//
// Parsing is conservative: a hash is only paired with a path when the
// association is unambiguous. Ambiguous mentions are printed as warnings
// and do not fail the gate. Mismatches and missing files exit nonzero.
//
// Zero dependencies (Node crypto + fs only).

import { createHash } from 'node:crypto';
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { dirname, join, relative, sep } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const INVENTORY = join(ROOT, 'sources', 'INVENTORY.md');
const HEX64 = /`([a-f0-9]{64})`/g;
const PATH_IN_BACKTICKS =
  /`((?:sources\/|pipeline\/)?[A-Za-z0-9][A-Za-z0-9_./-]*\.[A-Za-z0-9]+)`/g;

/**
 * @typedef {{ path: string, expected: string, where: string, hintDirs?: string[] }} Entry
 */

function sha256File(absPath) {
  return createHash('sha256').update(readFileSync(absPath)).digest('hex');
}

/** Walk sources/ + pipeline/ for basename hits (skip junk dirs). */
function findByBasename(basename, root = ROOT) {
  const hits = [];
  const roots = [join(root, 'sources'), join(root, 'pipeline')];
  const skip = new Set(['node_modules', '__pycache__', '.git', 'dist', 'build']);

  function walk(dir) {
    let names;
    try {
      names = readdirSync(dir);
    } catch {
      return;
    }
    for (const name of names) {
      if (skip.has(name)) continue;
      const full = join(dir, name);
      let st;
      try {
        st = statSync(full);
      } catch {
        continue;
      }
      if (st.isDirectory()) walk(full);
      else if (name === basename) hits.push(full);
    }
  }
  for (const r of roots) {
    if (existsSync(r)) walk(r);
  }
  return hits;
}

/**
 * Resolve a repo-relative or sources-relative path declaration to a single
 * absolute file path, or null if zero/many matches.
 * @returns {{ abs: string, rel: string } | null}
 */
function resolvePath(declared, hintDirs = [], root = ROOT) {
  const raw = declared.replace(/^`|`$/g, '').trim();
  const candidates = [];

  if (raw.startsWith('sources/') || raw.startsWith('pipeline/')) {
    candidates.push(join(root, raw));
  } else if (raw.includes('/')) {
    candidates.push(join(root, 'sources', raw), join(root, raw));
  } else {
    const hits = findByBasename(raw, root);
    if (hits.length === 1) {
      return { abs: hits[0], rel: relative(root, hits[0]).split(sep).join('/') };
    }
    if (hits.length > 1 && hintDirs.length) {
      const narrowed = hits.filter((h) =>
        hintDirs.some(
          (d) => h.includes(`${sep}${d}${sep}`) || h.includes(`/${d}/`) || h.endsWith(`${sep}${d}`),
        ),
      );
      if (narrowed.length === 1) {
        return {
          abs: narrowed[0],
          rel: relative(root, narrowed[0]).split(sep).join('/'),
        };
      }
    }
    return null;
  }

  const existing = [...new Set(candidates.filter((c) => existsSync(c) && statSync(c).isFile()))];
  if (existing.length !== 1) return null;
  return { abs: existing[0], rel: relative(root, existing[0]).split(sep).join('/') };
}

/** Collect nearby directory segments from path-like backticks in a line range. */
function nearbyDirs(lines, from, to) {
  const dirs = new Set();
  for (let i = Math.max(0, from); i < Math.min(lines.length, to); i++) {
    for (const m of lines[i].matchAll(PATH_IN_BACKTICKS)) {
      const p = m[1];
      const parts = p.split('/');
      if (parts.length >= 2) {
        dirs.add(parts[0] === 'sources' || parts[0] === 'pipeline' ? parts[1] : parts[0]);
      }
    }
  }
  return [...dirs];
}

function extractPaths(cell) {
  const paths = [];
  for (const m of cell.matchAll(PATH_IN_BACKTICKS)) paths.push(m[1]);
  return paths;
}

function extractHashes(cell) {
  const hashes = [];
  for (const m of cell.matchAll(HEX64)) hashes.push(m[1]);
  return hashes;
}

/**
 * Parse INVENTORY.md into unambiguous {path, expected, where} entries.
 * Ambiguous hash mentions go to warnings (not errors).
 */
export function parseInventory(text) {
  /** @type {Entry[]} */
  const entries = [];
  /** @type {string[]} */
  const warnings = [];
  const paired = new Set();
  const lines = text.split(/\r?\n/);

  function add(path, expected, where) {
    if (paired.has(expected)) return;
    paired.add(expected);
    entries.push({ path, expected, where });
  }

  function markAmbiguous(hash, where, reason) {
    if (paired.has(hash)) return;
    // Don't double-warn the same hash.
    paired.add(hash);
    warnings.push(`${where}: skipped ambiguous hash ${hash.slice(0, 12)}… (${reason})`);
  }

  // --- Pattern A: `path` (SHA-256 `hash`) ---
  {
    const re =
      /`((?:sources\/|pipeline\/)?[A-Za-z0-9][A-Za-z0-9_./-]*\.[A-Za-z0-9]+)`\s*\(SHA-256\s+`([a-f0-9]{64})`\)/g;
    let m;
    while ((m = re.exec(text))) {
      const lineNo = text.slice(0, m.index).split(/\r?\n/).length;
      add(m[1], m[2], `L${lineNo} paren-form`);
    }
  }

  // --- Pattern B: `path` … SHA-256 `hash` (same line / cell) ---
  {
    const re =
      /`((?:sources\/|pipeline\/)?[A-Za-z0-9][A-Za-z0-9_./-]*\.[A-Za-z0-9]+)`[^`|\n]{0,120}?SHA-256\s+`([a-f0-9]{64})`/g;
    let m;
    while ((m = re.exec(text))) {
      if (paired.has(m[2])) continue;
      const lineNo = text.slice(0, m.index).split(/\r?\n/).length;
      add(m[1], m[2], `L${lineNo} inline`);
    }
  }

  // --- Pattern C: | SHA-256 (basename.ext) | `hash` | ---
  {
    const re = /SHA-256\s+\(([^)|]+\.[A-Za-z0-9]+)\)\s*\|\s*`([a-f0-9]{64})`/g;
    let m;
    while ((m = re.exec(text))) {
      if (paired.has(m[2])) continue;
      const lineNo = text.slice(0, m.index).split(/\r?\n/).length;
      add(m[1].trim(), m[2], `L${lineNo} label-basename`);
    }
  }

  // --- Pattern D: table rows — File/Files path cells paired with SHA-256 cells ---
  // Walk the whole table: remember the most recent File/Files path cells, then
  // pair any later SHA-256 row in the same table by column (and raw/clean labels).
  let tablePathCells = null; // string[][] | null
  let inTable = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed.startsWith('|')) {
      inTable = false;
      tablePathCells = null;
      continue;
    }

    // Header separator |---|---|
    if (/^\|[\s:|-]+\|$/.test(trimmed.replace(/\s/g, '')) || /^\|[-:| ]+\|$/.test(trimmed)) {
      inTable = true;
      continue;
    }

    inTable = true;
    const cells = trimmed
      .replace(/^\|/, '')
      .replace(/\|$/, '')
      .split('|')
      .map((c) => c.trim());
    const label = cells[0] || '';

    if (/^Files?$/i.test(label)) {
      tablePathCells = cells.slice(1).map(extractPaths);
      continue;
    }

    if (!/^SHA-256/i.test(label)) continue;
    if (!tablePathCells) {
      // Bare SHA-256 row without a preceding File row in this table — may still
      // be Pattern C (basename in label), already handled. Any leftover hashes
      // without paths will be warned at the end.
      continue;
    }

    const hashCells = cells.slice(1).map(extractHashes);
    const labelKind = (() => {
      const mm = label.match(/SHA-256\s*\(([^)]+)\)/i);
      return mm ? mm[1].toLowerCase() : '';
    })();

    // Basename already in label (Pattern C) — skip re-pairing here if already paired.
    if (/\.[A-Za-z0-9]+\)$/.test(label) || /\.[A-Za-z0-9]+\)/.test(label)) {
      // Pattern C form: SHA-256 (file.ext) — path is the basename, not table columns.
      continue;
    }

    const n = Math.max(tablePathCells.length, hashCells.length);
    for (let col = 0; col < n; col++) {
      const ps = tablePathCells[col] || [];
      const hs = hashCells[col] || [];
      if (hs.length === 0) continue;

      if (hs.length === 1 && ps.length === 1) {
        if (!paired.has(hs[0])) add(ps[0], hs[0], `L${i + 1} table-col`);
        continue;
      }

      // Multi-path Files cell + SHA-256 (raw) / (clean)
      if (hs.length === 1 && (ps.length >= 1 || tablePathCells.flat().length >= 1) && labelKind) {
        const allPaths = tablePathCells.flat();
        let cands = [];
        if (/\braw\b/.test(labelKind) && !/\bclean\b/.test(labelKind)) {
          cands = allPaths.filter((p) => {
            const base = p.split('/').pop() || '';
            return !/\.clean\./i.test(p) && !/clean/i.test(base);
          });
          const txts = cands.filter((p) => p.endsWith('.txt'));
          if (txts.length === 1) cands = txts;
        } else if (/\bclean\b/.test(labelKind)) {
          cands = allPaths.filter((p) => {
            const base = p.split('/').pop() || '';
            return /\.clean\./i.test(p) || /clean/i.test(base);
          });
        }

        if (cands.length === 1) {
          if (!paired.has(hs[0])) add(cands[0], hs[0], `L${i + 1} table-rawclean`);
        } else if (!paired.has(hs[0])) {
          markAmbiguous(hs[0], `L${i + 1}`, `raw/clean label matched ${cands.length} path(s)`);
        }
        continue;
      }

      if (hs.length === ps.length && hs.length > 1) {
        for (let k = 0; k < hs.length; k++) {
          if (!paired.has(hs[k])) add(ps[k], hs[k], `L${i + 1} table-zip`);
        }
        continue;
      }

      for (const h of hs) {
        if (!paired.has(h)) {
          markAmbiguous(h, `L${i + 1}`, `could not pair with a unique path in column ${col}`);
        }
      }
    }
  }

  // Remaining unpaired full hashes → warnings.
  {
    let m;
    const re = /`([a-f0-9]{64})`/g;
    while ((m = re.exec(text))) {
      if (paired.has(m[1])) continue;
      const lineNo = text.slice(0, m.index).split(/\r?\n/).length;
      markAmbiguous(m[1], `L${lineNo}`, 'no unambiguous path association');
    }
  }

  for (const e of entries) {
    if (e.path.includes('/')) continue;
    const lineNo = parseInt(e.where.match(/L(\d+)/)?.[1] || '1', 10);
    e.hintDirs = nearbyDirs(lines, lineNo - 12, lineNo + 2);
  }

  return { entries, warnings };
}

const SUMS_REF = /`((?:sources\/|pipeline\/)[A-Za-z0-9_./-]*SHA256SUMS)`/g;
const EMPTY_SOURCE_SET = /\bempty source set\b/i;

function referencedSumsFiles(text) {
  const found = [];
  const seen = new Set();
  SUMS_REF.lastIndex = 0;
  let m;
  while ((m = SUMS_REF.exec(text))) {
    if (seen.has(m[1])) continue;
    seen.add(m[1]);
    found.push(m[1]);
  }
  return found;
}

function parseSha256Sums(text) {
  const entries = [];
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const match = /^([a-fA-F0-9]{64})\s+\*?(\S.*)$/.exec(trimmed);
    if (!match) continue;
    entries.push({ expected: match[1].toLowerCase(), path: match[2].trim() });
  }
  return entries;
}

/**
 * Verify every unambiguous inventory entry against disk.
 * Astra lane B, F4: also read referenced SHA256SUMS files.
 */
export function verifyInventoryHashes(inventoryText = readFileSync(INVENTORY, 'utf8'), opts = {}) {
  const root = opts.root ?? ROOT;
  const { entries, warnings } = parseInventory(inventoryText);
  const problems = [];
  let verified = 0;
  const seen = new Set();
  let declarationCount = entries.length;

  for (const e of entries) {
    const resolved = resolvePath(e.path, e.hintDirs || [], root);
    if (!resolved) {
      const hits = e.path.includes('/') ? [] : findByBasename(e.path, root);
      if (hits.length > 1) {
        warnings.push(
          `${e.where}: skipped ${e.path} — resolves to ${hits.length} files; association ambiguous`,
        );
      } else {
        problems.push(`${e.where}: missing file for declared path ${e.path}`);
      }
      continue;
    }
    const actual = sha256File(resolved.abs);
    const key = `${resolved.rel}|${e.expected}`;
    if (seen.has(key)) continue;
    seen.add(key);

    if (actual !== e.expected) {
      problems.push(
        `${e.where}: HASH MISMATCH ${resolved.rel}\n` +
          `  expected ${e.expected}\n` +
          `  actual   ${actual}`,
      );
    } else {
      verified += 1;
    }
  }

  for (const sumsRel of referencedSumsFiles(inventoryText)) {
    const sumsAbs = join(root, sumsRel);
    if (!existsSync(sumsAbs) || !statSync(sumsAbs).isFile()) {
      problems.push(`missing SHA256SUMS file ${sumsRel}`);
      continue;
    }
    const listed = parseSha256Sums(readFileSync(sumsAbs, 'utf8'));
    declarationCount += listed.length;
    if (listed.length === 0) {
      problems.push(`${sumsRel}: no hash declarations`);
      continue;
    }
    const sumsDir = dirname(sumsAbs);
    for (const item of listed) {
      const abs = join(sumsDir, item.path);
      const rel = relative(root, abs).split(sep).join('/');
      if (!existsSync(abs) || !statSync(abs).isFile()) {
        problems.push(`${sumsRel}: missing file for declared path ${item.path}`);
        continue;
      }
      const actual = sha256File(abs);
      const key = `${rel}|${item.expected}`;
      if (seen.has(key)) continue;
      seen.add(key);
      if (actual !== item.expected) {
        problems.push(
          `${sumsRel}: HASH MISMATCH ${rel}\n` +
            `  expected ${item.expected}\n` +
            `  actual   ${actual}`,
        );
      } else {
        verified += 1;
      }
    }
  }

  const emptyDeclared = EMPTY_SOURCE_SET.test(inventoryText);
  if (verified === 0 && declarationCount === 0 && !emptyDeclared) {
    problems.push(
      'zero hash declarations; inventory must list SHA256SUMS files or declare an empty source set',
    );
  }

  return {
    ok: problems.length === 0 && (verified > 0 || emptyDeclared),
    verified,
    problems,
    warnings,
    entryCount: declarationCount,
  };
}

/** --self-test: exercise the mismatch failure path with an in-memory entry. */
function runSelfTest() {
  const realRel = 'sources/INVENTORY.md';
  const realAbs = join(ROOT, realRel);
  if (!existsSync(realAbs)) {
    console.error('self-test: sources/INVENTORY.md missing');
    process.exit(1);
  }
  const realHash = sha256File(realAbs);
  const fakeHash = '0'.repeat(64);

  const fabricated =
    `# self-test inventory\n\n` +
    `| | |\n|---|---|\n` +
    `| File | \`${realRel}\` |\n` +
    `| SHA-256 | \`${fakeHash}\` |\n`;

  const result = verifyInventoryHashes(fabricated);
  if (result.ok || result.problems.length === 0) {
    console.error('self-test FAIL: expected mismatch problems, got none');
    process.exit(1);
  }
  if (!result.problems.some((p) => p.includes('HASH MISMATCH'))) {
    console.error('self-test FAIL: expected a HASH MISMATCH problem, got:', result.problems);
    process.exit(1);
  }

  const good =
    `# self-test inventory good\n\n` +
    `| | |\n|---|---|\n` +
    `| File | \`${realRel}\` |\n` +
    `| SHA-256 | \`${realHash}\` |\n`;
  const goodResult = verifyInventoryHashes(good);
  if (!goodResult.ok || goodResult.verified !== 1) {
    console.error('self-test FAIL: positive control did not verify', goodResult);
    process.exit(1);
  }

  console.log('self-test OK: mismatch path demonstrated, then positive control verified');
  console.log(`  fabricated mismatch problems: ${result.problems.length}`);
  for (const p of result.problems) console.log(`  - ${p.split('\n')[0]}`);
  console.log(`  positive control verified: ${goodResult.verified}`);
  process.exit(0);
}

function main() {
  const args = process.argv.slice(2);
  if (args.includes('--self-test')) {
    runSelfTest();
    return;
  }

  if (!existsSync(INVENTORY)) {
    console.error(`INVENTORY not found: ${INVENTORY}`);
    process.exit(1);
  }

  console.log('Verifying sources/INVENTORY.md SHA-256 declarations');
  const result = verifyInventoryHashes();
  for (const w of result.warnings) console.warn(`  warning: ${w}`);
  console.log(
    `  ${result.verified} hash(es) verified (${result.entryCount} unambiguous declaration(s))`,
  );
  if (result.problems.length) {
    console.error(`  ${result.problems.length} problem(s):`);
    for (const p of result.problems) console.error(`  ${p}`);
    process.exit(1);
  }
  if (result.verified <= 20) {
    console.error(
      `  FAIL: verified count ${result.verified} is not > 20 (parser too conservative or inventory empty)`,
    );
    process.exit(1);
  }
  console.log('  OK');
  process.exit(0);
}

// CLI when invoked directly (not when imported by build-public.mjs).
if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) {
  main();
}
