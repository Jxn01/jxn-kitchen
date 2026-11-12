import { describe, expect, it } from 'vitest';
import lib from './fixtures/knowhow.json';
import { searchKnowhow, findPage } from '../src/lib/knowhow';

describe('know-how search', () => {
  it('finds a page by its title, with or without accents, in either language', () => {
    for (const q of ['rántás', 'rantas', 'roux']) expect(searchKnowhow(lib as any, q, 'hu')[0].page.id).toBe('rantas');
  });
  it('finds words inside bodies too, titles first', () => {
    const hits = searchKnowhow(lib as any, 'xanthan', 'en');
    expect(hits.length).toBeGreaterThan(1);
    expect(hits.some((h) => h.section.id === 'baking')).toBe(true);
  });
  it('a snippet shows where the word is', () => {
    const [h] = searchKnowhow(lib as any, 'psyllium', 'en').filter((x) => x.where === 'body');
    expect(h.snippet.toLowerCase()).toContain('psyllium');
  });
  it('empty or one-letter queries find nothing', () => {
    expect(searchKnowhow(lib as any, ' ', 'en')).toEqual([]);
    expect(searchKnowhow(lib as any, 'a', 'en')).toEqual([]);
  });
  it('pages are found by section and id', () => {
    expect(findPage(lib as any, 'celiac', 'labels')?.page.en.title).toBe('Reading Hungarian labels');
    expect(findPage(lib as any, 'celiac', 'nope')).toBeNull();
  });
});
