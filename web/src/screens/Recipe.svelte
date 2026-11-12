<script lang="ts">
  import PageHeader from '../components/PageHeader.svelte';
  import Icon from '../components/Icon.svelte';
  import Switch from '../components/Switch.svelte';
  import GlutenChip from '../components/GlutenChip.svelte';
  import LinePicker from '../components/LinePicker.svelte';
  import FolderPicker from '../components/FolderPicker.svelte';
  import { folderList, foldersLoaded, loadFolders, pathLabel, refusalKey } from '../lib/folders';
  import { folders } from '../lib/folderactions';
  import { failKey } from '../lib/api';
  import { api, badge, lineText, pendingEdits, type Line, type Recipe } from '../lib/recipes';
  import { P } from '../lib/palette';
  import { t } from '../lib/i18n';
  import { go } from '../lib/router';
  import { showToast } from '../lib/toast';
  import { pantry } from '../lib/pantry';

  let { id }: { id: number } = $props();
  let r = $state<Recipe | null>(null);
  let servings = $state<number | null>(null);
  let gf = $state(true);                       // the kitchen is fully GF: the GF version is the default view
  let picking = $state<Line | null>(null);
  let filing = $state(false);
  // load ONCE (the SSE `recipes` event keeps it fresh): conditioned on the list being empty, every load set a new
  // empty array, re-ran this, and fetched again as fast as the server answered while no folder existed
  $effect(() => { if (!$foldersLoaded) loadFolders(); });
  const st = pantry.state;

  async function load() { try { r = await api.get(id, servings ?? undefined); } catch { r = null; } }
  $effect(() => { void id; void servings; void $st; load(); });

  let b = $derived(r ? badge(r.verdict) : null);
  let tips = $derived(r ? [...new Set(r.lines.filter((l) => (l.gluten === 'swap' || l.gluten === 'check') && l.tip).map((l) => l.tip!))] : []);
  const step = (d: number) => { if (r) servings = Math.min(50, Math.max(1, r.servings + d)); };
  async function toBuy() {
    try { await api.missingToShopping(id); showToast({ text: $t('recipe.tobuy.done') }); } catch (e) { showToast({ text: $t(failKey(e)), tone: 'warn' }); }
  }
  async function fileIn(target: number | null) {
    filing = false;
    try {
      await folders.moveRecipes([id], target);
      await load();
      showToast({ text: $t('folders.moved', { place: target === null ? $t('folders.pick.top') : pathLabel($folderList, target) }) });
    } catch (e) { showToast({ text: $t(refusalKey(e)), tone: 'warn' }); }
  }
  async function pick(itemId: string | null, ok: boolean) {
    const l = picking; picking = null;
    if (!l) return;
    try { r = await api.fixLine(id, l.pos, itemId, ok); } catch (e) { showToast({ text: $t(failKey(e)), tone: 'warn' }); }
  }
</script>

{#if r}
  <div class="screen">
    {#snippet stepper(rr: Recipe)}
      <div class="serv"><button class="pressable" onclick={() => step(-1)}>−</button><b>{$t('recipes.servings', { n: rr.servings })}</b><button class="pressable" onclick={() => step(1)}>+</button></div>
    {/snippet}
    <PageHeader title={r.title} sub={r.source_site ? $t('recipe.source', { site: r.source_site }) : ''} icon="recipes" color={P.tomato} back={() => go(r?.folder_id ? `/recipes/${r.folder_id}` : '/recipes')}>
      <span class="wide">{@render stepper(r)}</span>
      <button class="edit pressable" aria-label={$t('recipe.move')} title={$t('recipe.move')} onclick={() => (filing = true)}><Icon name="folder" size={28} /></button>
      <button class="edit pressable" aria-label={$t('recipe.edit')} onclick={() => go(`/recipe/${id}/edit`)}>✎</button>
    </PageHeader>
    <div class="narrow">{@render stepper(r)}</div>
    <div class="gbar {b?.tone}">
      <span class="wheat"><Icon name="wheat" size={44} /></span>
      <span class="v">{$t(`recipe.verdict.${r.verdict.state}`, { n: r.verdict.state === 'swaps' ? r.verdict.swaps : r.verdict.state === 'check' ? r.verdict.check : r.verdict.unknown })}</span>
      {#if r.verdict.swaps}<button class="gfsw pressable" onclick={() => (gf = !gf)}>{$t('recipe.gfversion')} <Switch on={gf} /></button>{/if}
    </div>
    {#if $pendingEdits.has(id)}<p class="pending">{$t('recipe.pending')}</p>{/if}
    <div class="body">
      <section class="left">
        <h2>{$t('recipe.ingredients')}</h2>
        <ul class="ing">
          {#each r.lines as l (l.pos)}
            {@const lt = lineText(l, gf)}
            <li><button class="line" onclick={() => (picking = l)}>
              <span class="dot" class:yes={l.have === true} class:no={l.have === false}></span>
              <span class="txt">{#if lt.struck}<s>{lt.struck}</s> → {/if}<b>{lt.text}</b>{#if l.note}<i> ({l.note})</i>{/if}</span>
              <GlutenChip status={l.gluten} />
            </button></li>
          {/each}
        </ul>
        {#if r.steps.length}
          <h2>{$t('recipe.steps')}</h2>
          <ol class="steps">{#each r.steps as s (s.pos)}<li>{s.text}</li>{/each}</ol>
        {/if}
        {#if r.notes}<h2>{$t('recipe.notes')}</h2><p class="notes">{r.notes}</p>{/if}
      </section>
      <aside class="side">
        {#if r.image}<img class="photo" src={r.image} alt="" />{/if}
        <div class="have">
          <small>{$t('recipe.have')}</small>
          <b>{$t('recipe.of', { have: r.have, total: r.total })}</b>
          {#if r.missing.length}
            <span class="miss">{$t('recipe.missing', { list: r.missing.map((m) => m.name).join(', ') })}</span>
            <button class="buy pressable" onclick={toBuy}>{$t('recipe.tobuy')}</button>
          {:else}<span class="miss">{$t('recipe.allhere')}</span>{/if}
        </div>
        {#each tips as tip}<div class="tip"><span class="tipi"><Icon name="tip" size={26} /></span>{tip}</div>{/each}
        <button class="cook pressable" onclick={() => go(`/cook/${id}?servings=${r!.servings}`)}>{$t('recipe.cook')} ▶</button>
      </aside>
    </div>
  </div>
  {#if filing}
    <FolderPicker title={$t('recipe.move')} current={r.folder_id} onpick={fileIn} oncancel={() => (filing = false)} />
  {/if}
  {#if picking}
    <LinePicker name={picking.name} onpick={(i) => pick(i, false)} onok={() => pick(null, true)} oncancel={() => (picking = null)} />
  {/if}
{/if}

<style>
  .screen { height: 100%; display: flex; flex-direction: column; }
  .narrow { display: none; }
  .serv { display: flex; align-items: center; gap: 8px; background: var(--paper); border: var(--outline) solid var(--ink); border-radius: 999px; padding: 4px; }
  .serv button { width: var(--touch); height: var(--touch); border-radius: 50%; border: var(--outline) solid var(--ink); background: var(--butter); font-size: 26px; font-weight: 900; line-height: 1; }
  .serv b { white-space: nowrap; font-size: 15px; }
  .edit { width: var(--touch); height: var(--touch); border-radius: 50%; border: var(--outline) solid var(--ink); background: var(--paper); font-size: 24px;
          display: grid; place-items: center; }
  .gbar { flex: none; margin: 12px 20px 0; min-height: 70px; display: flex; align-items: center; gap: 12px; padding: 6px 12px; font-weight: 800; font-size: 17px;
          border: var(--outline) solid var(--ink); border-radius: var(--r); box-shadow: var(--shadow-sm); background: var(--butter); }
  .gbar.ok { background: #CFEFD0; } .gbar.unknown { background: var(--paper); border-style: dashed; }
  .wheat { position: relative; display: grid; }
  .gbar:not(.ok) .wheat::after { content: ''; position: absolute; left: -4px; right: -4px; top: 46%; height: 6px; background: var(--tomato);
          border: 2px solid var(--ink); border-radius: 4px; transform: rotate(-40deg); }
  .v { flex: 1; }
  .gfsw { display: flex; align-items: center; gap: 10px; min-height: var(--touch); padding: 0 6px 0 14px; border-radius: 999px; border: var(--outline) solid var(--ink);
          background: var(--paper); font-weight: 800; font-size: 15px; }
  .body { flex: 1; min-height: 0; display: grid; grid-template-columns: 1fr 340px; gap: 16px; padding: 12px 20px 16px; }
  /* an edit saved offline, not on the server yet (lib/recipes.ts pendingEdits) */
  .pending { margin: 8px 20px 0; padding: 8px 14px; border: var(--outline) solid var(--ink); border-radius: var(--r); background: var(--butter); font-weight: 800; }
  .left { min-height: 0; overflow-y: auto; background: var(--paper); border: var(--outline) solid var(--ink); border-radius: var(--r); padding: 12px 16px 60px; }
  h2 { font-size: 19px; margin: 6px 0 8px; }
  .ing { list-style: none; margin: 0 0 10px; padding: 0; }
  .ing li { border-bottom: 2px dashed #E7DCCB; }
  .line { width: 100%; display: flex; align-items: center; gap: 10px; min-height: var(--touch); border: 0; background: none;
          padding: 0; text-align: left; font: inherit; font-size: 16px; color: inherit; }
  .line:active { background: var(--cream); }
  .dot { width: 16px; height: 16px; border-radius: 50%; border: 2px solid var(--ink); flex: none; background: transparent; opacity: .35; }
  .dot.yes { background: var(--herb); opacity: 1; } .dot.no { background: var(--paper); opacity: 1; }
  .txt { flex: 1; min-width: 0; } .txt s { opacity: .5; font-weight: 600; } .txt i { opacity: .6; font-style: normal; font-size: 14px; }
  .steps { margin: 0; padding-left: 26px; display: flex; flex-direction: column; gap: 10px; font-size: 16.5px; line-height: 1.4; }
  .notes { white-space: pre-wrap; opacity: .8; }
  .side { min-height: 0; display: flex; flex-direction: column; gap: 12px; overflow-y: auto; }
  .photo { width: 100%; height: 150px; object-fit: cover; border: var(--outline) solid var(--ink); border-radius: var(--r); }
  .have { background: var(--paper); border: var(--outline) solid var(--ink); border-radius: var(--r); padding: 12px 16px; display: flex; flex-direction: column; gap: 4px; }
  .have small { font-weight: 800; font-size: 14px; } .have b { font-family: var(--font-display); font-weight: 400; font-size: 32px; }
  .miss { font-weight: 700; font-size: 14px; }
  .buy { margin-top: 6px; min-height: var(--touch); border-radius: var(--r-sm); border: var(--outline) solid var(--ink); background: var(--teal); color: var(--ink); font-weight: 900; font-size: 15px; }
  .tip { display: flex; gap: 8px; align-items: flex-start; background: var(--teal); color: var(--ink); border: var(--outline) solid var(--ink); border-radius: var(--r); padding: 10px 14px; font-weight: 700; font-size: 14px; line-height: 1.35; }
  .tipi { flex: none; width: 30px; height: 30px; border-radius: 50%; background: var(--cream); display: grid; place-items: center; }
  .cook { margin-top: auto; min-height: 76px; border-radius: var(--r); border: var(--outline-thick) solid var(--ink); background: var(--herb); color: var(--ink);
          font-family: var(--font-display); font-size: 26px; box-shadow: var(--shadow); flex: none; }
  @media (max-aspect-ratio: 1/1) {
    .body { grid-auto-rows: max-content; }
    .wide { display: none; } .narrow { display: flex; justify-content: center; padding: 10px 12px 0; }
    .body { grid-template-columns: 1fr; overflow-y: auto; } .left { overflow: visible; } .side { overflow: visible; }
    .gbar { flex-wrap: wrap; }
  }
</style>
