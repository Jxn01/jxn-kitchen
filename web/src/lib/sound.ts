// Tiny synthesised sounds (no files): "tok" for a toggle on, "tuk" for off, "ring" for timers.
// Muted when settings.sounds is off. The kiosk's Chrome runs with --autoplay-policy=no-user-gesture-required.
import { get } from 'svelte/store';
import { settings } from './settings';

let ctx: AudioContext | null = null;
let sleep: ReturnType<typeof setTimeout> | null = null;
function ac(): AudioContext | null {
  try { return (ctx ??= new AudioContext()); } catch { return null; }
}
/** A running AudioContext keeps an audio thread busy forever; on the kiosk's Atom it sleeps between sounds. */
function suspendLater(ms: number): void {
  if (sleep) clearTimeout(sleep);
  sleep = setTimeout(() => { ctx?.suspend().catch(() => {}); }, ms + 300);
}

function blip(freqFrom: number, freqTo: number, ms: number, gain = 0.18): void {
  if (!get(settings).sounds) return;
  const a = ac();
  if (!a) return;
  if (a.state === 'suspended') a.resume().catch(() => {});
  suspendLater(ms);
  const o = a.createOscillator(), g = a.createGain(), t = a.currentTime;
  o.type = 'triangle';
  o.frequency.setValueAtTime(freqFrom, t);
  o.frequency.exponentialRampToValueAtTime(freqTo, t + ms / 1000);
  g.gain.setValueAtTime(gain, t);
  g.gain.exponentialRampToValueAtTime(0.0001, t + ms / 1000);
  o.connect(g).connect(a.destination);
  o.start(t);
  o.stop(t + ms / 1000 + 0.02);
}

/** The timer chime — a soft music-box phrase, G5 B5 D6 G6 rising. Each note is a sine with a faint octave above it,
 *  fades in over 12 ms (no click) and rings out slowly. It replaces a hard double strike on E6 every 1.6 s, which was
 *  high, click-sharp and relentless. */
const CHIME: readonly (readonly [number, number])[] = [[784, 0], [988, 0.15], [1175, 0.3], [1568, 0.45]];
/** How often the chime repeats while a finished timer waits for a tap (TimerDone uses this). */
export const RING_EVERY_MS = 3000;

function chime(): void {
  if (!get(settings).sounds) return;
  const a = ac();
  if (!a) return;
  if (a.state === 'suspended') a.resume().catch(() => {});
  suspendLater(2200);
  const t0 = a.currentTime + 0.02;
  for (const [freq, at] of CHIME) {
    for (const [mult, peak, decay] of [[1, 0.085, 1.5], [2, 0.022, 0.45]] as const) {
      const o = a.createOscillator(), v = a.createGain(), t = t0 + at;
      o.type = 'sine';
      o.frequency.setValueAtTime(freq * mult, t);
      v.gain.setValueAtTime(0.0001, t);
      v.gain.linearRampToValueAtTime(peak, t + 0.012);
      v.gain.exponentialRampToValueAtTime(0.0001, t + decay);
      o.connect(v).connect(a.destination);
      o.start(t);
      o.stop(t + decay + 0.05);
    }
  }
}

export const sound = {
  on: () => blip(520, 880, 90),
  off: () => blip(420, 220, 90, 0.14),
  ring: chime,
};
