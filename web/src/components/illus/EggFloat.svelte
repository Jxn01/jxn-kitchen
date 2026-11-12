<script lang="ts">
  // eggs/freshness: the float test. An egg in a glass of water lies flat when fresh, tilts up after a week or two,
  // stands on end at two to three weeks, and floats when old — because the air cell at its blunt end (drawn inside the
  // egg, at the blunt end — which rises: an older egg stands on its point) grows as it ages. The egg moves and turns, the air cell grows, a few bubbles rise once; the glass and water
  // are static drawings.
  import Chips from './Chips.svelte';
  import Card from './Card.svelte';

  let { lang }: { lang: 'en' | 'hu' } = $props();
  const S = [
    { x: 0, y: 0, r: 90, air: 0.35, en: ['Lies flat', 'Very fresh — days old. Best for poaching and frying: the white holds together.'],
      hu: ['Fekszik', 'Nagyon friss — néhány napos. Buggyantani, tükörtojásnak a legjobb: a fehérje egyben marad.'] },
    { x: 4, y: 0, r: 135, air: 0.6, en: ['Tilts up', 'About one to two weeks old. Good for everything.'],
      hu: ['Megbillen', 'Kb. egy-két hetes. Mindenre jó.'] },
    { x: 10, y: -4, r: 180, air: 0.85, en: ['Stands on end', 'Two to three weeks old. Still fine — and the easiest to peel when hard-boiled. Use it soon.'],
      hu: ['Feláll', 'Két-három hetes. Még jó — keményre főzve a legkönnyebben hámozható. Hamar használd el.'] },
    { x: 10, y: -118, r: 172, air: 1.25, en: ['Floats', 'Old: the air cell has grown big. Crack it into a separate bowl first — if it smells bad, throw it out.'],
      hu: ['Feljön', 'Öreg: a légkamra nagyra nőtt. Előbb külön tálba üsd fel — ha rossz a szaga, dobd ki.'] },
  ];
  let sel = $state(0);
  let s = $derived(S[sel]);
</script>

<div class="illus">
  <div class="draw">
    <div class="water"></div>
    {#key sel}{#each [0, 1, 2] as b}<div class="bub" style:left="{78 + b * 22}px" style:animation-delay="{b * 160}ms"></div>{/each}{/key}
    <div class="egg" style:transform="translate({s.x}px, {s.y}px) rotate({s.r}deg)">
      <svg viewBox="0 0 50 66" aria-hidden="true"><path class="shell" d="M25,2 C11,2 3,22 3,38 C3,54 13,64 25,64 C37,64 47,54 47,38 C47,22 39,2 25,2 Z" /></svg>
      <div class="air" style:transform="scale({s.air})"></div>
    </div>
    <svg class="glass" viewBox="0 0 220 230" aria-hidden="true">
      <path class="g" d="M44,14 L54,214 Q55,222 64,222 H156 Q165,222 166,214 L176,14" />
      <path class="line" d="M48,58 H172" />
      <path class="shine" d="M64,40 L72,200" />
    </svg>
  </div>
  <div class="side">
    <Chips labels={S.map((x) => x[lang][0])} bind:sel on="butter" />
    <Card title={s[lang][0]} text={s[lang][1]} />
    <p class="fine">{lang === 'hu' ? 'A teszt a kort mutatja, nem a biztonságot: a tojást hűtőben tárold, és süsd, főzd át.' : 'The test shows age, not safety: keep eggs in the fridge and cook them through.'}</p>
  </div>
</div>

<style>
  .illus { display: flex; gap: 16px; align-items: flex-start; }
  .draw { position: relative; flex: none; width: 220px; height: 230px; }
  .water { position: absolute; left: 50px; right: 50px; top: 58px; bottom: 9px; background: linear-gradient(180deg, rgba(146, 211, 245, .55), rgba(91, 181, 240, .55));
           clip-path: polygon(0 0, 100% 0, 96% 100%, 4% 100%); }
  .egg { position: absolute; left: 85px; top: 152px; width: 50px; height: 66px; transform-origin: 50% 50%; transition: transform 1s cubic-bezier(.34, 1.25, .64, 1); }
  .egg svg { width: 50px; height: 66px; display: block; }
  .shell { fill: #F2D3AE; stroke: var(--ink); stroke-width: 3; }
  .air { position: absolute; left: 12px; top: 49px; width: 26px; height: 12px; border-radius: 50% 50% 45% 45%; background: rgba(255, 255, 255, .75);
         border: 1.5px dashed rgba(31, 26, 23, .5); transform-origin: 50% 100%; transition: transform .8s cubic-bezier(.3, 1.3, .5, 1); }
  .bub { position: absolute; top: 200px; width: 8px; height: 8px; border-radius: 50%; border: 2px solid #fff; opacity: 0; animation: bub 1.3s ease-out both; pointer-events: none; }
  @keyframes bub { 0% { opacity: 0; } 25% { opacity: 1; } 100% { opacity: 0; transform: translateY(-120px); } }
  .glass { position: absolute; inset: 0; width: 220px; height: 230px; pointer-events: none; }
  .g { fill: none; stroke: var(--ink); stroke-width: 5; stroke-linejoin: round; stroke-linecap: round; }
  .line { stroke: #5BB5F0; stroke-width: 3; }
  .shine { stroke: #fff; stroke-width: 5; stroke-linecap: round; opacity: .8; }
  .side { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 10px; }
  .fine { margin: 0; font-weight: 700; font-size: 12.5px; opacity: .75; }
  @media (max-aspect-ratio: 1/1) { .illus { flex-direction: column; align-items: center; } .side { width: 100%; } }
</style>
