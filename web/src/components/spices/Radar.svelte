<script lang="ts">
  // The flavour radar: eight axes, the blend's shape (share-weighted, the strongest axis at the rim) and, dashed, the
  // shape before the last change — so a tap shows what it moved. A static svg: an evaluation changes two `d` attributes.
  import type { Labelled } from '../../lib/spices';
  import type { Lang } from '../../lib/i18n';
  let { radar, axes, lang, ghost = null, size = 190, fill = '#F28C28' }:
    { radar: Record<string, number>; axes: Labelled[]; lang: Lang; ghost?: Record<string, number> | null; size?: number; fill?: string } = $props();
  const CX = 100, CY = 100, R = 66;
  const pt = (i: number, v: number) => {
    const a = -Math.PI / 2 + (i * 2 * Math.PI) / axes.length;
    return [CX + Math.cos(a) * R * v, CY + Math.sin(a) * R * v];
  };
  const path = (r: Record<string, number> | null) =>
    r ? axes.map((ax, i) => pt(i, Math.max(0.04, r[ax.id] ?? 0))).map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ') + ' Z' : '';
</script>

<svg viewBox="0 0 200 200" width={size} height={size} aria-hidden="true">
  {#each [0.33, 0.66, 1] as k (k)}
    <path class="grid" d={axes.map((_, i) => pt(i, k)).map(([x, y], i) => `${i ? 'L' : 'M'}${x},${y}`).join(' ') + ' Z'} />
  {/each}
  {#each axes as ax, i (ax.id)}
    {@const [x, y] = pt(i, 1)}
    {@const [lx, ly] = pt(i, 1.32)}
    <path class="spoke" d="M{CX},{CY} L{x},{y}" />
    <text x={lx} y={ly + 4} text-anchor="middle">{ax[lang]}</text>
  {/each}
  <!-- always there (hidden with no shape before): an answer only changes its `d` -->
  <path class="ghost" class:blank={!ghost} d={path(ghost ?? radar)} />
  <path class="shape" d={path(radar)} fill={fill} />
</svg>

<style>
  svg { display: block; overflow: visible; flex: none; }
  .grid { fill: none; stroke: #E2D6C4; stroke-width: 1.2; }
  .spoke { stroke: #E2D6C4; stroke-width: 1.2; }
  text { font: 800 10.5px var(--font-body); fill: var(--ink); }
  .ghost.blank { visibility: hidden; }
  .ghost { fill: none; stroke: var(--ink); stroke-width: 1.6; stroke-dasharray: 4 3; opacity: .5; }
  .shape { fill-opacity: .62; stroke: var(--ink); stroke-width: 2.6; stroke-linejoin: round; }
</style>
