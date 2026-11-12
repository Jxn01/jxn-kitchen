<script lang="ts">
  import { failKey } from '../lib/api';
  // The Cook tile: free kitchen timers (spec §6.5) — big presets, a custom length, an optional label — and every
  // timer that runs, with pause/resume, +1 min and cancel. Recipes are cooked from their own page ("Start cooking").
  import PageHeader from '../components/PageHeader.svelte';
  import { timers, tick, left, fmtTime, timerApi } from '../lib/cooktimers';
  import { P } from '../lib/palette';
  import { t } from '../lib/i18n';
  import { go } from '../lib/router';
  import { osk } from '../lib/osk';
  import { showToast } from '../lib/toast';

  const PRESETS = [1, 3, 5, 10, 15, 20, 30, 45, 60];
  let label = $state('');
  let custom = $state(12);
  const start = async (min: number) => {
    try { await timerApi.start(label.trim(), min * 60); label = ''; } catch (e) { showToast({ text: $t(failKey(e)), tone: 'warn' }); }
  };
  const act = (id: number, a: 'pause' | 'resume' | 'add') => timerApi.act(id, a, 60).catch((e) => showToast({ text: $t(failKey(e)), tone: 'warn' }));
</script>

<div class="screen">
  <PageHeader title={$t('timers.title')} sub={$t('timers.sub')} icon="cook" color={P.herb} back={() => go('/')} />
  <div class="body">
    <section class="new">
      <input bind:value={label} placeholder={$t('timers.label')} use:osk maxlength="60" autocomplete="off" />
      <div class="presets">
        {#each PRESETS as m}
          <button class="preset pressable" onclick={() => start(m)}><b>{m}</b><span>{$t('timers.min')}</span></button>
        {/each}
      </div>
      <div class="custom">
        <button class="step pressable" onclick={() => (custom = Math.max(1, custom - 1))}>−</button>
        <b>{custom} {$t('timers.min')}</b>
        <button class="step pressable" onclick={() => (custom = Math.min(600, custom + 1))}>+</button>
        <button class="go pressable" onclick={() => start(custom)}>{$t('timers.start')}</button>
      </div>
    </section>
    <section class="list">
      {#each $timers as x (x.id)}
        <div class="timer" class:done={x.state === 'done'}>
          <div class="info"><span class="name">{x.label || $t('timers.untitled')}</span><b>{fmtTime(left(x, $tick))}</b></div>
          {#if x.state === 'running'}<button class="b pressable" onclick={() => act(x.id, 'pause')}>{$t('timers.pause')}</button>
          {:else if x.state === 'paused'}<button class="b pressable" onclick={() => act(x.id, 'resume')}>{$t('timers.resume')}</button>{/if}
          <button class="b pressable" onclick={() => act(x.id, 'add')}>+1 {$t('timers.min')}</button>
          <button class="b x pressable" aria-label={$t('timers.cancel')} onclick={() => timerApi.remove(x.id).catch(() => {})}>✕</button>
        </div>
      {:else}
        <p class="empty">{$t('timers.none')}</p>
      {/each}
    </section>
  </div>
</div>

<style>
  .screen { height: 100%; display: flex; flex-direction: column; }
  .body { flex: 1; min-height: 0; overflow-y: auto; display: grid; grid-template-columns: 1fr 1fr; gap: 18px; padding: 16px 20px calc(var(--kb-h) + 10px); }
  .new { display: flex; flex-direction: column; gap: 12px; }
  input { height: var(--touch); border: var(--outline) solid var(--ink); border-radius: 999px; padding: 0 20px; font: inherit; font-weight: 700; font-size: 18px; background: var(--paper); }
  .presets { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
  .preset { min-height: 76px; border-radius: var(--r); border: var(--outline) solid var(--ink); background: var(--butter); box-shadow: var(--shadow-sm);
            display: flex; align-items: baseline; justify-content: center; gap: 6px; }
  .preset b { font-family: var(--font-display); font-weight: 400; font-size: 32px; }
  .preset span { font-weight: 800; }
  .custom { display: flex; align-items: center; gap: 10px; }
  .custom b { min-width: 90px; text-align: center; font-family: var(--font-display); font-weight: 400; font-size: 22px; }
  .step { width: var(--touch); height: var(--touch); border-radius: 50%; border: var(--outline) solid var(--ink); background: var(--paper); font-size: 28px; font-weight: 900; }
  .go { flex: 1; min-height: var(--touch); border-radius: var(--r); border: var(--outline) solid var(--ink); background: var(--herb); color: var(--ink); font-weight: 900; font-size: 18px; }
  .list { display: flex; flex-direction: column; gap: 10px; }
  .timer { contain: content; display: flex; align-items: center; gap: 8px; padding: 8px 8px 8px 16px; background: var(--paper); border: var(--outline) solid var(--ink); border-radius: var(--r); }
  .timer.done { background: var(--tomato); color: var(--ink); }
  .info { flex: 1; min-width: 0; display: flex; flex-direction: column; }
  .name { font-weight: 800; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .info b { font-family: var(--font-display); font-weight: 400; font-size: 30px; font-variant-numeric: tabular-nums; }
  .b { min-height: var(--touch); min-width: var(--touch); padding: 0 12px; border-radius: 999px; border: var(--outline) solid var(--ink); background: var(--cream); color: var(--ink); font-weight: 800; }
  .empty { opacity: .6; font-weight: 800; }
  /* align-content start: the stacked grid's rows stretched to the screen's height and left a gap above the running timers */
  @media (max-aspect-ratio: 1/1) { .body { grid-template-columns: 1fr; align-content: start; padding: 12px 12px 16px; } }
</style>
