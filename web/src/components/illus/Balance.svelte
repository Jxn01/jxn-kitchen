<script lang="ts">
  // The taste wheel: seven tastes around a plate; tap one and the needle swings to it (a springy rotation — the needle
  // is a div, compositor-only), with what adds that taste and what balances it when there is too much.
  let { lang }: { lang: 'en' | 'hu' } = $props();
  type T = { id: string; en: string; hu: string; c: string; add: { en: string; hu: string }; fix: { en: string; hu: string } };
  const TASTES: T[] = [
    { id: 'salt', en: 'Salt', hu: 'Sós', c: '#9FB3C8', add: { en: 'salt, parmesan, olives, capers, GF tamari', hu: 'só, parmezán, olívabogyó, kapribogyó, GM tamari' }, fix: { en: 'more unsalted base, a little acid or fat', hu: 'több sózatlan alap, kevés sav vagy zsiradék' } },
    { id: 'acid', en: 'Sour', hu: 'Savanyú', c: '#F2D64B', add: { en: 'lemon, vinegar, wine, sour cream, tomato', hu: 'citrom, ecet, bor, tejföl, paradicsom' }, fix: { en: 'a pinch of sugar, cream or butter, more base', hu: 'egy csipet cukor, tejszín vagy vaj, több alap' } },
    { id: 'fat', en: 'Rich', hu: 'Zsíros', c: '#FFE29A', add: { en: 'butter, oil, lard, cream, nuts', hu: 'vaj, olaj, zsír, tejszín, olajos mag' }, fix: { en: 'acid, salt, something fresh or crunchy', hu: 'sav, só, valami friss vagy ropogós' } },
    { id: 'sweet', en: 'Sweet', hu: 'Édes', c: '#F57FB0', add: { en: 'slow-cooked onion, carrot, honey, a pinch of sugar', hu: 'lassan párolt hagyma, sárgarépa, méz, egy csipet cukor' }, fix: { en: 'acid, salt, a little heat', hu: 'sav, só, egy kis csípős' } },
    { id: 'heat', en: 'Hot', hu: 'Csípős', c: '#FF826E', add: { en: 'chilli, black pepper, hot paprika, mustard, horseradish', hu: 'chili, fekete bors, erős paprika, mustár, torma' }, fix: { en: 'sour cream or yoghurt, a little sugar, more base', hu: 'tejföl vagy joghurt, kevés cukor, több alap' } },
    { id: 'umami', en: 'Savoury', hu: 'Umami', c: '#D6A27C', add: { en: 'tomato paste, mushrooms, parmesan, anchovy, GF tamari', hu: 'paradicsompüré, gomba, parmezán, szardella, GM tamari' }, fix: { en: 'acid, fresh herbs', hu: 'sav, friss zöldfűszer' } },
    { id: 'bitter', en: 'Bitter', hu: 'Keserű', c: '#A6D96A', add: { en: 'coffee, cocoa, walnuts, charred bits, chicory', hu: 'kávé, kakaó, dió, pirult részek, cikória' }, fix: { en: 'a pinch of salt, sweetness, fat', hu: 'egy csipet só, édesség, zsiradék' } },
  ];
  const N = TASTES.length, R = 108, C = 120;
  const ang = (i: number) => (i * 360) / N;            // 0° = up
  const pt = (a: number, r: number) => [C + r * Math.sin((a * Math.PI) / 180), C - r * Math.cos((a * Math.PI) / 180)];
  function wedge(i: number): string {
    const a0 = ang(i) - 180 / N, a1 = ang(i) + 180 / N;
    const [x0, y0] = pt(a0, R), [x1, y1] = pt(a1, R);
    return `M${C},${C} L${x0},${y0} A${R},${R} 0 0 1 ${x1},${y1} Z`;
  }
  let sel = $state(0);
  let turns = $state(0);                                // keep the needle turning the short way round
  let rot = $derived(ang(sel) + 360 * turns);
  function pick(i: number) {
    const from = ang(sel), to = ang(i);
    let d = to - from;
    if (d > 180) turns -= 1; else if (d < -180) turns += 1;
    sel = i;
  }
  let t = $derived(TASTES[sel]);
</script>

<div class="illus">
  <div class="wheel">
    <svg viewBox="0 0 240 240" aria-hidden="true">
      {#each TASTES as tt, i}<path d={wedge(i)} fill={tt.c} class="wedge" />{/each}
      {#each TASTES as tt, i}
        {@const [x, y] = pt(ang(i), 76)}
        <text {x} y={y + 5} text-anchor="middle" class="lbl">{tt[lang]}</text>
      {/each}
      <circle cx={C} cy={C} r="38" class="plate" /><circle cx={C} cy={C} r="28" class="plate2" />
    </svg>
    <div class="needle" style:transform="rotate({rot}deg)">
      <svg viewBox="0 0 240 240" aria-hidden="true"><path class="arrow" d="M120,60 L130,112 Q120,120 110,112 Z" /><circle cx="120" cy="120" r="9" class="hub" /></svg>
    </div>
  </div>
  <div class="side">
    <div class="card" style:--c={t.c}>
      <b class="name">{t[lang]}</b>
      <p><span>{lang === 'hu' ? 'Mi adja:' : 'Adds it:'}</span> {t.add[lang]}</p>
      <p><span>{lang === 'hu' ? 'Ha túl sok:' : 'Too much?'}</span> {t.fix[lang]}</p>
    </div>
    <div class="chips">{#each TASTES as tt, i}<button class="chip pressable" class:on={sel === i} style:--c={tt.c} onclick={() => pick(i)}>{tt[lang]}</button>{/each}</div>
  </div>
</div>

<style>
  .illus { display: flex; gap: 18px; align-items: center; }
  .wheel { position: relative; flex: none; width: 240px; height: 240px; }
  .wheel > svg, .needle svg { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
  .wedge { stroke: var(--ink); stroke-width: 3; stroke-linejoin: round; }
  .lbl { font-weight: 900; font-size: 13px; fill: var(--ink); }
  .plate { fill: var(--paper); stroke: var(--ink); stroke-width: 3.5; } .plate2 { fill: none; stroke: #E7DCCB; stroke-width: 2.5; }
  .needle { position: absolute; inset: 0; pointer-events: none; transform-origin: 50% 50%; transition: transform .7s cubic-bezier(.34, 1.56, .64, 1); will-change: transform; }
  .arrow { fill: var(--ink); } .hub { fill: var(--butter); stroke: var(--ink); stroke-width: 3; }
  .side { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 10px; }
  .card { border: var(--outline) solid var(--ink); border-radius: var(--r); background: var(--c); padding: 10px 14px; transition: background-color .3s; }
  .name { font-family: var(--font-display); font-weight: 400; font-size: 26px; }
  .card p { margin: 4px 0 0; font-weight: 700; font-size: 15px; } .card span { font-weight: 900; }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; }
  .chip { min-height: var(--touch); min-width: var(--touch); padding: 0 14px; border-radius: 999px; border: var(--outline) solid var(--ink); background: var(--paper); font-weight: 800; font-size: 15px; }
  .chip.on { background: var(--c); }
  @media (max-aspect-ratio: 1/1) { .illus { flex-direction: column; } }
</style>
