<script lang="ts">
  // A pot of basil and a salt & pepper pair on the idle counter. `sway` plays a breeze through the leaves (the leaf
  // crown is a div pivoting at the soil, so the sway is a compositor-only rotation).
  import { box, vb } from '../../lib/mascot';
  let { sway = false, size = 210 }: { sway?: boolean; size?: number } = $props();
  const LEAVES: [number, number, number, number][] = [   // x, y, angle, size
    [38, 58, -38, 1], [84, 54, 34, 1], [50, 38, -18, .95], [74, 32, 20, .95], [42, 20, -34, .85], [80, 14, 30, .85], [60, 8, 0, .8], [62, 46, 6, .9],
  ];
</script>

<div class="herbs" class:sway style:zoom={size / 210} aria-hidden="true">
  <!-- salt and pepper -->
  <svg class="still" viewBox="0 0 210 150">
    <g>
      <rect class="salt ol" x="128" y="96" width="30" height="46" rx="12" stroke-width="3" />
      <path class="cap ol" stroke-width="3" d="M131,100 Q131,84 143,84 Q155,84 155,100 Z" />
      <circle class="dot" cx="139" cy="92" r="1.6" /><circle class="dot" cx="143" cy="89" r="1.6" /><circle class="dot" cx="147" cy="92" r="1.6" />
      <path class="shine" d="M134,104 V132" />
      <rect class="pepper ol" x="166" y="92" width="30" height="50" rx="12" stroke-width="3" />
      <path class="cap ol" stroke-width="3" d="M169,96 Q169,80 181,80 Q193,80 193,96 Z" />
      <circle class="dot" cx="177" cy="88" r="1.6" /><circle class="dot" cx="181" cy="85" r="1.6" /><circle class="dot" cx="185" cy="88" r="1.6" />
      <path class="shine pep" d="M172,100 V130" />
    </g>
    <!-- the pot -->
    <path class="pot ol" stroke-width="3.5" d="M18,86 L104,86 L95,144 L27,144 Z" />
    <rect class="rim ol" x="12" y="76" width="98" height="16" rx="5" stroke-width="3.5" />
    <path class="potshine" d="M28,98 L33,136" />
    <ellipse class="soil" cx="61" cy="78" rx="42" ry="5" />
  </svg>
  <div class="part crown" style={box(0, -10, 120, 96, 61, 80)}>
    <svg viewBox={vb(0, -10, 120, 96)}>
      <path class="stem" d="M61,80 C60,66 52,58 40,56 M61,80 C62,64 72,58 84,52 M61,78 C60,58 54,46 50,36 M61,76 C63,56 70,44 74,30 M58,60 C52,40 46,30 42,18 M64,56 C70,38 76,26 80,12 M61,70 C60,40 60,20 60,6" />
      {#each LEAVES as [x, y, a, k]}
        <g transform="rotate({a} {x} {y})">
          <ellipse class="leafbody ol" cx={x} cy={y} rx={9 * k} ry={14 * k} stroke-width="2.4" />
          <path class="vein" d="M{x},{y - 11 * k} V{y + 11 * k}" />
        </g>
      {/each}
    </svg>
  </div>
</div>

<style>
  .herbs { position: relative; width: 210px; height: 150px; }
  .still { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; }
  .part { position: absolute; will-change: transform; }
  .part > svg { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; display: block; }
  .ol { stroke: var(--ink); stroke-linejoin: round; }
  .pot { fill: #D9703F; } .rim { fill: #E8875A; } .soil { fill: #5A3A22; }
  .potshine { stroke: #F2A27A; stroke-width: 4; stroke-linecap: round; }
  .stem { fill: none; stroke: #3E8E41; stroke-width: 3; stroke-linecap: round; }
  .leafbody { fill: #62C46A; } .vein { stroke: #3E8E41; stroke-width: 1.8; stroke-linecap: round; }
  .salt { fill: #FFFFFF; } .pepper { fill: #4A423C; } .cap { fill: #C9CFD5; } .dot { fill: var(--ink); }
  .shine { stroke: #E6E0D6; stroke-width: 3; stroke-linecap: round; } .shine.pep { stroke: #6E655E; }
  .sway .crown { animation: sway 2.6s ease-in-out both; }
  @keyframes sway { 15% { transform: rotate(-5deg); } 35% { transform: rotate(4deg); } 55% { transform: rotate(-3deg); } 75% { transform: rotate(1.5deg); } }
</style>
