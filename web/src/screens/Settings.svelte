<script lang="ts">
  import { onMount } from 'svelte';
  import RoundButton from '../components/RoundButton.svelte';
  import { settings, save } from '../lib/settings';
  import { t } from '../lib/i18n';
  import { go } from '../lib/router';
  import { getJSON } from '../lib/api';
  import { BUILT_IN, isWebLink } from '../lib/sites';
  import { osk } from '../lib/osk';
  import { showToast } from '../lib/toast';
  let newName = $state(''), newUrl = $state('');
  function toggleSite(id: string) {
    const on = $settings.browse_sites.includes(id);
    // keep the built-in order whatever was switched when
    save({ browse_sites: BUILT_IN.map((s) => s.id).filter((x) => (x === id ? !on : $settings.browse_sites.includes(x))) });
  }
  function addSite() {
    if (!newName.trim() || !isWebLink(newUrl)) { showToast({ text: $t('settings.browse.bad'), tone: 'warn' }); return; }
    save({ browse_custom: [...$settings.browse_custom, { name: newName.trim().slice(0, 40), url: newUrl.trim() }] });
    newName = ''; newUrl = '';
  }
  const removeSite = (i: number) => save({ browse_custom: $settings.browse_custom.filter((_, j) => j !== i) });

  let version = $state('…');
  onMount(async () => { try { version = (await getJSON<{ version: string }>('/api/health')).version; } catch { /* offline */ } });
  const hour = (h: number) => `${String(h).padStart(2, '0')}:00`;
  const wrap = (h: number) => (h + 24) % 24;
  const clamp = (v: number) => Math.min(100, Math.max(5, v));
</script>

<div class="settings">
  <header>
    <RoundButton icon="back" label={$t('common.back')} onclick={() => go('/')} />
    <h1>{$t('settings.title')}</h1>
  </header>
  <div class="grid">
    <section class="card">
      <h2>{$t('settings.language')}</h2>
      <div class="seg">
        <button class:on={$settings.language === 'en'} onclick={() => save({ language: 'en' })}>English</button>
        <button class:on={$settings.language === 'hu'} onclick={() => save({ language: 'hu' })}>Magyar</button>
      </div>
      <h2>{$t('settings.sounds')}</h2>
      <div class="seg">
        <button class:on={$settings.sounds} onclick={() => save({ sounds: true })}>{$t('settings.on')}</button>
        <button class:on={!$settings.sounds} onclick={() => save({ sounds: false })}>{$t('settings.off')}</button>
      </div>
      <h2>{$t('settings.idle')}</h2>
      <div class="seg">
        {#each [1, 2, 5, 10] as n}
          <button class:on={$settings.idle_minutes === n} onclick={() => save({ idle_minutes: n as 1 | 2 | 5 | 10 })}>{$t('settings.idle.min', { n })}</button>
        {/each}
      </div>
    </section>
    <section class="card">
      <h2>{$t('settings.night')}</h2>
      <div class="pair">
        <span>{$t('settings.night.from')}</span>
        <div class="step"><button onclick={() => save({ night_start: wrap($settings.night_start - 1) })}>−</button><b>{hour($settings.night_start)}</b><button onclick={() => save({ night_start: wrap($settings.night_start + 1) })}>+</button></div>
      </div>
      <div class="pair">
        <span>{$t('settings.night.to')}</span>
        <div class="step"><button onclick={() => save({ night_end: wrap($settings.night_end - 1) })}>−</button><b>{hour($settings.night_end)}</b><button onclick={() => save({ night_end: wrap($settings.night_end + 1) })}>+</button></div>
      </div>
      <p class="hint">{$t('settings.night.hint')}</p>
      <div class="pair">
        <span>{$t('settings.brightness.day')}</span>
        <div class="step"><button onclick={() => save({ day_brightness: clamp($settings.day_brightness - 5) })}>−</button><b>{$settings.day_brightness}%</b><button onclick={() => save({ day_brightness: clamp($settings.day_brightness + 5) })}>+</button></div>
      </div>
      <div class="pair">
        <span>{$t('settings.brightness.night')}</span>
        <div class="step"><button onclick={() => save({ night_brightness: clamp($settings.night_brightness - 5) })}>−</button><b>{$settings.night_brightness}%</b><button onclick={() => save({ night_brightness: clamp($settings.night_brightness + 5) })}>+</button></div>
      </div>
    </section>
    <section class="card wide">
      <h2>{$t('settings.browse')}</h2>
      <div class="sites">
        {#each BUILT_IN as s (s.id)}
          <button class="site" class:on={$settings.browse_sites.includes(s.id)} onclick={() => toggleSite(s.id)}>{$settings.browse_sites.includes(s.id) ? '✓ ' : ''}{s.name}</button>
        {/each}
      </div>
      {#if $settings.browse_custom.length}
        <h2>{$t('settings.browse.own')}</h2>
        {#each $settings.browse_custom as c, i}
          <div class="own"><b>{c.name}</b><span>{c.url}</span><button onclick={() => removeSite(i)}>{$t('settings.browse.remove')}</button></div>
        {/each}
      {/if}
      {#if $settings.browse_custom.length < 8}
        <form class="add" onsubmit={(e) => { e.preventDefault(); addSite(); }}>
          <input bind:value={newName} placeholder={$t('settings.browse.name')} use:osk maxlength="40" />
          <input bind:value={newUrl} placeholder={$t('settings.browse.url')} use:osk inputmode="url" />
          <button>{$t('settings.browse.add')}</button>
        </form>
      {/if}
    </section>
  </div>
  <footer>
    <b>{$t('settings.about')}:</b> {$t('settings.about.body', { version, build: __BUILD__ })} · {$t('settings.credits')}
    <button class="lab pressable" onclick={() => go('/lab/mascot')}>{$t('lab.title')} →</button>
  </footer>
</div>

<style>
  .lab { margin-left: 12px; min-height: var(--touch); padding: 0 18px; border-radius: 999px; border: var(--outline) solid var(--ink); background: var(--butter); font-weight: 800; font-size: 15px; }
  .settings { height: 100%; padding: 22px 28px; display: flex; flex-direction: column; gap: 16px; overflow: auto; }
  header { display: flex; align-items: center; gap: 18px; }
  h1 { font-size: 38px; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  .card {
    background: var(--paper); border: var(--outline) solid var(--ink); border-radius: var(--r-lg); box-shadow: var(--shadow);
    padding: 16px 20px; display: flex; flex-direction: column; gap: 10px;
  }
  h2 { font-size: 19px; margin-top: 4px; }
  .seg { display: flex; border: var(--outline) solid var(--ink); border-radius: 14px; overflow: hidden; }
  .seg button { flex: 1; min-height: var(--touch); border: 0; border-left: var(--outline) solid var(--ink); background: var(--cream); font-weight: 800; font-size: 17px; }
  .seg button:first-child { border-left: 0; }
  .seg .on { background: var(--herb); color: var(--ink); }
  .pair { display: flex; align-items: center; justify-content: space-between; font-weight: 800; font-size: 17px; }
  .step { display: flex; align-items: center; gap: 10px; }
  .step button {
    width: var(--touch); height: var(--touch); border-radius: 50%; border: var(--outline) solid var(--ink); background: var(--butter);
    font-size: 30px; font-weight: 900; line-height: 1; box-shadow: var(--shadow-sm);
  }
  .step b { min-width: 74px; text-align: center; font-family: var(--font-display); font-weight: 400; font-size: 24px; }
  .hint { margin: -4px 0 4px; font-size: 14px; opacity: .7; }
  .wide { grid-column: 1 / -1; }
  .sites { display: flex; flex-wrap: wrap; gap: 10px; }
  .site { min-height: var(--touch); padding: 0 20px; border-radius: 999px; border: var(--outline) solid var(--ink); background: var(--cream); font-weight: 800; font-size: 16px; }
  .site.on { background: var(--herb); color: var(--ink); }
  .own { display: flex; align-items: center; gap: 12px; min-height: var(--touch); }
  .own span { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; opacity: .7; }
  .own button, .add button { min-height: var(--touch); padding: 0 18px; border-radius: 999px; border: var(--outline) solid var(--ink); background: var(--paper); font-weight: 800; }
  .add { display: flex; gap: 10px; flex-wrap: wrap; padding-bottom: calc(var(--kb-h) * 0); }
  .add input { flex: 1 1 200px; height: var(--touch); border: var(--outline) solid var(--ink); border-radius: 14px; padding: 0 14px; font: inherit; font-weight: 700; }
  .add button { background: var(--herb); color: var(--ink); }
  footer { font-size: 13px; opacity: .75; }
  @media (max-aspect-ratio: 1/1) { .grid { grid-template-columns: 1fr; } }
</style>
