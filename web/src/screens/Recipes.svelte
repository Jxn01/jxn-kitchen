<script lang="ts">
  import MascotNote from '../components/MascotNote.svelte';
  import { onMount } from 'svelte';
  import PageHeader from '../components/PageHeader.svelte';
  import Icon from '../components/Icon.svelte';
  import FolderPicker from '../components/FolderPicker.svelte';
  import FolderName from '../components/FolderName.svelte';
  import { api, badge, filterRecipes, recipeList, loadRecipes, type FilterMode, type Summary } from '../lib/recipes';
  import { childrenOf, folderList, foldersLoaded, pathLabel, pathOf, refusalKey, subtree } from '../lib/folders';
  import { folders } from '../lib/folderactions';
  import { importLink } from '../lib/importflow';
  import { importDraft } from '../lib/recipes';
  import { isKiosk } from '../lib/kiosk';
  import { showToast } from '../lib/toast';
  import { fold } from '../lib/search';
  import { P } from '../lib/palette';
  import { t } from '../lib/i18n';
  import { go } from '../lib/router';
  import { osk } from '../lib/osk';

  /** The folder being looked at; null = the top level. */
  let { folder = null }: { folder?: number | null } = $props();

  let reading = $state(false);
  async function fromPhoto(e: Event) {
    const file = (e.currentTarget as HTMLInputElement).files?.[0];
    (e.currentTarget as HTMLInputElement).value = '';
    if (!file) return;
    reading = true;
    showToast({ text: $t('recipes.photo.reading') }, 20000);
    try {
      const ids = await api.scan(file);
      if (ids.length > 1) showToast({ text: $t('recipes.photo.many', { n: ids.length }) }, 8000);
      importDraft.set({ id: ids[0], code: 'scan' });
      go(`/recipe/${ids[0]}/edit`);
    } catch { showToast({ text: $t('recipes.photo.failed'), tone: 'warn' }, 8000); }
    finally { reading = false; }
  }

  let q = $state('');
  let mode = $state<FilterMode>('all');
  let tag = $state<string | null>(null);
  let importing = $state(false);
  let link = $state('');
  let busy = $state(false);
  onMount(loadRecipes);
  let tags = $derived([...new Set($recipeList.flatMap((r) => r.tags))].sort().slice(0, 6));
  let cookable = $state<Summary[]>([]);

  // A search, a filter or a tag looks through EVERY folder (each hit says where it lives); otherwise the screen shows
  // the folder being looked at: its subfolders, then its own recipes.
  let flat = $derived(!!q.trim() || mode !== 'all' || !!tag);
  let here = $derived(folder === null ? null : $folderList.find((f) => f.id === folder) ?? null);
  let crumbs = $derived(pathOf($folderList, folder));
  let subfolders = $derived(flat ? [] : childrenOf($folderList, folder));
  let shown = $derived(flat
    ? (mode === 'cook' ? cookable : filterRecipes($recipeList, { mode, tag }))
        .filter((r) => !q.trim() || fold(r.title).includes(fold(q)) || r.tags.some((x) => fold(x).includes(fold(q))))
    : $recipeList.filter((r) => r.folder_id === folder));
  // a folder deleted (here or on another screen) while it was open: go up to the top level
  $effect(() => { if (folder !== null && $foldersLoaded && !here) go('/recipes', { replace: true }); });

  async function bringIn() {
    if (!link.trim()) return;
    busy = true;
    if (await importLink(link)) { link = ''; importing = false; }
    busy = false;
  }
  // What can I cook (spec §6.3): ranked by the share in stock, GF-ready first — the server's order
  $effect(() => { if (mode === 'cook') api.cookable().then((x) => (cookable = x)).catch(() => {}); void $recipeList; });

  // --- folders: name, move, delete; select recipes and move them ---------------------------------------------
  let naming = $state<null | 'new' | 'rename'>(null);
  let picking = $state<null | 'recipes' | 'folder'>(null);
  let deleting = $state(false);
  let selecting = $state(false);
  let picked = $state<number[]>([]);
  $effect(() => { void folder; selecting = false; picked = []; });       // a selection belongs to one folder view

  const place = (id: number | null) => (id === null ? $t('folders.pick.top') : pathLabel($folderList, id));
  const toggle = (id: number) => { picked = picked.includes(id) ? picked.filter((x) => x !== id) : [...picked, id]; };

  async function saveName(name: string): Promise<string | null> {
    try {
      if (naming === 'new') await folders.create(name, folder);      // offline: made here, sent at the next reconnect
      else if (here) await folders.rename(here.id, name);
      naming = null;
      return null;
    } catch (e) { return $t(refusalKey(e)); }
  }
  async function pickedPlace(target: number | null) {
    const what = picking;
    picking = null;
    try {
      if (what === 'recipes') {
        await folders.moveRecipes(picked, target);
        selecting = false; picked = [];
      } else if (what === 'folder' && here) {
        await folders.move(here.id, target);
      }
      showToast({ text: $t('folders.moved', { place: place(target) }) });
    } catch (e) { showToast({ text: $t(refusalKey(e)), tone: 'warn' }, 6000); }
  }
  async function deleteHere() {
    if (!here) return;
    const parent = here.parent_id;
    deleting = false;
    try {
      await folders.remove(here.id);
      go(parent === null ? '/recipes' : `/recipes/${parent}`, { replace: true });
      showToast({ text: $t('folders.deleted', { place: place(parent) }) });
    } catch (e) { showToast({ text: $t(refusalKey(e)), tone: 'warn' }); }
  }
</script>

<div class="screen">
  <PageHeader title={here ? here.name : $t('recipes.title')} icon={here ? 'folder-open' : 'recipes'} color={P.tomato}
              back={() => go(here ? (here.parent_id === null ? '/recipes' : `/recipes/${here.parent_id}`) : '/')}>
    <input class="search" type="search" bind:value={q} placeholder={$t('recipes.search')} use:osk autocomplete="off" />
    <button class="hbtn pressable" aria-label={$t('recipes.import')} onclick={() => (importing = !importing)}><Icon name="browse" size={26} /><span class="lbl">{$t('recipes.import')}</span></button>
    {#if !$isKiosk}
      <label class="hbtn pressable" class:busy={reading} aria-label={$t('recipes.photo')}><Icon name="camera" size={26} /><span class="lbl">{$t('recipes.photo')}</span>
        <input type="file" accept="image/*,application/pdf" capture="environment" onchange={fromPhoto} disabled={reading} hidden />
      </label>
    {/if}
    <button class="hbtn new pressable" aria-label={$t('recipes.new')} onclick={() => go(`/recipe/new${folder !== null ? `?folder=${folder}` : ''}`)}><Icon name="plus" size={24} /><span class="lbl">{$t('recipes.new')}</span></button>
  </PageHeader>
  {#if importing}
    <form class="import" onsubmit={(e) => { e.preventDefault(); bringIn(); }}>
      <input bind:value={link} placeholder={$t('recipes.import.ph')} use:osk inputmode="url" autocomplete="off" />
      <button class="pressable" disabled={busy || !link.trim()}>{busy ? $t('recipes.import.busy') : $t('recipes.import.go')}</button>
    </form>
  {/if}
  <div class="filters">
    {#each [['all', 'recipes.filter.all'], ['cook', 'recipes.filter.cook'], ['cookable', 'recipes.filter.cookable'], ['quick', 'recipes.filter.quick']] as [m, k]}
      <button class="f pressable" class:on={mode === m && !tag} onclick={() => { mode = m as FilterMode; tag = null; }}>{$t(k)}</button>
    {/each}
    {#each tags as tg}<button class="f tag pressable" class:on={tag === tg} onclick={() => (tag = tag === tg ? null : tg)}>#{tg}</button>{/each}
  </div>
  <div class="bar" class:deep={crumbs.length > 0}>
    <nav class="crumbs" aria-label={$t('recipes.title')}>
      <button class="crumb pressable" class:cur={folder === null} onclick={() => go('/recipes')}><Icon name="recipes" size={24} /><span>{$t('recipes.title')}</span></button>
      {#each crumbs as c (c.id)}
        <span class="sep">›</span>
        <button class="crumb pressable" class:cur={c.id === folder} onclick={() => go(`/recipes/${c.id}`)}><span>{c.name}</span></button>
      {/each}
    </nav>
    <!-- both sets are always there and swapped by class: a tap never builds icons -->
    <div class="acts" class:off={selecting}>
      {#if here}
        <button class="act pressable" aria-label={$t('folders.rename')} onclick={() => (naming = 'rename')}><span class="glyph">✎</span><span class="lbl">{$t('folders.rename')}</span></button>
        <button class="act pressable" aria-label={$t('folders.move')} onclick={() => (picking = 'folder')}><Icon name="folder" size={24} /><span class="lbl">{$t('folders.move')}</span></button>
        <button class="act pressable" aria-label={$t('folders.delete')} onclick={() => (deleting = true)}><Icon name="trash" size={24} /><span class="lbl">{$t('folders.delete')}</span></button>
      {/if}
      <button class="act pressable" aria-label={$t('folders.new')} onclick={() => (naming = 'new')}><Icon name="plus" size={22} /><span class="lbl">{$t('folders.new')}</span></button>
      <button class="act pressable" aria-label={$t('folders.select')} onclick={() => (selecting = true)}><Icon name="checkmark" size={22} /><span class="lbl">{$t('folders.select')}</span></button>
    </div>
    <div class="acts sel" class:off={!selecting}>
      <span class="count">{$t('folders.selected', { n: picked.length })}</span>
      <button class="act go pressable" disabled={!picked.length} onclick={() => (picking = 'recipes')}><Icon name="folder" size={24} /><span>{$t('folders.moveto')}</span></button>
      <button class="act pressable" onclick={() => { selecting = false; picked = []; }}>{$t('folders.done')}</button>
    </div>
  </div>
  <div class="scroll">
    {#if subfolders.length}
      <div class="folders">
        {#each subfolders as f (f.id)}
          <button class="folder pressable" onclick={() => go(`/recipes/${f.id}`)}>
            <Icon name="folder" size={44} />
            <span class="fn">{f.name}</span>
            <span class="fc">{[$t('folders.recipes', { n: f.recipes }), ...(f.folders ? [$t('folders.folders', { n: f.folders })] : [])].join(' · ')}</span>
          </button>
        {/each}
      </div>
    {/if}
    <div class="grid stagger" class:selecting>
      {#each shown as r (r.id)}
        {@const b = badge(r.verdict)}
        <button class="card pressable" class:picked={picked.includes(r.id)} aria-pressed={selecting ? picked.includes(r.id) : undefined}
                onclick={() => (selecting ? toggle(r.id) : go(`/recipe/${r.id}`))}>
          <span class="pic">{#if r.image}<img src={r.image} alt="" loading="lazy" />{:else}<Icon name="recipes" size={64} />{/if}<span class="tick" aria-hidden="true">✓</span></span>
          <span class="t">{r.title}</span>
          <span class="meta">
            {#if r.minutes}<span class="mins"><Icon name="cook" size={18} />{$t('recipes.min', { n: r.minutes })}</span>{/if}
            <span class="b {b.tone}">{$t(`badge.${b.kind}`, { n: b.n })}</span>
            {#if r.total}<span class="have" class:all={r.missing === 0}>{r.have}/{r.total}</span>{/if}
          </span>
          {#if flat && r.folder_id !== null}<span class="where">{$t('folders.in', { place: place(r.folder_id) })}</span>{/if}
          {#if mode === 'cook' && r.missing_names?.length}
            <span class="miss">{$t('recipes.missing.list', { list: r.missing_names.join(', ') + (r.missing > r.missing_names.length ? ' …' : '') })}</span>
          {/if}
        </button>
      {:else}
        {#if !subfolders.length}
          <div class="empty"><MascotNote act="shrug" text={here && !flat ? $t('folders.empty') : $t('recipes.empty')} /></div>
        {/if}
      {/each}
    </div>
  </div>
</div>

{#if naming}
  <FolderName title={naming === 'new' ? $t('folders.name.new') : $t('folders.name.rename')} initial={naming === 'rename' ? here?.name ?? '' : ''}
              onsave={saveName} oncancel={() => (naming = null)} />
{/if}
{#if picking === 'recipes'}
  <FolderPicker title={$t('folders.pick.recipes', { n: picked.length })} current={folder} onpick={pickedPlace} oncancel={() => (picking = null)} />
{:else if picking === 'folder' && here}
  <FolderPicker title={$t('folders.pick.folder', { name: here.name })} current={here.parent_id} blocked={subtree($folderList, here.id)}
                onpick={pickedPlace} oncancel={() => (picking = null)} />
{/if}
{#if deleting && here}
  <div class="scrim" role="presentation" onclick={() => (deleting = false)}></div>
  <div class="sheet" role="dialog" aria-modal="true">
    <h2>{$t('folders.delete.title', { name: here.name })}</h2>
    <p>{$t('folders.delete.body', { place: place(here.parent_id) })}</p>
    <div class="row">
      <button class="danger pressable" onclick={deleteHere}>{$t('folders.delete.go')}</button>
      <button class="cancel pressable" onclick={() => (deleting = false)}>{$t('folders.cancel')}</button>
    </div>
  </div>
{/if}

<style>
  .screen { height: 100%; display: flex; flex-direction: column; }
  .search { height: var(--touch); width: 250px; border: var(--outline) solid var(--ink); border-radius: 999px; padding: 0 18px; font: inherit; font-weight: 700; font-size: 16px; background: var(--paper); }
  .hbtn { min-height: var(--touch); display: flex; align-items: center; gap: 6px; padding: 0 14px; border-radius: 999px; border: var(--outline) solid var(--ink);
          background: var(--paper); font-weight: 800; font-size: 15px; white-space: nowrap; }
  .hbtn.new { background: var(--herb); color: var(--ink); }
  label.hbtn { cursor: pointer; } .hbtn.busy { opacity: .5; }
  .import { display: flex; gap: 10px; padding: 12px 20px 0; }
  .import input { flex: 1; height: var(--touch); border: var(--outline) solid var(--ink); border-radius: var(--r); padding: 0 16px; font: inherit; font-weight: 700; font-size: 17px; }
  .import button { min-width: 150px; min-height: var(--touch); border-radius: var(--r); border: var(--outline) solid var(--ink); background: var(--sky); font-weight: 900; font-size: 16px; }
  .filters { display: flex; gap: 8px; padding: 12px 20px 4px; overflow-x: auto; flex: none; }
  .f { flex: none; min-height: var(--touch); min-width: var(--touch); padding: 0 16px; border-radius: 999px; border: var(--outline) solid var(--ink); background: var(--paper); font-weight: 800; font-size: 15px; white-space: nowrap; }
  .f.on { background: var(--ink); color: #fff; }

  /* the folder bar: where you are on the left, what you can do on the right */
  .bar { flex: none; display: flex; align-items: center; gap: 10px; padding: 6px 20px 2px; }
  .crumbs { flex: 1; min-width: 0; display: flex; align-items: center; gap: 4px; overflow-x: auto; }
  .crumb { flex: none; min-height: var(--touch); display: flex; align-items: center; gap: 6px; padding: 0 12px; border-radius: 999px; border: 0;
           background: none; font-weight: 800; font-size: 16px; white-space: nowrap; max-width: 260px; }
  .crumb span { overflow: hidden; text-overflow: ellipsis; }
  .crumb.cur { background: var(--butter); border: var(--outline) solid var(--ink); }
  .sep { flex: none; font-weight: 900; font-size: 20px; opacity: .5; }
  .acts { flex: none; display: flex; align-items: center; gap: 8px; }
  .acts.off { display: none; }
  .act { min-height: var(--touch); min-width: var(--touch); display: flex; align-items: center; justify-content: center; gap: 6px; padding: 0 12px;
         border-radius: 999px; border: var(--outline) solid var(--ink); background: var(--paper); font-weight: 800; font-size: 15px; white-space: nowrap; }
  .act:disabled { opacity: .45; }
  .act.go { background: var(--sky); }
  .glyph { font-size: 20px; line-height: 1; }
  .count { font-weight: 900; font-size: 16px; padding: 0 6px; white-space: nowrap; }

  .scroll { flex: 1; min-height: 0; overflow-y: auto; padding: 8px 20px 100px; display: flex; flex-direction: column; gap: 16px; }
  .folders { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }
  .folder { min-height: 76px; display: grid; grid-template-columns: auto minmax(0, 1fr); grid-template-rows: auto auto; column-gap: 10px; align-items: center;
            text-align: left; padding: 8px 14px; background: var(--butter); border: var(--outline) solid var(--ink); border-radius: var(--r); box-shadow: var(--shadow-sm); }
  .folder :global(svg) { grid-row: 1 / span 2; }
  .fn { font-family: var(--font-display); font-size: 19px; line-height: 1.15; overflow: hidden; overflow-wrap: anywhere;
        display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; }
  .fc { font-weight: 800; font-size: 13.5px; opacity: .75; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); grid-auto-rows: min-content; gap: 16px; }
  .card { display: flex; flex-direction: column; text-align: left; background: var(--paper); border: var(--outline) solid var(--ink); border-radius: var(--r);
          box-shadow: var(--shadow-sm); overflow: hidden; padding: 0; }
  .pic { position: relative; height: 150px; background: var(--salmon); display: grid; place-items: center; border-bottom: var(--outline) solid var(--ink); overflow: hidden; }
  .pic img { width: 100%; height: 100%; object-fit: cover; display: block; }
  /* select mode: a round tick on every card, filled on the picked ones (always in the page, shown by class) */
  .tick { position: absolute; top: 10px; left: 10px; width: 44px; height: 44px; border-radius: 50%; border: var(--outline) solid var(--ink); background: var(--paper);
          display: none; place-items: center; font-weight: 900; font-size: 24px; color: transparent; }
  .selecting .tick { display: grid; }
  .card.picked { outline: 5px solid var(--ink); outline-offset: -2px; }
  .card.picked .tick { background: var(--herb); color: var(--ink); }
  .t { font-family: var(--font-display); font-size: 19px; line-height: 1.15; padding: 10px 12px 4px; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .mins { display: inline-flex; align-items: center; gap: 4px; }
  .meta { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; padding: 4px 12px 12px; font-weight: 800; font-size: 13.5px; }
  .b { border: 2px solid var(--ink); border-radius: 999px; padding: 1px 8px; }
  .b.ok { background: #CFEFD0; } .b.swap { background: var(--teal); color: var(--ink); } .b.warn { background: var(--butter); } .b.unknown { border-style: dashed; }
  .have { margin-left: auto; background: var(--cream); border-radius: 999px; padding: 1px 9px; }
  .have.all { background: var(--herb); color: var(--ink); }
  .where { padding: 0 12px 10px; font-weight: 800; font-size: 13px; opacity: .7; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .miss { padding: 0 12px 12px; font-weight: 700; font-size: 13.5px; opacity: .75; }
  .empty { grid-column: 1 / -1; text-align: center; font-weight: 800; font-size: 19px; padding: 50px 20px; }

  .scrim { position: fixed; inset: 0; background: rgba(0, 0, 0, .35); z-index: 35; }
  .sheet { position: fixed; left: 50%; top: calc(24px + env(safe-area-inset-top)); transform: translateX(-50%); z-index: 36; width: min(560px, calc(100vw - 24px));
           background: var(--cream); border: var(--outline-thick) solid var(--ink); border-radius: var(--r-lg); box-shadow: var(--shadow);
           padding: 18px; display: flex; flex-direction: column; gap: 12px; }
  .sheet h2 { font-size: 22px; } .sheet p { font-weight: 700; font-size: 16px; }
  .row { display: flex; gap: 10px; }
  .danger { flex: 1; min-height: var(--touch); border-radius: var(--r); border: var(--outline) solid var(--ink); background: var(--tomato); color: var(--ink); font-weight: 900; font-size: 16px; }
  .cancel { min-height: var(--touch); padding: 0 20px; border-radius: var(--r); border: var(--outline) solid var(--ink); background: var(--paper); font-weight: 800; }

  @media (max-aspect-ratio: 1/1) {
    .search { display: none; } .grid { grid-template-columns: 1fr; }
    .lbl { display: none; } .hbtn { min-width: var(--touch); justify-content: center; padding: 0 10px; }   /* phones: icons only */
    /* a row per recipe: the picture as a square on the left, so three or four recipes show at once instead of two cards
       that were mostly an empty salmon block */
    .scroll { padding: 8px 12px 24px; gap: 12px; } .grid { gap: 12px; } .filters { padding: 10px 12px 4px; } .import { padding: 10px 12px 0; }
    .bar { padding: 6px 12px 2px; flex-wrap: wrap; row-gap: 4px; } .bar.deep .crumbs { flex-basis: 100%; } .acts { margin-left: auto; } .act { padding: 0 10px; }
    .folders { grid-template-columns: 1fr 1fr; gap: 10px; } .folder { min-height: calc(var(--touch) + 12px); padding: 6px 10px; } .fn { font-size: 17px; }
    .card { display: grid; grid-template-columns: 96px minmax(0, 1fr); grid-auto-rows: min-content; align-content: start; }
    .pic { grid-row: 1 / span 5; height: 100%; min-height: 96px; border-bottom: 0; border-right: var(--outline) solid var(--ink); }
    .pic :global(svg) { width: 40px; height: 40px; }
    .tick { top: 6px; left: 6px; width: 36px; height: 36px; font-size: 20px; }
    .t { font-size: 17px; padding: 9px 10px 2px; } .meta { padding: 4px 10px 8px; font-size: 13px; } .miss, .where { padding: 0 10px 9px; font-size: 13px; }
    .import button { min-width: 0; padding: 0 14px; }
  }
</style>
