<script lang="ts">
  // The family tree: all forty sauce families in their ten groups, the sauce's path lit (a group, its family, a child —
  // mayonnaise → aïoli). On the sauce's page it is a picture of where the sauce sits; in the editor's family sheet each
  // family is a button (`onpick`) and the user's choice is marked. Built once: a new answer only moves the lit path.
  import { familyTree, type Family } from '../../lib/sauces';
  import type { Lang } from '../../lib/i18n';
  let { families, path = [], lang, onpick = null, chosen = null }:
    { families: Family[]; path?: string[]; lang: Lang; onpick?: ((id: string) => void) | null; chosen?: string | null } = $props();
  let tree = $derived(familyTree(families));
  let lit = $derived(new Set(path));
</script>

{#snippet node(f: { id: string; en: string; hu: string }, depth: number)}
  {#if onpick}
    <button class="fam d{depth} pressable" class:lit={lit.has(f.id)} class:chosen={chosen === f.id} onclick={() => onpick?.(f.id)}>{f[lang]}</button>
  {:else}
    <span class="fam d{depth}" class:lit={lit.has(f.id)}>{f[lang]}</span>
  {/if}
{/snippet}

<div class="tree" class:picking={!!onpick}>
  {#each tree as g (g.id)}
    <div class="group" class:lit={lit.has(g.id)}>
      {@render node(g, 0)}
      {#each g.kids as k (k.id)}
        <div class="branch">
          {@render node(k, 1)}
          {#each k.kids as kk (kk.id)}<div class="twig">{@render node(kk, 2)}</div>{/each}
        </div>
      {/each}
    </div>
  {/each}
</div>

<style>
  .tree { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 8px; }
  .group { contain: content; display: flex; flex-direction: column; gap: 4px; padding: 8px; border: 2.5px solid #CDBFA8; border-radius: var(--r-sm);
           background: var(--paper); }
  .group.lit { border-color: var(--ink); background: var(--cream); }
  .branch { display: flex; flex-direction: column; gap: 3px; margin-left: 10px; padding-left: 8px; border-left: 3px solid #E2D6C4; }
  .group.lit .branch { border-left-color: #CDBFA8; }
  .twig { margin-left: 10px; }
  .fam { display: block; font-weight: 800; font-size: 13.5px; line-height: 1.2; padding: 3px 8px; border-radius: 999px; border: 2px solid transparent; }
  .fam.d0 { font-family: var(--font-display); font-weight: 400; font-size: 16px; padding-left: 2px; }
  .fam.lit { background: var(--butter); border-color: var(--ink); }
  .fam.d0.lit { background: none; border-color: transparent; text-decoration: underline; text-decoration-thickness: 3px; text-decoration-color: var(--tangerine); }
  /* the sheet: every family a full touch target */
  .picking .fam { min-height: var(--touch); width: 100%; text-align: left; background: var(--paper); border: 2.5px solid var(--ink); font: inherit;
                  font-weight: 800; font-size: 14px; color: var(--ink); padding: 0 10px; border-radius: var(--r-sm); }
  .picking .fam.d0 { font-family: var(--font-display); font-weight: 400; font-size: 16px; }
  .picking .fam.lit { background: var(--cream); }
  .picking .fam.chosen { background: var(--butter); box-shadow: inset 0 0 0 3px var(--ink); }
</style>
