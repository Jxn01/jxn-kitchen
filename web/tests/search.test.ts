import { describe, expect, it } from 'vitest';
import cases from './fixtures/fold_cases.json';
import { fold, search, type Cat } from '../src/lib/search';

const CAT: Cat = { categories: [
  { id: 'spices', en: 'Spices', hu: 'Fűszerek', icon: 'x', color: 'tangerine', kind: 'food', groups: [
    { id: 'pepper', en: 'Pepper', hu: 'Bors', icon: 'x', items: [
      { id: 'black-pepper', en: 'Black pepper', hu: 'Fekete bors', icon: null, gluten: 'free', aliases: ['pepper', 'bors', 'őrölt bors'] },
      { id: 'sichuan-pepper', en: 'Sichuan pepper', hu: 'Szecsuáni bors', icon: null, gluten: 'free', aliases: ['sichuan peppercorn', 'szecsuani bors'] },
      { id: 'pink-pepper', en: 'Pink peppercorns', hu: 'Rózsabors', icon: null, gluten: 'free' },
    ] },
  ] },
  { id: 'meat', en: 'Meat', hu: 'Hús', icon: 'x', color: 'tomato', kind: 'food', groups: [
    { id: 'chicken', en: 'Chicken', hu: 'Csirke', icon: 'x', items: [
      { id: 'chicken-wings', en: 'Wings', hu: 'Szárny', icon: null, gluten: 'free', aliases: ['csirkeszárny'] },
    ] },
  ] },
] };

describe('fold — same table as the server (server/tests/test_catalogue.py)', () => {
  it.each(cases as [string, string][])('%s', (raw, want) => expect(fold(raw)).toBe(want));
});

describe('search', () => {
  const ids = (q: string) => search(CAT, q).map((r) => r.id);
  it('finds Sichuan pepper in both languages, accents or not', () => {
    for (const q of ['sichuan', 'Szecsuáni', 'szecsuani', 'SICH']) expect(ids(q)[0]).toBe('sichuan-pepper');
  });
  it('ranks exact > prefix > alias > substring', () => {
    expect(ids('bors')[0]).toBe('black-pepper');              // exact alias beats "Szecsuáni bors" substring
    expect(ids('pepper').slice(0, 1)).toEqual(['black-pepper']);
  });
  it('finds groups too, marked as groups', () => {
    const r = search(CAT, 'csirke');
    expect(r.some((x) => x.kind === 'group' && x.id === 'chicken')).toBe(true);
    expect(r.some((x) => x.kind === 'item' && x.id === 'chicken-wings')).toBe(true);
  });
  it('an empty or blank query shows nothing', () => {
    expect(search(CAT, '')).toEqual([]);
    expect(search(CAT, '   ')).toEqual([]);
  });
});
