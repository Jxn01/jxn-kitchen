<script lang="ts">
  import PageHeader from '../components/PageHeader.svelte';
  import HaveButton from '../components/HaveButton.svelte';
  import Icon from '../components/Icon.svelte';
  import ItemTile from '../components/ItemTile.svelte';
  import Switch from '../components/Switch.svelte';
  import { catalogue, pantry, isOn } from '../lib/pantry';
  import { nameOf } from '../lib/search';
  import { color } from '../lib/palette';
  import { textOn } from '../lib/color';
  import { lang, t } from '../lib/i18n';
  import { go } from '../lib/router';
  import { toggleWithToast } from '../lib/pantry-actions';

  let { cat, sub }: { cat: string; sub?: string } = $props();
  const st = pantry.state;
  let category = $derived($catalogue?.categories.find((c) => c.id === cat));
  let group = $derived(category?.groups.find((g) => g.id === sub) ?? category?.groups[0]);
  let c = $derived(category ? color(category.color) : '#5C6B7A');
  const groupCount = (gid: string) => {
    const g = category?.groups.find((x) => x.id === gid);
    return g ? g.items.filter((i) => $st.have.includes(i.id)).length + ($st.groups_some.includes(g.id) ? 1 : 0) : 0;
  };
</script>

{#if category && group}
  <div class="screen">
    <PageHeader title={nameOf(category, $lang)} icon={category.icon} color={c} back={() => go('/pantry')}>
      <HaveButton />
    </PageHeader>
    <div class="body">
      <nav class="rail" aria-label={$t('pantry.groups')}>
        {#each category.groups as g (g.id)}
          {@const n = groupCount(g.id)}
          <button class="g pressable" class:sel={g.id === group.id} style:--c={c} style:color={g.id === group.id ? textOn(c) : 'var(--ink)'}
                  onclick={() => go(`/pantry/${category.id}/${g.id}`)}>
            <Icon name={g.icon} size={36} /><span class="gn">{nameOf(g, $lang)}</span>{#if n}<b>{n}</b>{/if}
          </button>
        {/each}
      </nav>
      <section class="pane">
        {#key group.id}
          <button class="some pressable" class:on={isOn($st, 'group:' + group.id)}
                  onclick={() => toggleWithToast('group:' + group.id, nameOf(group, $lang))}>
            <Icon name={group.icon} size={44} />
            <span>{$t('pantry.some', { name: nameOf(group, $lang).toLocaleLowerCase($lang) })}</span>
            <Switch on={isOn($st, 'group:' + group.id)} />
          </button>
          <div class="items stagger">
            {#each group.items as it (it.id)}
              <ItemTile name={nameOf(it, $lang)} icon={it.icon ?? group.icon} color={c} on={isOn($st, it.id)}
                        note={it.staple ? $t('pantry.staple') : ''}
                        ontoggle={() => toggleWithToast(it.id, nameOf(it, $lang))} />
            {/each}
          </div>
        {/key}
      </section>
    </div>
  </div>
{/if}

<style>
  .screen { height: 100%; display: flex; flex-direction: column; }
  .body { flex: 1; min-height: 0; display: flex; gap: 16px; padding: 16px 20px 20px; }
  .rail { flex: none; width: 236px; display: flex; flex-direction: column; gap: 8px; overflow-y: auto; padding: 2px 8px 90px 2px; }
  .g {
    flex: none; min-height: var(--touch); display: flex; align-items: center; gap: 10px; padding: 0 10px; text-align: left;
    border: var(--outline) solid var(--ink); border-radius: var(--r-sm); background: var(--paper); font-weight: 800; font-size: 15.5px;
  }
  .g.sel { background: var(--c); box-shadow: var(--shadow-sm); transform: translateX(6px); }
  .gn { flex: 1; min-width: 0; line-height: 1.1; }
  .g b { background: var(--herb); color: var(--ink); border-radius: 999px; padding: 1px 9px; font-size: 13px; }
  .pane { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 14px; overflow-y: auto; padding: 2px 8px 90px 2px; }
  .some {
    flex: none; min-height: 68px; display: flex; align-items: center; gap: 12px; padding: 0 16px; text-align: left;
    background: var(--butter); border: var(--outline) solid var(--ink); border-radius: var(--r); box-shadow: var(--shadow-sm);
    font-weight: 800; font-size: 17px;
  }
  .some span { flex: 1; }
  .items { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; }
  @media (max-aspect-ratio: 1/1) {
    .body { flex-direction: column; padding: 10px; }
    .rail { width: auto; flex-direction: row; overflow-x: auto; overflow-y: hidden; padding: 2px 2px 8px; }
    .g { min-width: 150px; }
    .g.sel { transform: translateY(-3px); }
    .items { grid-template-columns: repeat(2, 1fr); }
  }
</style>
