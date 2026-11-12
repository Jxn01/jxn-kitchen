<script lang="ts">
  // "Move … to…": the whole folder tree as one list, the top level first. `current` is where the thing is now (marked,
  // not pickable); `blocked` are folders it may not go into (a folder's own subtree). A sheet, built when it opens.
  import Icon from './Icon.svelte';
  import { folderList, treeRows } from '../lib/folders';
  import { t } from '../lib/i18n';
  let { title, current, blocked = new Set<number>(), onpick, oncancel }:
    { title: string; current: number | null; blocked?: Set<number>; onpick: (folder: number | null) => void; oncancel: () => void } = $props();
  let rows = $derived(treeRows($folderList));
</script>

<div class="scrim" role="presentation" onclick={oncancel}></div>
<div class="sheet" role="dialog" aria-modal="true" aria-label={title}>
  <h2>{title}</h2>
  <div class="list">
    <button class="row pressable" class:here={current === null} disabled={current === null} onclick={() => onpick(null)}>
      <Icon name="recipes" size={30} /><span class="n">{$t('folders.pick.top')}</span>
      <span class="tag">{$t('folders.here')}</span>
    </button>
    {#each rows as r (r.folder.id)}
      <button class="row pressable" class:here={current === r.folder.id} disabled={current === r.folder.id || blocked.has(r.folder.id)}
              style:--d={r.depth + 1} onclick={() => onpick(r.folder.id)}>
        <Icon name={current === r.folder.id ? 'folder-open' : 'folder'} size={30} /><span class="n">{r.folder.name}</span>
        <span class="tag">{$t('folders.here')}</span>
      </button>
    {/each}
  </div>
  <button class="cancel pressable" onclick={oncancel}>{$t('folders.cancel')}</button>
</div>

<style>
  .scrim { position: fixed; inset: 0; background: rgba(0, 0, 0, .35); z-index: 35; }
  .sheet {
    position: fixed; left: 50%; top: calc(24px + env(safe-area-inset-top)); transform: translateX(-50%); z-index: 36; width: min(620px, calc(100vw - 24px));
    background: var(--cream); border: var(--outline-thick) solid var(--ink); border-radius: var(--r-lg); box-shadow: var(--shadow);
    padding: 18px; display: flex; flex-direction: column; gap: 12px; max-height: calc(100vh - 48px);
    max-height: calc(100dvh - 48px - env(safe-area-inset-top) - env(safe-area-inset-bottom));
  }
  h2 { font-size: 22px; }
  .list { display: flex; flex-direction: column; gap: 6px; overflow-y: auto; min-height: 0; }
  .row { flex: none; min-height: var(--touch); display: flex; align-items: center; gap: 10px; padding: 0 14px 0 calc(10px + (var(--d, 0) * 22px));
         border-radius: var(--r); border: var(--outline) solid var(--ink); background: var(--paper); font-weight: 800; font-size: 17px; text-align: left; }
  .row:disabled { opacity: .45; }
  .row.here { opacity: 1; background: var(--butter); border-style: dashed; }
  .n { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .tag { display: none; font-size: 13px; font-weight: 800; border: 2px solid var(--ink); border-radius: 999px; padding: 1px 8px; background: var(--paper); }
  .row.here .tag { display: inline; }
  .cancel { flex: none; min-height: var(--touch); border-radius: var(--r); border: var(--outline) solid var(--ink); background: var(--paper); font-weight: 800; font-size: 16px; }
  @media (max-aspect-ratio: 1/1) { .row { padding-left: calc(8px + (var(--d, 0) * 14px)); font-size: 16px; } }
</style>
