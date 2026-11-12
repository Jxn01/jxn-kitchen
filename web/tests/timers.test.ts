import { describe, expect, it } from 'vitest';
import { get } from 'svelte/store';
import { ApiError, OfflineError } from '../src/lib/api';
import { due, flushDismissals, fmtTime, localTimers, left, pendingDismiss, type ServerTimer } from '../src/lib/cooktimers';

describe('timer display', () => {
  it.each([[0, '0:00'], [5, '0:05'], [65, '1:05'], [600, '10:00'], [3600, '1:00:00'], [3725, '1:02:05']])('%i s -> %s', (s, want) => {
    expect(fmtTime(s)).toBe(want);
  });
  it('counts down from the server\'s remaining at receipt — immune to the device clock being off', () => {
    const got = 1_000_000;                                   // Date.now() when the list arrived
    const [t] = localTimers([{ id: 1, label: 'Tészta', seconds: 600, state: 'running', remaining: 300, ends_at: '2000-01-01T00:00:00Z', recipe_id: null, step_pos: null }], got);
    expect(left(t, got)).toBe(300);
    expect(left(t, got + 61_000)).toBe(239);
    expect(left(t, got + 400_000)).toBe(0);
  });
  it('paused and done timers stand still', () => {
    const [p, d] = localTimers([
      { id: 1, label: 'a', seconds: 60, state: 'paused', remaining: 42, ends_at: null, recipe_id: null, step_pos: null },
      { id: 2, label: 'b', seconds: 60, state: 'done', remaining: 0, ends_at: null, recipe_id: null, step_pos: null },
    ], 0);
    expect(left(p, 99_999)).toBe(42);
    expect(left(d, 99_999)).toBe(0);
  });
});

describe('offline (2026-11-12: a timer running when the network dropped never rang on the kiosk)', () => {
  const run = (over: Partial<ServerTimer> = {}): ServerTimer =>
    ({ id: 1, label: 'Tészta', seconds: 600, state: 'running', remaining: 300, ends_at: '2026-11-12T02:00:00Z', recipe_id: null, step_pos: null, ...over });

  it('a running timer rings once its local countdown passes zero, with no word from the server', () => {
    const [t] = localTimers([run()], 0);
    expect(due([t], 299_000, new Set())).toEqual([]);
    expect(due([t], 300_000, new Set()).map((x) => x.id)).toEqual([1]);
  });
  it('what the server says is done rings too; a stop made here silences either', () => {
    const [d, r] = localTimers([run({ id: 2, state: 'done', remaining: 0, ends_at: null }), run()], 0);
    expect(due([d, r], 400_000, new Set()).map((x) => x.id)).toEqual([2, 1]);
    expect(due([d, r], 400_000, new Set([1, 2]))).toEqual([]);
  });
  it('paused timers never ring', () => {
    const [p] = localTimers([run({ state: 'paused', remaining: 0, ends_at: null })], 0);
    expect(due([p], 9e12, new Set())).toEqual([]);
  });
  it('a cached (stale) list counts down from ends_at; a fresh one from remaining, whatever ends_at says', () => {
    const at = Date.parse('2026-11-12T01:55:00Z');
    const [stale] = localTimers([run()], at, true);
    expect(left(stale, at)).toBe(300);                                  // 02:00 - 01:55
    const [staleLater] = localTimers([run()], at + 120_000, true);       // reloaded 2 min later: still ends at 02:00
    expect(left(staleLater, at + 120_000)).toBe(180);
    const [fresh] = localTimers([run({ ends_at: '2000-01-01T00:00:00Z' })], at);
    expect(left(fresh, at)).toBe(300);
  });
  it('stops reach the server one by one; a 404 counts as told; a network failure keeps the rest', async () => {
    pendingDismiss.set(new Set([1, 2, 3]));
    const sent: number[] = [];
    await flushDismissals(async (id) => {
      sent.push(id);
      if (id === 2) throw new ApiError('gone', 404, null);
      if (id === 3) throw new OfflineError('down');
    });
    expect(sent).toEqual([1, 2, 3]);
    expect([...get(pendingDismiss)]).toEqual([3]);
  });
});
