import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
  normalizeWithMap,
  snippetForOffset,
  findSnippetRawIndex,
  nearestRowIndex,
  rowDistance,
  computeColumnIds,
} from '../sweeps/s15-keyed-placement.mjs';

// REVIEW-CHECKLIST 15 audit: the two pure algorithms behind the DOM
// measurement -- row-top distance counting, and whitespace-normalised text
// matching -- tested without a browser. The DOM Range/TreeWalker mechanics
// that use these (evalInPage, in the main script) need a real page and are
// exercised by the full crawl instead.

test('nearestRowIndex picks the row whose top is closest, ties keep the first', () => {
  const tops = [0, 20, 40, 60];
  assert.equal(nearestRowIndex(tops, 0), 0);
  assert.equal(nearestRowIndex(tops, 41), 2);
  assert.equal(nearestRowIndex(tops, 50), 2); // equidistant from 40 and 60 -> first
  assert.equal(nearestRowIndex(tops, 1000), 3);
});

test('rowDistance is 0 on the target row, signed away from it', () => {
  const tops = [0, 20, 40, 60, 80];
  assert.equal(rowDistance(tops, 2, 40), 0); // English lands on its own Greek row
  assert.equal(rowDistance(tops, 2, 0), -2); // English two rows early (above)
  assert.equal(rowDistance(tops, 2, 80), 2); // English two rows late (below)
  assert.equal(rowDistance(tops, 0, 20), 1);
});

test('normalizeWithMap collapses whitespace runs and keeps a reversible index map', () => {
  const { normalized, map } = normalizeWithMap('Then  the\n\nking   spoke.');
  assert.equal(normalized, 'Then the king spoke.');
  // Every normalized index maps back to a raw index holding that character.
  for (let i = 0; i < normalized.length; i++) {
    if (normalized[i] === ' ') continue;
    assert.equal('Then  the\n\nking   spoke.'[map[i]], normalized[i]);
  }
});

test('snippetForOffset returns a 30-char whitespace-normalised window at the offset', () => {
  const text = 'Then the elder king spoke and said: It is a hard fate to refuse obedience';
  const snippet = snippetForOffset(text, 0);
  assert.equal(snippet, 'Then the elder king spoke and ');
  assert.equal(snippet.length, 30);
});

test('snippetForOffset shrinks near the end of the chunk, and returns null below minLen', () => {
  const text = 'Then the elder king spoke and said, a rather long sentence indeed.';
  const nearEnd = snippetForOffset(text, text.length - 20);
  assert.equal(nearEnd, 'ong sentence indeed.'); // fewer than 30 chars left, so the window shrinks
  assert.equal(snippetForOffset(text, text.length - 3), null); // only 3 chars left, below minLen
});

test('snippetForOffset skips leading whitespace at the offset, same as the reader\'s own skipSpace', () => {
  const text = 'end of sentence.   Then the elder king spoke and said: more text here';
  const snippet = snippetForOffset(text, text.indexOf('   '));
  assert.equal(snippet.startsWith('Then the elder king'), true);
});

test('findSnippetRawIndex maps a normalised match back to its raw offset', () => {
  const text = 'Then  the\n\nking   spoke.';
  const idx = findSnippetRawIndex(text, 'the king spoke');
  assert.equal(idx, text.indexOf('the'));
});

test('findSnippetRawIndex returns -1 when the snippet is not present', () => {
  assert.equal(findSnippetRawIndex('Then the king spoke.', 'nobody home'), -1);
});

test('computeColumnIds gives the first segment at a column value the bare id, later ones a --k suffix', () => {
  const segments = [
    { column: '1' },
    { column: '40' },
    { column: '803' },
    { column: '804' },
    { column: '803' }, // Seven Against Thebes' doublet: two segments, one column value
  ];
  assert.deepEqual(computeColumnIds(segments), ['col-1', 'col-40', 'col-803', 'col-804', 'col-803--2']);
});

test('computeColumnIds handles three or more repeats of the same column', () => {
  const segments = [{ column: '5' }, { column: '5' }, { column: '5' }];
  assert.deepEqual(computeColumnIds(segments), ['col-5', 'col-5--2', 'col-5--3']);
});
