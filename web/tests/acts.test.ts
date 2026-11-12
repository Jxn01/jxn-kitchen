import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createScheduler, type Act } from '../src/lib/acts';

function act(id: string, ms: number, log: string[]): Act {
  return { id, run: () => { log.push(`start:${id}`); return new Promise((r) => setTimeout(() => { log.push(`end:${id}`); r(); }, ms)); } };
}

describe('act scheduler', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('never overlaps, never repeats an act twice in a row, gaps within [min,max]', async () => {
    const log: string[] = [];
    const starts: number[] = [];
    const acts = ['a', 'b', 'c'].map((id) => act(id, 1000, log));
    const wrapped = acts.map((a) => ({ id: a.id, run: () => { starts.push(Date.now()); return a.run(); } }));
    const s = createScheduler({ acts: wrapped, minGapMs: 15000, maxGapMs: 40000, rng: Math.random });
    s.start();
    await vi.advanceTimersByTimeAsync(10 * 60 * 1000);
    let open = 0;
    for (const e of log) { open += e.startsWith('start') ? 1 : -1; expect(open).toBeLessThanOrEqual(1); }
    const ids = log.filter((e) => e.startsWith('start')).map((e) => e.slice(6));
    for (let i = 1; i < ids.length; i++) expect(ids[i]).not.toBe(ids[i - 1]);
    for (let i = 1; i < starts.length; i++) {
      const gap = starts[i] - starts[i - 1] - 1000;          // minus the act's own duration
      expect(gap).toBeGreaterThanOrEqual(15000);
      expect(gap).toBeLessThanOrEqual(40000);
    }
    expect(ids.length).toBeGreaterThan(10);
  });

  it('schedules nothing while hidden and resumes on wake', async () => {
    const log: string[] = [];
    let hidden = true;
    const s = createScheduler({ acts: [act('a', 100, log), act('b', 100, log)], isHidden: () => hidden });
    s.start();
    await vi.advanceTimersByTimeAsync(5 * 60 * 1000);
    expect(log).toEqual([]);
    hidden = false;
    s.wake();
    await vi.advanceTimersByTimeAsync(41000);
    expect(log.length).toBeGreaterThan(0);
  });

  it('night doubles the gaps', async () => {
    const starts: number[] = [];
    const acts: Act[] = ['a', 'b'].map((id) => ({ id, run: async () => { starts.push(Date.now()); } }));
    const s = createScheduler({ acts, minGapMs: 15000, maxGapMs: 15000 });
    s.setNight(true);
    const t0 = Date.now();
    s.start();
    await vi.advanceTimersByTimeAsync(31000);
    expect(starts.map((t) => t - t0)).toEqual([30000]);
  });

  it('skips acts that are not available on the current screen', async () => {
    const ran: string[] = [];
    const acts: Act[] = [
      { id: 'idle-only', available: () => false, run: async () => { ran.push('idle-only'); } },
      { id: 'pan', run: async () => { ran.push('pan'); } },
      { id: 'pan2', run: async () => { ran.push('pan2'); } },
    ];
    const s = createScheduler({ acts, minGapMs: 1000, maxGapMs: 1000 });
    s.start();
    await vi.advanceTimersByTimeAsync(20000);
    expect(ran).not.toContain('idle-only');
    expect(ran.length).toBeGreaterThan(5);
  });

  it('stop cancels the pending act', async () => {
    const ran: string[] = [];
    const s = createScheduler({ acts: [{ id: 'a', run: async () => { ran.push('a'); } }], minGapMs: 1000, maxGapMs: 1000 });
    s.start();
    s.stop();
    await vi.advanceTimersByTimeAsync(10000);
    expect(ran).toEqual([]);
  });
});
