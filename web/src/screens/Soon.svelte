<script lang="ts">
  import Mascot from '../components/Mascot.svelte';
  import RoundButton from '../components/RoundButton.svelte';
  import { t } from '../lib/i18n';
  import { go } from '../lib/router';
  let { section }: { section: string } = $props();
</script>

<div class="soon">
  <RoundButton icon="back" label={$t('common.home')} onclick={() => go('/')} />
  <div class="card">
    <Mascot act="shrug" size={240} />
    <h1>{$t('soon.title')}</h1>
    <p>{$t('soon.body')}</p>
    <code>{section}</code>
  </div>
</div>

<style>
  .soon { height: 100%; padding: 26px 30px; display: flex; flex-direction: column; gap: 18px; }
  .card {
    flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px;
    background: var(--paper); border: var(--outline) solid var(--ink); border-radius: var(--r-lg); box-shadow: var(--shadow);
    text-align: center; padding: 20px;
  }
  h1 { font-size: 40px; }
  p { font-size: 19px; max-width: 520px; margin: 0; }
  code { font-family: var(--font-body); font-weight: 800; opacity: .5; }
</style>
