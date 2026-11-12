// JSON helpers for /api — every app write goes through these. A network failure OR a 5xx answer (Caddy's 502 while
// the container restarts) throws OfflineError: the server is away, the write is worth queueing (lib/outbox.ts). Any
// other non-2xx throws an ApiError (status + the body's detail): the server refused it, queueing would not help.
export class OfflineError extends Error {}
/** The server refused a write (a non-2xx below 500): `status` and the body's `detail` (a string, or `{code, message}`). */
export class ApiError extends Error {
  constructor(message: string, public status: number, public detail: unknown) { super(message); }
  /** `detail.code` when the server sent one (e.g. folders: 'taken' | 'cycle' | 'depth'). */
  get code(): string | null {
    const d = this.detail as { code?: unknown } | null;
    return d && typeof d === 'object' && typeof d.code === 'string' ? d.code : null;
  }
}

type Listener = (ok: boolean) => void;
const listeners = new Set<Listener>();
export function onApiStatus(fn: Listener): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}
function report(ok: boolean) { for (const fn of listeners) fn(ok); }

async function send(method: string, path: string, body?: unknown): Promise<Response> {
  let r: Response;
  try {
    r = await fetch(path, {
      method,
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (e) {
    report(false);
    throw new OfflineError(String(e));
  }
  // The service worker marks answers it served from its cache (the server was unreachable or answered 5xx).
  report(r.status < 500 && r.headers.get('x-kitchen-stale') !== '1');
  if (r.status >= 500) throw new OfflineError(`${method} ${path} -> ${r.status}`);
  if (!r.ok) {
    const body = await r.json().catch(() => null) as { detail?: unknown } | null;
    throw new ApiError(`${method} ${path} -> ${r.status}`, r.status, body?.detail ?? null);
  }
  return r;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const r = await send(method, path, body);
  return (r.status === 204 ? undefined : await r.json()) as T;
}

/** A GET that also says whether the answer is the service worker's cached stand-in (`x-kitchen-stale`): data that
 *  was true when cached, not now (cooktimers.ts then counts down from `ends_at` instead of `remaining`). */
export async function getJSONWithAge<T>(path: string): Promise<{ data: T; stale: boolean }> {
  const r = await send('GET', path);
  return { data: (await r.json()) as T, stale: r.headers.get('x-kitchen-stale') === '1' };
}

/** The message key for a write that failed: "needs a connection" when the server is away (OfflineError), else the
 *  generic error. Every failing action's toast goes through this (tests/offline-edits.test.ts keeps it so), so an
 *  online-only action (import, scan, photo, a new recipe, the sauce and blend editors) says why it cannot work offline. */
export function failKey(e: unknown): 'toast.needs' | 'toast.error' {
  return e instanceof OfflineError ? 'toast.needs' : 'toast.error';
}

export const getJSON = <T>(path: string) => request<T>('GET', path);
export const putJSON = <T>(path: string, body: unknown) => request<T>('PUT', path, body);
export const postJSON = <T>(path: string, body: unknown) => request<T>('POST', path, body);
export const patchJSON = <T>(path: string, body: unknown) => request<T>('PATCH', path, body);
export const del = (path: string) => request<void>('DELETE', path);
