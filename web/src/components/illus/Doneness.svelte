<script lang="ts">
  // Meat doneness: a thermometer whose column rises to the band you tap (transform only), with the safe minimums.
  let { lang }: { lang: 'en' | 'hu' } = $props();
  const LEVELS = [
    { en: 'Rare', hu: 'Véres', t: '50–52 °C', f: 0.52, c: '#B3263A' },
    { en: 'Medium-rare', hu: 'Angolos', t: '55–57 °C', f: 0.6, c: '#D6336C' },
    { en: 'Medium', hu: 'Közepes', t: '60–63 °C', f: 0.68, c: '#E8708A' },
    { en: 'Medium-well', hu: 'Majdnem átsült', t: '65–68 °C', f: 0.76, c: '#C58B7A' },
    { en: 'Well done', hu: 'Átsült', t: '70 °C +', f: 0.84, c: '#8B5A3C' },
  ];
  const SAFE = [
    { en: 'Pork', hu: 'Sertés', t: '63 °C', f: 0.68, c: '#F2B705' },
    { en: 'Mince', hu: 'Darált hús', t: '71 °C', f: 0.85, c: '#F28C28' },
    { en: 'Poultry', hu: 'Szárnyas', t: '74 °C', f: 0.9, c: '#E8442E' },
  ];
  let sel = $state.raw(LEVELS[1]);   // raw: compared by identity below
</script>

<div class="illus">
  <!-- the column is a div scaling from the bulb (compositor-only); the tube, ticks and bulb are static svg -->
  <div class="thermo" aria-hidden="true">
    <svg viewBox="0 0 120 300">
      <rect x="40" y="10" width="40" height="230" rx="20" fill="#FFF" stroke="#1F1A17" stroke-width="6" />
      {#each [0.52, 0.6, 0.68, 0.76, 0.84] as f}<line x1="80" x2="94" y1={240 - 220 * f} y2={240 - 220 * f} stroke="#1F1A17" stroke-width="4" />{/each}
    </svg>
    <div class="col" style:transform="scaleY({sel.f})"><svg viewBox="0 0 120 300"><rect x="50" y="20" width="20" height="230" rx="10" fill={sel.c} /></svg></div>
    <svg viewBox="0 0 120 300"><circle cx="60" cy="255" r="34" fill={sel.c} stroke="#1F1A17" stroke-width="6" /></svg>
  </div>
  <div class="side">
    <div class="readout"><b>{sel.t}</b><span>{sel[lang]}</span></div>
    <div class="chips">
      {#each LEVELS as l}<button class="chip pressable" class:on={sel === l} style:--c={l.c} onclick={() => (sel = l)}>{l[lang]}</button>{/each}
    </div>
    <div class="chips safe">
      {#each SAFE as l}<button class="chip pressable" class:on={sel === l} style:--c={l.c} onclick={() => (sel = l)}>{l[lang]} ≥ {l.t}</button>{/each}
    </div>
  </div>
</div>

<style>
  .illus { display: flex; gap: 20px; align-items: center; }
  .thermo { position: relative; width: 110px; height: 270px; flex: none; }
  .thermo > svg, .col, .col svg { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
  .col { transform-origin: 50% 80%; transition: transform .7s cubic-bezier(.34, 1.56, .64, 1); will-change: transform; }
  .side { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 10px; }
  .readout { display: flex; align-items: baseline; gap: 14px; }
  .readout b { font-family: var(--font-display); font-weight: 400; font-size: 44px; }
  .readout span { font-weight: 800; font-size: 20px; }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; }
  .chip { min-height: var(--touch); padding: 0 16px; border-radius: 999px; border: var(--outline) solid var(--ink); background: var(--paper); font-weight: 800; font-size: 15px; }
  .chip.on { background: var(--c); color: var(--ink); }
  .safe .chip { border-style: dashed; }
</style>
