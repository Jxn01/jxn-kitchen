// Wires <input use:osk> to the app's on-screen keyboard (kiosk only; phones/PCs use their own keyboards).
import { get, writable } from 'svelte/store';
import { isKiosk } from './kiosk';

export const activeInput = writable<HTMLInputElement | HTMLTextAreaElement | null>(null);

export function osk(node: HTMLInputElement | HTMLTextAreaElement) {
  if (!get(isKiosk)) return {};
  node.setAttribute('inputmode', 'none');            // no OS keyboard: ours is the only one
  const focus = () => activeInput.set(node);
  // Our keys cancel their pointerdown, so typing never blurs; a real blur (tapping elsewhere) closes the keyboard.
  const blur = () => setTimeout(() => {
    if (get(activeInput) === node && document.activeElement !== node) activeInput.set(null);
  }, 60);
  node.addEventListener('focus', focus);
  node.addEventListener('blur', blur);
  return {
    destroy() {
      node.removeEventListener('focus', focus);
      node.removeEventListener('blur', blur);
      if (get(activeInput) === node) activeInput.set(null);
    },
  };
}
