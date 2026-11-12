<script lang="ts">
  import { t } from '../lib/i18n';
  let { status, onclick }: { status: 'ok' | 'yours' | 'swap' | 'check' | 'unknown'; onclick?: () => void } = $props();
</script>

{#if onclick}
  <button class="chip {status} pressable" {onclick}>{$t(`chip.${status === 'ok' ? 'ok' : status}`)}</button>
{:else}
  <span class="chip {status}">{$t(`chip.${status === 'ok' ? 'ok' : status}`)}</span>
{/if}

<style>
  .chip { flex: none; font-weight: 900; font-size: 12.5px; border: 2px solid var(--ink); border-radius: 999px; padding: 2px 9px;
          white-space: nowrap; line-height: 1.3; }
  button.chip { min-height: 40px; min-width: 52px; font-size: 14px; }
  .ok, .yours { background: transparent; border-color: #9BCF9E; color: #2E7D32; }   /* the quiet, normal case */
  .swap { background: var(--teal); color: var(--ink); }
  .check { background: var(--butter); }
  .unknown { background: var(--paper); border-style: dashed; font-size: 15px; }
</style>
