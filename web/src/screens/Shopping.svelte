<script lang="ts">
  import { failKey } from '../lib/api';
  import MascotNote from '../components/MascotNote.svelte';
  import PageHeader from '../components/PageHeader.svelte';
  import Icon from '../components/Icon.svelte';
  import { shopping, type ShopItem } from '../lib/shopping';
  import { catalogue, pantry } from '../lib/pantry';
  import { search, nameOf } from '../lib/search';
  import { P } from '../lib/palette';
  import { lang, t } from '../lib/i18n';
  import { go } from '../lib/router';
  import { osk, activeInput } from '../lib/osk';
  import { showToast } from '../lib/toast';
  import { sound } from '../lib/sound';

  const { open, done } = shopping;
  let text = $state('');
  let hits = $derived($catalogue && text.trim() ? search($catalogue, text, 8).filter((h) => h.kind === 'item') : []);

  async function addText() {
    const v = text; text = '';
    try { await shopping.add(v); sound.on(); } catch (e) { showToast({ text: $t(failKey(e)), tone: 'warn' }); }
  }
  async function addHit(itemId: string) {
    text = '';
    try { await shopping.addItem(itemId); sound.on(); } catch (e) { showToast({ text: $t(failKey(e)), tone: 'warn' }); }
  }
  async function tick(it: ShopItem) {
    try {
      await shopping.tick(it.id, !it.done);
      sound.on();
      if (!it.done && it.item_id) {
        const id = it.item_id;
        showToast({ text: $t('toast.got', { name: it.text }), action: { label: $t('toast.got.yes'), run: () => pantry.toggle(id, true).catch(() => {}) } });
      }
    } catch (e) { showToast({ text: $t(failKey(e)), tone: 'warn' }); }
  }
  async function remove(it: ShopItem) {
    try {
      await shopping.remove(it.id);
      sound.off();
      // ✕ sits next to the tick: a slip must be one tap to undo
      showToast({ text: $t('toast.removed', { name: it.text }), undo: () => { shopping.restore(it).catch(() => {}); } });
    } catch (e) { showToast({ text: $t(failKey(e)), tone: 'warn' }); }
  }
</script>

<div class="screen">
  <PageHeader title={$t('shopping.title')} sub={$t('shopping.sub')} icon="shopping" color={P.teal} back={() => go('/')}>
    {#if $done.length}<button class="clear pressable" onclick={() => shopping.clearDone()}>{$t('shopping.clear')} ({$done.length})</button>{/if}
  </PageHeader>
  <div class="body" class:kb={!!$activeInput}>
    <form class="add" onsubmit={(e) => { e.preventDefault(); addText(); }}>
      <input bind:value={text} placeholder={$t('shopping.add')} use:osk autocomplete="off" />
      <button class="pressable" type="submit" disabled={!text.trim()}><Icon name="plus" size={26} />{$t('shopping.add.btn')}</button>
    </form>
    {#if hits.length}
      <div class="sugg">
        {#each hits as h (h.id)}
          <button class="chip pressable" type="button" onclick={() => addHit(h.id)}><Icon name={h.item?.icon ?? h.group.icon} size={30} />{nameOf(h.item!, $lang)}</button>
        {/each}
      </div>
    {/if}
    <ul class="list">
      {#each $open as it (it.id)}
        <li>
          <button class="tick pressable" aria-label={$t('shopping.done')} onclick={() => tick(it)}></button>
          <span class="txt">{it.text}</span>
          <button class="del pressable" aria-label={$t('a11y.remove')} onclick={() => remove(it)}>✕</button>
        </li>
      {:else}
        <li class="empty"><MascotNote act="hop" expr="happy" text={$t('shopping.empty')} /></li>
      {/each}
      {#each $done as it (it.id)}
        <li class="done">
          <button class="tick on pressable" aria-label={$t('a11y.untick')} onclick={() => tick(it)}>✓</button>
          <span class="txt">{it.text}</span>
          <button class="del pressable" aria-label={$t('a11y.remove')} onclick={() => remove(it)}>✕</button>
        </li>
      {/each}
    </ul>
  </div>
</div>

<style>
  .screen { height: 100%; display: flex; flex-direction: column; }
  .body { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 12px; padding: 16px 20px 20px; }
  .body.kb { padding-bottom: calc(var(--kb-h) + 8px); }
  .clear { min-height: var(--touch); padding: 0 16px; border-radius: 999px; border: var(--outline) solid var(--ink); background: var(--paper);
           font-weight: 800; font-size: 15px; }
  .add { display: flex; gap: 10px; }
  .add input { flex: 1; min-width: 0; height: var(--touch); border: var(--outline) solid var(--ink); border-radius: var(--r); padding: 0 18px;
               font: inherit; font-weight: 700; font-size: 20px; background: var(--paper); outline: none; }
  .add button { min-width: 140px; height: var(--touch); border-radius: var(--r); border: var(--outline) solid var(--ink); background: var(--herb);
                color: var(--ink); font-weight: 900; font-size: 18px; display: flex; align-items: center; justify-content: center; gap: 8px;
                box-shadow: var(--shadow-sm); }
  .add button:disabled { opacity: .45; box-shadow: none; }
  .sugg { display: flex; gap: 8px; flex-wrap: wrap; }
  .chip { min-height: 56px; display: flex; align-items: center; gap: 8px; padding: 0 14px 0 8px; border-radius: 999px;
          border: var(--outline) dashed var(--ink); background: var(--paper); font-weight: 800; font-size: 15px; }
  .list { list-style: none; margin: 0; padding: 0 4px 80px 0; flex: 1; min-height: 0; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; }
  li { display: flex; align-items: center; gap: 12px; min-height: 76px; padding: 0 8px 0 10px; background: var(--paper);
       border: var(--outline) solid var(--ink); border-radius: var(--r); }
  .txt { flex: 1; min-width: 0; font-weight: 800; font-size: 20px; }
  .tick { width: var(--touch); height: var(--touch); border-radius: 14px; border: var(--outline) solid var(--ink); background: var(--cream);
          font-weight: 900; font-size: 26px; color: var(--ink); flex: none; }
  .tick.on { background: var(--herb); }
  .del { width: var(--touch); height: var(--touch); border-radius: 50%; border: 0; background: transparent; font-size: 22px; font-weight: 900; opacity: .5; flex: none; }
  .done { opacity: .6; } .done .txt { text-decoration: line-through; }
  .empty { justify-content: center; font-weight: 800; border-style: dashed; }
</style>
