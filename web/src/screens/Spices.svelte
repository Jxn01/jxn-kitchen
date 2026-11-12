<script lang="ts">
  // The shelf (spec 2026-10-19 §6.2): the owner's blends as jars on wooden planks — each jar the colour of what is in
  // it, its name on a hand-lettered label, heat pips, the verdict's colour on the lid, a ribbon on the classics. The
  // jars are reused by place (keyed by index): a letter typed in the search changes what they show, it builds none.
  import { onMount } from 'svelte';
  import PageHeader from '../components/PageHeader.svelte';
  import Icon from '../components/Icon.svelte';
  import MascotNote from '../components/MascotNote.svelte';
  import SpiceJar from '../components/spices/SpiceJar.svelte';
  import { blendList, loadBlends, loadRack, rack, WORD_COLOR } from '../lib/spices';
  import { fold } from '../lib/search';
  import { color, P } from '../lib/palette';
  import { lang, t } from '../lib/i18n';
  import { go } from '../lib/router';
  import { osk } from '../lib/osk';

  let q = $state('');
  let sort = $state<'recent' | 'name'>('recent');
  onMount(() => { loadBlends(); if (!$rack) loadRack(); });
  const HEAT: Record<string, number> = { mild: 0, warm: 1, hot: 2, fiery: 3 };
  let shown = $derived.by(() => {
    const f = fold(q.trim());
    const list = $blendList.filter((b) => !f || fold(b.names[$lang]).includes(f) || b.tags.some((x) => fold(x).includes(f)));
    return sort === 'name' ? [...list].sort((a, b) => a.names[$lang].localeCompare(b.names[$lang], $lang)) : list;
  });
  // each blend keeps its own jar, built once (keyed by id); the search and the sort only say which jars show and in what
  // order (CSS `order`) — the sideboard's lesson: refilling cells with other content re-ran every one of them
  let place = $derived(new Map(shown.map((b, i) => [b.id, i])));
</script>

<div class="screen">
  <PageHeader title={$t('spices.title')} sub={$t('spices.sub', { n: $blendList.length })} icon="spices" color={P.tangerine} back={() => go('/')}>
    <input class="search" type="search" bind:value={q} placeholder={$t('spices.search')} use:osk autocomplete="off" />
    <button class="hbtn pressable" onclick={() => (sort = sort === 'recent' ? 'name' : 'recent')}>{$t(`spices.sort.${sort}`)}</button>
    <button class="hbtn new pressable" aria-label={$t('spices.new')} onclick={() => go('/spices/new')}><Icon name="plus" size={24} /><span class="lbl">{$t('spices.new')}</span></button>
  </PageHeader>
  <div class="shelf">
    <div class="jars stagger">
      <button class="cell pressable" style:order="-1" onclick={() => go('/spices/new')}>
        <SpiceJar empty size={112} />
        <span class="cap new">{$t('spices.new')}</span>
      </button>
      {#each $blendList as b (b.id)}
        <button class="cell pressable" class:vacant={!place.has(b.id)} disabled={!place.has(b.id)} style:order={place.get(b.id) ?? 0}
                onclick={() => go(`/spices/${b.id}`)}>
          <SpiceJar fill={b?.jar_fill} size={112} label={b?.names[$lang] ?? ''} heat={b ? HEAT[b.heat] ?? 0 : 0}
                    dot={b?.word ? color(WORD_COLOR[b.word]) : null} ribbon={b?.origin === 'seed' ? $t('spices.classic') : ''} />
          <span class="cap"><span class="gf" class:gone={b?.gluten.status !== 'check'}>{$t('chip.check')}</span>
            <b class:gone={b?.score == null}>{b?.score ?? ''}</b></span>
        </button>
      {/each}
    </div>
    {#if !$blendList.length}
      <MascotNote act="shrug" text={$t('spices.empty')} />
    {/if}
  </div>
</div>

<style>
  .screen { height: 100%; display: flex; flex-direction: column; }
  .search { height: var(--touch); width: 230px; border: var(--outline) solid var(--ink); border-radius: 999px; padding: 0 18px; font: inherit; font-weight: 700; font-size: 16px; background: var(--paper); }
  .hbtn { min-height: var(--touch); min-width: var(--touch); display: flex; align-items: center; gap: 6px; padding: 0 14px; border-radius: 999px;
          border: var(--outline) solid var(--ink); background: var(--paper); font-weight: 800; font-size: 15px; white-space: nowrap; justify-content: center; }
  .hbtn.new { background: var(--herb); color: var(--ink); }
  .shelf { flex: 1; min-height: 0; overflow-y: auto; padding: 8px 18px 90px; }
  /* the planks: one under every 226 px row of jars, drawn by the grid's own background so they share its origin —
     the jars stand on them (a static background, never redrawn) */
  .jars { display: grid; grid-template-columns: repeat(auto-fill, minmax(148px, 1fr)); grid-auto-rows: 226px; min-width: 0;
          background: linear-gradient(to bottom, transparent 0 196px, #C08A55 196px 210px, #8C5A2E 210px 215px, transparent 215px) 0 0 / 100% 226px repeat-y; }
  .cell { display: flex; flex-direction: column; align-items: center; justify-content: flex-end; gap: 2px; padding: 0 0 30px; background: none; border: 0; min-height: var(--touch); }
  .cap { height: 0; display: flex; gap: 6px; align-items: center; font-weight: 900; font-size: 13px; color: var(--cream); position: relative; top: 7px; }
  .cap b { background: var(--ink); color: #fff; border-radius: 999px; padding: 0 7px; font-size: 12px; }
  .cap .gf { background: var(--butter); color: var(--ink); border: 2px solid var(--ink); border-radius: 999px; padding: 0 6px; font-size: 11px; }
  .cell.vacant, .gone { display: none !important; }
  .cap.new { color: var(--ink); background: var(--cream); border: 2px solid var(--ink); border-radius: 999px; padding: 0 8px; height: auto; top: -8px; }
  @media (max-aspect-ratio: 1/1) {
    .search { display: none; } .lbl { display: none; }
    .jars { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  }
</style>
