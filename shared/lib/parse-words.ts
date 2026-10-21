// A parse in words for the word panel (UI pass 2, docs/redesign/
// HANDOFF-ui-pass2-build.md §7.6: "the morphology in words ('aorist indicative
// active, third singular')"). The analyses carry Morpheus' abbreviations
// ("aor ind act 3rd sg"); each is spelled out, a slash-joined set word by
// word ("nom/voc" → "nominative/vocative"), and a comma set before the person,
// gender, or case that follows a verb's tense, mood, and voice. A word with
// no spelling of its own is kept as printed.
const WORDS: Record<string, string> = {
  pres: 'present', imperf: 'imperfect', fut: 'future', aor: 'aorist', perf: 'perfect',
  plup: 'pluperfect', futperf: 'future perfect',
  ind: 'indicative', subj: 'subjunctive', opt: 'optative', imperat: 'imperative',
  inf: 'infinitive', part: 'participle',
  act: 'active', mid: 'middle', pass: 'passive', mp: 'middle or passive',
  '1st': 'first', '2nd': 'second', '3rd': 'third',
  sg: 'singular', pl: 'plural', dual: 'dual',
  masc: 'masculine', fem: 'feminine', neut: 'neuter',
  nom: 'nominative', gen: 'genitive', dat: 'dative', acc: 'accusative', voc: 'vocative',
  comp: 'comparative', superl: 'superlative',
  prep: 'preposition', conj: 'conjunction', exclam: 'exclamation', interrog: 'interrogative',
  indecl: 'indeclinable', indeclform: 'indeclinable', contr: 'contracted',
  a_priv: 'alpha privative',
};
const VERBAL = new Set(['pres', 'imperf', 'fut', 'aor', 'perf', 'plup', 'futperf', 'ind', 'subj', 'opt', 'imperat', 'inf', 'part', 'act', 'mid', 'pass', 'mp']);
const AGREEMENT = new Set(['1st', '2nd', '3rd', 'masc', 'fem', 'neut', 'nom', 'gen', 'dat', 'acc', 'voc']);

export function parseInWords(parse: string): string {
  const tokens = parse.trim().split(/\s+/).filter(Boolean);
  let out = '';
  let verbal = false;
  let comma = false;
  tokens.forEach((token, i) => {
    const parts = token.split('/');
    const word = parts.map((p) => WORDS[p] ?? p).join('/');
    // The comma falls once, before the first person, gender or case after a
    // tense, mood or voice.
    if (i > 0) out += verbal && !comma && AGREEMENT.has(parts[0]!) ? ', ' : ' ';
    if (i > 0 && verbal && AGREEMENT.has(parts[0]!)) comma = true;
    if (VERBAL.has(parts[0]!)) verbal = true;
    out += word;
  });
  return out;
}
