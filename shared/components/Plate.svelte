<script lang="ts">
  import { SPK_PALETTE_N } from '../lib/speaker-colors';

  // The play's opening plate — the first screen of the play-line reader,
  // above line 1 (P4, docs/p4-plan.md; the visual spec is the `.plate2`
  // block of docs/mockups/2026-09-08-blend.html: A's coloured band over
  // B's manuscript body with a scholia margin).
  //
  // Static: no state, no listeners, no hydration — ReaderShell renders it
  // server-side only. Every string comes from the registry or the book's
  // own speaker roster; this component writes no reader-facing copy of its
  // own beyond the six fixed labels below (John's wording, p4-plan: no
  // "how to read this" note, "Translations" never "bench").
  export let greekTitle: string | null = null;
  export let title: string;
  export let authorName: string;
  export let argument: string | null = null;
  // The paragraph under the argument: what happens, ending included
  // (REVIEW-CHECKLIST 12).
  export let synopsis: string | null = null;
  export let production: string | null = null;
  export let greekSource: string | null = null;
  export let translations: string[] = [];
  // "Cite as": the work's copy abbreviation and the printed extent of the
  // play, e.g. "Aesch. Ag. 1–1673" — the last PRINTED line (see
  // lastPrintedRef in shared/lib/citation.ts), not the last chunk start.
  // Both parts or nothing.
  export let copyAbbr: string | null = null;
  export let lastLine: string | null = null;
  // The cast, in order of appearance (the book's own speakerRoster), each
  // with its palette slot from assignSpeakerSlots — the SAME slot the
  // reader tints that speaker's lead-in with.
  export let persons: { name: string; slot: number }[] = [];
  // Anchor of line 1 (`#col-<first ref>`), so "Start reading →" scrolls
  // past the plate to the text.
  export let startHref: string;

  // A roster entry the pipeline numbered: Agamemnon's Elder 1 … Elder 12,
  // the chorus members who speak singly at 1348–71. Twelve "Elder" lines
  // would be twelve persons on the plate; they are one.
  const NUMBERED = /^(.+) (\d+)$/;

  // The cast as the plate prints it: each numbered family collapsed into a
  // single entry at its FIRST member's place, "Elders 1–12". A collapsed
  // entry has no slot of its own (its members hold different palette slots),
  // so its initial takes the plain --text-mid ink instead of a speaker
  // colour. Ordinal-word names ("First Innkeeper") are not numbered and are
  // never collapsed.
  $: cast = (() => {
    const size = new Map<string, number>();
    for (const p of persons) {
      const base = NUMBERED.exec(p.name)?.[1];
      if (base) size.set(base, (size.get(base) ?? 0) + 1);
    }
    const out: { key: string; label: string; slot: number | null }[] = [];
    const done = new Set<string>();
    for (const p of persons) {
      const m = NUMBERED.exec(p.name);
      const base = m?.[1];
      if (!base || (size.get(base) ?? 0) < 2) {
        out.push({ key: p.name, label: p.name, slot: p.slot });
        continue;
      }
      if (done.has(base)) continue;
      done.add(base);
      const ns = persons
        .map((q) => NUMBERED.exec(q.name))
        .filter((x): x is RegExpExecArray => !!x && x[1] === base)
        .map((x) => Number(x[2]));
      out.push({ key: base, label: `${base}s ${Math.min(...ns)}–${Math.max(...ns)}`, slot: null });
    }
    return out;
  })();

  // Registry copy is DRAFT until John approves it (p4-plan): the prefix is
  // stripped from the sentence and shown as a tag after it, so the plate
  // never presents unapproved copy as final.
  const DRAFT = /^DRAFT\s*[—–-]\s*/;
  $: draft = DRAFT.test(argument ?? '');
  $: argumentText = (argument ?? '').replace(DRAFT, '');
  $: synopsisDraft = DRAFT.test(synopsis ?? '');
  $: synopsisText = (synopsis ?? '').replace(DRAFT, '');
  $: citeAs = copyAbbr && lastLine ? `${copyAbbr} 1–${lastLine}` : null;
  // Defensive: a slot outside the palette would resolve to an undefined
  // custom property and paint the cast initial in the inherited ink.
  const slotVar = (slot: number) =>
    `--spk: var(--spk-${((slot % SPK_PALETTE_N) + SPK_PALETTE_N) % SPK_PALETTE_N})`;
</script>

<section class="plate" aria-labelledby="plate-title">
  <div class="plate-band">
    {#if greekTitle}<p class="plate-gt" lang="grc">{greekTitle}</p>{/if}
    <h2 class="plate-en" id="plate-title">{title}</h2>
    <p class="plate-au">{authorName}</p>
  </div>
  <div class="plate-body">
    <div class="plate-main">
      {#if argumentText}
        <p class="plate-arg">{argumentText}{#if draft}<span class="plate-draft">draft</span>{/if}</p>
      {/if}
      {#if synopsisText}
        <p class="plate-syn">{synopsisText}{#if synopsisDraft}<span class="plate-draft">draft</span>{/if}</p>
      {/if}
      {#if persons.length}
        <h3 class="plate-h">Persons</h3>
        <ul class="plate-cast">
          {#each cast as p (p.key)}
            <li style={p.slot == null ? '--spk: var(--text-mid)' : slotVar(p.slot)}>{p.label}</li>
          {/each}
        </ul>
      {/if}
    </div>
    <aside class="plate-margin">
      {#if production}<p><b>Production</b>{production}</p>{/if}
      {#if greekSource}<p><b>Greek text</b>{greekSource}</p>{/if}
      {#if translations.length}<p><b>Translations</b>{translations.join('; ')}</p>{/if}
      {#if citeAs}<p><b>Cite as</b>{citeAs}</p>{/if}
    </aside>
  </div>
</section>
