<script lang="ts">
  // The mascot with a line of text: empty states (a shrug), busy states (stirring, thinking), small celebrations.
  import Mascot from './Mascot.svelte';
  import type { Expr } from '../lib/mascot';
  let { text = '', act = null, loop = null, expr = 'neutral', size = 190, prop = null, breathe = true, restAfter = 0 }:
    { text?: string; act?: string | null; loop?: string | null; expr?: Expr; size?: number; prop?: 'cap' | 'chef' | null;
      breathe?: boolean; restAfter?: number } = $props();
  // restAfter (ms): blinks and glances for that long, then the face rests — for working screens (0 = always alive)
  let alive = $state(true);
  $effect(() => { if (!restAfter) return; const t = setTimeout(() => (alive = false), restAfter); return () => clearTimeout(t); });
</script>

<div class="note">
  <Mascot {size} {act} {loop} {expr} {prop} {breathe} {alive} />
  {#if text}<p>{text}</p>{/if}
</div>

<style>
  .note { display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 10px 20px 20px; text-align: center; }
  p { margin: 0; font-weight: 800; font-size: 19px; opacity: .75; max-width: 420px; }
</style>
