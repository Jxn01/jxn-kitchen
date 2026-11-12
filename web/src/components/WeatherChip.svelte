<script lang="ts">
  import { onMount } from 'svelte';
  import Icon from './Icon.svelte';
  import { getJSON } from '../lib/api';
  type W = { condition: string | null; temp?: number; unit?: string };
  let w = $state<W>({ condition: null });
  async function refresh() { try { w = await getJSON<W>('/api/weather'); } catch { /* keep last */ } }
  onMount(() => { refresh(); const id = setInterval(refresh, 10 * 60 * 1000); return () => clearInterval(id); });
</script>

{#if w.condition}
  <div class="chip"><span class="ic"><Icon name={w.condition} size={30} /></span>{#if typeof w.temp === 'number'}{Math.round(w.temp)}°{/if}</div>
{/if}

<style>
  .chip {
    display: flex; align-items: center; gap: 6px; height: 48px; padding: 0 16px 0 8px; background: var(--paper);
    border: var(--outline) solid var(--ink); border-radius: 999px; box-shadow: var(--shadow-sm); font-weight: 900; font-size: 19px;
  }
</style>
