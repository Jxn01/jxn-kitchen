<script lang="ts">
  // The idle scene (spec §5): a big clock, the weather, running timers — and the kitchen counter, where the mascot
  // lives between a pot of basil and the cutting board. At night the mascot sleeps in its nightcap and only snores;
  // the props rest. Acts come from lib/ambient.ts (one at a time, nothing between them but the mascot's blinks).
  import { onMount } from 'svelte';
  import Clock from '../components/Clock.svelte';
  import Mascot from '../components/Mascot.svelte';
  import Icon from '../components/Icon.svelte';
  import WeatherChip from '../components/WeatherChip.svelte';
  import TimerChips from '../components/TimerChips.svelte';
  import Counter from '../components/scene/Counter.svelte';
  import Board from '../components/scene/Board.svelte';
  import Herbs from '../components/scene/Herbs.svelte';
  import { mascotCue, propAct } from '../lib/ambient';
  import { t } from '../lib/i18n';
  let { night = false }: { night?: boolean } = $props();
  let m: Mascot | undefined = $state();
  onMount(() => {
    if (!night) setTimeout(() => m?.play('yawn'), 900);   // quiet time: a stretch to settle in
    // for scripts/anim-sheet.py --scene: play a prop act on demand
    (window as unknown as Record<string, unknown>).__idle = { prop: (id: string | null) => propAct.set(id) };
    return () => { delete (window as unknown as Record<string, unknown>).__idle; };
  });
  $effect(() => { const c = $mascotCue; if (c) m?.play(c.id); });
</script>

<div class="idle" class:night class:night-palette={night}>
  <div class="top">
    <div><Clock size={176} /></div>
    <div class="side"><WeatherChip /><TimerChips dark={night} /><div class="hint">{$t('idle.tap')}</div></div>
  </div>
  <div class="scene" aria-hidden="true">
    <div class="counter"><Counter height={300} /></div>
    {#if $propAct === 'chicken'}
      <div class="chicken"><div class="bob"><Icon name="chicken" size={92} /></div></div>
    {/if}
    <div class="herbs"><Herbs sway={$propAct === 'herbs'} size={210} /></div>
    <div class="board"><Board chop={$propAct === 'chop'} size={400} /></div>
    <div class="mascot"><Mascot bind:this={m} size={360} {night} expr={night ? 'asleep' : 'neutral'} /></div>
  </div>
</div>

<style>
  .idle { position: relative; height: 100%; overflow: hidden; padding: 30px 40px; }
  .top { position: relative; z-index: 2; display: flex; justify-content: space-between; align-items: flex-start; }
  .side { display: flex; flex-direction: column; align-items: flex-end; gap: 14px; padding-top: 14px; }
  .hint { font-weight: 800; font-size: 16px; opacity: .55; }
  .scene { position: absolute; left: 0; right: 0; bottom: 0; height: 300px; }
  .counter { position: absolute; inset: 0; }
  /* the table top runs from 130 to 170 px in this 300 px box; things stand on it */
  .herbs { position: absolute; left: 34px; bottom: 132px; }
  .board { position: absolute; right: 22px; bottom: 120px; }
  .mascot { position: absolute; left: 258px; bottom: 104px; }
  .chicken { position: absolute; left: 0; bottom: 156px; animation: walk 7.4s linear both; }
  .bob { animation: bob .36s ease-in-out infinite alternate; transform-origin: bottom center; }   /* episodic: only during the 7.4 s walk */
  @keyframes walk { from { transform: translateX(1080px); } to { transform: translateX(-140px); } }
  @keyframes bob { from { transform: translateY(0) rotate(-5deg); } to { transform: translateY(-7px) rotate(5deg); } }

  .night { color: #FFF4DF; }
  .night .herbs, .night .board { opacity: .78; }
</style>
