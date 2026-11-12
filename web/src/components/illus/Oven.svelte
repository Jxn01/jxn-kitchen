<script lang="ts">
  // Gas marks: a dial whose pointer turns to the mark you tap (transform only); conventional and fan temperatures.
  let { lang }: { lang: 'en' | 'hu' } = $props();
  const MARKS = [[1, 140, 120], [2, 150, 130], [3, 165, 145], [4, 180, 160], [5, 190, 170], [6, 200, 180], [7, 220, 200], [8, 230, 210], [9, 240, 220]];
  const angle = (i: number) => -135 + i * (270 / 8);
  let sel = $state(3);
</script>

<div class="illus">
  <div class="dialwrap" aria-hidden="true">
  <svg viewBox="0 0 200 200" class="dial">
    <circle cx="100" cy="100" r="88" fill="#FFF" stroke="#1F1A17" stroke-width="7" />
    {#each MARKS as m, i}
      <g transform="rotate({angle(i)} 100 100)"><line x1="100" y1="20" x2="100" y2="34" stroke="#1F1A17" stroke-width="5" stroke-linecap="round" /></g>
      <text x={100 + 58 * Math.sin((angle(i) * Math.PI) / 180)} y={106 - 58 * Math.cos((angle(i) * Math.PI) / 180)} text-anchor="middle" font-size="17" font-weight="900" fill={i === sel ? '#E8442E' : '#1F1A17'}>{m[0]}</text>
    {/each}
  </svg>
  <!-- the needle is a div turning round the hub (compositor-only) -->
  <div class="needle" style:transform="rotate({angle(sel)}deg)">
    <svg viewBox="0 0 200 200"><line x1="100" y1="100" x2="100" y2="44" stroke="#E8442E" stroke-width="8" stroke-linecap="round" /></svg>
  </div>
  <svg class="hub" viewBox="0 0 200 200"><circle cx="100" cy="100" r="14" fill="#1F1A17" /></svg>
  </div>
  <div class="side">
    <div class="readout"><span>{lang === 'hu' ? 'Gázfokozat' : 'Gas mark'} <b>{MARKS[sel][0]}</b></span></div>
    <div class="temps">
      <div><small>{lang === 'hu' ? 'Alsó-felső' : 'Conventional'}</small><b>{MARKS[sel][1]} °C</b></div>
      <div><small>{lang === 'hu' ? 'Légkeveréses' : 'Fan'}</small><b>{MARKS[sel][2]} °C</b></div>
    </div>
    <div class="marks">{#each MARKS as m, i}<button class="mk pressable" class:on={i === sel} onclick={() => (sel = i)}>{m[0]}</button>{/each}</div>
  </div>
</div>

<style>
  .illus { display: flex; gap: 20px; align-items: center; }
  .dialwrap { position: relative; width: 210px; height: 210px; flex: none; }
  /* decoration layers never take touches: the rotated needle's corners reach over the mark buttons */
  .dial, .hub, .needle, .needle svg { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
  .needle { transform-origin: 50% 50%; transition: transform .6s cubic-bezier(.34, 1.56, .64, 1); will-change: transform; }
  .side { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 10px; }
  .readout { font-weight: 800; font-size: 20px; } .readout b { font-family: var(--font-display); font-weight: 400; font-size: 36px; }
  .temps { display: flex; gap: 22px; }
  .temps div { display: flex; flex-direction: column; } .temps small { font-weight: 800; opacity: .7; }
  .temps b { font-family: var(--font-display); font-weight: 400; font-size: 32px; }
  .marks { display: flex; flex-wrap: wrap; gap: 6px; }
  .mk { flex: none; width: var(--touch); height: var(--touch); border-radius: 50%; border: var(--outline) solid var(--ink); background: var(--paper); font-weight: 900; font-size: 20px; }
  .mk.on { background: var(--tomato); color: var(--ink); }
  @media (max-aspect-ratio: 1/1) { .illus { flex-direction: column; } }
</style>
