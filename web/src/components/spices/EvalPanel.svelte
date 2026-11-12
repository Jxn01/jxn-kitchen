<script lang="ts">
  // Everything the spice engine says about a blend, laid out for reading: the ring, the mascot's face and the radar
  // on top, then the Why ledger, the harmony web, the goes-with board, timing and heat, the nearest classics and the
  // cuisines. `tabs` (the editor): one section at a time under segment buttons. `scroll` (the blend's page): all of them.
  //
  // Built ONCE: the panel exists before the first jar (`e` null = the empty shape),
  // and every section is mounted when the page opens — a tap never creates a component (creating the panel on the
  // first jar cost a 450 ms frame, mounting a section on its first tab 170–320 ms). Every section follows every
  // evaluation (keyed lists: only what is new is created) — see `held` — so a tab tap only flips opacity. Letting a
  // hidden section catch up only when shown made the tap pay for all of it at once (168 ms on the timing lanes).
  import { untrack } from 'svelte';
  import Mascot from '../Mascot.svelte';
  import ScoreRing from './ScoreRing.svelte';
  import Radar from './Radar.svelte';
  import Ledger from './Ledger.svelte';
  import HarmonyWeb from './HarmonyWeb.svelte';
  import FoodBoard from './FoodBoard.svelte';
  import TimingStrip from './TimingStrip.svelte';
  import HeatGauge from './HeatGauge.svelte';
  import ClassicsList from './ClassicsList.svelte';
  import CuisineBars from './CuisineBars.svelte';
  import { EMPTY_EVALUATION, jarIndex, ledgerFor, WORD_FACE, type Evaluation, type Finding, type Rack, type Word } from '../../lib/spices';
  import { lang, t } from '../../lib/i18n';

  let { e = null, rack, mode = 'scroll', focus = null, busy = false, ghost = null, mascotSize = 96, emptyText = '' }:
    { e?: Evaluation | null; rack: Rack; mode?: 'tabs' | 'scroll'; focus?: string | null; busy?: boolean;
      ghost?: Record<string, number> | null; mascotSize?: number; emptyText?: string } = $props();

  const SECTIONS = ['why', 'web', 'foods', 'timing', 'classics'] as const;
  type Section = typeof SECTIONS[number];
  let tab = $state<Section>('why');
  let picked = $state<Finding | null>(null);
  let cur = $derived(e ?? EMPTY_EVALUATION);
  // Every section follows every evaluation, ONE PER FRAME: the ring, the face and the radar take the frame the answer
  // lands in, the section on screen the next, then each hidden one in a frame of its own. All of it in one frame (the
  // first jar: the head, a ledger built from no rows and the tray's suggestions) cost 84–184 ms on the kiosk; timers a
  // fixed 70 ms apart still fired back to back when the Atom was busy and stacked two sections in one frame (84 ms).
  // A tab tap shows a section that is already up to date (or brings it up first).
  const first = untrack(() => e ?? EMPTY_EVALUATION);   // server rendering runs no effects: start with what we were given
  let held = $state.raw<Record<Section, Evaluation>>({ why: first, web: first, foods: first, timing: first, classics: first });
  $effect(() => {
    const now = cur;
    if (mode === 'scroll') { held = { why: now, web: now, foods: now, timing: now, classics: now }; return; }
    if (!e) return;            // an emptied tray: the sections are hidden behind the hint — keep what they show, redraw nothing
    const visible = untrack(() => tab);
    const order = [visible, ...SECTIONS.filter((s) => s !== visible)];
    const bring = (s: Section) => { if (held[s] !== now) held = { ...held, [s]: now }; };
    // a timer started inside a frame runs after that frame is drawn: each section lands in the frame after the last
    let raf = 0, later: ReturnType<typeof setTimeout> | undefined, gone = false;
    const step = (i: number) => {
      if (gone || i >= order.length) return;
      raf = requestAnimationFrame(() => { later = setTimeout(() => { bring(order[i]); step(i + 1); }, 0); });
    };
    step(0);
    return () => { gone = true; cancelAnimationFrame(raf); clearTimeout(later); };
  });
  $effect(() => { const t = tab; if (mode === 'tabs' && untrack(() => held[t]) !== untrack(() => cur)) held = { ...untrack(() => held), [t]: untrack(() => cur) }; });
  let jars = $derived(jarIndex(rack));
  let names = $derived(Object.fromEntries([...jars].map(([id, j]) => [id, j.label[$lang]])));
  let fills = $derived(Object.fromEntries([...jars].map(([id, j]) => [id, j.fill])));
  let pair = $derived<[string, string] | null>(picked && picked.about.length >= 2 ? [picked.about[0], picked.about[1]] : null);
  $effect(() => { if (picked && !cur.findings.some((f) => f.id === picked!.id)) picked = null; });

  // the mascot reacts once when the word changes (episodic), and keeps the face of the word
  let m: Mascot | undefined = $state();
  let lastWord: Word | null = null;
  $effect(() => {
    if (!e) { lastWord = null; return; }
    const w = e.word;
    if (lastWord && w !== lastWord) m?.play(WORD_FACE[w].act);
    lastWord = w;
  });
  // episodic life: blinks and glances for 15 s after each new evaluation, then the face rests until the blend changes
  // (a reading screen left open must cost what a still page costs)
  let alive = $state(true);
  $effect(() => {
    void e;
    alive = true;
    const timer = setTimeout(() => (alive = false), 15000);
    return () => clearTimeout(timer);
  });
  function pick(f: Finding | null) { picked = f; if (f && mode === 'tabs' && f.about.length >= 2) tab = 'web'; }
  // before the first jar nothing is shown but the hint (the sections are built, just not visible)
  const on = (s: Section) => mode === 'scroll' || (!!e && tab === s);
</script>

<div class="panel" class:tabs={mode === 'tabs'}>
  <div class="head">
    <ScoreRing score={e ? e.score : null} word={cur.word} text={e ? e.word_text[$lang] : ''} size={mode === 'tabs' ? 100 : 118} />
    <!-- no continuous breath on a reading screen (it alone kept the page at ~10 % CPU on the kiosk); it blinks and glances
         for 15 s after each change (`alive`) and reacts once when the word changes -->
    <div class="face" class:busy><Mascot bind:this={m} size={mascotSize} expr={e ? WORD_FACE[e.word].expr : 'focus'} breathe={false} {alive} /></div>
    <Radar radar={cur.radar} axes={rack.axes} lang={$lang} {ghost} size={mode === 'tabs' ? 168 : 200} fill={cur.jar_fill} />
  </div>
  <!-- always there (empty and invisible before the first jar), in a box two lines tall: a line that comes and goes, or
       wraps to a second line (three label jars), would shift everything below it, and a layout move repaints the whole
       pane (84 ms on the kiosk when the tray emptied) -->
  <div class="gfbox"><p class="gf {e?.gluten?.status ?? 'ok'}" class:blank={!e?.gluten}>{e?.gluten ? e.gluten[$lang] : '·'}</p></div>

  {#if mode === 'tabs'}
    <div class="seg" role="tablist">
      {#each SECTIONS as s (s)}
        <button class="sg pressable" class:on={tab === s} role="tab" aria-selected={tab === s} onclick={() => (tab = s)}>{$t(`spices.tab.${s}`)}</button>
      {/each}
    </div>
  {/if}

  <div class="body">
    <!-- always there, hidden by the first jar (taking a block out of the grid relaid every section) -->
    <p class="empty" class:blank={!!e || !emptyText}>{emptyText}</p>
    <section class:off={!on('why')}>
      {#if mode === 'scroll'}<h2>{$t('spices.tab.why')}</h2>{/if}
      <Ledger findings={ledgerFor(held.why.findings, focus)} lang={$lang} base={held.why.base} picked={picked?.id ?? null} onpick={pick} />
    </section>
    <section class="center" class:off={!on('web')}>
      {#if mode === 'scroll'}<h2>{$t('spices.tab.web')}</h2>{/if}
      <HarmonyWeb nodes={held.web.web.nodes} edges={held.web.web.edges} {names} {fills} highlight={pair} {focus} size={mode === 'tabs' ? 300 : 340} />
      <!-- three lines kept for it (the longest pair line is two at this width, the hint one): on the blend's page a
           caption that grows moves every section below it -->
      <p class="cap" class:muted={!pair}>{pair ? picked?.[$lang] : $t('spices.web.hint')}</p>
    </section>
    <section class:off={!on('foods')}>
      {#if mode === 'scroll'}<h2>{$t('spices.tab.foods')}</h2>{/if}
      <FoodBoard foods={rack.foods} scored={held.foods.foods} lang={$lang} {names} />
    </section>
    <section class:off={!on('timing')}>
      {#if mode === 'scroll'}<h2>{$t('spices.tab.timing')}</h2>{/if}
      <TimingStrip timing={held.timing.timing} timings={rack.timings} {jars} lang={$lang} />
      <h3>{$t('spices.heat')}</h3>
      <HeatGauge value={held.timing.heat.value} word={held.timing.heat.word} words={rack.heat} lang={$lang} />
    </section>
    <section class:off={!on('classics')}>
      {#if mode === 'scroll'}<h2>{$t('spices.tab.classics')}</h2>{/if}
      <ClassicsList classics={held.classics.classics} {jars} lang={$lang} />
      <h3>{$t('spices.cuisines')}</h3>
      <CuisineBars cuisines={held.classics.cuisines} labels={rack.cuisines} lang={$lang} />
    </section>
  </div>
</div>

<style>
  .panel { display: flex; flex-direction: column; gap: 10px; min-height: 0; min-width: 0; }
  .panel.tabs { height: 100%; }
  .head { display: flex; align-items: center; gap: 6px; justify-content: space-between; flex-wrap: wrap; contain: layout; }
  .face { width: 96px; display: grid; place-items: center; flex: none; }
  .face.busy { opacity: .75; }
  .gfbox { flex: none; height: 47px; display: flex; align-items: center; contain: strict; }   /* 2 lines of 14 px × 1.25 + padding + border */
  .gf { margin: 0; font-weight: 800; font-size: 14px; line-height: 1.25; border: 2px solid var(--ink); border-radius: 16px; padding: 4px 12px; }
  .gf.ok, .gf.yours { border-color: #9BCF9E; color: #2E7D32; background: transparent; }
  .gf.check { background: var(--butter); }
  .gf.blank { visibility: hidden; }
  .seg { display: flex; gap: 6px; flex: none; min-width: 0; }
  .sg { flex: 1 1 0; min-width: var(--touch); min-height: var(--touch); padding: 0 4px; border: var(--outline) solid var(--ink); border-radius: var(--r-sm);
        background: var(--paper); font-weight: 900; font-size: 13.5px; line-height: 1.1; }
  .sg.on { background: var(--ink); color: #fff; }
  .body { display: flex; flex-direction: column; gap: 18px; }
  /* tabs: the five sections share one place, each scrolling on its own; a hidden one is still built (its own layer),
     so showing it repaints nothing that was not already drawn */
  .tabs .body { flex: 1; min-height: 0; display: grid; position: relative; }
  /* contained: one section's update never makes another lay out or repaint */
  .tabs .body > section { grid-area: 1 / 1; min-height: 0; overflow-y: auto; padding-bottom: 12px; will-change: opacity; contain: strict; }
  /* 0.002, not 0: a fully transparent layer is never rasterised, so its first show painted 25 OpenMoji foods during the
     tap (84–151 ms on the kiosk); this faint, it is drawn while hidden and shows for free. Not 1 %: four hidden sections
     stack, and at 1 % their text showed through the one on screen (a classic's "83 %" over the timing lanes) */
  .tabs .body > section.off { opacity: .002; pointer-events: none; }
  .tabs .body > section.off * { pointer-events: none; }
  .empty { margin: 0; font-weight: 800; font-size: 17px; opacity: .7; text-align: center; padding: 14px; }
  .tabs .empty { grid-area: 1 / 1; z-index: 1; background: var(--cream); align-self: start; }
  .empty.blank { visibility: hidden; }
  .panel:not(.tabs) .empty.blank { display: none; }
  section.center { display: flex; flex-direction: column; align-items: center; }
  h2 { font-size: 20px; margin: 0 0 8px; align-self: stretch; }
  h3 { font-size: 15px; margin: 14px 0 6px; }
  .cap { margin: 6px 0 0; font-weight: 700; font-size: 14.5px; text-align: center; max-width: 380px; line-height: 1.3; min-height: 3.9em; }
  .muted { opacity: .65; }
</style>
