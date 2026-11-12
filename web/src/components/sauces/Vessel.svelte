<script lang="ts" module>
  let n = 0;
  // The five vessels in one 100 x 100 drawing, standing on y = 94: the wall, what pours (a spout, a handle, a lid or a
  // cap), and the inside the sauce fills (its top and bottom, for the level). A vessel that changes (a family detected
  // in the editor) only changes these `d` attributes: the svg is built once.
  const SHAPES = {
    jug: { wall: 'M30,18 H70 L68,30 Q80,58 74,84 Q72,94 62,94 H38 Q28,94 26,84 Q20,58 32,30 Z',
           extra: 'M30,18 L16,12 Q18,22 31,27 M70,34 Q90,34 88,52 Q86,68 71,70', top: 30, bottom: 93 },
    sauceboat: { wall: 'M6,46 Q20,52 32,52 H76 Q90,50 94,44 Q92,72 70,80 H36 Q16,76 6,46 Z',
                 extra: 'M42,80 L38,92 H68 L64,80 M88,54 Q100,46 93,36', top: 50, bottom: 80 },
    bowl: { wall: 'M8,44 H92 Q90,80 64,88 H36 Q10,80 8,44 Z', extra: 'M38,88 L36,94 H64 L62,88', top: 46, bottom: 88 },
    bottle: { wall: 'M42,10 H58 V26 Q74,34 74,50 V86 Q74,94 66,94 H34 Q26,94 26,86 V50 Q26,34 42,26 Z',
              extra: 'M40,2 H60 V10 H40 Z', top: 30, bottom: 93 },
    jar: { wall: 'M20,26 H80 V86 Q80,94 72,94 H28 Q20,94 20,86 Z', extra: 'M16,12 H84 V26 H16 Z', top: 28, bottom: 93 },
  } as const;
</script>

<script lang="ts">
  // A sauce in its vessel — our own drawing, after the spice jar: a jug, a sauceboat, a bowl, a bottle or a jar (the
  // family's), the contents in the sauce's colour with a soft wave on top. Static svg: nothing in it animates (a screen
  // moves the HTML wrapper). An empty one (a new sauce) is dashed with a plus.
  import type { Vessel } from '../../lib/sauces';
  let { vessel = 'jug', fill = '#E8DCC4', size = 120, level = 0.72, empty = false, ribbon = '' }:
    { vessel?: Vessel; fill?: string; size?: number; level?: number; empty?: boolean; ribbon?: string } = $props();
  const uid = `vessel${++n}`;
  let sh = $derived(SHAPES[vessel] ?? SHAPES.jug);
  let y = $derived(sh.bottom - (sh.bottom - sh.top) * Math.max(0, Math.min(1, level)));
  let wave = $derived(`M0,${y} Q25,${y - 3} 50,${y} T100,${y} V100 H0 Z`);
</script>

<span class="vessel" style:width="{size}px" style:height="{size}px">
  <svg viewBox="0 0 100 100" width={size} height={size} aria-hidden="true">
    <defs><clipPath id="{uid}-in"><path d={sh.wall} /></clipPath></defs>
    <path class="glaze" d={sh.wall} />
    <g clip-path="url(#{uid}-in)" class:gone={empty}>
      <path d={wave} fill={fill} />
      <path class="sheen" d="M0,{y + 1.5} Q25,{y - 1.5} 50,{y + 1.5}" />
    </g>
    <path class="wall" class:dashed={empty} d={sh.wall} />
    <path class="extra" class:dashed={empty} d={sh.extra} />
    <path class="shine" d="M{vessel === 'sauceboat' ? 22 : vessel === 'bowl' ? 20 : 34},{sh.top + 8} v{Math.max(6, (sh.bottom - sh.top) * 0.45)}" />
    <path class="plus" class:gone={!empty} d="M50,{(sh.top + sh.bottom) / 2 - 12} v24 M38,{(sh.top + sh.bottom) / 2} h24" />
  </svg>
  <span class="ribbon" class:gone={!ribbon}>{ribbon}</span>
</span>

<style>
  .vessel { position: relative; display: inline-block; flex: none; }
  svg { display: block; overflow: visible; }
  .glaze { fill: #FBF7EF; }
  .wall, .extra { fill: none; stroke: var(--ink); stroke-width: 3.4; stroke-linejoin: round; stroke-linecap: round; }
  .dashed { stroke-dasharray: 7 5; }
  .sheen { fill: none; stroke: rgba(255, 255, 255, .45); stroke-width: 2.4; stroke-linecap: round; }
  .shine { stroke: #fff; stroke-width: 4; stroke-linecap: round; opacity: .7; }
  .plus { stroke: var(--ink); stroke-width: 6; stroke-linecap: round; opacity: .55; }
  .gone { display: none; }
  .ribbon { position: absolute; left: -6%; top: 6%; background: var(--butter); color: var(--ink); border: 2px solid var(--ink);
            border-radius: 3px; padding: 1px 5px; font-weight: 900; font-size: 11px; transform: rotate(-12deg); text-transform: uppercase;
            letter-spacing: .03em; }
</style>
