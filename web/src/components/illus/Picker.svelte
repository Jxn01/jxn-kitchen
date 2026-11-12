<script lang="ts">
  // chart type `picker`: a grid of icon tiles — what a rice cooker can do, what to use a kettle for, what went wrong
  // with a bake. Each tile is a touch target; the chosen one lifts and the card explains it (with its value, if any).
  import { tx, type KPicker } from '../../lib/knowhow';
  import Icon from '../Icon.svelte';
  import Card from './Card.svelte';

  let { chart, lang }: { chart: KPicker; lang: 'en' | 'hu' } = $props();
  let sel = $state(0);
  let it = $derived(chart.items[sel]);
  const cols = $derived(chart.items.length <= 6 ? 3 : 4);
</script>

<div class="wrap">
  <div class="tiles" style:grid-template-columns="repeat({cols}, 1fr)">
    {#each chart.items as x, i}
      <button class="tile pressable" class:on={i === sel} style:animation-delay="{i * 45}ms" onclick={() => (sel = i)}>
        {#if x.icon}<span class="plate"><Icon name={x.icon} size={34} /></span>{/if}
        <span class="lb">{tx(x.label, lang)}</span>
      </button>
    {/each}
  </div>
  <Card title={tx(it.label, lang)} value={it.value ? tx(it.value, lang) : ''} text={tx(it.note, lang)} />
</div>

<style>
  .wrap { display: flex; flex-direction: column; gap: 12px; }
  .tiles { display: grid; gap: 8px; }
  .tile { min-height: var(--touch); display: flex; align-items: center; gap: 8px; padding: 8px 10px; text-align: left; border: var(--outline) solid var(--ink);
          border-radius: 14px; background: var(--paper); color: var(--ink); font: inherit; font-weight: 800; font-size: 14px; line-height: 1.15;
          transition: transform .25s cubic-bezier(.34, 1.56, .64, 1); animation: tile-in .4s cubic-bezier(.34, 1.56, .64, 1) both; }
  @keyframes tile-in { from { opacity: 0; transform: scale(.8); } to { opacity: 1; transform: none; } }
  .tile.on { background: var(--butter); transform: translateY(-3px); box-shadow: 0 5px 0 var(--ink); }
  .plate { flex: none; width: 44px; height: 44px; border-radius: 50%; background: var(--cream); border: 2.5px solid var(--ink); display: grid; place-items: center; }
  @media (max-aspect-ratio: 1/1) { .tiles { grid-template-columns: 1fr 1fr !important; } }
</style>
