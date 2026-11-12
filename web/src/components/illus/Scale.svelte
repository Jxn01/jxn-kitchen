<script lang="ts">
  // chart type `scale`: a wall thermometer. Beside the glass tube a ruler shows the bands in their colours (a band need
  // not touch the next: the gaps are what the page says nothing about), with the marks printed on it. Tap a band: the
  // red column rises or falls to it (one scaled div, eased with a little overshoot) and the card says what it means.
  import { tx, type KScale } from '../../lib/knowhow';
  import { paint } from '../../lib/palette';
  import Chips from './Chips.svelte';
  import Card from './Card.svelte';

  let { chart, lang }: { chart: KScale; lang: 'en' | 'hu' } = $props();
  let sel = $state(0);
  const TOP = 14, LEN = 236;                          // the tube's scale: from TOP down LEN px
  const y = (v: number) => TOP + ((chart.max - v) / (chart.max - chart.min)) * LEN;
  let b = $derived(chart.bands[sel]);
  let level = $derived(((b.from + b.to) / 2 - chart.min) / (chart.max - chart.min));
  let unit = $derived(tx(chart.unit, lang));
  const num = (v: number) => String(v).replace('-', '−');
  let range = $derived(b.range ? tx(b.range, lang) : `${num(b.from)}–${num(b.to)} ${unit}`);
  // fine graduation on the glass: a "nice" step giving about 12–25 ticks
  const step = $derived([1, 2, 5, 10, 20, 50].find((s) => (chart.max - chart.min) / s <= 25) ?? 100);
  const grads = $derived(Array.from({ length: Math.floor((chart.max - chart.min) / step) + 1 }, (_, k) => Math.ceil(chart.min / step) * step + k * step).filter((v) => v <= chart.max));
</script>

<div class="illus">
  <div class="therm">
    <div class="tube"></div>
    <div class="mercury" style:top="{TOP}px" style:height="{LEN + 10}px" style:transform="scaleY({(LEN * level + 10) / (LEN + 10)})"></div>
    <div class="bulb"></div>
    <svg class="glass" viewBox="0 0 70 300" aria-hidden="true">
      <path class="ol" d="M24,{TOP - 4} Q24,4 35,4 Q46,4 46,{TOP - 4} V{TOP + LEN + 8} A20,20 0 1 1 24,{TOP + LEN + 8} Z" />
      <path class="shine" d="M30,{TOP + 6} V{TOP + LEN - 6}" />
      {#each grads as g}<path class="grad" class:major={g % (step * 5) === 0} d="M46,{y(g)} H{g % (step * 5) === 0 ? 55 : 51}" />{/each}
    </svg>
    <div class="ruler">
      {#each chart.bands as band, i}
        <div class="band" class:on={i === sel} style:top="{y(band.to)}px" style:height="{y(band.from) - y(band.to)}px" style:background={paint(band.fill)}></div>
      {/each}
    </div>
    <svg class="marks" viewBox="0 0 90 300" aria-hidden="true">
      {#each chart.marks ?? [] as m}
        <path class="tick" d="M0,{y(m.value)} H12" />
        <text class="ml" x="16" y={y(m.value) + 5}>{tx(m.label, lang)}</text>
      {/each}
    </svg>
  </div>
  <div class="side">
    <Chips labels={chart.bands.map((x) => tx(x.label, lang))} bind:sel on="tomato" />
    <Card title={tx(b.label, lang)} value={range} text={tx(b.note, lang)} />
  </div>
</div>

<style>
  .illus { display: flex; gap: 18px; align-items: flex-start; }
  .therm { position: relative; flex: none; width: 196px; height: 300px; }
  .tube { position: absolute; left: 26px; top: 6px; width: 18px; height: 262px; background: rgba(255, 255, 255, .85); border-radius: 9px; }
  .mercury { position: absolute; left: 30px; width: 10px; border-radius: 5px; background: linear-gradient(90deg, #E8442E, #FF7B5C 45%, #C9302A);
             transform-origin: 50% 100%; transition: transform .9s cubic-bezier(.3, 1.3, .5, 1); }
  .bulb { position: absolute; left: 17px; top: 253px; width: 36px; height: 36px; border-radius: 50%; background: radial-gradient(circle at 35% 35%, #FF8E70, #E8442E 55%, #B92A25); }
  .glass { position: absolute; left: 0; top: 0; width: 70px; height: 300px; overflow: visible; pointer-events: none; }
  .ol { fill: none; stroke: var(--ink); stroke-width: 4.5; stroke-linejoin: round; }
  .shine { stroke: #fff; stroke-width: 3; stroke-linecap: round; opacity: .9; }
  .grad { stroke: var(--ink); stroke-width: 1.6; } .grad.major { stroke-width: 2.4; }
  .ruler { position: absolute; left: 62px; top: 0; width: 26px; height: 300px; }
  .band { position: absolute; left: 0; width: 100%; border: 2.5px solid var(--ink); border-radius: 6px; transform-origin: 0 50%;
          transition: transform .3s cubic-bezier(.34, 1.56, .64, 1); }
  .band.on { transform: scaleX(1.35); }
  .marks { position: absolute; left: 96px; top: 0; width: 90px; height: 300px; overflow: visible; pointer-events: none; }
  .tick { stroke: var(--ink); stroke-width: 3; stroke-linecap: round; }
  .ml { font-family: var(--font-display); font-size: 15px; fill: var(--ink); }
  .side { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 12px; }
  @media (max-aspect-ratio: 1/1) { .illus { flex-direction: column; align-items: center; } .side { width: 100%; } }
</style>
