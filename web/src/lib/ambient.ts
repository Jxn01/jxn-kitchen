// The ambient acts wired to stores the screens read. One scheduler for the whole app: one act at a
// time, a random rest between acts, nothing while the page is hidden. The mascot has its own small life between acts
// (blinks, glances — lib/mascot.ts); the scheduler hands it the bigger ones, and plays the idle scene's props.
import { get, writable } from 'svelte/store';
import { createScheduler, timedAct, type Act } from './acts';
import { ACTIONS, AMBIENT, NIGHT_AMBIENT } from './mascot';
import { route } from './router';
import { HOME_TILES } from './tiles';

/** The act the visible mascot (home or idle) should play; `key` makes a repeat of the same act play again. */
export const mascotCue = writable<{ id: string; key: number } | null>(null);
export const wiggleTile = writable<string | null>(null);  // Home: one tile's icon plate wiggles
export const propAct = writable<string | null>(null);     // Idle: chop | herbs | chicken

let cueKey = 0;
/** Ask the visible mascot to play an act now (also used by reactions: a saved recipe, a toggle…). */
export function cueMascot(id: string): void { mascotCue.set({ id, key: ++cueKey }); }

const onHome = () => get(route).name === 'home';
const onIdle = () => get(route).name === 'idle';
let night = false;

const mascotAct = (id: string, nightAct: boolean): Act =>
  timedAct(`m-${id}${nightAct ? '-n' : ''}`, ACTIONS[id].ms + 300, () => cueMascot(id), () => {},
           () => (onHome() || onIdle()) && night === nightAct && (!nightAct || onIdle()));

export function createAmbient(gaps: { minGapMs?: number; maxGapMs?: number } = {}) {
  const s = createScheduler({
    minGapMs: gaps.minGapMs ?? 8000,
    maxGapMs: gaps.maxGapMs ?? 22000,
    acts: [
      ...AMBIENT.map((id) => mascotAct(id, false)),
      ...NIGHT_AMBIENT.map((id) => mascotAct(id, true)),
      timedAct('tile', 1100,
        () => wiggleTile.set(HOME_TILES[Math.floor(Math.random() * HOME_TILES.length)].id),
        () => wiggleTile.set(null), () => onHome() && !night),
      timedAct('chicken', 7400, () => propAct.set('chicken'), () => propAct.set(null), () => onIdle() && !night),
      timedAct('chop', 3000, () => propAct.set('chop'), () => propAct.set(null), () => onIdle() && !night),
      timedAct('herbs', 2700, () => propAct.set('herbs'), () => propAct.set(null), () => onIdle() && !night),
    ],
  });
  return {
    start: s.start, stop: s.stop, wake: s.wake,
    setNight(v: boolean) { night = v; s.setNight(v); },
    get running() { return s.running; },
  };
}
