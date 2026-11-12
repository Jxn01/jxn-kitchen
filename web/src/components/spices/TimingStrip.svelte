<script lang="ts">
  // When each jar wants to meet the pan: blooming in the hot fat, with the liquid, at the very end. Each lane is a
  // fixed pool of jar slots (an answer only fills them), and the dash of an empty lane is always there.
  import MiniJar from './MiniJar.svelte';
  import { pool, SLOTS, type Evaluation, type Jar, type Labelled } from '../../lib/spices';
  import type { Lang } from '../../lib/i18n';
  let { timing, timings, jars, lang }: { timing: Evaluation['timing']; timings: Labelled[]; jars: Map<string, Jar>; lang: Lang } = $props();
  const LANE = { bloom: 'tangerine', during: 'butter', finish: 'leaf' } as const;
</script>

<div class="lanes">
  {#each timings as tm (tm.id)}
    {@const ids = timing[tm.id as 'bloom' | 'during' | 'finish'] ?? []}
    <div class="lane" style:--c="var(--{LANE[tm.id as keyof typeof LANE]})">
      <span class="h">{tm[lang]}</span>
      <div class="jars">
        {#each pool(ids, SLOTS.lane) as id, k (k)}
          {@const j = id ? jars.get(id) : undefined}
          <span class="j" class:gone={!id}><MiniJar fill={j?.fill} size={30} /><small>{j ? j.label[lang] : (id ?? '')}</small></span>
        {/each}
        <span class="none" class:gone={ids.length}>—</span>
      </div>
    </div>
  {/each}
</div>

<style>
  .lanes { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
  .lane { border: var(--outline) solid var(--ink); border-radius: var(--r-sm); background: var(--c); padding: 8px; min-height: 120px; }
  .h { display: block; font-weight: 900; font-size: 13.5px; margin-bottom: 6px; }
  .jars { display: flex; flex-wrap: wrap; gap: 6px; }
  .j { display: flex; flex-direction: column; align-items: center; width: 62px; }
  small { font-weight: 800; font-size: 10.5px; text-align: center; line-height: 1.1; }
  .none { font-weight: 900; opacity: .4; } .gone { display: none !important; }
</style>
