// HTML sanitizer for corpus-sourced markup rendered via {@html}/set:html.
//
// The HTML comes from the build pipeline, not from user input, so this is a
// supply-chain defence: a bad data file can emit only this small set of markup,
// never scripts, event handlers, or unsafe URLs. The entity decoding, stray-"<"
// escaping, and tag rule below are ported from aristotle-reader (25d0d67596,
// fb8afa978e; plato and homer carry the same), 2026-10-24.

const ALLOWED_TAGS = new Set([
  'a',
  'b',
  'br',
  'div',
  'em',
  'i',
  'li',
  'ol',
  'p',
  'span',
  'strong',
  'sub',
  'sup',
  'ul',
]);

const VOID_TAGS = new Set(['br']);

function escapeAttr(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function safeHref(value: string): string | null {
  const trimmed = value.trim();
  // Strip whitespace and control characters (\p{Cc} = C0 0x00-0x1F and DEL/C1
  // 0x7F-0x9F) before scheme-matching, so "java\tscript:" or a leading control
  // char can't slip a dangerous scheme past the prefix check.
  const normalized = trimmed.replace(/[\s\p{Cc}]+/gu, '').toLowerCase();
  if (
    normalized.startsWith('javascript:') ||
    normalized.startsWith('data:') ||
    normalized.startsWith('vbscript:')
  ) {
    return null;
  }
  return trimmed;
}

// An attribute value arrives as HTML source, entities and all, and leaves
// through escapeAttr, which escapes every "&" again: title="Smith &amp; Jones"
// reached the browser as "Smith &amp;amp; Jones" and showed the entity itself.
// Decoding first also puts the scheme check on what the browser would see —
// "&#106;avascript:" IS "javascript:" — instead of on its spelling. Only the
// entities the pipeline (and escapeAttr) write; anything else stays literal and
// is re-escaped, so no decoding can be undone twice.
const NAMED_ENTITY = new Map<string, string>([
  ['amp', '&'], ['lt', '<'], ['gt', '>'], ['quot', '"'], ['apos', "'"],
]);
// HTML's rules for a NUMERIC character reference, which are not "the code point
// you wrote". The C1 block 0x80-0x9F maps through a fixed table — &#128; is the
// euro sign, not U+0080 — and null, a lone surrogate and anything past the last
// plane become U+FFFD. Returning the raw code point put a corrupt character in
// the value, and escaping afterwards cannot repair it.
const C1_REPLACEMENT: Record<number, number> = {
  0x80: 0x20ac, 0x82: 0x201a, 0x83: 0x0192, 0x84: 0x201e, 0x85: 0x2026,
  0x86: 0x2020, 0x87: 0x2021, 0x88: 0x02c6, 0x89: 0x2030, 0x8a: 0x0160,
  0x8b: 0x2039, 0x8c: 0x0152, 0x8e: 0x017d, 0x91: 0x2018, 0x92: 0x2019,
  0x93: 0x201c, 0x94: 0x201d, 0x95: 0x2022, 0x96: 0x2013, 0x97: 0x2014,
  0x98: 0x02dc, 0x99: 0x2122, 0x9a: 0x0161, 0x9b: 0x203a, 0x9c: 0x0153,
  0x9e: 0x017e, 0x9f: 0x0178,
};
const REPLACEMENT = 0xfffd;
function numericRef(cp: number): number {
  if (!Number.isFinite(cp) || cp === 0 || cp > 0x10ffff) return REPLACEMENT;
  if (cp >= 0xd800 && cp <= 0xdfff) return REPLACEMENT;   // lone surrogate
  return C1_REPLACEMENT[cp] ?? cp;
}

function decodeEntities(value: string): string {
  if (!value.includes('&')) return value;
  return value.replace(/&(?:#x([0-9a-f]{1,6})|#(\d{1,7})|([a-z]+));/gi, (m, hex, dec, named) => {
    if (named) return NAMED_ENTITY.get(named.toLowerCase()) ?? m;
    const cp = hex ? parseInt(hex, 16) : Number(dec);
    return String.fromCodePoint(numericRef(cp));
  });
}

function sanitizeAttrs(raw: string, tag: string): string {
  const attrs: string[] = [];
  // The unquoted alternative deliberately allows '='. Authoring rules forbid it
  // there, but the tokenizer's unquoted-value state runs to whitespace or '>'
  // and keeps the character: the browser reads href=/search?q=greek whole,
  // where excluding '=' made this sanitizer emit /search?q and change the link.
  // The NAME alternative still stops at '=', which is what ends a name.
  const attrRe = /([^\s"'<>/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'<>`]+)))?/g;
  let match: RegExpExecArray | null;
  while ((match = attrRe.exec(raw))) {
    const name = match[1].toLowerCase();
    const value = decodeEntities(match[2] ?? match[3] ?? match[4] ?? '');
    if (name.startsWith('on')) continue;

    if (name === 'class' && /^[\w -]+$/.test(value)) {
      attrs.push(`class="${escapeAttr(value)}"`);
    } else if (name === 'href' && tag === 'a') {
      const href = safeHref(value);
      if (href) attrs.push(`href="${escapeAttr(href)}"`);
    } else if (name === 'data-level' && /^\d{1,2}$/.test(value)) {
      // Sense depth, the hook the hierarchy styling indents from. Digits only:
      // the value reaches CSS as an attribute selector, never as markup.
      attrs.push(`data-level="${value}"`);
    } else if (name === 'title' || name === 'aria-label') {
      attrs.push(`${name}="${escapeAttr(value)}"`);
    } else if (name === 'style' && tag === 'span' && /^\s*font-variant\s*:\s*small-caps\s*;?\s*$/i.test(value)) {
      attrs.push('style="font-variant: small-caps"');
    }
  }
  return attrs.length ? ` ${attrs.join(' ')}` : '';
}

// A tag is what the HTML tokenizer calls a tag: "<" or "</" followed AT ONCE by
// a letter, through to the next ">". Allowing whitespace after the "<" (as this
// did until 2026-09-07) read "a < b and c > d" as a <b> element and ate the
// prose between; the browser shows that as text, and so does this now.
//
// Every "<" the tag pass leaves behind is escaped. The output is not always
// mounted on its own: renderLsjEntry and the forms block concatenate more
// markup after it, and set:html splices it into a server-rendered page. A
// trailing `<a href=x onclick=alert(1)` with no ">" — which the tag pass
// cannot match — passed through verbatim and closed itself on whatever came
// next, `</div>` included, into a live handler. As text it is "&lt;a href…",
// which is what the parser would have shown for it anyway. A stray "<!" or
// "<?" likewise opened a bogus comment that hid everything up to the next ">".
export function sanitizeHtml(html: string): string {
  return html
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/<(script|style|iframe|object|embed)\b[\s\S]*?<\/\1\s*>/gi, '')
    .replace(/<(\/?)([a-z][\w:-]*)([^>]*)>|</gi, (full, slash, rawTag, rawAttrs) => {
      if (rawTag === undefined) return '&lt;';
      const tag = rawTag.toLowerCase();
      if (!ALLOWED_TAGS.has(tag)) return '';
      if (slash) return VOID_TAGS.has(tag) ? '' : `</${tag}>`;
      return `<${tag}${sanitizeAttrs(rawAttrs ?? '', tag)}>`;
    });
}
