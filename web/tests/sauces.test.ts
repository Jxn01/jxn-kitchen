import { describe, expect, it, vi } from 'vitest';
import { OfflineError } from '../src/lib/api';
import { createEvaluator, fmtFrac } from '../src/lib/engine';
import {
  baseYield, convert, EMPTY_SAUCE_EVALUATION, familyTree, flipUnit, fmtAmount, fromTyped, fromView, itemIndex, lineKey, nameIndex,
  roundFor, SAUCE_SLOTS, scaleQty, sortSauces, stepAmount, stepOf, trayAdd, trayDrop, traySet, unitsOf, byChip,
  type SauceEvaluation, type SauceLine, type SauceSummary, type Shelves,
} from '../src/lib/sauces';
import shelvesFx from './fixtures/engine-sauce-shelves.json';
import paprikas from './fixtures/engine-sauce-paprikas.json';
import mayonnaise from './fixtures/engine-sauce-mayonnaise.json';
import fights from './fixtures/engine-sauce-fights.json';

const SH = shelvesFx as unknown as Shelves;
const items = itemIndex(SH);
const jars = new Map([['cumin', { g_per_tsp: 2.1 }], ['sweet-paprika', { g_per_tsp: 2.3 }]]);

describe('amounts as the owner reads them', () => {
  it('quarters and halves as fractions, the rest with the language\'s decimal mark', () => {
    expect([0.25, 0.5, 0.75, 1, 1.5, 2.25, 0.3].map((n) => fmtFrac(n, 'en'))).toEqual(['¼', '½', '¾', '1', '1½', '2¼', '0.3']);
    expect(fmtFrac(0.3, 'hu')).toBe('0,3');
  });
  it('an amount is a number and the unit\'s label from the server, in either language', () => {
    expect(fmtAmount(2, 'tbsp', SH.units, 'en')).toBe('2 tbsp');
    expect(fmtAmount(2, 'tbsp', SH.units, 'hu')).toBe('2 ek');
    expect(fmtAmount(0.5, 'tsp', SH.units, 'hu')).toBe('½ tk');
    expect(fmtAmount(1.5, 'dl', SH.units, 'en')).toBe('1.5 dl');
    expect(fmtAmount(1.5, 'dl', SH.units, 'hu')).toBe('1,5 dl');
    expect(fmtAmount(300, 'ml', SH.units, 'en')).toBe('300 ml');
    expect(fmtAmount(27.4, 'g', SH.units, 'en')).toBe('27 g');
    expect(fmtAmount(2, 'pcs', SH.units, 'hu')).toBe('2 db');
  });
});

describe('the units a line can be measured in', () => {
  it('a shelf item: its own unit, then its others; a jar: tsp, tbsp, g; a blend: tsp, tbsp; typed lines: none', () => {
    expect(unitsOf({ shelf: 'sunflower-oil', qty: 2, unit: 'tbsp' }, items)).toEqual(['tbsp', 'ml', 'dl']);
    expect(unitsOf({ spice: 'cumin', qty: 1, unit: 'tsp' }, items)).toEqual(['tsp', 'tbsp', 'g']);
    expect(unitsOf({ blend: 3, qty: 1, unit: 'tsp' }, items)).toEqual(['tsp', 'tbsp']);
    expect(unitsOf({ item: 'ketchup', raw: 'ketchup' }, items)).toEqual([]);
    expect(unitsOf({ raw: 'a splash' }, items)).toEqual([]);
  });
  it('an item with no other unit does not flip', () => {
    const lone = [...items.values()].find((e) => !e.alt.length)!;
    const ln: SauceLine = { shelf: lone.id, qty: lone.default, unit: lone.unit };
    expect(flipUnit(ln, items, jars)).toBe(ln);
  });
  it('flips through every unit of every shelf item and stays a valid amount; flipping all the way round lands within one step', () => {
    for (const e of items.values()) {
      const units = [e.unit, ...e.alt];
      let ln: SauceLine = { shelf: e.id, qty: e.default, unit: e.unit };
      for (let i = 0; i < units.length; i++) {
        ln = flipUnit(ln, items, jars);
        expect(units, e.id).toContain(ln.unit);
        expect(ln.qty!, e.id).toBeGreaterThan(0);
        expect(ln.qty!, e.id).toBeLessThanOrEqual(5000);
      }
      expect(ln.unit, e.id).toBe(e.unit);
      expect(Math.abs(ln.qty! - e.default), e.id).toBeLessThanOrEqual(stepOf(ln, items) + 1e-9);
    }
  });
  it('converts with the server\'s own table: tbsp 15 ml, tsp 5, dl 100, grams by density, pieces by weight', () => {
    const oil = items.get('sunflower-oil')!;
    expect(convert(oil, 2, 'tbsp', 'ml')).toBeCloseTo(30);
    expect(convert(oil, 30, 'ml', 'dl')).toBeCloseTo(0.3);
    const withPc = [...items.values()].find((e) => e.g_per_pc && [e.unit, ...e.alt].includes('g'))!;
    expect(convert(withPc, 1, 'pcs', 'g')).toBeCloseTo(withPc.g_per_pc!);
    const noPc = [...items.values()].find((e) => !e.g_per_pc)!;
    expect(convert(noPc, 1, 'pcs', 'g')).toBeNull();
  });
  it('a jar flips tsp → tbsp → g → tsp', () => {
    let ln: SauceLine = { spice: 'cumin', qty: 1, unit: 'tsp' };
    ln = flipUnit(ln, items, jars); expect(ln).toMatchObject({ unit: 'tbsp' });
    ln = flipUnit(ln, items, jars); expect(ln).toMatchObject({ unit: 'g' });
    ln = flipUnit(ln, items, jars); expect(ln).toMatchObject({ unit: 'tsp', qty: 1 });
  });
});

describe('one tap on ±', () => {
  it('moves by the step, never to 0 (hold the line to take it off) and never past 5000', () => {
    expect(stepAmount(2, 1, 1)).toBe(3);
    expect(stepAmount(1, 1, -1)).toBe(1);
    expect(stepAmount(0.25, 0.25, -1)).toBe(0.25);
    expect(stepAmount(4990, 50, 1)).toBe(5000);
    expect(stepAmount(1.3, 0.5, 1)).toBe(2);        // an odd typed amount lands back on the steps
  });
  it('the item\'s own step in its own unit, a round step in another', () => {
    const oil = items.get('sunflower-oil')!;
    expect(stepOf({ shelf: oil.id, qty: 2, unit: oil.unit }, items)).toBe(oil.step);
    expect(stepOf({ shelf: oil.id, qty: 30, unit: 'ml' }, items)).toBe(10);
    expect(stepOf({ spice: 'cumin', qty: 1, unit: 'tsp' }, items)).toBe(0.25);
  });
  it('rounds a scaled amount to what a cook can measure', () => {
    expect(roundFor('tbsp', 1.13)).toBe(1);
    expect(roundFor('tsp', 0.6)).toBe(0.5);
    expect(roundFor('tsp', 0.01)).toBe(0.25);
    expect(roundFor('g', 27.4)).toBe(27);
    expect(roundFor('dl', 1.234)).toBe(1.2);
    expect(scaleQty(2, 'tbsp', 1.5)).toBe(3);
  });
});

describe('the tray', () => {
  it('a shelf item, a jar and a blend join once; typed lines may repeat; at most max_lines', () => {
    let t: SauceLine[] = [];
    t = trayAdd(t, { shelf: 'olive-oil', qty: 2, unit: 'tbsp' });
    t = trayAdd(t, { shelf: 'olive-oil', qty: 4, unit: 'tbsp' });
    t = trayAdd(t, { spice: 'cumin', qty: 1, unit: 'tsp' });
    t = trayAdd(t, { spice: 'cumin', qty: 1, unit: 'tsp' });
    t = trayAdd(t, { blend: 3, qty: 1, unit: 'tsp' });
    t = trayAdd(t, { blend: 3, qty: 1, unit: 'tsp' });
    t = trayAdd(t, { raw: 'a splash' });
    t = trayAdd(t, { raw: 'a splash' });
    expect(t.map(lineKey)).toEqual(['shelf:olive-oil', 'spice:cumin', 'blend:3', 'raw:a splash', 'raw:a splash']);
    const full = Array.from({ length: SH.max_lines }, (_, i) => ({ raw: `l${i}` }));
    expect(trayAdd(full, { raw: 'one more' }, SH.max_lines)).toBe(full);
  });
  it('sets and drops by place', () => {
    const t: SauceLine[] = [{ raw: 'x' }, { shelf: 'olive-oil', qty: 2, unit: 'tbsp' }];
    expect(traySet(t, 1, { qty: 3 })[1]).toEqual({ shelf: 'olive-oil', qty: 3, unit: 'tbsp' });
    expect(trayDrop(t, 0)).toEqual([{ shelf: 'olive-oil', qty: 2, unit: 'tbsp' }]);
  });
  it('a typed line lands as what it is, keeping its text and how it matched', () => {
    expect(fromTyped({ shelf: 'olive-oil', qty: 3, unit: 'tbsp', raw: '3 ek olívaolaj', match_how: 'exact' }))
      .toEqual({ shelf: 'olive-oil', qty: 3, unit: 'tbsp', raw: '3 ek olívaolaj', match_how: 'exact' });
    expect(fromTyped({ spice: 'cumin', qty: 1, unit: 'tsp', raw: '1 tk kömény', match_how: 'stem' }))
      .toEqual({ spice: 'cumin', qty: 1, unit: 'tsp', match_how: 'stem' });
    expect(fromTyped({ item: 'ketchup', raw: 'ketchup', match_how: 'exact' })).toEqual({ item: 'ketchup', raw: 'ketchup', match_how: 'exact' });
    expect(fromTyped({ raw: 'valami' })).toEqual({ raw: 'valami' });
  });
  it('a saved sauce comes back as the lines that were sent: text, match and the owner\'s GF override kept', () => {
    const view = [
      { pos: 0, kind: 'shelf', shelf_id: 'olive-oil', spice_id: null, blend_id: null, item_id: 'olive-oil', raw: '6 tbsp olive oil', qty: 6, unit: 'tbsp', ok_gf: false, match_how: 'exact' },
      { pos: 1, kind: 'spice', shelf_id: null, spice_id: 'cumin', blend_id: null, item_id: 'cumin', raw: null, qty: 1, unit: 'tsp', ok_gf: true, match_how: null },
      { pos: 2, kind: 'blend', shelf_id: null, spice_id: null, blend_id: 4, item_id: null, raw: null, qty: 2, unit: 'tsp', ok_gf: false, match_how: null },
      { pos: 3, kind: 'off-shelf', shelf_id: null, spice_id: null, blend_id: null, item_id: 'ketchup', raw: 'ketchup', qty: null, unit: null, ok_gf: true, match_how: 'stem' },
      { pos: 4, kind: 'raw', shelf_id: null, spice_id: null, blend_id: null, item_id: null, raw: 'valami', qty: null, unit: null, ok_gf: false, match_how: null },
    ] as Parameters<typeof fromView>[0];
    expect(fromView(view)).toEqual([
      { shelf: 'olive-oil', qty: 6, unit: 'tbsp', raw: '6 tbsp olive oil', match_how: 'exact' },
      { spice: 'cumin', qty: 1, unit: 'tsp', ok_gf: true },
      { blend: 4, qty: 2, unit: 'tsp' },
      { item: 'ketchup', raw: 'ketchup', match_how: 'stem', ok_gf: true },
      { raw: 'valami' },
    ]);
  });
});

describe('the evaluator, on a sauce', () => {
  it('a refused tray (only typed lines weigh nothing: 422) clears the panel; being offline keeps the last answer', async () => {
    vi.useFakeTimers();
    const got: (number | null)[] = [];
    let fail: Error | null = null;
    const send = vi.fn(async (_l: SauceLine[], seq: number) => { if (fail) throw fail; return { seq } as unknown as SauceEvaluation; });
    const e = createEvaluator(send, (x) => got.push(x ? x.seq ?? 0 : null));
    e.schedule([{ shelf: 'olive-oil', qty: 2, unit: 'tbsp' }]);
    await vi.advanceTimersByTimeAsync(300);
    fail = new OfflineError('away');
    e.schedule([{ shelf: 'olive-oil', qty: 3, unit: 'tbsp' }]);
    await vi.advanceTimersByTimeAsync(300);
    expect(got).toEqual([1]);                     // offline: the last good answer stays
    fail = new Error('POST /api/sauces/evaluate -> 422');
    e.schedule([{ raw: 'a splash' }]);
    await vi.advanceTimersByTimeAsync(300);
    expect(got).toEqual([1, null]);               // refused: nothing to say about this tray
    vi.useRealTimers();
  });
  it('a refusal of a request that is no longer the newest changes nothing', async () => {
    vi.useFakeTimers();
    const got: (number | null)[] = [];
    const resolvers: (() => void)[] = [];
    const send = vi.fn((_l: SauceLine[], seq: number) => new Promise<SauceEvaluation>((ok, no) =>
      resolvers.push(seq === 1 ? () => no(new Error('-> 422')) : () => ok({ seq } as unknown as SauceEvaluation))));
    const e = createEvaluator(send, (x) => got.push(x ? x.seq ?? 0 : null));
    e.schedule([{ raw: 'a' }]);
    await vi.advanceTimersByTimeAsync(300);
    e.schedule([{ shelf: 'olive-oil', qty: 2, unit: 'tbsp' }]);
    await vi.advanceTimersByTimeAsync(300);
    resolvers[1](); resolvers[0]();
    await vi.runAllTimersAsync();
    expect(got).toEqual([2]);
    vi.useRealTimers();
  });
});

describe('the families, the sideboard', () => {
  it('forty families in their ten groups, every family once, children under their parent', () => {
    const tree = familyTree(SH.families);
    expect(tree).toHaveLength(10);
    const all: string[] = [];
    const walk = (n: ReturnType<typeof familyTree>[number]) => { all.push(n.id); n.kids.forEach(walk); };
    tree.forEach(walk);
    expect(all.sort()).toEqual(SH.families.map((f) => f.id).sort());
    const emulsions = tree.find((g) => g.id === 'emulsions')!;
    expect(emulsions.kids.find((k) => k.id === 'mayonnaise')!.kids.map((k) => k.id)).toEqual(['aioli', 'tartare']);
  });
  it('filters by chip (a sauce with no family is only under All) and sorts newest or by name', () => {
    const s = (id: number, name: string, chip: string | null, at: string) =>
      ({ id, names: { en: name, hu: name }, family: chip ? { chip } : null, updated_at: at }) as unknown as SauceSummary;
    const list = [s(1, 'Zöld', 'hungarian', '2026-10-20T10:00'), s(2, 'Aioli', 'emulsions', '2026-10-20T12:00'), s(3, 'Mystery', null, '2026-10-20T11:00')];
    expect(byChip(list, 'hungarian').map((x) => x.id)).toEqual([1]);
    expect(byChip(list, null).map((x) => x.id)).toEqual([1, 2, 3]);
    expect(sortSauces(list, 'new', 'en').map((x) => x.id)).toEqual([2, 3, 1]);
    expect(sortSauces(list, 'az', 'hu').map((x) => x.id)).toEqual([2, 3, 1]);
  });
  it('a sauce\'s yield: the owner\'s, else its weight rounded to 50 ml, else 250', () => {
    expect(baseYield({ yield_ml: 400, evaluation: null })).toBe(400);
    expect(baseYield({ yield_ml: null, evaluation: { total_g: 659.6 } as SauceEvaluation })).toBe(650);
    expect(baseYield({ yield_ml: null, evaluation: { total_g: 12 } as SauceEvaluation })).toBe(50);
    expect(baseYield({ yield_ml: null, evaluation: null })).toBe(250);
  });
  it('names every voucher can name: the shelf items and the rack jars', () => {
    const names = nameIndex(SH, [{ id: 'cumin', name: { en: 'Cumin', hu: 'Római kömény' } }], 'hu');
    expect(names['sour-cream']).toBe('Tejföl');
    expect(names.cumin).toBe('Római kömény');
    for (const ev of [paprikas, mayonnaise, fights] as unknown as SauceEvaluation[])
      for (const f of ev.foods) for (const v of f.vouchers) expect(names[v.item], v.item).toBeTruthy();
  });
});

describe('the pools are big enough for anything the engine says', () => {
  it('every fixture fits its pool', () => {
    for (const ev of [paprikas, mayonnaise, fights] as unknown as SauceEvaluation[]) {
      expect(ev.findings.length).toBeLessThanOrEqual(SAUCE_SLOTS.findings);
      expect(ev.stability.length).toBeLessThanOrEqual(SAUCE_SLOTS.stability);
      expect(ev.fixes.length).toBeLessThanOrEqual(SAUCE_SLOTS.fixes);
      expect(ev.suggest.length).toBeLessThanOrEqual(SAUCE_SLOTS.suggest);
      for (const f of ev.foods) expect(f.vouchers.length).toBeLessThanOrEqual(SAUCE_SLOTS.vouchers);
    }
  });
  it('the empty evaluation has every key a real one has', () => {
    expect(Object.keys(EMPTY_SAUCE_EVALUATION).sort()).toEqual(Object.keys(paprikas).filter((k) => k !== 'gluten').sort());
    expect(Object.keys(EMPTY_SAUCE_EVALUATION.taste).sort()).toEqual(SH.taste.map((x) => x.id).sort());
  });
});
