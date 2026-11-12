<script lang="ts">
  // The engines' answer, docked at the bottom of a phone. On a phone the blend and sauce
  // editors stack: name, shelves, tray, then the live panel far below — the score changed out of sight with every tap.
  // This shows the score and its word all the time and scrolls to the panel on a tap; it hides while the panel itself is
  // on screen. Phones only: `display: none` elsewhere, and the observer is only made where the phone query matches, so
  // the kiosk neither paints nor observes it.
  import { onMount } from 'svelte';
  import { WORD_COLOR, type Word } from '../lib/engine';

  let { score, word, text, target, label }:
    { score: number | null; word: Word | null; text: string; target: HTMLElement | undefined; label: string } = $props();
  let panelInView = $state(false);

  onMount(() => {
    if (!target || typeof IntersectionObserver === 'undefined' || !matchMedia('(max-aspect-ratio: 1/1)').matches) return;
    const io = new IntersectionObserver(([en]) => { panelInView = en.isIntersecting; }, { threshold: 0.25 });
    io.observe(target);
    return () => io.disconnect();
  });
</script>

<button class="dock pressable" class:away={panelInView} aria-label={label}
        onclick={() => target?.scrollIntoView({ behavior: 'smooth', block: 'start' })}>
  <b class="n" style:background={word ? `var(--${WORD_COLOR[word]})` : 'var(--paper)'}>{score ?? '–'}</b>
  <span class="w">{text}</span>
  <span class="chev" aria-hidden="true"></span>
</button>

<style>
  .dock { display: none; }
  @media (max-aspect-ratio: 1/1) {
    .dock {
      display: flex; align-items: center; gap: 12px; position: fixed; z-index: 15;
      left: calc(12px + env(safe-area-inset-left)); right: calc(12px + env(safe-area-inset-right));
      bottom: calc(12px + env(safe-area-inset-bottom));
      min-height: 56px; padding: 6px 14px 6px 6px; border-radius: 999px; border: var(--outline) solid var(--ink);
      background: var(--paper); color: var(--ink); box-shadow: var(--shadow-sm); text-align: left;
      transition: transform .2s ease-out, opacity .2s ease-out;
    }
    .dock.away { transform: translateY(140%); opacity: 0; pointer-events: none; }
    .n { flex: none; min-width: 44px; height: 44px; padding: 0 8px; border-radius: 999px; border: var(--outline) solid var(--ink);
         display: grid; place-items: center; font-family: var(--font-display); font-weight: 400; font-size: 22px; }
    .w { flex: 1; min-width: 0; font-weight: 800; font-size: 16px; line-height: 1.2;
         display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
    .chev { flex: none; width: 12px; height: 12px; margin: 0 4px 6px; border-right: 3px solid var(--ink); border-bottom: 3px solid var(--ink);
            transform: rotate(45deg); }   /* drawn: no emoji glyphs, and the sprite has no chevron */
  }
</style>
