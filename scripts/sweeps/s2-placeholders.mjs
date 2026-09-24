import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { realpathSync } from 'node:fs';
import { walkFiles, visibleText, attrTexts, jsonStrings, parseArgs, writeReport, context, allowlist, allowed, finish, relativeFile } from './lib.mjs';
const rules = [
  ['marker', /DRAFT|TODO|TBD|FIXME|XXX|\[object Object\]/g],
  ['bad value', /\b(?:undefined|NaN|null)\b/g],
  ['leftover entity', /&(?:[a-zA-Z]+|#\d+);/g],
  ['raw tag', /[<>](?=[a-zA-Z])/g],
  ['replacement character', /\uFFFD/g],
];
function scan(rows, file, where, text, data = false) {
  const checks = [...rules, ...(where === 'text' || data ? [['placeholder text', /\b(?:lorem|placeholder)\b/gi], ['brace', /[{}]/g]] : [])];
  for (const [category, regex] of checks) for (const m of text.matchAll(regex)) rows.push({ sweep:'s2', severity:'fail', category, file, where, match:m[0], context:context(text,m.index,m[0].length) });
  if (data) for (const m of text.matchAll(/\b([a-zA-Z]+)\s+\1\b/gi)) rows.push({ sweep:'s2', severity:'info', category:'repeated word', file, where, match:m[0], context:context(text,m.index,m[0].length) });
}
function structure(rows, file, html) {
  const add = (severity, category, match, at) => rows.push({ sweep:'s2', severity, category, file, where:'text', match, context:context(html,at,match.length) });
  for (const m of html.matchAll(/<title\b[^>]*>([\s\S]*?)<\/title>/gi)) if (!visibleText(m[1])) add('fail','empty title','<title>',m.index);
  for (const m of html.matchAll(/<h([1-6])\b[^>]*>([\s\S]*?)<\/h\1>/gi)) if (!visibleText(m[2])) add('fail','empty heading',`<h${m[1]}>`,m.index);
  for (const m of html.matchAll(/<a\b([^>]*)>([\s\S]*?)<\/a>/gi)) {
    const attrs = attrTexts(`<a ${m[1]}>`), inner = m[2];
    if (!visibleText(inner) && !attrs.some(a => a.name === 'aria-label' && a.text.trim()) && !/<img\b[^>]*\balt\s*=\s*(?:"[^"]+"|'[^']+'|[^\s>]+)/i.test(inner)) add('fail','empty link','<a>',m.index);
  }
  if (!/<h1\b/i.test(html)) add('info','no h1','<h1>',0);
}
export async function run(args = parseArgs()) {
  const rows = [], allow = (await allowlist()).s2;
  for await (const path of walkFiles(args.dist, ['.html','.json'])) {
    const file = relativeFile(args.dist,path);
    if (file.endsWith('.html')) {
      const html = await readFile(path,'utf8');
      scan(rows,file,'text',visibleText(html));
      for (const attr of attrTexts(html)) scan(rows,file,`attr:${attr.name}`,attr.text);
      structure(rows,file,html);
    } else if (file.startsWith('data/')) {
      for (const item of jsonStrings(JSON.parse(await readFile(path,'utf8')))) scan(rows,file,`json:${item.path}`,item.text,true);
    }
  }
  const kept = rows.filter(row => !allowed(row,allow));
  await writeReport('s2-placeholders',kept,args.out);
  finish('s2',kept);
  return kept;
}
if (process.argv[1] && realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)) await run();
