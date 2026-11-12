<script lang="ts">
  // chart type `layers`: a see-through vessel (glass cup, tall latte glass, cut-away lábas, jar) that the chosen item
  // fills part by part, bottom up — a coffee drink's espresso, milk and foam; a grain and its water; a flour blend.
  // Each part is a div grown from its bottom (compositor-only), poured one after another; the legend names the parts.
  import { tx, type KLayers } from '../../lib/knowhow';
  import { paint } from '../../lib/palette';
  import Chips from './Chips.svelte';
  import Card from './Card.svelte';

  let { chart, lang }: { chart: KLayers; lang: 'en' | 'hu' } = $props();
  let sel = $state(0);
  let it = $derived(chart.items[sel]);
  const IN = $derived(({ cup: { x: 44, y: 70, w: 132, h: 128 }, glass: { x: 72, y: 26, w: 96, h: 190 },
                         pot: { x: 38, y: 94, w: 164, h: 104 }, jar: { x: 56, y: 58, w: 112, h: 158 } })[chart.shape]);
  const most = $derived(Math.max(...chart.items.map((x) => x.layers.reduce((n, l) => n + l.part, 0))));
  let stack = $derived.by(() => {
    let y = 0;
    return it.layers.map((l, i) => { const h = (l.part / most) * IN.h; const o = { ...l, i, h, y }; y += h; return o; });
  });
</script>

<div class="illus">
  <div class="draw">
    <div class="back" class:glassy={chart.shape !== 'pot'} class:pot={chart.shape === 'pot'}
         style:left="{IN.x}px" style:top="{IN.y}px" style:width="{IN.w}px" style:height="{IN.h}px"></div>
    {#key sel}
      {#each stack as l (l.i)}
        <div class="layer" style:left="{IN.x}px" style:width="{IN.w}px" style:top="{IN.y + IN.h - l.y - l.h}px" style:height="{l.h + 0.6}px"
             style:--f={paint(l.fill)} style:animation-delay="{l.i * 260}ms"></div>
      {/each}
    {/key}
    <svg class="outline" viewBox="0 0 240 240" aria-hidden="true">
      {#if chart.shape === 'cup'}
        <path class="handle" d="M176,96 C214,96 214,168 176,168" /><path class="handle in" d="M176,96 C214,96 214,168 176,168" />
        <path class="wall" d="M40,66 L44,190 Q45,202 58,202 H162 Q175,202 176,190 L180,66" />
        <ellipse class="saucer" cx="110" cy="214" rx="96" ry="12" />
        <path class="shine" d="M54,86 V182" /><path class="shine thin" d="M64,92 V130" />
      {:else if chart.shape === 'glass'}
        <path class="wall" d="M70,20 L72,212 Q72,220 80,220 H160 Q168,220 168,212 L170,20" />
        <path class="shine" d="M82,40 V200" /><path class="shine thin" d="M92,48 V100" />
      {:else if chart.shape === 'pot'}
        {#each ['o', 'e'] as k}
          <path class="pw {k}" d="M33,92 V191 Q33,203 45,203 H195 Q207,203 207,191 V92" />
          <path class="pr {k}" d="M27,90 H213" />
          <path class="pe {k}" d="M27,104 H14 Q8,104 8,110 V114 Q8,120 14,120 H31" />
          <path class="pe {k}" d="M213,104 H226 Q232,104 232,110 V114 Q232,120 226,120 H209" />
        {/each}
        {#each [60, 100, 140, 180] as x}<circle class="dot" cx={x} cy="203" r="2.6" />{/each}
        <path class="ring" d="M44,224 H196" />
        {#each [64, 92, 120, 148, 176] as x}<path class="flame" d="M{x},222 Q{x - 7},212 {x},200 Q{x + 7},212 {x},222 Z" />{/each}
      {:else}
        <rect class="lid" x="50" y="30" width="124" height="22" rx="6" />
        <path class="wall" d="M60,54 H164 Q170,54 170,62 V210 Q170,218 162,218 H62 Q54,218 54,210 V62 Q54,54 60,54 Z" />
        <path class="shine" d="M66,70 V200" />
      {/if}
    </svg>
  </div>
  <div class="side">
    <Chips labels={chart.items.map((x) => tx(x.label, lang))} bind:sel on="cocoa" />
    <ul class="legend">
      {#each [...it.layers].reverse() as l}<li><span class="sw" style:background={paint(l.fill)}></span>{tx(l.label, lang)}</li>{/each}
    </ul>
    <Card title={tx(it.label, lang)} value={it.value ? tx(it.value, lang) : ''} text={tx(it.note, lang)} />
  </div>
</div>

<style>
  .illus { display: flex; gap: 18px; align-items: flex-start; }
  .draw { position: relative; flex: none; width: 240px; height: 240px; }
  .back { position: absolute; border-radius: 0 0 8px 8px; }
  .back.glassy { background: linear-gradient(90deg, #DCE7EE, #F3F7FA 35%, #DCE7EE); }   /* glass: white foam must still show */
  .back.pot { background: linear-gradient(90deg, #E9E1D6, #FBF7F1 30%, #EDE5DA); }
  .layer { position: absolute; background: var(--f); transform-origin: 50% 100%; animation: pour .55s cubic-bezier(.3, 1.4, .5, 1) both;
           background-image: linear-gradient(180deg, rgba(255, 255, 255, .22), transparent 40%), radial-gradient(rgba(0, 0, 0, .09) 1px, transparent 1.6px);
           background-size: 100% 100%, 7px 7px; box-shadow: inset 0 2px 0 rgba(0, 0, 0, .16); }
  @keyframes pour { from { transform: scaleY(0); opacity: .5; } to { transform: scaleY(1); opacity: 1; } }
  .outline { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; pointer-events: none; }
  .wall { fill: none; stroke: var(--ink); stroke-width: 5; stroke-linecap: round; stroke-linejoin: round; }
  .handle { fill: none; stroke: var(--ink); stroke-width: 16; stroke-linecap: round; } .handle.in { stroke: #F4F1EA; stroke-width: 8; }
  .saucer { fill: #F4F1EA; stroke: var(--ink); stroke-width: 4; }
  .shine { stroke: #fff; stroke-width: 6; stroke-linecap: round; opacity: .8; } .shine.thin { stroke-width: 3; }
  .lid { fill: #B5BEC7; stroke: var(--ink); stroke-width: 4; }
  .pw, .pr, .pe { fill: none; stroke-linecap: round; stroke-linejoin: round; }
  .pw.o, .pr.o { stroke: var(--ink); stroke-width: 15; } .pw.e, .pr.e { stroke: #D9412F; stroke-width: 8; }
  .pe.o { stroke: var(--ink); stroke-width: 11; } .pe.e { stroke: #D9412F; stroke-width: 5; }
  .dot { fill: #fff; } .ring { stroke: var(--ink); stroke-width: 7; stroke-linecap: round; }
  .flame { fill: #5BB5F0; stroke: var(--ink); stroke-width: 2.5; stroke-linejoin: round; }
  .side { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 10px; }
  .legend { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 4px 14px; font-weight: 800; font-size: 14px; }
  .legend li { display: flex; align-items: center; gap: 6px; }
  .sw { width: 16px; height: 16px; border-radius: 4px; border: 2px solid var(--ink); }
  @media (max-aspect-ratio: 1/1) { .illus { flex-direction: column; align-items: center; } .side { width: 100%; } }
</style>
