// The Beta Code chart: the letters, the marks, and examples, as the search's
// "How to type Greek" help printed them; drawn on the How to search page
// (app/src/pages/search/how.astro, UI pass 2). Keys are the same letters the
// search index uses, so anything typed here matches directly.
export const BETA_LETTERS: { beta: string; greek: string; name: string }[] = [
  { beta: 'a', greek: 'α', name: 'alpha' },
  { beta: 'b', greek: 'β', name: 'beta' },
  { beta: 'g', greek: 'γ', name: 'gamma' },
  { beta: 'd', greek: 'δ', name: 'delta' },
  { beta: 'e', greek: 'ε', name: 'epsilon' },
  { beta: 'z', greek: 'ζ', name: 'zeta' },
  { beta: 'h', greek: 'η', name: 'eta' },
  { beta: 'q', greek: 'θ', name: 'theta' },
  { beta: 'i', greek: 'ι', name: 'iota' },
  { beta: 'k', greek: 'κ', name: 'kappa' },
  { beta: 'l', greek: 'λ', name: 'lambda' },
  { beta: 'm', greek: 'μ', name: 'mu' },
  { beta: 'n', greek: 'ν', name: 'nu' },
  { beta: 'c', greek: 'ξ', name: 'xi' },
  { beta: 'o', greek: 'ο', name: 'omicron' },
  { beta: 'p', greek: 'π', name: 'pi' },
  { beta: 'r', greek: 'ρ', name: 'rho' },
  { beta: 's', greek: 'σ / ς', name: 'sigma' },
  { beta: 't', greek: 'τ', name: 'tau' },
  { beta: 'u', greek: 'υ', name: 'upsilon' },
  { beta: 'f', greek: 'φ', name: 'phi' },
  { beta: 'x', greek: 'χ', name: 'chi' },
  { beta: 'y', greek: 'ψ', name: 'psi' },
  { beta: 'w', greek: 'ω', name: 'omega' },
];

// Diacritics are typed AFTER the vowel. They're stripped before matching,
// so they're optional — but they show how full Beta Code is written.
export const BETA_MARKS: { beta: string; example: string; name: string }[] = [
  { beta: ')', example: 'a) → ἀ', name: 'smooth breathing' },
  { beta: '(', example: 'a( → ἁ', name: 'rough breathing' },
  { beta: '/', example: 'a/ → ά', name: 'acute accent' },
  { beta: '\\', example: 'a\\ → ὰ', name: 'grave accent' },
  { beta: '=', example: 'a= → ᾶ', name: 'circumflex' },
  { beta: '|', example: 'a| → ᾳ', name: 'iota subscript' },
  { beta: '+', example: 'i+ → ϊ', name: 'diaeresis' },
];

export const BETA_EXAMPLES: { beta: string; greek: string }[] = [
  { beta: 'a)reth/', greek: 'ἀρετή' },
  { beta: 'lo/gos', greek: 'λόγος' },
  { beta: 'yuxh/', greek: 'ψυχή' },
  { beta: 'h(donh/', greek: 'ἡδονή' },
  { beta: 'eu)daimoni/a', greek: 'εὐδαιμονία' },
  { beta: 'fron*', greek: 'φρόν… (wildcard)' },
];
