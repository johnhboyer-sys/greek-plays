<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  export let edition: string;
  export let initialLocation: string | null = null;
  const dispatch = createEventDispatcher();
  onMount(() => {
    const state = globalThis as typeof globalThis & { __readerProbeMounts__?: number };
    state.__readerProbeMounts__ = (state.__readerProbeMounts__ ?? 0) + 1;
  });
</script>

<div data-testid="reader-probe" data-ed={edition} data-anchor={initialLocation ?? ''}>
  <button on:click={() => dispatch('editionChange', { trans: 'morshead', view: 'greek', loc: '1203' })}>same edition</button>
  <button on:click={() => dispatch('editionChange', { trans: 'morshead', view: 'both', loc: '1203' })}>new edition</button>
</div>
