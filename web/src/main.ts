import './lib/base.css';
import { mount } from 'svelte';
import App from './App.svelte';
import { registerWorker } from './lib/swregister';

// The service worker keeps the kiosk showing the app (cached shell + last data) while the server is down.
registerWorker(__BUILD__);

const app = mount(App, { target: document.getElementById('app')! });
// tells index.html's boot guard the app is up (it reloads a page whose bundle never arrived)
(window as unknown as { __kitchenUp?: boolean }).__kitchenUp = true;
// …and which build it is (scripts/kiosk-measure.py refuses to measure a page that is not the server's build)
(window as unknown as { __kitchenBuild?: string }).__kitchenBuild = __BUILD__;
try { sessionStorage.removeItem('kitchen.boot'); } catch { /* storage may be off */ }
export default app;
