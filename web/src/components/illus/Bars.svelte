<script lang="ts">
  // chart type `bars`: one row per item — its name, a bar in the item's own colour (grown in once, one after another;
  // a range `value–to` shows as a solid bar with a lighter tail), its value, and its note in small print. A marker
  // line (e.g. water's 100 g) runs through every track. Nothing to choose: everything is on screen at once, so the
  // rows are not touch targets and stay compact.
  import { tx, type KBars } from '../../lib/knowhow';
  import { paint } from '../../lib/palette';

  let { chart, lang }: { chart: KBars; lang: 'en' | 'hu' } = $props();
  const pct = (v: number) => (v / chart.max) * 100;
  let unit = $derived(tx(chart.unit, lang));
</script>

<div class="bars">
  {#each chart.items as it, i}
    <div class="row">
      <span class="name">{tx(it.label, lang)}</span>
      <span class="track">
        <span class="bar" style:width="{pct(it.to ?? it.value)}%" style:--f={paint(it.fill ?? 'butter')} style:animation-delay="{i * 60}ms">
          {#if it.to}<span class="tail" style:width="{((it.to - it.value) / it.to) * 100}%"></span>{/if}
        </span>
        {#if chart.marker}<span class="mark" style:left="{pct(chart.marker.value)}%"></span>{/if}
      </span>
      <span class="val"><b>{it.to ? `${it.value}–${it.to}` : it.value} {unit}</b>{#if it.note}<small>{tx(it.note, lang)}</small>{/if}</span>
    </div>
  {/each}
  {#if chart.marker}<p class="key"><span class="markk"></span>{tx(chart.marker.label, lang)}</p>{/if}
</div>

<style>
  .bars { display: flex; flex-direction: column; gap: 5px; }
  .row { display: grid; grid-template-columns: 190px 1fr 146px; align-items: center; gap: 10px; min-height: 34px; }
  .name { font-weight: 800; font-size: 15px; line-height: 1.15; }
  .track { position: relative; height: 24px; border-radius: 12px; background: var(--paper); border: 2px solid var(--ink); overflow: hidden; }
  .bar { position: absolute; left: 0; top: 0; bottom: 0; background: var(--f); border-right: 2px solid var(--ink);
         background-image: radial-gradient(rgba(0, 0, 0, .12) 1px, transparent 1.5px); background-size: 6px 6px;
         transform-origin: left; animation: grow .8s cubic-bezier(.34, 1.3, .64, 1) both; }
  @keyframes grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
  .tail { position: absolute; right: 0; top: 0; bottom: 0; background: repeating-linear-gradient(135deg, rgba(255, 255, 255, .55) 0 4px, transparent 4px 8px); }
  .mark { position: absolute; top: -2px; bottom: -2px; width: 3px; margin-left: -1px; background: var(--ink); }
  .val { display: flex; flex-direction: column; line-height: 1.1; }
  .val b { font-family: var(--font-display); font-weight: 400; font-size: 17px; overflow-wrap: anywhere; }   /* a long unit wraps, never spills */
  .val small { font-weight: 700; font-size: 12px; opacity: .7; }
  .key { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 13px; opacity: .75; margin: 4px 0 0; }
  .markk { width: 3px; height: 18px; background: var(--ink); display: inline-block; }
  @media (max-aspect-ratio: 1/1) { .row { grid-template-columns: 1fr 90px; } .track { grid-column: 1 / -1; grid-row: 2; } }
</style>
