<script lang="ts">
  import MascotNote from '../components/MascotNote.svelte';
  // One know-how section: its pages on the left, the chosen page on the right (illustration, then the text).
  import { onMount } from 'svelte';
  import PageHeader from '../components/PageHeader.svelte';
  import Doneness from '../components/illus/Doneness.svelte';
  import Sugar from '../components/illus/Sugar.svelte';
  import Smoke from '../components/illus/Smoke.svelte';
  import Oven from '../components/illus/Oven.svelte';
  import Cuts from '../components/illus/Cuts.svelte';
  import Blend from '../components/illus/Blend.svelte';
  import Balance from '../components/illus/Balance.svelte';
  import Chart from '../components/illus/Chart.svelte';
  import Onion from '../components/illus/Onion.svelte';
  import Angle from '../components/illus/Angle.svelte';
  import CutSizes from '../components/illus/CutSizes.svelte';
  import Press from '../components/illus/Press.svelte';
  import Moka from '../components/illus/Moka.svelte';
  import EggTimer from '../components/illus/EggTimer.svelte';
  import EggFloat from '../components/illus/EggFloat.svelte';
  import Fridge from '../components/illus/Fridge.svelte';
  import { knowhow, loadKnowhow } from '../lib/knowhow';
  import { renderMd } from '../lib/md';
  import { color } from '../lib/palette';
  import { lang, t } from '../lib/i18n';
  import { go } from '../lib/router';
  import Icon from '../components/Icon.svelte';

  let { sid, pid = null }: { sid: string; pid?: string | null } = $props();
  onMount(() => { if (!$knowhow) loadKnowhow(); });
  let section = $derived($knowhow?.find((s) => s.id === sid) ?? null);
  let page = $derived(section ? (section.pages.find((p) => p.id === pid) ?? section.pages[0]) : null);
  let scroller: HTMLElement | undefined = $state();
  $effect(() => { void page; scroller?.scrollTo({ top: 0 }); });
</script>

{#if section && page}
  <div class="screen">
    <PageHeader title={section[$lang].title} sub={section[$lang].sub} icon={section.icon} color={color(section.color)} back={() => go('/knowhow')} />
    <div class="body">
      <nav class="rail">
        {#each section.pages as p (p.id)}
          <button class="pg pressable" class:on={p.id === page.id} style:--c={color(section.color)} onclick={() => go(`/knowhow/${sid}/${p.id}`)}>{p[$lang].title}</button>
        {/each}
        <!-- a sticker of the section in the rail's empty space (decoration: static, a single wiggle as it lands) -->
        <div class="sticker" aria-hidden="true" style:--c={color(section.color)}>
          <svg class="doodle" viewBox="0 0 160 120"><path d="M18,30 l6,-10 l6,10 l-6,10 z M136,22 l4,-7 l4,7 l-4,7 z M140,92 c8,-6 8,-14 0,-20 M14,88 q10,-10 20,0 t20,0" /><circle cx="122" cy="104" r="4" /><circle cx="30" cy="62" r="3" /></svg>
          <span class="plate"><Icon name={section.icon} size={64} /></span>
        </div>
      </nav>
      <article class="page" bind:this={scroller}>
        <h2>{page[$lang].title}</h2>
        {#if page.open}
          <button class="engine pressable" onclick={() => go(page.open === 'spices' ? '/spices/new' : '/sauces/new')}>
            <Icon name={page.open} size={36} />{$t(`knowhow.open.${page.open}`)}</button>
        {/if}
        <!-- keyed by page: the next page's infographic must mount FRESH — a reused component kept the old page's selection
             (the 5th band of one thermometer read on a 4-band one threw), and every page replays its entrance -->
        {#key `${sid}/${page.id}`}
        {#if page.illustration}
          <div class="illus">
            {#if page.illustration === 'doneness'}<Doneness lang={$lang} />
            {:else if page.illustration === 'sugar'}<Sugar lang={$lang} />
            {:else if page.illustration === 'smoke'}<Smoke lang={$lang} />
            {:else if page.illustration === 'oven'}<Oven lang={$lang} />
            {:else if page.illustration === 'cuts'}<Cuts lang={$lang} animal={page.id} />
            {:else if page.illustration === 'blend'}<Blend lang={$lang} />
            {:else if page.illustration === 'balance'}<Balance lang={$lang} />
            {:else if page.illustration === 'onion'}<Onion lang={$lang} />
            {:else if page.illustration === 'angle'}<Angle lang={$lang} />
            {:else if page.illustration === 'cutsizes'}<CutSizes lang={$lang} />
            {:else if page.illustration === 'press'}<Press lang={$lang} />
            {:else if page.illustration === 'moka'}<Moka lang={$lang} />
            {:else if page.illustration === 'eggtimer'}<EggTimer lang={$lang} />
            {:else if page.illustration === 'eggfloat'}<EggFloat lang={$lang} />
            {:else if page.illustration === 'fridge'}<Fridge lang={$lang} />{/if}
          </div>
        {:else if page.chart}
          <div class="illus"><Chart chart={page.chart} lang={$lang} /></div>
        {/if}
        {/key}
        <div class="md">{@html renderMd(page[$lang].body)}</div>
      </article>
    </div>
  </div>
{:else if $knowhow}
  <MascotNote act="shrug" text={$t('knowhow.none')} />
{/if}

<style>
  .engine { display: flex; align-items: center; gap: 10px; min-height: var(--touch); padding: 0 20px 0 12px; margin: 4px 0 12px;
            border: var(--outline) solid var(--ink); border-radius: 999px; background: var(--tangerine); color: var(--ink);
            font-weight: 900; font-size: 16px; box-shadow: var(--shadow-sm); }
  .screen { height: 100%; display: flex; flex-direction: column; }
  /* minmax(0, 1fr), not 1fr: a grid track never shrinks below its content's min width, so a wide table stretched the whole
     article past the screen (phone, 2026-10-11) — now the table scrolls inside its own box */
  .body { flex: 1; min-height: 0; display: grid; grid-template-columns: 250px minmax(0, 1fr); gap: 16px; padding: 14px 20px 16px; }
  .rail { min-height: 0; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; }
  .sticker { position: relative; margin-top: auto; align-self: center; width: 160px; height: 130px; flex: none; display: grid; place-items: center; }
  .sticker .doodle { position: absolute; inset: 0; width: 160px; height: 120px; fill: none; stroke: var(--ink); stroke-width: 3; stroke-linecap: round; stroke-linejoin: round; opacity: .35; }
  .sticker .plate { width: 100px; height: 100px; border-radius: 50%; background: var(--c); border: var(--outline) solid var(--ink); box-shadow: 0 5px 0 var(--ink);
                    display: grid; place-items: center; transform: rotate(-8deg); animation: stick .7s cubic-bezier(.34, 1.56, .64, 1) .3s both; }
  @keyframes stick { 0% { opacity: 0; transform: scale(.6) rotate(-30deg); } 60% { opacity: 1; transform: scale(1.06) rotate(4deg); } 100% { transform: rotate(-8deg); } }
  .pg { min-height: var(--touch); padding: 8px 14px; text-align: left; border-radius: var(--r); border: var(--outline) solid var(--ink); background: var(--paper);
        font-weight: 800; font-size: 15px; line-height: 1.2; }
  .pg.on { background: var(--c); color: var(--ink); }
  .page { min-height: 0; min-width: 0; overflow-y: auto; background: var(--paper); border: var(--outline) solid var(--ink); border-radius: var(--r); padding: 16px 22px 60px; }
  h2 { font-size: 28px; margin-bottom: 10px; }
  .illus { margin: 6px 0 18px; padding: 14px; background: var(--cream); border: var(--outline) solid var(--ink); border-radius: var(--r); }
  .md { font-size: 17px; line-height: 1.5; }
  .md :global(h3) { font-size: 21px; margin: 18px 0 6px; }
  .md :global(p) { margin: 0 0 12px; }
  .md :global(ul), .md :global(ol) { margin: 0 0 12px; padding-left: 24px; }
  .md :global(li) { margin-bottom: 6px; }
  .md :global(.tbl) { overflow-x: auto; margin: 4px 0 14px; border: var(--outline) solid var(--ink); border-radius: var(--r-sm); }
  .md :global(table) { border-collapse: collapse; width: 100%; font-size: 15px; }
  .md :global(th) { background: var(--ink); color: #fff; text-align: left; padding: 8px 10px; font-weight: 800; }
  .md :global(td) { padding: 8px 10px; border-top: 2px solid #E7DCCB; vertical-align: top; }
  .md :global(tr:nth-child(even) td) { background: var(--cream); }
  .md :global(.tip) { position: relative; margin: 14px 0; padding: 12px 16px 12px 58px; background: var(--teal); color: var(--ink); border: var(--outline) solid var(--ink); border-radius: var(--r); font-weight: 700; }
  /* a little light-bulb doodle on every tip (static) */
  .md :global(.tip)::before { content: ''; position: absolute; left: 12px; top: 10px; width: 34px; height: 34px; border-radius: 50%; background: var(--paper) no-repeat center / 24px 24px;
                              border: 2.5px solid var(--ink); background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%231F1A17' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M9 18h6M10 21h4M12 3a6 6 0 0 0-4 10.5c.8.8 1 1.6 1 2.5h6c0-.9.2-1.7 1-2.5A6 6 0 0 0 12 3z' fill='%23FFD23F'/%3E%3C/svg%3E"); }
  @media (max-aspect-ratio: 1/1) {
    .body { grid-template-columns: minmax(0, 1fr); grid-auto-rows: max-content; overflow-y: auto; }
    .rail { flex-direction: row; overflow-x: auto; } .pg { flex: none; } .sticker { display: none; }
    .page { overflow: visible; padding: 14px 14px 40px; }
  }
</style>
