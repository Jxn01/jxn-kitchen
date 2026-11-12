<script lang="ts">
  // knife/sharpening: the edge angle, seen end-on. The blade (a steel wedge, edge on the stone) tilts to the chosen
  // angle; the arc and its label follow; then it makes two strokes along the combination stone (1000 / 3000–6000
  // grit) — keep the angle steady. Blade, arc and label are HTML layers; the stone is a static drawing.
  let { lang }: { lang: 'en' | 'hu' } = $props();
  const ANGLES = [
    { deg: 15, en: ['15° — Japanese style', 'A thinner edge: sharper, a little more delicate. Usually about 15° per side.'],
      hu: ['15° — japán stílus', 'Vékonyabb él: élesebb, kicsit kényesebb. Általában oldalanként kb. 15°.'] },
    { deg: 20, en: ['20° — European chef’s knife', 'A sturdier edge that keeps longer. Usually about 20° per side.'],
      hu: ['20° — európai szakácskés', 'Erősebb, tartósabb él. Általában oldalanként kb. 20°.'] },
  ];
  let sel = $state(0);
  let a = $derived(ANGLES[sel]);
  const OX = 70, OY = 168;                          // where the edge touches the stone
  const R = 120;                                    // the angle wedge's radius
  const wedge = (deg: number) => {
    const t = (-deg * Math.PI) / 180;
    return `M${OX},${OY} H${OX + R} A${R},${R} 0 0 0 ${OX + R * Math.cos(t)},${OY + R * Math.sin(t)} Z`;
  };
  const lab = (_deg: number) => ({ x: OX + 46, y: OY - 104 });   // clear of the blade at either angle
</script>

<div class="illus">
  <div class="draw">
    <svg class="stone" viewBox="0 0 340 230" aria-hidden="true">
      <rect class="s1" x="14" y={OY + 1} width="156" height="34" rx="5" />
      <rect class="s2" x="170" y={OY + 1} width="156" height="34" rx="5" />
      <path class="sl" d="M14,{OY + 1} H326" />
      <text class="grit" x="92" y={OY + 26} text-anchor="middle">1000</text>
      <text class="grit" x="248" y={OY + 26} text-anchor="middle">3000–6000</text>
      <path class="base" d="M8,{OY + 36} H332" />
    </svg>
    {#each ANGLES as x, i}
      <span class="deg" class:on={i === sel} style:left="{lab(x.deg).x}px" style:top="{lab(x.deg).y}px">{x.deg}°</span>
    {/each}
    <!-- the strokes restart on every choice (two identical keyframes, alternating names); the blade itself stays
         mounted, so it TILTS to the new angle instead of jumping there -->
    <div class="stroke" style:animation-name={sel % 2 ? 'kk-strokes-a' : 'kk-strokes-b'}>
        {#each ANGLES as x, i}
          <div class="arcl" class:on={i === sel}><svg viewBox="0 0 340 230" aria-hidden="true"><path class="wedge" d={wedge(x.deg)} /></svg></div>
        {/each}
        <div class="blade" style:transform="rotate({-a.deg}deg)">
          <svg viewBox="0 0 250 30" preserveAspectRatio="none" aria-hidden="true">
            <defs><linearGradient id="steel" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#F4F7FA" /><stop offset="1" stop-color="#9AA6B2" /></linearGradient></defs>
            <path d="M0,15 L232,3 Q240,3 240,9 V21 Q240,27 232,27 Z" fill="url(#steel)" class="steel" />
            <path class="bevel" d="M0,15 L38,13 M0,15 L38,17" />
            <rect class="spine" x="236" y="2" width="12" height="26" rx="5" />
          </svg>
        </div>
    </div>
    <p class="cap">{lang === 'hu' ? 'A penge élből nézve, a kövön' : 'The blade seen end-on, on the stone'}</p>
  </div>
  <div class="side">
    <div class="chips">
      {#each ANGLES as x, i}<button class="chip pressable" class:on={i === sel} onclick={() => (sel = i)}>{x[lang][0]}</button>{/each}
    </div>
    {#key sel}<p class="say">{a[lang][1]}</p>{/key}
  </div>
</div>

<style>
  .illus { display: flex; gap: 16px; align-items: flex-start; }
  .draw { position: relative; flex: none; width: 340px; height: 252px; }
  .stone, .arcl svg { position: absolute; left: 0; top: 0; width: 340px; height: 230px; }
  .s1 { fill: #B5643A; stroke: var(--ink); stroke-width: 3.5; } .s2 { fill: #E8DCC4; stroke: var(--ink); stroke-width: 3.5; }
  .sl { stroke: rgba(255, 255, 255, .5); stroke-width: 2; }
  .grit { font-family: var(--font-display); font-size: 14px; fill: var(--ink); opacity: .75; }
  .base { stroke: var(--ink); stroke-width: 4; stroke-linecap: round; }
  .arcl { position: absolute; inset: 0; opacity: 0; transition: opacity .3s; pointer-events: none; }
  .arcl.on { opacity: 1; }
  .wedge { fill: rgba(255, 130, 110, .45); stroke: var(--ink); stroke-width: 2.5; stroke-linejoin: round; }
  .deg { position: absolute; transform: translate(-50%, -50%); opacity: 0; transition: opacity .25s; font-family: var(--font-display); font-size: 30px; color: var(--ink);
         background: var(--butter); border: var(--outline) solid var(--ink); border-radius: 12px; padding: 0 8px; line-height: 1.25; pointer-events: none; }
  .deg.on { opacity: 1; }
  .stroke { position: absolute; left: 0; top: 0; width: 340px; height: 230px; animation: kk-strokes-b 1.6s ease-in-out .5s both; pointer-events: none; }
  @keyframes -global-kk-strokes-a { 0%, 100% { transform: none; } 25% { transform: translateX(90px); } 50% { transform: none; } 75% { transform: translateX(90px); } }
  @keyframes -global-kk-strokes-b { 0%, 100% { transform: none; } 25% { transform: translateX(90px); } 50% { transform: none; } 75% { transform: translateX(90px); } }
  .blade { position: absolute; left: 70px; top: 156px; width: 170px; height: 24px; transform-origin: 0 50%; transition: transform .6s cubic-bezier(.34, 1.4, .64, 1); }
  .blade svg { width: 170px; height: 24px; display: block; }
  .steel { stroke: var(--ink); stroke-width: 3; stroke-linejoin: round; }
  .bevel { stroke: #fff; stroke-width: 1.6; opacity: .9; }
  .spine { fill: #3A2E28; stroke: var(--ink); stroke-width: 2.5; }
  .cap { position: absolute; left: 0; right: 0; bottom: 0; margin: 0; text-align: center; font-weight: 700; font-size: 13px; opacity: .7; }
  .side { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 12px; }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; }
  .chip { min-height: var(--touch); min-width: var(--touch); padding: 0 14px; border-radius: 999px; border: var(--outline) solid var(--ink);
          background: var(--paper); color: var(--ink); font: inherit; font-weight: 800; font-size: 15px; }
  .chip.on { background: var(--butter); }
  .say { margin: 0; background: var(--paper); border: var(--outline) solid var(--ink); border-radius: 16px; padding: 10px 14px; box-shadow: 0 4px 0 var(--ink);
         font-weight: 700; font-size: 15px; line-height: 1.35; animation: pop .35s cubic-bezier(.34, 1.56, .64, 1) both; }
  @keyframes pop { from { opacity: 0; transform: scale(.92) translateY(4px); } to { opacity: 1; transform: none; } }
  @media (max-aspect-ratio: 1/1) { .illus { flex-direction: column; align-items: center; } .side { width: 100%; } }
</style>
