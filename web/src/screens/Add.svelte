<script lang="ts">
  import MascotNote from '../components/MascotNote.svelte';
  // The phone's share target (spec §6.3): an iOS Shortcut opens #/add?url=<the page>. One tap saves it — never on
  // its own, so a stray link can't import anything by itself.
  import PageHeader from '../components/PageHeader.svelte';
  import { importLink } from '../lib/importflow';
  import { isWebLink } from '../lib/sites';
  import { P } from '../lib/palette';
  import { t } from '../lib/i18n';
  import { go } from '../lib/router';
  let { url }: { url: string } = $props();
  let busy = $state(false);
  let ok = $derived(isWebLink(url));
  async function save() { busy = true; await importLink(url); busy = false; }
</script>

<div class="screen">
  <PageHeader title={$t('add.title')} icon="recipes" color={P.tomato} back={() => go('/recipes')} />
  <div class="body">
    {#if ok}
      <p class="q">{$t('add.question')}</p>
      <p class="url">{url}</p>
      <button class="go pressable" onclick={save} disabled={busy}>{busy ? $t('add.busy') : $t('add.go')}</button>
      {#if busy}<MascotNote loop="stir" prop="chef" size={200} />{/if}
    {:else}
      <p class="q">{$t('add.none')}</p>
    {/if}
  </div>
</div>

<style>
  .screen { height: 100%; display: flex; flex-direction: column; }
  .body { padding: 24px 20px; display: flex; flex-direction: column; gap: 16px; align-items: flex-start; }
  .q { font-weight: 900; font-size: 22px; margin: 0; }
  .url { word-break: break-all; font-weight: 600; opacity: .75; margin: 0; }
  .go { min-height: 76px; padding: 0 36px; border-radius: var(--r); border: var(--outline-thick) solid var(--ink); background: var(--herb); color: var(--ink);
        font-family: var(--font-display); font-size: 26px; box-shadow: var(--shadow); }
</style>
