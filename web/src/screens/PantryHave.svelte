<script lang="ts">
  import MascotNote from '../components/MascotNote.svelte';
  import PageHeader from '../components/PageHeader.svelte';
  import Icon from '../components/Icon.svelte';
  import { catalogue, pantry } from '../lib/pantry';
  import { nameOf } from '../lib/search';
  import { color, P } from '../lib/palette';
  import { textOn } from '../lib/color';
  import { lang, t } from '../lib/i18n';
  import { go } from '../lib/router';
  import { toggleWithToast } from '../lib/pantry-actions';
  const st = pantry.state;
  // Everything that is in, grouped by category: the "some … somewhere" switches first, then the items.
  let sections = $derived(($catalogue?.categories ?? []).map((c) => ({
    c,
    chips: [
      ...c.groups.filter((g) => $st.groups_some.includes(g.id))
        .map((g) => ({ node: 'group:' + g.id, name: '~ ' + nameOf(g, $lang), icon: g.icon })),
      ...c.groups.flatMap((g) => g.items.filter((i) => $st.have.includes(i.id))
        .map((i) => ({ node: i.id, name: nameOf(i, $lang), icon: i.icon ?? g.icon }))),
    ],
  })).filter((s) => s.chips.length));
</script>

<div class="screen">
  <PageHeader title={$t('pantry.have')} icon="checkmark" color={P.herb} back={() => go('/pantry')} />
  <div class="list">
    {#each sections as s (s.c.id)}
      <section>
        <h2 style:--c={color(s.c.color)} style:color={textOn(color(s.c.color))}>{nameOf(s.c, $lang)}</h2>
        <div class="chips">
          {#each s.chips as ch (ch.node)}
            <button class="chip pressable" onclick={() => toggleWithToast(ch.node, ch.name.replace(/^~ /, ''))}>
              <Icon name={ch.icon} size={32} /><span>{ch.name}</span>
            </button>
          {/each}
        </div>
      </section>
    {:else}
      <MascotNote act="shrug" text={$t('pantry.have.empty')} />
    {/each}
  </div>
</div>

<style>
  .screen { height: 100%; display: flex; flex-direction: column; }
  .list { flex: 1; min-height: 0; overflow-y: auto; padding: 16px 20px 100px; display: flex; flex-direction: column; gap: 14px; }
  h2 { display: inline-block; font-size: 17px; background: var(--c); border: var(--outline) solid var(--ink); border-radius: 10px;
       padding: 4px 12px; margin-bottom: 8px; }
  .chips { display: flex; flex-wrap: wrap; gap: 10px; }
  .chip { min-height: var(--touch); display: flex; align-items: center; gap: 8px; padding: 0 16px 0 10px; border-radius: 999px;
          border: var(--outline) solid var(--ink); background: var(--paper); font-weight: 800; font-size: 16px; }
</style>
