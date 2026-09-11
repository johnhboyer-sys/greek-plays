// P6 (docs/plan.md §6, Lyceum handoff): emit the Drama wing's `snapshot.v1`
// entry from the committed manifests, so the Lyceum Reader's catalog can mount
// this corpus without hand-authoring anything. Writes build/dist/wing.drama.json
// as a COMPLETE snapshot.v1 document holding the one wing (so it validates on
// its own with drama_pipeline.validate_contracts --snapshot); the Lyceum repo
// splices `wings[0]` into its own fixtures/snapshot.lyceum.json.
//
// Every membership note and featured blurb is the play's `registry.argument`
// verbatim -- DRAFT prefix included. Nothing here rewrites copy: the Lyceum
// prints exactly what the manifests carry, and the prefix comes off only when
// John approves a line in the manifest (REVIEW-CHECKLIST 12).
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadYaml, REPO_ROOT as ROOT } from './lib/load-yaml.mjs';

const MANIFESTS = join(ROOT, 'manifests');
const OUT = join(ROOT, 'build', 'dist', 'wing.drama.json');

// Featured: one play per author, the canonical first reads. Paths: the one
// trilogy the corpus carries whole, in performance order -- facts, not taste.
export const FEATURED = ['agamemnon', 'oedipus-tyrannus', 'bacchae', 'frogs'];
export const ORESTEIA = ['agamemnon', 'libation-bearers', 'eumenides'];

export function buildWing(authors, readManifest) {
  if (!Array.isArray(authors) || !authors.length) throw new Error('emit-wing: authors.yaml has no authors[]');

  const memberships = [];
  for (const author of authors) {
    for (const id of author.works ?? []) {
      const reg = readManifest(id).registry;
      if (!reg) throw new Error(`emit-wing: ${id} has no registry: block`);
      const note = typeof reg.argument === 'string' && reg.argument.trim() ? reg.argument.trim() : null;
      memberships.push(note ? { work: id, wing_note: note } : { work: id });
    }
  }

  // Astra lane B, F5: featured works and path stops are included only when
  // the work is a member. Zero members → valid empty snapshot, not a throw.
  const memberIds = new Set(memberships.map((x) => x.work));
  const argumentOf = (id) => memberships.find((x) => x.work === id)?.wing_note;

  const featured = FEATURED.filter((id) => memberIds.has(id)).map((work) => {
    const blurb = argumentOf(work);
    return blurb ? { work, blurb } : { work };
  });

  const stops = ORESTEIA.filter((id) => memberIds.has(id)).map((work) => {
    const note = argumentOf(work);
    const stop = { work, locus: '1' };
    if (note) stop.note = note;
    return stop;
  });
  const paths = [];
  if (stops.length) {
    paths.push({
      id: 'the-oresteia',
      title: 'The Oresteia',
      description: 'DRAFT — The one trilogy that survives whole, in the order it was played at the City Dionysia of 458 BC.',
      stops,
    });
  }

  const wing = {
    id: 'drama',
    name: 'Greek Drama',
    description: 'DRAFT — The forty-four surviving plays of Aeschylus, Sophocles, Euripides and Aristophanes, in Greek with public-domain English translations side by side.',
    corpora: ['drama'],
    memberships,
    featured,
    paths,
  };
  return wing;
}

const isMain = process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1]);
if (isMain) {
  const yaml = await loadYaml();
  const readYaml = (path) => yaml.load(readFileSync(path, 'utf8'));
  const authors = readYaml(join(MANIFESTS, 'authors.yaml')).authors;
  const wing = buildWing(authors, (id) => readYaml(join(MANIFESTS, `${id}.yaml`)));
  const snapshot = {
    schema_version: 'snapshot.v1',
    generated: new Date().toISOString(),
    wings: [wing],
  };
  mkdirSync(join(ROOT, 'build', 'dist'), { recursive: true });
  writeFileSync(OUT, JSON.stringify(snapshot, null, 2) + '\n');
  console.log(`emit-wing: wrote ${OUT}: ${wing.memberships.length} memberships, ${wing.featured.length} featured, ${wing.paths.length} path(s)`);
}
