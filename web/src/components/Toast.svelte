<script lang="ts">
  import { toast } from '../lib/toast';
  import { t } from '../lib/i18n';
  import { activeInput } from '../lib/osk';
  import { badgeShown } from '../lib/badge';
</script>

{#if $toast}
  {#key $toast.id}
    <div class="toast" class:above-badge={$badgeShown} class:raised={!!$activeInput} class:warn={$toast.tone === 'warn'} role="status">
      <span class="txt">{$toast.text}</span>
      {#if $toast.undo}<button class="pressable" onclick={$toast.undo}>{$t('toast.undo')}</button>{/if}
      {#if $toast.action}<button class="pressable act" onclick={$toast.action.run}>{$toast.action.label}</button>{/if}
    </div>
  {/key}
{/if}

<style>
  .toast {
    position: fixed; left: 50%; bottom: calc(18px + env(safe-area-inset-bottom)); z-index: 45; transform: translateX(-50%);
    display: flex; align-items: center; gap: 10px; max-width: calc(100vw - 32px);
    background: var(--ink); color: #fff; border-radius: 999px; padding: 6px 6px 6px 22px;
    font-weight: 800; font-size: 17px; box-shadow: 0 6px 0 rgba(0, 0, 0, .25);
    animation: rise 260ms var(--ease-pop) both;
  }
  /* clear of the offline badge (bottom 14px, 42px tall: 8+26+8) — before .raised, so the keyboard's lift wins */
  .above-badge { bottom: calc(66px + env(safe-area-inset-bottom)); }
  .raised { bottom: calc(var(--kb-h) + 12px); }
  .warn { background: var(--tomato); }
  .txt { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  button {
    min-height: var(--touch); min-width: var(--touch); padding: 0 18px; border-radius: 999px; border: 0;
    background: var(--butter); color: var(--ink); font-weight: 900; font-size: 16px; white-space: nowrap;
  }
  .act { background: var(--teal); color: var(--ink); }
  @keyframes rise { from { transform: translate(-50%, 140%); } to { transform: translate(-50%, 0); } }
</style>
