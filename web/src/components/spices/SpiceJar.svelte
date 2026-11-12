<script lang="ts" module>
  let n = 0;
</script>

<script lang="ts">
  // A spice jar, drawn once: glass, a cork lid, the contents in their colour — one mixed colour with a scatter of
  // grains (the owner's blend on the shelf), or stripes of every part bottom up (the composition). Static svg only:
  // nothing in it animates (the screens move the HTML wrapper). The hand-lettered label is HTML over the glass, so
  // long names wrap and shrink like text, not like a drawing.
  let { fill = '#CCBFA8', stripes = null, size = 120, label = '', heat = 0, dot = null, ribbon = '', empty = false, level = 1 }:
    { fill?: string; stripes?: { fill: string; part: number }[] | null; size?: number; label?: string; heat?: number;
      dot?: string | null; ribbon?: string; empty?: boolean; level?: number } = $props();
  const uid = `jar${++n}`;
  // the label's type size: the longest word must fit the label's width (~58 % of the jar) without breaking
  let fs = $derived.by(() => {
    const longest = Math.max(4, ...label.split(/\s+/).map((w) => w.length));
    return Math.max(8, Math.min(size * 0.105, (size * 0.56) / (0.64 * longest)));
  });
  // the inside of the glass, in the 100 x 120 drawing
  const IN = { x: 17, y: 30, w: 66, h: 82 };
  let top = $derived(IN.y + IN.h * (1 - Math.max(0, Math.min(1, level))));
  let bands = $derived.by(() => {
    if (!stripes?.length) return [];
    const total = stripes.reduce((s, p) => s + p.part, 0) || 1;
    let y = IN.y + IN.h;
    const h = IN.y + IN.h - top;
    return stripes.map((p) => { const bh = (p.part / total) * h; y -= bh; return { fill: p.fill, y, h: bh + 0.4 }; });
  });
  // a fixed scatter of grains (same place in every jar, so a shelf reads as one family)
  const PIPS = [0, 1, 2, 3, 4];
  const GRAINS = [[24, 98], [31, 106], [40, 94], [47, 104], [56, 97], [64, 107], [72, 99], [28, 84], [37, 76], [52, 82],
                  [61, 74], [70, 86], [44, 66], [66, 60], [25, 62], [57, 108]];
</script>

<span class="jar" style:width="{size}px" style:height="{size * 1.2}px">
  <svg viewBox="0 0 100 120" width={size} height={size * 1.2} aria-hidden="true">
    <defs>
      <clipPath id="{uid}-in"><path d="M17,30 H83 V104 Q83,112 75,112 H25 Q17,112 17,104 Z" /></clipPath>
    </defs>
    <path class="glass" d="M14,26 Q14,22 18,22 H82 Q86,22 86,26 V106 Q86,116 76,116 H24 Q14,116 14,106 Z" />
    {#if !empty}
      <g clip-path="url(#{uid}-in)">
        {#if bands.length}
          {#each bands as b, i (i)}<rect x="10" y={b.y} width="80" height={b.h} fill={b.fill} />{/each}
          {#each bands.slice(1) as b, i (i)}<path class="seam" d="M17,{b.y + b.h - 0.4} H83" />{/each}
        {:else}
          <rect x="10" y={top} width="80" height={IN.y + IN.h - top + 4} fill={fill} />
          {#each GRAINS as [gx, gy], i (i)}{#if gy > top + 3}<circle class="grain" class:lite={i % 3 === 0} cx={gx} cy={gy} r={i % 2 ? 1.6 : 1.1} />{/if}{/each}
        {/if}
        <path class="mound" d="M17,{top + 2} Q50,{top - 5} 83,{top + 2}" />
      </g>
    {/if}
    <path class="wall" class:dashed={empty} d="M14,26 Q14,22 18,22 H82 Q86,22 86,26 V106 Q86,116 76,116 H24 Q14,116 14,106 Z" />
    <path class="shine" d="M23,36 V100" /><path class="shine thin" d="M30,40 V58" />
    <rect class="lid" x="20" y="6" width="60" height="18" rx="5" />
    <path class="lid-line" d="M24,12 H76 M24,18 H76" />
    {#if empty}<path class="plus" d="M50,54 V86 M34,70 H66" />{/if}
    {#if dot}<circle class="dot" cx="82" cy="10" r="7" fill={dot} />{/if}
  </svg>
  {#if label}<span class="label" style:font-size="{fs}px">{label}</span>{/if}
  <!-- five pips always there, shown by class: a reused jar (the editor's rack slots) changes its heat without building any -->
  <span class="pips" class:none={heat <= 0} aria-hidden="true">{#each PIPS as i (i)}<i class:off={i >= heat}></i>{/each}</span>
  {#if ribbon}<span class="ribbon" style:font-size="{Math.max(9, size * 0.08)}px">{ribbon}</span>{/if}
</span>

<style>
  .jar { position: relative; display: inline-block; flex: none; }
  svg { display: block; overflow: visible; }
  .glass { fill: #EEF3F6; }
  .wall { fill: none; stroke: var(--ink); stroke-width: 3.4; stroke-linejoin: round; }
  .wall.dashed { stroke-dasharray: 7 5; }
  .shine { stroke: #fff; stroke-width: 4; stroke-linecap: round; opacity: .75; } .shine.thin { stroke-width: 2.4; }
  .grain { fill: #000; opacity: .18; } .grain.lite { fill: #fff; opacity: .3; }
  .mound { fill: none; stroke: rgba(255, 255, 255, .35); stroke-width: 2.2; stroke-linecap: round; }
  .seam { stroke: rgba(0, 0, 0, .22); stroke-width: 1; }
  .lid { fill: #C48A55; stroke: var(--ink); stroke-width: 3.4; }
  .lid-line { stroke: #8A5A30; stroke-width: 1.6; opacity: .6; }
  .plus { stroke: var(--ink); stroke-width: 6; stroke-linecap: round; opacity: .55; }
  .dot { stroke: var(--ink); stroke-width: 3; }
  .label {
    position: absolute; left: 21%; right: 21%; top: 44%; padding: 3px 2px; background: var(--cream); color: var(--ink);
    border: 2px solid var(--ink); border-radius: 4px; transform: rotate(-2deg); text-align: center;
    font-family: var(--font-display); line-height: 1.05; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 3;
    line-clamp: 3; -webkit-box-orient: vertical; overflow-wrap: normal; box-shadow: 1px 2px 0 rgba(0, 0, 0, .18);
  }
  .pips { position: absolute; left: 0; right: 0; bottom: 6%; display: flex; justify-content: center; gap: 2px; }
  .pips.none, .pips i.off { display: none; }
  .pips i { width: 7px; height: 9px; border-radius: 50% 50% 50% 50% / 60% 60% 40% 40%; background: #D9412F; border: 1.5px solid var(--ink); }
  .ribbon { position: absolute; left: -6%; top: 14%; background: var(--butter); color: var(--ink); border: 2px solid var(--ink);
            border-radius: 3px; padding: 1px 5px; font-weight: 900; transform: rotate(-12deg); text-transform: uppercase; letter-spacing: .03em; }
</style>
