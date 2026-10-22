// The book a reader page renders, handed to the reader island outside its
// props. Astro serializes an island's props into the page as an HTML-escaped
// attribute, and its Svelte hydrator wraps them in a deep `$state` proxy, so
// every read of a play passed as a prop went through the proxy while the
// reader hydrated. Instead the page carries the book once, as JSON in a
// <script type="application/json" id={id}>, and the island takes it by id:
// on the server from the map the page filled (putBook), in the browser from
// that script element. The server's copy is dropped once taken, so a build
// of every play never holds more than the page in hand.
import type { BookData } from './data';

const serverBooks = new Map<string, BookData>();

export function putBook(id: string, data: BookData): void {
  serverBooks.set(id, data);
}

export function takeBook(id: string): BookData | null {
  if (typeof document === 'undefined') {
    const data = serverBooks.get(id) ?? null;
    serverBooks.delete(id);
    return data;
  }
  const el = document.getElementById(id);
  return el?.textContent ? (JSON.parse(el.textContent) as BookData) : null;
}
