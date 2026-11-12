<script lang="ts">
  // The verdict: a ring filled to the score, the number in the middle (it counts to a new value — once, ~0.4 s, per
  // evaluation: episodic), the word beneath. Ink text on the word's palette colour.
  import { untrack } from 'svelte';
  import { color } from '../../lib/palette';
  import { WORD_COLOR, type Word } from '../../lib/spices';
  let { score, word, text, size = 108 }: { score: number | null; word: Word; text: string; size?: number } = $props();
  const R = 42, C = 2 * Math.PI * R;
  let shown = $state(0);
  // `shown` is read untracked: the tween writes it every frame, and a tracked read would restart the effect each time
  // (seen as a ring counting to -51671124). The clock is the frames' own timestamps, starting at the first frame; a
  // timer lands the final number even when frames are throttled. Cleanup lives in the effect (SSR never runs it).
  $effect(() => {
    const to = score ?? 0, from = untrack(() => shown);
    let t0 = -1, raf = 0;
    // stepped at ~10 fps (a new number every 100 ms, not every frame) and starting the frame AFTER the new evaluation
    // lands, so it never adds a text layout to the frame that rebuilds the ledger
    let last = -1;
    const step = (t: number) => {
      if (t0 < 0) t0 = t;
      const k = Math.min(1, Math.max(0, (t - t0) / 420));
      if (k >= 1 || t - last >= 100) { last = t; shown = Math.round(from + (to - from) * (1 - (1 - k) ** 3)); }
      if (k < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(() => (raf = requestAnimationFrame(step)));
    const land = setTimeout(() => { cancelAnimationFrame(raf); shown = to; }, 460);
    return () => { cancelAnimationFrame(raf); clearTimeout(land); };
  });
  let c = $derived(color(WORD_COLOR[word]));
</script>

<div class="ring" style:width="{size}px" style:--s="{size}px">
  <svg viewBox="0 0 100 100" width={size} height={size} aria-hidden="true">
    <circle class="track" cx="50" cy="50" r={R} />
    <!-- always there (hidden before the first jar): the first answer only changes it -->
    <circle class="arc" class:blank={score === null} cx="50" cy="50" r={R} stroke={c} stroke-dasharray="{(C * (score ?? 0)) / 100} {C}" transform="rotate(-90 50 50)" />
    <circle class="rim" cx="50" cy="50" r={R + 6} />
  </svg>
  <span class="n" style:font-size="{size * 0.3}px">{score === null ? '–' : shown}</span>
  <!-- the chip keeps its place when there is no word yet, so nothing below it moves -->
  <span class="w" class:blank={!text} style:background={c}>{text || '·'}</span>
</div>

<style>
  .ring { position: relative; display: flex; flex-direction: column; align-items: center; flex: none; contain: layout paint; }
  svg { display: block; }
  .track { fill: var(--paper); stroke: var(--cream); stroke-width: 11; }
  .arc { fill: none; stroke-width: 11; stroke-linecap: round; } .arc.blank { visibility: hidden; }
  .rim { fill: none; stroke: var(--ink); stroke-width: 3; }
  .n { position: absolute; top: 0; left: 0; width: 100%; height: var(--s); display: grid; place-items: center; font-family: var(--font-display);
       line-height: 1; font-variant-numeric: tabular-nums; }
  .w { margin-top: -10px; position: relative; border: var(--outline) solid var(--ink); border-radius: 999px; padding: 2px 12px;
       font-weight: 900; font-size: 15px; color: var(--ink); white-space: nowrap; box-shadow: 2px 2px 0 var(--ink); }
  .w.blank { visibility: hidden; }
</style>
