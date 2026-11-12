<script lang="ts">
  // storage/fridge: an open fridge with its contents where they belong. The door swings open when the page opens (a
  // one-off 3D transform); the chosen zone glows and the card says what goes there and why. Food icons are static;
  // the glow, the door and the zone outline are HTML layers (transform/opacity).
  import Icon from '../Icon.svelte';
  import Chips from './Chips.svelte';
  import Card from './Card.svelte';

  let { lang }: { lang: 'en' | 'hu' } = $props();
  type Zone = { x: number; y: number; w: number; h: number; icons: string[]; en: [string, string]; hu: [string, string] };
  const Z: Zone[] = [
    { x: 26, y: 26, w: 168, h: 54, icons: ['om-1f961', 'om-1f963', 'om-1f9c0'],
      en: ['Top shelf', 'Ready-to-eat: leftovers, cooked food, yoghurt, cheese. Covered, and up high, away from raw meat.'],
      hu: ['Felső polc', 'Fogyasztásra kész: maradék, főtt étel, joghurt, sajt. Lefedve, fent, a nyers hústól távol.'] },
    { x: 26, y: 86, w: 168, h: 54, icons: ['om-1f95b', 'om-1f95a', 'om-1f9c8'],
      en: ['Middle shelf', 'Milk, eggs in their box, butter, opened jars. Milk keeps longer here than in the door.'],
      hu: ['Középső polc', 'Tej, tojás a dobozában, vaj, felbontott üvegek. A tej itt tovább eláll, mint az ajtóban.'] },
    { x: 26, y: 146, w: 168, h: 54, icons: ['om-1f969', 'om-1f41f'],
      en: ['Bottom shelf', 'Raw meat, poultry and fish — sealed, on a plate. The coldest shelf, and below everything ready-to-eat, so nothing drips onto it.'],
      hu: ['Alsó polc', 'Nyers hús, szárnyas, hal — lezárva, tányéron. A leghidegebb polc, és minden kész étel alatt, így semmi nem csöpög rá.'] },
    { x: 26, y: 206, w: 168, h: 62, icons: ['om-1f955', 'om-1f966', 'om-1f34e'],
      en: ['Drawers', 'Vegetables and fruit. Keep apples apart if you can — they ripen everything around them.'],
      hu: ['Fiókok', 'Zöldség és gyümölcs. Az almát ha lehet, tartsd külön — mindent megérlel maga körül.'] },
    { x: 214, y: 26, w: 62, h: 242, icons: ['om-1f9c3', 'om-1fad9', 'om-1f96b'],
      en: ['Door', 'The warmest place: drinks, sauces, jams, mustard. Not milk or eggs.'],
      hu: ['Ajtó', 'A legmelegebb hely: italok, szószok, lekvár, mustár. Tejet, tojást ne.'] },
  ];
  let sel = $state(2);
  let z = $derived(Z[sel]);
</script>

<div class="illus">
  <div class="draw">
    <svg class="body" viewBox="0 0 300 300" aria-hidden="true">
      <rect class="cab" x="16" y="14" width="190" height="270" rx="14" />
      <rect class="in" x="24" y="22" width="174" height="254" rx="8" />
      {#each [82, 142, 202] as y}<path class="shelf" d="M24,{y} H198" />{/each}
      <path class="drawer" d="M30,210 H192 V268 H30 Z M30,239 H192" />
      <rect class="therm" x="160" y="30" width="30" height="14" rx="4" /><text class="tt" x="175" y="41" text-anchor="middle">4°</text>
    </svg>
    {#each Z as zone}
      <div class="items" style:left="{zone.x}px" style:top="{zone.y}px" style:width="{zone.w}px" style:height="{zone.h}px"
           class:door={zone.x > 200}>
        {#each zone.icons as ic}<Icon name={ic} size={zone.x > 200 ? 30 : 36} />{/each}
      </div>
    {/each}
    {#key sel}
      <div class="glow" style:left="{z.x - 3}px" style:top="{z.y - 3}px" style:width="{z.w + 6}px" style:height="{z.h + 6}px"></div>
    {/key}
    <!-- the door: open, its shelves facing us; it swings open once when the page opens -->
    <div class="doorwrap">
      <svg viewBox="0 0 80 270" aria-hidden="true">
        <rect class="dr" x="4" y="0" width="72" height="270" rx="12" />
        {#each [60, 120, 180, 240] as y}<path class="rack" d="M10,{y} H70" />{/each}
      </svg>
    </div>
  </div>
  <div class="side">
    <Chips labels={Z.map((x) => x[lang][0])} bind:sel on="mint" />
    <Card title={z[lang][0]} text={z[lang][1]} />
  </div>
</div>

<style>
  .illus { display: flex; gap: 16px; align-items: flex-start; }
  .draw { position: relative; flex: none; width: 300px; height: 300px; perspective: 600px; }
  .body { position: absolute; inset: 0; width: 300px; height: 300px; }
  .cab { fill: #EEF3F6; stroke: var(--ink); stroke-width: 5; }
  .in { fill: #F9FCFE; stroke: #C9D6DE; stroke-width: 2; }
  .shelf { stroke: #9FC3D6; stroke-width: 5; stroke-linecap: round; }
  .drawer { fill: rgba(159, 211, 242, .25); stroke: #9FC3D6; stroke-width: 3; }
  .therm { fill: var(--paper); stroke: var(--ink); stroke-width: 2; } .tt { font-family: var(--font-display); font-size: 11px; fill: var(--ink); }
  .items { position: absolute; display: flex; align-items: flex-end; justify-content: space-evenly; padding-bottom: 4px; pointer-events: none; }
  .items.door { flex-direction: column; align-items: center; justify-content: space-around; padding: 6px 0; z-index: 2; }
  .glow { position: absolute; border: 4px solid var(--ink); border-radius: 10px; background: rgba(125, 220, 181, .28); pointer-events: none;
          animation: glow .5s cubic-bezier(.34, 1.56, .64, 1) both; z-index: 3; }
  @keyframes glow { from { opacity: 0; transform: scale(.9); } to { opacity: 1; transform: none; } }
  .doorwrap { position: absolute; left: 208px; top: 14px; width: 80px; height: 270px; transform-origin: 0 50%; z-index: 1;
              animation: open-door 1.1s cubic-bezier(.34, 1.2, .64, 1) .2s both; pointer-events: none; }
  @keyframes open-door { from { transform: translateX(-192px) rotateY(0deg); } 40% { transform: translateX(-192px) rotateY(-70deg); } to { transform: none; } }
  .doorwrap svg { width: 80px; height: 270px; display: block; }
  .dr { fill: #E2EBF0; stroke: var(--ink); stroke-width: 5; }
  .rack { stroke: #9FC3D6; stroke-width: 5; stroke-linecap: round; }
  .side { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 12px; }
  @media (max-aspect-ratio: 1/1) { .illus { flex-direction: column; align-items: center; } .side { width: 100%; } }
</style>
