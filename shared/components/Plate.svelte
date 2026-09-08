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
  export let production: string | null = null;
  export let greekSource: string | null = null;
  export let translations: string[] = [];
  // "Cite as": the work's copy abbreviation and the printed extent of the
  // play, e.g. "Aesch. Ag. 1–1672". Both parts or nothing.
  export let copyAbbr: string | null = null;
  export let lastLine: string | null = null;
  // The cast, in order of appearance (the book's own speakerRoster), each
  // with its palette slot from assignSpeakerSlots — the SAME slot the
  // reader tints that speaker's lead-in with.
  export let persons: { name: string; slot: number }[] = [];
  // Anchor of line 1 (`#col-<first ref>`), so "Start reading →" scrolls
  // past the plate to the text.
  export let startHref: string;

  // Registry copy is DRAFT until John approves it (p4-plan): the prefix is
  // stripped from the sentence and shown as a tag after it, so the plate
  // never presents unapproved copy as final.
  $: draft = /^DRAFT\s*[—–-]\s*/.test(argument ?? '');
  $: argumentText = (argument ?? '').replace(/^DRAFT\s*[—–-]\s*/, '');
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
      {#if persons.length}
        <h3 class="plate-h">Persons</h3>
        <ul class="plate-cast">
          {#each persons as p (p.name)}
            <li style={slotVar(p.slot)}>{p.name}</li>
          {/each}
        </ul>
      {/if}
      <a class="plate-go" href={startHref}>Start reading →</a>
    </div>
    <aside class="plate-margin">
      {#if production}<p><b>Production</b>{production}</p>{/if}
      {#if greekSource}<p><b>Greek text</b>{greekSource}</p>{/if}
      {#if translations.length}<p><b>Translations</b>{translations.join(' · ')}</p>{/if}
      {#if citeAs}<p><b>Cite as</b>{citeAs}</p>{/if}
    </aside>
  </div>
</section>
