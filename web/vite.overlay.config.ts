// The Browse overlay (src/overlay/main.ts) as ONE self-contained classic script, dist/overlay.js: the kiosk agent
// fetches it from the server and injects it into third-party pages over CDP. Shares the keyboard layouts
// and i18n with the app. Built after the app (emptyOutDir: false keeps the app's files).
import { defineConfig } from 'vite';

export default defineConfig({
  build: {
    outDir: 'dist',
    emptyOutDir: false,
    copyPublicDir: false,
    lib: { entry: 'src/overlay/main.ts', name: 'kitchenOverlay', formats: ['iife'], fileName: () => 'overlay.js' },
    minify: true,
  },
});
