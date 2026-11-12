// The Browse overlay: our Home · Back · Save bar and on-screen keyboard on top of third-party recipe sites, on the
// kiosk only. The kiosk agent injects this file over CDP into every page (Page.addScriptToEvaluateOnNewDocument),
// after setting window.__kitchenOverlayConfig = {app, lang, idleMinutes, build}. "Save" calls the agent's CDP binding
// window.kitchenSave(JSON) and the agent answers through window.__kitchenOverlay.saved(result).
// Everything lives in a closed Shadow DOM so the site's CSS can't touch it (and ours can't touch the site).
import en from '../i18n/en.json';
import hu from '../i18n/hu.json';
import icons from './icons.json';
import { LAYOUTS, type KeyDef } from '../lib/keyboard-layouts';
import { P } from '../lib/palette';
import { backspace, enter, idleTimer, insertText, isEditable, keepAttached, keepInTab, pageUrl, shouldRun, takeSecrets } from './core';

interface SaveResult { ok: boolean; id?: number; draft?: boolean; code?: string }
type W = Window & { __kitchenOverlay?: unknown };

const w = window as W;
const { cfg, save } = takeSecrets(window as Window & Record<string, any>);     // first thing, in every frame
const appOrigin = new URL(cfg.app).origin;

if (!w.__kitchenOverlay && shouldRun(location, appOrigin, window.top === window)) start();

function start() {
  const dict = (cfg.lang === 'en' ? en : hu) as Record<string, string>;
  const tr = (k: string) => dict[k] ?? (en as Record<string, string>)[k] ?? k;
  const goApp = (hash = '') => { location.href = cfg.app + hash; };
  let toast: (text: string, action?: { label: string; run: () => void }) => void = () => {};

  w.__kitchenOverlay = {
    build: cfg.build,
    saved(r: SaveResult) {
      if (!r.ok) { toast(tr(r.code === 'unavailable' ? 'overlay.unavailable' : r.code === 'busy' ? 'overlay.busy' : 'overlay.failed')); return; }
      toast(tr(r.draft ? 'overlay.draft' : 'overlay.saved'),
            { label: tr('overlay.open'), run: () => goApp(`#/recipe/${r.id}${r.draft ? '/edit' : ''}`) });
    },
  };
  keepInTab(document, window, (url) => { location.href = url; });
  idleTimer(document, Math.max(1, cfg.idleMinutes) * 60000, () => goApp('#/idle'));

  const mount = () => {
    const host = document.createElement('kitchen-overlay');
    host.setAttribute('style', 'all: initial; position: fixed; top: 0; left: 0; width: 0; height: 0; z-index: 2147483647;');
    const root = host.attachShadow({ mode: 'closed' });
    // The agent does NOT switch the site's CSP off: styles go in as a constructable sheet (CSSOM,
    // not governed by style-src), markup through a Trusted Types policy where the browser enforces them.
    let styled = false;
    try {
      const sheet = new CSSStyleSheet();
      sheet.replaceSync(css(appOrigin));
      root.adoptedStyleSheets = [sheet];
      styled = true;
    } catch { /* old engine: a <style> element below */ }
    setHTML(root, `${styled ? '' : `<style>${css(appOrigin)}</style>`}
      <div class="bar" part="bar">
        <button class="b home" aria-label="${tr('overlay.home')}">${svg('home')}</button>
        <button class="b back" aria-label="${tr('overlay.back')}">${svg('back')}</button>
        <button class="b save">${svg('save')}<span>${tr('overlay.save')}</span></button>
      </div>
      <div class="toast" hidden><span class="t"></span><button class="act" hidden></button></div>
      <div class="kb" hidden></div>`);
    document.documentElement.appendChild(host);
    keepAttached(document, host);
    try {   // the kiosk shows Windows' classic scrollbars on sites; touch scrolls anyway (same as the app does)
      const bars = new CSSStyleSheet();
      bars.replaceSync('html, body { scrollbar-width: none !important; }');
      document.adoptedStyleSheets = [...document.adoptedStyleSheets, bars];
    } catch { /* cosmetic */ }
    const $ = <T extends Element>(s: string) => root.querySelector(s) as T;

    // --- the bar
    $<HTMLButtonElement>('.home').onclick = () => goApp();
    $<HTMLButtonElement>('.back').onclick = () => (history.length > 1 ? history.back() : goApp());
    $<HTMLButtonElement>('.save').onclick = () => {
      if (!save) { toast(tr('overlay.unavailable')); return; }
      toast(tr('overlay.saving'));
      save(JSON.stringify({ url: pageUrl(document, location), nonce: cfg.nonce }));
    };

    // --- the toast
    let hideT: ReturnType<typeof setTimeout> | undefined;
    toast = (text, action) => {
      const el = $<HTMLDivElement>('.toast'), act = $<HTMLButtonElement>('.act');
      $<HTMLSpanElement>('.t').textContent = text;
      act.hidden = !action;
      if (action) { act.textContent = action.label; act.onclick = () => { el.hidden = true; action.run(); }; }
      el.hidden = false;
      clearTimeout(hideT);
      hideT = setTimeout(() => { el.hidden = true; }, 7000);
    };

    // --- the keyboard, for the site's own inputs
    const kb = $<HTMLDivElement>('.kb');
    let target: Element | null = null;
    let layer: 'letters' | 'num' = 'letters', kbLang: 'en' | 'hu' = cfg.lang, shift = false;
    const draw = () => {
      kb.textContent = '';
      for (const row of layer === 'num' ? LAYOUTS.num : LAYOUTS[kbLang]) {
        const r = document.createElement('div'); r.className = 'row';
        for (const key of row) r.appendChild(keyButton(key));
        kb.appendChild(r);
      }
    };
    const keyButton = (key: KeyDef) => {
      const b = document.createElement('button');
      const k = typeof key === 'string' ? key : key.k;
      b.className = 'key' + (typeof key === 'string' ? '' : ' special') + (k === 'shift' && shift ? ' on' : '');
      b.style.flexGrow = String(typeof key === 'string' ? 1 : (key.w ?? 1));
      if (k === 'lang') setHTML(b, svg('language') + kbLang.toUpperCase());
      else b.textContent = typeof key === 'string' ? (shift ? key.toLocaleUpperCase('hu') : key)
        : ({ shift: '⇧', back: '⌫', space: tr('kb.space'), enter: target instanceof HTMLTextAreaElement ? '↵' : tr('kb.done'),
             mode: layer === 'num' ? tr('kb.letters') : tr('kb.numbers') } as Record<string, string>)[k];
      b.addEventListener('pointerdown', (e) => { e.preventDefault(); press(k, typeof key === 'string'); });   // keep the site's focus
      return b;
    };
    const press = (k: string, letter: boolean) => {
      if (!target) return;
      if (k === 'shift') { shift = !shift; draw(); return; }
      if (k === 'mode') { layer = layer === 'num' ? 'letters' : 'num'; draw(); return; }
      if (k === 'lang') { kbLang = kbLang === 'en' ? 'hu' : 'en'; draw(); return; }
      if (k === 'back') { backspace(target); return; }
      if (k === 'space') { insertText(target, ' '); return; }
      if (k === 'enter') {
        const t = target;
        enter(t);
        if (!(t instanceof HTMLTextAreaElement)) { (t as HTMLElement).blur(); close(); }
        return;
      }
      insertText(target, shift ? k.toLocaleUpperCase('hu') : k);
      if (letter && shift) { shift = false; draw(); }
    };
    const open = (el: Element) => {
      target = el; draw(); kb.hidden = false; host.classList.add('kb-open');
      root.querySelector('.bar')!.classList.add('up');
      const r = el.getBoundingClientRect();
      if (r.bottom > innerHeight - 320) (el as HTMLElement).scrollIntoView({ block: 'center' });
    };
    const close = () => { target = null; kb.hidden = true; root.querySelector('.bar')!.classList.remove('up'); };
    document.addEventListener('focusin', (e) => {
      const el = e.composedPath()[0] as Element;           // inputs inside the site's own shadow roots too
      if (isEditable(el)) open(el);
    }, true);
    document.addEventListener('focusout', (e) => {
      const el = e.composedPath()[0];
      setTimeout(() => { if (target === el && deepActive() !== el) close(); }, 80);
    }, true);
  };
  if (document.readyState === 'loading' && !document.documentElement) document.addEventListener('DOMContentLoaded', mount, { once: true });
  else if (document.documentElement) mount();
  else document.addEventListener('DOMContentLoaded', mount, { once: true });
}

let ttPolicy: { createHTML(s: string): unknown } | null | undefined;
function setHTML(el: Element | ShadowRoot, html: string): void {
  if (ttPolicy === undefined) {
    try { ttPolicy = (window as any).trustedTypes?.createPolicy?.('kitchen-overlay', { createHTML: (s: string) => s }) ?? null; }
    catch { ttPolicy = null; }                       // the site restricts policy names: plain strings, best effort
  }
  (el as any).innerHTML = ttPolicy ? ttPolicy.createHTML(html) : html;
}

function deepActive(): Element | null {
  let a: Element | null = document.activeElement;
  while (a?.shadowRoot?.activeElement) a = a.shadowRoot.activeElement;
  return a;
}

function svg(id: keyof typeof icons): string {
  const i = icons[id];
  return `<svg viewBox="${i.viewBox}" aria-hidden="true">${i.body}</svg>`;
}

function css(origin: string): string {
  const latin = 'U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD';
  const ext = 'U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+1E00-1E9F, U+20A0-20AB, U+20AD-20C4, U+2C60-2C7F, U+A720-A7FF';
  return `
  @font-face { font-family: 'KArchivo'; font-weight: 100 900; src: url('${origin}/fonts/archivo-latin.woff2') format('woff2'); unicode-range: ${latin}; }
  @font-face { font-family: 'KArchivo'; font-weight: 100 900; src: url('${origin}/fonts/archivo-latin-ext.woff2') format('woff2'); unicode-range: ${ext}; }
  * { box-sizing: border-box; font-family: 'KArchivo', 'Segoe UI', system-ui, sans-serif; }
  button { font: inherit; color: inherit; cursor: pointer; -webkit-tap-highlight-color: transparent; }
  svg { width: 40px; height: 40px; flex: none; }
  .bar { position: fixed; left: 14px; bottom: 14px; display: flex; gap: 10px; padding: 8px; background: #1F1A17; border-radius: 999px;
         box-shadow: 0 6px 0 rgba(0,0,0,.25); transition: transform 180ms ease-out; }
  .bar.up { transform: translateY(-302px); }
  .b { height: 64px; min-width: 64px; border-radius: 999px; border: 3px solid #1F1A17; background: #FFF4DF; display: flex;
       align-items: center; justify-content: center; gap: 8px; padding: 0 12px; font-weight: 900; font-size: 18px; color: #1F1A17; }
  .b:active { transform: scale(.94); }
  .save { background: ${P.herb}; color: #1F1A17; padding: 0 20px 0 12px; }
  .toast { position: fixed; left: 50%; top: 16px; transform: translateX(-50%); max-width: calc(100vw - 32px); display: flex;
           align-items: center; gap: 12px; padding: 8px 8px 8px 22px; background: #1F1A17; color: #fff; border-radius: 999px;
           font-weight: 800; font-size: 17px; box-shadow: 0 6px 0 rgba(0,0,0,.25); }
  .toast[hidden], .act[hidden], .kb[hidden] { display: none; }
  .act { min-height: 64px; min-width: 64px; padding: 0 20px; border-radius: 999px; border: 0; background: ${P.teal}; color: #1F1A17; font-weight: 900; font-size: 16px; }
  .kb { position: fixed; left: 0; right: 0; bottom: 0; height: 302px; padding: 10px 10px 12px; background: #1F1A17; display: flex;
        flex-direction: column; gap: 8px; }
  .row { display: flex; gap: 7px; }
  .key { flex: 1 1 0; min-width: 0; height: 64px; border-radius: 10px; border: 0; background: #FFF4DF; color: #1F1A17; font-weight: 800;
         font-size: 24px; display: flex; align-items: center; justify-content: center; gap: 6px; box-shadow: 0 4px 0 #000; }
  .key svg { width: 26px; height: 26px; }
  .key:active { transform: translateY(3px); box-shadow: 0 1px 0 #000; }
  .special { background: #FFD23F; font-size: 17px; }
  .on { background: #F28C28; }`;
}
