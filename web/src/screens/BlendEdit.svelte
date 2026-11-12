<script lang="ts">
  import { failKey } from '../lib/api';
  // The spice engine. Left: the rack — shelf tabs, the jars of a shelf (tap: onto your tray;
  // hold: the jar's know-how note), and your tray (± in half teaspoons; tap a jar to see only its lines; hold it to put
  // it back), with the engine's suggestions at the end of the tray. Right: the live panel — 300 ms after the last tap
  // the engine reads the blend, and an answer older than the newest request is dropped.
  import { onDestroy } from 'svelte';
  import PageHeader from '../components/PageHeader.svelte';
  import Icon from '../components/Icon.svelte';
  import SpiceJar from '../components/spices/SpiceJar.svelte';
  import EvalPanel from '../components/spices/EvalPanel.svelte';
  import ScoreDock from '../components/ScoreDock.svelte';
  import MiniJar from '../components/spices/MiniJar.svelte';
  import { api, createEvaluator, fmtParts, jarIndex, loadBlends, loadRack, rack, stepParts, trayAdd, trayDrop, traySet,
           pool, SLOTS, type Evaluation, type Jar, type Part } from '../lib/spices';
  import { longpress } from '../lib/longpress';
  import { P } from '../lib/palette';
  import { lang, t } from '../lib/i18n';
  import { go } from '../lib/router';
  import { osk } from '../lib/osk';
  import { showToast } from '../lib/toast';

  let { id = null }: { id?: number | null } = $props();
  let name = $state(''), notes = $state(''), tags = $state('');
  let tray = $state<Part[]>([]);
  let shelf = $state(0);                       // a shelf index, or -1 = the notes tab
  let focus = $state<string | null>(null);
  let e = $state<Evaluation | null>(null);
  let panel = $state<HTMLElement>();
  let ghost = $state<Record<string, number> | null>(null);
  let saving = $state(false), confirmDelete = $state(false);
  let hopped = $state<string | null>(null);
  let noteJar = $state<Jar | null>(null);

  $effect(() => { if (!$rack) loadRack(); });
  $effect(() => {
    if (id == null) return;
    api.get(id).then((b) => { name = b.name; notes = b.notes ?? ''; tags = b.tags.join(', '); tray = b.parts.map((p) => ({ ...p })); })
      .catch((e) => showToast({ text: $t(failKey(e)), tone: 'warn' }));
  });
  let jars = $derived(jarIndex($rack));
  let max = $derived($rack?.max_spices ?? 16);
  // the rack is a fixed set of slots (as many as the fullest shelf), reused by every shelf: a shelf tap only changes
  // what each slot shows — building one shelf's jars and dropping the last one's cost a 168 ms frame on the kiosk
  let slots = $derived(Math.max(0, ...($rack?.shelves ?? []).map((s) => s.jars.length)));
  let onShelf = $derived(shelf >= 0 ? ($rack?.shelves[shelf]?.jars ?? []) : []);
  const ev = createEvaluator<Part, Evaluation>((parts, seq) => api.evaluate(parts, seq), (x) => { ghost = e?.radar ?? null; e = x; });
  const busy = ev.busy;
  $effect(() => { ev.schedule(tray.map((p) => ({ spice: p.spice, parts: p.parts }))); });
  onDestroy(() => ev.cancel());
  $effect(() => { if (focus && !tray.some((p) => p.spice === focus)) focus = null; });
  // the engine's suggestions follow an answer a moment later (gone at once with an emptied tray): three new cards in
  // the frame the answer lands made it one of the kiosk's slowest (84 ms)
  let offered = $state<string[]>([]);
  $effect(() => {
    const s = e?.suggest ?? [];
    if (!s.length) { offered = []; return; }
    const h = setTimeout(() => (offered = s), 450);
    return () => clearTimeout(h);
  });
  let suggest = $derived(offered.filter((s) => !tray.some((p) => p.spice === s)).slice(0, SLOTS.suggest));

  function add(j: string) {
    if (tray.length >= max && !tray.some((p) => p.spice === j)) { showToast({ text: $t('edit.blend.full') }); return; }
    tray = trayAdd(tray, j, max);
    hopped = j; setTimeout(() => { if (hopped === j) hopped = null; }, 600);
  }
  function step(j: string, dir: 1 | -1) {
    const p = tray.find((x) => x.spice === j);
    if (p) tray = traySet(tray, j, stepParts(p.parts, dir));
  }
  async function save() {
    if (!name.trim() || !tray.length) return;
    saving = true;
    const body = { name: name.trim(), notes: notes.trim() || null, parts: tray, tags: tags.split(',').map((x) => x.trim()).filter(Boolean) };
    try {
      const rid = id ?? (await api.create(body)).id;
      if (id != null) await api.update(id, body);
      showToast({ text: $t('edit.blend.saved') });
      loadBlends();
      go(`/spices/${rid}`);
    } catch (e) { showToast({ text: $t(failKey(e)), tone: 'warn' }); } finally { saving = false; }
  }
  async function del() {
    if (!confirmDelete) { confirmDelete = true; setTimeout(() => (confirmDelete = false), 4000); return; }
    try {
      const r = await api.remove(id!);
      if (r.ok) { loadBlends(); go('/spices'); }
      else showToast({ text: $t('blend.inuse', { list: r.sauces.map((s) => s.name).join(', ') }), tone: 'warn' }, 8000);
    } catch (e) { showToast({ text: $t(failKey(e)), tone: 'warn' }); }
  }
</script>

<div class="screen">
  <PageHeader title={$t(id == null ? 'edit.blend.new' : 'edit.blend.title')} icon="spices" color={P.tangerine}
              back={() => go(id == null ? '/spices' : `/spices/${id}`)}>
    <input class="name hname" bind:value={name} use:osk maxlength="80" placeholder={$t('edit.blend.name.ph')} aria-label={$t('edit.blend.name')} />
    {#if id != null}<button class="hbtn del pressable" class:armed={confirmDelete} onclick={del}>{confirmDelete ? $t('blend.delete.confirm') : $t('blend.delete')}</button>{/if}
    <button class="hbtn save pressable" disabled={saving || !name.trim() || !tray.length} onclick={save}>✓ {$t('edit.save')}</button>
  </PageHeader>
  {#if $rack}
    <div class="body">
      <section class="left">
        <input class="name bname" bind:value={name} use:osk maxlength="80" placeholder={$t('edit.blend.name.ph')} aria-label={$t('edit.blend.name')} />
        <div class="tabs" role="tablist">
          {#each $rack.shelves as s, i (s.id)}
            <button class="tab pressable" class:on={shelf === i} role="tab" aria-selected={shelf === i} onclick={() => (shelf = i)}>
              <span class="tsw" style:background={s.jars[0]?.fill}></span>{s[$lang]}
            </button>
          {/each}
          <button class="tab pressable" class:on={shelf === -1} role="tab" aria-selected={shelf === -1} onclick={() => (shelf = -1)}>{$t('edit.blend.notes.tab')}</button>
        </div>
        <!-- the rack and the notes are both always there (a tab shows one): the notes tab dropped and rebuilt every jar -->
        <div class="rack" class:gone={shelf < 0}>
          {#each Array(slots) as _, k (k)}
            {@const j = onShelf[k]}
            {@const inTray = !!j && tray.some((p) => p.spice === j.id)}
            <button class="rj pressable" class:vacant={!j} class:in={inTray} class:hop={!!j && hopped === j.id} disabled={!j}
                    onclick={() => { if (j) add(j.id); }} use:longpress={{ onlong: () => { if (j) noteJar = j; } }} aria-label={j?.label[$lang] ?? ''}>
              <SpiceJar fill={j?.fill} size={48} heat={j?.heat ?? 0} />
              <span class="rl">{j?.label[$lang] ?? ''}</span>
              <span class="tick" class:shown={inTray} aria-hidden="true"></span>
              <span class="lbl-gf" class:gone={j?.gluten !== 'label'}>{$t('chip.check')}</span>
            </button>
          {/each}
        </div>
        <div class="notes" class:gone={shelf >= 0}>
          <label>{$t('edit.blend.notes')}<textarea bind:value={notes} use:osk rows="5" maxlength="4000"></textarea></label>
          <label>{$t('edit.blend.tags')}<input bind:value={tags} use:osk /></label>
        </div>
        <div class="tray">
          <span class="th">{$t('edit.blend.tray')} · {tray.length}/{max}</span>
          <div class="cards">
            <!-- a fixed pool of as many cards as a blend holds, filled in order (vacant ones hidden): a jar landing only
                 fills a card — a card built on every tap was the editor's slowest residue (82–101 ms) -->
            {#each pool(tray, max) as p, k (k)}
              {@const j = p ? jars.get(p.spice) : undefined}
              <div class="card" class:vacant={!p} class:on={!!p && focus === p.spice}>
                <button class="st pressable" disabled={!p} aria-label={$t('blend.less')} onclick={() => { if (p) step(p.spice, -1); }}>−</button>
                <button class="cb pressable" disabled={!p} use:longpress={{ onlong: () => { if (p) tray = trayDrop(tray, p.spice); } }}
                        onclick={() => { if (p) focus = focus === p.spice ? null : p.spice; }} aria-label={j?.label[$lang] ?? p?.spice ?? ''}>
                  <MiniJar fill={j?.fill} size={28} />
                  <span class="cw"><b class="cv">{p ? fmtParts(p.parts) : ''}</b><span class="cn">{j?.label[$lang] ?? p?.spice ?? ''}</span></span>
                  <span class="ring" aria-hidden="true"></span>
                </button>
                <button class="st pressable" disabled={!p} aria-label={$t('blend.more')} onclick={() => { if (p) step(p.spice, 1); }}>+</button>
              </div>
            {/each}
            <p class="empty" class:gone={tray.length > 0}>{$t('edit.blend.tray.empty')}</p>
            <!-- the suggestions are a fixed pool of three cards (hidden when empty): an answer only fills them -->
            {#each pool(suggest, SLOTS.suggest) as s, k (k)}
              {@const j = s ? jars.get(s) : undefined}
              <button class="card try pressable" class:vacant={!s} disabled={!s} onclick={() => { if (s) add(s); }}>
                <span class="tl">{$t('edit.blend.try')}</span>
                <MiniJar fill={j?.fill} size={30} />
                <span class="cn">{j?.label[$lang] ?? s ?? ''}</span>
                <b class="plus" aria-hidden="true">+</b>
              </button>
            {/each}
          </div>
          <!-- always there, hidden on an empty tray: a line that came with the first jar grew the tray and shrank the rack
               above it, and the kiosk laid out and repainted every jar (84–100 ms frames) -->
          <span class="hint" class:blank={!tray.length}>{$t('edit.blend.hold')}</span>
        </div>
      </section>
      <section class="right" bind:this={panel}>
        <!-- always there: before the first jar it shows the empty shape and the hint, so the first tap only updates it -->
        <EvalPanel {e} rack={$rack} mode="tabs" {focus} busy={$busy} {ghost} mascotSize={88} emptyText={$t('edit.blend.pick')} />
      </section>
    </div>
    <ScoreDock score={e?.score ?? null} word={e?.word ?? null} text={e ? e.word_text[$lang] : $t('edit.blend.pick')} target={panel} label={$t('edit.dock')} />
  {/if}
  {#if noteJar}
    <div class="sheet" role="dialog" aria-label={noteJar.label[$lang]}>
      <div class="note">
        <SpiceJar fill={noteJar.fill} size={70} heat={noteJar.heat} />
        <div class="nt">
          <h3>{noteJar.name[$lang]}</h3>
          <p class="tag">{noteJar.tag[$lang]}</p>
          {#if noteJar.note}<p>{noteJar.note[$lang]}</p>{/if}
          <div class="na">
            {#if noteJar.page}<button class="hbtn pressable" onclick={() => go(`/knowhow/${noteJar!.page}`)}>{$t('spices.note.open')}</button>{/if}
            <button class="hbtn edit pressable" onclick={() => { add(noteJar!.id); noteJar = null; }}>{$t('spices.note.add')}</button>
            <button class="hbtn pressable" onclick={() => (noteJar = null)}>{$t('spices.note.close')}</button>
          </div>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .screen { height: 100%; display: flex; flex-direction: column; position: relative; }
  .hbtn { min-height: var(--touch); min-width: var(--touch); padding: 0 16px; border-radius: 999px; border: var(--outline) solid var(--ink);
          background: var(--paper); font-weight: 800; font-size: 15px; white-space: nowrap; }
  .hbtn.save, .hbtn.edit { background: var(--herb); color: var(--ink); font-weight: 900; }
  .hbtn.save:disabled { opacity: .5; }
  .hbtn.del.armed { background: var(--tomato); color: var(--ink); }
  /* an explicit row: with an auto row the grid measured both panes' contents whenever either changed — every answer
     re-laid out the rack and the tray */
  .body { flex: 1; min-height: 0; display: grid; grid-template-columns: minmax(0, 56%) minmax(0, 1fr); grid-template-rows: minmax(0, 1fr); }
  .left { min-height: 0; display: flex; flex-direction: column; gap: 8px; padding: 10px 12px 10px 18px; border-right: var(--outline) dashed #E2D6C4; }
  .right { min-height: 0; padding: 10px 16px 0 14px; display: flex; flex-direction: column; }
  .name { flex: none; height: var(--touch); border: var(--outline) solid var(--ink); border-radius: var(--r-sm); padding: 0 14px; font: inherit;
          font-family: var(--font-display); font-size: 20px; background: var(--paper); color: var(--ink); }
  /* the name lives in the header on the kiosk (a whole row more for the rack), in the pane on a phone */
  .hname { width: 330px; } .bname { display: none; }
  .tabs { flex: none; display: flex; gap: 6px; overflow-x: auto; scrollbar-width: none; }
  .tab { flex: none; min-height: var(--touch); min-width: var(--touch); padding: 0 12px; display: flex; align-items: center; gap: 6px;
         border: var(--outline) solid var(--ink); border-radius: var(--r-sm); background: var(--paper); font-weight: 800; font-size: 13.5px; white-space: nowrap; }
  .tab.on { background: var(--ink); color: #fff; }
  .tsw { width: 14px; height: 14px; border-radius: 4px; border: 2px solid currentColor; }
  .rack { flex: 1; min-height: 0; overflow-y: auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(84px, 1fr)); grid-auto-rows: 104px; gap: 6px; align-content: start; }
  .rj { contain: content; position: relative; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px; padding: 2px;
        border: 2.5px solid var(--ink); border-radius: var(--r-sm); background: var(--paper); min-height: var(--touch); }
  .rj.in { background: var(--cream); opacity: .7; }
  .rj.vacant, .card.vacant, .gone { display: none !important; }
  .rj.hop :global(.jar) { animation: hop .5s cubic-bezier(.3, 1.6, .5, 1); }
  @keyframes hop { 0% { transform: none; } 40% { transform: translateY(-14px) scale(1.08); } 100% { transform: none; } }
  .rl { font-weight: 800; font-size: 11.5px; line-height: 1.05; text-align: center; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; }
  /* drawn in CSS and always there (shown by opacity): an OpenMoji check created on every tap cost ~400 ms on the kiosk */
  .tick { position: absolute; top: 4px; right: 4px; width: 22px; height: 22px; background: var(--herb); border: 2px solid var(--ink);
          border-radius: 50%; opacity: 0; }
  .tick::after { content: ''; position: absolute; left: 6px; top: 2px; width: 5px; height: 10px; border: solid var(--ink);
                 border-width: 0 3px 3px 0; transform: rotate(45deg); }
  .tick.shown { opacity: 1; }
  .plus { font-size: 24px; font-weight: 900; line-height: 1; }
  .lbl-gf { position: absolute; top: 3px; left: 3px; background: var(--butter); border: 2px solid var(--ink); border-radius: 999px; font-size: 9.5px; font-weight: 900; padding: 0 4px; }
  .notes { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 10px; overflow-y: auto; padding-bottom: calc(var(--kb-h) + 10px); }
  .notes label { display: flex; flex-direction: column; gap: 4px; font-weight: 800; font-size: 14px; }
  .notes textarea, .notes input { border: var(--outline) solid var(--ink); border-radius: var(--r-sm); padding: 10px 14px; font: inherit; font-weight: 600; font-size: 17px; background: var(--paper); }
  .notes input { min-height: var(--touch); }
  .tray { flex: none; background: var(--cream); border: var(--outline) solid var(--ink); border-radius: var(--r); padding: 6px 8px 6px; }
  .th { display: block; font-weight: 900; font-size: 13px; margin: 0 2px 4px; }
  /* a fixed height: the hint and a row of cards differed by a few pixels, so the first jar and an emptied tray resized
     the rack above and repainted all its jars (84 ms frames on the kiosk) */
  .cards { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 4px; height: 82px; align-items: center; contain: layout paint; }
  .card { contain: content; flex: none; display: flex; align-items: center; gap: 4px; background: var(--paper); border: 2.5px solid var(--ink); border-radius: var(--r-sm);
          padding: 3px; animation: land .45s cubic-bezier(.3, 1.6, .5, 1) backwards; }
  @keyframes land { from { transform: translateY(16px) scale(.85); opacity: 0; } }
  .card.on { background: var(--butter); }
  .cb { position: relative; min-height: var(--touch); min-width: var(--touch); width: 92px; display: flex; align-items: center; gap: 4px; padding: 0 2px;
        background: none; border: 0; text-align: left; }
  .cw { display: flex; flex-direction: column; min-width: 0; }
  .cn { font-weight: 800; font-size: 11.5px; line-height: 1.05; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; }
  .cv { font-family: var(--font-display); font-weight: 400; font-size: 19px; line-height: 1; }
  .ring { position: absolute; inset: 2px; border: 3px solid var(--tomato); border-radius: var(--r-sm); opacity: 0; transform: scale(.6); pointer-events: none; }
  .cb:global(.holding) .ring { animation: hold .6s linear forwards; }
  @keyframes hold { to { opacity: 1; transform: none; } }
  .st { flex: none; width: var(--touch); height: var(--touch); border-radius: var(--r-sm); border: var(--outline) solid var(--ink); background: var(--cream);
        font-size: 28px; font-weight: 900; line-height: 1; }
  .card.try { border-style: dashed; background: transparent; flex-direction: row; align-items: center; min-height: var(--touch); padding: 4px 8px; align-self: stretch; }
  .tl { font-size: 10.5px; font-weight: 900; text-transform: uppercase; writing-mode: vertical-rl; transform: rotate(180deg); opacity: .7; }
  .empty { margin: 0 4px; font-weight: 800; font-size: 14px; opacity: .65; }
  .hint { display: block; font-weight: 700; font-size: 11.5px; opacity: .6; margin: 2px 2px 0; }
  .hint.blank { visibility: hidden; }
  .sheet { position: absolute; inset: 0; background: rgba(31, 26, 23, .35); display: grid; place-items: center; z-index: 20; }
  .note { width: min(560px, 92%); display: flex; gap: 14px; background: var(--paper); border: var(--outline) solid var(--ink); border-radius: var(--r); box-shadow: var(--shadow); padding: 16px; }
  .nt { flex: 1; min-width: 0; } .nt h3 { margin: 0; font-size: 22px; } .tag { margin: 2px 0 6px; font-weight: 800; opacity: .7; }
  .nt p { line-height: 1.4; font-weight: 600; }
  .na { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
  @media (max-aspect-ratio: 1/1) {
    /* stacked: each pane as tall as its content (min-height: 0 would let a grid row shrink under it and overlap) */
    .body { grid-template-columns: minmax(0, 1fr); grid-template-rows: max-content max-content; overflow-y: auto; }
    .hname { display: none; } .bname { display: block; }
    .left { border: 0; min-height: auto; } .rack { flex: none; max-height: 330px; } .right { height: 640px; min-height: auto; }
    .body { padding-bottom: 84px; }   /* room for the score dock */
    /* the tray as a list, a line per row: in a sideways strip a phone showed two of sixteen and hid the rest */
    .cards { flex-wrap: wrap; height: auto; overflow-x: visible; align-items: stretch; }
    .card { flex: 1 1 100%; min-width: 0; } .card .cb { flex: 1 1 auto; min-width: 0; }   /* the + at the row's end */
  }
</style>
