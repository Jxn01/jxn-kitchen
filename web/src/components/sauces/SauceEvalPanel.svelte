<script lang="ts">
  // Everything the sauce engine says about a sauce, laid out for reading: the ring, the
  // mascot's face and the taste wheel on top, the gluten line, then Why (the ledger), Balance (the seven tastes, salt,
  // heat), Body & stability (the spoon, the dials), Goes with (the 25 foods) and Keeps (the fridge, the fix-it ledger).
  // `tabs` (the editor): one section at a time under segment buttons. `scroll` (a sauce's page): all of them, and the
  // family tree at the end.
  //
  // Built ONCE, as the spice panel (measured on the kiosk): the panel exists before the first line
  // (`e` null = the empty shape), every section is mounted when the page opens, every list is a fixed pool, and after
  // an answer the sections follow it ONE PER FRAME — the one on screen first.
  import { untrack } from 'svelte';
  import Mascot from '../Mascot.svelte';
  import ScoreRing from '../spices/ScoreRing.svelte';
  import Radar from '../spices/Radar.svelte';
  import Ledger from '../spices/Ledger.svelte';
  import FoodBoard from '../spices/FoodBoard.svelte';
  import HeatGauge from '../spices/HeatGauge.svelte';
  import BodyGauge from './BodyGauge.svelte';
  import StabilityMeter from './StabilityMeter.svelte';
  import KeepsCard from './KeepsCard.svelte';
  import FixList from './FixList.svelte';
  import FamilyTree from './FamilyTree.svelte';
  import { ledgerFor, WORD_FACE, type Word } from '../../lib/engine';
  import { EMPTY_SAUCE_EVALUATION, type SauceEvaluation, type Shelves } from '../../lib/sauces';
  import { badge } from '../../lib/recipes';
  import { lang, t } from '../../lib/i18n';

  let { e = null, shelves, names, mode = 'scroll', focus = null, busy = false, ghost = null, mascotSize = 96, emptyText = '' }:
    { e?: SauceEvaluation | null; shelves: Shelves; names: Record<string, string>; mode?: 'tabs' | 'scroll'; focus?: string | null;
      busy?: boolean; ghost?: Record<string, number> | null; mascotSize?: number; emptyText?: string } = $props();

  const SECTIONS = ['why', 'balance', 'body', 'foods', 'keeps'] as const;
  type Section = typeof SECTIONS[number];
  let tab = $state<Section>('why');
  let cur = $derived(e ?? EMPTY_SAUCE_EVALUATION);
  const first = untrack(() => e ?? EMPTY_SAUCE_EVALUATION);
  let held = $state.raw<Record<Section, SauceEvaluation>>({ why: first, balance: first, body: first, foods: first, keeps: first });
  $effect(() => {
    const now = cur;
    if (mode === 'scroll') { held = { why: now, balance: now, body: now, foods: now, keeps: now }; return; }
    if (!e) return;            // an emptied tray: the sections are hidden behind the hint — keep what they show
    const visible = untrack(() => tab);
    const order = [visible, ...SECTIONS.filter((s) => s !== visible)];
    const bring = (s: Section) => { if (held[s] !== now) held = { ...held, [s]: now }; };
    let raf = 0, later: ReturnType<typeof setTimeout> | undefined, gone = false;
    const step = (i: number) => {
      if (gone || i >= order.length) return;
      raf = requestAnimationFrame(() => { later = setTimeout(() => { bring(order[i]); step(i + 1); }, 0); });
    };
    step(0);
    return () => { gone = true; cancelAnimationFrame(raf); clearTimeout(later); };
  });
  $effect(() => { const s = tab; if (mode === 'tabs' && untrack(() => held[s]) !== untrack(() => cur)) held = { ...untrack(() => held), [s]: untrack(() => cur) }; });

  // the taste wheel is the sauce's SHAPE: its strongest taste at the rim (a mild béchamel was a speck in the middle),
  // floored at a quarter of "fully that taste" so a faint sauce stays small; the Balance tab shows the amounts
  const wheel = (x: Record<string, number>) => {
    const top = Math.max(0.25, ...shelves.taste.map((a) => x[a.id] ?? 0));
    return Object.fromEntries(shelves.taste.map((a) => [a.id, Math.min(1, (x[a.id] ?? 0) / top)]));
  };
  let radar = $derived(wheel(cur.taste));
  let gf = $derived(e?.gluten ? badge(e.gluten.verdict) : null);

  let m: Mascot | undefined = $state();
  let lastWord: Word | null = null;
  $effect(() => {
    if (!e) { lastWord = null; return; }
    const w = e.word;
    if (lastWord && w !== lastWord) m?.play(WORD_FACE[w].act);
    lastWord = w;
  });
  let alive = $state(true);
  $effect(() => {
    void e;
    alive = true;
    const timer = setTimeout(() => (alive = false), 15000);
    return () => clearTimeout(timer);
  });
  const on = (s: Section) => mode === 'scroll' || (!!e && tab === s);
</script>

<div class="panel" class:tabs={mode === 'tabs'}>
  <div class="head">
    <ScoreRing score={e ? e.score : null} word={cur.word} text={e ? e.word_text[$lang] : ''} size={mode === 'tabs' ? 100 : 118} />
    <div class="face" class:busy><Mascot bind:this={m} size={mascotSize} expr={e ? WORD_FACE[e.word].expr : 'focus'} breathe={false} {alive} /></div>
    <Radar radar={radar} axes={shelves.taste} lang={$lang} ghost={ghost ? wheel(ghost) : null} size={mode === 'tabs' ? 168 : 200} fill={cur.fill} />
  </div>
  <!-- always there, two lines tall (a line that comes and goes would shift everything below it) -->
  <div class="gfbox"><p class="gf {gf?.tone ?? 'ok'}" class:blank={!gf}>{gf && e?.gluten ? $t(`recipe.verdict.${e.gluten.verdict.state}`, { n: gf.n }) : '·'}</p></div>

  {#if mode === 'tabs'}
    <div class="seg" role="tablist">
      {#each SECTIONS as s (s)}
        <button class="sg pressable" class:on={tab === s} role="tab" aria-selected={tab === s} onclick={() => (tab = s)}>{$t(`sauce.tab.${s}`)}</button>
      {/each}
    </div>
  {/if}

  <div class="body">
    <p class="empty" class:blank={!!e || !emptyText}>{emptyText}</p>
    <section class:off={!on('why')}>
      {#if mode === 'scroll'}<h2>{$t('sauce.tab.why')}</h2>{/if}
      <Ledger findings={ledgerFor(held.why.findings, focus)} lang={$lang} base={held.why.base} baseKey="sauce.ledger.base" />
    </section>
    <section class:off={!on('balance')}>
      {#if mode === 'scroll'}<h2>{$t('sauce.tab.balance')}</h2>{/if}
      <ul class="tastes">
        {#each shelves.taste as a (a.id)}
          {@const v = held.balance.taste[a.id] ?? 0}
          <li class="taste {a.id}">
            <span class="tl">{a[$lang]}</span>
            <span class="track"><span class="fillbar" class:over={v > 1} style:transform="scaleX({Math.min(1, v / 1.25)})"></span><i class="rim"></i></span>
          </li>
        {/each}
      </ul>
      <p class="saltline"><b>{$t('sauce.salt')}</b> {$t('sauce.salt.pct', { pct: held.balance.salt_pct.toLocaleString($lang === 'hu' ? 'hu-HU' : 'en', { maximumFractionDigits: 2 }) })}</p>
      <h3>{$t('sauce.heat')}</h3>
      <HeatGauge value={held.balance.heat.value} word={held.balance.heat.word} words={shelves.heat} lang={$lang} max={1} />
    </section>
    <section class:off={!on('body')}>
      {#if mode === 'scroll'}<h2>{$t('sauce.tab.body')}</h2>{/if}
      <BodyGauge body={held.body.body} bands={shelves.body} lang={$lang} blank={!e} />
      <h3>{$t('sauce.stability')}</h3>
      <StabilityMeter items={held.body.stability} kinds={shelves.stability} levels={shelves.levels} lang={$lang} blank={!e} />
    </section>
    <section class:off={!on('foods')}>
      {#if mode === 'scroll'}<h2>{$t('sauce.tab.foods')}</h2>{/if}
      <FoodBoard foods={shelves.foods} scored={held.foods.foods} lang={$lang} {names} noneKey="sauce.foods.none" />
    </section>
    <section class:off={!on('keeps')}>
      {#if mode === 'scroll'}<h2>{$t('sauce.tab.keeps')}</h2>{/if}
      <KeepsCard keeps={held.keeps.keeps} classes={shelves.keeps} lang={$lang} blank={!e} />
      <h3>{$t('sauce.fixes')}</h3>
      <FixList fixes={held.keeps.fixes} lang={$lang} />
    </section>
    {#if mode === 'scroll'}
      <section>
        <h2>{$t('sauce.tab.family')}</h2>
        <FamilyTree families={shelves.families} path={cur.family?.path ?? []} lang={$lang} />
      </section>
    {/if}
  </div>
</div>

<style>
  .panel { display: flex; flex-direction: column; gap: 10px; min-height: 0; min-width: 0; }
  .panel.tabs { height: 100%; }
  .head { display: flex; align-items: center; gap: 6px; justify-content: space-between; flex-wrap: wrap; contain: layout; }
  .face { width: 96px; display: grid; place-items: center; flex: none; }
  .face.busy { opacity: .75; }
  .gfbox { flex: none; height: 47px; display: flex; align-items: center; contain: strict; }
  .gf { margin: 0; font-weight: 800; font-size: 14px; line-height: 1.25; border: 2px solid var(--ink); border-radius: 16px; padding: 4px 12px; }
  .gf.ok { border-color: #9BCF9E; background: #EEF8EE; } .gf.swap { background: var(--teal); } .gf.warn { background: var(--butter); }
  .gf.unknown { background: var(--paper); border-style: dashed; }
  .gf.blank { visibility: hidden; }
  .seg { display: flex; gap: 6px; flex: none; min-width: 0; }
  .sg { flex: 1 1 0; min-width: var(--touch); min-height: var(--touch); padding: 0 4px; border: var(--outline) solid var(--ink); border-radius: var(--r-sm);
        background: var(--paper); font-weight: 900; font-size: 13px; line-height: 1.1; }
  .sg.on { background: var(--ink); color: #fff; }
  .body { display: flex; flex-direction: column; gap: 18px; }
  .tabs .body { flex: 1; min-height: 0; display: grid; position: relative; }
  .tabs .body > section { grid-area: 1 / 1; min-height: 0; overflow-y: auto; padding-bottom: 12px; will-change: opacity; contain: strict; }
  /* 0.002, not 0 (a fully transparent layer is never rasterised; its first show paints during the tap) */
  .tabs .body > section.off { opacity: .002; pointer-events: none; }
  .tabs .body > section.off * { pointer-events: none; }
  .empty { margin: 0; font-weight: 800; font-size: 17px; opacity: .7; text-align: center; padding: 14px; }
  .tabs .empty { grid-area: 1 / 1; z-index: 1; background: var(--cream); align-self: start; }
  .empty.blank { visibility: hidden; }
  .panel:not(.tabs) .empty.blank { display: none; }
  h2 { font-size: 20px; margin: 0 0 8px; }
  h3 { font-size: 15px; margin: 14px 0 6px; }
  .tastes { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
  .taste { display: grid; grid-template-columns: 96px 1fr; align-items: center; gap: 8px; contain: content; }
  .tl { font-weight: 800; font-size: 14px; }
  .track { position: relative; height: 22px; border: 2.5px solid var(--ink); border-radius: 999px; background: var(--paper); overflow: hidden; }
  /* the bar is scaled, never resized: the compositor moves it (the rim marks "fully that taste", at 80 %) */
  .fillbar { position: absolute; inset: 0; transform-origin: 0 50%; background: var(--butter); }
  .salt .fillbar { background: #CFE8F2; } .acid .fillbar { background: #E3F28B; } .fat .fillbar { background: #F2D86B; }
  .sweet .fillbar { background: #F7B6C8; } .heat .fillbar { background: #FF826E; } .umami .fillbar { background: #C9A27E; }
  .aromatic .fillbar { background: #9BCF9E; }
  .fillbar.over { background-image: repeating-linear-gradient(45deg, transparent 0 6px, rgba(31, 26, 23, .25) 6px 9px); }
  .rim { position: absolute; top: -2px; bottom: -2px; left: 80%; width: 3px; background: var(--ink); opacity: .55; }
  .saltline { margin: 12px 0 0; font-weight: 800; font-size: 15px; }
</style>
