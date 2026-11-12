// The mascot (a cast-iron-pan mascot).
//
// Mascot.svelte is a RIG: one absolutely positioned HTML div per moving part (shadow, body, handle, egg, yolk, eyes,
// pupils, lids, brows, mouths, cheeks, arms in three segments, props, effects), each wrapping a STATIC svg fragment
// drawn in one shared 340×260 design space. Everything moves with CSS animations of `transform` and `opacity` on those
// divs — never on svg children, which Chrome cannot composite (each frame would repaint on the Atom's main thread).
// The whole rig is sized with CSS `zoom`, so every layer rasterises crisply at its real size.
//
// This module holds what is not markup: the part geometry helper, the action table, and the "brain" that keeps the
// character alive (blinks, glances, the odd yolk wobble) between the big acts the ambient scheduler hands it.

export const W = 340;
export const H = 260;

/** Style for a part: its box in design units (relative to its parent part's box) and its pivot, in design units. */
export function box(x: number, y: number, w: number, h: number, px = x + w / 2, py = y + h / 2,
                    parent: [number, number] = [0, 0]): string {
  return `left:${x - parent[0]}px;top:${y - parent[1]}px;width:${w}px;height:${h}px;` +
         `transform-origin:${px - x}px ${py - y}px`;
}
/** The matching svg viewBox, so a part's geometry is written in the shared design space. */
export const vb = (x: number, y: number, w: number, h: number) => `${x} ${y} ${w} ${h}`;

export type Expr = 'neutral' | 'happy' | 'joy' | 'surprised' | 'sleepy' | 'asleep' | 'worried' | 'focus' | 'proud' | 'alarm';

export interface ActionDef {
  ms: number;          // how long the CSS animations of `a-<id>` run (the longest one)
  expr?: Expr;         // the face for the duration (mid-action changes are in the keyframes)
  hold?: boolean;      // keep the last frame (a pose: shrug) instead of returning to rest
}

/** Every action the rig can play — each has CSS `.a-<id>` rules in Mascot.svelte (tested). */
export const ACTIONS: Record<string, ActionDef> = {
  hello: { ms: 1700, expr: 'happy' },
  wave: { ms: 1800, expr: 'happy' },
  hop: { ms: 1000, expr: 'joy' },
  flip: { ms: 2400 },
  stir: { ms: 2600, expr: 'focus' },
  yawn: { ms: 2600 },
  snore: { ms: 3200, expr: 'asleep' },
  alarm: { ms: 1200, expr: 'alarm' },
  giggle: { ms: 950, expr: 'joy' },
  shrug: { ms: 1400, expr: 'neutral', hold: true },
  think: { ms: 2200, expr: 'focus' },
  worried: { ms: 2400, expr: 'worried' },
  look: { ms: 1900 },
  sizzle: { ms: 1400, expr: 'happy' },
  steam: { ms: 2600 },
  dance: { ms: 2800, expr: 'joy' },
  celebrate: { ms: 1800, expr: 'joy' },
  nod: { ms: 650, expr: 'happy' },
  talk: { ms: 1600, expr: 'happy' },
};

/** The acts the ambient scheduler may pick on its own (home + idle). The rest are reactions or states. */
export const AMBIENT = ['wave', 'hop', 'flip', 'stir', 'yawn', 'look', 'sizzle', 'steam', 'dance'] as const;
export const NIGHT_AMBIENT = ['snore', 'snore', 'look'] as const;   // asleep: mostly snoring (look = a dream twitch)

export interface Clock {
  setTimeout: (fn: () => void, ms: number) => unknown;
  clearTimeout: (h: unknown) => void;
  rng: () => number;
}

export interface BrainHooks {
  blink: (double: boolean) => void;       // play a 200 ms (or 420 ms double) blink
  look: (dx: number, dy: number) => void; // move the pupils (design units); (0, 0) = straight ahead
  wobble: () => void;                     // the yolk's small idle wobble
  canMove: () => boolean;                 // false while an action plays, the page is hidden or the mascot sleeps
}

/** Keeps the character alive between acts: a blink every 2.4–6 s (one in eight doubled), a glance every 7–15 s that
 *  holds 0.9–1.7 s, and a yolk wobble every 14–28 s. All short transform animations; nothing runs in between. */
// The default clock wraps the timers in arrows: browsers throw "Illegal invocation" when setTimeout is called as a
// method of another object (`c.setTimeout(…)`) — the brain died at start on the kiosk and nothing ever blinked.
const realClock: Clock = {
  setTimeout: (fn, ms) => setTimeout(fn, ms),
  clearTimeout: (h) => clearTimeout(h as ReturnType<typeof setTimeout>),
  rng: () => Math.random(),
};

export function createBrain(h: BrainHooks, c: Clock = realClock) {
  const timers = new Set<unknown>();
  let on = false;
  const later = (ms: number, fn: () => void) => {
    const t = c.setTimeout(() => { timers.delete(t); if (on) fn(); }, ms);
    timers.add(t);
  };
  const span = (a: number, b: number) => a + c.rng() * (b - a);
  function blinkLoop() {
    if (h.canMove()) h.blink(c.rng() < 0.125);
    later(span(2400, 6000), blinkLoop);
  }
  function glanceLoop() {
    if (h.canMove()) {
      // always a real glance: 3–6 units to one side (a random (0, 0) would be a glance nobody sees)
      const dx = (c.rng() < 0.5 ? -1 : 1) * Math.round(span(3, 6)), dy = Math.round(span(-4, 2));
      h.look(dx, dy);
      later(span(900, 1700), () => h.look(0, 0));
    }
    later(span(7000, 15000), glanceLoop);
  }
  function wobbleLoop() {
    if (h.canMove()) h.wobble();
    later(span(14000, 28000), wobbleLoop);
  }
  return {
    start() {
      if (on) return;
      on = true;
      later(span(1200, 3000), blinkLoop);
      later(span(4000, 9000), glanceLoop);
      later(span(9000, 18000), wobbleLoop);
    },
    stop() {
      on = false;
      for (const t of timers) c.clearTimeout(t);
      timers.clear();
      h.look(0, 0);
    },
    get running() { return on; },
  };
}
