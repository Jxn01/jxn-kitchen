<script lang="ts">
  // "What is this line?" — pick the catalogue item by search, or declare the line gluten-free by hand.
  import Icon from './Icon.svelte';
  import { catalogue } from '../lib/pantry';
  import { search, nameOf } from '../lib/search';
  import { lang, t } from '../lib/i18n';
  import { osk } from '../lib/osk';
  let { name, onpick, onok, oncancel }:
    { name: string; onpick: (itemId: string) => void; onok: () => void; oncancel: () => void } = $props();
  // the search starts from the line's name and is the user's from then on (the picker is built for one line)
  // svelte-ignore state_referenced_locally
  let q = $state(name);
  let hits = $derived($catalogue ? search($catalogue, q, 12).filter((h) => h.kind === 'item') : []);
</script>

<div class="scrim" role="presentation" onclick={oncancel}></div>
<div class="sheet" role="dialog" aria-modal="true">
  <h2>{$t('picker.title', { name })}</h2>
  <input bind:value={q} placeholder={$t('picker.search')} use:osk autocomplete="off" />
  <div class="hits">
    {#each hits as h (h.id)}
      <button class="hit pressable" onclick={() => onpick(h.id)}><Icon name={h.item?.icon ?? h.group.icon} size={34} />{nameOf(h.item!, $lang)}</button>
    {/each}
  </div>
  <div class="row">
    <button class="ok pressable" onclick={onok}>✓ {$t('picker.ok')}</button>
    <button class="cancel pressable" onclick={oncancel}>{$t('picker.cancel')}</button>
  </div>
</div>

<style>
  .scrim { position: fixed; inset: 0; background: rgba(0, 0, 0, .35); z-index: 35; }
  .sheet {
    position: fixed; left: 50%; top: calc(24px + env(safe-area-inset-top)); transform: translateX(-50%); z-index: 36; width: min(720px, calc(100vw - 24px));
    background: var(--cream); border: var(--outline-thick) solid var(--ink); border-radius: var(--r-lg); box-shadow: var(--shadow);
    padding: 18px; display: flex; flex-direction: column; gap: 12px; max-height: calc(100vh - 48px);
    max-height: calc(100dvh - 48px - env(safe-area-inset-top) - env(safe-area-inset-bottom));   /* where dvh exists */
  }
  :global(:root.kiosk) .sheet { max-height: 300px; top: 10px; }
  h2 { font-size: 22px; }
  input { height: var(--touch); border: var(--outline) solid var(--ink); border-radius: var(--r); padding: 0 16px; font: inherit; font-weight: 700; font-size: 19px; }
  .hits { display: flex; flex-wrap: wrap; gap: 8px; overflow-y: auto; min-height: 0; }
  .hit { min-height: var(--touch); display: flex; align-items: center; gap: 8px; padding: 0 14px 0 8px; border-radius: 999px;
         border: var(--outline) solid var(--ink); background: var(--paper); font-weight: 800; font-size: 16px; }
  .row { display: flex; gap: 10px; }
  .ok { flex: 1; min-height: var(--touch); border-radius: var(--r); border: var(--outline) solid var(--ink); background: var(--herb); color: var(--ink); font-weight: 900; font-size: 16px; }
  .cancel { min-height: var(--touch); padding: 0 20px; border-radius: var(--r); border: var(--outline) solid var(--ink); background: var(--paper); font-weight: 800; }
</style>
