// LSJ entries are the one place in the corpus where the markup carries an
// ARGUMENT: LSJ's A → I → 1 → a hierarchy is how the lexicon divides a word's
// senses. Until 2026-08-19 the sanitizer dropped every <div>, so the hierarchy
// never reached the page — the stylesheet's .lsj-sense rules had nothing to
// match and entries rendered as one wall of prose. These lock the structure in.
//
// The rendering that used to sit on top of this (outlineLsjSenses,
// stampSenseDepth, prefixLsjCitationHrefs, renderLsjEntry) is gone: every LSJ
// entry the site shows is now Grammata's T8 widget (CLAUDE.md, "Dictionary"),
// never local HTML — see shared/components/WordPopup.svelte and
// app/src/components/LemmaEntry.svelte. sanitizeHtml itself stays live (it
// sanitizes corpus HTML generally, not just LSJ shards), so its coverage
// stays here.
import { describe, expect, it } from 'vitest';
import { sanitizeHtml } from '../lib/html';

// The shape stage5_lsj.py emits (nested senses, sense number in a leading <b>).
const ENTRY = [
  '<b class="lsj-head">λόγος</b>, <span class="lsj-gen">ὁ</span>, ',
  '<div class="lsj-sense" data-level="1"><b class="lsj-sense-n">A.</b> ',
  'computation, reckoning ',
  '<div class="lsj-sense" data-level="2"><b class="lsj-sense-n">I.</b> ',
  'account of money handled ',
  '<div class="lsj-sense" data-level="3"><b class="lsj-sense-n">2.</b> ',
  'generally, <i>account</i> ',
  '<a class="lsj-bibl" href="/EN/book/1?loc=1094a:5">1094a5</a>',
  '</div></div></div>',
  '<div class="lsj-sense" data-level="1"><b class="lsj-sense-n">B.</b> ',
  'relation, correspondence &amp; proportion</div>',
  '<div class="lsj-sense" data-level="1"><b class="lsj-sense-n">C.</b> ',
  'explanation</div>',
].join('');

describe('sanitizeHtml on LSJ sense structure', () => {
  it('keeps the sense divs and their depth', () => {
    const out = sanitizeHtml(ENTRY);
    // The sanitizer alone: data-depth is stamped later, by renderLsjEntry.
    expect(out).toContain('<div class="lsj-sense" data-level="1">');
    expect(out).toContain('<div class="lsj-sense" data-level="3">');
    // Nesting survives: three opens before the first close.
    expect(out.indexOf('data-level="3"')).toBeLessThan(out.indexOf('</div>'));
    expect(out.match(/<\/div>/g)).toHaveLength(5);
  });

  it('accepts data-level only as a small integer', () => {
    expect(sanitizeHtml('<div data-level="12">x</div>')).toBe('<div data-level="12">x</div>');
    for (const bad of ['foo', '', '123', '-1', '1 2', '1;background:red']) {
      expect(sanitizeHtml(`<div data-level="${bad}">x</div>`)).toBe('<div>x</div>');
    }
    // A quote closed early inside the value cannot smuggle a second attribute:
    // the parser sees data-level="1" and a separate onload, which is dropped.
    expect(sanitizeHtml('<div data-level="1"onload="steal()">x</div>'))
      .toBe('<div data-level="1">x</div>');
  });

  it('still refuses script, handlers and other data-* attributes', () => {
    expect(sanitizeHtml('<div onclick="steal()" data-href="/x">x</div>'))
      .toBe('<div>x</div>');
    expect(sanitizeHtml('<div><script>alert(1)</script>ok</div>'))
      .toBe('<div>ok</div>');
  });
});
