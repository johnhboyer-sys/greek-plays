// Copy-citation for a play read in a non-reference Greek edition (plan §4.5):
// the text names the editor, and the URL carries `ed=` (a `?loc=` without `?ed=`
// means the TLG numbering). The reference edition ('tlg') stays as it was.
import { formatCopyCitationRange } from './citation';
import { readerHref } from './data';
import { getWork } from './works';

type Cite = { column: string; line?: number | null } | null;

// "H. W. Smyth" -> "Smyth"; "Denniston and Page" stays whole.
const surname = (editor: string) => editor.replace(/^(?:[A-Z]\.\s*)+/, '').trim();

export function editionCopyCitation(
  work: string, ed: string | null, start: Cite, end: Cite, book = 1, trans?: string,
): { text: string; url: string } | null {
  const text = formatCopyCitationRange(work, start, end);
  if (!text) return null;
  // readerHref throws for a work the registry lacks; the copy text must not.
  let url: URL;
  try { url = new URL(readerHref(work, { book, loc: start?.column ?? end?.column, trans }), 'https://reader.invalid'); }
  catch { return { text, url: '' }; }
  if (!ed || ed === 'tlg') return { text, url: url.pathname + url.search };
  url.searchParams.set('ed', ed);
  // "(Aesch. Ag. 1203, Smyth 1926)": editor and year (John, 2026-09-29).
  const edition = getWork(work)?.greekEditions?.find(item => item.id === ed);
  const name = edition?.editor ? [surname(edition.editor), edition.year].filter(Boolean).join(' ') : '';
  return {
    text: name ? text.replace(/\)$/, `, ${name})`) : text,
    url: url.pathname + url.search,
  };
}
