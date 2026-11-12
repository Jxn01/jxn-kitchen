<script lang="ts">
  // Name a folder: a new one, or a rename. The server judges the name (unique among its siblings, 1–60 characters);
  // `onsave` returns the refusal text to show, or null when it went through and the sheet may close.
  import { MAX_NAME } from '../lib/folders';
  import { t } from '../lib/i18n';
  import { osk } from '../lib/osk';
  let { title, initial = '', onsave, oncancel }:
    { title: string; initial?: string; onsave: (name: string) => Promise<string | null>; oncancel: () => void } = $props();
  // svelte-ignore state_referenced_locally
  let name = $state(initial);
  let error = $state<string | null>(null);
  let busy = $state(false);
  let input: HTMLInputElement | undefined = $state();
  $effect(() => { input?.focus(); input?.select(); });
  async function save(e: Event) {
    e.preventDefault();
    if (!name.trim() || busy) return;
    busy = true;
    error = await onsave(name.trim());
    busy = false;
    if (error) { input?.focus(); input?.select(); }     // refused: the name is selected, ready to be typed over
  }
</script>

<div class="scrim" role="presentation" onclick={oncancel}></div>
<div class="sheet" role="dialog" aria-modal="true" aria-label={title}><form onsubmit={save}>
  <h2>{title}</h2>
  <input bind:this={input} bind:value={name} maxlength={MAX_NAME} placeholder={$t('folders.name.ph')} use:osk autocomplete="off" />
  <p class="err" class:on={!!error} role="alert">{error ?? ''}</p>
  <div class="row">
    <button class="ok pressable" disabled={busy || !name.trim()}>{$t('folders.save')}</button>
    <button type="button" class="cancel pressable" onclick={oncancel}>{$t('folders.cancel')}</button>
  </div>
</form></div>

<style>
  .scrim { position: fixed; inset: 0; background: rgba(0, 0, 0, .35); z-index: 35; }
  .sheet {
    position: fixed; left: 50%; top: calc(24px + env(safe-area-inset-top)); transform: translateX(-50%); z-index: 36; width: min(560px, calc(100vw - 24px));
    background: var(--cream); border: var(--outline-thick) solid var(--ink); border-radius: var(--r-lg); box-shadow: var(--shadow);
    padding: 18px; display: flex; flex-direction: column; gap: 10px;
  }
  /* the kiosk's on-screen keyboard takes the lower half: keep the sheet at the top */
  :global(:root.kiosk) .sheet { top: 10px; }
  form { display: contents; }
  h2 { font-size: 22px; }
  input { height: var(--touch); border: var(--outline) solid var(--ink); border-radius: var(--r); padding: 0 16px; font: inherit; font-weight: 700; font-size: 19px; }
  .err { min-height: 20px; font-weight: 800; font-size: 15px; color: var(--ink); visibility: hidden; }
  .err.on { visibility: visible; }
  .row { display: flex; gap: 10px; }
  .ok { flex: 1; min-height: var(--touch); border-radius: var(--r); border: var(--outline) solid var(--ink); background: var(--herb); color: var(--ink); font-weight: 900; font-size: 16px; }
  .ok:disabled { opacity: .5; }
  .cancel { min-height: var(--touch); padding: 0 20px; border-radius: var(--r); border: var(--outline) solid var(--ink); background: var(--paper); font-weight: 800; }
</style>
