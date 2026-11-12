// @vitest-environment jsdom
/// <reference types="node" />
import { describe, expect, it } from 'vitest';
import { parse } from '../src/lib/router';

describe('router.parse', () => {
  it.each([
    ['', { name: 'home' }],
    ['#/', { name: 'home' }],
    ['#/idle', { name: 'idle' }],
    ['#/settings', { name: 'settings' }],
    ['#/soon/pantry', { name: 'soon', param: 'pantry' }],
    ['#/nope', { name: 'home' }],
    ['#/soon', { name: 'home' }],
    ['#/pantry', { name: 'pantry' }],
    ['#/pantry/meat', { name: 'pantry-cat', param: 'meat' }],
    ['#/pantry/meat/chicken', { name: 'pantry-cat', param: 'meat', sub: 'chicken' }],
    ['#/pantry-have', { name: 'pantry-have' }],
    ['#/shopping', { name: 'shopping' }],
    ['#/recipes', { name: 'recipes', folder: null }],
    ['#/recipes/7', { name: 'recipes', folder: 7 }],
    ['#/recipes/0', { name: 'home' }],
    ['#/recipes/x', { name: 'home' }],
    ['#/recipe/12', { name: 'recipe', id: 12 }],
    ['#/recipe/12/edit', { name: 'recipe-edit', id: 12 }],
    ['#/recipe/new', { name: 'recipe-edit', id: null, folder: null }],
    ['#/recipe/new?folder=4', { name: 'recipe-edit', id: null, folder: 4 }],
    ['#/recipe/new?folder=nope', { name: 'recipe-edit', id: null, folder: null }],
    ['#/recipe/abc', { name: 'home' }],
    ['#/cook/3', { name: 'cook', id: 3, servings: null }],
    ['#/cook/3?servings=6', { name: 'cook', id: 3, servings: 6 }],
    ['#/cook/3?servings=999', { name: 'cook', id: 3, servings: null }],
    ['#/spices', { name: 'spices' }],
    ['#/spices/new', { name: 'blend-edit', id: null }],
    ['#/spices/4', { name: 'blend', id: 4 }],
    ['#/spices/4/edit', { name: 'blend-edit', id: 4 }],
    ['#/sauces', { name: 'sauces' }],
    ['#/sauces/new', { name: 'sauce-edit', id: null }],
    ['#/sauces/7', { name: 'sauce', id: 7 }],
    ['#/sauces/7/edit', { name: 'sauce-edit', id: 7 }],
    ['#/sauces/x', { name: 'home' }],
    ['#/sauces/7/nope', { name: 'home' }],
    ['#/cook/sauce/7', { name: 'cook-sauce', id: 7 }],
    ['#/cook/sauce/x', { name: 'home' }],
    ['#/browse', { name: 'browse' }],
    ['#/knowhow', { name: 'knowhow' }],
    ['#/knowhow/celiac', { name: 'knowhow-section', sid: 'celiac', pid: null }],
    ['#/knowhow/celiac/labels', { name: 'knowhow-section', sid: 'celiac', pid: 'labels' }],
    ['#/add?url=https%3A%2F%2Fwww.nosalty.hu%2Frecept%2Fx', { name: 'add', url: 'https://www.nosalty.hu/recept/x' }],
    ['#/add', { name: 'add', url: '' }],
  ])('%s', (hash, want) => expect(parse(hash)).toEqual(want));
});

describe('go(replace)', () => {
  it('replaces the history entry instead of pushing one (idle transitions never land in Back)', async () => {
    const { go, route } = await import('../src/lib/router');
    const before = history.length;
    go('/idle', { replace: true });
    expect(history.length).toBe(before);
    let r: any; route.subscribe((x) => (r = x))();
    expect(r.name).toBe('idle');
    go('/', { replace: true });
  });
});

describe('no history.back() anywhere (class guard: Back must never land on the idle scene or leave the app)', () => {
  it('source scan', async () => {
    const { readdirSync, readFileSync, statSync } = await import('node:fs');
    const { join } = await import('node:path');
    const walk = (d: string): string[] => readdirSync(d).flatMap((f) => statSync(join(d, f)).isDirectory() ? walk(join(d, f)) : [join(d, f)]);
    // src/overlay/ is exempt: it runs on third-party sites, where Back IS the site's own history
    const hits = walk(join(__dirname, '../src')).filter((f) => !f.includes('/overlay/') && /\.(ts|svelte)$/.test(f) && /history\.(back|go)\(/.test(readFileSync(f, 'utf8')));
    expect(hits).toEqual([]);
  });
});
