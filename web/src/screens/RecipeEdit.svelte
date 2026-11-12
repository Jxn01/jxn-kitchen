<script lang="ts">
  import PageHeader from '../components/PageHeader.svelte';
  import GlutenChip from '../components/GlutenChip.svelte';
  import { api, importDraft, pendingEdits, saveRecipe, type RecipeIn } from '../lib/recipes';
  import { failKey } from '../lib/api';
  import { get } from 'svelte/store';
  import { P } from '../lib/palette';
  import { t } from '../lib/i18n';
  import { go } from '../lib/router';
  import { osk } from '../lib/osk';
  import { showToast } from '../lib/toast';

  /** `folder`: a NEW recipe is filed in this folder (the one it was started from); an existing one keeps its own. */
  let { id = null, folder = null }: { id?: number | null; folder?: number | null } = $props();
  let inFolder = $state<number | null>(null);        // where the recipe being edited lives (for Back after Delete)
  let title = $state(''), servings = $state(4), total = $state<number | null>(null);
  let ingredients = $state(''), steps = $state(''), tags = $state(''), notes = $state(''), sourceUrl = $state<string | null>(null);
  let preview = $state<Awaited<ReturnType<typeof api.parse>>>([]);
  let file = $state<File | null>(null);
  let confirmDelete = $state(false), saving = $state(false);
  let scanImage = $state<string | null>(null);      // a draft read by OCR: its page beside the form
  let draftCode = $derived($importDraft && $importDraft.id === id ? $importDraft.code : null);

  $effect(() => {
    if (id == null) return;
    api.get(id).then((r) => {
      inFolder = r.folder_id; title = r.title; servings = r.base_servings; total = r.total_min; notes = r.notes ?? ''; sourceUrl = r.source_url;
      scanImage = r.origin === 'scan' ? r.image : null;
      ingredients = [...new Set(r.lines.map((l) => l.raw))].join('\n'); steps = r.steps.map((s) => s.text).join('\n'); tags = r.tags.join(', ');
      // an edit saved offline and not on the server yet: continue from it, not from the server's older copy
      const p = get(pendingEdits).get(id!);
      if (p) {
        title = p.title; servings = p.servings; total = p.total_min ?? null; notes = p.notes ?? ''; sourceUrl = p.source_url ?? null;
        ingredients = p.ingredients.join('\n'); steps = p.steps.join('\n'); tags = p.tags.join(', ');
      }
    });
  });
  let timer: ReturnType<typeof setTimeout>;
  $effect(() => {
    const lines = ingredients.split('\n').map((x) => x.trim()).filter(Boolean).slice(0, 200);
    clearTimeout(timer);
    timer = setTimeout(() => { api.parse(lines).then((p) => (preview = p)).catch(() => {}); }, 400);
  });

  async function save() {
    if (!title.trim()) return;
    saving = true;
    const body: RecipeIn = {
      title: title.trim(), servings, total_min: total || null, notes: notes.trim() || null, source_url: sourceUrl,
      ingredients: ingredients.split('\n').map((x) => x.trim()).filter(Boolean),
      steps: steps.split('\n').map((x) => x.trim()).filter(Boolean),
      tags: tags.split(',').map((x) => x.trim()).filter(Boolean),
    };
    try {
      if (id != null && (await saveRecipe(id, body)) === 'queued') {
        // offline: the edit waits on this kiosk (lib/outbox.ts); a photo needs the server, so it is not kept
        showToast({ text: $t(file ? 'offline.photo' : 'offline.queued') }, file ? 6000 : 4000);
        importDraft.set(null);
        go(`/recipe/${id}`);
        return;
      }
      const rid = id ?? (await api.create({ ...body, folder_id: folder })).id;   // a NEW recipe needs the server
      if (file) await api.uploadImage(rid, file);
      showToast({ text: $t('edit.saved') });
      importDraft.set(null);
      go(`/recipe/${rid}`);
    } catch (e) { showToast({ text: $t(failKey(e)), tone: 'warn' }); } finally { saving = false; }
  }
  async function del() {
    if (!confirmDelete) { confirmDelete = true; setTimeout(() => (confirmDelete = false), 4000); return; }
    try { await api.remove(id!); go(inFolder ? `/recipes/${inFolder}` : '/recipes'); } catch (e) { showToast({ text: $t(failKey(e)), tone: 'warn' }); }
  }
</script>

<div class="screen">
  <PageHeader title={id == null ? $t('edit.new') : title || '…'} icon="recipes" color={P.tomato} back={() => go(id == null ? (folder ? `/recipes/${folder}` : '/recipes') : `/recipe/${id}`)}>
    {#if id != null}<button class="del pressable" class:armed={confirmDelete} onclick={del}>{confirmDelete ? $t('edit.delete.confirm') : $t('edit.delete')}</button>{/if}
    <button class="save pressable" disabled={saving || !title.trim()} onclick={save}>✓ {$t('edit.save')}</button>
  </PageHeader>
  <div class="body">
    <div class="col">
      {#if draftCode}
        <div class="draft"><b>{$t('import.draft.title')}</b> {$t(`import.reason.${draftCode}`)}</div>
      {/if}
      <label>{$t('edit.title')}<input bind:value={title} use:osk maxlength="200" /></label>
      <div class="row">
        <label>{$t('edit.servings')}<input type="number" min="1" max="50" bind:value={servings} /></label>
        <label>{$t('edit.time')}<input type="number" min="0" max="10000" bind:value={total} /></label>
      </div>
      <label class="grow">{$t('edit.ingredients')}<textarea bind:value={ingredients} use:osk rows="8"></textarea></label>
      <label class="grow">{$t('edit.steps')}<textarea bind:value={steps} use:osk rows="6"></textarea></label>
      <label>{$t('edit.tags')}<input bind:value={tags} use:osk /></label>
      <label>{$t('edit.notes')}<textarea bind:value={notes} use:osk rows="2"></textarea></label>
      <label class="photo">{$t('edit.photo')}<input type="file" accept="image/*" capture="environment" onchange={(e) => (file = (e.currentTarget as HTMLInputElement).files?.[0] ?? null)} /></label>
    </div>
    <aside class="prev">
      {#if scanImage}<a class="scan" href={scanImage} target="_blank" rel="noopener"><img src={scanImage} alt={$t('edit.scan')} /></a>{/if}
      <h2>{$t('edit.preview')}</h2>
      <ul>
        {#each preview as p, i (i)}
          <li><span class="q">{p.qty_text}</span><span class="n">{p.item_name ?? p.name}{#if p.gf_name}<small> → {p.gf_name}</small>{/if}</span><GlutenChip status={p.gluten} /></li>
        {/each}
      </ul>
    </aside>
  </div>
</div>

<style>
  .screen { height: 100%; display: flex; flex-direction: column; }
  .save { min-height: var(--touch); padding: 0 20px; border-radius: 999px; border: var(--outline) solid var(--ink); background: var(--herb); color: var(--ink); font-weight: 900; font-size: 16px; }
  .save:disabled { opacity: .5; }
  .del { min-height: var(--touch); padding: 0 16px; border-radius: 999px; border: var(--outline) solid var(--ink); background: var(--paper); font-weight: 800; }
  .del.armed { background: var(--tomato); color: var(--ink); }
  .body { flex: 1; min-height: 0; display: grid; grid-template-columns: 1fr 340px; gap: 16px; padding: 14px 20px 20px; }
  .col { min-height: 0; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; padding-bottom: calc(var(--kb-h) + 10px); }
  .draft { background: var(--butter); border: var(--outline) solid var(--ink); border-radius: var(--r); padding: 12px 16px;
           font-weight: 700; font-size: 16px; line-height: 1.35; }
  label { display: flex; flex-direction: column; gap: 4px; font-weight: 800; font-size: 14px; }
  input, textarea { border: var(--outline) solid var(--ink); border-radius: var(--r-sm); padding: 10px 14px; font: inherit; font-weight: 600; font-size: 17px; background: var(--paper); }
  input { min-height: var(--touch); } textarea { resize: vertical; line-height: 1.4; }
  .row { display: flex; gap: 10px; } .row label { flex: 1; }
  .photo input { border-style: dashed; }   /* a touch target like any other (it was 50 px: unseen below the fold until the audit scrolled to it) */
  .prev { min-height: 0; overflow-y: auto; background: var(--paper); border: var(--outline) solid var(--ink); border-radius: var(--r); padding: 10px 14px; }
  h2 { font-size: 17px; margin-bottom: 6px; }
  .scan img { width: 100%; max-height: 360px; object-fit: contain; background: #fff; border: var(--outline) solid var(--ink); border-radius: var(--r-sm); margin-bottom: 10px; }
  ul { list-style: none; margin: 0; padding: 0; }
  li { display: flex; align-items: center; gap: 8px; min-height: 40px; border-bottom: 2px dashed #E7DCCB; font-size: 14.5px; }
  .q { width: 64px; flex: none; opacity: .6; font-weight: 700; } .n { flex: 1; font-weight: 800; } small { font-weight: 700; color: var(--teal); }
  @media (max-aspect-ratio: 1/1) {
    .body { grid-template-columns: 1fr; grid-auto-rows: max-content; overflow-y: auto; } .col { overflow: visible; padding-bottom: 20px; }
    .save, .del { padding: 0 12px; font-size: 15px; }   /* phones: the title keeps some room beside both buttons */
  }
</style>
