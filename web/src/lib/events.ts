// The live channel: /api/events (SSE). We own reconnection (a native EventSource gives up for good on an HTTP
// error such as Caddy's 502 while the container restarts): close, wait 1,2,4,8… s (max 30), reconnect.
type Handler = (data: any) => void;
interface ESLike {
  addEventListener(type: string, fn: (e: any) => void): void;
  close(): void;
}
type ESCtor = new (url: string) => ESLike;

export interface EventsOptions {
  url?: string;
  ES?: ESCtor;
  onStatus?: (ok: boolean) => void;
}

export const MAX_BACKOFF_MS = 30000;
/** The server sends an `event: ping` every 20 s; this long without ANY message means the stream died silently
 *  (a half-open TCP connection after Wi-Fi trouble), so we reconnect. */
export const STALE_MS = 50000;

export function connectEvents(opts: EventsOptions = {}) {
  const url = opts.url ?? '/api/events';
  const ES = opts.ES ?? (globalThis as any).EventSource;
  const handlers = new Map<string, Set<Handler>>();
  let backoff = 1000;
  let closed = false;
  let current: ESLike | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let stale: ReturnType<typeof setTimeout> | null = null;

  function fail(es: ESLike) {
    es.close();
    if (current !== es || closed) return;
    current = null;
    if (stale) clearTimeout(stale);
    opts.onStatus?.(false);
    timer = setTimeout(open, backoff);
    backoff = Math.min(backoff * 2, MAX_BACKOFF_MS);
  }
  function alive(es: ESLike) {
    if (stale) clearTimeout(stale);
    stale = setTimeout(() => fail(es), STALE_MS);
  }

  function attach(es: ESLike, type: string) {
    es.addEventListener(type, (e: any) => {
      alive(es);
      let data: any = null;
      try { data = JSON.parse(e.data); } catch { return; }
      for (const fn of handlers.get(type) ?? []) fn(data);
    });
  }

  function open() {
    if (closed) return;
    const es = new ES(url);
    current = es;
    es.addEventListener('open', () => { backoff = 1000; alive(es); opts.onStatus?.(true); });
    es.addEventListener('ping', () => alive(es));
    es.addEventListener('error', () => fail(es));
    alive(es);
    for (const type of handlers.keys()) attach(es, type);
  }
  open();

  return {
    on(type: string, fn: Handler): () => void {
      if (!handlers.has(type)) {
        handlers.set(type, new Set());
        if (current) attach(current, type);
      }
      handlers.get(type)!.add(fn);
      return () => handlers.get(type)!.delete(fn);
    },
    close() {
      closed = true;
      if (timer) clearTimeout(timer);
      if (stale) clearTimeout(stale);
      current?.close();
    },
  };
}
