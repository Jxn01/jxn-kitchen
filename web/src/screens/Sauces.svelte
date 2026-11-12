<script lang="ts">
  // The sideboard: the user's sauces as vessels on the shelves of a sideboard — each the
  // family's vessel (a jug, a sauceboat, a bowl, a bottle, a jar), filled with the sauce's colour, its name on a tag,
  // the family under it, how many days it keeps, the verdict's colour on a dot, a ribbon on the classics. Family chips
  // filter it. The vessels are reused by place (keyed by index): a chip or a letter typed in the search changes what
  // they show, it builds none: every sauce has its own cell, and a chip or the search only shows, hides and orders them.
  import { onMount } from 'svelte';
  import PageHeader from '../components/PageHeader.svelte';
  import Icon from '../components/Icon.svelte';
  import MascotNote from '../components/MascotNote.svelte';
  import Vessel from '../components/sauces/Vessel.svelte';
  import { byChip, loadSauces, loadShelves, sauceList, shelves, sortSauces } from '../lib/sauces';
  import { WORD_COLOR } from '../lib/engine';
  import { fold } from '../lib/search';
  import { color, P } from '../lib/palette';
  import { lang, t } from '../lib/i18n';
  import { go } from '../lib/router';
  import { osk } from '../lib/osk';

  let q = $state('');
  let sort = $state<'new' | 'az'>('new');
  let chip = $state<string | null>(null);
  onMount(() => { loadSauces(); if (!$shelves) loadShelves(); });
  let shown = $derived.by(() => {
    const f = fold(q.trim());
    const found = $sauceList.filter((s) => !f || fold(s.names[$lang]).includes(f) || s.tags.some((x) => fold(x).includes(f)));
    return sortSauces(byChip(found, chip), sort, $lang);
  });
  // each sauce keeps its own cell, built once (keyed by id); a chip, a letter or the sort only says which cells show and
  // in what order (CSS `order`) — refilling a pool of cells with other sauces re-ran every vessel, tag and pill: 78 ms of
  // script when a chip went back to All
  let place = $derived(new Map(shown.map((s, i) => [s.id, i])));
</script>

<div class="screen">
  <PageHeader title={$t('sauces.title')} sub={$t('sauces.sub', { n: $sauceList.length })} icon="sauces" color={P.teal} back={() => go('/')}>
    <input class="search" type="search" bind:value={q} placeholder={$t('sauces.search')} use:osk autocomplete="off" />
    <button class="hbtn pressable" onclick={() => (sort = sort === 'new' ? 'az' : 'new')}>{$t(sort === 'new' ? 'sauces.sort.recent' : 'sauces.sort.name')}</button>
    <button class="hbtn new pressable" aria-label={$t('sauces.new')} onclick={() => go('/sauces/new')}><Icon name="plus" size={24} /><span class="lbl">{$t('sauces.new')}</span></button>
  </PageHeader>
  <div class="chips" role="tablist">
    <button class="chip pressable" class:on={chip === null} role="tab" aria-selected={chip === null} onclick={() => (chip = null)}>{$t('sauces.all')}</button>
    {#each $shelves?.chips ?? [] as c (c.id)}
      <button class="chip pressable" class:on={chip === c.id} role="tab" aria-selected={chip === c.id} onclick={() => (chip = c.id)}>{c[$lang]}</button>
    {/each}
  </div>
  <div class="board">
    <div class="vessels stagger">
      <button class="cell pressable" style:order="-1" onclick={() => go('/sauces/new')}>
        <Vessel empty size={104} />
        <span class="tag new">{$t('sauces.new')}</span>
      </button>
      {#each $sauceList as s (s.id)}
        <button class="cell pressable" class:vacant={!place.has(s.id)} disabled={!place.has(s.id)} style:order={place.get(s.id) ?? 0}
                onclick={() => go(`/sauces/${s.id}`)} aria-label={s.names[$lang]}>
          <span class="pot">
            <Vessel vessel={s?.vessel ?? 'jug'} fill={s?.fill} size={104} ribbon={s?.origin === 'seed' ? $t('sauces.classic') : ''} />
            <span class="dot" class:gone={!s?.word} style:background={s?.word ? color(WORD_COLOR[s.word]) : 'transparent'}></span>
          </span>
          <span class="tag">{s?.names[$lang] ?? ''}</span>
          <span class="meta">
            <!-- the family, unless the sauce is named after it (a classic: Tzatziki in the Tzatziki family) -->
            <span class="fam" class:gone={!s || (!!s.family && s.family[$lang] === s.names[$lang])}>{s?.family ? s.family[$lang] : $t('sauce.family.none')}</span>
            <span class="pills">
              <span class="keeps" class:gone={!s?.keeps}>{s?.keeps ? $t('sauces.keeps', { n: s.keeps.days }) : ''}</span>
              <span class="gf" class:gone={!s || s.gluten.state === 'gf'}>{$t(!s || s.gluten.state === 'gf' ? 'chip.ok' : s.gluten.state === 'swaps' ? 'chip.swap' : s.gluten.state === 'check' ? 'chip.check' : 'chip.unknown')}</span>
              <b class="score" class:gone={s?.score == null}>{s?.score ?? ''}</b>
            </span>
          </span>
        </button>
      {/each}
    </div>
    <!-- only when there are no sauces at all: a chip with none in it shows just the empty vessel (a mascot built on a tap) -->
    {#if !$sauceList.length}
      <MascotNote act="shrug" text={$t('sauces.empty')} />
    {/if}
  </div>
</div>

<style>
  .screen { height: 100%; display: flex; flex-direction: column; }
  .search { height: var(--touch); width: 230px; border: var(--outline) solid var(--ink); border-radius: 999px; padding: 0 18px; font: inherit; font-weight: 700; font-size: 16px; background: var(--paper); }
  .hbtn { min-height: var(--touch); min-width: var(--touch); display: flex; align-items: center; gap: 6px; padding: 0 14px; border-radius: 999px;
          border: var(--outline) solid var(--ink); background: var(--paper); font-weight: 800; font-size: 15px; white-space: nowrap; justify-content: center; }
  .hbtn.new { background: var(--herb); color: var(--ink); }
  .chips { flex: none; display: flex; gap: 6px; overflow-x: auto; scrollbar-width: none; padding: 8px 18px 0; }
  .chip { flex: none; min-height: var(--touch); min-width: var(--touch); padding: 0 14px; border: var(--outline) solid var(--ink); border-radius: 999px;
          background: var(--paper); font-weight: 800; font-size: 14px; white-space: nowrap; }
  .chip.on { background: var(--ink); color: #fff; }
  .board { flex: 1; min-height: 0; overflow-y: auto; padding: 6px 18px 90px; }
  /* the sideboard: a painted top and its edge under every 232 px row, drawn by the grid's own background so they share
     its origin — the vessels stand on them (a static background, never redrawn) */
  .vessels { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); grid-auto-rows: 232px; min-width: 0;
             background: linear-gradient(to bottom, transparent 0 119px, #3E8E86 119px 131px, #2A6A63 131px 137px, transparent 137px) 0 0 / 100% 232px repeat-y; }
  .cell { display: flex; flex-direction: column; align-items: center; justify-content: flex-start; gap: 3px; padding: 22px 4px 0; background: none; border: 0;
          min-height: var(--touch); min-width: 0; color: var(--ink); }
  .pot { position: relative; display: block; height: 108px; }
  .dot { position: absolute; right: -4px; top: 2px; width: 18px; height: 18px; border-radius: 50%; border: 2.5px solid var(--ink); }
  .tag { margin-top: 18px; max-width: 100%; background: var(--cream); border: 2px solid var(--ink); border-radius: 4px; padding: 1px 8px; transform: rotate(-1.5deg);
         font-family: var(--font-display); font-size: 15px; line-height: 1.1; text-align: center; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2;
         line-clamp: 2; -webkit-box-orient: vertical; box-shadow: 1px 2px 0 rgba(0, 0, 0, .18); }
  .tag.new { margin-top: 18px; }
  .meta { display: flex; flex-direction: column; align-items: center; gap: 3px; max-width: 100%; }
  .fam { font-weight: 800; font-size: 12px; opacity: .75; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
  .pills { display: flex; gap: 4px; align-items: center; flex-wrap: wrap; justify-content: center; }   /* wraps between pills, never inside one */
  .pills > * { white-space: nowrap; }
  .keeps { font-weight: 900; font-size: 11px; border: 2px solid var(--ink); border-radius: 999px; padding: 0 6px; background: #CFE8F2; }
  .gf { font-weight: 900; font-size: 11px; border: 2px solid var(--ink); border-radius: 999px; padding: 0 6px; background: var(--butter); }
  .score { background: var(--ink); color: #fff; border-radius: 999px; padding: 0 7px; font-size: 12px; }
  .gone, .cell.vacant { display: none !important; }
  @media (max-aspect-ratio: 1/1) {
    .search { display: none; } .lbl { display: none; }
    .vessels { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  }
</style>
