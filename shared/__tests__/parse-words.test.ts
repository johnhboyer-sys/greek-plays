import { describe, expect, it } from 'vitest';
import { parseInWords } from '../lib/parse-words';

// The word panel's parse in words (UI pass 2, spec §7.6).
describe('parseInWords', () => {
  it('spells out a finite verb, the person and number after a comma', () => {
    expect(parseInWords('aor ind act 3rd sg')).toBe('aorist indicative active, third singular');
    expect(parseInWords('pres ind mp 2nd sg')).toBe('present indicative middle or passive, second singular');
  });

  it('puts the comma before a participle\'s gender and case', () => {
    expect(parseInWords('aor part act masc nom sg')).toBe('aorist participle active, masculine nominative singular');
  });

  it('spells out a noun with no comma, a slash set word by word', () => {
    expect(parseInWords('fem nom/voc/acc pl')).toBe('feminine nominative/vocative/accusative plural');
  });

  it('keeps an infinitive whole and a word it does not know as printed', () => {
    expect(parseInWords('pres inf act')).toBe('present infinitive active');
    expect(parseInWords('adverb')).toBe('adverb');
    expect(parseInWords('particle enclitic')).toBe('particle enclitic');
  });
});
