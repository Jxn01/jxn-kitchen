<script lang="ts">
  // What the blend (or the sauce) goes with, right now: all 25 foods on a board, MOUNTED ONCE (an OpenMoji drawing is expensive to
  // build on the Atom — the lábas lesson), each grown and lit by how well the blend suits it; the best three get a
  // rank. Tap a food: the jars (a sauce's: its items) that vouch for it, and why. The ranks and the why box are always there (shown by class)
  // and its lines are a fixed pool (lib/spices pool): nothing is built when an answer lands.
  import Icon from '../Icon.svelte';
  import { pool, SLOTS, type Bi, type Food } from '../../lib/spices';
  import type { Lang } from '../../lib/i18n';
  import { t } from '../../lib/i18n';
  let { foods, scored, lang, names, noneKey = 'spices.foods.none' }:
    { foods: Food[]; scored: { id: string; score: number; vouchers: (Bi & { spice?: string; item?: string })[] }[]; lang: Lang;
      names: Record<string, string>; noneKey?: string } = $props();
  let sel = $state<string | null>(null);
  let by = $derived(new Map(scored.map((f, i) => [f.id, { ...f, rank: i }])));
  let top = $derived(scored.length ? scored[0].score || 1 : 1);
  let chosen = $derived(sel ? by.get(sel) : scored[0] ? by.get(scored[0].id) : undefined);
</script>

<div class="board">
  {#each foods as f (f.id)}
    {@const s = by.get(f.id)}
    {@const k = s ? Math.max(0, s.score / top) : 0}
    <button class="cell pressable" class:on={chosen?.id === f.id} aria-label={f[lang]} onclick={() => (sel = f.id)}>
      <span class="ic" style:transform="scale({0.5 + 0.6 * k})" style:opacity={0.22 + 0.78 * k}><Icon name={f.icon} size={44} /></span>
      <span class="rank" class:gone={!(s && s.rank < 3 && s.score > 0)}>{s ? s.rank + 1 : ''}</span>
    </button>
  {/each}
</div>
<div class="why" class:gone={!chosen}>
  <b>{chosen ? `${foods.find((f) => f.id === chosen.id)?.[lang]} · ${Math.round(chosen.score * 100)} %` : ''}</b>
  {#each pool(chosen?.vouchers ?? [], SLOTS.vouchers) as v, k (k)}<p class:gone={!v}><span class="sp">{v ? names[v.spice ?? v.item ?? ''] : ''}</span> {v ? v[lang] : ''}</p>{/each}
  <p class:gone={!chosen || chosen.vouchers.length > 0}>{$t(noneKey)}</p>
</div>

<style>
  .board { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; }
  /* contained: a rank that comes and goes (or a cell lit) lays out and repaints that cell alone */
  .cell { contain: strict; position: relative; min-height: var(--touch); min-width: var(--touch); display: grid; place-items: center; padding: 0;
          border: 2.5px solid var(--ink); border-radius: var(--r-sm); background: var(--paper); }
  .cell.on { background: var(--butter); }
  .ic { display: block; transform-origin: 50% 50%; will-change: transform; }   /* resized by the compositor, never repainted */
  .rank { position: absolute; top: 3px; right: 4px; width: 20px; height: 20px; border-radius: 50%; background: var(--ink); color: #fff;
          font-weight: 900; font-size: 12px; display: grid; place-items: center; }
  /* taller than the most a food can say (its name and four jars, one line each, ~160 px with the chips): on the blend's page a box that grew or
     shrank with the food tapped moved every section below it */
  .why { margin-top: 10px; background: var(--paper); border: var(--outline) solid var(--ink); border-radius: var(--r-sm); padding: 10px 14px;
         min-height: 170px; }
  .why b { font-family: var(--font-display); font-weight: 400; font-size: 18px; }
  .why p { margin: 6px 0 0; font-weight: 700; font-size: 15px; line-height: 1.3; }
  .gone { display: none !important; }
  .sp { display: inline-block; background: var(--cream); border: 2px solid var(--ink); border-radius: 999px; padding: 0 8px; font-weight: 900; font-size: 13px; margin-right: 4px; }
</style>
