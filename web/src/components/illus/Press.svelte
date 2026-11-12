<script lang="ts">
  // coffee/french-press: the press in five steps. The grounds drop in; a splash of water blooms them (bubbles); the
  // press fills, the lid and plunger go on and the brew darkens while a 4:00 badge shows; the plunger pushes the crust
  // down to the grounds; the coffee is poured into the cup beside it. Liquid, crust, plunger, cup, bubbles and badge
  // are HTML layers (transform/opacity, transitions between steps); the glass, frame and handle are one static drawing.
  import Chips from './Chips.svelte';
  import Card from './Card.svelte';

  let { lang }: { lang: 'en' | 'hu' } = $props();
  const STEPS = [
    { en: ['Coffee in', 'Preheat the press with hot water and pour it out. Coarse grounds in: about 6–7 g per 100 ml of water (1 : 15).'],
      hu: ['Kávé bele', 'Melegítsd át a kancsót forró vízzel, öntsd ki. Durvára őrölt kávé bele: kb. 6–7 g 100 ml vízhez (1 : 15).'] },
    { en: ['Bloom', 'Water just off the boil (93–96 °C: boil, wait 30 s). Pour only enough to wet the grounds and wait 30 seconds while they swell.'],
      hu: ['Virágoztatás', 'Épp forrás alatti víz (93–96 °C: forrald fel, várj 30 mp-et). Csak annyit önts, hogy átnedvesedjen, és várj 30 mp-et, amíg megduzzad.'] },
    { en: ['Fill & steep', 'Fill up, stir gently, lid on with the plunger up. Steep 4 minutes.'],
      hu: ['Feltöltés, ázás', 'Töltsd fel, keverd meg finoman, fedő rá felhúzott dugattyúval. Ázzon 4 percig.'] },
    { en: ['Press slowly', 'Push the plunger down slowly and evenly, 15–20 seconds. If it fights back, lift a little and go again.'],
      hu: ['Lassan lenyomni', 'Nyomd le a dugattyút lassan, egyenletesen, 15–20 mp alatt. Ha ellenáll, emeld meg kicsit, és újra.'] },
    { en: ['Pour it all', 'Pour everything straight away — coffee left on the grounds keeps brewing and turns bitter. Grounds go in the bin, not the sink.'],
      hu: ['Mind kiönteni', 'Azonnal öntsd ki az egészet — a zaccon hagyott kávé tovább ázik és megkeseredik. A zacc a kukába, ne a lefolyóba.'] },
  ];
  let step = $state(0);
  const IN = { x: 82, y: 72, w: 100, h: 156 };                 // inside the glass
  const LEVEL = [0, 0.26, 0.9, 0.9, 0.12];                      // liquid height (share of IN.h) per step
  const BREW = [0, 0.25, 1, 1, 1];                               // how dark it is
  let level = $derived(LEVEL[step]);
  const PRESS = 116;                                            // how far the plunger travels (px)
</script>

<div class="illus">
  <div class="draw"><div class="stage">
    <div class="glassbg" style:left="{IN.x}px" style:top="{IN.y}px" style:width="{IN.w}px" style:height="{IN.h}px"></div>
    <div class="liq water" style:left="{IN.x}px" style:top="{IN.y}px" style:width="{IN.w}px" style:height="{IN.h}px" style:transform="scaleY({level})"></div>
    <div class="liq brew" style:left="{IN.x}px" style:top="{IN.y}px" style:width="{IN.w}px" style:height="{IN.h}px"
         style:transform="scaleY({level})" style:opacity={BREW[step]} style:transition-duration="0.9s, {step === 2 ? 2.6 : 0.4}s"></div>
    <div class="grounds" style:left="{IN.x}px" style:top="{IN.y + IN.h - 22}px" style:width="{IN.w}px"></div>
    <!-- the crust floats on top while it blooms and steeps, rides down under the plunger, and joins the grounds -->
    <div class="crust" class:on={step >= 1 && step <= 3} style:left="{IN.x}px" style:width="{IN.w}px"
         style:top="{IN.y + IN.h - 34}px" style:transform="translateY({-(step === 1 ? 0.26 : step === 2 ? 0.9 : 0.14) * IN.h + 22}px)"></div>
    {#key step}
      {#if step === 1}
        {#each [0, 1, 2, 3, 4] as b}<div class="bub" style:left="{IN.x + 12 + b * 19}px" style:top="{IN.y + IN.h - 30}px" style:animation-delay="{b * 120}ms"></div>{/each}
      {/if}
      {#if step === 2}<div class="badge">4:00</div>{/if}
    {/key}
    <div class="plunger" class:on={step >= 2} style:transform={step >= 3 ? `translateY(${PRESS}px)` : step === 2 ? 'none' : 'translateY(-46px)'}>
      <!-- the rod is as long as the travel: up, the knob stands high above the lid; pressed, it rests just on it -->
      <svg viewBox="0 -90 260 350" aria-hidden="true">
        <rect class="rod" x="129" y="-70" width="6" height="150" />
        <ellipse class="knob" cx="132" cy="-70" rx="12" ry="9" />
        <rect class="disc" x="{IN.x + 2}" y="78" width="{IN.w - 4}" height="7" rx="3" />
        <path class="mesh" d="M{IN.x + 8},81.5 H{IN.x + IN.w - 8}" />
      </svg>
    </div>
    <svg class="frame" viewBox="0 0 260 260" aria-hidden="true">
      <path class="hand" d="M184,96 C226,96 226,196 184,196" />
      <path class="wall" d="M82,66 V226 Q82,232 88,232 H176 Q182,232 182,226 V66" />
      <rect class="base" x="72" y="230" width="120" height="10" rx="4" />
      <path class="band" d="M80,150 H184" />
      <path class="shine" d="M92,84 V214" /><path class="shine thin" d="M101,92 V140" />
    </svg>
    <div class="lid" class:on={step >= 2} style:transform={step >= 2 ? 'none' : 'translateY(-46px)'}>
      <svg viewBox="0 0 260 260" aria-hidden="true"><rect class="lidr" x="76" y="58" width="112" height="14" rx="5" /><path class="spout" d="M76,64 L66,58" /></svg>
    </div>
    <!-- the cup beside it fills on the last step -->
    <div class="cupfill" style:transform="scaleY({step === 4 ? 1 : 0})"></div>
    <svg class="cup" viewBox="0 0 60 60" aria-hidden="true">
      <path class="cw" d="M6,14 L9,46 Q10,52 16,52 H40 Q46,52 47,46 L50,14" /><path class="ch" d="M50,22 C62,22 62,40 49,40" />
    </svg>
  </div></div>
  <div class="side">
    <Chips labels={STEPS.map((s, i) => `${i + 1} ${s[lang][0]}`)} bind:sel={step} on="cocoa" />
    <Card title={`${step + 1}. ${STEPS[step][lang][0]}`} text={STEPS[step][lang][1]} />
  </div>
</div>

<style>
  .illus { display: flex; gap: 16px; align-items: flex-start; }
  .draw { position: relative; flex: none; width: 260px; height: 324px; }
  .stage { position: absolute; left: 0; top: 64px; width: 260px; height: 260px; }
  .glassbg { position: absolute; background: rgba(255, 255, 255, .72); }
  .liq { position: absolute; transform-origin: 50% 100%; transition-property: transform, opacity; transition-timing-function: cubic-bezier(.3, 1.2, .5, 1), ease; }
  .water { background: linear-gradient(180deg, #E2B97E, #C98B4E); transition-duration: .9s, .4s; }
  .brew { background: linear-gradient(180deg, #6B4226, #3B2416 50%, #2A190F); }
  .grounds { position: absolute; height: 22px; background: #5A3A22; animation: drop .6s cubic-bezier(.3, 1.4, .5, 1) .2s both;
             background-image: radial-gradient(rgba(255, 255, 255, .22) 1px, transparent 1.6px), radial-gradient(rgba(0, 0, 0, .3) 1px, transparent 1.6px);
             background-size: 6px 6px, 5px 5px; background-position: 0 0, 2px 3px; }
  @keyframes drop { from { opacity: 0; transform: translateY(-60px); } to { opacity: 1; transform: none; } }
  .crust { position: absolute; height: 12px; background: #7A5232; border-radius: 3px; opacity: 0;
           background-image: radial-gradient(rgba(255, 255, 255, .25) 1px, transparent 1.6px); background-size: 6px 6px;
           transition: transform 1.2s cubic-bezier(.45, .05, .4, 1), opacity .4s; }
  .crust.on { opacity: 1; }
  .bub { position: absolute; width: 9px; height: 9px; border-radius: 50%; border: 2px solid rgba(255, 240, 220, .95); opacity: 0; animation: bub 1.2s ease-out both; pointer-events: none; }
  @keyframes bub { 0% { opacity: 0; } 25% { opacity: 1; } 100% { opacity: 0; transform: translateY(-34px); } }
  .badge { position: absolute; left: 196px; top: 0px; font-family: var(--font-display); font-size: 22px; background: var(--butter); border: var(--outline) solid var(--ink);
           border-radius: 12px; padding: 0 8px; animation: pop .4s cubic-bezier(.34, 1.56, .64, 1) .3s both; }
  @keyframes pop { from { opacity: 0; transform: scale(.6); } to { opacity: 1; transform: none; } }
  .plunger, .lid, .frame { position: absolute; left: 0; top: 0; width: 260px; height: 260px; pointer-events: none; }
  .plunger { top: -90px; height: 350px; }
  .plunger svg { width: 260px; height: 350px; display: block; }
  .lid svg { width: 260px; height: 260px; display: block; }
  .plunger, .lid { opacity: 0; transition: transform 1.2s cubic-bezier(.45, .05, .4, 1), opacity .35s; }
  .plunger.on, .lid.on { opacity: 1; }
  .lid { transition-duration: .5s, .35s; }
  .rod { fill: #B9C2CC; stroke: var(--ink); stroke-width: 2.5; }
  .knob { fill: #2E2622; stroke: var(--ink); stroke-width: 3; }
  .disc { fill: #C8D0D8; stroke: var(--ink); stroke-width: 2.5; }
  .mesh { stroke: var(--ink); stroke-width: 1.5; stroke-dasharray: 2 3; }
  .lidr { fill: #C8D0D8; stroke: var(--ink); stroke-width: 3.5; }
  .spout { stroke: var(--ink); stroke-width: 3.5; stroke-linecap: round; }
  .wall { fill: none; stroke: var(--ink); stroke-width: 5; stroke-linejoin: round; }
  .hand { fill: none; stroke: #2E2622; stroke-width: 16; stroke-linecap: round; }
  .base { fill: #C8D0D8; stroke: var(--ink); stroke-width: 3.5; }
  .band { stroke: #C8D0D8; stroke-width: 6; opacity: .9; }
  .shine { stroke: #fff; stroke-width: 6; stroke-linecap: round; opacity: .75; } .shine.thin { stroke-width: 3; }
  .cupfill { position: absolute; left: 10px; top: 212px; width: 37px; height: 34px; background: #3B2416; transform-origin: 50% 100%;
             border-radius: 0 0 6px 6px; transition: transform 1s cubic-bezier(.3, 1.2, .5, 1) .2s; }
  .cup { position: absolute; left: 0; top: 196px; width: 60px; height: 60px; pointer-events: none; }
  .cw { fill: none; stroke: var(--ink); stroke-width: 3.5; stroke-linejoin: round; }
  .ch { fill: none; stroke: var(--ink); stroke-width: 3.5; stroke-linecap: round; }
  .side { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 12px; }
  @media (max-aspect-ratio: 1/1) { .illus { flex-direction: column; align-items: center; } .side { width: 100%; } }
</style>
