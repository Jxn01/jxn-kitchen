/// <reference types="node" />
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

// A kiosk that boots before its Wi-Fi gets a page whose bundle never loads: blank, and the agent's probe still sees a
// live page. index.html carries a guard that reloads unless main.ts says the app mounted.
describe('the boot guard', () => {
  const html = readFileSync(join(__dirname, '../index.html'), 'utf8');
  const main = readFileSync(join(__dirname, '../src/main.ts'), 'utf8');
  it('index.html reloads a page whose app never mounted, before the bundle is even requested', () => {
    expect(html).toMatch(/if \(window\.__kitchenUp\) return;[\s\S]*location\.reload\(\)/);
    expect(html.indexOf('__kitchenUp')).toBeLessThan(html.indexOf('src="/src/main.ts"'));
  });
  it('main.ts sets the flag right after mounting', () => {
    expect(main.indexOf('__kitchenUp = true')).toBeGreaterThan(main.indexOf('mount(App'));
  });
});
