import { readFile, mkdir } from 'node:fs/promises';
import { join } from 'node:path';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { realpathSync } from 'node:fs';
import { walkFiles, visibleText, attrTexts, jsonStrings, parseArgs, writeReport, writeTsv, context, allowlist, allowed, finish, relativeFile } from './lib.mjs';

const pattern = /\b(?:plato|platonic|aristotle|philosoph\w*|lyceum|stephanus|bekker|meno|diogenes laertius|latin|lucretius|dialogues?|treatises?|socrat\w*|classical philosophy)\b|\bPHI\b/gi;
const images = ['.png','.jpg','.jpeg','.webp','.ico','.gif','.svg'];
function hits(rows, file, where, text, severity = 'fail') {
  for (const m of text.matchAll(pattern)) {
    if (m[0].toLowerCase() === 'phi' && m[0] !== 'PHI') continue;
    rows.push({ sweep:'s1', severity, category:'inherited identity', file, where, match:m[0], context:context(text, m.index, m[0].length) });
  }
}
export async function run(args = parseArgs()) {
  const rows = [], imageRows = [];
  const allow = (await allowlist()).s1;
  for await (const path of walkFiles(args.dist)) {
    const file = relativeFile(args.dist, path), ext = file.slice(file.lastIndexOf('.')).toLowerCase();
    if (images.includes(ext)) {
      const bytes = await readFile(path);
      imageRows.push({ file, bytes: bytes.length, sha256:createHash('sha256').update(bytes).digest('hex') });
    }
    if (ext === '.html') {
      const html = await readFile(path, 'utf8');
      hits(rows, file, 'text', visibleText(html));
      for (const attr of attrTexts(html)) hits(rows, file, `attr:${attr.name}`, attr.text);
    } else if (['.webmanifest','.txt','.xml'].includes(ext)) hits(rows, file, 'text', await readFile(path, 'utf8'));
    else if (ext === '.svg') {
      const svg = await readFile(path, 'utf8');
      for (const m of svg.matchAll(/<!--([\s\S]*?)-->|<(text|title|desc)\b[^>]*>([\s\S]*?)<\/\2>/gi)) hits(rows, file, 'text', visibleText(m[1] ?? m[3]));
    } else if (ext === '.json' && file.startsWith('data/')) {
      const json = JSON.parse(await readFile(path, 'utf8'));
      for (const item of jsonStrings(json)) {
        const keys = item.path.split(/[.\[\]]/).filter(Boolean);
        const identifier = keys.some(k => /^(scheme|id|kind|type|model|anchor_model)$/i.test(k) || /(?:Id|_id)$/.test(k));
        hits(rows, file, `json:${item.path}`, item.text, identifier ? 'info' : 'fail');
      }
    } else if (ext === '.js') {
      const js = await readFile(path, 'utf8');
      const grouped = new Map();
      for (const literal of js.matchAll(/'(?:\\.|[^'\\])*'|"(?:\\.|[^"\\])*"|`(?:\\.|[^`\\])*`/g)) {
        const text = literal[0].slice(1, -1);
        const found = [];
        hits(found, file, 'js', text, 'info');
        if (found.length) {
          const key = literal[0];
          const group = grouped.get(key) ?? { ...found[0], match:key, context:context(js, literal.index, literal[0].length), count:0 };
          group.count++;
          grouped.set(key, group);
        }
      }
      rows.push(...grouped.values());
    }
  }
  const kept = rows.filter(row => !allowed(row, allow.filter(entry => !entry.why.startsWith('Footer link text') || (row.where === 'text' && row.context.includes(entry.why.slice('Footer link text: '.length))))));
  await writeReport('s1-identity', kept, args.out);
  await mkdir(args.out, { recursive:true });
  await writeTsv(join(args.out, 's1-images.tsv'), imageRows, ['file','bytes','sha256']);
  finish('s1', kept);
  console.log(`s1 images: ${imageRows.length}`);
  return kept;
}
if (process.argv[1] && realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)) await run();
