/// <reference types="node" />
import { describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import { createPantry } from '../src/lib/pantry';

const S0 = { have: ['salt'], groups_some: [], staples_off: [], rev: 0 };

describe('pantry store', () => {
  it('toggle is optimistic, then takes the server echo', async () => {
    let resolve!: (s: any) => void;
    const api = { put: vi.fn(() => new Promise((r) => { resolve = r; })) };
    const p = createPantry(api as any);
    p.accept(S0);
    const done = p.toggle('chicken-wings');
    expect(get(p.state).have).toContain('chicken-wings');      // at once
    resolve({ have: ['chicken-wings', 'salt'], groups_some: [], staples_off: [], rev: 1 });
    await done;
    expect(api.put).toHaveBeenCalledWith('chicken-wings', true);
    expect(get(p.state).have).toEqual(['chicken-wings', 'salt']);
  });
  it('a failed write rolls back', async () => {
    const api = { put: vi.fn(() => Promise.reject(new Error('offline'))) };
    const p = createPantry(api as any);
    p.accept(S0);
    await p.toggle('chicken-wings').catch(() => {});
    expect(get(p.state)).toEqual(S0);
  });
  it('group switches use the group: prefix and staples can go off', async () => {
    const api = { put: vi.fn(async (node: string, have: boolean) => ({ ...S0, groups_some: node.startsWith('group:') && have ? ['chicken'] : [], have: node === 'salt' ? [] : S0.have })) };
    const p = createPantry(api as any);
    p.accept(S0);
    await p.toggle('group:chicken');
    expect(api.put).toHaveBeenLastCalledWith('group:chicken', true);
    await p.toggle('salt');
    expect(api.put).toHaveBeenLastCalledWith('salt', false);
  });
});

describe('stale pantry state is dropped (review: a late answer could overwrite newer state)', () => {
  it('an older rev never replaces a newer one', () => {
    const p = createPantry({ put: vi.fn() } as any);
    p.accept({ have: ['a', 'b'], groups_some: [], staples_off: [], rev: 5 });
    p.accept({ have: ['a'], groups_some: [], staples_off: [], rev: 4 });       // a late SSE event / PUT answer
    expect(get(p.state).have).toEqual(['a', 'b']);
    p.accept({ have: ['b'], groups_some: [], staples_off: [], rev: 6 });
    expect(get(p.state).have).toEqual(['b']);
  });
  it('a slow PUT answer arriving after a newer SSE event is ignored', async () => {
    let resolve!: (s: any) => void;
    const p = createPantry({ put: vi.fn(() => new Promise((r) => { resolve = r; })) } as any);
    p.accept({ have: [], groups_some: [], staples_off: [], rev: 1 });
    const done = p.toggle('x');
    p.accept({ have: ['x', 'y'], groups_some: [], staples_off: [], rev: 3 });  // the phone added y meanwhile
    resolve({ have: ['x'], groups_some: [], staples_off: [], rev: 2 });
    await done;
    expect(get(p.state).have).toEqual(['x', 'y']);
  });
  it('nothing outside lib/pantry.ts sets the pantry store directly', async () => {
    const { readdirSync, readFileSync, statSync } = await import('node:fs');
    const { join } = await import('node:path');
    const walk = (d: string): string[] => readdirSync(d).flatMap((f) => statSync(join(d, f)).isDirectory() ? walk(join(d, f)) : [join(d, f)]);
    const hits = walk(join(__dirname, '../src')).filter((f) => !f.endsWith('lib/pantry.ts') && /pantry\.state\.set\(/.test(readFileSync(f, 'utf8')));
    expect(hits).toEqual([]);
  });
});
