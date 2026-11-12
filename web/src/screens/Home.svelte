<script lang="ts">
  import Clock from '../components/Clock.svelte';
  import { onDestroy, onMount } from 'svelte';
  import Mascot from '../components/Mascot.svelte';
  import MascotBubble from '../components/MascotBubble.svelte';
  import Counter from '../components/scene/Counter.svelte';
  import { mascotCue } from '../lib/ambient';
  import { TIPS, type Tip } from '../lib/tips';
  import Tile from '../components/Tile.svelte';
  import WeatherChip from '../components/WeatherChip.svelte';
  import LangChip from '../components/LangChip.svelte';
  import RoundButton from '../components/RoundButton.svelte';
  import TimerChips from '../components/TimerChips.svelte';
  import { HOME_TILES } from '../lib/tiles';
  import { t } from '../lib/i18n';
  import { go } from '../lib/router';
  import { haveCount } from '../lib/pantry';
  import { openCount } from '../lib/shopping';
  import { recipeList } from '../lib/recipes';
  import { blendList } from '../lib/spices';
  import { sauceList } from '../lib/sauces';
  import { timers } from '../lib/cooktimers';
  let { wiggleTile = null }: { wiggleTile?: string | null } = $props();

  // the mascot: pops up with a hello, plays the ambient acts, and when tapped giggles and tells a kitchen tip
  let m: Mascot | undefined = $state();
  let tip = $state<Tip | null>(null);
  let lastTip = -1;
  let hideTimer: ReturnType<typeof setTimeout> | null = null;
  onMount(() => { requestAnimationFrame(() => m?.play('hello')); });
  onDestroy(() => { if (hideTimer) clearTimeout(hideTimer); });
  $effect(() => { const c = $mascotCue; if (c && !tip) m?.play(c.id); });
  function tapped() {
    let i = Math.floor(Math.random() * TIPS.length);
    if (i === lastTip) i = (i + 1) % TIPS.length;
    lastTip = i;
    tip = null;
    setTimeout(() => { tip = TIPS[i]; m?.play('talk'); }, 650);        // after the giggle
    if (hideTimer) clearTimeout(hideTimer);
    hideTimer = setTimeout(() => (tip = null), 9000);
  }
</script>

<div class="home">
  <section class="left">
    <Clock />
    <div class="chips">
      <WeatherChip />
      <LangChip />
    </div>
    <div class="chips quick">
      <RoundButton icon="cook" label={$t('home.timers')} badge={$timers.length} onclick={() => go('/timers')} />
      <RoundButton icon="shopping" label={$t('home.shopping')} badge={$openCount} color="var(--teal)" onclick={() => go('/shopping')} />
      <RoundButton icon="settings" label={$t('home.settings')} onclick={() => go('/settings')} />
    </div>
    <div class="timers"><TimerChips /></div>
    <div class="counter" aria-hidden="true"><Counter height={104} tiles={false} top={30} /></div>
    <div class="mascot"><Mascot bind:this={m} size={236} tappable ontap={tapped} label={$t('mascot.label')} /></div>
    {#if tip}<div class="bubble"><MascotBubble {tip} onclose={() => (tip = null)} /></div>{/if}
  </section>
  <section class="tiles stagger">
    {#each HOME_TILES as tile (tile.id)}
      <Tile icon={tile.icon} color={tile.color} title={$t(tile.title)} subtitle={$t(tile.sub, { n: tile.id === 'spices' ? $blendList.length : tile.id === 'sauces' ? $sauceList.length : tile.id === 'recipes' ? $recipeList.length : $haveCount })}
            wiggle={wiggleTile === tile.id} onclick={() => go(tile.route ?? `/soon/${tile.id}`)} />
    {/each}
  </section>
</div>

<style>
  .home {
    position: relative; height: 100%; display: grid; grid-template-columns: minmax(330px, 37%) 1fr; gap: 26px;
    padding: 26px 30px 30px 30px;
  }
  .left { position: relative; display: flex; flex-direction: column; min-width: 0; }
  .chips { display: flex; gap: 12px; align-items: center; margin-top: 18px; flex-wrap: wrap; }
  .chips.quick { margin-top: 12px; }
  .timers { margin-top: 14px; position: relative; z-index: 1; }
  .counter { position: fixed; left: 0; bottom: 0; width: calc(37% + 30px); min-width: 360px; height: 104px; overflow: hidden; }
  .mascot { position: fixed; left: 34px; bottom: 50px; z-index: 2; }
  .bubble { position: fixed; left: 26px; bottom: 214px; z-index: 5; }
  /* Rows share the height but never go below their content (a tile's text is never cut off — Tile.svelte); where the
     content cannot fit, the page scrolls. The kiosk (1024x640) and a 720p desktop fit without scrolling. */
  .tiles { display: grid; grid-template-columns: repeat(3, 1fr); grid-template-rows: repeat(2, minmax(min-content, 1fr));
           gap: 20px; min-height: 0; }

  /* A short landscape screen (a phone on its side, 390 px tall): the fixed mascot scene, sized for the kiosk's 640 px,
     sat on top of the language chip and hid the timer, shopping and settings buttons entirely. It
     goes, as it does on a phone held upright, and the page scrolls when the tiles need the room. */
  @media (max-height: 500px) and (min-aspect-ratio: 1/1) {
    .home { overflow-y: auto; }
    .counter, .mascot, .bubble { display: none; }
    .tiles { min-height: auto; }   /* grow the row (and the scroll) rather than spill out of it past the page's padding */
  }
  @media (max-aspect-ratio: 1/1) {
    .home { grid-template-columns: 1fr; grid-template-rows: auto 1fr; padding: 22px 18px 18px; gap: 18px; overflow-y: auto; }
    .counter, .mascot, .bubble { display: none; }
    .tiles { grid-template-columns: 1fr 1fr; grid-template-rows: repeat(3, minmax(min-content, 1fr)); gap: 14px;
             min-height: auto; }
  }
</style>
