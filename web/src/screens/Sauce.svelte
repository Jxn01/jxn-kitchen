<script lang="ts">
  import { failKey } from '../lib/api';
  // One sauce (spec 2026-10-19 §6.3): the vessel big; what goes in, with the yield scaler (± 50 ml, the amounts scale)
  // and every line's GF chip; the steps, their durations as timer buttons; Cook it, Riff on it, Edit, Delete; and
  // everything the engine says, read-only, in one scroll.
  import { onMount } from 'svelte';
  import PageHeader from '../components/PageHeader.svelte';
  import GlutenChip from '../components/GlutenChip.svelte';
  import Vessel from '../components/sauces/Vessel.svelte';
  import SauceEvalPanel from '../components/sauces/SauceEvalPanel.svelte';
  import { api, baseYield, lineLabel, loadSauces, loadShelves, MAX_YIELD, MIN_YIELD, nameIndex, SAUCE_SLOTS, sauceList, shelves, YIELD_STEP,
           type Sauce } from '../lib/sauces';
  import { pool } from '../lib/engine';
  import { blendList, loadBlends, loadRack, rack } from '../lib/spices';
  import { stepParts, timerLabel } from '../lib/cook';
  import { fmtTime, timerApi } from '../lib/cooktimers';
  import { badge } from '../lib/recipes';
  import { P } from '../lib/palette';
  import { lang, t } from '../lib/i18n';
  import { go } from '../lib/router';
  import { showToast } from '../lib/toast';
  import { sound } from '../lib/sound';

  let { id }: { id: number } = $props();
  let s = $state<Sauce | null>(null);
  let missing = $state(false);
  let ml = $state<number | null>(null);
  let confirmDelete = $state(false);
  onMount(() => { if (!$shelves) loadShelves(); if (!$rack) loadRack(); loadBlends(); });
  $effect(() => {
    void $sauceList;                                  // an SSE `sauces` (or `blends`) event reloads the list: reload this one too
    api.get(id).then((x) => { s = x; missing = false; }).catch(() => (missing = true));
  });
  let names = $derived(nameIndex($shelves, ($rack?.shelves ?? []).flatMap((sh) => sh.jars), $lang));
  let blends = $derived(Object.fromEntries($blendList.map((b) => [b.id, b.names[$lang]])));
  let base = $derived(s ? baseYield(s) : 250);
  let size = $derived(ml ?? base);
  let factor = $derived(size / base);
  let fills = $derived.by(() => {
    const items = new Map(($shelves?.shelves ?? []).flatMap((sh) => sh.items.map((i) => [i.id, i.fill] as const)));
    const jars = new Map(($rack?.shelves ?? []).flatMap((sh) => sh.jars.map((j) => [j.id, j.fill] as const)));
    return (s?.lines ?? []).map((v) => (v.shelf_id ? items.get(v.shelf_id) : v.spice_id ? jars.get(v.spice_id) : null) ?? '#E8DCC4');
  });
  let gf = $derived(s ? badge(s.gluten) : null);
  let e = $derived(s?.evaluation ? { ...s.evaluation, gluten: { lines: [], verdict: s.gluten } } : null);

  async function startTimer(seconds: number, pos: number) {
    try { await timerApi.start(timerLabel(s!.names[$lang], pos, $lang), seconds); sound.on(); showToast({ text: $t('cook.timer.started', { time: fmtTime(seconds) }) }); }
    catch (e) { showToast({ text: $t(failKey(e)), tone: 'warn' }); }
  }
  async function riff() {
    try { const r = await api.riff(id); loadSauces(); go(`/sauces/${r.id}/edit`); } catch (e) { showToast({ text: $t(failKey(e)), tone: 'warn' }); }
  }
  async function del() {
    if (!confirmDelete) { confirmDelete = true; setTimeout(() => (confirmDelete = false), 4000); return; }
    try { await api.remove(id); showToast({ text: $t('blend.deleted') }); loadSauces(); go('/sauces'); }
    catch (e) { showToast({ text: $t(failKey(e)), tone: 'warn' }); }
  }
</script>

<!-- Delete and Riff: in the header on the kiosk, at the end of the left pane on a phone (three buttons beside the title
     left room for "Béch…") -->
{#snippet more()}
  <button class="hbtn del pressable" class:armed={confirmDelete} onclick={del}>{confirmDelete ? $t('sauce.delete.confirm') : $t('sauce.delete')}</button>
  <button class="hbtn pressable" onclick={riff}>{$t('sauce.riff')}</button>
{/snippet}

<div class="screen">
  <PageHeader title={s ? s.names[$lang] : '…'} sub={!s ? '' : !s.family ? $t('sauce.family.none') : s.family[$lang] === s.names[$lang] ? '' : s.family[$lang]}
              icon="sauces" color={P.teal} back={() => go('/sauces')}>
    {#if s}
      <span class="hmore">{@render more()}</span>
      <button class="hbtn edit pressable" onclick={() => go(`/sauces/${id}/edit`)}>{$t('sauce.edit')}</button>
    {/if}
  </PageHeader>
  {#if missing}
    <p class="gone">{$t('sauce.gone')}</p>
  {:else if s && $shelves}
    <div class="body">
      <aside class="left">
        <div class="big"><Vessel vessel={s.vessel} fill={s.fill} size={150} ribbon={s.origin === 'seed' ? $t('sauces.classic') : ''} /></div>
        <div class="yield">
          <button class="st pressable" aria-label={$t('sauce.less')} onclick={() => (ml = Math.max(MIN_YIELD, size - YIELD_STEP))}>−</button>
          <b>{$t('sauce.yield', { ml: size })}</b>
          <button class="st pressable" aria-label={$t('sauce.more')} onclick={() => (ml = Math.min(MAX_YIELD, size + YIELD_STEP))}>+</button>
        </div>
        <div class="gbar {gf?.tone}">{$t(`recipe.verdict.${s.gluten.state}`, { n: gf?.n ?? 0 })}</div>
        <h3>{$t('sauce.lines')}</h3>
        <ul class="lines">
          <!-- a fixed pool (a reload after an edit elsewhere only refills it), as every list the engine's answers fill -->
          {#each pool(s.lines, SAUCE_SLOTS.lines) as v, i (i)}
            <li class:typed={!!v && (v.kind === 'raw' || v.kind === 'off-shelf')} class:gone={!v}>
              <span class="sw" style:background={fills[i] ?? 'transparent'}></span>
              <span class="lt">{v ? lineLabel(v, $lang, $shelves.units, names, blends, factor) : ''}</span>
              <GlutenChip status={v?.gluten?.status ?? 'ok'} />
            </li>
          {/each}
        </ul>
        <h3>{$t('sauce.steps')}</h3>
        {#if s.steps[$lang].length}
          <ol class="steps">
            {#each s.steps[$lang] as step, i (i)}
              <li>{#each stepParts(step, s.timers[$lang][i] ?? []) as p}{#if p.seconds}<button class="dur pressable" onclick={() => startTimer(p.seconds!, i)}><span class="clk" aria-hidden="true"></span>{p.text}</button>{:else}{p.text}{/if}{/each}</li>
            {/each}
          </ol>
        {:else}<p class="muted">{$t('sauce.nosteps')}</p>{/if}
        {#if s.method?.[$lang]}<div class="method"><h3>{$t('sauce.notes')}</h3><p>{s.method[$lang]}</p></div>{/if}
        {#if s.tags.length}<p class="tags">{#each s.tags as tg}<span>#{tg}</span>{/each}</p>{/if}
        <button class="cook pressable" onclick={() => go(`/cook/sauce/${id}`)}>{$t('sauce.cook')} ▶</button>
        <div class="pmore">{@render more()}</div>
      </aside>
      <main class="right">
        <SauceEvalPanel {e} shelves={$shelves} {names} mode="scroll" mascotSize={104} emptyText={$t('sauce.noeval')} />
      </main>
    </div>
  {/if}
</div>

<style>
  .screen { height: 100%; display: flex; flex-direction: column; }
  .hbtn { min-height: var(--touch); min-width: var(--touch); padding: 0 16px; border-radius: 999px; border: var(--outline) solid var(--ink);
          background: var(--paper); font-weight: 800; font-size: 15px; white-space: nowrap; }
  .hbtn.edit { background: var(--herb); color: var(--ink); }
  .hbtn.del.armed { background: var(--tomato); color: var(--ink); }
  .hmore { display: contents; } .pmore { display: none; }
  .gone { padding: 40px; font-weight: 800; font-size: 19px; text-align: center; }
  .body { flex: 1; min-height: 0; display: grid; grid-template-columns: 340px minmax(0, 1fr); }
  .left { overflow-y: auto; padding: 14px 16px 90px 20px; border-right: var(--outline) dashed #E2D6C4; display: flex; flex-direction: column; gap: 10px; }
  .right { overflow-y: auto; padding: 14px 20px 90px 18px; }
  .big { display: grid; place-items: center; animation: settle .9s cubic-bezier(.3, 1.5, .5, 1) both; transform-origin: 50% 100%; }
  @keyframes settle { 0% { transform: rotate(-9deg) translateY(-14px); opacity: 0; } 55% { transform: rotate(4deg); opacity: 1; } 100% { transform: none; } }
  .yield { display: flex; align-items: center; gap: 8px; justify-content: center; }
  .yield b { font-family: var(--font-display); font-weight: 400; font-size: 20px; min-width: 7em; text-align: center; }
  .st { flex: none; width: var(--touch); height: var(--touch); border-radius: 50%; border: var(--outline) solid var(--ink); background: var(--paper);
        font-size: 30px; font-weight: 900; line-height: 1; box-shadow: var(--shadow-sm); }
  .gbar { font-weight: 800; font-size: 14px; border: var(--outline) solid var(--ink); border-radius: var(--r-sm); padding: 6px 10px; background: var(--butter); }
  .gbar.ok { background: #CFEFD0; } .gbar.swap { background: var(--teal); } .gbar.unknown { background: var(--paper); border-style: dashed; }
  h3 { font-size: 16px; margin: 6px 0 0; }
  .lines { list-style: none; margin: 0; padding: 0; }
  .lines li { display: flex; align-items: center; gap: 8px; min-height: 40px; border-bottom: 2px dashed #E7DCCB; font-weight: 800; font-size: 15px; }
  .lines li.typed .lt { font-style: italic; font-weight: 700; }
  .sw { flex: none; width: 18px; height: 18px; border-radius: 50%; border: 2px solid var(--ink); }
  .lt { flex: 1; min-width: 0; }
  .lines li.gone { display: none; }
  .steps { margin: 0; padding-left: 22px; display: flex; flex-direction: column; gap: 8px; font-weight: 600; font-size: 15.5px; line-height: 1.4; }
  .dur { display: inline-flex; align-items: center; min-height: var(--touch); padding: 0 12px; margin: 0 2px; border-radius: 999px; border: var(--outline) solid var(--ink);
         background: var(--butter); font: inherit; font-weight: 900; gap: 6px; }
  /* a clock face drawn in CSS: an OpenMoji icon here would be built inside the page's {#if} */
  .clk { flex: none; position: relative; width: 20px; height: 20px; border: 2.5px solid var(--ink); border-radius: 50%; background: var(--paper); }
  .clk::after { content: ''; position: absolute; left: 6.5px; top: 2px; width: 5px; height: 6px; border: solid var(--ink); border-width: 0 0 2.5px 2.5px; }
  .muted { margin: 0; opacity: .65; font-weight: 700; }
  .method p { margin: 0; font-weight: 600; line-height: 1.4; white-space: pre-wrap; }
  .tags { display: flex; flex-wrap: wrap; gap: 6px; margin: 0; } .tags span { font-weight: 800; font-size: 13px; background: var(--cream); border-radius: 999px; padding: 2px 9px; }
  .cook { min-height: 76px; border-radius: var(--r); border: var(--outline-thick) solid var(--ink); background: var(--herb); color: var(--ink);
          font-family: var(--font-display); font-size: 24px; box-shadow: var(--shadow); margin-top: 6px; }
  @media (max-aspect-ratio: 1/1) {
    .body { grid-template-columns: minmax(0, 1fr); overflow-y: auto; } .left, .right { overflow: visible; padding-bottom: 20px; } .left { border: 0; }
    .hbtn { padding: 0 10px; font-size: 13px; }
    .hmore { display: none; } .pmore { display: flex; gap: 8px; flex-wrap: wrap; }
  }
</style>
