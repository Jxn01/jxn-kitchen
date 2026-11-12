<script lang="ts">
  import { haveCount } from '../lib/pantry';
  import { t } from '../lib/i18n';
  import { go } from '../lib/router';
</script>
<button class="have pressable" onclick={() => go('/pantry-have')}>✓ <span class="lbl">{$t('pantry.have')}</span> <b>{$haveCount}</b></button>
<style>
  .have { min-height: var(--touch); padding: 0 16px; border-radius: 999px; border: var(--outline) solid var(--ink); background: var(--ink);
          color: #fff; font-weight: 800; font-size: 16px; white-space: nowrap; display: flex; align-items: center; gap: 8px; }
  b { background: var(--herb); color: var(--ink); border-radius: 999px; padding: 2px 10px; }   /* not the inherited white */
  @media (max-aspect-ratio: 1/1) { .lbl { display: none; } }
</style>
