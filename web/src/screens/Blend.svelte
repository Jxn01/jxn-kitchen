<script lang="ts">
  import { failKey } from '../lib/api';
  // One blend: the jar big, its parts striped bottom up; the parts list with the batch scaler
  // (one jar = N tablespoons → grams of each, and the jar on screen fills to that level); the method; and everything
  // the engine says, read-only, in one scroll.
  import PageHeader from '../components/PageHeader.svelte';
  import SpiceJar from '../components/spices/SpiceJar.svelte';
  import EvalPanel from '../components/spices/EvalPanel.svelte';
  import { api, batchGrams, blendList, fmtParts, jarIndex, JAR_TSP, loadRack, rack, type Blend } from '../lib/spices';
  import { P } from '../lib/palette';
  import { lang, t } from '../lib/i18n';
  import { go } from '../lib/router';
  import { showToast } from '../lib/toast';

  let { id }: { id: number } = $props();
  let b = $state<Blend | null>(null);
  let missing = $state(false);
  let tbsp = $state<number | null>(null);
  let confirmDelete = $state(false);
  $effect(() => { if (!$rack) loadRack(); });
  $effect(() => {
    void $blendList;                                  // an SSE `blends` event reloads the list: reload this one too
    api.get(id).then((x) => { b = x; missing = false; }).catch(() => (missing = true));
  });
  let jars = $derived(jarIndex($rack));
  let total = $derived(b ? b.parts.reduce((n, p) => n + p.parts, 0) : 0);
  let size = $derived(tbsp ?? Math.round((total / 3) * 2) / 2);
  let grams = $derived(b ? batchGrams(b.parts, jars, size) : []);
  let stripes = $derived(b ? b.parts.map((p) => ({ fill: jars.get(p.spice)?.fill ?? '#CCBFA8', part: p.parts })) : null);

  async function riff() {
    try { const r = await api.riff(id); go(`/spices/${r.id}/edit`); } catch (e) { showToast({ text: $t(failKey(e)), tone: 'warn' }); }
  }
  async function del() {
    if (!confirmDelete) { confirmDelete = true; setTimeout(() => (confirmDelete = false), 4000); return; }
    try {
      const r = await api.remove(id);
      if (r.ok) { showToast({ text: $t('blend.deleted') }); go('/spices'); }
      else showToast({ text: $t('blend.inuse', { list: r.sauces.map((s) => s.name).join(', ') }), tone: 'warn' }, 8000);
    } catch (e) { showToast({ text: $t(failKey(e)), tone: 'warn' }); }
  }
</script>

<!-- Delete and Riff: in the header on the kiosk, at the end of the left pane on a phone (three buttons beside the title
     left room for one letter of it) -->
{#snippet more()}
  <button class="hbtn del pressable" class:armed={confirmDelete} onclick={del}>{confirmDelete ? $t('blend.delete.confirm') : $t('blend.delete')}</button>
  <button class="hbtn pressable" onclick={riff}>{$t('blend.riff')}</button>
{/snippet}

<div class="screen">
  <PageHeader title={b ? b.names[$lang] : '…'} sub={b ? $t('blend.parts', { n: b.parts.length, tsp: fmtParts(total) }) : ''}
              icon="spices" color={P.tangerine} back={() => go('/spices')}>
    {#if b}
      <span class="hmore">{@render more()}</span>
      <button class="hbtn edit pressable" onclick={() => go(`/spices/${id}/edit`)}>{$t('blend.edit')}</button>
    {/if}
  </PageHeader>
  {#if missing}
    <p class="gone">{$t('blend.gone')}</p>
  {:else if b && $rack}
    <div class="body">
      <aside class="left">
        <div class="bigjar"><SpiceJar size={170} stripes={stripes} level={Math.min(1, (size * 3) / JAR_TSP)} /></div>
        <div class="batch">
          <span class="bl">{$t('blend.batch')}</span>
          <button class="st pressable" aria-label={$t('blend.less')} onclick={() => (tbsp = Math.max(1, size - 1))}>−</button>
          <b>{$t('blend.batch.tbsp', { n: fmtParts(size) })}</b>
          <button class="st pressable" aria-label={$t('blend.more')} onclick={() => (tbsp = Math.min(60, size + 1))}>+</button>
        </div>
        <p class="fillpct">{$t('blend.batch.fill', { pct: Math.round(((size * 3) / JAR_TSP) * 100) })}</p>
        <table class="parts">
          <tbody>
            {#each b.parts as p, i (p.spice)}
              {@const j = jars.get(p.spice)}
              <tr><td><span class="sw" style:background={j?.fill}></span></td><td class="nm">{j?.label[$lang] ?? p.spice}</td>
                <td class="n">{fmtParts(grams[i].tsp)} {$t('blend.tsp')}</td><td class="n g">{grams[i].g.toLocaleString($lang)} g</td></tr>
            {/each}
          </tbody>
          <tfoot><tr><td></td><td colspan="3">{$t('blend.total', { g: grams.reduce((n, x) => n + x.g, 0).toLocaleString($lang, { maximumFractionDigits: 1 }) })}</td></tr></tfoot>
        </table>
        {#if b.method?.[$lang]}<div class="method"><h3>{$t('blend.method')}</h3><p>{b.method[$lang]}</p></div>{/if}
        {#if b.tags.length}<p class="tags">{#each b.tags as tg}<span>#{tg}</span>{/each}</p>{/if}
        {#if b.missing_jars.length}<p class="warn">{$t('blend.missing', { list: b.missing_jars.join(', ') })}</p>{/if}
        <div class="pmore">{@render more()}</div>
      </aside>
      <main class="right">
        {#if b.evaluation}<EvalPanel e={{ ...b.evaluation, gluten: b.gluten }} rack={$rack} mode="scroll" mascotSize={104} />{/if}
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
  .body { flex: 1; min-height: 0; display: grid; grid-template-columns: 330px minmax(0, 1fr); }
  .left { overflow-y: auto; padding: 14px 16px 90px 20px; border-right: var(--outline) dashed #E2D6C4; display: flex; flex-direction: column; gap: 10px; }
  .right { overflow-y: auto; padding: 14px 20px 90px 18px; }
  .bigjar { display: grid; place-items: center; animation: settle .9s cubic-bezier(.3, 1.5, .5, 1) both; transform-origin: 50% 100%; }
  @keyframes settle { 0% { transform: rotate(-9deg) translateY(-14px); opacity: 0; } 55% { transform: rotate(4deg); opacity: 1; } 100% { transform: none; } }
  .batch { display: flex; align-items: center; gap: 8px; justify-content: center; }
  .bl { font-weight: 900; font-size: 14px; }
  .batch b { font-family: var(--font-display); font-weight: 400; font-size: 20px; min-width: 5.5em; text-align: center; }
  .st { flex: none; width: var(--touch); height: var(--touch); border-radius: 50%; border: var(--outline) solid var(--ink); background: var(--paper);
        font-size: 30px; font-weight: 900; line-height: 1; box-shadow: var(--shadow-sm); }
  .fillpct { margin: -4px 0 0; text-align: center; font-weight: 700; font-size: 13px; opacity: .7; }
  .parts { width: 100%; border-collapse: collapse; font-weight: 800; font-size: 15px; }
  .parts td { padding: 5px 4px; border-bottom: 2px dashed #E7DCCB; }
  .parts tfoot td { border: 0; font-weight: 900; padding-top: 8px; }
  .sw { display: block; width: 18px; height: 18px; border-radius: 5px; border: 2px solid var(--ink); }
  .nm { width: 100%; } .n { text-align: right; white-space: nowrap; } .g { opacity: .7; }
  .method h3 { font-size: 15px; margin: 6px 0 2px; } .method p { margin: 0; font-weight: 600; line-height: 1.4; }
  .tags { display: flex; flex-wrap: wrap; gap: 6px; margin: 0; } .tags span { font-weight: 800; font-size: 13px; background: var(--cream); border-radius: 999px; padding: 2px 9px; }
  .warn { background: var(--butter); border: 2px solid var(--ink); border-radius: var(--r-sm); padding: 6px 10px; font-weight: 800; margin: 0; }
  @media (max-aspect-ratio: 1/1) {
    .body { grid-template-columns: minmax(0, 1fr); overflow-y: auto; } .left, .right { overflow: visible; padding-bottom: 20px; } .left { border: 0; }
    .hbtn { padding: 0 10px; font-size: 13px; }
    .hmore { display: none; } .pmore { display: flex; gap: 8px; flex-wrap: wrap; }
  }
</style>
