// Static copies of the vase drawings the site shows (see lib/drawings.ts).
import type { APIRoute } from 'astro';
import { homeFigureNames, servedSvg } from '../../lib/drawings';

export function getStaticPaths() {
  return homeFigureNames().map((name) => ({ params: { name } }));
}

export const GET: APIRoute = ({ params }) =>
  new Response(servedSvg(params.name!), { headers: { 'Content-Type': 'image/svg+xml' } });
