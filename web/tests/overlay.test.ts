// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { backspace, idleTimer, insertText, isEditable, keepInTab, pageUrl, shouldRun } from '../src/overlay/core';

describe('overlay: where it runs', () => {
  const app = 'https://kitchen.example.com';
  it.each([
    ['https://www.nosalty.hu', 'https:', true, true],
    ['https://kitchen.example.com', 'https:', true, false],   // our own app has its own UI
    ['null', 'chrome-error:', true, false],
    ['null', 'about:', true, false],
    ['https://ads.example', 'https:', false, false],     // iframes (ads, videos) never get a bar
  ])('%s %s top=%s -> %s', (origin, protocol, top, want) => {
    expect(shouldRun({ origin, protocol }, app, top)).toBe(want);
  });
});

describe('overlay: which URL Save sends', () => {
  it('the canonical link when it is a web link on the same site, else the address', () => {
    document.head.innerHTML = '<link rel="canonical" href="https://www.nosalty.hu/recept/paprikas-csirke">';
    expect(pageUrl(document, { href: 'https://www.nosalty.hu/recept/paprikas-csirke?utm=x', origin: 'https://www.nosalty.hu' }))
      .toBe('https://www.nosalty.hu/recept/paprikas-csirke');
    document.head.innerHTML = '<link rel="canonical" href="https://evil.example/x">';
    expect(pageUrl(document, { href: 'https://www.nosalty.hu/a', origin: 'https://www.nosalty.hu' })).toBe('https://www.nosalty.hu/a');
  });
});

describe('overlay: typing into the site', () => {
  it('reaches React-controlled inputs (native value setter + input event)', () => {
    const el = document.createElement('input');
    document.body.appendChild(el);
    // React shadows `value` on the instance and ignores writes through it; only the prototype setter is real
    let reactSaw = '';
    Object.defineProperty(el, 'value', { configurable: true, get() { return Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.get!.call(this); }, set(v) { reactSaw = v; } });
    const events: string[] = [];
    el.addEventListener('input', () => events.push('input'));
    el.focus();
    insertText(el, 'g'); insertText(el, 'ulyás');
    expect(Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.get!.call(el)).toBe('gulyás');
    expect(reactSaw).toBe('');
    expect(events.length).toBe(2);
    backspace(el);
    expect(Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.get!.call(el)).toBe('gulyá');
  });
  it('inserts at the cursor in a textarea', () => {
    const t = document.createElement('textarea');
    t.value = 'ab'; t.setSelectionRange(1, 1);
    insertText(t, 'X');
    expect(t.value).toBe('aXb');
  });
  it('knows what is editable', () => {
    const mk = (h: string) => { const d = document.createElement('div'); d.innerHTML = h; return d.firstElementChild!; };
    expect(isEditable(mk('<input type="search">'))).toBe(true);
    expect(isEditable(mk('<input type="checkbox">'))).toBe(false);
    expect(isEditable(mk('<textarea></textarea>'))).toBe(true);
    expect(isEditable(mk('<div contenteditable="true"></div>'))).toBe(true);
    expect(isEditable(mk('<button></button>'))).toBe(false);
  });
});

describe('overlay: one tab only', () => {
  it('links that would open a new tab open here; window.open too', () => {
    const go = vi.fn();
    const win = { open: (() => null) as any, location: { href: 'https://www.nosalty.hu/' } };
    keepInTab(document, win as any, go);
    document.body.innerHTML = '<a id="a" href="https://www.nosalty.hu/recept/x" target="_blank">x</a><a id="b" href="/y">y</a>';
    const e = new MouseEvent('click', { bubbles: true, cancelable: true });
    document.getElementById('a')!.dispatchEvent(e);
    expect(e.defaultPrevented).toBe(true);
    expect(go).toHaveBeenCalledWith('https://www.nosalty.hu/recept/x');
    const e2 = new MouseEvent('click', { bubbles: true, cancelable: true });
    document.getElementById('b')!.dispatchEvent(e2);
    expect(e2.defaultPrevented).toBe(false);                    // a normal link is left alone
    win.open('https://www.nosalty.hu/z');
    expect(go).toHaveBeenLastCalledWith('https://www.nosalty.hu/z');
  });
});

describe('overlay: never stuck on a site', () => {
  afterEach(() => vi.useRealTimers());
  it('goes back to the kitchen after the idle time without a touch; a touch restarts it', () => {
    vi.useFakeTimers();
    const onIdle = vi.fn();
    idleTimer(document, 1000, onIdle);
    vi.advanceTimersByTime(900);
    document.dispatchEvent(new Event('pointerdown'));
    vi.advanceTimersByTime(900);
    expect(onIdle).not.toHaveBeenCalled();
    vi.advanceTimersByTime(100);
    expect(onIdle).toHaveBeenCalledOnce();
  });
});

import { takeSecrets } from '../src/overlay/core';

describe('overlay: the save channel is ours alone', () => {
  it('takes the config (with its secret) and the binding, then removes both globals before any site script runs', () => {
    const calls: string[] = [];
    const w: any = { __kitchenOverlayConfig: { app: 'https://kitchen.example.com/?kiosk=1', lang: 'hu', idleMinutes: 2, nonce: 's3cret' },
                     kitchenSave: (p: string) => calls.push(p) };
    const { cfg, save } = takeSecrets(w);
    expect(cfg.nonce).toBe('s3cret');
    expect('__kitchenOverlayConfig' in w).toBe(false);
    expect('kitchenSave' in w).toBe(false);            // a site's script can no longer call it…
    save!('{"url":"x"}');                                // …but we still can
    expect(calls).toEqual(['{"url":"x"}']);
  });
  it('a frame without the agent gives no binding and defaults', () => {
    const { cfg, save } = takeSecrets({} as any);
    expect(save).toBeNull();
    expect(cfg.app).toContain('kitchen.example.com');
  });
});

import { keepAttached } from '../src/overlay/core';

describe('overlay: survives the site rebuilding its document', () => {
  it('puts its host back whenever the page removes it', async () => {
    const host = document.createElement('kitchen-overlay');
    document.documentElement.appendChild(host);
    keepAttached(document, host);
    host.remove();                                   // what Next.js hydration did
    await new Promise((r) => setTimeout(r, 0));      // mutation observers run as microtasks
    expect(host.isConnected).toBe(true);
    document.documentElement.replaceChildren(document.createElement('head'), document.createElement('body'));
    await new Promise((r) => setTimeout(r, 0));
    expect(host.isConnected).toBe(true);
  });
});
