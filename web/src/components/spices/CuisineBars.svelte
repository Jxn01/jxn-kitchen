<script lang="ts">
  // Which kitchen the blend leans to: the top three cuisines, as bars (a fixed pool: an answer only fills them).
  import { pool, SLOTS, type Labelled } from '../../lib/spices';
  import type { Lang } from '../../lib/i18n';
  let { cuisines, labels, lang }: { cuisines: { id: string; pct: number }[]; labels: Labelled[]; lang: Lang } = $props();
  let top = $derived(Math.max(1, ...cuisines.map((c) => c.pct)));
</script>

<ul class="cb">
  {#each pool(cuisines, SLOTS.cuisines) as c, i (i)}
    <li class:gone={!c}><span class="l">{c ? (labels.find((x) => x.id === c.id)?.[lang] ?? c.id) : ''}</span>
      <span class="bar"><span style:transform="scaleX({c ? c.pct / top : 0})"></span></span><b>{c ? `${c.pct} %` : ''}</b></li>
  {/each}
</ul>

<style>
  .cb { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
  li { display: grid; grid-template-columns: 9.5em 1fr 3.2em; align-items: center; gap: 8px; font-weight: 800; font-size: 14px; }
  .l { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .bar { height: 16px; border: 2px solid var(--ink); border-radius: 999px; overflow: hidden; background: var(--cream); }
  .bar span { display: block; height: 100%; background: var(--plum); transform-origin: 0 50%; }
  b { text-align: right; }
  li.gone { display: none; }
</style>
