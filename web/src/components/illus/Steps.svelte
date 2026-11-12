<script lang="ts">
  // chart type `steps`: a strip of numbered recipe cards joined by a line. Each card (icon, step, time) is a touch
  // target; the line fills up to the chosen card, which lifts, and the note says what to do. The cards deal in once.
  import { tx, type KSteps } from '../../lib/knowhow';
  import Icon from '../Icon.svelte';
  import Card from './Card.svelte';

  let { chart, lang }: { chart: KSteps; lang: 'en' | 'hu' } = $props();
  let sel = $state(0);
  let it = $derived(chart.items[sel]);
  const n = $derived(chart.items.length);
</script>

<div class="wrap">
  <div class="strip">
    <div class="line"></div>
    <div class="fill" style:transform="scaleX({n > 1 ? sel / (n - 1) : 0})"></div>
    {#each chart.items as s, i}
      <button class="step pressable" class:on={i === sel} class:done={i < sel} style:animation-delay="{i * 80}ms" onclick={() => (sel = i)}>
        <span class="num">{i + 1}</span>
        {#if s.icon}<Icon name={s.icon} size={40} />{/if}
        <b>{tx(s.label, lang)}</b>
        {#if s.time}<small>{tx(s.time, lang)}</small>{/if}
      </button>
    {/each}
  </div>
  <Card title={`${sel + 1}. ${tx(it.label, lang)}`} value={it.time ? tx(it.time, lang) : ''} text={tx(it.note, lang)} />
</div>

<style>
  .wrap { display: flex; flex-direction: column; gap: 14px; }
  .strip { position: relative; display: flex; gap: 10px; justify-content: space-between; padding-top: 4px; }
  .line, .fill { position: absolute; left: 40px; right: 40px; top: 60px; height: 6px; border-radius: 3px; pointer-events: none; }
  .line { background: repeating-linear-gradient(90deg, var(--ink) 0 8px, transparent 8px 14px); opacity: .35; }
  .fill { background: var(--herb); border: 2px solid var(--ink); transform-origin: 0 50%; transition: transform .5s cubic-bezier(.34, 1.2, .64, 1); }
  .step { position: relative; flex: 1; min-width: 0; min-height: 132px; display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 10px 6px 8px;
          border: var(--outline) solid var(--ink); border-radius: 16px; background: var(--paper); color: var(--ink); font: inherit; text-align: center;
          transition: transform .25s cubic-bezier(.34, 1.56, .64, 1); animation: deal .4s cubic-bezier(.34, 1.56, .64, 1) both; }
  @keyframes deal { from { opacity: 0; transform: translateY(20px) rotate(-4deg); } to { opacity: 1; transform: none; } }
  .step.on { transform: translateY(-6px); box-shadow: 0 6px 0 var(--ink); background: var(--butter); }
  .step.done { background: color-mix(in srgb, var(--herb) 30%, var(--paper)); }
  .num { position: absolute; left: -8px; top: -10px; width: 28px; height: 28px; border-radius: 50%; background: var(--ink); color: #fff;
         font-family: var(--font-display); font-size: 16px; line-height: 28px; }
  b { font-weight: 800; font-size: 14px; line-height: 1.15; }
  small { font-weight: 700; font-size: 12px; opacity: .7; }
  @media (max-aspect-ratio: 1/1) { .strip { flex-wrap: wrap; } .step { flex: 1 1 40%; } .line, .fill { display: none; } }
</style>
