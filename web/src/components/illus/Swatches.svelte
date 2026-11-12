<script lang="ts">
  // chart type `swatches`: wooden spoons each holding a heap of its colour (the paprikas, the rántás colours) — or,
  // with shape `jars`, a spice rack: glass jars on wooden shelves, each with its spice and a tag on the shelf edge.
  // Spoons and jars are the touch targets; the chosen one lifts (the jar tips forward a little); a chilli meter shows
  // the heat when the items have one; the card adds the item's `value` (its taste). Static drawings, HTML layers.
  import { tx, type KSwatches } from '../../lib/knowhow';
  import { paint } from '../../lib/palette';
  import Icon from '../Icon.svelte';
  import Card from './Card.svelte';

  let { chart, lang }: { chart: KSwatches; lang: 'en' | 'hu' } = $props();
  let sel = $state(0);
  let it = $derived(chart.items[sel]);
  const hot = $derived(chart.items.some((x) => x.heat !== undefined));
  const jars = $derived(chart.shape === 'jars');
  const cols = $derived(Math.min(5, Math.ceil(chart.items.length / 2)));
</script>

<div class="wrap">
  {#if jars}
    <div class="rack" style:grid-template-columns="repeat({cols}, 1fr)">
      {#each chart.items as s, i}
        <button class="jar pressable" class:on={i === sel} style:--f={paint(s.fill)} style:animation-delay="{i * 55}ms" onclick={() => (sel = i)}>
          <span class="tilt">
            <span class="glass"><span class="spice"></span><span class="shine"></span></span>
            <span class="cap"></span>
          </span>
          <span class="plank"></span>
          <span class="tag">{tx(s.label, lang)}</span>
        </button>
      {/each}
    </div>
  {:else}
  <div class="spoons">
    {#each chart.items as s, i}
      <button class="spoon pressable" class:on={i === sel} style:--f={paint(s.fill)} style:animation-delay="{i * 60}ms" onclick={() => (sel = i)}>
        <span class="lift">
          <svg class="wood" viewBox="0 0 80 150" aria-hidden="true">
            <path class="handle" d="M36,62 L33,140 Q33,146 40,146 Q47,146 47,140 L44,62 Z" />
            <ellipse class="bowl" cx="40" cy="36" rx="30" ry="33" />
            <ellipse class="cup" cx="40" cy="38" rx="22" ry="25" />
          </svg>
          <span class="heap"></span>
        </span>
        <span class="name">{tx(s.label, lang)}</span>
      </button>
    {/each}
  </div>
  {/if}
  {#if hot}
    <div class="heat" aria-label="heat {it.heat ?? 0} / 5">
      {#each [1, 2, 3, 4, 5] as h}<span class="chilli" class:lit={(it.heat ?? 0) >= h}><Icon name="om-1f336" size={30} /></span>{/each}
    </div>
  {/if}
  <Card title={tx(it.label, lang)} value={it.value ? tx(it.value, lang) : ''} text={tx(it.note, lang)} />
</div>

<style>
  .wrap { display: flex; flex-direction: column; gap: 10px; }
  .spoons { display: flex; flex-wrap: wrap; gap: 2px; justify-content: center; }
  .spoon { width: 86px; min-height: var(--touch); padding: 4px 0 6px; border: 0; border-radius: 16px; background: none; color: var(--ink); font: inherit;
           display: flex; flex-direction: column; align-items: center; gap: 2px; animation: spoon-in .45s cubic-bezier(.34, 1.56, .64, 1) both; }
  @keyframes spoon-in { from { opacity: 0; transform: translateY(18px) rotate(-6deg); } to { opacity: 1; transform: none; } }
  .lift { position: relative; width: 70px; height: 131px; transition: transform .3s cubic-bezier(.34, 1.56, .64, 1); }
  .spoon.on .lift { transform: translateY(-8px) rotate(-4deg); }
  .wood { position: absolute; inset: 0; width: 70px; height: 131px; }
  .handle, .bowl { fill: #D9A066; stroke: var(--ink); stroke-width: 3.5; stroke-linejoin: round; }
  .cup { fill: #B97E45; }
  .heap { position: absolute; left: 14px; top: 10px; width: 42px; height: 41px; border-radius: 50% 50% 46% 46%;
          background: var(--f); border: 2.5px solid var(--ink);
          background-image: radial-gradient(rgba(0, 0, 0, .2) 1px, transparent 1.6px), radial-gradient(rgba(255, 255, 255, .28) 1px, transparent 1.6px),
                            radial-gradient(circle at 35% 30%, rgba(255, 255, 255, .35), transparent 45%);
          background-size: 6px 6px, 8px 8px, 100% 100%; background-position: 0 0, 3px 3px, 0 0;
          transition: transform .3s cubic-bezier(.34, 1.56, .64, 1); }
  .spoon.on .heap { transform: scale(1.12); }
  .name { font-weight: 800; font-size: 13px; line-height: 1.15; text-align: center; padding: 0 2px; }
  .spoon.on .name { background: var(--butter); border-radius: 8px; }
  .rack { display: grid; gap: 0; }
  .jar { position: relative; min-height: var(--touch); padding: 8px 4px 0; border: 0; background: none; color: var(--ink); font: inherit;
         display: flex; flex-direction: column; align-items: center; animation: jar-in .45s cubic-bezier(.34, 1.56, .64, 1) both; }
  @keyframes jar-in { from { opacity: 0; transform: translateY(-22px); } to { opacity: 1; transform: none; } }
  .tilt { position: relative; width: 64px; height: 86px; transform-origin: 50% 100%; transition: transform .3s cubic-bezier(.34, 1.56, .64, 1); }
  .jar.on .tilt { transform: translateY(-10px) rotate(-6deg); }
  .glass { position: absolute; left: 4px; right: 4px; top: 16px; bottom: 0; border: 3px solid var(--ink); border-radius: 8px 8px 12px 12px;
           background: rgba(255, 255, 255, .55); overflow: hidden; }
  .spice { position: absolute; left: 0; right: 0; bottom: 0; height: 74%; background: var(--f);
           background-image: radial-gradient(rgba(0, 0, 0, .2) 1px, transparent 1.6px), radial-gradient(rgba(255, 255, 255, .3) 1px, transparent 1.6px);
           background-size: 6px 6px, 8px 8px; background-position: 0 0, 3px 4px; border-top: 2px solid rgba(0, 0, 0, .2); }
  .shine { position: absolute; left: 6px; top: 6px; bottom: 8px; width: 5px; border-radius: 3px; background: rgba(255, 255, 255, .75); }
  .cap { position: absolute; left: 0; right: 0; top: 2px; height: 18px; border: 3px solid var(--ink); border-radius: 6px;
         background: repeating-linear-gradient(90deg, #C8D0D8 0 5px, #A9B4BF 5px 7px); }
  .plank { display: block; align-self: stretch; height: 12px; margin-top: -2px; background: #C98A4E; border-top: 3px solid var(--ink); border-bottom: 3px solid var(--ink); }
  .tag { margin: -1px 0 8px; padding: 1px 8px; font-weight: 800; font-size: 12.5px; line-height: 1.2; background: var(--paper); border: 2px solid var(--ink);
         border-top: 0; border-radius: 0 0 8px 8px; text-align: center; max-width: 100%; }
  .jar.on .tag { background: var(--butter); }
  .heat { display: flex; gap: 2px; justify-content: center; }
  .chilli { opacity: .18; transition: opacity .25s, transform .25s cubic-bezier(.34, 1.56, .64, 1); }
  .chilli.lit { opacity: 1; transform: scale(1.1); }
</style>
