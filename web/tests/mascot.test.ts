/// <reference types="node" />
import { describe, expect, it } from 'vitest';
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { ACTIONS, AMBIENT, createBrain, NIGHT_AMBIENT } from '../src/lib/mascot';

// Chrome composites transform/opacity animations of HTML elements, never of svg children (<g>, <path>, … — even
// through a class): those repaint the svg on the main thread every frame, the "≈1 % CPU per animated element" the
// spec measured. So the rig animates only its divs. This scans a component: every class used on an svg element (or
// the element names themselves) must never be the target of an animation or a transition, and keyframes may touch
// only transform and opacity.
const SVG_TAGS = ['svg', 'g', 'path', 'circle', 'ellipse', 'rect', 'line', 'polygon', 'polyline', 'text'];

export function svgAnimationProblems(source: string): string[] {
  const style = /<style>([\s\S]*?)<\/style>/.exec(source)?.[1] ?? '';
  const markup = source.replace(/<style>[\s\S]*?<\/style>/, '');
  const svgClasses = new Set<string>();
  for (const m of markup.matchAll(/<(svg|g|path|circle|ellipse|rect|line|polygon|polyline|text)\b[^>]*?\bclass="([^"{}]+)"/g)) {
    for (const c of m[2].split(/\s+/)) if (c) svgClasses.add(c);
  }
  const bad: string[] = [];
  for (const m of markup.matchAll(/<(g|path|circle|ellipse|rect|line|polygon|polyline|text)\b[^>]*\bstyle="[^"]*(transition|animation)/g)) {
    bad.push(`inline ${m[2]} on <${m[1]}>`);
  }
  const noKeyframes = style.replace(/@keyframes[^{]+\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}/g, '');
  for (const m of noKeyframes.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    const [, sel, body] = m;
    if (!/(^|;|\s)(animation|transition)(-name)?\s*:/.test(body) || /^\s*(animation|transition)-(delay|iteration-count|fill-mode)/.test(body.trim())) continue;
    if (!/(^|;|\s)(animation|transition)\s*:/.test(body)) continue;
    for (const one of sel.split(',')) {
      const last = one.trim().split(/[\s>+~]+/).pop() ?? '';
      const tag = /^[a-z]+/.exec(last)?.[0];
      if (tag && SVG_TAGS.includes(tag)) bad.push(`${one.trim()} (svg element)`);
      for (const c of last.match(/\.[\w-]+/g) ?? []) if (svgClasses.has(c.slice(1))) bad.push(`${one.trim()} (svg class ${c})`);
    }
  }
  for (const k of style.matchAll(/@keyframes\s+([\w-]+)\s*\{((?:[^{}]*\{[^{}]*\})*)[^{}]*\}/g)) {
    for (const d of k[2].matchAll(/([a-z-]+)\s*:/g)) {
      if (!['transform', 'opacity', 'animation-timing-function'].includes(d[1])) bad.push(`@keyframes ${k[1]} animates ${d[1]}`);
    }
  }
  return bad;
}

const read = (p: string) => readFileSync(join(__dirname, '../src', p), 'utf8');

describe('the mascot animates only compositor-friendly things', () => {
  it('positive control: the old pan (animating classes on svg ellipses/g) is caught', () => {
    const old = `<svg><g class="egg"><ellipse class="eye" cx="1" /></g></svg>
      <style>.act-blink .eye { animation: blink .5s; } .act-sizzle .egg { animation: s 1s; } @keyframes s { 0% { fill: red; } }</style>`;
    const bad = svgAnimationProblems(old);
    expect(bad.some((b) => b.includes('.eye'))).toBe(true);
    expect(bad.some((b) => b.includes('.egg'))).toBe(true);
    expect(bad.some((b) => b.includes('animates fill'))).toBe(true);
  });
  it('the mascot and the idle scene animate divs only, and only transform/opacity', () => {
    for (const f of ['components/Mascot.svelte', 'components/MascotBubble.svelte', 'components/scene/Counter.svelte',
                     'components/scene/Board.svelte', 'components/scene/Herbs.svelte', 'screens/Idle.svelte', 'screens/Home.svelte',
                     'components/illus/Doneness.svelte', 'components/illus/Sugar.svelte', 'components/illus/Smoke.svelte',
                     'components/illus/Oven.svelte', 'components/illus/Cuts.svelte', 'components/illus/Blend.svelte',
                     'components/illus/Balance.svelte', 'components/TimerDone.svelte', 'components/MascotNote.svelte']) {
      expect(svgAnimationProblems(read(f)), f).toEqual([]);
    }
  });
  it('every action has its CSS', () => {
    const css = read('components/Mascot.svelte');
    for (const id of Object.keys(ACTIONS)) expect(css.includes(`.a-${id} `), id).toBe(true);
    for (const id of [...AMBIENT, ...NIGHT_AMBIENT]) expect(ACTIONS[id], id).toBeTruthy();
  });
});

describe('the brain keeps the mascot alive between acts', () => {
  function fakeClock(seq = [0.5, 0.2, 0.8, 0.35, 0.65, 0.1, 0.9]) {
    let now = 0, i = 0;
    const q: { at: number; fn: () => void; id: number }[] = [];
    let id = 0;
    return {
      clock: {
        setTimeout: (fn: () => void, ms: number) => { const h = ++id; q.push({ at: now + ms, fn, id: h }); return h; },
        clearTimeout: (h: unknown) => { const k = q.findIndex((x) => x.id === h); if (k >= 0) q.splice(k, 1); },
        rng: () => seq[i++ % seq.length],
      },
      advance(ms: number) {
        const end = now + ms;
        for (;;) {
          q.sort((a, b) => a.at - b.at);
          const next = q[0];
          if (!next || next.at > end) break;
          q.shift(); now = next.at; next.fn();
        }
        now = end;
      },
      pending: () => q.length,
    };
  }
  it('blinks every few seconds, glances and returns, wobbles the yolk', () => {
    const f = fakeClock();
    const log: string[] = [];
    const b = createBrain({ blink: () => log.push('blink'), look: (x, y) => log.push(`look ${x},${y}`), wobble: () => log.push('wobble'), canMove: () => true }, f.clock);
    b.start();
    f.advance(60000);
    const blinks = log.filter((l) => l === 'blink').length;
    expect(blinks).toBeGreaterThanOrEqual(10);                 // ~ every 4.2 s at rng 0.5
    expect(blinks).toBeLessThanOrEqual(25);
    expect(log.filter((l) => l.startsWith('look') && l !== 'look 0,0').length).toBeGreaterThanOrEqual(3);
    expect(log).toContain('look 0,0');                         // every glance comes back
    expect(log.filter((l) => l === 'wobble').length).toBeGreaterThanOrEqual(2);
  });
  it('does nothing while it may not move, and stop() clears every timer', () => {
    const f = fakeClock();
    const log: string[] = [];
    const b = createBrain({ blink: () => log.push('blink'), look: () => {}, wobble: () => log.push('wobble'), canMove: () => false }, f.clock);
    b.start();
    f.advance(30000);
    expect(log).toEqual([]);
    b.stop();
    expect(f.pending()).toBe(0);
  });
});


describe('the brain runs on the real timers', () => {
  it('works with a browser-strict setTimeout (called as a method of another object it throws, like Chrome)', async () => {
    const realSet = globalThis.setTimeout, realClear = globalThis.clearTimeout;
    const strict = function (this: unknown, fn: () => void, ms?: number) {
      if (this !== undefined && this !== globalThis) throw new TypeError('Illegal invocation');
      return realSet(fn, ms);
    };
    globalThis.setTimeout = strict as unknown as typeof setTimeout;
    try {
      const b = createBrain({ blink: () => {}, look: () => {}, wobble: () => {}, canMove: () => true });
      expect(() => b.start()).not.toThrow();
      b.stop();
    } finally {
      globalThis.setTimeout = realSet; globalThis.clearTimeout = realClear;
    }
  });
});


// On the kiosk ANY animation running at 60 Hz costs ~14 % CPU, whatever its size (compositor + GPU process + DWM
// present per frame — measured 2026-10-11: a 120 px and a 360 px mascot cost the same). So nothing may run forever at
// full rate: a never-ending animation is stepped (identical frames between steps are not drawn), or it is marked
// `episodic:` with what ends it.
export function foreverProblems(src: string): string[] {
  return src.split('\n').filter((l) => /\binfinite\b/.test(l) && !/steps\(/.test(l) && !/episodic:/.test(l)).map((l) => l.trim());
}

describe('nothing animates forever at 60 Hz', () => {
  const walk = (d: string): string[] => readdirSync(d, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? walk(join(d, e.name)) : /\.(svelte|css)$/.test(e.name) ? [join(d, e.name)] : []);
  const files = walk(join(__dirname, '../src')).map((f) => [f.split('/src/')[1], readFileSync(f, 'utf8')] as const);
  it('sees the app (the walk found the files that must be checked)', () => {
    expect(files.map(([n]) => n)).toEqual(expect.arrayContaining(['components/Mascot.svelte', 'screens/Idle.svelte', 'lib/base.css']));
  });
  it('positive control: the old smooth breath is caught', () => {
    expect(foreverProblems('  .breathe .squash { animation: breathe 4.2s ease-in-out infinite; }')).toHaveLength(1);
    expect(foreverProblems('  .breathe .squash { animation: breathe 4.2s steps(5, jump-end) infinite; }')).toHaveLength(0);
  });
  it.each(files)('%s', (_name, src) => {
    expect(foreverProblems(src)).toEqual([]);
  });
});
