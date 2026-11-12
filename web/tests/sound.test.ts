/// <reference types="node" />
import { describe, expect, it, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

// A fake Web Audio graph that records what the ring schedules.
type Ev = { kind: string; v: number; t: number };
const notes: { freq: number; start: number; gain: Ev[] }[] = [];
class FakeParam { evs: Ev[] = []; setValueAtTime(v: number, t: number) { this.evs.push({ kind: 'set', v, t }); }
  linearRampToValueAtTime(v: number, t: number) { this.evs.push({ kind: 'lin', v, t }); }
  exponentialRampToValueAtTime(v: number, t: number) { this.evs.push({ kind: 'exp', v, t }); } }
class FakeCtx {
  state = 'running'; currentTime = 10; destination = {};
  resume() { return Promise.resolve(); } suspend() { return Promise.resolve(); }
  createGain() { const gain = new FakeParam(); return { gain, connect: (d: unknown) => d }; }
  createOscillator() {
    const frequency = new FakeParam(); let g: FakeParam | null = null;
    const o = { type: '', frequency, connect: (gn: { gain: FakeParam }) => { g = gn.gain; return gn; },
      start: (t: number) => notes.push({ freq: frequency.evs[0].v, start: t, gain: g!.evs }), stop: () => {} };
    return o;
  }
}
vi.stubGlobal('AudioContext', FakeCtx);
const { sound, RING_EVERY_MS } = await import('../src/lib/sound');

describe('the timer ring is a soft chime, not an alarm (owner, 2026-10-11)', () => {
  sound.ring();
  const fundamentals = notes.filter((n, i, all) => all.every((m) => m.start !== n.start || m.freq >= n.freq));

  it('is a rising four-note phrase', () => {
    const f = fundamentals.map((n) => n.freq);
    expect(f).toHaveLength(4);
    expect([...f].sort((a, b) => a - b)).toEqual(f);
    expect(Math.max(...f)).toBeLessThan(1600);             // nothing shrill
  });

  it('fades every note in (no click) and keeps it quiet', () => {
    for (const n of notes) {
      expect(n.gain[0]).toMatchObject({ kind: 'set' });
      expect(n.gain[0].v).toBeLessThanOrEqual(0.001);       // starts silent…
      expect(n.gain[1].kind).toBe('lin');                    // …and ramps up
      expect(n.gain[1].t - n.start).toBeGreaterThanOrEqual(0.008);
    }
    const peakAtOnce = Math.max(...fundamentals.map((f) => notes.filter((n) => n.start === f.start)
      .reduce((s, n) => s + Math.max(...n.gain.map((e) => e.v)), 0)));
    expect(peakAtOnce).toBeLessThanOrEqual(0.12);
  });

  it('repeats at a calm pace, and the card uses that pace', () => {
    expect(RING_EVERY_MS).toBeGreaterThanOrEqual(2500);
    const card = readFileSync(join(__dirname, '../src/components/TimerDone.svelte'), 'utf8');
    expect(card).toMatch(/setInterval\(\(\) => sound\.ring\(\), RING_EVERY_MS\)/);
  });
});
