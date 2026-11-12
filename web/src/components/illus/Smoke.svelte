<script lang="ts">
  // Smoke points: bars grow in once (transform only), a line marks the 180 °C frying heat. Tap a fat to read it.
  let { lang }: { lang: 'en' | 'hu' } = $props();
  const FATS = [
    { en: 'Butter', hu: 'Vaj', a: 150, b: 175 },
    { en: 'Virgin coconut oil', hu: 'Szűz kókuszolaj', a: 175, b: 175 },
    { en: 'Extra virgin olive oil', hu: 'Extra szűz olívaolaj', a: 180, b: 210 },
    { en: 'Lard', hu: 'Zsír', a: 180, b: 200 },
    { en: 'Refined sunflower / rapeseed', hu: 'Finomított napraforgó / repce', a: 220, b: 230 },
    { en: 'Light olive oil', hu: 'Finomított olívaolaj', a: 230, b: 240 },
    { en: 'Ghee', hu: 'Ghí', a: 230, b: 250 },
    { en: 'Refined avocado oil', hu: 'Finomított avokádóolaj', a: 250, b: 270 },
  ];
  const pct = (t: number) => (t / 280) * 100;
  let sel = $state<number | null>(null);
</script>

<div class="illus">
  {#each FATS as f, i}
    <button class="row" class:on={sel === i} onclick={() => (sel = sel === i ? null : i)}>
      <span class="name">{f[lang]}</span>
      <span class="track">
        <span class="bar" style:width="{pct(f.b)}%" style:animation-delay="{i * 70}ms"></span>
        <span class="fry" style:left="{pct(180)}%"></span>
      </span>
      <b>{f.a === f.b ? f.a : `${f.a}–${f.b}`} °C</b>
    </button>
  {/each}
  <p class="key"><span class="fryk"></span>{lang === 'hu' ? '180 °C — olajban sütés' : '180 °C — deep-frying'}</p>
</div>

<style>
  .illus { display: flex; flex-direction: column; gap: 6px; }
  .row { display: grid; grid-template-columns: 210px 1fr 136px; align-items: center; gap: 10px; min-height: var(--touch); border: 0; background: none; text-align: left; font: inherit; padding: 0 6px; border-radius: 12px; }
  .row.on { background: var(--butter); }
  .name { font-weight: 800; font-size: 15px; }
  .track { position: relative; height: 26px; border-radius: 13px; background: var(--paper); border: 2px solid var(--ink); overflow: hidden; }
  .bar { position: absolute; left: 0; top: 0; bottom: 0; background: linear-gradient(90deg, #FFD23F, #F28C28 70%, #E8442E);
         transform-origin: left; animation: grow 900ms cubic-bezier(.34,1.3,.64,1) both; }
  @keyframes grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
  .fry { position: absolute; top: -2px; bottom: -2px; width: 3px; background: var(--ink); }
  b { font-family: var(--font-display); font-weight: 400; font-size: 18px; text-align: right; white-space: nowrap; }
  .key { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 13px; opacity: .75; margin: 4px 0 0; }
  .fryk { width: 3px; height: 18px; background: var(--ink); display: inline-block; }
  @media (max-aspect-ratio: 1/1) { .row { grid-template-columns: 1fr 70px; } .track { grid-column: 1 / -1; grid-row: 2; } }
</style>
