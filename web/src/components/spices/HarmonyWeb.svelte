<script lang="ts">
  // The harmony web: the blend's jars on a circle, every pair a line — green and solid when they like each other,
  // red and dashed when they fight, thin grey when they have nothing to say. Built from FIXED POOLS (16 node slots,
  // 120 edge slots, positions fixed): a change of blend only sets attributes, it never creates a node or a line.
  // Lighting a pair or a jar never touches those 120 lines: the base layer only dims (an HTML layer's opacity — the
  // compositor's job) and a small top layer (a pool of 15 lines, the most one jar can have) draws what is lit.
  // Repainting all 120 lines to dim them cost a 168 ms frame on the kiosk.
  import type { Edge } from '../../lib/spices';
  let { nodes, edges, names, fills, highlight = null, focus = null, size = 300 }:
    { nodes: { id: string; share: number }[]; edges: Edge[]; names: Record<string, string>; fills: Record<string, string>;
      highlight?: [string, string] | null; focus?: string | null; size?: number } = $props();
  const SLOTS = 16, LIT = 15, CX = 150, CY = 150, R = 104;
  const pos = Array.from({ length: SLOTS }, (_, i) => {
    const a = -Math.PI / 2 + (i * 2 * Math.PI) / SLOTS;
    return { x: CX + Math.cos(a) * R, y: CY + Math.sin(a) * R, lx: CX + Math.cos(a) * (R + 26), ly: CY + Math.sin(a) * (R + 26) };
  });
  const PAIRS: [number, number][] = [];
  for (let i = 0; i < SLOTS; i++) for (let j = i + 1; j < SLOTS; j++) PAIRS.push([i, j]);
  // spread a small blend round the whole circle: n jars take every (16/n)-th slot
  let slotOf = $derived.by(() => {
    const n = nodes.length, m = new Map<string, number>();
    nodes.forEach((nd, k) => m.set(nd.id, n ? Math.floor((k * SLOTS) / n) : k));
    return m;
  });
  let atSlot = $derived.by(() => {
    const a: ({ id: string; share: number } | null)[] = Array(SLOTS).fill(null);
    for (const nd of nodes) a[slotOf.get(nd.id)!] = nd;
    return a;
  });
  let score = $derived(new Map(edges.flatMap((e) => [[`${slotOf.get(e.a)}-${slotOf.get(e.b)}`, e.score], [`${slotOf.get(e.b)}-${slotOf.get(e.a)}`, e.score]] as const)));
  const STROKE: Record<string, string> = { '3': '#2E9E4F', '2': '#4CB863', '1': '#9BCF9E', '0': '#CFC6BA', '-1': '#F2A07F', '-2': '#E0583A', '-3': '#B83224' };
  function style(s: number | undefined, on: boolean) {
    if (s === undefined || !on) return { o: 0, w: 0, c: 'none', d: '' };
    return { o: s === 0 ? 0.5 : 0.95, w: 1.4 + Math.abs(s) * 1.5, c: STROKE[String(s)], d: s < 0 ? '6 4' : s === 0 ? '2 4' : '' };
  }
  let lit = $derived.by(() => {
    if (!highlight && !focus) return [];
    const want = (e: Edge) => highlight ? highlight.includes(e.a) && highlight.includes(e.b) : e.a === focus || e.b === focus;
    return edges.filter(want).slice(0, LIT).map((e) => ({ i: slotOf.get(e.a)!, j: slotOf.get(e.b)!, s: e.score }));
  });
  let litNodes = $derived(new Set(highlight ? highlight : focus ? [focus] : []));
</script>

<div class="web" style:width="{size}px" style:height="{size}px">
  <div class="layer base" class:dim={!!(highlight || focus)}>
    <svg viewBox="0 0 300 300" width={size} height={size} aria-hidden="true">
      <circle class="halo" cx={CX} cy={CY} r={R} />
      {#each PAIRS as [i, j] (`${i}-${j}`)}
        {@const st = style(score.get(`${i}-${j}`), !!atSlot[i] && !!atSlot[j])}
        <line x1={pos[i].x} y1={pos[i].y} x2={pos[j].x} y2={pos[j].y} stroke={st.c} stroke-width={st.w} stroke-opacity={st.o}
              stroke-dasharray={st.d} stroke-linecap="round" />
      {/each}
      {#each pos as p, i (i)}
        {@const nd = atSlot[i]}
        <g opacity={nd ? 1 : 0}>
          <circle class="node" cx={p.x} cy={p.y} r={nd ? 7 + 16 * Math.sqrt(nd.share) : 0} fill={nd ? fills[nd.id] : 'none'} />
          <text x={p.lx} y={p.ly + 4} text-anchor="middle">{nd ? names[nd.id] : ''}</text>
        </g>
      {/each}
    </svg>
  </div>
  <div class="layer top">
    <svg viewBox="0 0 300 300" width={size} height={size} aria-hidden="true">
      {#each Array(LIT) as _, k (k)}
        {@const l = lit[k]}
        {@const st = l ? style(l.s, true) : style(undefined, false)}
        <line x1={l ? pos[l.i].x : 0} y1={l ? pos[l.i].y : 0} x2={l ? pos[l.j].x : 0} y2={l ? pos[l.j].y : 0} stroke={st.c}
              stroke-width={st.w + 1} stroke-opacity={st.o} stroke-dasharray={st.d} stroke-linecap="round" />
      {/each}
      {#each pos as p, i (i)}
        {@const nd = atSlot[i]}
        {@const on = !!nd && (litNodes.has(nd.id) || lit.some((l) => l.i === i || l.j === i))}
        <g opacity={on ? 1 : 0}>
          <circle class="node" cx={p.x} cy={p.y} r={nd ? 7 + 16 * Math.sqrt(nd.share) : 0} fill={nd ? fills[nd.id] : 'none'} />
          <text x={p.lx} y={p.ly + 4} text-anchor="middle">{nd && on ? names[nd.id] : ''}</text>
        </g>
      {/each}
    </svg>
  </div>
</div>

<style>
  .web { position: relative; flex: none; }
  .layer { position: absolute; inset: 0; }
  .base { will-change: opacity; }
  .base.dim { opacity: .22; }
  svg { display: block; overflow: visible; }
  .halo { fill: var(--paper); stroke: #E9DECD; stroke-width: 2; stroke-dasharray: 3 5; }
  .node { stroke: var(--ink); stroke-width: 3; }
  text { font: 800 11px var(--font-body); fill: var(--ink); paint-order: stroke; stroke: var(--paper); stroke-width: 3px; }
</style>
