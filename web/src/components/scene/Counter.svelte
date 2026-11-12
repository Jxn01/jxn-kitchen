<script lang="ts" module>
  let uid = 0;
</script>

<script lang="ts">
  // The counter the mascot stands on (idle scene and home): kitchen wall tiles, a gingham tablecloth whose top is seen
  // in perspective, a rounded front edge, and a drape with soft folds and a scalloped, stitched hem. One static svg —
  // nothing in it moves, so it is painted once. Width-responsive: the drawing is 1200 wide and is cropped
  // (xMidYMax slice), so the checks never stretch.
  let { height = 300, tiles = true, top = 40 }: { height?: number; tiles?: boolean; top?: number } = $props();
  const id = `ctr${uid++}`;
  const Wd = 1200;
  const S = 30;                                   // stripe width; a check is S × S
  let T = $derived(tiles ? height - 170 : 6);    // back edge of the table top
  let F = $derived(T + top);                       // front edge (the fold)
  let H = $derived(height);
  const cx = Wd / 2;
  const persp = (x: number) => cx + (x - cx) * 0.9;   // a stripe's x at the back edge
  let vStripes = $derived(Array.from({ length: Wd / (2 * S) + 1 }, (_, k) => k * 2 * S));
  // the top's horizontal stripes, foreshortened towards the back
  let hTop = $derived.by(() => {
    const out: [number, number][] = [];
    let y = F, h = 15;
    while (y - h > T + 2) { out.push([y - h, h]); y -= h * 2; h *= 0.72; }
    return out;
  });
  let hFront = $derived(Array.from({ length: Math.ceil((H - F) / (2 * S)) + 1 }, (_, j) => F + 8 + j * 2 * S));
  // the scalloped hem
  let hem = $derived.by(() => {
    const r = 15, base = H - 14;
    let d = `M0,${F} H${Wd} V${base}`;
    for (let x = Wd; x > 0; x -= 2 * r) d += ` A${r},${r} 0 0 1 ${x - 2 * r},${base}`;
    return d + ' Z';
  });
</script>

<svg class="counter" viewBox="0 0 {Wd} {H}" preserveAspectRatio="xMidYMax slice" width="100%" height={H} aria-hidden="true">
  <defs>
    <clipPath id="{id}-top"><path d="M{persp(0)},{T} H{persp(Wd)} L{Wd},{F} H0 Z" /></clipPath>
    <clipPath id="{id}-drape"><path d={hem} /></clipPath>
    <linearGradient id="{id}-fold" x1="0" x2="1">
      <stop offset="0" stop-color="#000" stop-opacity="0" /><stop offset=".5" stop-color="#000" stop-opacity=".09" />
      <stop offset="1" stop-color="#000" stop-opacity="0" />
    </linearGradient>
    <linearGradient id="{id}-shine" x1="0" x2="1">
      <stop offset="0" stop-color="#fff" stop-opacity="0" /><stop class="shinestop" offset=".5" stop-color="#fff" />
      <stop offset="1" stop-color="#fff" stop-opacity="0" />
    </linearGradient>
    <linearGradient id="{id}-under" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0" stop-color="#000" stop-opacity=".16" /><stop offset="1" stop-color="#000" stop-opacity="0" />
    </linearGradient>
  </defs>

  {#if tiles}
    <!-- subway tiles on the wall behind the counter -->
    <rect x="0" y="0" width={Wd} height={T} class="grout" />
    {#each Array.from({ length: Math.ceil(T / 34) }, (_, r) => r) as r}
      {#each Array.from({ length: 20 }, (_, c) => c) as c}
        <rect class="tile" x={c * 66 - (r % 2 ? 33 : 0) + 3} y={T - (r + 1) * 34 + 3} width="60" height="28" rx="6" />
      {/each}
    {/each}
    <rect x="0" y={T - 10} width={Wd} height="10" class="tileshadow" />
  {/if}

  <!-- the table top in perspective -->
  <g clip-path="url(#{id}-top)">
    <rect x="0" y={T} width={Wd} height={F - T} class="cloth" />
    {#each vStripes as x}<path class="check" d="M{persp(x)},{T} H{persp(x + S)} L{x + S},{F} H{x} Z" />{/each}
    {#each hTop as [y, h]}<rect class="check" x="0" {y} width={Wd} height={h} />{/each}
  </g>
  <path class="edge" d="M{persp(0) - 2},{T} H{persp(Wd) + 2}" />

  <!-- the drape over the front edge -->
  <g clip-path="url(#{id}-drape)">
    <rect x="0" y={F} width={Wd} height={H - F} class="cloth" />
    {#each vStripes as x}<rect class="check" {x} y={F} width={S} height={H - F} />{/each}
    {#each hFront as y}<rect class="check" x="0" {y} width={Wd} height={S} />{/each}
    {#each [140, 420, 700, 980] as x}<rect x={x - 50} y={F} width="100" height={H - F} fill="url(#{id}-fold)" />{/each}
    {#each [280, 560, 840, 1120] as x}<rect x={x - 40} y={F} width="80" height={H - F} fill="url(#{id}-shine)" />{/each}
    <rect x="0" y={F} width={Wd} height="22" fill="url(#{id}-under)" />
    <path class="stitch" d="M0,{H - 24} H{Wd}" />
  </g>
  <!-- the rounded front edge where the cloth folds over -->
  <path class="lip" d="M0,{F} H{Wd}" />
  <path class="lipshine" d="M0,{F - 3} H{Wd}" />
</svg>

<style>
  .counter { display: block; }
  .shinestop { stop-opacity: var(--shine, .16); }
  .grout { fill: var(--grout, #FBEBD0); }
  .tile { fill: var(--tile, #FFF7E8); stroke: var(--tile-edge, #EAD5B2); stroke-width: 2; }
  .tileshadow { fill: #000; opacity: .06; }
  .cloth { fill: var(--cloth, #FFFDF8); }
  .check { fill: var(--gingham, #E14B3B); opacity: .5; }
  .edge { stroke: var(--ink); stroke-width: 4; stroke-linecap: round; }
  .lip { stroke: var(--ink); stroke-width: 4; }
  .lipshine { stroke: #fff; stroke-width: 3; opacity: .55; }
  .stitch { stroke: #fff; stroke-width: 3; stroke-dasharray: 9 7; opacity: .75; fill: none; }
</style>
