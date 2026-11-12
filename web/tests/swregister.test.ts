// @vitest-environment jsdom
import { describe, expect, it, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

describe('registration (2026-11-12: a stale sw-strategy.js in the HTTP cache killed the new worker\'s install)', () => {
  it('passes updateViaCache none and the build, and a failure is logged rather than thrown', async () => {
    const { registerWorker } = await import('../src/lib/swregister');
    const register = vi.fn(() => Promise.reject(new Error('import failed')));
    Object.defineProperty(navigator, 'serviceWorker', { value: { register }, configurable: true });
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    registerWorker('ad78a12');
    expect(register).toHaveBeenCalledWith('/sw.js?v=ad78a12', { type: 'module', updateViaCache: 'none' });
    await Promise.resolve(); await Promise.resolve();
    expect(warn).toHaveBeenCalled();
    warn.mockRestore();
  });
  it('the app registers through it at start and again at every reconnect, and nowhere else', () => {
    const main = readFileSync(join(__dirname, '../src/main.ts'), 'utf8');
    const app = readFileSync(join(__dirname, '../src/App.svelte'), 'utf8');
    expect(main).toMatch(/registerWorker\(__BUILD__\)/);
    expect(app).toMatch(/if \(ok\) \{[^}]*registerWorker\(__BUILD__\)/);
    expect(main + app).not.toMatch(/serviceWorker\.register\(/);
  });
});
