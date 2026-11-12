// One import flow for every place a link comes in (Recipes' "From a link", Browse's import box, the phone's
// #/add share route): import, then the recipe — or, for a draft, the editor with the reason.
import { get } from 'svelte/store';
import { api, importDraft, ImportRefusedError } from './recipes';
import { go } from './router';
import { showToast } from './toast';
import { t } from './i18n';
import { failKey } from './api';

export async function importLink(url: string): Promise<boolean> {
  try {
    const r = await api.importUrl(url.trim());
    if (r.draft) {
      importDraft.set({ id: r.id, code: r.code ?? 'scraper' });
      go(`/recipe/${r.id}/edit`);
    } else go(`/recipe/${r.id}`);
    return true;
  } catch (e) {
    const tr = get(t);
    showToast({ text: e instanceof ImportRefusedError ? tr(`import.reason.${e.code}`) : tr(failKey(e)), tone: 'warn' }, 8000);
    return false;
  }
}
