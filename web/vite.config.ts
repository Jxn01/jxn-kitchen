import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte()],
  define: { __BUILD__: JSON.stringify(process.env.KITCHEN_BUILD ?? new Date().toISOString()) },
  build: { outDir: 'dist', target: 'chrome120', assetsInlineLimit: 0 },
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
  test: { include: ['tests/**/*.test.ts'], environment: 'node' },
});
