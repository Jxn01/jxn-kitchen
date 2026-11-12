// Registers the service worker: at start, and again at every reconnect (App.svelte), so an install that failed heals
// itself without waiting for a page reload. Registering the same URL again is a no-op.
//
// updateViaCache 'none': the worker script AND its imports (sw-strategy.js) are always fetched past the HTTP cache.
// With the default ('imports') Chrome served the kiosk an hours-old sw-strategy.js, the new worker's
// import failed, the install died silently, and the kiosk kept the previous build's worker (server/kitchen/app.py
// WebFiles also sends no-cache for every unhashed file).
export function registerWorker(build: string): void {
  if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) return;
  if (!(location.protocol === 'https:' || location.hostname === 'localhost')) return;
  navigator.serviceWorker
    .register(`/sw.js?v=${encodeURIComponent(build)}`, { type: 'module', updateViaCache: 'none' })
    .catch((e) => console.warn('kitchen: service worker registration failed', e));
}
