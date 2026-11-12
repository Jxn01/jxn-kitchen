import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { connectEvents } from '../src/lib/events';

class FakeES {
  static all: FakeES[] = [];
  listeners: Record<string, ((e: any) => void)[]> = {};
  closed = false;
  constructor(public url: string) { FakeES.all.push(this); }
  addEventListener(type: string, fn: (e: any) => void) { (this.listeners[type] ??= []).push(fn); }
  emit(type: string, e: any = {}) { for (const fn of this.listeners[type] ?? []) fn(e); }
  close() { this.closed = true; }
}

describe('connectEvents', () => {
  beforeEach(() => { vi.useFakeTimers(); FakeES.all = []; });
  afterEach(() => vi.useRealTimers());

  it('reconnects with 1,2,4,8… capped at 30 s, and an open resets the backoff', () => {
    const status: boolean[] = [];
    connectEvents({ url: '/api/events', ES: FakeES as any, onStatus: (ok) => status.push(ok) });
    const delays: number[] = [];
    for (let i = 0; i < 7; i++) {
      const before = FakeES.all.length;
      const es = FakeES.all.at(-1)!;
      es.emit('error');
      expect(es.closed).toBe(true);                  // we own reconnection: the dead source is closed
      let waited = 0;
      while (FakeES.all.length === before) { vi.advanceTimersByTime(500); waited += 500; }
      delays.push(waited);
    }
    expect(delays).toEqual([1000, 2000, 4000, 8000, 16000, 30000, 30000]);
    FakeES.all.at(-1)!.emit('open');
    FakeES.all.at(-1)!.emit('error');
    const n = FakeES.all.length;
    vi.advanceTimersByTime(999);
    expect(FakeES.all.length).toBe(n);
    vi.advanceTimersByTime(1);
    expect(FakeES.all.length).toBe(n + 1);
    expect(status.includes(false) && status.at(-2) === true).toBe(true);
  });

  it('handlers survive a reconnect and receive parsed data', () => {
    const got: any[] = [];
    const ev = connectEvents({ url: '/api/events', ES: FakeES as any });
    ev.on('settings', (d) => got.push(d));
    FakeES.all[0].emit('error');
    vi.advanceTimersByTime(1000);
    FakeES.all[1].emit('settings', { data: '{"language":"hu"}' });
    expect(got).toEqual([{ language: 'hu' }]);
  });

  it('close stops reconnecting', () => {
    const ev = connectEvents({ url: '/api/events', ES: FakeES as any });
    ev.close();
    FakeES.all[0].emit('error');
    vi.advanceTimersByTime(60000);
    expect(FakeES.all.length).toBe(1);
  });
});

describe('watchdog (review: a silently dead stream was never noticed)', () => {
  beforeEach(() => { vi.useFakeTimers(); FakeES.all = []; });
  afterEach(() => vi.useRealTimers());
  it('reconnects when nothing — not even a ping — arrives for STALE_MS', async () => {
    const { STALE_MS } = await import('../src/lib/events');
    const status: boolean[] = [];
    connectEvents({ url: '/api/events', ES: FakeES as any, onStatus: (ok) => status.push(ok) });
    const first = FakeES.all[0];
    first.emit('open');
    vi.advanceTimersByTime(STALE_MS - 1000);
    first.emit('ping', { data: '{}' });                 // a ping keeps it alive
    vi.advanceTimersByTime(STALE_MS - 1000);
    expect(FakeES.all.length).toBe(1);
    vi.advanceTimersByTime(2000);                        // silence: close, report offline, reconnect
    expect(first.closed).toBe(true);
    expect(status.at(-1)).toBe(false);
    vi.advanceTimersByTime(1000);
    expect(FakeES.all.length).toBe(2);
  });
});
