import { describe, expect, it } from 'vitest';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { ApiError } from '../src/lib/api';
import { childrenOf, pathLabel, pathOf, refusal, refusalKey, subtree, treeRows, type Folder } from '../src/lib/folders';

const f = (id: number, name: string, parent_id: number | null): Folder =>
  ({ id, name, parent_id, recipes: 0, folders: 0, created_at: '', updated_at: '' });
// the server's order: siblings by name
const LIST = [f(3, 'Édességek', null), f(1, 'Levesek', null), f(4, 'Gyors', 1), f(2, 'Magyar', 1), f(5, 'Bográcsos', 2)];

describe('folder tree helpers', () => {
  it('children of a folder, and of the top level', () => {
    expect(childrenOf(LIST, null).map((x) => x.id)).toEqual([3, 1]);
    expect(childrenOf(LIST, 1).map((x) => x.id)).toEqual([4, 2]);
    expect(childrenOf(LIST, 5)).toEqual([]);
  });
  it('the path from the top level down to a folder', () => {
    expect(pathOf(LIST, 5).map((x) => x.name)).toEqual(['Levesek', 'Magyar', 'Bográcsos']);
    expect(pathOf(LIST, null)).toEqual([]);
    expect(pathOf(LIST, 99)).toEqual([]);
    expect(pathLabel(LIST, 5)).toBe('Levesek › Magyar › Bográcsos');
  });
  it('a broken parent chain cannot loop forever', () => {
    const loop = [f(1, 'A', 2), f(2, 'B', 1)];
    expect(pathOf(loop, 1).length).toBeLessThanOrEqual(3);
  });
  it('a subtree holds the folder and everything below it, nothing else', () => {
    expect([...subtree(LIST, 1)].sort()).toEqual([1, 2, 4, 5]);
    expect([...subtree(LIST, 2)].sort()).toEqual([2, 5]);
    expect([...subtree(LIST, 3)]).toEqual([3]);
  });
  it('tree rows: depth first, siblings in the server order, with their depth', () => {
    expect(treeRows(LIST).map((r) => `${r.depth}:${r.folder.name}`))
      .toEqual(['0:Édességek', '0:Levesek', '1:Gyors', '1:Magyar', '2:Bográcsos']);
  });
});

describe('folder refusals', () => {
  it('reads the server code off an ApiError', () => {
    expect(refusal(new ApiError('x -> 409', 409, { code: 'taken', message: '' }))).toBe('taken');
    expect(refusal(new ApiError('x -> 409', 409, { code: 'cycle', message: '' }))).toBe('cycle');
    expect(refusal(new ApiError('x -> 409', 409, { code: 'depth', message: '' }))).toBe('depth');
    expect(refusal(new ApiError('x -> 422', 422, [{ msg: 'too long' }]))).toBe('name');
    expect(refusalKey(new ApiError('x -> 409', 409, { code: 'taken', message: '' }))).toBe('folders.err.taken');
  });
  it('anything else is the generic error', () => {
    expect(refusal(new ApiError('x -> 404', 404, 'no such folder'))).toBeNull();
    expect(refusal(new Error('offline'))).toBeNull();
    expect(refusalKey(new Error('offline'))).toBe('toast.error');
  });
});

// An effect that loads while a store's LIST is empty re-runs on every load (a store notifies on each new array) and
// fetches without end while the server's answer is empty — the recipe page did, 223 requests a second with no folders.
const LOAD_WHILE_EMPTY = /\$effect\(\(\) => \{[^}]*\$\w+\.length[^}]*\bload\w*\(/;
function sources(dir: string): string[] {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n);
    return statSync(p).isDirectory() ? sources(p) : /\.(svelte|ts)$/.test(n) ? [p] : [];
  });
}
describe('no effect loads while a list is empty', () => {
  it('positive control: the pattern catches the line that looped', () => {
    expect(LOAD_WHILE_EMPTY.test('$effect(() => { if (!$folderList.length) loadFolders(); });')).toBe(true);
    expect(LOAD_WHILE_EMPTY.test('$effect(() => { if (!$foldersLoaded) loadFolders(); });')).toBe(false);
  });
  it('no source has one', () => {
    const bad = sources(join(__dirname, '../src')).filter((p) => LOAD_WHILE_EMPTY.test(readFileSync(p, 'utf8')));
    expect(bad).toEqual([]);
  });
});

describe('the folder screens', () => {
  const src = (p: string) => readFileSync(join(__dirname, '../src', p), 'utf8');
  it('every refusal code has a message in the dictionaries', async () => {
    const en = (await import('../src/i18n/en.json')).default as Record<string, string>;
    for (const c of ['taken', 'cycle', 'depth', 'name']) expect(en[`folders.err.${c}`], c).toBeTruthy();
  });
  it('select mode never builds icons on a tap: both action sets live in the page, swapped by class', () => {
    const s = src('screens/Recipes.svelte');
    expect(s).toMatch(/class="acts" class:off=\{selecting\}/);
    expect(s).toMatch(/class="acts sel" class:off=\{!selecting\}/);
    expect(s).not.toMatch(/\{#if selecting\}/);
    expect(s).not.toMatch(/\{#if !selecting\}/);
  });
});
