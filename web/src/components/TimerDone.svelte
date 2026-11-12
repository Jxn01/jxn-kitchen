<script lang="ts">
  import Mascot from './Mascot.svelte';
  // A timer ended: full screen until someone taps (spec §6.5). The kiosk chimes meanwhile (every RING_EVERY_MS,
  // muted with the `sounds` setting); other devices just show the card. "+1 min" gives it another minute.
  import { onDestroy } from 'svelte';
  import { dismissTimers, doneTimers, timerApi } from '../lib/cooktimers';
  import { isKiosk } from '../lib/kiosk';
  import { sound, RING_EVERY_MS } from '../lib/sound';
  import { t } from '../lib/i18n';

  let ringing: ReturnType<typeof setInterval> | null = null;
  $effect(() => {
    const on = $doneTimers.length > 0 && $isKiosk;
    if (on && !ringing) { sound.ring(); ringing = setInterval(() => sound.ring(), RING_EVERY_MS); }
    if (!on && ringing) { clearInterval(ringing); ringing = null; }
  });
  // The mascot shakes ONCE per chime (alarm, 1.2 s every RING_EVERY_MS) and holds its alarmed face in between: an
  // undismissed timer stays up all night (no expiry), and a looping 60 Hz alarm would cost ~25–30 % CPU for as long.
  let pulse = $state(0);
  let beat: ReturnType<typeof setInterval> | null = null;
  $effect(() => {
    const on = $doneTimers.length > 0;
    if (on && !beat) { pulse++; beat = setInterval(() => pulse++, RING_EVERY_MS); }
    if (!on && beat) { clearInterval(beat); beat = null; }
  });
  onDestroy(() => { if (ringing) clearInterval(ringing); if (beat) clearInterval(beat); });
  const stop = () => dismissTimers($doneTimers.map((x) => x.id));   // silent at once, even offline (cooktimers.ts)
  const more = () => { for (const x of $doneTimers) timerApi.act(x.id, 'add', 60).catch(() => {}); };
</script>

{#if $doneTimers.length}
  <div class="timer-done" role="alertdialog" aria-live="assertive">
    <div class="mascot"><Mascot size={250} act="alarm" actKey={pulse} expr="alarm" /></div>
    <h1>{$t('timers.done')}</h1>
    <p class="labels">{$doneTimers.map((x) => x.label || $t('timers.untitled')).join(' · ')}</p>
    <div class="row">
      <button class="more pressable" onclick={more}>+1 {$t('timers.min')}</button>
      <button class="stop pressable" onclick={stop}>{$t('timers.stop')}</button>
    </div>
  </div>
{/if}

<style>
  .timer-done { position: fixed; inset: 0; z-index: 60; background: var(--tomato); color: var(--ink); display: flex; flex-direction: column;
          align-items: center; justify-content: center; gap: 14px; text-align: center;
          padding: calc(20px + env(safe-area-inset-top)) calc(20px + env(safe-area-inset-right)) calc(20px + env(safe-area-inset-bottom)) calc(20px + env(safe-area-inset-left)); }
  .mascot { margin: -40px 0 -14px; }
  h1 { font-size: 56px; color: var(--ink); }
  .labels { font-weight: 900; font-size: 26px; margin: 0; }
  .row { display: flex; gap: 16px; margin-top: 10px; }
  .row button { min-height: 86px; padding: 0 34px; border-radius: var(--r); border: var(--outline-thick) solid var(--ink);
                font-family: var(--font-display); font-size: 28px; box-shadow: var(--shadow); }
  .more { background: var(--butter); color: var(--ink); }
  .stop { background: var(--paper); color: var(--ink); }
</style>
