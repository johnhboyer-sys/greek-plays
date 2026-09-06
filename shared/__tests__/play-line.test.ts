import { describe, expect, it, vi } from 'vitest';

// schemeFor reads works.ts' citation.scheme; a fixture meta stands in for a
// real registry entry (mirrors citation.test.ts's own mocking pattern).
vi.mock('../lib/works', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/works')>();
  return {
    ...actual,
    getWork: (id: string) => {
      if (id === 'agamemnon') {
        return {
          id: 'agamemnon',
          abbr: 'Ag.',
          title: 'Agamemnon',
          books: 1,
          citation: { scheme: 'play-line', copyAbbr: 'Aesch. Ag.' },
        };
      }
      return actual.getWork(id);
    },
  };
});

import {
  PLAY_LINE_REF_SOURCE,
  isPlayLineRange,
  playLineOrderKey,
  scheme,
  schemeFor,
  formatCite,
  formatLocValue,
  formatCopyCitation,
  unitNounFor,
} from '../lib/citation';

describe('play-line scheme grammar (parity with scheme.py PLAY_LINE_REF_SOURCE)', () => {
  const s = scheme('play-line');

  it('accepts every grammar form', () => {
    for (const ref of ['1', '1234', '47a', '106-107', 'post 1226']) {
      expect(s.parseColumnToken(ref)).toBe(ref);
    }
  });

  it('rejects malformed forms', () => {
    for (const bad of ['', '1.101', '47A', '106--107', 'post1226', 'post  1226', '-1', '1-']) {
      expect(s.parseColumnToken(bad)).toBeNull();
    }
  });

  it('trims outer whitespace only', () => {
    expect(s.parseColumnToken(' 1234 ')).toBe('1234');
    expect(s.parseColumnToken('12 34')).toBeNull();
  });

  it('the regex SOURCE string is exactly what the Python side must byte-match', () => {
    // See pipeline/drama_pipeline/scheme.py's PLAY_LINE_REF_SOURCE — this is
    // the TS<->Python parity test's single source of truth for both sides.
    expect(PLAY_LINE_REF_SOURCE).toBe('^[0-9]+$|^[0-9]+[a-z]$|^[0-9]+-[0-9]+$|^post [0-9]+$');
  });
});

describe('isPlayLineRange / playLineOrderKey (mirrors scheme.py play_line_kind/play_line_order_key)', () => {
  it('classifies a range', () => {
    expect(isPlayLineRange('106-107')).toBe(true);
    expect(isPlayLineRange('1234')).toBe(false);
    expect(isPlayLineRange('post 1226')).toBe(false);
  });

  it('order key: leading integer, suffix after plain, post after everything at N, range at its start', () => {
    expect(playLineOrderKey('47')).toEqual([47, 0, '']);
    expect(playLineOrderKey('47a')).toEqual([47, 0, 'a']);
    expect(playLineOrderKey('post 1226')).toEqual([1226, 1, '']);
    // Ordering: 47 < 47a < 48; 1226 < post 1226 < 1227.
    const lt = (a: readonly [number, number, string], b: readonly [number, number, string]) =>
      a[0] < b[0] || (a[0] === b[0] && (a[1] < b[1] || (a[1] === b[1] && a[2] < b[2])));
    expect(lt(playLineOrderKey('47'), playLineOrderKey('47a'))).toBe(true);
    expect(lt(playLineOrderKey('47a'), playLineOrderKey('48'))).toBe(true);
    expect(lt(playLineOrderKey('1226'), playLineOrderKey('post 1226'))).toBe(true);
    expect(lt(playLineOrderKey('post 1226'), playLineOrderKey('1227'))).toBe(true);
  });

  it('throws on a malformed ref', () => {
    expect(() => playLineOrderKey('not-a-ref')).toThrow();
  });
});

describe('play-line parseLocation / formatCitation / formatLocValue', () => {
  const s = scheme('play-line');

  it('parseLocation returns the ref as-is with no separate line axis', () => {
    expect(s.parseLocation('1234')).toEqual({ column: '1234', line: null, isRange: false });
    expect(s.parseLocation('106-107')).toEqual({ column: '106-107', line: null, isRange: true });
    expect(s.parseLocation('not-a-ref')).toBeNull();
  });

  it('formatCitation returns the bare ref — the printed lineref IS the whole citation', () => {
    expect(s.formatCitation('1234')).toBe('1234');
    expect(s.formatCitation('1234', 5)).toBe('1234'); // a line arg is always ignored
  });

  it('formatLocValue produces the bare ref (no column prefix, no colon)', () => {
    expect(formatLocValue('agamemnon', '1234')).toBe('1234');
  });

  it('bookFromColumn is always 1 (bookless by construction — never null)', () => {
    // Deviation from makeFlatScheme's own bookFromColumn (always null): see
    // shared/lib/citation.ts's makePlayLineScheme doc comment for why a
    // play-line work's internal columns.json keys (each segment's own
    // first-line ref, stage1_greek.py's `_segment_play_lines`) are NOT the
    // citable ref space a reader jumps within, so CommandPalette/BekkerJump
    // must not fall back to a columns.json lookup for this scheme.
    expect(s.bookFromColumn('1234')).toBe(1);
    expect(s.bookFromColumn('anything')).toBe(1);
  });

  it('hasSections is false and hasUserFacingLines is false (the ref IS the whole address)', () => {
    expect(s.hasSections).toBe(false);
    expect(s.hasUserFacingLines).toBe(false);
  });
});

describe('play-line via schemeFor/formatCite/formatCopyCitation (a real work)', () => {
  it('formatCite round-trips a bare ref', () => {
    expect(formatCite('agamemnon', '1234')).toBe('1234');
  });

  it('formatCopyCitation uses the scholarly copyAbbr prefix', () => {
    expect(formatCopyCitation('agamemnon', '1234')).toBe('Aesch. Ag. 1234');
  });

  it('unitNounFor is "line"', () => {
    const n = unitNounFor('agamemnon');
    expect(n.singular).toBe('line');
    expect(n.plural).toBe('lines');
  });

  it('schemeFor resolves the play-line scheme', () => {
    expect(schemeFor('agamemnon').id).toBe('play-line');
  });
});
