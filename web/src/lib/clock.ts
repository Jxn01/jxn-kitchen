// A `now` store that ticks once a minute, exactly on the minute (no 1-second repaint on a 24/7 Atom).
import { readable } from 'svelte/store';

export function msToNextMinute(d: Date): number {
  const ms = d.getTime() % 60000;
  return 60000 - ms;
}

export const now = readable(new Date(), (set) => {
  let timer: ReturnType<typeof setTimeout>;
  const tick = () => {
    const d = new Date();
    set(d);
    timer = setTimeout(tick, msToNextMinute(d) + 20);
  };
  timer = setTimeout(tick, msToNextMinute(new Date()) + 20);
  return () => clearTimeout(timer);
});
