<script lang="ts">
  // eggs/boiling: a kitchen timer and a halved egg. Choose the minutes: the timer's needle swings round to them, the
  // yolk changes from runny (a drip running out of it) through jammy and set to hard — and at 14 minutes the grey-green
  // ring of an overcooked egg appears. Needle, yolk states, drip, ring and shine are HTML layers (transform/opacity,
  // cross-fades); the dial and the white are static drawings.
  import Chips from './Chips.svelte';
  import Card from './Card.svelte';

  let { lang }: { lang: 'en' | 'hu' } = $props();
  const T = [
    { m: 5, yolk: 0, drip: 1, en: ['5 min', 'Runny', 'Set white, runny yolk — the dippy egg. GF toast soldiers at the ready.'],
      hu: ['5 perc', 'Folyós', 'Kemény fehérje, folyós sárgája — a lágy tojás. Jöhet a GM pirítóscsík.'] },
    { m: 6, yolk: 1, drip: 0.5, en: ['6 min', 'Jammy-runny', 'A liquid centre with a jammy rim — the ramen egg is 6½ minutes.'],
      hu: ['6 perc', 'Krémesen folyós', 'Folyós közép, lekvárszerű szél — a ramen-tojás 6½ perc.'] },
    { m: 7, yolk: 2, drip: 0, en: ['7 min', 'Jammy', 'A soft yolk that holds its shape — salads, toast.'],
      hu: ['7 perc', 'Lekváros', 'Puha sárgája, amely megtartja a formáját — salátába, pirítósra.'] },
    { m: 8, yolk: 3, drip: 0, en: ['8 min', 'Just set', 'Set but still creamy and deep yellow.'],
      hu: ['8 perc', 'Épp megkötött', 'Megkötött, de még krémes és mélysárga.'] },
    { m: 10, yolk: 4, drip: 0, en: ['10 min', 'Hard', 'Firm and yellow — for slicing and kaszinótojás.'],
      hu: ['10 perc', 'Kemény', 'Szilárd és sárga — szeleteléshez, kaszinótojáshoz.'] },
    { m: 12, yolk: 5, drip: 0, en: ['12 min', 'Fully hard', 'Pale and crumbly — egg salad and egg spreads.'],
      hu: ['12 perc', 'Teljesen kemény', 'Halvány és morzsálódó — tojássalátához, tojáskrémhez.'] },
    { m: 14, yolk: 5, drip: 0, ring: true, en: ['14 min +', 'Overcooked', 'A grey-green ring and a rubbery white: iron and sulphur meet. Shorter next time, and straight into iced water.'],
      hu: ['14 perc +', 'Túlfőtt', 'Szürkészöld gyűrű és gumis fehérje: a vas és a kén találkozása. Legközelebb rövidebben, és rögtön jeges vízbe.'] },
  ];
  // yolk looks: runny (glossy orange) → jammy → set → hard → pale
  const YOLK = ['radial-gradient(circle at 38% 35%, #FFE27A, #FFAA00 45%, #F08A00)', 'radial-gradient(circle at 40% 38%, #FFD45E, #F9A21B 55%, #E8890A)',
                'radial-gradient(circle at 45% 42%, #FFC94A, #F4A21B 70%)', 'radial-gradient(circle at 50% 45%, #FFD15A, #F2B230)',
                'radial-gradient(circle at 50% 50%, #FBD86A, #F2C440)', 'radial-gradient(circle at 50% 50%, #FBE7A0, #F3D77A)'];
  let sel = $state(1);
  let t = $derived(T[sel]);
</script>

<div class="illus">
  <div class="draw">
    <!-- the kitchen timer -->
    <div class="dial">
      <svg viewBox="0 0 140 140" aria-hidden="true">
        <circle class="face" cx="70" cy="70" r="62" />
        {#each Array.from({ length: 15 }, (_, i) => i) as i}
          <path class="tk" class:big={i % 5 === 0} d="M70,{i % 5 === 0 ? 14 : 17} V24" transform="rotate({i * 24} 70 70)" />
        {/each}
        {#each [0, 5, 10] as n}
          <text class="tn" x={70 + 38 * Math.sin((n * 24 * Math.PI) / 180)} y={75 - 38 * Math.cos((n * 24 * Math.PI) / 180)} text-anchor="middle">{n}</text>
        {/each}
        <path class="bell" d="M50,10 Q70,-6 90,10" />
      </svg>
      <div class="needle" style:transform="rotate({(t.m / 15) * 360}deg)"></div>
      <div class="hub"></div>
    </div>
    <!-- the halved egg -->
    <div class="egg">
      <svg viewBox="0 0 130 170" aria-hidden="true"><path class="white" d="M65,6 C28,6 8,62 8,102 C8,140 34,164 65,164 C96,164 122,140 122,102 C122,62 102,6 65,6 Z" /></svg>
      <div class="drip" style:transform="scaleY({t.drip})"></div>
      <div class="ring" class:on={t.ring}></div>
      {#each YOLK as y, i}<div class="yolk" class:on={t.yolk === i} style:background={y}></div>{/each}
      <div class="gloss" class:on={t.yolk <= 1}></div>
    </div>
  </div>
  <div class="side">
    <Chips labels={T.map((x) => x[lang][0])} bind:sel on="butter" />
    <Card title={`${t[lang][0]} — ${t[lang][1]}`} text={t[lang][2]} />
    <p class="fine">{lang === 'hu' ? 'L-es tojás, hűtőből, forrásban lévő vízbe; utána jeges víz. M-es: fél perccel kevesebb.' : 'Large eggs from the fridge into boiling water; then iced water. Medium: half a minute less.'}</p>
  </div>
</div>

<style>
  .illus { display: flex; gap: 16px; align-items: flex-start; }
  .draw { position: relative; flex: none; width: 310px; height: 210px; }
  .dial { position: absolute; left: 0; top: 30px; width: 140px; height: 140px; }
  .dial svg { position: absolute; inset: 0; width: 140px; height: 140px; overflow: visible; }
  .face { fill: #FF826E; stroke: var(--ink); stroke-width: 4; }
  .tk { stroke: var(--ink); stroke-width: 2; stroke-linecap: round; } .tk.big { stroke-width: 3.5; }
  .tn { font-family: var(--font-display); font-size: 16px; fill: var(--ink); }
  .bell { fill: none; stroke: var(--ink); stroke-width: 5; stroke-linecap: round; }
  .needle { position: absolute; left: 67px; top: 22px; width: 6px; height: 50px; border-radius: 3px; background: var(--ink); transform-origin: 3px 48px;
            transition: transform .7s cubic-bezier(.34, 1.4, .64, 1); }
  .hub { position: absolute; left: 61px; top: 61px; width: 18px; height: 18px; border-radius: 50%; background: var(--paper); border: 3px solid var(--ink); }
  .egg { position: absolute; left: 170px; top: 18px; width: 130px; height: 170px; }
  .egg svg { position: absolute; inset: 0; width: 130px; height: 170px; }
  .white { fill: #FFFDF6; stroke: var(--ink); stroke-width: 4; }
  .yolk, .ring, .gloss, .drip { position: absolute; border-radius: 50%; pointer-events: none; }
  .yolk { left: 32px; top: 70px; width: 66px; height: 66px; opacity: 0; transition: opacity .5s; box-shadow: inset 0 0 0 2.5px rgba(31, 26, 23, .55); }
  .yolk.on { opacity: 1; }
  .ring { left: 27px; top: 65px; width: 76px; height: 76px; background: #8A9A6A; opacity: 0; transition: opacity .6s; }
  .ring.on { opacity: 1; }
  .gloss { left: 46px; top: 80px; width: 18px; height: 11px; background: rgba(255, 255, 255, .8); transform: rotate(-25deg); opacity: 0; transition: opacity .4s; }
  .gloss.on { opacity: 1; }
  .drip { left: 56px; top: 118px; width: 22px; height: 44px; border-radius: 40% 40% 50% 50% / 30% 30% 70% 70%; background: linear-gradient(180deg, #FFAA00, #F08A00);
          transform-origin: 50% 0; transition: transform .6s cubic-bezier(.3, 1.3, .5, 1); box-shadow: inset 0 0 0 2px rgba(31, 26, 23, .45); }
  .side { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 10px; }
  .fine { margin: 0; font-weight: 700; font-size: 12.5px; opacity: .75; }
  @media (max-aspect-ratio: 1/1) { .illus { flex-direction: column; align-items: center; } .side { width: 100%; } }
</style>
