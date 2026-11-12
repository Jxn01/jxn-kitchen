// The one-tap flows shared by every pantry screen: toggle with sound + toast (Undo, and "+ shopping list" when
// something runs out).
import { get } from 'svelte/store';
import { pantry } from './pantry';
import { sound } from './sound';
import { showToast } from './toast';
import { t } from './i18n';
import { shopping } from './shopping';
import { failKey } from './api';

export async function toggleWithToast(node: string, name: string): Promise<void> {
  const tr = get(t);
  let have: boolean;
  try {
    have = await pantry.toggle(node);
  } catch (e) {
    showToast({ text: tr(failKey(e)), tone: 'warn' });
    return;
  }
  (have ? sound.on : sound.off)();
  const undo = () => { pantry.toggle(node, !have).catch(() => {}); };
  if (have) {
    showToast({ text: tr('toast.in', { name }), undo });
  } else {
    const itemId = node.startsWith('group:') ? undefined : node;
    showToast({
      text: tr('toast.out', { name }), undo,
      action: { label: tr('toast.shop'), run: () => addToShopping(itemId, name) },
    });
  }
}

export async function addToShopping(itemId: string | undefined, name: string): Promise<void> {
  const tr = get(t);
  try {
    await (itemId ? shopping.addItem(itemId, name) : shopping.add(name));     // one write path (queued offline)
    showToast({ text: tr('toast.shopped', { name }) });
  } catch (e) {
    showToast({ text: tr(failKey(e)), tone: 'warn' });
  }
}
