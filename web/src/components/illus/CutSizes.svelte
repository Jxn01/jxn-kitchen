<script lang="ts">
  // knife/cuts: the classic cuts TO SCALE on a cutting board (3.6 px per mm, with a centimetre ruler): carrot cubes from
  // brunoise to large dice, julienne and batonnet sticks, basil chiffonade, minced garlic. Each cut is a button; the
  // chosen one lifts and the card says its size and what it is for. Pieces are static drawings in HTML layers.
  let { lang }: { lang: 'en' | 'hu' } = $props();
  const MM = 3.6;                                          // px per millimetre
  type Cut = { id: string; kind: 'cube' | 'stick' | 'ribbon' | 'mince'; a: number; b?: number; n: number;
               en: [string, string, string]; hu: [string, string, string] };
  const CUTS: Cut[] = [
    { id: 'brunoise', kind: 'cube', a: 3, n: 4, en: ['Brunoise', '2–3 mm cubes', 'Garnish, fine sauces, fried rice.'], hu: ['Brunoise', '2–3 mm-es kocka', 'Díszítés, finom mártások, pirított rizs.'] },
    { id: 'small', kind: 'cube', a: 5, n: 3, en: ['Small dice', '5 mm', 'Soffritto, sauces, fillings.'], hu: ['Apró kocka', '5 mm', 'Soffritto, mártások, töltelékek.'] },
    { id: 'medium', kind: 'cube', a: 12, n: 2, en: ['Medium dice', '1–1.5 cm', 'Soups, stews, lecsó.'], hu: ['Közepes kocka', '1–1,5 cm', 'Levesek, raguk, lecsó.'] },
    { id: 'large', kind: 'cube', a: 20, n: 1, en: ['Large dice', '2 cm and up', 'Slow stews, roasting.'], hu: ['Nagy kocka', '2 cm és nagyobb', 'Lassú raguk, sütés.'] },
    { id: 'julienne', kind: 'stick', a: 2.5, b: 50, n: 3, en: ['Julienne', '2–3 mm × 5 cm sticks', 'Salads, stir-fries.'], hu: ['Julienne', '2–3 mm × 5 cm-es csík', 'Saláták, wokban sült ételek.'] },
    { id: 'batonnet', kind: 'stick', a: 6, b: 60, n: 2, en: ['Batonnet', '6 mm × 6 cm sticks', 'Chips, crudités.'], hu: ['Batonnet', '6 mm × 6 cm-es hasáb', 'Hasábburgonya, nyers zöldséghasábok.'] },
    { id: 'chiffonade', kind: 'ribbon', a: 2, b: 34, n: 4, en: ['Chiffonade', 'thin ribbons', 'Basil, spinach, sorrel: roll the leaves up, slice thin.'], hu: ['Chiffonade', 'vékony szalagok', 'Bazsalikom, spenót, sóska: tekerd fel a leveleket, vágd vékonyra.'] },
    { id: 'mince', kind: 'mince', a: 1, n: 18, en: ['Mince', 'as fine as it gets', 'Garlic, ginger, herbs.'], hu: ['Darálás', 'amilyen finom csak lehet', 'Fokhagyma, gyömbér, fűszernövények.'] },
  ];
  let sel = $state(3);
  let c = $derived(CUTS[sel]);
  const cubes = CUTS.filter((x) => x.kind === 'cube');
  const sticks = CUTS.filter((x) => x.kind === 'stick');
  const soft = CUTS.filter((x) => x.kind === 'ribbon' || x.kind === 'mince');
  const idx = (x: Cut) => CUTS.indexOf(x);
  // a little isometric carrot cube of side s px
  const cube = (s: number) => {
    const d = Math.max(2, s * 0.35);
    return { w: s + d, h: s + d, top: `M0,${d} L${d},0 H${s + d} L${s},${d} Z`, side: `M${s},${d} L${s + d},0 V${s} L${s},${s + d} Z`, front: `M0,${d} H${s} V${s + d} H0 Z` };
  };
  const minceBits = Array.from({ length: 18 }, (_, i) => ({ x: (i * 37) % 46, y: (i * 23) % 22, s: 3 + (i % 3) }));
</script>

{#snippet piece(x: Cut)}
  {#if x.kind === 'cube'}
    {@const k = cube(x.a * MM)}
    <span class="pcs">
      {#each Array.from({ length: x.n }) as _}
        <svg width={k.w} height={k.h} viewBox="0 0 {k.w} {k.h}" aria-hidden="true">
          <path class="ct" d={k.top} /><path class="cs" d={k.side} /><path class="cf" d={k.front} />
        </svg>
      {/each}
    </span>
  {:else if x.kind === 'stick'}
    <span class="pcs col">
      {#each Array.from({ length: x.n }) as _}
        <svg width={x.b! * MM + 6} height={x.a * MM + 6} viewBox="0 0 {x.b! * MM + 6} {x.a * MM + 6}" aria-hidden="true">
          <path class="ct" d="M0,4 L4,0 H{x.b! * MM + 6} L{x.b! * MM + 2},4 Z" /><rect class="cf" x="0" y="4" width={x.b! * MM + 2} height={x.a * MM} />
        </svg>
      {/each}
    </span>
  {:else if x.kind === 'ribbon'}
    <svg class="pcs" width="104" height="46" viewBox="0 0 104 46" aria-hidden="true">
      {#each [0, 1, 2, 3] as r}<path class="rib" d="M{6 + r * 5},{8 + r * 10} q15,-9 30,0 t30,0 t30,0" />{/each}
    </svg>
  {:else}
    <svg class="pcs" width="56" height="30" viewBox="0 0 56 30" aria-hidden="true">
      {#each minceBits as m}<rect class="garlic" x={m.x} y={m.y} width={m.s} height={m.s} rx="1" />{/each}
    </svg>
  {/if}
{/snippet}

<div class="illus">
  <div class="board">
    <div class="row">
      {#each [...cubes, ...soft.filter((x) => x.kind === 'mince')] as x}
        <button class="cut pressable" class:on={idx(x) === sel} style:animation-delay="{idx(x) * 60}ms" onclick={() => (sel = idx(x))}>
          {@render piece(x)}<span class="nm">{x[lang][0]}</span>
        </button>
      {/each}
    </div>
    <div class="row">
      {#each [...sticks, ...soft.filter((x) => x.kind === 'ribbon')] as x}
        <button class="cut pressable" class:on={idx(x) === sel} style:animation-delay="{idx(x) * 60}ms" onclick={() => (sel = idx(x))}>
          {@render piece(x)}<span class="nm">{x[lang][0]}</span>
        </button>
      {/each}
    </div>
    <svg class="ruler" viewBox="0 0 {60 * MM + 20} 30" width={60 * MM + 20} height="30" aria-hidden="true">
      <rect x="0" y="2" width={60 * MM + 20} height="26" rx="4" class="rl" />
      {#each Array.from({ length: 61 }, (_, i) => i) as mm}
        <path class="rt" d="M{10 + mm * MM},2 V{mm % 10 === 0 ? 16 : mm % 5 === 0 ? 12 : 8}" />
        {#if mm % 10 === 0}<text class="rn" x={10 + mm * MM} y="26" text-anchor="middle">{mm / 10}</text>{/if}
      {/each}
    </svg>
  </div>
  {#key sel}
    <div class="card"><b>{c[lang][0]}</b><span>{c[lang][1]}</span><p>{c[lang][2]}</p></div>
  {/key}
</div>

<style>
  .illus { display: flex; flex-direction: column; gap: 12px; }
  .board { position: relative; background: #E2B07A; border: var(--outline) solid var(--ink); border-radius: 18px; padding: 6px 10px 6px;
           background-image: repeating-linear-gradient(0deg, rgba(160, 100, 50, .18) 0 2px, transparent 2px 19px); display: flex; flex-direction: column; gap: 2px; }
  .row { display: flex; flex-wrap: wrap; gap: 6px; align-items: flex-end; }
  .cut { min-height: var(--touch); min-width: var(--touch); padding: 6px 8px 4px; border: 2.5px solid transparent; border-radius: 14px; background: none; color: var(--ink);
         font: inherit; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; gap: 4px;
         transition: transform .25s cubic-bezier(.34, 1.56, .64, 1); animation: drop .45s cubic-bezier(.34, 1.56, .64, 1) both; }
  @keyframes drop { from { opacity: 0; transform: translateY(-16px); } to { opacity: 1; transform: none; } }
  .cut.on { transform: translateY(-4px); background: rgba(255, 244, 223, .75); border-color: var(--ink); }
  .pcs { display: flex; gap: 4px; align-items: flex-end; }
  .pcs.col { flex-direction: column; align-items: flex-start; gap: 3px; }
  .ct { fill: #FFB25C; stroke: var(--ink); stroke-width: 1.5; stroke-linejoin: round; }
  .cs { fill: #D96A1E; stroke: var(--ink); stroke-width: 1.5; stroke-linejoin: round; }
  .cf { fill: #F28C28; stroke: var(--ink); stroke-width: 1.5; stroke-linejoin: round; }
  .rib { fill: none; stroke: #3F8F3A; stroke-width: 5; stroke-linecap: round; }
  .garlic { fill: #FBF3DC; stroke: var(--ink); stroke-width: 1; }
  .nm { font-weight: 800; font-size: 13px; white-space: nowrap; }
  .ruler { display: block; margin-top: 2px; }
  .rl { fill: #FFF8E6; stroke: var(--ink); stroke-width: 2.5; }
  .rt { stroke: var(--ink); stroke-width: 1.4; }
  .rn { font-family: var(--font-display); font-size: 11px; fill: var(--ink); }
  .card { background: var(--paper); border: var(--outline) solid var(--ink); border-radius: 16px; padding: 10px 14px; box-shadow: 0 4px 0 var(--ink);
          display: flex; align-items: baseline; flex-wrap: wrap; gap: 4px 10px; animation: pop .35s cubic-bezier(.34, 1.56, .64, 1) both; }
  @keyframes pop { from { opacity: 0; transform: scale(.92) translateY(4px); } to { opacity: 1; transform: none; } }
  .card b { font-family: var(--font-display); font-weight: 400; font-size: 24px; }
  .card span { font-family: var(--font-display); font-size: 18px; opacity: .7; }
  .card p { margin: 0; flex-basis: 100%; font-weight: 700; font-size: 15px; }
</style>
