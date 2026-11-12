<script lang="ts">
  import { lang, t } from '../lib/i18n';
  import { save } from '../lib/settings';
</script>

<button class="chip pressable" onclick={() => save({ language: $lang === 'en' ? 'hu' : 'en' })} aria-label={$t('a11y.language')}>
  <span class:on={$lang === 'en'}>EN</span><span class="dot">·</span><span class:on={$lang === 'hu'}>HU</span>
</button>

<style>
  .chip {
    height: var(--touch); padding: 0 18px; background: var(--butter); border: var(--outline) solid var(--ink); border-radius: 999px;
    box-shadow: var(--shadow-sm); font-weight: 700; font-size: 17px; display: flex; gap: 6px; align-items: center;
    position: relative;
  }
  span { opacity: .45; } .on { opacity: 1; font-weight: 900; } .dot { opacity: .6; }
</style>
