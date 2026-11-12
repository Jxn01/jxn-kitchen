// @vitest-environment jsdom
/// <reference types="node" />
import { describe, expect, it, vi } from 'vitest';
import { fit } from '../src/lib/fit';

// On the real kiosk a Hungarian home tile title re-fitted ~330×/s (Chrome busy 60 %). Its
// container was shrink-to-fit, so its width depended on the title's own font size: every fit() resized the
// container, the ResizeObserver fired, fit() ran again… This models such a container and counts the font writes.
describe('fit never feeds back on its own resizes', () => {
  it('a container whose width follows the text does not loop', () => {
    let roCb = null as (() => void) | null;   // assigned in a callback: `: T | null = null` narrows it to null
    vi.stubGlobal('ResizeObserver', class { constructor(cb: () => void) { roCb = cb; } observe() {} disconnect() {} });
    const parent = document.createElement('span');
    const node = document.createElement('span');
    parent.appendChild(node);
    document.body.appendChild(parent);
    let font = '';                                     // node.style.fontSize, counted
    let writes = 0;
    Object.defineProperty(node.style, 'fontSize', { get: () => font, set: (v: string) => { font = v; writes++; } });
    const px = () => parseFloat(font || '30');
    // layout model: max font 30 px; the text is 10 px wide per font px; its box is 200 px; the container hugs the text
    vi.spyOn(window, 'getComputedStyle').mockReturnValue({ fontSize: '30px' } as CSSStyleDeclaration);
    Object.defineProperty(node, 'scrollWidth', { get: () => px() * 10 });
    Object.defineProperty(node, 'clientWidth', { get: () => 200 });
    Object.defineProperty(parent, 'clientWidth', { get: () => Math.min(240, px() * 10) });
    const action = fit(node, 'Bevásárlólista');
    expect(px()).toBeLessThanOrEqual(20);             // it shrank to fit
    writes = 0;
    for (let i = 0; i < 50; i++) roCb?.();            // the observer firing because of fit's own change…
    expect(writes).toBe(0);                            // …must not run it again
    action.destroy?.();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('a real change of the available width still re-fits', () => {
    let roCb = null as (() => void) | null;   // assigned in a callback: `: T | null = null` narrows it to null
    vi.stubGlobal('ResizeObserver', class { constructor(cb: () => void) { roCb = cb; } observe() {} disconnect() {} });
    const parent = document.createElement('div');
    const node = document.createElement('span');
    parent.appendChild(node);
    let font = '';
    Object.defineProperty(node.style, 'fontSize', { get: () => font, set: (v: string) => { font = v; } });
    vi.spyOn(window, 'getComputedStyle').mockReturnValue({ fontSize: '30px' } as CSSStyleDeclaration);
    let box = 200;
    Object.defineProperty(node, 'scrollWidth', { get: () => parseFloat(font || '30') * 10 });
    Object.defineProperty(node, 'clientWidth', { get: () => box });
    Object.defineProperty(parent, 'clientWidth', { get: () => box });
    fit(node, 'x');
    expect(parseFloat(font)).toBe(20);
    box = 150;                                          // the window got narrower
    roCb?.();
    expect(parseFloat(font)).toBe(17);                  // min is 55 % of 30 = 17 (rounded)
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });
});

describe('reduced motion (base.css)', () => {
  it('never puts a transition on every property, and leaves the kiosk its motion', async () => {
    const { readFileSync } = await import('node:fs');
    const { join } = await import('node:path');
    const css = readFileSync(join(__dirname, '../src/lib/base.css'), 'utf8');
    const block = css.slice(css.indexOf('@media (prefers-reduced-motion'));
    expect(block).toMatch(/:root:not\(\.kiosk\)/);
    expect(block).not.toMatch(/transition-duration/);
  });
});

describe('fit re-fits when a web font arrives', () => {
  it('runs again on document.fonts loadingdone (the display font is wider than the fallback)', () => {
    vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} });
    const fonts = new EventTarget();
    Object.defineProperty(document, 'fonts', { configurable: true, value: Object.assign(fonts, { ready: new Promise(() => {}) }) });
    const parent = document.createElement('div');
    const node = document.createElement('span');
    parent.appendChild(node);
    let font = '';
    Object.defineProperty(node.style, 'fontSize', { get: () => font, set: (v: string) => { font = v; } });
    vi.spyOn(window, 'getComputedStyle').mockReturnValue({ fontSize: '30px' } as CSSStyleDeclaration);
    let perPx = 5;                                            // the fallback font: narrow, fits at 30 px
    Object.defineProperty(node, 'scrollWidth', { get: () => parseFloat(font || '30') * perPx });
    Object.defineProperty(node, 'clientWidth', { get: () => 200 });
    Object.defineProperty(parent, 'clientWidth', { get: () => 200 });
    const a = fit(node, 'Konyhatudás');
    expect(font).toBe('');
    perPx = 10;                                               // Alfa Slab One arrives: twice as wide
    fonts.dispatchEvent(new Event('loadingdone'));
    expect(parseFloat(font)).toBe(20);
    a.destroy?.();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });
});

// On a phone held sideways (scripts/clip-audit.py) the pantry's category names ("Pasta, rice &
// grains") did not fit even at fit's floor, and fit stopped there, leaving overflow: hidden to cut the end off.
describe('fit never leaves a label cut off', () => {
  // layout model: 10 px of text width per font px; the box is `box` px wide; with white-space normal the text
  // wraps into ceil(width / box) lines of 1.1 × font px each (unless one word is wider than the box)
  function rig(width: number, textOverflow = 'clip') {
    let box = width;
    vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} });
    const parent = document.createElement('div');
    const node = document.createElement('span');
    parent.appendChild(node);
    let font = '';
    Object.defineProperty(node.style, 'fontSize', { get: () => font, set: (v: string) => { font = v; } });
    const px = () => parseFloat(font || '30');
    const wraps = () => node.style.whiteSpace === 'normal';
    vi.spyOn(window, 'getComputedStyle').mockImplementation(() =>
      ({ fontSize: '30px', textOverflow, lineHeight: `${px() * 1.1}px` } as CSSStyleDeclaration));
    Object.defineProperty(node, 'scrollWidth', { get: () => (wraps() ? Math.min(px() * 10, box) : px() * 10) });
    Object.defineProperty(node, 'clientWidth', { get: () => box });
    Object.defineProperty(node, 'scrollHeight', { get: () => Math.ceil(px() * 10 / box) * px() * 1.1 });
    Object.defineProperty(parent, 'clientWidth', { get: () => box });
    return { node, px, setBox: (w: number) => { box = w; } };
  }

  it('wraps onto two lines when even the floor is too wide, at the largest size that fits', () => {
    const { node, px } = rig(120);                 // needs 17 px × 10 = 170 px at the floor: one line cannot fit
    fit(node, 'Pasta, rice & grains');
    expect(node.style.whiteSpace).toBe('normal');
    expect(node.dataset.fitWrapped).toBe('');
    expect(px()).toBe(24);                         // 24 px: 240 px of text = 2 lines of 120; 25 px would be 3 lines
    expect(node.scrollWidth).toBeLessThanOrEqual(node.clientWidth);
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('keeps one line and the ellipsis where the element asks for one (the page header)', () => {
    const { node, px } = rig(120, 'ellipsis');
    fit(node, 'A very long recipe title');
    expect(node.style.whiteSpace).toBe('');
    expect(node.dataset.fitWrapped).toBeUndefined();
    expect(px()).toBe(17);                          // shrunk to the floor, then the ellipsis does the rest
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('goes back to one line when the box grows again', () => {
    const { node, setBox } = rig(120);
    const a = fit(node, 'x');
    expect(node.dataset.fitWrapped).toBe('');
    setBox(400);
    a.update?.();
    expect(node.style.whiteSpace).toBe('');
    expect(node.dataset.fitWrapped).toBeUndefined();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });
});
