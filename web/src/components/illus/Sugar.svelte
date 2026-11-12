<script lang="ts">
  // Sugar stages: a 100–180 °C strip; tap a stage and the marker slides to it (transform only).
  let { lang }: { lang: 'en' | 'hu' } = $props();
  const STAGES = [
    { en: 'Thread', hu: 'Fonal', a: 106, b: 112, c: '#FFF4C2' },
    { en: 'Soft ball', hu: 'Lágy golyó', a: 112, b: 116, c: '#FFE7A0' },
    { en: 'Firm ball', hu: 'Kemény golyó', a: 118, b: 120, c: '#FFD97A' },
    { en: 'Hard ball', hu: 'N. kemény golyó', a: 121, b: 130, c: '#FFC75A' },
    { en: 'Soft crack', hu: 'Lágy törés', a: 132, b: 143, c: '#F5AE3D' },
    { en: 'Hard crack', hu: 'Kemény törés', a: 146, b: 154, c: '#E38E27' },
    { en: 'Caramel', hu: 'Karamell', a: 160, b: 177, c: '#A85A1C' },
  ];
  const x = (t: number) => ((t - 100) / 80) * 100;
  let sel = $state.raw(STAGES[1]);   // raw: compared by identity below
</script>

<div class="illus">
  <div class="strip">
    <!-- a picture you can tap; the chips below are the real (64 px) targets -->
    {#each STAGES as s}<span class="seg" role="presentation" style:left="{x(s.a)}%" style:width="{x(s.b) - x(s.a)}%" style:background={s.c} onclick={() => (sel = s)}></span>{/each}
    <div class="marker" style:transform="translateX({x((sel.a + sel.b) / 2)}cqw)"></div>
  </div>
  <div class="scale"><span>100 °C</span><span>140 °C</span><span>180 °C</span></div>
  <div class="readout"><b>{sel.a}–{sel.b} °C</b><span>{sel[lang]}</span></div>
  <div class="chips">{#each STAGES as s}<button class="chip pressable" class:on={sel === s} style:--c={s.c} onclick={() => (sel = s)}>{s[lang]}</button>{/each}</div>
</div>

<style>
  .illus { display: flex; flex-direction: column; gap: 8px; }
  .strip { position: relative; height: var(--touch); border: var(--outline) solid var(--ink); border-radius: 14px; background: var(--paper); overflow: visible; container-type: inline-size; }
  .seg { position: absolute; top: 0; bottom: 0; border-right: 2px solid var(--ink); cursor: pointer; }
  .marker { position: absolute; top: -16px; left: 0; width: 0; height: 0; margin-left: -12px; border: 12px solid transparent; border-top: 16px solid var(--ink);
            transition: transform 600ms cubic-bezier(.34,1.56,.64,1); }
  .scale { display: flex; justify-content: space-between; font-weight: 700; font-size: 13px; opacity: .7; }
  .readout { display: flex; align-items: baseline; gap: 14px; }
  .readout b { font-family: var(--font-display); font-weight: 400; font-size: 36px; }
  .readout span { font-weight: 800; font-size: 19px; }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; }
  .chip { min-height: var(--touch); padding: 0 14px; border-radius: 999px; border: var(--outline) solid var(--ink); background: var(--paper); font-weight: 800; font-size: 15px; }
  .chip.on { background: var(--c); }
</style>
