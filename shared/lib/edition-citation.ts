import { formatCopyCitationRange } from './citation';
import { readerHref } from './data';
import { getWork } from './works';

type Cite = { column: string; line?: number | null } | null;

export function editionCopyCitation(
  work: string, ed: string | null, start: Cite, end: Cite, book = 1, trans?: string,
): { text: string; url: string } | null {
  const text = formatCopyCitationRange(work, start, end);
  if (!text) return null;
  const loc = start?.column ?? end?.column;
  const url = new URL(readerHref(work, { book, loc, ed: ed ?? 'tlg', trans }), 'https://reader.invalid');
  if (ed && ed !== 'tlg') {
    url.searchParams.set('ed', ed);
    const editor = getWork(work)?.greekEditions?.find(item => item.id === ed)?.editor;
    return { text: editor ? `${text.slice(0, -1)} (${editor.trim().split(/\s+/).at(-1)}))` : text, url: url.pathname + url.search };
  }
  return { text, url: url.pathname + url.search };
}
