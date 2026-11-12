// Idle detection for the kiosk. After `timeoutMs` without a touch -> onIdle (the idle scene). The touch that wakes
// it is CONSUMED: its pointerdown is cancelled and the click that follows within 600 ms is swallowed, so the finger
// that wakes the screen never presses whatever happens to be under it.
export interface IdleOptions {
  timeoutMs: number;
  onIdle: () => void;
  onWake: () => void;
  target?: Document | HTMLElement;
  /** True while the idle SCREEN is showing. A touch then always wakes, even when this controller never went idle
   *  itself (a reload on #/idle, or Back into it) — otherwise every tap just re-armed the timer and the kiosk froze. */
  onIdleScreen?: () => boolean;
  /** While true the screen never goes idle (cook mode: hands are busy, the step must stay up). */
  holdIf?: () => boolean;
}

const SWALLOW_MS = 600;

export function createIdle(o: IdleOptions) {
  const target: any = o.target ?? document;
  let timeoutMs = o.timeoutMs;
  let idle = false;
  let swallowUntil = 0;
  let timer: ReturnType<typeof setTimeout> | null = null;

  function arm() {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      if (o.holdIf?.()) { arm(); return; }
      idle = true;
      o.onIdle();
    }, timeoutMs);
  }

  function onDown(e: Event) {
    if (idle || o.onIdleScreen?.()) {
      e.preventDefault();
      e.stopPropagation();
      idle = false;
      swallowUntil = Date.now() + SWALLOW_MS;
      o.onWake();
    }
    arm();
  }

  function onClick(e: Event) {
    if (Date.now() < swallowUntil) { e.preventDefault(); e.stopPropagation(); }
  }

  target.addEventListener('pointerdown', onDown, true);
  target.addEventListener('keydown', onDown, true);
  target.addEventListener('click', onClick, true);
  arm();

  return {
    isIdle: () => idle,
    setTimeoutMs(ms: number) { timeoutMs = ms; if (!idle) arm(); },
    destroy() {
      if (timer) clearTimeout(timer);
      target.removeEventListener('pointerdown', onDown, true);
      target.removeEventListener('keydown', onDown, true);
      target.removeEventListener('click', onClick, true);
    },
  };
}
