// Routing table and cache rules for the service worker (sw.js) — a plain ES module so vitest can test it directly.
// cache-first: hashed/immutable assets and recipe photos (their names change when they do) · network-first: the app
// shell and GET /api/* (cache fallback when the server is down, so the kiosk keeps showing something) · bypass: SSE,
// writes, other origins (recipe sites), and navigations to anything but the app itself.
export function strategyFor(url, method, mode, origin) {
  if (url.origin !== origin) return 'bypass';
  if (method !== 'GET') return 'bypass';
  if (url.pathname === '/api/events' || url.pathname === '/api/health') return 'bypass';   // live-only answers
  if (mode === 'navigate') return isShell(url) ? 'network-first' : 'bypass';
  if (url.pathname.startsWith('/api/images/')) return 'cache-first';
  if (url.pathname.startsWith('/api/')) return 'network-first';
  if (url.pathname.startsWith('/assets/') || url.pathname.startsWith('/fonts/') || url.pathname === '/sprite.svg')
    return 'cache-first';
  return 'network-first';
}

/** The app's own page (the router is in the hash, so it is always '/'). Only it may be stored as the cached shell —
 *  opening /api/health in a tab must not overwrite the shell with JSON. */
export function isShell(url) {
  return url.pathname === '/' || url.pathname === '/index.html';
}

/** The cache that outlives deploys: every GET /api answer and every recipe photo. The app page and its hashed
 *  assets live in a cache named after the build instead (`kitchen-<build>`), which each new build replaces. Until
 *  2026-11-12 the data lived there too, so every deploy emptied the kiosk's offline copy, and a recipe was there
 *  offline only if it had been opened since. */
export const DATA_CACHE = 'kitchen-data';

/** Which cache a response belongs in: 'data' (DATA_CACHE) for /api/*, 'shell' (the build's) for the rest. */
export function cacheFor(url) {
  return url.pathname.startsWith('/api/') ? 'data' : 'shell';
}

/** The keys to try, in order, for an offline stand-in. A recipe asked for at another serving size
 *  (`?servings=6`) — or a blend at another batch (`?batch_tbsp=`) — falls back to its default copy, which the
 *  warm-up always holds; that answer carries its own size, so the screen shows that size, consistently. */
export function fallbackKeys(url) {
  const keys = [url.href];
  if (url.search && /^\/api\/(recipes|blends)\/\d+$/.test(url.pathname)) keys.push(url.origin + url.pathname);
  return keys;
}

/** Cached photos the latest complete warm-up no longer lists (a photo replaced or a recipe deleted). Photos are the
 *  only part of the data cache that can grow without bound; everything else is a handful of small JSON answers. */
export function staleImageKeys(cachedUrls, wantedUrls) {
  const wanted = new Set(wantedUrls);
  return cachedUrls.filter((u) => new URL(u).pathname.startsWith('/api/images/') && !wanted.has(u));
}

/** What a build's page needs to start with no network, as its HTML names it: the hashed /assets/* (script and
 *  stylesheet) and the preloaded /fonts/*. The worker precaches these at install (2026-11-12: the kiosk's build cache
 *  held only '/' and the sprite — the bundle had been fetched under the previous worker, whose cache `activate` then
 *  deleted — so a cold start with no network had no app code). */
export function shellAssets(html) {
  return [...new Set([...html.matchAll(/(?:src|href)="(\/(?:assets|fonts)\/[^"]+)"/g)].map((m) => m[1]))];
}

/** The fonts a stylesheet loads (`url(/fonts/…)`, quoted or not). */
export function fontUrls(css) {
  return [...new Set([...css.matchAll(/url\(\s*["']?(\/fonts\/[^"')\s]+)["']?\s*\)/g)].map((m) => m[1]))];
}

/** A network answer worth showing instead of the cache. A 5xx (Caddy's 502 while the container restarts) is a
 *  failure: the cached shell/data is better than an error page (spec §9: the kiosk never shows one). A 4xx is a real
 *  answer (a deleted recipe is gone) and passes through. */
export function usable(res) {
  return !!res && res.status < 500;
}
