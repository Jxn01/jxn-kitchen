// JXN Kitchen service worker (module). Registered as /sw.js?v=<build>.
// Two caches: the build's own (`kitchen-<build>`: the app page, hashed assets, fonts, sprite), replaced by every new
// build, and DATA_CACHE (`kitchen-data`: every GET /api answer and every recipe photo), which outlives deploys and is
// kept full by the kiosk's warm-up (the 'warm' message, sent by lib/offlinewarm.ts).
import { cacheFor, DATA_CACHE, fallbackKeys, fontUrls, shellAssets, staleImageKeys, strategyFor, usable } from './sw-strategy.js';

const VERSION = new URL(self.location.href).searchParams.get('v') || 'dev';
const SHELL_CACHE = `kitchen-${VERSION}`;
const NETWORK_TIMEOUT_MS = 4000;   // a dead server must not leave the kiosk spinning

const cacheName = (url) => (cacheFor(url) === 'data' ? DATA_CACHE : SHELL_CACHE);

// The build's whole shell, before this worker takes over: the page, the assets and fonts it names, the fonts its
// stylesheet loads, the sprite. Any failure fails the install, so the previous worker (whose cache still holds a
// complete shell) stays in charge and registerWorker tries again at the next reconnect. The page goes in last: a
// shell is stored only together with everything it needs.
async function precacheShell() {
  const cache = await caches.open(SHELL_CACHE);
  const page = await fetch('/', { cache: 'no-cache' });
  if (!page.ok) throw new Error(`the app page answered ${page.status}`);
  const files = new Set(['/sprite.svg', ...shellAssets(await page.clone().text())]);
  for (const css of [...files].filter((u) => u.endsWith('.css'))) {
    const res = await fetch(css);
    if (!res.ok) throw new Error(`${css} answered ${res.status}`);
    for (const font of fontUrls(await res.clone().text())) files.add(font);
    await cache.put(css, res);
  }
  await cache.addAll([...files].filter((u) => !u.endsWith('.css')));
  await cache.put('/', page);
}

self.addEventListener('install', (event) => {
  event.waitUntil(precacheShell().then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    for (const key of await caches.keys()) {
      if (key.startsWith('kitchen-') && key !== SHELL_CACHE && key !== DATA_CACHE) await caches.delete(key);
    }
    await self.clients.claim();
  })());
});

function fetchWithTimeout(req) {
  return Promise.race([
    fetch(req),
    new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), NETWORK_TIMEOUT_MS)),
  ]);
}

async function cacheFirst(req) {
  const hit = await caches.match(req);
  if (hit) return hit;
  const res = await fetch(req);
  if (res.ok) (await caches.open(cacheName(new URL(req.url)))).put(req, res.clone());
  return res;
}

// The page's offline badge must still know the server is away, so cached stand-ins carry a header.
function markStale(res) {
  const headers = new Headers(res.headers);
  headers.set('x-kitchen-stale', '1');
  return new Response(res.body, { status: res.status, statusText: res.statusText, headers });
}

async function networkFirst(req, cacheKey) {
  let res = null, err = null;
  try { res = await fetchWithTimeout(req); } catch (e) { err = e; }
  const url = typeof cacheKey === 'string' ? new URL(cacheKey, self.location.origin) : new URL(cacheKey.url);
  if (usable(res)) {
    if (res.ok) (await caches.open(cacheName(url))).put(cacheKey, res.clone());
    return res;
  }
  // down, too slow, or a 5xx: the last good copy beats an error page
  for (const key of typeof cacheKey === 'string' ? [cacheKey] : fallbackKeys(url)) {
    const hit = await caches.match(key);
    if (hit) return markStale(hit);
  }
  if (res) return res;
  throw err;
}

// The warm-up: fetch every listed URL into DATA_CACHE, one at a time (the kiosk is a small PC and the server
// serves everyone else too). Stops at the first failure: offline, too slow or a 5xx means "try again next time",
// and an incomplete run never prunes. A 404 is a real answer (the thing was deleted) and drops the cached copy.
// Photos are immutable (their names change when they do), so one already held is not fetched again.
let warming = null;
async function warm(urls) {
  const cache = await caches.open(DATA_CACHE);
  const wanted = [];
  let complete = true;
  for (const u of urls) {
    const url = new URL(u, self.location.origin);
    if (url.origin !== self.location.origin || cacheFor(url) !== 'data') continue;
    wanted.push(url.href);
    try {
      if (url.pathname.startsWith('/api/images/') && (await cache.match(url.href))) continue;
      const res = await fetchWithTimeout(url.href);
      if (res.ok) await cache.put(url.href, res);
      else if (res.status === 404) await cache.delete(url.href);
      else if (!usable(res)) { complete = false; break; }
    } catch { complete = false; break; }
  }
  if (complete) {
    const keys = (await cache.keys()).map((r) => r.url);
    for (const key of staleImageKeys(keys, wanted)) await cache.delete(key);
  }
  return { complete, listed: wanted.length };
}

self.addEventListener('message', (event) => {
  if (event.data?.type !== 'warm' || !Array.isArray(event.data.urls)) return;
  if (!warming) warming = warm(event.data.urls).finally(() => { warming = null; });   // one run at a time
  event.waitUntil(warming);
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  const strategy = strategyFor(url, event.request.method, event.request.mode, self.location.origin);
  if (strategy === 'bypass') return;
  if (strategy === 'cache-first') { event.respondWith(cacheFirst(event.request)); return; }
  // navigations all share the cached shell ('/'): the router is client-side
  const key = event.request.mode === 'navigate' ? '/' : event.request;
  event.respondWith(networkFirst(event.request, key));
});
