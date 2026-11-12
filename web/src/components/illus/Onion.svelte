<script lang="ts">
  // knife/onion: the four steps of dicing an onion, on the half onion's ring face. Each step adds its cuts and keeps
  // the earlier ones: the down cuts draw in from the top one after another, the flat cuts slide in from the side,
  // and on the last step the dice tumble out onto the board. The knife moves to where each step happens. Every cut,
  // die and the knife are HTML layers (transform/opacity); the onion is one static drawing.
  let { lang }: { lang: 'en' | 'hu' } = $props();
  const STEPS = [
    { en: ['1 Halve', 'Cut it in half from root to tip. Peel it, leave the root on — it holds the layers together.'],
      hu: ['1 Félbe', 'Vágd félbe a gyökértől a csúcsig. Hámozd meg, a gyökerét hagyd rajta — az tartja össze a rétegeket.'] },
    { en: ['2 Down cuts', 'Flat side down: cut from the tip towards the root, stopping short of it. Closer cuts = finer dice.'],
      hu: ['2 Függőleges vágások', 'Vágott felével lefelé: a csúcs felől a gyökér felé vágj, mielőtt elérnéd, állj meg. Sűrűbb vágás = apróbb kocka.'] },
    { en: ['3 Flat cuts', 'One or two cuts parallel to the board, towards the root — carefully, claw on top.'],
      hu: ['3 Vízszintes vágások', 'Egy-két vágás a deszkával párhuzamosan, a gyökér felé — óvatosan, a karomfogással felül.'] },
    { en: ['4 Slice across', 'Now slice across: the dice falls away. Stop at the root and save it for stock.'],
      hu: ['4 Keresztbe', 'Most szeleteld keresztben: a kocka magától leválik. A gyökérnél állj meg, és tedd el alaplének.'] },
  ];
  let step = $state(0);
  const CX = 170, BASE = 176, R = 132;                      // the half onion's ring face: centre, board line, radius
  const top = (x: number) => BASE - Math.sqrt(Math.max(0, R * R - (x - CX) ** 2));
  const DOWN = [-96, -64, -32, 0, 32, 64, 96].map((d) => CX + d);
  const FLAT = [BASE - 40, BASE - 82];
  const half = (y: number) => Math.sqrt(R * R - (BASE - y) ** 2);
  // the dice on the board in front of the onion
  const DICE = Array.from({ length: 14 }, (_, i) => ({ x: CX - 120 + (i % 7) * 36 + (i > 6 ? 18 : 0), y: BASE + 14 + (i > 6 ? 24 : 0), r: (i * 37) % 40 - 20 }));
  // where the knife's TIP is for each step, and its angle (the handle swings up and away from the onion):
  // lying on the board · coming down at the right · entering flat from the right · slicing across at the left
  const KNIFE = [
    { x: 196, y: 204, r: 0 }, { x: 252, y: 112, r: -55 }, { x: 226, y: BASE - 82, r: 0 }, { x: 82, y: 128, r: -125 },
  ];
</script>

<div class="illus">
  <div class="draw">
    <svg class="onion" viewBox="0 0 340 250" aria-hidden="true">
      <path class="board" d="M10,{BASE + 2} H330 V{BASE + 54} Q330,{BASE + 62} 322,{BASE + 62} H18 Q10,{BASE + 62} 10,{BASE + 54} Z" />
      <path class="grain" d="M30,{BASE + 20} H150 M190,{BASE + 34} H310 M60,{BASE + 48} H240" />
      <path class="skin" d="M{CX - R - 6},{BASE} A{R + 6},{R + 6} 0 0 1 {CX + R + 6},{BASE} Z" />
      {#each [R, R - 26, R - 50, R - 74, R - 96, R - 116] as r, i}
        <path class="ring" class:core={i === 5} d="M{CX - r},{BASE} A{r},{r} 0 0 1 {CX + r},{BASE}" />
      {/each}
    </svg>
    {#each DOWN as x, i}
      <div class="cut down" class:on={step >= 1} style:left="{x - 1.5}px" style:top="{top(x)}px" style:height="{BASE - top(x)}px"
           style:transition-delay="{step >= 1 ? i * 90 : 0}ms"></div>
    {/each}
    {#each FLAT as y, i}
      <div class="cut flat" class:on={step >= 2} style:left="{CX - half(y)}px" style:top="{y - 1.5}px" style:width="{2 * half(y)}px"
           style:transition-delay="{step >= 2 ? i * 160 : 0}ms"></div>
    {/each}
    {#each DICE as d, i}
      <div class="die" class:on={step >= 3} style:left="{d.x}px" style:top="{d.y}px" style:--r="{d.r}deg" style:transition-delay="{step >= 3 ? i * 45 : 0}ms"></div>
    {/each}
    <div class="knife" style:transform="translate({KNIFE[step].x}px, {KNIFE[step].y - 12.5}px) rotate({KNIFE[step].r}deg)">
      <svg viewBox="0 0 150 34" aria-hidden="true">
        <path class="blade" d="M4,22 Q30,4 96,6 H100 V28 H8 Q3,28 4,22 Z" />
        <path class="bolster" d="M98,5 H106 V29 H98 Z" />
        <rect class="handle" x="105" y="8" width="42" height="18" rx="8" />
        <circle class="rivet" cx="118" cy="17" r="2.4" /><circle class="rivet" cx="134" cy="17" r="2.4" />
      </svg>
    </div>
  </div>
  <div class="side">
    <div class="chips">
      {#each STEPS as s, i}<button class="chip pressable" class:on={i === step} onclick={() => (step = i)}>{s[lang][0]}</button>{/each}
    </div>
    {#key step}<p class="say">{STEPS[step][lang][1]}</p>{/key}
  </div>
</div>

<style>
  .illus { display: flex; gap: 16px; align-items: flex-start; }
  .draw { position: relative; flex: none; width: 340px; height: 250px; }
  .onion { position: absolute; inset: 0; width: 340px; height: 250px; }
  .board { fill: #D9A066; stroke: var(--ink); stroke-width: 3.5; }
  .grain { stroke: #B97E45; stroke-width: 2.5; stroke-linecap: round; }
  .skin { fill: #C98A3D; stroke: var(--ink); stroke-width: 4; }
  .ring { fill: #F6ECD6; stroke: #D9C29A; stroke-width: 3; }
  .ring:first-of-type { stroke: var(--ink); }
  .ring.core { fill: #EDE0BE; }
  .cut { position: absolute; background: var(--ink); border-radius: 2px; transition: transform .35s cubic-bezier(.3, 1.2, .5, 1); pointer-events: none; }
  .down { width: 3px; transform-origin: 50% 0; transform: scaleY(0); }
  .flat { height: 3px; transform-origin: 100% 50%; transform: scaleX(0); }
  .cut.on { transform: none; }
  .die { position: absolute; width: 20px; height: 18px; border-radius: 4px; background: #F6ECD6; border: 2.5px solid var(--ink); opacity: 0;
         transform: translateY(-46px) rotate(0deg); transition: transform .45s cubic-bezier(.3, 1.5, .5, 1), opacity .2s; pointer-events: none; }
  .die.on { opacity: 1; transform: rotate(var(--r)); }
  .knife { position: absolute; left: 0; top: 0; width: 110px; height: 25px; transform-origin: 0 50%;
           transition: transform .6s cubic-bezier(.34, 1.3, .64, 1); pointer-events: none; }
  .knife svg { width: 110px; height: 25px; display: block; }
  .blade { fill: #DCE3EA; stroke: var(--ink); stroke-width: 3; stroke-linejoin: round; }
  .bolster { fill: #A9B4BF; stroke: var(--ink); stroke-width: 2.5; }
  .handle { fill: #3A2E28; stroke: var(--ink); stroke-width: 2.5; }
  .rivet { fill: #DCE3EA; }
  .side { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 12px; }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; }
  .chip { min-height: var(--touch); min-width: var(--touch); padding: 0 14px; border-radius: 999px; border: var(--outline) solid var(--ink);
          background: var(--paper); color: var(--ink); font: inherit; font-weight: 800; font-size: 15px; }
  .chip.on { background: var(--butter); }
  .say { margin: 0; background: var(--paper); border: var(--outline) solid var(--ink); border-radius: 16px; padding: 10px 14px; box-shadow: 0 4px 0 var(--ink);
         font-weight: 700; font-size: 15px; line-height: 1.35; animation: pop .35s cubic-bezier(.34, 1.56, .64, 1) both; }
  @keyframes pop { from { opacity: 0; transform: scale(.92) translateY(4px); } to { opacity: 1; transform: none; } }
  @media (max-aspect-ratio: 1/1) { .illus { flex-direction: column; align-items: center; } .side { width: 100%; } }
</style>
