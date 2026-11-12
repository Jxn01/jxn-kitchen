<script lang="ts">
  // Make-your-own blends: tap a blend and a glass jar fills, layer by layer (each spice's share, its colour, its
  // grains), then gets a little shake. Layers are divs growing with scaleY from their bottom (compositor-only); the
  // chips under the jar are the touch targets.
  let { lang }: { lang: 'en' | 'hu' } = $props();
  type Part = { en: string; hu: string; n: number; c: string };
  const S = (en: string, hu: string, n: number, c: string): Part => ({ en, hu, n, c });
  const PAPRIKA = '#D6402E', CARAWAY = '#8A6A3B', MARJORAM = '#7FA35A', GARLIC = '#EADDB8', PEPPER = '#3A3430',
    OREGANO = '#6E8B3D', ONION = '#E6CF98', CUMIN = '#A8743E', CORIANDER = '#C9A86A', THYME = '#7E9A55',
    TURMERIC = '#F2B705', GINGER = '#E3B76A', FENUGREEK = '#C99A4A', CINNAMON = '#B5651D', CARDAMOM = '#9BAF6E',
    CHILLI = '#B8322A', CLOVE = '#5A3A2A', NUTMEG = '#A0704A', SMOKED = '#9E3426', SUGAR = '#B07D45', SALT = '#F4F1EA',
    MUSTARD = '#E5B53A', ROSEMARY = '#5E7D4C', SAVORY = '#7B8F5A', ALLSPICE = '#7A4E35', ANISE = '#6B3E2E',
    SUMAC = '#8E2F3A', SESAME = '#E8D8A8', CAYENNE = '#C0392B', FENNEL = '#A8B26A', BASIL = '#6F8F3F', HOTPAP = '#A8331C',
    MSEED = '#C9A84A', DILLSEED = '#8C8A5A', BAY = '#8A9A5B', ORANGE = '#E8892A';
  const BLENDS: { id: string; en: string; hu: string; parts: Part[] }[] = [
    { id: 'porkolt', en: 'Pörkölt', hu: 'Pörkölt', parts: [S('sweet paprika', 'édesnemes paprika', 4, PAPRIKA), S('caraway', 'kömény', 1, CARAWAY), S('marjoram', 'majoránna', 1, MARJORAM), S('garlic powder', 'fokhagymapor', 1, GARLIC), S('black pepper', 'fekete bors', .5, PEPPER)] },
    { id: 'gyros', en: 'Gyros', hu: 'Gyros', parts: [S('oregano', 'oregánó', 2, OREGANO), S('garlic powder', 'fokhagymapor', 2, GARLIC), S('onion powder', 'hagymapor', 2, ONION), S('sweet paprika', 'édesnemes paprika', 2, PAPRIKA), S('thyme', 'kakukkfű', 1, THYME), S('cumin', 'római kömény', 1, CUMIN), S('coriander', 'koriander', 1, CORIANDER), S('black pepper', 'fekete bors', 1, PEPPER)] },
    { id: 'grill', en: 'Grill rub', hu: 'Grill', parts: [S('smoked paprika', 'füstölt paprika', 6, SMOKED), S('brown sugar', 'barna cukor', 3, SUGAR), S('salt', 'só', 2, SALT), S('garlic powder', 'fokhagymapor', 2, GARLIC), S('onion powder', 'hagymapor', 2, ONION), S('black pepper', 'fekete bors', 1, PEPPER), S('mustard powder', 'mustárpor', 1, MUSTARD), S('chilli', 'chili', .5, CHILLI)] },
    { id: 'curry', en: 'Curry', hu: 'Curry', parts: [S('coriander', 'koriander', 4, CORIANDER), S('cumin', 'római kömény', 2, CUMIN), S('turmeric', 'kurkuma', 2, TURMERIC), S('ginger', 'gyömbér', 1, GINGER), S('fenugreek', 'görögszéna', 1, FENUGREEK), S('cinnamon', 'fahéj', .5, CINNAMON), S('cardamom', 'kardamom', .5, CARDAMOM), S('chilli', 'chili', .5, CHILLI), S('black pepper', 'fekete bors', .5, PEPPER)] },
    { id: 'garam', en: 'Garam masala', hu: 'Garam masala', parts: [S('coriander', 'koriander', 3, CORIANDER), S('cumin', 'római kömény', 2, CUMIN), S('cardamom', 'kardamom', 1, CARDAMOM), S('black pepper', 'fekete bors', 1, PEPPER), S('cinnamon', 'fahéj', .5, CINNAMON), S('clove', 'szegfűszeg', .5, CLOVE), S('nutmeg', 'szerecsendió', .5, NUTMEG)] },
    { id: 'taco', en: 'Taco', hu: 'Taco', parts: [S('mild chilli', 'enyhe chilipor', 4, CHILLI), S('cumin', 'római kömény', 2, CUMIN), S('paprika', 'paprika', 1, PAPRIKA), S('garlic powder', 'fokhagymapor', 1, GARLIC), S('onion powder', 'hagymapor', 1, ONION), S('oregano', 'oregánó', 1, OREGANO), S('salt', 'só', 1, SALT), S('black pepper', 'fekete bors', .5, PEPPER)] },
    { id: 'provence', en: 'Herbes de Provence', hu: 'Provence-i', parts: [S('thyme', 'kakukkfű', 3, THYME), S('rosemary', 'rozmaring', 2, ROSEMARY), S('savory', 'borsikafű', 2, SAVORY), S('oregano', 'oregánó', 1, OREGANO), S('marjoram', 'majoránna', 1, MARJORAM)] },
    { id: 'ginger', en: 'Gingerbread', hu: 'Mézeskalács', parts: [S('cinnamon', 'fahéj', 4, CINNAMON), S('ginger', 'gyömbér', 2, GINGER), S('clove', 'szegfűszeg', 1, CLOVE), S('nutmeg', 'szerecsendió', 1, NUTMEG), S('allspice', 'szegfűbors', 1, ALLSPICE), S('cardamom', 'kardamom', .5, CARDAMOM), S('star anise', 'csillagánizs', .5, ANISE)] },
    // eight more, the same recipes as the DIY page's text
    { id: 'zaatar', en: "Za'atar", hu: "Za'atar", parts: [S('thyme', 'kakukkfű', 3, THYME), S('sumac', 'szömörce', 2, SUMAC), S('toasted sesame', 'pirított szezám', 2, SESAME), S('salt', 'só', .5, SALT)] },
    { id: 'ras', en: 'Ras el hanout', hu: 'Ras el hanout', parts: [S('cumin', 'római kömény', 2, CUMIN), S('ginger', 'gyömbér', 2, GINGER), S('coriander', 'koriander', 2, CORIANDER), S('turmeric', 'kurkuma', 1, TURMERIC), S('cinnamon', 'fahéj', 1, CINNAMON), S('sweet paprika', 'édesnemes paprika', 1, PAPRIKA), S('cardamom', 'kardamom', .5, CARDAMOM), S('allspice', 'szegfűbors', .5, ALLSPICE), S('black pepper', 'fekete bors', .5, PEPPER)] },
    { id: 'cajun', en: 'Cajun', hu: 'Cajun', parts: [S('sweet paprika', 'édesnemes paprika', 3, PAPRIKA), S('garlic powder', 'fokhagymapor', 2, GARLIC), S('onion powder', 'hagymapor', 1, ONION), S('oregano', 'oregánó', 1, OREGANO), S('thyme', 'kakukkfű', 1, THYME), S('black pepper', 'fekete bors', 1, PEPPER), S('salt', 'só', 1, SALT), S('cayenne', 'cayenne-bors', .5, CAYENNE)] },
    { id: 'five', en: 'Five-spice', hu: 'Ötfűszer', parts: [S('star anise', 'csillagánizs', 2, ANISE), S('fennel seed', 'édesköménymag', 2, FENNEL), S('cinnamon', 'fahéj', 1, CINNAMON), S('black pepper', 'fekete bors', 1, PEPPER), S('clove', 'szegfűszeg', .5, CLOVE)] },
    { id: 'italian', en: 'Italian herbs', hu: 'Olasz', parts: [S('oregano', 'oregánó', 2, OREGANO), S('basil', 'bazsalikom', 2, BASIL), S('thyme', 'kakukkfű', 1, THYME), S('rosemary', 'rozmaring', 1, ROSEMARY), S('marjoram', 'majoránna', 1, MARJORAM)] },
    { id: 'kolbasz', en: 'Kolbász', hu: 'Kolbász', parts: [S('sweet paprika', 'édesnemes paprika', 4, PAPRIKA), S('hot paprika', 'erős paprika', 1, HOTPAP), S('garlic powder', 'fokhagymapor', 1, GARLIC), S('caraway', 'kömény', .5, CARAWAY), S('black pepper', 'fekete bors', .5, PEPPER)] },
    { id: 'pickle', en: 'Pickling', hu: 'Savanyúság', parts: [S('mustard seed', 'mustármag', 2, MSEED), S('coriander seed', 'koriandermag', 1, CORIANDER), S('peppercorns', 'egész bors', 1, PEPPER), S('dill seed', 'kapormag', 1, DILLSEED), S('allspice', 'szegfűbors', .5, ALLSPICE), S('bay', 'babér', .5, BAY)] },
    { id: 'mulled', en: 'Mulled wine', hu: 'Forralt bor', parts: [S('cinnamon', 'fahéj', 2, CINNAMON), S('orange peel', 'narancshéj', 2, ORANGE), S('clove', 'szegfűszeg', 1, CLOVE), S('star anise', 'csillagánizs', 1, ANISE), S('allspice', 'szegfűbors', 1, ALLSPICE), S('cardamom', 'kardamom', .5, CARDAMOM)] },
  ];
  let sel = $state.raw(BLENDS[0]);
  let total = $derived(sel.parts.reduce((a, p) => a + p.n, 0));
  const FILL = 176;                                     // px of jar the blend fills
  let layers = $derived.by(() => {
    let y = 0;
    return sel.parts.map((p, i) => { const h = (p.n / total) * FILL; const l = { ...p, i, h, y }; y += h; return l; });
  });
  const fmt = (n: number) => (n === .5 ? '½' : n % 1 ? `${Math.floor(n)}½` : String(n));
  const tsp = $derived(lang === 'hu' ? 'tk' : 'tsp');
</script>

<div class="illus">
  {#key sel}
    <div class="jarwrap">
      <div class="jar">
        <div class="glass"></div>
        {#each layers as l (l.i)}
          <div class="layer" style:bottom="{l.y + 12}px" style:height="{l.h + 0.6}px" style:--c={l.c} style:animation-delay="{l.i * 110}ms"></div>
        {/each}
        <svg class="outline" viewBox="0 0 150 230" aria-hidden="true">
          <rect x="22" y="12" width="106" height="22" rx="6" class="lid" />
          <path class="jarline" d="M30,36 H120 Q126,36 126,44 V214 Q126,222 118,222 H32 Q24,222 24,214 V44 Q24,36 30,36 Z" />
          <path class="shine" d="M36,52 V196" /><path class="shine thin" d="M45,60 V120" />
          <rect x="44" y="96" width="62" height="34" rx="5" class="label" />
          <text x="75" y="118" text-anchor="middle" class="gf">GF</text>
        </svg>
      </div>
    </div>
  {/key}
  <div class="side">
    <ul class="legend">
      {#each sel.parts as p}<li><span class="sw" style:background={p.c}></span><b>{fmt(p.n)} {tsp}</b> {p[lang]}</li>{/each}
    </ul>
    <div class="chips">
      {#each BLENDS as b}<button class="chip pressable" class:on={sel === b} onclick={() => (sel = b)}>{b[lang]}</button>{/each}
    </div>
  </div>
</div>

<style>
  .illus { display: flex; gap: 18px; align-items: flex-start; }
  .jarwrap { flex: none; width: 150px; height: 230px; transform-origin: 50% 100%; animation: shake .6s ease-in-out both; animation-delay: 1.1s; }
  .jar { position: relative; width: 150px; height: 230px; }
  .glass { position: absolute; left: 26px; right: 26px; top: 38px; bottom: 10px; border-radius: 4px 4px 7px 7px; background: rgba(255, 255, 255, .7); }
  .layer { position: absolute; left: 27px; right: 27px; background: var(--c);
           background-image: radial-gradient(rgba(0, 0, 0, .18) 1px, transparent 1.6px), radial-gradient(rgba(255, 255, 255, .25) 1px, transparent 1.6px);
           background-size: 7px 7px, 9px 9px; background-position: 0 0, 3px 4px;
           transform-origin: 50% 100%; animation: pour .5s cubic-bezier(.3, 1.5, .5, 1) both; }
  @keyframes pour { from { transform: scaleY(0); opacity: .6; } to { transform: scaleY(1); opacity: 1; } }
  @keyframes shake { 20% { transform: rotate(-4deg); } 45% { transform: rotate(3.5deg); } 70% { transform: rotate(-2deg); } 88% { transform: rotate(1deg); } }
  .outline { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; }
  .jarline { fill: none; stroke: var(--ink); stroke-width: 4; stroke-linejoin: round; }
  .lid { fill: #B5BEC7; stroke: var(--ink); stroke-width: 4; }
  .shine { stroke: #fff; stroke-width: 5; stroke-linecap: round; opacity: .8; } .shine.thin { stroke-width: 2.5; }
  .label { fill: var(--paper); stroke: var(--ink); stroke-width: 2.5; }
  .gf { font-family: var(--font-display); font-size: 17px; fill: var(--herb); }
  .side { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 10px; }
  .legend { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: 1fr 1fr; gap: 4px 14px; font-size: 15px; font-weight: 700; }
  .legend li { display: flex; align-items: center; gap: 7px; }
  .sw { flex: none; width: 16px; height: 16px; border-radius: 4px; border: 2px solid var(--ink); }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; }
  .chip { min-height: var(--touch); min-width: var(--touch); padding: 0 14px; border-radius: 999px; border: var(--outline) solid var(--ink); background: var(--paper); font-weight: 800; font-size: 15px; }
  .chip.on { background: var(--rust); }
  @media (max-aspect-ratio: 1/1) { .illus { flex-direction: column; align-items: center; } .legend { grid-template-columns: 1fr; } }
</style>
