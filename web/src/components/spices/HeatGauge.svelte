<script lang="ts">
  // The heat: four bands, mild to fiery, and a marker at the share-weighted heat (moved by transform). A blend's heat
  // runs to 3 (cayenne's), a sauce's to 1 (`max`).
  import type { Labelled } from '../../lib/spices';
  import type { Lang } from '../../lib/i18n';
  let { value, word, words, lang, max = 3 }: { value: number; word: string; words: (Labelled & { below: number })[]; lang: Lang; max?: number } = $props();
  const FILL: Record<string, string> = { mild: '#CFEFD0', warm: '#FFD23F', hot: '#F28C28', fiery: '#FF826E' };
  let bands = $derived(words.map((w, i) => ({ ...w, from: i ? words[i - 1].below : 0, to: Math.min(max, w.below) })));
</script>

<div class="gauge">
  <div class="bar">
    {#each bands as b (b.id)}
      <span class="band" class:on={b.id === word} style:flex-grow={b.to - b.from} style:background={FILL[b.id]}>{b[lang]}</span>
    {/each}
    <span class="marker" style:transform="translateX({Math.min(1, value / max) * 100}cqw)"></span>
  </div>
</div>

<style>
  .gauge { container-type: inline-size; }
  .bar { position: relative; display: flex; height: 48px; border: var(--outline) solid var(--ink); border-radius: 999px; overflow: hidden; }
  .band { flex-basis: 0; display: grid; place-items: center; font-weight: 800; font-size: 13px; border-right: 2px solid var(--ink); }
  .band:last-of-type { border-right: 0; }
  .band.on { font-weight: 900; text-decoration: underline; text-decoration-thickness: 2px; }
  .marker { position: absolute; left: -7px; top: -4px; bottom: -4px; width: 14px; background: var(--ink); border-radius: 7px;
            box-shadow: 0 0 0 3px var(--paper); }
</style>
