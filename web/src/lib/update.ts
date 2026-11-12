// A 24/7 kiosk never reloads by itself, so after a deploy it would keep running the old app. On every (re)connect
// we ask the server which build it runs and reload once if it differs. A deploy restarts the container, which drops
// SSE, so the reconnect is exactly when this runs. Remembered per server build, so a stale cache can't loop.

const KEY = 'kitchen.reloadedFor';

export function shouldReload(server: string | undefined, client: string, triedFor: string | null): boolean {
  if (!server || server === 'dev' || server === client) return false;
  return triedFor !== server;
}

export async function checkForUpdate(): Promise<void> {
  try {
    // raw fetch, any status: /api/health answers 503 (with the build) when stored ids dangle — that must
    // neither block updates nor count as "offline"
    const h = (await (await fetch('/api/health', { cache: 'no-store' })).json()) as { build?: string };
    let tried: string | null = null;
    try { tried = sessionStorage.getItem(KEY); } catch { /* ignore */ }
    if (shouldReload(h.build, __BUILD__, tried)) {
      try { sessionStorage.setItem(KEY, h.build!); } catch { /* ignore */ }
      location.reload();
    }
  } catch { /* offline: try at the next reconnect */ }
}
