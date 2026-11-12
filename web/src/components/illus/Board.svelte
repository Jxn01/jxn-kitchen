<script lang="ts">
  // chart type `board`: a pantry board of grouped tags — e.g. the celiac grains: naturally GF · only with a GF label ·
  // never. Each group is one big touch target (its whole panel); the card under the board says what the chosen group
  // means, and the chosen panel lifts. Nothing is ever dimmed: on the celiac board 'never' must always read at full
  // strength. The tags pop in once, one after another.
  import { tx, type KBoard } from '../../lib/knowhow';
  import { color } from '../../lib/palette';
  import Icon from '../Icon.svelte';
  import Card from './Card.svelte';

  let { chart, lang }: { chart: KBoard; lang: 'en' | 'hu' } = $props();
  let sel = $state(0);
  let g = $derived(chart.groups[sel]);
  // up to three groups side by side, weighted by their size; four make a 2 × 2 (four columns overflow the kiosk)
  const cols = $derived(chart.groups.length > 3 ? '1fr 1fr' : chart.groups.map((x) => `minmax(172px, ${x.items.length + 4}fr)`).join(' '));
  // each tag's entrance delay: its position across the whole board, 32 ms apart
  const start = $derived(chart.groups.map((_, gi) => chart.groups.slice(0, gi).reduce((n, x) => n + x.items.length, 0)));
</script>

<div class="wrap">
  <div class="board" style:grid-template-columns={cols}>
    {#each chart.groups as grp, gi}
      <button class="grp pressable" class:on={sel === gi} style:--c={color(grp.color)} onclick={() => (sel = gi)}>
        <span class="head">{#if grp.icon}<Icon name={grp.icon} size={30} />{/if}<b>{tx(grp.label, lang)}</b></span>
        <span class="tags">
          {#each grp.items as it, i}
            <span class="tag" style:animation-delay="{(start[gi] + i) * 32}ms">{#if it.icon}<Icon name={it.icon} size={20} />{/if}{tx(it.label, lang)}</span>
          {/each}
        </span>
      </button>
    {/each}
  </div>
  {#if g.note}<Card title={tx(g.label, lang)} text={tx(g.note, lang)} />{/if}
</div>

<style>
  .wrap { display: flex; flex-direction: column; gap: 12px; }
  .board { display: grid; gap: 10px; align-items: stretch; }
  .grp { display: flex; flex-direction: column; text-align: left; padding: 0; min-height: var(--touch); border: var(--outline) solid var(--ink);
         border-radius: 16px; background: var(--paper); color: var(--ink); font: inherit; overflow: hidden;
         transition: transform .25s cubic-bezier(.34, 1.56, .64, 1); }
  .grp.on { transform: translateY(-4px); box-shadow: 0 6px 0 var(--ink); }
  .head { display: flex; align-items: center; gap: 8px; padding: 8px 10px; background: var(--c); border-bottom: var(--outline) solid var(--ink); }
  .head b { font-family: var(--font-display); font-weight: 400; font-size: 16px; line-height: 1.1; }
  .tags { display: flex; flex-wrap: wrap; gap: 5px; padding: 8px; align-content: flex-start; }
  .tag { display: inline-flex; align-items: center; gap: 5px; padding: 2px 9px 2px 7px; border: 2px solid var(--ink); border-radius: 999px;
         background: color-mix(in srgb, var(--c) 30%, var(--paper)); font-weight: 800; font-size: 13px; max-width: 100%;
         animation: tag-in .35s cubic-bezier(.34, 1.56, .64, 1) both; }
  @keyframes tag-in { from { opacity: 0; transform: scale(.6); } to { opacity: 1; transform: none; } }
  @media (max-aspect-ratio: 1/1) { .board { grid-template-columns: 1fr !important; } }
</style>
