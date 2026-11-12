<script lang="ts">
  // chart type `vessel`: a measuring jug, a cut-away pot on a gas ring or a glass coffee cup on its saucer, filled to
  // the chosen chip's level. The liquid
  // is one straight-walled div scaled from its bottom (compositor-only, eased with a little slosh); its surface and
  // whatever floats in it slide to the same level; a few bubbles (jug) or puffs of steam (pot) play once per choice.
  // The drawing is static svg on top — straight inner walls, so the liquid needs no clip.
  import { tx, type KVessel } from '../../lib/knowhow';
  import { paint } from '../../lib/palette';
  import Icon from '../Icon.svelte';
  import Chips from './Chips.svelte';
  import Card from './Card.svelte';

  let { chart, lang }: { chart: KVessel; lang: 'en' | 'hu' } = $props();
  let sel = $state(0);
  const jug = $derived(chart.shape === 'jug');
  const cup = $derived(chart.shape === 'cup');
  const W = 240, H = 240;
  // the inside of each vessel, in drawing px
  const IN = $derived(jug ? { x: 52, y: 46, w: 112, h: 172 } : cup ? { x: 44, y: 70, w: 132, h: 128 } : { x: 38, y: 94, w: 164, h: 104 });
  let it = $derived(chart.items[sel]);
  let level = $derived(it.value / chart.max);
  let lift = $derived(level * IN.h);
  let fill = $derived(paint(it.fill ?? (jug ? 'sky' : cup ? '#5A3A22' : 'tomato')));
  let value = $derived(chart.unit ? `${it.value} ${tx(chart.unit, lang)}` : '');
  const tickY = (v: number) => IN.y + IN.h - (v / chart.max) * IN.h;
</script>

<div class="illus">
  <div class="draw" style:--f={fill}>
    <div class="glass" class:pot={!jug && !cup} style:left="{IN.x}px" style:top="{IN.y}px" style:width="{IN.w}px" style:height="{IN.h}px"></div>
    <div class="liquid" style:left="{IN.x}px" style:top="{IN.y}px" style:width="{IN.w}px" style:height="{IN.h}px"
         style:transform="scaleY({level})"></div>
    <div class="surface" style:left="{IN.x}px" style:top="{IN.y + IN.h - 5}px" style:width="{IN.w}px"
         style:transform="translateY({-lift}px)"></div>
    {#if chart.items.some((x) => x.icons?.length)}
      <!-- every item's floating icons exist from the start, each set on its own layer; a choice only switches which set is
           visible. Re-creating them on each tap cost the kiosk 370–440 ms a tap -->
      <div class="float" style:left="{IN.x}px" style:top="{IN.y + IN.h - 24}px" style:width="{IN.w}px" style:transform="translateY({-lift}px)">
        {#each chart.items as item, k}
          <div class="set" class:on={k === sel}>
            {#each item.icons ?? [] as ic, i}<div class="bob" style:animation-delay="{500 + i * 120}ms"><Icon name={ic} size={38} /></div>{/each}
          </div>
        {/each}
      </div>
    {/if}
    {#key sel}
      {#if jug}
        {#each [0, 1, 2, 3] as b}
          <div class="bubble" style:left="{IN.x + 18 + b * 24}px" style:top="{IN.y + IN.h - 12}px" style:--rise="{-Math.max(lift - 14, 6)}px"
               style:animation-delay="{250 + b * 140}ms"></div>
        {/each}
      {:else}
        {#each [0, 1, 2] as p}
          <div class="steam" style:left="{IN.x + 30 + p * 44}px" style:top="{IN.y + IN.h - lift - 30}px" style:animation-delay="{600 + p * 220}ms"></div>
        {/each}
      {/if}
    {/key}
    <svg class="outline" viewBox="0 0 {W} {H}" aria-hidden="true">
      {#if jug}
        <!-- handle, then the body with its spout, then the printed scale -->
        <path class="handle" d="M166,74 C214,74 214,182 166,182" />
        <path class="handle in" d="M166,74 C214,74 214,182 166,182" />
        <path class="wall" d="M52,46 L52,214 Q52,220 58,220 H158 Q164,220 164,214 L164,46" />
        <path class="wall" d="M164,46 Q166,40 172,38 M52,50 Q50,38 34,30" />
        <path class="shine" d="M154,64 V196" /><path class="shine thin" d="M145,72 V128" />
        {#each chart.ticks ?? [] as t}
          <path class="tick" d="M56,{tickY(t.value)} H82" />
          <text class="tl" x="88" y={tickY(t.value) + 5}>{tx(t.label, lang)}</text>
        {/each}
      {:else if cup}
        <!-- a glass coffee cup on its saucer -->
        <path class="handle" d="M176,96 C214,96 214,168 176,168" /><path class="handle in" d="M176,96 C214,96 214,168 176,168" />
        <path class="wall" d="M40,66 L44,190 Q45,202 58,202 H162 Q175,202 176,190 L180,66" />
        <ellipse class="saucer" cx="110" cy="214" rx="96" ry="12" />
        <path class="shine" d="M54,86 V182" /><path class="shine thin" d="M64,92 V130" />
        {#each chart.ticks ?? [] as t}
          <path class="tick" d="M150,{tickY(t.value)} H172" />
          <text class="tl" x="146" y={tickY(t.value) + 5} text-anchor="end">{tx(t.label, lang)}</text>
        {/each}
      {:else}
        <!-- gas ring and flames (static), the pot cut away so the inside shows, its handles and rim -->
        <path class="ring" d="M44,224 H196" />
        {#each [64, 92, 120, 148, 176] as x}<path class="flame" d="M{x},222 Q{x - 7},212 {x},200 Q{x + 7},212 {x},222 Z" />{/each}
        {#each ['o', 'e'] as k}
          <path class="pw {k}" d="M33,92 V191 Q33,203 45,203 H195 Q207,203 207,191 V92" />
          <path class="pr {k}" d="M27,90 H213" />
          <path class="pe {k}" d="M27,104 H14 Q8,104 8,110 V114 Q8,120 14,120 H31" />
          <path class="pe {k}" d="M213,104 H226 Q232,104 232,110 V114 Q232,120 226,120 H209" />
        {/each}
        {#each [60, 100, 140, 180] as x}<circle class="dot" cx={x} cy="203" r="2.6" />{/each}
        <path class="shine" d="M46,108 V178" />
      {/if}
    </svg>
  </div>
  <div class="side">
    <Chips labels={chart.items.map((i) => tx(i.label, lang))} bind:sel on={jug ? 'sky' : cup ? 'cocoa' : 'tomato'} />
    <Card title={tx(it.label, lang)} {value} text={tx(it.note, lang)} />
  </div>
</div>

<style>
  .illus { display: flex; gap: 18px; align-items: flex-start; }
  .draw { position: relative; flex: none; width: 240px; height: 240px; }
  .glass { position: absolute; background: rgba(255, 255, 255, .72); border-radius: 0 0 6px 6px; }
  .glass.pot { background: linear-gradient(90deg, #E9E1D6, #FBF7F1 30%, #EDE5DA); }
  .liquid { position: absolute; transform-origin: 50% 100%; border-radius: 0 0 6px 6px;
            background: linear-gradient(180deg, color-mix(in srgb, var(--f) 78%, #fff), var(--f) 40%, color-mix(in srgb, var(--f) 82%, #000));
            transition: transform .9s cubic-bezier(.3, 1.35, .5, 1); }
  .surface { position: absolute; height: 10px; border-radius: 50%; background: color-mix(in srgb, var(--f) 55%, #fff);
             transition: transform .9s cubic-bezier(.3, 1.35, .5, 1); }
  .float { position: absolute; height: 40px; transition: transform .9s cubic-bezier(.3, 1.35, .5, 1); pointer-events: none; }
  .set { position: absolute; inset: 0; display: flex; justify-content: space-evenly; opacity: 0; will-change: opacity; transition: opacity .25s; }
  .set.on { opacity: 1; }
  .set.on .bob { animation: bob 1.1s ease-in-out both; }
  @keyframes bob { 0% { transform: translateY(14px) rotate(-8deg); opacity: 0; } 40% { opacity: 1; } 60% { transform: translateY(-5px) rotate(5deg); } 100% { transform: none; opacity: 1; } }
  .bubble { position: absolute; width: 9px; height: 9px; border-radius: 50%; border: 2px solid rgba(255, 255, 255, .9); opacity: 0;
            animation: rise 1.1s ease-out both; pointer-events: none; }
  @keyframes rise { 0% { opacity: 0; transform: none; } 20% { opacity: 1; } 100% { opacity: 0; transform: translateY(var(--rise)); } }
  .steam { position: absolute; width: 22px; height: 22px; border-radius: 50%; background: #fff; opacity: 0; animation: steam 1.6s ease-out both; pointer-events: none; }
  @keyframes steam { 0% { opacity: 0; transform: scale(.5); } 30% { opacity: .85; } 100% { opacity: 0; transform: translate(6px, -46px) scale(1.5); } }
  .outline { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; pointer-events: none; }
  .wall, .rim { fill: none; stroke: var(--ink); stroke-width: 5; stroke-linecap: round; stroke-linejoin: round; }
  .rim { stroke-width: 9; }
  .ear { fill: none; stroke: var(--ink); stroke-width: 6; stroke-linecap: round; stroke-linejoin: round; }
  .handle { fill: none; stroke: var(--ink); stroke-width: 18; stroke-linecap: round; }
  .handle.in { stroke: var(--paper); stroke-width: 9; }
  .shine { stroke: #fff; stroke-width: 6; stroke-linecap: round; opacity: .85; } .shine.thin { stroke-width: 3; }
  .tick { stroke: var(--ink); stroke-width: 3; stroke-linecap: round; }
  .tl { font-family: var(--font-display); font-size: 15px; fill: var(--ink); paint-order: stroke; stroke: rgba(255, 255, 255, .85); stroke-width: 4px; }
  .pw, .pr, .pe { fill: none; stroke-linecap: round; stroke-linejoin: round; }
  .pw.o { stroke: var(--ink); stroke-width: 15; } .pw.e { stroke: #D9412F; stroke-width: 8; }
  .pr.o { stroke: var(--ink); stroke-width: 15; } .pr.e { stroke: #D9412F; stroke-width: 8; }
  .pe.o { stroke: var(--ink); stroke-width: 11; } .pe.e { stroke: #D9412F; stroke-width: 5; }
  .dot { fill: #fff; }
  .saucer { fill: #F4F1EA; stroke: var(--ink); stroke-width: 4; }
  .ring { stroke: var(--ink); stroke-width: 7; stroke-linecap: round; }
  .flame { fill: #5BB5F0; stroke: var(--ink); stroke-width: 2.5; stroke-linejoin: round; }
  .side { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 12px; }
  @media (max-aspect-ratio: 1/1) { .illus { flex-direction: column; align-items: center; } .side { width: 100%; } }
</style>
