<script lang="ts">
  // coffee/moka: the kotyogós, cut away. Water fills the bottom to the valve; coffee fills the basket; the lid opens and
  // the flame lights (bubbles in the water); the coffee rises out of the central column while the water goes down; it
  // gurgles — "kotyog!" — the flame goes out and cold water runs down the base. Water, coffee, flame, lid and the
  // little effects are HTML layers (transform/opacity); the pot is one static drawing.
  import Chips from './Chips.svelte';
  import Card from './Card.svelte';

  let { lang }: { lang: 'en' | 'hu' } = $props();
  const STEPS = [
    { en: ['Water', 'Fill the bottom with hot water up to just below the safety valve — never above it.'],
      hu: ['Víz', 'Az alját töltsd fel forró vízzel, épp a biztonsági szelep alá — soha ne fölé.'] },
    { en: ['Coffee', 'Fill the basket with fine-medium coffee (a little coarser than espresso) and level it with a finger — don’t press it down.'],
      hu: ['Kávé', 'A szűrőt töltsd meg közepesen finomra őrölt kávéval (kicsit durvábbra, mint az eszpresszóé), és simítsd el az ujjaddal — ne nyomkodd le.'] },
    { en: ['Heat', 'Screw it together tight (with a cloth — the base is hot). Medium-low heat, lid open so you can watch.'],
      hu: ['Tűzre', 'Csavard össze szorosan (konyharuhával — az alja forró). Közepes-alacsony láng, nyitott fedővel, hogy lásd.'] },
    { en: ['It rises', 'The coffee comes up like warm honey. A strong jet means the heat is too high — turn it down.'],
      hu: ['Feljön', 'A kávé meleg mézként csordogál fel. Ha erősen spriccel, túl nagy a láng — vedd lejjebb.'] },
    { en: ['Kotyog!', 'When it starts to gurgle, take it off the heat and cool the base under the cold tap. Stir, then pour.'],
      hu: ['Kotyog!', 'Amikor kotyogni kezd, vedd le a tűzről, és az alját hűtsd le hideg csap alatt. Keverd meg, aztán töltsd ki.'] },
  ];
  let step = $state(0);
  const TOP = { x: 88, y: 72, w: 84, h: 82 }, BOIL = { x: 86, y: 176, w: 88, h: 82 }, BASK = { x: 92, y: 158, w: 76, h: 16 };
  const WATER = [0.7, 0.7, 0.7, 0.26, 0.12], RISE = [0, 0, 0, 0.74, 0.82];
</script>

<div class="illus">
  <div class="draw">
    <div class="inner" style:left="{TOP.x}px" style:top="{TOP.y}px" style:width="{TOP.w}px" style:height="{TOP.h}px"></div>
    <div class="inner" style:left="{BOIL.x}px" style:top="{BOIL.y}px" style:width="{BOIL.w}px" style:height="{BOIL.h}px"></div>
    <div class="water" style:left="{BOIL.x}px" style:top="{BOIL.y}px" style:width="{BOIL.w}px" style:height="{BOIL.h}px" style:transform="scaleY({WATER[step]})"></div>
    <div class="coffee" style:left="{TOP.x}px" style:top="{TOP.y}px" style:width="{TOP.w}px" style:height="{TOP.h}px" style:transform="scaleY({RISE[step]})"></div>
    <div class="basket" class:on={step >= 1} style:left="{BASK.x}px" style:top="{BASK.y}px" style:width="{BASK.w}px" style:height="{BASK.h}px"></div>
    <div class="flame" class:on={step === 2 || step === 3}>
      {#each [0, 1, 2, 3, 4] as f}<span style:left="{84 + f * 22}px"></span>{/each}
    </div>
    {#key step}
      {#if step === 2}
        {#each [0, 1, 2, 3] as b}<div class="bub" style:left="{BOIL.x + 14 + b * 20}px" style:top="{BOIL.y + BOIL.h - 14}px" style:animation-delay="{300 + b * 150}ms"></div>{/each}
      {/if}
      {#if step === 3}
        {#each [0, 1, 2] as d}<div class="drop" style:--dx="{(d - 1) * 14}px" style:animation-delay="{d * 220}ms"></div>{/each}
      {/if}
      {#if step === 4}
        {#each [0, 1, 2] as p}<div class="puff" style:left="{114 + p * 12}px" style:animation-delay="{p * 200}ms"></div>{/each}
        <div class="say">kotyog-<br />kotyog!</div>
        {#each [0, 1, 2, 3] as c}<div class="cold" style:left="{196 + (c % 2) * 8}px" style:animation-delay="{700 + c * 180}ms"></div>{/each}
      {/if}
    {/key}
    <svg class="pot" viewBox="0 0 260 290" aria-hidden="true">
      <!-- the bakelite handle, the top chamber with its spout, the central column, the waist, the boiler and its valve -->
      <path class="handle" d="M186,80 C226,80 228,92 224,128 C222,140 206,142 182,140" />
      <path class="alu" d="M84,156 L74,66 H186 L176,156 Z" />
      <path class="alu" d="M84,172 L70,262 H190 L176,172 Z" />
      <path class="facet" d="M96,150 L90,72 M164,150 L170,72 M94,178 L86,256 M166,178 L174,256" />
      <path class="spout" d="M76,68 Q66,62 56,58 L60,70 Q70,72 77,78" />
      <!-- the waist (the screw thread) as two side clamps, so the basket shows through the cut-away -->
      <rect class="waist" x="78" y="154" width="16" height="20" rx="3" /><rect class="waist" x="166" y="154" width="16" height="20" rx="3" />
      <path class="thread" d="M94,156 H166 M94,172 H166" />
      <path class="column" d="M126,154 V98 H134 V154" />
      <circle class="valve" cx="186" cy="198" r="6" />
      <path class="cut" d="M{TOP.x},{TOP.y} H{TOP.x + TOP.w} V{TOP.y + TOP.h} H{TOP.x} Z M{BOIL.x},{BOIL.y} H{BOIL.x + BOIL.w} V{BOIL.y + BOIL.h} H{BOIL.x} Z" />
      <path class="stove" d="M60,286 H200" />
    </svg>
    <div class="lid" class:open={step >= 2}>
      <svg viewBox="0 0 260 290" aria-hidden="true"><path class="lidp" d="M72,66 Q130,44 188,66 Z" /><circle class="knob" cx="130" cy="50" r="6" /></svg>
    </div>
  </div>
  <div class="side">
    <Chips labels={STEPS.map((s, i) => `${i + 1} ${s[lang][0]}`)} bind:sel={step} on="cocoa" />
    <Card title={`${step + 1}. ${STEPS[step][lang][0]}`} text={STEPS[step][lang][1]} />
  </div>
</div>

<style>
  .illus { display: flex; gap: 16px; align-items: flex-start; }
  .draw { position: relative; flex: none; width: 260px; height: 290px; }
  .inner { position: absolute; background: linear-gradient(90deg, #D7DCE1, #EEF1F4 40%, #D7DCE1); }
  .water { position: absolute; transform-origin: 50% 100%; background: linear-gradient(180deg, #A8DBF5, #5BB5F0);
           transition: transform 1.8s cubic-bezier(.4, 0, .3, 1); }
  .coffee { position: absolute; transform-origin: 50% 100%; background: linear-gradient(180deg, #A0673C, #5A3A22 30%, #3B2416);
            transition: transform 2.2s cubic-bezier(.4, 0, .3, 1); }
  .basket { position: absolute; background: #5A3A22; opacity: 0; transform: translateY(-30px);
            background-image: radial-gradient(rgba(255, 255, 255, .25) 1px, transparent 1.6px); background-size: 5px 5px;
            transition: transform .5s cubic-bezier(.3, 1.4, .5, 1), opacity .3s; }
  .basket.on { opacity: 1; transform: none; }
  .flame { position: absolute; left: 0; top: 264px; width: 260px; height: 22px; opacity: 0; transition: opacity .4s; pointer-events: none; }
  .flame.on { opacity: 1; }
  .flame span { position: absolute; top: 0; width: 14px; height: 20px; border-radius: 50% 50% 40% 40% / 70% 70% 30% 30%;
                background: radial-gradient(circle at 50% 75%, #FFE08A, #5BB5F0 70%); border: 2px solid var(--ink); }
  .bub { position: absolute; width: 8px; height: 8px; border-radius: 50%; border: 2px solid #fff; opacity: 0; animation: bub 1.1s ease-out both; pointer-events: none; }
  @keyframes bub { 0% { opacity: 0; } 25% { opacity: 1; } 100% { opacity: 0; transform: translateY(-40px); } }
  .drop { position: absolute; left: 127px; top: 96px; width: 7px; height: 9px; border-radius: 50% 50% 50% 50% / 60% 60% 40% 40%; background: #5A3A22;
          opacity: 0; animation: spurt .7s ease-out 3 both; pointer-events: none; }
  @keyframes spurt { 0% { opacity: 1; transform: none; } 50% { transform: translate(calc(var(--dx) * .5), -14px); } 100% { opacity: 0; transform: translate(var(--dx), 6px); } }
  .puff { position: absolute; top: 80px; width: 20px; height: 20px; border-radius: 50%; background: #fff; opacity: 0; animation: puff 1.4s ease-out both; pointer-events: none; }
  @keyframes puff { 0% { opacity: 0; transform: scale(.4); } 30% { opacity: .9; } 100% { opacity: 0; transform: translateY(-50px) scale(1.5); } }
  .say { position: absolute; left: 194px; top: 4px; max-width: 70px; text-align: center; line-height: 1.05; font-family: var(--font-display); font-size: 16px; background: var(--butter); border: var(--outline) solid var(--ink);
         border-radius: 14px; padding: 2px 10px; transform-origin: 0 100%; animation: say .5s cubic-bezier(.34, 1.56, .64, 1) .3s both; pointer-events: none; }
  @keyframes say { from { opacity: 0; transform: scale(.5) rotate(-8deg); } to { opacity: 1; transform: rotate(-4deg); } }
  .cold { position: absolute; top: 170px; width: 6px; height: 10px; border-radius: 50%; background: #5BB5F0; border: 1.5px solid var(--ink); opacity: 0;
          animation: fall .9s ease-in 2 both; pointer-events: none; }
  @keyframes fall { 0% { opacity: 1; transform: none; } 100% { opacity: 0; transform: translateY(86px); } }
  .pot, .lid { position: absolute; left: 0; top: 0; width: 260px; height: 290px; pointer-events: none; }
  .lid svg { width: 260px; height: 290px; display: block; }
  .lid { transform-origin: 188px 66px; transition: transform .6s cubic-bezier(.34, 1.4, .64, 1); }
  .lid.open { transform: rotate(35deg); }
  .alu { fill: none; stroke: var(--ink); stroke-width: 5; stroke-linejoin: round; }
  .facet { stroke: #9AA6B2; stroke-width: 2.5; stroke-linecap: round; }
  .spout { fill: #C8D0D8; stroke: var(--ink); stroke-width: 3.5; stroke-linejoin: round; }
  .waist { fill: #C8D0D8; stroke: var(--ink); stroke-width: 3.5; }
  .thread { stroke: var(--ink); stroke-width: 2.5; stroke-dasharray: 6 4; }
  .column { fill: none; stroke: var(--ink); stroke-width: 3; }
  .valve { fill: #E7C35C; stroke: var(--ink); stroke-width: 3; }
  .handle { fill: none; stroke: #2E2622; stroke-width: 14; stroke-linecap: round; stroke-linejoin: round; }
  .cut { fill: none; stroke: var(--ink); stroke-width: 2; stroke-dasharray: 5 4; opacity: .5; }
  .stove { stroke: var(--ink); stroke-width: 6; stroke-linecap: round; }
  .lidp { fill: #C8D0D8; stroke: var(--ink); stroke-width: 4; stroke-linejoin: round; }
  .knob { fill: #2E2622; stroke: var(--ink); stroke-width: 2.5; }
  .side { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 12px; }
  @media (max-aspect-ratio: 1/1) { .illus { flex-direction: column; align-items: center; } .side { width: 100%; } }
</style>
