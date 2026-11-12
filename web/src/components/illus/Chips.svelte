<script lang="ts">
  // The touch targets under a chart: one chip per choice (>= 64 px), the chosen one in the chart's colour.
  import { color } from '../../lib/palette';
  let { labels, sel = $bindable(0), on = 'butter' }: { labels: string[]; sel?: number; on?: string } = $props();
</script>

<div class="chips">
  {#each labels as l, i}
    <button class="chip pressable" class:on={sel === i} style:--on={color(on)} onclick={() => (sel = i)}>{l}</button>
  {/each}
</div>

<style>
  .chips { display: flex; flex-wrap: wrap; gap: 8px; }
  .chip { min-height: var(--touch); min-width: var(--touch); padding: 0 14px; border-radius: 999px; border: var(--outline) solid var(--ink);
          background: var(--paper); color: var(--ink); font: inherit; font-weight: 800; font-size: 15px; }
  .chip.on { background: var(--on); }
</style>
