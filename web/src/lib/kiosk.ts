// Are we the kitchen kiosk? The agent opens the app with ?kiosk=1; remember it so reloads/deep links keep it.
import { readable } from 'svelte/store';

const KEY = 'kitchen.kiosk';
function detect(): boolean {
  if (typeof location === 'undefined') return false;
  try {
    if (new URLSearchParams(location.search).get('kiosk') === '1') localStorage.setItem(KEY, '1');
    return localStorage.getItem(KEY) === '1';
  } catch {
    return new URLSearchParams(location.search).get('kiosk') === '1';
  }
}
export const isKiosk = readable(detect());
