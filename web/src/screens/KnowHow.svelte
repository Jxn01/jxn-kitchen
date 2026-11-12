<script lang="ts">
  import MascotNote from '../components/MascotNote.svelte';
  // The know-how library: every section as a tile and a search over every page in both languages.
  import { onMount } from 'svelte';
  import Mascot from '../components/Mascot.svelte';
  import MascotBubble from '../components/MascotBubble.svelte';
  import { TIPS, type Tip } from '../lib/tips';
  import PageHeader from '../components/PageHeader.svelte';
  import Icon from '../components/Icon.svelte';
  import { knowhow, loadKnowhow, searchKnowhow } from '../lib/knowhow';
  import { color } from '../lib/palette';
  import { textOn } from '../lib/color';
  import { P } from '../lib/palette';
  import { lang, t } from '../lib/i18n';
  import { go } from '../lib/router';
  import { osk } from '../lib/osk';
  import { fit } from '../lib/fit';

  let q = $state('');
  // the last cell of the grid: the mascot in its toque; tap it for a tip
  let tip = $state<Tip | null>(null);
  let tipTimer: ReturnType<typeof setTimeout> | null = null;
  function tapped() {
    tip = null;
    const next = TIPS[Math.floor(Math.random() * TIPS.length)];
    setTimeout(() => (tip = next), 600);
    if (tipTimer) clearTimeout(tipTimer);
    tipTimer = setTimeout(() => (tip = null), 9000);
  }
  onMount(() => { if (!$knowhow) loadKnowhow(); });
  let hits = $derived($knowhow && q.trim() ? searchKnowhow($knowhow, q, $lang) : []);
</script>

<div class="screen">
  <PageHeader title={$t('knowhow.title')} sub={$t('knowhow.sub')} icon="knowhow" color={P.plum} back={() => go('/')}>
    <input class="search hsearch" type="search" bind:value={q} placeholder={$t('knowhow.search')} use:osk autocomplete="off" />
  </PageHeader>
  <div class="body">
    <!-- phones: the search gets a row of its own (in the header it had room for "Search the kn") -->
    <input class="search bsearch" type="search" bind:value={q} placeholder={$t('knowhow.search')} autocomplete="off" />
    {#if !$knowhow}
      <p class="empty">…</p>
    {:else if q.trim()}
      <div class="hits">
        {#each hits as h (h.section.id + h.page.id)}
          <button class="hit pressable" onclick={() => go(`/knowhow/${h.section.id}/${h.page.id}`)}>
            <span class="where" style:--c={color(h.section.color)}>{h.section[$lang].title}</span>
            <b>{h.page[$lang].title}</b>
            <span class="snip">{h.snippet}</span>
          </button>
        {:else}
          <MascotNote act="shrug" text={$t('knowhow.none')} />
        {/each}
      </div>
    {:else}
      <div class="tiles stagger">
        {#each $knowhow as s (s.id)}
          {@const c = color(s.color)}
          <button class="tile pressable" style:--c={c} style:color={textOn(c)} onclick={() => go(`/knowhow/${s.id}`)}>
            <span class="plate"><Icon name={s.icon} size={32} /></span>
            <span class="tt" use:fit={s[$lang].title}>{s[$lang].title}</span>
            <span class="sub">{s[$lang].sub}</span>
          </button>
        {/each}
        <div class="cheff">
          <Mascot size={150} prop="chef" tappable ontap={tapped} label={$t('mascot.label')} />
          {#if tip}<div class="bubble"><MascotBubble {tip} onclose={() => (tip = null)} /></div>{/if}
        </div>
      </div>
    {/if}
  </div>
</div>

<style>
  .cheff { position: relative; display: grid; place-items: end center; min-height: 118px; }
  .bubble { position: absolute; right: 8px; bottom: calc(100% - 26px); z-index: 5; width: max-content; }
  .screen { height: 100%; display: flex; flex-direction: column; }
  .search { height: var(--touch); width: 280px; border: var(--outline) solid var(--ink); border-radius: 999px; padding: 0 18px; font: inherit; font-weight: 700; font-size: 16px; background: var(--paper); }
  .body { flex: 1; min-height: 0; overflow-y: auto; padding: 16px 20px calc(var(--kb-h) + 10px);
          /* a faint scatter of kitchen doodles behind the grid — whisk, spoon, steam, sparkles, a leaf (static, painted once) */
          background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='260' height='220' viewBox='0 0 260 220' fill='none' stroke='%231F1A17' stroke-opacity='.07' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M30 40c10-14 30-14 40 0s-8 40-20 46c-12-6-30-32-20-46zM50 86v40'/%3E%3Cpath d='M150 30c0 10 8 14 8 24s-8 14-8 24M170 30c0 10 8 14 8 24s-8 14-8 24'/%3E%3Cpath d='M210 120l6-12 6 12-6 12zM96 170l4-8 4 8-4 8z'/%3E%3Cpath d='M190 170c18-20 44-14 50 4-18 10-38 10-50-4zM196 172c14 0 26 2 38 4'/%3E%3Cellipse cx='60' cy='176' rx='18' ry='10'/%3E%3Cpath d='M78 176h40'/%3E%3Ccircle cx='130' cy='110' r='3'/%3E%3Ccircle cx='240' cy='60' r='3'/%3E%3C/svg%3E") repeat; }
  /* up to 19 sections + the mascot: 5 × 4 fits one kiosk screen (1024 × 640); titles shrink to fit (use:fit), subs
     keep two lines */
  .tiles { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }
  .tile { min-height: 118px; display: flex; flex-direction: column; align-items: flex-start; gap: 4px; padding: 10px; text-align: left; background: var(--c);
          border: var(--outline) solid var(--ink); border-radius: var(--r-lg); box-shadow: var(--shadow); overflow: hidden; }
  .plate { width: 44px; height: 44px; border-radius: 50%; background: var(--cream); border: var(--outline) solid var(--ink); display: grid; place-items: center; margin-bottom: auto; }
  .tt { display: block; width: 100%; font-family: var(--font-display); font-size: 19px; line-height: 1.05; white-space: nowrap; overflow: hidden; }
  .sub { font-weight: 700; font-size: 11.5px; line-height: 1.22; opacity: .9; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .hits { display: flex; flex-direction: column; gap: 10px; }
  .hit { display: flex; flex-direction: column; align-items: flex-start; gap: 4px; min-height: var(--touch); padding: 12px 16px; text-align: left;
         background: var(--paper); border: var(--outline) solid var(--ink); border-radius: var(--r); font: inherit; }
  .where { font-weight: 900; font-size: 12px; padding: 2px 10px; border-radius: 999px; background: var(--c); color: var(--ink); }
  .hit b { font-size: 18px; }
  .snip { font-size: 14px; opacity: .75; }
  .empty { text-align: center; font-weight: 800; padding: 40px; }
  .bsearch { display: none; }
  @media (max-aspect-ratio: 1/1) { .cheff { display: none; } .tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); } .hsearch { display: none; } .bsearch { display: block; width: 100%; margin-bottom: 14px; } }
</style>
