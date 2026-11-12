<script lang="ts">
  import PageHeader from '../components/PageHeader.svelte';
  import HaveButton from '../components/HaveButton.svelte';
  import Icon from '../components/Icon.svelte';
  import ItemTile from '../components/ItemTile.svelte';
  import { catalogue, pantry, isOn } from '../lib/pantry';
  import { search, nameOf, type CatCategory } from '../lib/search';
  import { color } from '../lib/palette';
  import { textOn } from '../lib/color';
  import { lang, t } from '../lib/i18n';
  import { go } from '../lib/router';
  import { osk } from '../lib/osk';
  import { fit } from '../lib/fit';
  import { toggleWithToast } from '../lib/pantry-actions';
  import { P } from '../lib/palette';

  let query = $state('');
  let hits = $derived($catalogue ? search($catalogue, query) : []);
  const pantryState = pantry.state;
  const countIn = (c: CatCategory) =>
    c.groups.reduce((n, g) => n + g.items.filter((i) => $pantryState.have.includes(i.id)).length
      + ($pantryState.groups_some.includes(g.id) ? 1 : 0), 0);
</script>

<div class="screen">
  {#snippet searchBox()}
    <label class="search">
      <Icon name="search" size={22} />
      <input type="search" bind:value={query} placeholder={$t('pantry.search')} use:osk autocomplete="off" />
      {#if query}<button class="x" aria-label={$t('a11y.clear')} onclick={() => (query = '')}>✕</button>{/if}
    </label>
  {/snippet}
  <PageHeader title={$t('pantry.title')} sub={$t('pantry.sub')} icon="pantry" color={P.mustard} back={() => go('/')}>
    <span class="wide">{@render searchBox()}</span>
    <HaveButton />
  </PageHeader>
  <div class="narrow">{@render searchBox()}</div>

  {#if !$catalogue}
    <div class="empty">…</div>
  {:else if query.trim()}
    <div class="results">
      {#each hits as h (h.kind + h.id)}
        {#if h.kind === 'item' && h.item}
          <ItemTile name={nameOf(h.item, $lang)} icon={h.item.icon ?? h.group.icon} color={color(h.category.color)}
                    on={isOn($pantryState, h.item.id)} ontoggle={() => toggleWithToast(h.item!.id, nameOf(h.item!, $lang))} />
        {:else}
          <button class="grouphit pressable" style:--c={color(h.category.color)} style:color={textOn(color(h.category.color))}
                  onclick={() => go(`/pantry/${h.category.id}/${h.group.id}`)}>
            <Icon name={h.group.icon} size={46} /><span>{nameOf(h.group, $lang)} →</span>
          </button>
        {/if}
      {:else}
        <p class="nothing">{$t('pantry.nothing')}</p>
      {/each}
    </div>
  {:else}
    <div class="cats stagger">
      {#each $catalogue.categories as c (c.id)}
        {@const n = countIn(c)}
        <button class="cat pressable" style:--c={color(c.color)} onclick={() => go(`/pantry/${c.id}`)}>
          <span class="plate"><Icon name={c.icon} size={58} /></span>
          <span class="cn" use:fit={nameOf(c, $lang)}>{nameOf(c, $lang)}</span>
          {#if n}<span class="badge">{$t('pantry.in', { n })}</span>{/if}
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .screen { height: 100%; display: flex; flex-direction: column; }
  .search {
    display: flex; align-items: center; gap: 8px; height: var(--touch); width: 330px; padding: 0 10px 0 14px;
    background: var(--paper); border: var(--outline) solid var(--ink); border-radius: 999px;
  }
  .search input { flex: 1; min-width: 0; align-self: stretch; border: 0; outline: 0; background: transparent; font: inherit; font-weight: 700; font-size: 17px; }
  .search input::-webkit-search-cancel-button { display: none; }
  .x { width: 52px; height: 52px; position: relative; border-radius: 50%; border: 0; background: var(--cream); font-weight: 900; }
  .cats {
    flex: 1; min-height: 0; display: grid; grid-template-columns: repeat(6, 1fr); grid-auto-rows: 1fr; gap: 16px; padding: 18px 20px 20px;
  }
  .cat {
    position: relative; background: var(--c); border: var(--outline) solid var(--ink); border-radius: var(--r);
    box-shadow: var(--shadow-sm); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px;
    padding: 8px; min-width: 0;
  }
  .plate { width: 78px; height: 78px; border-radius: 50%; background: var(--cream); border: var(--outline) solid var(--ink);
           display: grid; place-items: center; }
  .cn { font-family: var(--font-display); font-size: 15.5px; line-height: 1.1; background: var(--cream); border: 2px solid var(--ink);
        border-radius: 9px; padding: 3px 8px; max-width: 100%; white-space: nowrap; overflow: hidden; display: block; text-align: center; }
  .badge { position: absolute; top: -10px; right: -8px; background: var(--ink); color: #fff; font-weight: 900; font-size: 13px;
           border-radius: 999px; padding: 3px 9px; transform: rotate(8deg); }
  .results { flex: 1; min-height: 0; overflow-y: auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
             grid-auto-rows: min-content; gap: 12px; padding: 16px 20px calc(var(--kb-h) + 10px); }
  .grouphit { min-height: 118px; border-radius: var(--r); border: var(--outline) dashed var(--ink); background: var(--c);
              display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; font-weight: 900; font-size: 15px; }
  .nothing, .empty { grid-column: 1 / -1; font-weight: 800; font-size: 19px; opacity: .6; text-align: center; padding: 40px; }
  .narrow { display: none; }
  @media (max-aspect-ratio: 1/1) {
    .cats { grid-template-columns: repeat(2, 1fr); overflow-y: auto; grid-auto-rows: 150px; }
    .wide { display: none; }
    .narrow { display: flex; padding: 12px 12px 0; } .narrow .search { width: auto; flex: 1; }
  }
  .x::after { content: ''; position: absolute; inset: -6px; }   /* 64 px hit area */
</style>
