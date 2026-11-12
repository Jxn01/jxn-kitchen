import { describe, expect, it } from 'vitest';
import { badge, filterRecipes, lineText, type Summary, type Line } from '../src/lib/recipes';

const line = (o: Partial<Line>): Line => ({ pos: 0, raw: '', qty_text: '1 ek', name: 'Finomliszt', note: null, item_id: 'wheat-flour',
  item_name: 'Búzaliszt', how: 'exact', gluten: 'swap', ok_gf: false, gf_text: '1 ek GM lisztkeverék', tip: 'x', have: true, pantry_id: null, ...o }) as Line;

describe('lineText', () => {
  it('the GF version shows the swap, the original shows the source', () => {
    expect(lineText(line({}), true)).toEqual({ text: '1 ek GM lisztkeverék', struck: '1 ek Finomliszt' });
    expect(lineText(line({}), false)).toEqual({ text: '1 ek Finomliszt', struck: null });
  });
  it('a line without a swap is the same in both views', () => {
    const l = line({ gluten: 'ok', gf_text: null, qty_text: '2 db', name: 'Vöröshagyma' });
    expect(lineText(l, true)).toEqual({ text: '2 db Vöröshagyma', struck: null });
  });
  it('no quantity, no leading space', () => {
    expect(lineText(line({ gluten: 'ok', gf_text: null, qty_text: '', name: 'só' }), true).text).toBe('só');
  });
});

describe('badge', () => {
  it.each([
    [{ state: 'gf', swaps: 0, check: 0, unknown: 0 }, 'gf'],
    [{ state: 'swaps', swaps: 2, check: 1, unknown: 0 }, 'swaps'],
    [{ state: 'check', swaps: 0, check: 1, unknown: 0 }, 'check'],
    [{ state: 'unknown', swaps: 0, check: 0, unknown: 3 }, 'unknown'],
  ] as const)('%o -> %s', (v, kind) => expect(badge(v as any).kind).toBe(kind));
  it('never shows a green badge for unknown lines', () => {
    expect(badge({ state: 'unknown', swaps: 0, check: 0, unknown: 1 }).tone).not.toBe('ok');
  });
});

describe('filterRecipes', () => {
  const s = (id: number, o: Partial<Summary>): Summary => ({ id, title: `r${id}`, image: null, minutes: 45, servings: 4, tags: [],
    source_site: null, verdict: { state: 'gf', swaps: 0, check: 0, unknown: 0 }, have: 3, total: 4, missing: 1, origin: 'typed',
    created_at: '', folder_id: null, ...o });
  const all = [s(1, { minutes: 20 }), s(2, { missing: 0, have: 4 }), s(3, { tags: ['leves'], minutes: null })];
  it('can make now = nothing missing', () => expect(filterRecipes(all, { mode: 'cookable' }).map((r) => r.id)).toEqual([2]));
  it('quick = 30 min or less, unknown time excluded', () => expect(filterRecipes(all, { mode: 'quick' }).map((r) => r.id)).toEqual([1]));
  it('tag filter', () => expect(filterRecipes(all, { mode: 'all', tag: 'leves' }).map((r) => r.id)).toEqual([3]));
});

describe('an empty recipe never wears the GF tick (live, 2026-10-11)', () => {
  it("'empty' maps to the neutral badge, not the ✓ tone", async () => {
    const { badge } = await import('../src/lib/recipes');
    expect(badge({ state: 'empty', swaps: 0, check: 0, unknown: 0 })).toEqual({ kind: 'empty', tone: 'unknown', n: 0 });
    expect(badge({ state: 'gf', swaps: 0, check: 0, unknown: 0 }).tone).toBe('ok');
  });
});
