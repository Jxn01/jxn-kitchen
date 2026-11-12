<script lang="ts">
  // The sauce engine. Left: the shelves — eleven shelf tabs, the user's Blends, the Spices
  // (the rack, by its seven shelves) and Notes (steps, notes, yield, tags) — a fixed set of slots every tab reuses; tap:
  // onto the tray with the item's usual amount. Your sauce, the tray: − amount + in the item's step, the unit chip flips
  // through its units (converted), tap a line to see only its findings, hold it to put it back; "Something else…" reads
  // a typed line on the server and it lands as what it is. The header: the name, the family chip (detected, or the
  // user's choice from the family sheet), Save, Delete. Right: the live panel — 300 ms after the last change (the tray,
  // the steps or the family) the engine reads the sauce; an answer older than the newest request is dropped.
  //
  // Nothing is built on a tap — the slots, the tray's cards, the suggestion cards,
  // the notes pane, the typed-line sheet and the family sheet are all mounted with the page and shown by class.
  import { onDestroy, onMount } from 'svelte';
  import PageHeader from '../components/PageHeader.svelte';
  import MiniJar from '../components/spices/MiniJar.svelte';
  import SauceEvalPanel from '../components/sauces/SauceEvalPanel.svelte';
  import ScoreDock from '../components/ScoreDock.svelte';
  import FamilyTree from '../components/sauces/FamilyTree.svelte';
  import { createEvaluator, pool } from '../lib/engine';
  import { api, flipUnit, fmtAmount, fromTyped, fromView, itemIndex, lineKey, loadSauces, loadShelves, nameIndex, SAUCE_SLOTS,
           shelves, stepAmount, stepOf, trayAdd, trayDrop, traySet, unitsOf, type SauceEvaluation, type SauceLine } from '../lib/sauces';
  import { blendList, jarIndex, loadBlends, loadRack, rack } from '../lib/spices';
  import { failKey, OfflineError } from '../lib/api';
  import { longpress } from '../lib/longpress';
  import { P } from '../lib/palette';
  import { lang, t } from '../lib/i18n';
  import { go } from '../lib/router';
  import { osk } from '../lib/osk';
  import { showToast } from '../lib/toast';

  let { id = null }: { id?: number | null } = $props();
  let name = $state(''), notes = $state(''), tags = $state(''), stepsText = $state(''), yieldText = $state('');
  let tray = $state<SauceLine[]>([]);
  let family = $state<string | null>(null);        // the user's choice; null = the engine detects it
  let tab = $state(0);                              // 0..10 a shelf · BLENDS · SPICES · NOTES
  let rackShelf = $state(0);
  let focus = $state<string | null>(null);         // a tray line's item or jar: the ledger shows only its lines
  let e = $state<SauceEvaluation | null>(null);
  let panel = $state<HTMLElement>();
  let ghost = $state<Record<string, number> | null>(null);
  let saving = $state(false), confirmDelete = $state(false);
  let typedOpen = $state(false), typedText = $state(''), typedBusy = $state(false);
  let sheetOpen = $state(false);
  let hopped = $state<string | null>(null);

  onMount(() => { if (!$shelves) loadShelves(); if (!$rack) loadRack(); loadBlends(); });
  $effect(() => {
    if (id == null) return;
    api.get(id).then((s) => {
      name = s.name; notes = s.notes ?? ''; tags = s.tags.join(', '); yieldText = s.yield_ml ? String(s.yield_ml) : '';
      stepsText = s.steps[$lang].join('\n'); tray = fromView(s.lines); family = s.family_user ? (s.family?.id ?? null) : null;
    }).catch((e) => showToast({ text: $t(failKey(e)), tone: 'warn' }));
  });

  let shelfCount = $derived($shelves?.shelves.length ?? 0);
  let BLENDS = $derived(shelfCount), SPICES = $derived(shelfCount + 1), NOTES = $derived(shelfCount + 2);
  let items = $derived(itemIndex($shelves));
  let jars = $derived(jarIndex($rack));
  let names = $derived(nameIndex($shelves, ($rack?.shelves ?? []).flatMap((s) => s.jars), $lang));
  let blendNames = $derived(Object.fromEntries($blendList.map((b) => [b.id, b.names[$lang]])));
  let max = $derived($shelves?.max_lines ?? SAUCE_SLOTS.lines);

  // what a slot shows: a shelf item, a blend or a rack jar — one shape, so one set of slots serves every tab
  type Slot = { line: SauceLine; key: string; label: string; fill: string; jar: boolean; gf: boolean };
  const shelfSlots = (i: number): Slot[] => ($shelves?.shelves[i]?.items ?? []).map((it) => ({
    line: { shelf: it.id, qty: it.default, unit: it.unit }, key: `shelf:${it.id}`, label: it.name[$lang], fill: it.fill, jar: false, gf: it.gluten === 'label' }));
  const blendSlots = (): Slot[] => $blendList.map((b) => ({
    line: { blend: b.id, qty: 1, unit: 'tsp' }, key: `blend:${b.id}`, label: b.names[$lang], fill: b.jar_fill, jar: true, gf: b.gluten.status === 'check' }));
  const jarSlots = (i: number): Slot[] => ($rack?.shelves[i]?.jars ?? []).map((j) => ({
    line: { spice: j.id, qty: 1, unit: 'tsp' }, key: `spice:${j.id}`, label: j.label[$lang], fill: j.fill, jar: true, gf: j.gluten === 'label' }));
  // the slots are as many as the fullest tab: a tab tap only changes what each one shows (building one shelf's
  // jars and dropping the last one's cost a 168 ms frame on the kiosk)
  let slots = $derived(Math.max(0, ...($shelves?.shelves ?? []).map((s) => s.items.length), ...($rack?.shelves ?? []).map((s) => s.jars.length), $blendList.length));
  let onTab = $derived<Slot[]>(tab < shelfCount ? shelfSlots(tab) : tab === BLENDS ? blendSlots() : tab === SPICES ? jarSlots(rackShelf) : []);
  let inTray = $derived(new Set(tray.map(lineKey)));

  const steps = () => stepsText.split('\n').map((x) => x.trim()).filter(Boolean).slice(0, 30);
  const ev = createEvaluator<SauceLine, SauceEvaluation | null>(
    (lines, seq) => api.evaluate(lines, steps(), family, seq), (x) => { ghost = e?.taste ?? null; e = x; });
  const busy = ev.busy;
  // the steps and the family change the answer too (a whisked yolk over heat, a chosen family): each schedules one
  $effect(() => { void stepsText; void family; ev.schedule(tray.map((l) => ({ ...l }))); });
  onDestroy(() => ev.cancel());
  const about = (l: SauceLine) => l.shelf ?? l.spice ?? null;
  $effect(() => { if (focus && !tray.some((l) => about(l) === focus)) focus = null; });
  // the engine's suggestions follow an answer a moment later (three new cards in the answer's frame, 84 ms)
  let offered = $state<string[]>([]);
  $effect(() => {
    const s = e?.suggest ?? [];
    if (!s.length) { offered = []; return; }
    const h = setTimeout(() => (offered = s), 450);
    return () => clearTimeout(h);
  });
  let suggest = $derived(offered.filter((s) => items.has(s) && !inTray.has(`shelf:${s}`)).slice(0, 3));

  function add(l: SauceLine) {
    const k = lineKey(l);
    if (inTray.has(k)) return;
    if (tray.length >= max) { showToast({ text: $t('edit.sauce.full') }); return; }
    tray = trayAdd(tray, l, max);
    hopped = k; setTimeout(() => { if (hopped === k) hopped = null; }, 600);
  }
  function addItem(iid: string) { const it = items.get(iid); if (it) add({ shelf: it.id, qty: it.default, unit: it.unit }); }
  function step(i: number, dir: 1 | -1) {
    const l = tray[i];
    if (l?.qty !== undefined) tray = traySet(tray, i, { qty: stepAmount(l.qty, stepOf(l, items), dir) });
  }
  function flip(i: number) { tray = tray.map((l, k) => (k === i ? flipUnit(l, items, jars) : l)); }
  async function addTyped() {
    const text = typedText.trim();
    if (!text || typedBusy) return;
    typedBusy = true;
    try {
      const l = fromTyped(await api.typed(text));
      if (tray.length >= max) showToast({ text: $t('edit.sauce.full') });
      else { tray = trayAdd(tray, l, max); typedText = ''; typedOpen = false; }
    } catch (err) {
      showToast({ text: $t(err instanceof OfflineError ? 'toast.needs' : 'edit.sauce.typed.bad'), tone: 'warn' });
    } finally { typedBusy = false; }
  }
  async function save() {
    if (!name.trim() || !tray.length) return;
    saving = true;
    const ml = Number.parseInt(yieldText, 10);
    const body = { name: name.trim(), notes: notes.trim() || null, tags: tags.split(',').map((x) => x.trim()).filter(Boolean),
                   yield_ml: Number.isInteger(ml) && ml >= 10 && ml <= 5000 ? ml : null, family, lines: tray, steps: steps(), lang: $lang };
    try {
      const sid = id ?? (await api.create(body)).id;
      if (id != null) await api.update(id, body);
      showToast({ text: $t('edit.sauce.saved') });
      loadSauces();
      go(`/sauces/${sid}`);
    } catch (e) { showToast({ text: $t(failKey(e)), tone: 'warn' }); } finally { saving = false; }
  }
  async function del() {
    if (!confirmDelete) { confirmDelete = true; setTimeout(() => (confirmDelete = false), 4000); return; }
    try { await api.remove(id!); loadSauces(); go('/sauces'); } catch (e) { showToast({ text: $t(failKey(e)), tone: 'warn' }); }
  }
  // a line's look on the tray: what it is, its colour, whether it has an amount
  const lineFill = (l: SauceLine) => (l.shelf ? items.get(l.shelf)?.fill : l.spice ? jars.get(l.spice)?.fill
    : l.blend !== undefined ? $blendList.find((b) => b.id === l.blend)?.jar_fill : undefined) ?? '#E8DCC4';
  const lineName = (l: SauceLine) => (l.shelf ? names[l.shelf] : l.spice ? names[l.spice] : l.blend !== undefined ? blendNames[l.blend] : l.raw) ?? '';
  let familyName = $derived(family ? $shelves?.families.find((f) => f.id === family)?.[$lang] : e?.family?.[$lang]);
</script>

{#snippet famChip(where: string)}
  <button class="hbtn fam {where} pressable" class:mine={!!family} onclick={() => (sheetOpen = true)} aria-label={$t('edit.sauce.family')}>
    <span class="fl">{familyName ?? $t('sauce.family.none')}</span><small>{family ? $t('edit.sauce.family') : $t('edit.sauce.family.auto')}</small>
  </button>
{/snippet}

<div class="screen">
  <PageHeader title={$t(id == null ? 'edit.sauce.new' : 'edit.sauce.title')} icon="sauces" color={P.teal}
              back={() => go(id == null ? '/sauces' : `/sauces/${id}`)}>
    <input class="name hname" bind:value={name} use:osk maxlength="80" placeholder={$t('edit.sauce.name.ph')} aria-label={$t('edit.sauce.name')} />
    {@render famChip('hfam')}
    {#if id != null}<button class="hbtn del pressable" class:armed={confirmDelete} onclick={del}>{confirmDelete ? $t('sauce.delete.confirm') : $t('sauce.delete')}</button>{/if}
    <button class="hbtn save pressable" disabled={saving || !name.trim() || !tray.length} onclick={save}>✓ {$t('edit.save')}</button>
  </PageHeader>
  {#if $shelves && $rack}
    <div class="body">
      <section class="left">
        <!-- on a phone the name and the family chip live here (the header has room for Delete and Save only) -->
        <div class="bhead"><input class="name bname" bind:value={name} use:osk maxlength="80" placeholder={$t('edit.sauce.name.ph')} aria-label={$t('edit.sauce.name')} />
          {@render famChip('bfam')}</div>
        <div class="tabs" role="tablist">
          {#each $shelves.shelves as s, i (s.id)}
            <button class="tab pressable" class:on={tab === i} role="tab" aria-selected={tab === i} onclick={() => (tab = i)}>
              <span class="tsw" style:background={s.items[0]?.fill}></span>{s[$lang]}
            </button>
          {/each}
          <button class="tab pressable" class:on={tab === BLENDS} role="tab" aria-selected={tab === BLENDS} onclick={() => (tab = BLENDS)}>{$t('edit.sauce.blends')}</button>
          <button class="tab pressable" class:on={tab === SPICES} role="tab" aria-selected={tab === SPICES} onclick={() => (tab = SPICES)}>{$t('edit.sauce.spices')}</button>
          <button class="tab pressable" class:on={tab === NOTES} role="tab" aria-selected={tab === NOTES} onclick={() => (tab = NOTES)}>{$t('edit.sauce.notes.tab')}</button>
        </div>
        <div class="shelf" class:gone={tab === NOTES}>
          <!-- the rack's seven shelves, under the Spices tab: inside the shelf (always there, shown by class) — a row
               that came and went above it moved the whole shelf (a layout shift on every tab tap) -->
          <div class="subtabs" class:gone={tab !== SPICES}>
            {#each $rack.shelves as s, i (s.id)}
              <button class="sub pressable" class:on={rackShelf === i} onclick={() => (rackShelf = i)}>{s[$lang]}</button>
            {/each}
          </div>
          {#each Array(slots) as _, k (k)}
            {@const sl = onTab[k]}
            {@const has = !!sl && inTray.has(sl.key)}
            <button class="it pressable" class:vacant={!sl} class:in={has} class:hop={!!sl && hopped === sl.key} disabled={!sl}
                    onclick={() => { if (sl) add(sl.line); }} aria-label={sl?.label ?? ''}>
              <span class="dab" class:gone={!sl || sl.jar} style:background={sl?.fill}></span>
              <span class="mj" class:gone={!sl || !sl.jar}><MiniJar fill={sl?.fill} size={38} /></span>
              <span class="il">{sl?.label ?? ''}</span>
              <span class="tick" class:shown={has} aria-hidden="true"></span>
              <span class="lbl-gf" class:gone={!sl?.gf}>{$t('chip.check')}</span>
            </button>
          {/each}
          <p class="none" class:gone={tab !== BLENDS || $blendList.length > 0}>{$t('edit.sauce.blends.none')}</p>
        </div>
        <div class="notes" class:gone={tab !== NOTES}>
          <label>{$t('edit.sauce.steps')}<textarea bind:value={stepsText} use:osk rows="5" maxlength="8000"></textarea></label>
          <label>{$t('edit.sauce.notes')}<textarea bind:value={notes} use:osk rows="3" maxlength="4000"></textarea></label>
          <div class="row2">
            <label>{$t('edit.sauce.yield')}<input bind:value={yieldText} use:osk inputmode="numeric" maxlength="4" /></label>
            <label>{$t('edit.sauce.tags')}<input bind:value={tags} use:osk /></label>
          </div>
        </div>
        <div class="tray">
          <span class="th">{$t('edit.sauce.tray')} · {tray.length}/{max}</span>
          <div class="cards">
            <!-- first in the row, always: a line of its own typed in (the keyboard opens) -->
            <button class="card typed pressable" onclick={() => (typedOpen = true)}><b aria-hidden="true">✎</b><span class="cn">{$t('edit.sauce.typed')}</span></button>
            <!-- a fixed pool of as many cards as a sauce holds (vacant ones hidden): a line landing only fills a card -->
            {#each pool(tray, max) as l, k (k)}
              {@const amount = !!l && l.qty !== undefined && !!l.unit}
              {@const flips = !!l && unitsOf(l, items).length > 1}
              <div class="card" class:vacant={!l} class:raw={!!l && !amount} class:on={!!l && !!about(l) && focus === about(l)}>
                <button class="st pressable" class:gone={!amount} disabled={!amount} aria-label={$t('sauce.less')} onclick={() => step(k, -1)}>−</button>
                <button class="cb pressable" disabled={!l} use:longpress={{ onlong: () => { if (tray[k]) tray = trayDrop(tray, k); } }}
                        onclick={() => { const a = l ? about(l) : null; if (a) focus = focus === a ? null : a; }} aria-label={l ? lineName(l) : ''}>
                  <span class="dot" style:background={l ? lineFill(l) : 'transparent'}></span>
                  <span class="cn">{l ? lineName(l) : ''}</span>
                  <span class="ring" aria-hidden="true"></span>
                </button>
                <button class="un pressable" class:gone={!amount} class:still={!flips} disabled={!flips} aria-label={$t('edit.sauce.unit')} onclick={() => flip(k)}>
                  {amount ? fmtAmount(l!.qty!, l!.unit!, $shelves.units, $lang) : ''}
                </button>
                <button class="st pressable" class:gone={!amount} disabled={!amount} aria-label={$t('sauce.more')} onclick={() => step(k, 1)}>+</button>
              </div>
            {/each}
            <p class="empty" class:gone={tray.length > 0}>{$t('edit.sauce.tray.empty')}</p>
            {#each pool(suggest, 3) as s, k (k)}
              <button class="card try pressable" class:vacant={!s} disabled={!s} onclick={() => { if (s) addItem(s); }}>
                <span class="tl">{$t('edit.sauce.try')}</span>
                <span class="dot" style:background={s ? items.get(s)?.fill : 'transparent'}></span>
                <span class="cn">{s ? names[s] : ''}</span>
                <b class="plus" aria-hidden="true">+</b>
              </button>
            {/each}
          </div>
          <span class="hint" class:blank={!tray.length}>{$t('edit.sauce.hold')}</span>
        </div>
      </section>
      <section class="right" bind:this={panel}>
        <SauceEvalPanel {e} shelves={$shelves} {names} mode="tabs" {focus} busy={$busy} {ghost} mascotSize={88} emptyText={$t('edit.sauce.pick')} />
      </section>
    </div>
    <ScoreDock score={e?.score ?? null} word={e?.word ?? null} text={e ? e.word_text[$lang] : $t('edit.sauce.pick')} target={panel} label={$t('edit.dock')} />
    <!-- the two sheets are built with the page and shown by class: opening one builds nothing -->
    <div class="sheet top" class:gone={!typedOpen} role="dialog" aria-label={$t('edit.sauce.typed')}>
      <div class="box">
        <h3>{$t('edit.sauce.typed')}</h3>
        <input class="tin" bind:value={typedText} use:osk maxlength="200" placeholder={$t('edit.sauce.typed.ph')}
               onkeydown={(ev2) => { if (ev2.key === 'Enter') addTyped(); }} />
        <div class="na">
          <button class="hbtn save pressable" disabled={typedBusy || !typedText.trim()} onclick={addTyped}>{$t('edit.sauce.typed.add')}</button>
          <button class="hbtn pressable" onclick={() => { typedOpen = false; typedText = ''; }}>{$t('edit.sauce.family.close')}</button>
        </div>
      </div>
    </div>
    <div class="sheet" class:gone={!sheetOpen} role="dialog" aria-label={$t('edit.sauce.family.pick')}>
      <div class="box wide">
        <div class="sh"><h3>{$t('edit.sauce.family.pick')}</h3>
          <button class="hbtn pressable" class:on={!family} onclick={() => { family = null; sheetOpen = false; }}>{$t('edit.sauce.family.detect')}</button>
          <button class="hbtn pressable" onclick={() => (sheetOpen = false)}>{$t('edit.sauce.family.close')}</button></div>
        <div class="tree"><FamilyTree families={$shelves.families} path={e?.family?.path ?? []} lang={$lang} chosen={family}
                                      onpick={(f) => { family = f; sheetOpen = false; }} /></div>
      </div>
    </div>
  {/if}
</div>

<style>
  .screen { height: 100%; display: flex; flex-direction: column; position: relative; }
  .hbtn { min-height: var(--touch); min-width: var(--touch); padding: 0 16px; border-radius: 999px; border: var(--outline) solid var(--ink);
          background: var(--paper); font-weight: 800; font-size: 15px; white-space: nowrap; }
  .hbtn.save { background: var(--herb); color: var(--ink); font-weight: 900; }
  .hbtn.save:disabled { opacity: .5; }
  .hbtn.del.armed { background: var(--tomato); color: var(--ink); }
  .hbtn.on { background: var(--butter); }
  .hbtn.fam { display: flex; flex-direction: column; justify-content: center; line-height: 1.05; max-width: 190px; padding: 0 14px; }
  .hbtn.fam .fl { overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
  .hbtn.fam small { font-size: 10.5px; font-weight: 900; text-transform: uppercase; opacity: .7; }
  .hbtn.fam.mine { background: var(--butter); }
  /* an explicit row (with an auto row the grid measured both panes whenever either changed) */
  .body { flex: 1; min-height: 0; display: grid; grid-template-columns: minmax(0, 56%) minmax(0, 1fr); grid-template-rows: minmax(0, 1fr); }
  .left { min-height: 0; display: flex; flex-direction: column; gap: 8px; padding: 10px 12px 10px 18px; border-right: var(--outline) dashed #E2D6C4; }
  .right { min-height: 0; padding: 10px 16px 0 14px; display: flex; flex-direction: column; }
  .name { flex: none; height: var(--touch); border: var(--outline) solid var(--ink); border-radius: var(--r-sm); padding: 0 14px; font: inherit;
          font-family: var(--font-display); font-size: 20px; background: var(--paper); color: var(--ink); }
  .hname { width: 250px; } .bhead { display: none; } .bname { flex: 1; min-width: 0; }
  .tabs, .subtabs { flex: none; display: flex; gap: 6px; overflow-x: auto; scrollbar-width: none; }
  .subtabs { grid-column: 1 / -1; align-self: center; }
  .tab { flex: none; min-height: var(--touch); min-width: var(--touch); padding: 0 12px; display: flex; align-items: center; gap: 6px;
         border: var(--outline) solid var(--ink); border-radius: var(--r-sm); background: var(--paper); font-weight: 800; font-size: 13.5px; white-space: nowrap; }
  .tab.on { background: var(--ink); color: #fff; }
  .tsw { width: 14px; height: 14px; border-radius: 50%; border: 2px solid currentColor; }
  .sub { flex: none; min-height: var(--touch); min-width: var(--touch); padding: 0 12px; border: 2.5px solid var(--ink); border-radius: 999px;
         background: var(--cream); font-weight: 800; font-size: 13px; white-space: nowrap; }
  .sub.on { background: var(--butter); }
  .shelf { flex: 1; min-height: 0; overflow-y: auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(84px, 1fr)); grid-auto-rows: 96px; gap: 6px; align-content: start; }
  .it { contain: content; position: relative; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px; padding: 2px;
        border: 2.5px solid var(--ink); border-radius: var(--r-sm); background: var(--paper); min-height: var(--touch); }
  .it.in { background: var(--cream); opacity: .7; }
  .it.vacant, .card.vacant, .gone { display: none !important; }
  .it.hop .dab, .it.hop .mj { animation: hop .5s cubic-bezier(.3, 1.6, .5, 1); }
  @keyframes hop { 0% { transform: none; } 40% { transform: translateY(-12px) scale(1.08); } 100% { transform: none; } }
  /* a dab of the item, drawn in CSS: its colour, a shine (an svg per slot would be one more thing to build) */
  .dab { width: 38px; height: 38px; border-radius: 46% 54% 50% 50% / 56% 50% 50% 44%; border: 2.5px solid var(--ink);
         background-image: radial-gradient(circle at 32% 30%, rgba(255, 255, 255, .55) 0 18%, transparent 19%); }
  .mj { display: block; }
  .il { font-weight: 800; font-size: 11.5px; line-height: 1.05; text-align: center; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; }
  .tick { position: absolute; top: 4px; right: 4px; width: 22px; height: 22px; background: var(--herb); border: 2px solid var(--ink); border-radius: 50%; opacity: 0; }
  .tick::after { content: ''; position: absolute; left: 6px; top: 2px; width: 5px; height: 10px; border: solid var(--ink); border-width: 0 3px 3px 0; transform: rotate(45deg); }
  .tick.shown { opacity: 1; }
  .lbl-gf { position: absolute; top: 3px; left: 3px; background: var(--butter); border: 2px solid var(--ink); border-radius: 999px; font-size: 9.5px; font-weight: 900; padding: 0 4px; }
  .none { grid-column: 1 / -1; margin: 6px 2px; font-weight: 800; font-size: 14px; opacity: .7; }
  .notes { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 10px; overflow-y: auto; padding-bottom: calc(var(--kb-h) + 10px); }
  .notes label { display: flex; flex-direction: column; gap: 4px; font-weight: 800; font-size: 14px; }
  .notes textarea, .notes input, .tin { border: var(--outline) solid var(--ink); border-radius: var(--r-sm); padding: 10px 14px; font: inherit; font-weight: 600; font-size: 17px; background: var(--paper); }
  .notes input, .tin { min-height: var(--touch); }
  .row2 { display: grid; grid-template-columns: 150px 1fr; gap: 10px; }
  .tray { flex: none; background: var(--cream); border: var(--outline) solid var(--ink); border-radius: var(--r); padding: 6px 8px 6px; }
  .th { display: block; font-weight: 900; font-size: 13px; margin: 0 2px 4px; }
  .card.typed { border-style: dashed; background: transparent; min-height: var(--touch); width: 112px; padding: 4px 8px; align-self: stretch; gap: 6px;
                animation: none; }
  .card.typed b { font-size: 22px; line-height: 1; }
  /* a fixed height (the hint and a row of cards differed by a few pixels, and the shelf above was repainted) */
  .cards { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 4px; height: 82px; align-items: center; contain: layout paint; }
  .card { contain: content; flex: none; display: flex; align-items: center; gap: 4px; background: var(--paper); border: 2.5px solid var(--ink); border-radius: var(--r-sm);
          padding: 3px; animation: land .45s cubic-bezier(.3, 1.6, .5, 1) backwards; }
  @keyframes land { from { transform: translateY(16px) scale(.85); opacity: 0; } }
  .card.on { background: var(--butter); }
  .card.raw { border-style: dashed; }
  .card.raw .cn { font-style: italic; }
  .cb { position: relative; min-height: var(--touch); min-width: var(--touch); width: 96px; display: flex; align-items: center; gap: 5px; padding: 0 2px;
        background: none; border: 0; text-align: left; }
  .card.raw .cb { width: 150px; }
  .dot { flex: none; width: 20px; height: 20px; border-radius: 50%; border: 2px solid var(--ink); }
  .cn { font-weight: 800; font-size: 11.5px; line-height: 1.05; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 3; line-clamp: 3; -webkit-box-orient: vertical; }
  .ring { position: absolute; inset: 2px; border: 3px solid var(--tomato); border-radius: var(--r-sm); opacity: 0; transform: scale(.6); pointer-events: none; }
  .cb:global(.holding) .ring { animation: hold .6s linear forwards; }
  @keyframes hold { to { opacity: 1; transform: none; } }
  .st { flex: none; width: var(--touch); height: var(--touch); border-radius: var(--r-sm); border: var(--outline) solid var(--ink); background: var(--cream);
        font-size: 28px; font-weight: 900; line-height: 1; }
  .un { flex: none; min-width: var(--touch); height: var(--touch); padding: 0 6px; border-radius: var(--r-sm); border: 2.5px solid var(--ink); background: var(--butter);
        font-family: var(--font-display); font-size: 16px; line-height: 1; white-space: nowrap; }
  .un.still { background: var(--paper); border-style: dotted; }
  .un:disabled { opacity: 1; }
  .card.try { border-style: dashed; background: transparent; flex-direction: row; align-items: center; min-height: var(--touch); padding: 4px 8px; align-self: stretch; }
  .card.try .cn { max-width: 80px; }
  .tl { font-size: 10.5px; font-weight: 900; text-transform: uppercase; writing-mode: vertical-rl; transform: rotate(180deg); opacity: .7; }
  .plus { font-size: 24px; font-weight: 900; line-height: 1; }
  .empty { margin: 0 4px; font-weight: 800; font-size: 14px; opacity: .65; }
  .hint { display: block; font-weight: 700; font-size: 11.5px; opacity: .6; margin: 2px 2px 0; }
  .hint.blank { visibility: hidden; }
  .sheet { position: absolute; inset: 0; background: rgba(31, 26, 23, .35); display: grid; place-items: center; z-index: 20; }
  /* above the on-screen keyboard, which rises from the bottom when the field is focused */
  .sheet.top { place-items: start center; padding-top: 70px; }
  .box { width: min(560px, 92%); display: flex; flex-direction: column; gap: 10px; background: var(--paper); border: var(--outline) solid var(--ink);
         border-radius: var(--r); box-shadow: var(--shadow); padding: 16px; }
  .box.wide { width: min(980px, 96%); max-height: 92%; }
  .box h3 { margin: 0; font-size: 20px; }
  .sh { display: flex; align-items: center; gap: 8px; } .sh h3 { flex: 1; }
  .tree { min-height: 0; overflow-y: auto; }
  .na { display: flex; gap: 8px; }
  @media (max-aspect-ratio: 1/1) {
    .body { grid-template-columns: minmax(0, 1fr); grid-template-rows: max-content max-content; overflow-y: auto; }
    .hname, .hbtn.fam.hfam { display: none; } .bhead { display: flex; gap: 8px; align-items: center; }
    .left { border: 0; min-height: auto; } .shelf { flex: none; max-height: 330px; } .right { height: 640px; min-height: auto; }
    .body { padding-bottom: 84px; }   /* room for the score dock */
    /* the tray as a list, a line per row: in a sideways strip a phone showed two of sixteen and hid the rest */
    .cards { flex-wrap: wrap; height: auto; overflow-x: visible; align-items: stretch; }
    .card { flex: 1 1 100%; min-width: 0; } .card .cb { flex: 1 1 auto; min-width: 0; }   /* the + at the row's end */
  }
</style>
