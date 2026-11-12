import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { BASE_READS, startOfflineWarm, UNWARMED, warmUrls } from '../src/lib/offlinewarm';

const R = [{ id: 3, image: '/api/images/3-1.jpg' }, { id: 5, image: null }];
const S = [{ id: 7 }];
const B = [{ id: 9 }];

describe('warmUrls (item 5: the kiosk holds the whole library offline)', () => {
  it('the start-up reads, every detail, then every photo', () => {
    expect(warmUrls(R, S, B)).toEqual([
      ...BASE_READS, '/api/recipes/3', '/api/recipes/5', '/api/sauces/7', '/api/blends/9', '/api/images/3-1.jpg',
    ]);
  });
  it('a recipe without a photo adds no photo URL', () => {
    expect(warmUrls([{ id: 5, image: null }], [], []).filter((u) => u.startsWith('/api/images/'))).toEqual([]);
  });
});

describe('startOfflineWarm', () => {
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); });

  const setup = (lists = vi.fn(async () => [R, S, B] as [typeof R, typeof S, typeof B])) => {
    const post = vi.fn(() => true);
    const w = startOfflineWarm({ firstMs: 1000, everyMs: 60_000, debounceMs: 100 }, { lists, post });
    return { w, post, lists };
  };

  it('runs once after firstMs and hands the worker the full list', async () => {
    const { w, post } = setup();
    await vi.advanceTimersByTimeAsync(999);
    expect(post).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1);
    expect(post).toHaveBeenCalledTimes(1);
    expect(post).toHaveBeenCalledWith({ type: 'warm', urls: warmUrls(R, S, B) });
    w.stop();
  });

  it('a burst of pokes becomes one run', async () => {
    const { w, post } = setup();
    await vi.advanceTimersByTimeAsync(1000);
    post.mockClear();
    w.poke(); w.poke(); w.poke();
    await vi.advanceTimersByTimeAsync(100);
    expect(post).toHaveBeenCalledTimes(1);
    w.stop();
  });

  it('no run while the server is away (the lists throw), and the interval tries again', async () => {
    let away = true;
    const lists = vi.fn(async () => { if (away) throw new Error('offline'); return [R, S, B] as [typeof R, typeof S, typeof B]; });
    const { w, post } = setup(lists);
    await vi.advanceTimersByTimeAsync(1000);
    expect(lists).toHaveBeenCalledTimes(1);
    expect(post).not.toHaveBeenCalled();
    away = false;
    await vi.advanceTimersByTimeAsync(60_000);
    expect(post).toHaveBeenCalledTimes(1);
    w.stop();
  });

  it('stop() cancels everything', async () => {
    const { w, post } = setup();
    w.stop();
    await vi.advanceTimersByTimeAsync(120_000);
    expect(post).not.toHaveBeenCalled();
  });
});

// The class guard: the warm-up is only as complete as BASE_READS. A screen that starts reading a new path would be
// blank offline again, silently — so every getJSON path in the app must be warmed, listed as UNWARMED, or a detail
// the warm-up covers per id.
describe('every read a screen makes is warmed', () => {
  const src = join(__dirname, '../src');
  const files: string[] = [];
  const walk = (d: string) => {
    for (const f of readdirSync(d)) {
      const p = join(d, f);
      if (statSync(p).isDirectory()) walk(p);
      else if (/\.(ts|svelte)$/.test(f)) files.push(p);
    }
  };
  walk(src);
  const calls = files.flatMap((f) => [...readFileSync(f, 'utf8').matchAll(/getJSON(?:<(?:[^<>]|<[^<>]*>)*>)?\(\s*(['`])(\/api\/[a-z][^'`$]*)(\$\{)?/g)]
    .map((m) => ({ file: f.slice(src.length + 1), path: m[2], templated: !!m[3] })));

  it('the scan finds the app\'s reads (positive control)', () => {
    expect(calls.length).toBeGreaterThan(15);
    expect(calls.some((c) => c.path === '/api/weather')).toBe(true);
    expect(calls.some((c) => c.templated && c.path === '/api/recipes/')).toBe(true);
  });

  it('a plain read is in BASE_READS or UNWARMED', () => {
    const known = new Set<string>([...BASE_READS, ...UNWARMED]);
    expect(calls.filter((c) => !c.templated && !known.has(c.path)).map((c) => `${c.file}: ${c.path}`)).toEqual([]);
  });

  it('a read with parameters is a detail the warm-up fetches per id (or the recipe list, warmed without a query)', () => {
    const covered = new Set(['/api/recipes/', '/api/sauces/', '/api/blends/', '/api/recipes']);
    expect(calls.filter((c) => c.templated && !covered.has(c.path)).map((c) => `${c.file}: ${c.path}`)).toEqual([]);
  });
});
