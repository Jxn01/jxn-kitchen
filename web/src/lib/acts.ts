// Episodic ambient animation: one short "act" at a time, a random 15–40 s rest between acts (doubled
// at night), nothing scheduled while the page is hidden. Between acts NOTHING animates, which is what keeps the
// Atom's CPU low 24/7 (measured: ~1 % CPU per continuously animated element).
export interface Act {
  id: string;
  run: () => Promise<void>;
  available?: () => boolean;   // e.g. idle-scene-only props
}

export interface SchedulerOptions {
  acts: Act[];
  minGapMs?: number;
  maxGapMs?: number;
  rng?: () => number;
  isHidden?: () => boolean;
}

export function createScheduler(o: SchedulerOptions) {
  const min = o.minGapMs ?? 15000;
  const max = o.maxGapMs ?? 40000;
  const rng = o.rng ?? Math.random;
  const isHidden = o.isHidden ?? (() => typeof document !== 'undefined' && document.hidden);
  let night = false;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let running = false;
  let started = false;
  let last: string | null = null;

  function scheduleNext() {
    if (!started || timer || running || isHidden()) return;
    const gap = (min + rng() * (max - min)) * (night ? 2 : 1);
    timer = setTimeout(fire, gap);
  }

  async function fire() {
    timer = null;
    if (!started) return;
    if (isHidden()) return;                         // wake() reschedules when visible again
    const pool = o.acts.filter((a) => a.id !== last && (a.available?.() ?? true));
    const choice = pool.length ? pool[Math.floor(rng() * pool.length) % pool.length] : null;
    if (choice) {
      running = true;
      last = choice.id;
      try { await choice.run(); } catch { /* an act failing must not stop the show */ }
      running = false;
    }
    scheduleNext();
  }

  return {
    start() { started = true; scheduleNext(); },
    stop() { started = false; if (timer) { clearTimeout(timer); timer = null; } },
    wake() { scheduleNext(); },
    setNight(v: boolean) { night = v; },
    get running() { return running; },
  };
}

/** An act that sets some state, waits for its animation's known duration, then clears it. */
export function timedAct(id: string, ms: number, begin: () => void, end: () => void, available?: () => boolean): Act {
  return {
    id, available,
    run: () => new Promise<void>((resolve) => { begin(); setTimeout(() => { end(); resolve(); }, ms); }),
  };
}
