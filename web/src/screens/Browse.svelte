<script lang="ts">
  // Browse: recipe-site shortcuts + a search box. On the kiosk a tap takes Chrome to the real site and
  // the kiosk agent lays our Home · Back · Save bar and keyboard over it. Elsewhere sites open in a new tab and the
  // import box takes links.
  import { onMount } from 'svelte';
  import PageHeader from '../components/PageHeader.svelte';
  import Icon from '../components/Icon.svelte';
  import { settings } from '../lib/settings';
  import { siteList, searchUrl, type Site } from '../lib/sites';
  import { isKiosk } from '../lib/kiosk';
  import { importLink } from '../lib/importflow';
  import { P } from '../lib/palette';
  import { textOn } from '../lib/color';
  import { t } from '../lib/i18n';
  import { go } from '../lib/router';
  import { osk } from '../lib/osk';

  let q = $state('');
  let link = $state('');
  let busy = $state(false);
  let overlayOk = $state<boolean | null>(null);   // the kiosk agent's overlay: never send the kiosk somewhere it can't come back from
  let sites = $derived(siteList($settings.browse_sites, $settings.browse_custom));
  let searchable = $derived(sites.filter((s) => s.search));

  onMount(async () => {
    if (!$isKiosk) return;
    try { overlayOk = (await (await fetch('/api/kiosk/health', { cache: 'no-store' })).json()).overlay_ok ?? null; } catch { overlayOk = null; }
  });
  let blocked = $derived($isKiosk && overlayOk === false);

  function open(url: string) {
    if ($isKiosk) location.href = url;                      // the agent's overlay takes over on the site
    else window.open(url, '_blank', 'noopener');
  }
  function search(site: Site) { const u = searchUrl(site, q); if (u) open(u); }
  async function bringIn() { if (!link.trim()) return; busy = true; if (await importLink(link)) link = ''; busy = false; }
</script>

<div class="screen">
  <PageHeader title={$t('browse.title')} sub={$t('browse.sub')} icon="browse" color={P.sky} back={() => go('/')} />
  <div class="body">
    {#if blocked}<p class="warn">{$t('browse.unavailable')}</p>{/if}
    <form class="search" onsubmit={(e) => { e.preventDefault(); if (searchable[0]) search(searchable[0]); }}>
      <input bind:value={q} placeholder={$t('browse.search')} use:osk autocomplete="off" disabled={blocked} />
    </form>
    {#if q.trim()}
      <div class="chips">
        {#each searchable as s (s.id)}
          <button class="chip pressable" style:--c={s.color} style:color={textOn(s.color)} onclick={() => search(s)} disabled={blocked}>{$t('browse.search.on', { site: s.name })}</button>
        {/each}
      </div>
    {/if}
    <div class="grid">
      {#each sites as s (s.id)}
        <button class="site pressable" style:--c={s.color} style:color={textOn(s.color)} onclick={() => open(s.url)} disabled={blocked}>
          <span class="plate"><Icon name="browse" size={40} /></span>
          <span class="name">{s.name}</span>
          <span class="host">{new URL(s.url).hostname.replace(/^www\./, '')}{#if !$isKiosk}{' · '}{$t('browse.newtab')}{/if}</span>
        </button>
      {/each}
    </div>
    {#if !$isKiosk}
      <form class="import" onsubmit={(e) => { e.preventDefault(); bringIn(); }}>
        <input bind:value={link} placeholder={$t('recipes.import.ph')} inputmode="url" autocomplete="off" />
        <button class="pressable" disabled={busy || !link.trim()}>{busy ? $t('recipes.import.busy') : $t('browse.import')}</button>
      </form>
    {/if}
  </div>
</div>

<style>
  .screen { height: 100%; display: flex; flex-direction: column; }
  .body { flex: 1; min-height: 0; overflow-y: auto; display: flex; flex-direction: column; gap: 14px; padding: 16px 20px calc(var(--kb-h) + 10px); }
  .warn { background: var(--butter); border: var(--outline) solid var(--ink); border-radius: var(--r); padding: 12px 16px; font-weight: 800; margin: 0; }
  .search input, .import input { width: 100%; height: var(--touch); border: var(--outline) solid var(--ink); border-radius: 999px; padding: 0 22px;
                                 font: inherit; font-weight: 700; font-size: 19px; background: var(--paper); }
  .chips { display: flex; gap: 10px; flex-wrap: wrap; }
  .chip { min-height: var(--touch); padding: 0 20px; border-radius: 999px; border: var(--outline) solid var(--ink); background: var(--c); font-weight: 900; font-size: 16px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; }
  .site { min-height: 150px; display: flex; flex-direction: column; align-items: flex-start; justify-content: space-between; gap: 6px; padding: 14px;
          background: var(--c); border: var(--outline) solid var(--ink); border-radius: var(--r-lg); box-shadow: var(--shadow); text-align: left; }
  .plate { width: 64px; height: 64px; border-radius: 50%; background: var(--cream); border: var(--outline) solid var(--ink); display: grid; place-items: center; }
  .name { font-family: var(--font-display); font-size: 26px; line-height: 1.05; }
  .host { font-weight: 700; font-size: 13.5px; opacity: .85; }
  .site:disabled, .chip:disabled { opacity: .45; }
  .import { display: flex; gap: 10px; }
  .import button { flex: none; min-height: var(--touch); padding: 0 20px; border-radius: 999px; border: var(--outline) solid var(--ink); background: var(--herb); color: var(--ink); font-weight: 900; }
  /* minmax(0, 1fr): with plain 1fr a long site name ("Street Kitchen" at 26 px) set the column's minimum and pushed the
     second column off a phone screen */
  @media (max-aspect-ratio: 1/1) {
    .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; } .import { flex-direction: column; }
    .body { padding: 12px 12px 16px; } .site { min-height: 128px; padding: 12px; } .plate { width: 48px; height: 48px; }
    .name { font-size: 19px; overflow-wrap: break-word; } .search input, .import input { font-size: 17px; padding: 0 18px; }
  }
</style>
