<script lang="ts">
  import { outbox } from '../lib/queue';
  import { badgeShown } from '../lib/badge';
  const waiting = outbox.pending;
  import { t } from '../lib/i18n';
  import Icon from './Icon.svelte';
</script>

{#if $badgeShown}
  <div class="badge" role="status"><Icon name="offline" size={26} /> {$t('offline.badge')}{#if $waiting}{' · '}{$t('offline.waiting', { n: $waiting })}{/if}</div>
{/if}

<style>
  .badge {
    position: fixed; left: calc(14px + env(safe-area-inset-left)); bottom: calc(14px + env(safe-area-inset-bottom)); z-index: 50;
    display: flex; align-items: center; gap: 8px;
    background: var(--ink); color: #fff; border-radius: 999px; padding: 8px 16px 8px 10px;
    font-weight: 800; font-size: 15px;
    animation: rise 300ms var(--ease-pop) both;
  }
  @keyframes rise { from { transform: translateY(120%); } to { transform: none; } }
</style>
