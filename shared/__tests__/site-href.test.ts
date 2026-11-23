import { describe, expect, it } from 'vitest';
import { siteHref } from '../lib/edition-citation';

// Grok's read of #18: a citation copied from a Greek edition named the
// reader's path from the host's root, outside a mirror's base.
describe('siteHref', () => {
  it('puts a site path under the base', () => {
    expect(siteHref('/read/euripides/medea?ed=paley&loc=1', 'https://h.example', '/mirror/')).toBe('https://h.example/mirror/read/euripides/medea?ed=paley&loc=1');
    expect(siteHref('/read/euripides/medea', 'https://h.example', '/mirror')).toBe('https://h.example/mirror/read/euripides/medea');
  });
  it('at the root, is the address it always was', () => {
    expect(siteHref('/read/euripides/medea?loc=1', 'https://h.example', '/')).toBe('https://h.example/read/euripides/medea?loc=1');
  });
});
