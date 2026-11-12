// The Browse overlay's logic, kept free of UI so it is unit-tested (tests/overlay.test.ts). The overlay runs inside
// third-party recipe sites on the kiosk (injected by the kiosk agent over CDP), so everything here must cope with
// whatever the site does: React-controlled inputs, shadow roots, new-tab links, its own scripts.

/** Only on real web pages in the top frame, never on our own app (it has its own UI) or Chrome's error pages. */
export function shouldRun(loc: { origin: string; protocol: string }, appOrigin: string, isTop: boolean): boolean {
  if (!isTop) return false;
  if (loc.protocol !== 'https:' && loc.protocol !== 'http:') return false;
  return loc.origin !== appOrigin;
}

/** What "Save recipe" sends: the page's canonical link if it is a web link on the same site, else its address. */
export function pageUrl(doc: Document, loc: { href: string; origin: string }): string {
  const c = doc.querySelector<HTMLLinkElement>('link[rel="canonical"]')?.href;
  try {
    if (c) { const u = new URL(c); if ((u.protocol === 'https:' || u.protocol === 'http:') && u.origin === loc.origin) return u.href; }
  } catch { /* a broken canonical: use the address */ }
  return loc.href;
}

const TEXT_TYPES = new Set(['text', 'search', 'email', 'url', 'tel', 'number', 'password', '']);
export function isEditable(el: Element | null): el is HTMLInputElement | HTMLTextAreaElement | HTMLElement {
  if (!el) return false;
  if (el instanceof HTMLInputElement) return TEXT_TYPES.has((el.getAttribute('type') ?? '').toLowerCase()) && !el.readOnly && !el.disabled;
  if (el instanceof HTMLTextAreaElement) return !el.readOnly && !el.disabled;
  if (!(el instanceof HTMLElement)) return false;
  const ce = el.getAttribute('contenteditable');
  return el.isContentEditable === true || ce === '' || ce === 'true' || ce === 'plaintext-only';
}

// React (Street Kitchen is Next.js) keeps its own copy of an input's value and ignores writes through the instance:
// only the PROTOTYPE's setter plus an `input` event updates it. Write the same way for every framework.
function setValue(el: HTMLInputElement | HTMLTextAreaElement, v: string): void {
  const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(proto, 'value')!.set!.call(el, v);
  el.dispatchEvent(new Event('input', { bubbles: true }));
}
function realValue(el: HTMLInputElement | HTMLTextAreaElement): string {
  const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  return Object.getOwnPropertyDescriptor(proto, 'value')!.get!.call(el);
}
function caret(el: HTMLInputElement | HTMLTextAreaElement): [number, number] | null {
  try { return el.selectionStart == null ? null : [el.selectionStart, el.selectionEnd ?? el.selectionStart]; } catch { return null; }   // email/number have none
}

export function insertText(el: Element, text: string): void {
  if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) {
    const v = realValue(el);
    const c = caret(el);
    const [a, b] = c ?? [v.length, v.length];
    setValue(el, v.slice(0, a) + text + v.slice(b));
    try { el.setSelectionRange(a + text.length, a + text.length); } catch { /* no selection API */ }
  } else {
    document.execCommand('insertText', false, text);              // contenteditable
  }
}

export function backspace(el: Element): void {
  if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) {
    const v = realValue(el);
    const c = caret(el);
    const [a, b] = c ?? [v.length, v.length];
    const from = a === b ? Math.max(0, a - 1) : a;
    setValue(el, v.slice(0, from) + v.slice(b));
    try { el.setSelectionRange(from, from); } catch { /* no selection API */ }
  } else {
    document.execCommand('delete');
  }
}

/** Enter: what a real key would do — key events for sites that listen for them, then submit the form if nobody
 *  handled it. Synthetic events are untrusted, but frameworks act on them; forms need requestSubmit(). */
export function enter(el: Element): void {
  const init = { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true } as KeyboardEventInit;
  const down = new KeyboardEvent('keydown', init);
  el.dispatchEvent(down);
  el.dispatchEvent(new KeyboardEvent('keypress', init));
  el.dispatchEvent(new KeyboardEvent('keyup', init));
  if (el instanceof HTMLTextAreaElement) { insertText(el, '\n'); return; }
  const form = (el as HTMLInputElement).form;
  if (!down.defaultPrevented && form) { try { form.requestSubmit(); } catch { form.submit(); } }
}

/** The kiosk has ONE tab: a link meant for a new tab, or window.open, navigates this one instead. */
export function keepInTab(doc: Document, win: Window, navigate: (url: string) => void): void {
  doc.addEventListener('click', (e) => {
    const a = (e.composedPath() as Element[]).find((n) => n instanceof HTMLAnchorElement) as HTMLAnchorElement | undefined;
    if (!a || !a.href) return;
    const target = (a.getAttribute('target') ?? '').toLowerCase();
    if (target && target !== '_self' && target !== '_top' && target !== '_parent') {
      e.preventDefault();
      navigate(a.href);
    }
  }, true);
  win.open = ((url?: string | URL) => {
    if (url) navigate(new URL(String(url), win.location.href).href);
    return null;
  }) as typeof win.open;
}

/** No touch for `ms` -> onIdle (back to the kitchen app, whose idle scene takes over). Any touch or key restarts it. */
export function idleTimer(doc: Document, ms: number, onIdle: () => void): () => void {
  let t = setTimeout(onIdle, ms);
  const reset = () => { clearTimeout(t); t = setTimeout(onIdle, ms); };
  for (const ev of ['pointerdown', 'keydown', 'wheel']) doc.addEventListener(ev, reset, { capture: true, passive: true });
  return () => clearTimeout(t);
}

export interface OverlayConfig { app: string; lang: 'en' | 'hu'; idleMinutes: number; build?: string; nonce?: string }

/** Runs FIRST, in every frame, before any of the page's own scripts: take the agent's config (it carries the
 *  session's secret) and the kitchenSave binding into this closure, and delete both globals — so neither a site's
 *  script nor an ad iframe can read the secret or call the binding (security review, 2026-10-10). */
export function takeSecrets(w: Window & Record<string, any>): { cfg: OverlayConfig; save: ((p: string) => void) | null } {
  const cfg: OverlayConfig = { app: 'https://kitchen.example.com/?kiosk=1', lang: 'hu', idleMinutes: 2, ...(w.__kitchenOverlayConfig ?? {}) };
  const b = w.kitchenSave;
  const save = typeof b === 'function' ? (p: string) => b.call(w, p) : null;
  try { delete w.__kitchenOverlayConfig; } catch { w.__kitchenOverlayConfig = undefined; }
  try { delete w.kitchenSave; } catch { w.kitchenSave = undefined; }
  return { cfg, save };
}

/** Some sites (Next.js on Street Kitchen) rebuild their document after load and throw away nodes they don't know —
 *  our bar vanished 3–6 s after every page load there (measured on the kiosk). Watch the document and put the host
 *  back whenever it is removed. */
export function keepAttached(doc: Document, host: Element): MutationObserver {
  const mo = new MutationObserver(() => {
    if (!host.isConnected) (doc.documentElement ?? doc.appendChild(doc.createElement('html'))).appendChild(host);
  });
  mo.observe(doc, { childList: true, subtree: true });
  return mo;
}
