<script lang="ts">
  import { activeInput } from '../lib/osk';
  import { applyKey, LAYOUTS, type KeyDef } from '../lib/keyboard-layouts';
  import { lang, t } from '../lib/i18n';
  import Icon from './Icon.svelte';

  let layer = $state<'letters' | 'num'>('letters');
  let kbLang = $state<'en' | 'hu'>($lang);
  let shift = $state(false);
  let rows = $derived(layer === 'num' ? LAYOUTS.num : LAYOUTS[kbLang]);

  function press(e: PointerEvent, key: KeyDef) {
    e.preventDefault();                                  // keep focus (and the caret) in the input
    const input = $activeInput;
    if (!input) return;
    const k = typeof key === 'string' ? key : key.k;
    if (k === 'shift') { shift = !shift; return; }
    if (k === 'mode') { layer = layer === 'num' ? 'letters' : 'num'; return; }
    if (k === 'lang') { kbLang = kbLang === 'en' ? 'hu' : 'en'; return; }
    if (k === 'enter') {
      if (input instanceof HTMLTextAreaElement) {          // multi-line fields: a new line, not "done"
        input.value += '\n';
        input.dispatchEvent(new Event('input', { bubbles: true }));
        return;
      }
      input.form?.requestSubmit?.(); input.blur(); activeInput.set(null); return;
    }
    input.value = applyKey(input.value, k, shift);
    input.dispatchEvent(new Event('input', { bubbles: true }));
    if (typeof key === 'string') shift = false;
  }

  function label(key: KeyDef): string {
    if (typeof key === 'string') return shift ? key.toLocaleUpperCase('hu') : key;
    return { shift: '⇧', back: '⌫', space: $t('kb.space'), enter: $t('kb.done'),
             mode: layer === 'num' ? $t('kb.letters') : $t('kb.numbers'), lang: kbLang.toUpperCase() }[key.k]
      .replace($t('kb.done'), $activeInput instanceof HTMLTextAreaElement ? '↵' : $t('kb.done'));
  }
</script>

{#if $activeInput}
  <div class="kb" role="group" aria-label={$t('a11y.keyboard')}>
    {#if $activeInput instanceof HTMLTextAreaElement}<button class="close" onpointerdown={(e) => { e.preventDefault(); $activeInput?.blur(); activeInput.set(null); }}>{$t('kb.done')} ✓</button>{/if}
    {#each rows as row}
      <div class="row">
        {#each row as key}
          <button class="key" class:special={typeof key !== 'string'} class:on={typeof key !== 'string' && key.k === 'shift' && shift}
                  style:flex-grow={typeof key === 'string' ? 1 : (key.w ?? 1)} onpointerdown={(e) => press(e, key)}>
            {#if typeof key !== 'string' && key.k === 'lang'}<Icon name="language" size={22} />{/if}{label(key)}
          </button>
        {/each}
      </div>
    {/each}
  </div>
{/if}

<style>
  .kb {
    position: fixed; left: 0; right: 0; bottom: 0; z-index: 40; padding: 10px 10px 12px;
    background: var(--ink); display: flex; flex-direction: column; gap: 8px;
    animation: up 180ms ease-out both;
  }
  @keyframes up { from { transform: translateY(100%); } to { transform: none; } }
  .row { display: flex; gap: 7px; }
  .key {
    flex: 1 1 0; min-width: 0; height: var(--kb-key); border-radius: 10px; border: 0; background: var(--cream);
    font-family: var(--font-body); font-weight: 800; font-size: 24px; display: flex; align-items: center; justify-content: center; gap: 6px;
    box-shadow: 0 4px 0 #000; transition: transform 60ms;
  }
  .key:active { transform: translateY(3px); box-shadow: 0 1px 0 #000; }
  .special { background: var(--butter); font-size: 17px; }
  .on { background: var(--tangerine); }
  .close { position: absolute; right: 12px; top: -72px; height: var(--touch); padding: 0 18px; border-radius: 999px; border: 0;
           background: var(--herb); color: var(--ink); font-weight: 900; font-size: 17px; }
</style>
