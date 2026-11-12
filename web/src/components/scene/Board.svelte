<script lang="ts">
  // The cutting board on the idle counter: a wooden board with grain and a handle, a half-chopped carrot with its
  // leafy top, carrot coins, and a chef's knife. `chop` plays the chop act: the knife rises from where it rests, rocks
  // down four times on the carrot's cut end (pivot at the handle, like a real rock-chop) and a fresh coin pops out with
  // each cut. Every moving part is a div (compositor layer) around a static svg — never an animated svg child.
  import { box, vb } from '../../lib/mascot';
  let { chop = false, size = 400 }: { chop?: boolean; size?: number } = $props();
  const W = 400;
  const coin = (x: number, y: number) => ({ x, y });
  const OLD = [coin(190, 70), coin(207, 75), coin(223, 70)];
  const NEW = [coin(198, 88), coin(216, 90), coin(233, 86), coin(250, 90)];
</script>

<div class="board" class:chop style:zoom={size / W} aria-hidden="true">
  <svg class="still" viewBox="0 0 400 130">
    <!-- the board: its edge (darker, shifted down) under the top face -->
    <path class="edge ol" transform="translate(0 11)" d="M22,66 C22,52 30,48 46,48 H292 C304,48 308,52 316,56 L344,58 C358,60 358,76 344,78 L316,80 C306,84 300,90 288,90 H46 C30,90 22,84 22,74 Z" />
    <path class="top ol" d="M22,66 C22,52 30,48 46,48 H292 C304,48 308,52 316,56 L344,58 C358,60 358,76 344,78 L316,80 C306,84 300,90 288,90 H46 C30,90 22,84 22,74 Z" />
    <path class="grain" d="M40,60 C90,56 150,64 210,58 S290,62 300,60 M46,72 C110,68 170,78 240,70 S290,74 304,72 M60,82 C120,80 180,86 260,80" />
    <circle class="hole ol" cx="338" cy="68" r="5" stroke-width="2.5" />
    <path class="topshine" d="M40,53 H286" />
    <!-- the carrot: leafy top on the left, the cut end on the right -->
    <path class="leaf ol" stroke-width="2.6" d="M58,66 C44,52 32,44 24,30 C38,34 52,46 61,61 Z" />
    <path class="leaf2 ol" stroke-width="2.6" d="M60,62 C54,44 52,30 56,16 C64,30 66,46 64,61 Z" />
    <path class="leaf ol" stroke-width="2.6" d="M63,63 C70,48 80,38 94,32 C88,46 78,56 66,65 Z" />
    <path class="carrot ol" stroke-width="3" d="M60,58 C92,55 140,58 176,61 C181,64 181,74 176,77 C140,79 92,80 60,77 C52,73 52,62 60,58 Z" />
    <path class="ridge" d="M84,60 q2,7 0,15 M106,60 q2,8 0,16 M128,61 q2,8 0,15 M150,62 q2,7 0,14" />
    <path class="carrotshine" d="M70,61 C102,59 140,61 168,64" />
    <ellipse class="cut ol" cx="177" cy="69" rx="5.5" ry="8.5" stroke-width="2.5" /><ellipse class="core" cx="177.5" cy="69" rx="2.4" ry="4" />
    {#each OLD as c}
      <ellipse class="cut ol" cx={c.x} cy={c.y} rx="7.5" ry="9" stroke-width="2.5" /><ellipse class="core" cx={c.x} cy={c.y} rx="3.4" ry="4.4" />
    {/each}
  </svg>
  {#each NEW as c, i}
    <div class="part coin n{i + 1}" style={box(c.x - 11, c.y - 13, 22, 26, c.x, c.y + 8)}>
      <svg viewBox={vb(c.x - 11, c.y - 13, 22, 26)}>
        <ellipse class="cut ol" cx={c.x} cy={c.y} rx="7.5" ry="9" stroke-width="2.5" /><ellipse class="core" cx={c.x} cy={c.y} rx="3.4" ry="4.4" />
      </svg>
    </div>
  {/each}
  <!-- the chef's knife, drawn in its chopping position; the rest pose is a transform -->
  <div class="part knife" style={box(140, 24, 196, 40, 326, 44)}>
    <svg viewBox={vb(140, 24, 196, 40)}>
      <path class="steel ol" stroke-width="3" d="M252,30 L252,58 L168,58 Q150,57 146,52 Q178,36 252,30 Z" />
      <path class="spine" d="M182,38 Q216,31 250,31.5" />
      <path class="bevel" d="M166,54.5 H248" />
      <rect class="bolster ol" x="250" y="30" width="9" height="27" rx="2" stroke-width="3" />
      <path class="handle ol" stroke-width="3" d="M258,33 H316 Q327,33 327,44 Q327,55 316,55 H258 Z" />
      <circle class="rivet" cx="273" cy="44" r="3" /><circle class="rivet" cx="290" cy="44" r="3" /><circle class="rivet" cx="307" cy="44" r="3" />
    </svg>
  </div>
</div>

<style>
  .board { position: relative; width: 400px; height: 130px; }
  .still { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; }
  .part { position: absolute; will-change: transform; }
  .part > svg { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; display: block; }
  .ol { stroke: var(--ink); stroke-linejoin: round; }
  .edge { fill: #B47A44; stroke-width: 3.5; } .top { fill: #DCA76B; stroke-width: 3.5; }
  .grain { fill: none; stroke: #C68E52; stroke-width: 2; stroke-linecap: round; }
  .topshine { stroke: #F3C894; stroke-width: 3; stroke-linecap: round; opacity: .8; }
  .hole { fill: #8A5A30; }
  .leaf { fill: #5DBB63; } .leaf2 { fill: #3E8E41; }
  .carrot { fill: #F28C28; } .ridge { fill: none; stroke: #D06A12; stroke-width: 2; stroke-linecap: round; }
  .carrotshine { fill: none; stroke: #FFB070; stroke-width: 2.6; stroke-linecap: round; opacity: .85; }
  .cut { fill: #F28C28; } .core { fill: #FFB070; }
  .steel { fill: #E4E9ED; } .spine { fill: none; stroke: #B5BEC7; stroke-width: 3; stroke-linecap: round; }
  .bevel { stroke: #fff; stroke-width: 2.4; stroke-linecap: round; opacity: .95; }
  .bolster { fill: #9AA3AD; } .handle { fill: #2E2723; } .rivet { fill: #CFD5DA; stroke: var(--ink); stroke-width: 1.4; }

  /* rest: the knife lies on the board to the right; the new coins are not cut yet */
  .knife { transform: translate(64px, 22px) rotate(4deg); }
  .coin { opacity: 0; }
  /* chop: rise, rock down on the cut end four times (a coin per cut), back to rest; the coins fade at the end */
  .chop .knife { animation: chop 2.9s both; }
  @keyframes chop {
    0% { transform: translate(64px, 22px) rotate(4deg); }
    14% { transform: translate(0, -6px) rotate(-16deg); animation-timing-function: ease-in; }
    21% { transform: translate(0, 0) rotate(0deg); animation-timing-function: ease-out; }
    30% { transform: translate(0, -2px) rotate(-14deg); animation-timing-function: ease-in; }
    37% { transform: translate(0, 0) rotate(0deg); animation-timing-function: ease-out; }
    46% { transform: translate(0, -2px) rotate(-14deg); animation-timing-function: ease-in; }
    53% { transform: translate(0, 0) rotate(0deg); animation-timing-function: ease-out; }
    62% { transform: translate(0, -2px) rotate(-14deg); animation-timing-function: ease-in; }
    69% { transform: translate(0, 0) rotate(0deg); }
    84%, 100% { transform: translate(64px, 22px) rotate(4deg); }
  }
  .chop .coin { animation: coin 2.9s both; }
  .chop .n2 { animation-delay: .46s; } .chop .n3 { animation-delay: .93s; } .chop .n4 { animation-delay: 1.39s; }
  @keyframes coin {
    0%, 21% { opacity: 0; transform: translate(-14px, -10px) scale(.3); }
    25% { opacity: 1; transform: translate(-4px, -14px) scale(1.1) rotate(-20deg); }
    31% { transform: translate(0, 0) scale(1) rotate(0deg); }
    34% { transform: translate(0, -3px) scale(1, .95); }
    37%, 78% { opacity: 1; transform: translate(0, 0); }
    100% { opacity: 0; transform: translate(0, 0); }
  }
</style>
