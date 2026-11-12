<script lang="ts">
  // Running / paused / done timers as small pills (home, idle). A tap opens the Timers screen.
  import Icon from './Icon.svelte';
  import { t } from '../lib/i18n';
  import { timers, tick, left, fmtTime } from '../lib/cooktimers';
  import { go } from '../lib/router';
  let { dark = false }: { dark?: boolean } = $props();
</script>

{#if $timers.length}
  <div class="chips" class:dark>
    {#each $timers.slice(0, 4) as tm (tm.id)}
      <button class="chip pressable" class:done={tm.state === 'done'} class:paused={tm.state === 'paused'} onclick={() => go('/timers')}>
        <Icon name="cook" size={30} />
        <span class="l">{tm.label || $t('timers.untitled')}</span>
        <b>{fmtTime(left(tm, $tick))}</b>
      </button>
    {/each}
  </div>
{/if}

<style>
  .chips { display: flex; flex-wrap: wrap; gap: 10px; }
  /* the countdown changes every second: keep that from re-laying-out or repainting anything outside the chip */
  .chip { contain: content; min-height: var(--touch); display: flex; align-items: center; gap: 8px; padding: 0 18px 0 8px; border-radius: 999px;
          border: var(--outline) solid var(--ink); background: var(--paper); box-shadow: var(--shadow-sm); font-weight: 800; font-size: 16px;
          max-width: 300px; }
  .l { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
  b { font-family: var(--font-display); font-weight: 400; font-size: 22px; font-variant-numeric: tabular-nums;
      display: inline-block; min-width: 4.2ch; text-align: right; }
  .paused { opacity: .6; }
  .done { background: var(--tomato); color: var(--ink); }
  .dark .chip { background: rgba(255, 244, 223, .12); color: var(--cream); border-color: var(--cream); box-shadow: none; }
</style>
