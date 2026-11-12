import { describe, expect, it } from 'vitest';
import { fromRecipe, fromSauce, stepParts, timerLabel, usedUp } from '../src/lib/cook';
import type { Recipe } from '../src/lib/recipes';
import type { Sauce } from '../src/lib/sauces';

describe('cook mode', () => {
  it('a step becomes text and timer buttons', () => {
    const text = 'Főzzük 25 percig, majd pihentessük 5 percet.';
    const parts = stepParts(text, [{ start: 7, end: 16, seconds: 1500 }, { start: 35, end: 42, seconds: 300 }]);
    expect(parts).toEqual([
      { text: 'Főzzük ' }, { text: '25 percig', seconds: 1500 }, { text: ', majd pihentessük ' },
      { text: '5 perce', seconds: 300 }, { text: 't.' },
    ]);
    expect(stepParts('No timers.', [])).toEqual([{ text: 'No timers.' }]);
  });
  it('timer labels name the recipe and the step, within 60 characters', () => {
    expect(timerLabel('Paprikás csirke', 2, 'hu')).toBe('Paprikás csirke · 3. lépés');
    expect(timerLabel('Paprikás csirke', 2, 'en')).toBe('Paprikás csirke · step 3');
    expect(timerLabel('x'.repeat(80), 0, 'en').length).toBeLessThanOrEqual(60);
  });
  it('"used up anything?" offers each pantry tile that is in, once', () => {
    const l = (pantry_id: string | null, have: boolean | null) => ({ pantry_id, have }) as any;
    expect(usedUp([l('onion', true), l('onion', true), l('salt', true), l('milk', false), l(null, true)])).toEqual(['onion', 'salt']);
  });
});

describe('a recipe and a sauce both cook as a cookable', () => {
  const units = [{ id: 'tbsp', en: 'tbsp', hu: 'ek' }, { id: 'tsp', en: 'tsp', hu: 'tk' }, { id: 'ml', en: 'ml', hu: 'ml' }];
  const names = { 'olive-oil': 'Olívaolaj', cumin: 'Kömény' };
  const sauce = {
    id: 9, names: { en: 'My dressing', hu: 'Az öntetem' }, yield_ml: 200, keeps: { class: 'acid-preserved', days: 14 },
    steps: { en: ['Shake for 1 minute.'], hu: ['Rázd 1 percig.'] },
    timers: { en: [[{ seconds: 60, start: 10, end: 18 }]], hu: [[{ seconds: 60, start: 5, end: 12 }]] },
    lines: [
      { pos: 0, kind: 'shelf', shelf_id: 'olive-oil', spice_id: null, blend_id: null, item_id: 'olive-oil', raw: null, qty: 6, unit: 'tbsp', ok_gf: false, match_how: null, gluten: { status: 'ok', swap_id: null, tip_en: null, tip_hu: null, about: [] } },
      { pos: 1, kind: 'spice', shelf_id: null, spice_id: 'cumin', blend_id: null, item_id: 'cumin', raw: null, qty: 0.5, unit: 'tsp', ok_gf: false, match_how: null, gluten: { status: 'ok', swap_id: null, tip_en: null, tip_hu: null, about: [] } },
      { pos: 2, kind: 'blend', shelf_id: null, spice_id: null, blend_id: 4, item_id: null, raw: null, qty: 1, unit: 'tsp', ok_gf: false, match_how: null, gluten: { status: 'check', swap_id: null, tip_en: null, tip_hu: null, about: ['hing'] } },
      { pos: 3, kind: 'raw', shelf_id: null, spice_id: null, blend_id: null, item_id: null, raw: 'egy csipet szerelem', qty: null, unit: null, ok_gf: false, match_how: null, gluten: { status: 'unknown', swap_id: null, tip_en: null, tip_hu: null, about: [] } },
    ],
  } as unknown as Sauce;
  it('a sauce: its steps and their timers in the screen\'s language, its lines as amounts and names, no recipe for the timers', () => {
    const c = fromSauce(sauce, 'hu', units, names, { 4: 'Garam masala' });
    expect(c.title).toBe('Az öntetem');
    expect(c.steps).toEqual([{ text: 'Rázd 1 percig.', timers: [{ seconds: 60, start: 5, end: 12 }] }]);
    expect(c.lines.map((l) => l.text)).toEqual(['6 ek Olívaolaj', '½ tk Kömény', '1 tk Garam masala', 'egy csipet szerelem']);
    expect(c.lines.map((l) => l.gluten)).toEqual(['ok', 'ok', 'check', 'unknown']);
    expect(c).toMatchObject({ back: '/sauces/9', recipeId: null, used: [], keeps: 14, yield_ml: 200, servings: null });
  });
  it('a recipe: its GF version lines, the pantry tiles it used, its id for the timers', () => {
    const r = { id: 3, title: 'Paprikás', servings: 4, steps: [{ pos: 0, text: 'Főzd 5 percig.', timers: [] }],
      lines: [{ pos: 0, raw: '1 onion', qty_text: '1', name: 'onion', note: 'finely', item_id: 'onion', pantry_id: 'onion', have: true, gluten: 'ok', swap_name: null }] } as unknown as Recipe;
    const c = fromRecipe(r);
    expect(c).toMatchObject({ title: 'Paprikás', back: '/recipe/3', recipeId: 3, used: ['onion'], servings: 4, keeps: null });
    expect(c.lines[0]).toMatchObject({ key: 0, note: 'finely', gluten: 'ok' });
  });
});
