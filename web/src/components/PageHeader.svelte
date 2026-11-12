<script lang="ts">
  import type { Snippet } from 'svelte';
  import Icon from './Icon.svelte';
  import RoundButton from './RoundButton.svelte';
  import { textOn } from '../lib/color';
  import { t } from '../lib/i18n';
  import { fit } from '../lib/fit';
  let { title, sub = '', icon, color, back, children }:
    { title: string; sub?: string; icon: string; color: string; back: () => void; children?: Snippet } = $props();
</script>

<header style:--c={color} style:color={textOn(color)}>
  <RoundButton icon="back" label={$t('common.back')} onclick={back} />
  <span class="plate"><Icon name={icon} size={44} /></span>
  <div class="t"><h1 use:fit={title}>{title}</h1>{#if sub}<small>{sub}</small>{/if}</div>
  <div class="extra">{@render children?.()}</div>
</header>

<style>
  header {
    flex: none; height: 84px; display: flex; align-items: center; gap: 14px; padding: 0 20px;
    background: var(--c); border-bottom: var(--outline-thick) solid var(--ink);
  }
  .plate { width: 58px; height: 58px; border-radius: 50%; background: var(--cream); border: var(--outline) solid var(--ink);
           display: grid; place-items: center; flex: none; }
  .t { min-width: 0; flex: 1 1 auto; }
  /* long recipe titles: fit() shrinks the font to fit the space the buttons leave; past its minimum, an ellipsis */
  h1 { font-size: 30px; line-height: 1.1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  small { display: block; font-weight: 700; font-size: 13.5px; margin-top: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .extra { margin-left: auto; flex: none; display: flex; gap: 10px; align-items: center; color: var(--ink); }
  @media (max-aspect-ratio: 1/1) {
    small { display: none; } h1 { font-size: 22px; } header { height: calc(var(--touch) + 16px); padding: 0 10px; gap: 8px; }
    .plate { display: none; }            /* phones: the room goes to the title */
    .extra { gap: 6px; }
    .extra > :global(button) { white-space: nowrap; }   /* "✓ Save" must not break into two lines and spill */
  }
</style>
