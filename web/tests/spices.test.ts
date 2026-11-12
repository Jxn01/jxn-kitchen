import { describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import { createEvaluator, fmtParts, ledgerFor, ledgerTotal, pool, stepParts, trayAdd, trayDrop, traySet, type Evaluation, type Part } from '../src/lib/spices';

const ev = (seq: number, over: Partial<Evaluation> = {}) => ({ seq, score: 60, base: 50, findings: [], ...over }) as unknown as Evaluation;

describe('parts in level teaspoons', () => {
  it('reads like a cook writes them', () => {
    expect([0.5, 1, 1.5, 2, 4.5, 0.3].map(fmtParts)).toEqual(['½', '1', '1½', '2', '4½', '0.3']);
  });
  it('steps by half a teaspoon, never below ½ nor above 50', () => {
    expect(stepParts(1, 1)).toBe(1.5);
    expect(stepParts(0.5, -1)).toBe(0.5);
    expect(stepParts(50, 1)).toBe(50);
    expect(stepParts(0.3, 1)).toBe(1);        // an odd value lands back on the half steps
  });
});

describe('a fixed pool of slots', () => {
  it('pads a short list with empty slots up to the pool size', () => {
    expect(pool(['a', 'b'], 4)).toEqual(['a', 'b', null, null]);
    expect(pool([], 3)).toEqual([null, null, null]);
  });
  it('never drops an item: a longer list keeps all of it', () => {
    expect(pool([1, 2, 3], 2)).toEqual([1, 2, 3]);
  });
  it('the same size for every list up to the pool size — so an answer only fills slots', () => {
    for (let n = 0; n <= 5; n++) expect(pool(Array(n).fill(0), 5)).toHaveLength(5);
  });
});

describe('the tray', () => {
  it('adds a jar once, sets it, drops it, and holds at most 16', () => {
    let t: Part[] = [];
    t = trayAdd(t, 'cumin'); t = trayAdd(t, 'cumin');
    expect(t).toEqual([{ spice: 'cumin', parts: 1 }]);
    t = traySet(t, 'cumin', 2.5);
    expect(t[0].parts).toBe(2.5);
    expect(trayDrop(t, 'cumin')).toEqual([]);
    const full = Array.from({ length: 16 }, (_, i) => ({ spice: `j${i}`, parts: 1 }));
    expect(trayAdd(full, 'one-more')).toBe(full);
  });
});

describe('the ledger', () => {
  const findings = [
    { id: 'pair:a+b', kind: 'good', weight: 4, about: ['a', 'b'], en: 'x', hu: 'x' },
    { id: 'one-note', kind: 'warn', weight: -12, about: ['a'], en: 'y', hu: 'y' },
    { id: 'heat:mild', kind: 'info', weight: 0, about: [], en: 'z', hu: 'z' },
  ] as Evaluation['findings'];
  it('filters to the lines about one jar', () => {
    expect(ledgerFor(findings, 'b').map((f) => f.id)).toEqual(['pair:a+b']);
    expect(ledgerFor(findings, null)).toHaveLength(3);
  });
  it('adds up to the score, clamped', () => {
    expect(ledgerTotal(ev(1, { findings }))).toBe(42);
    expect(ledgerTotal(ev(1, { findings: [{ ...findings[1], weight: -80 }] }))).toBe(0);
  });
});

describe('the evaluator', () => {
  it('waits 300 ms after the last change and sends one request', async () => {
    vi.useFakeTimers();
    const send = vi.fn(async (_p: Part[], seq: number) => ev(seq));
    const got: (Evaluation | null)[] = [];
    const e = createEvaluator(send, (x) => got.push(x));
    e.schedule([{ spice: 'cumin', parts: 1 }]);
    vi.advanceTimersByTime(200);
    e.schedule([{ spice: 'cumin', parts: 1.5 }]);
    vi.advanceTimersByTime(299);
    expect(send).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(send).toHaveBeenCalledTimes(1);
    expect(send.mock.calls[0][0]).toEqual([{ spice: 'cumin', parts: 1.5 }]);
    await vi.runAllTimersAsync();
    expect(got).toHaveLength(1);
    vi.useRealTimers();
  });
  it('drops an answer that arrives after a newer request (a slow answer never overwrites a newer blend)', async () => {
    vi.useFakeTimers();
    const resolvers: (() => void)[] = [];
    const send = vi.fn((_p: Part[], seq: number) => new Promise<Evaluation>((r) => resolvers.push(() => r(ev(seq)))));
    const got: number[] = [];
    const e = createEvaluator(send, (x) => got.push(x?.seq ?? -1));
    e.schedule([{ spice: 'cumin', parts: 1 }]);
    vi.advanceTimersByTime(300);
    e.schedule([{ spice: 'cumin', parts: 2 }]);
    vi.advanceTimersByTime(300);
    expect(get(e.busy)).toBe(true);
    resolvers[1]();            // the newer answer first…
    resolvers[0]();            // …then the stale one
    await vi.runAllTimersAsync();
    expect(got).toEqual([2]);
    expect(get(e.busy)).toBe(false);
    vi.useRealTimers();
  });
  it('an empty tray answers null at once and cancels what was pending', async () => {
    vi.useFakeTimers();
    const send = vi.fn(async (_p: Part[], seq: number) => ev(seq));
    const got: (Evaluation | null)[] = [];
    const e = createEvaluator(send, (x) => got.push(x));
    e.schedule([{ spice: 'cumin', parts: 1 }]);
    e.schedule([]);
    await vi.runAllTimersAsync();
    expect(send).not.toHaveBeenCalled();
    expect(got).toEqual([null]);
    vi.useRealTimers();
  });
});
