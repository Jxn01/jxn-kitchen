<script lang="ts">
  // One pantry tile: one tap flips it. On = the category's colour + a stamp; off = paper white.
  import Icon from './Icon.svelte';
  import { textOn } from '../lib/color';
  import { fit } from '../lib/fit';
  let { name, icon, on, color, note = '', ontoggle }:
    { name: string; icon: string; on: boolean; color: string; note?: string; ontoggle: () => void } = $props();
</script>

<button class="item pressable" class:on style:--c={color} style:color={on ? textOn(color) : 'var(--ink)'}
        onclick={ontoggle} aria-pressed={on}>
  <span class="plate"><Icon name={icon} size={56} /></span>
  <span class="name" use:fit={name}>{name}</span>
  {#if note}<span class="note">{note}</span>{/if}
  {#if on}<span class="stamp" aria-hidden="true">✓</span>{/if}
</button>

<style>
  .item {
    position: relative; min-height: 118px; padding: 10px 8px 8px; border-radius: var(--r);
    border: var(--outline) solid var(--ink); background: var(--paper);
    display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; min-width: 0;
  }
  .item.on { background: var(--c); box-shadow: var(--shadow-sm); }
  .plate {
    width: 70px; height: 70px; border-radius: 50%; display: grid; place-items: center;
    opacity: .5;
  }
  .on .plate { opacity: 1; background: var(--cream); border: var(--outline) solid var(--ink); }
  .name { font-weight: 800; font-size: 16px; line-height: 1.1; white-space: nowrap; overflow: hidden; display: block;
          max-width: 100%; text-align: center; }
  .note { font-size: 11px; font-weight: 800; opacity: .7; text-transform: uppercase; letter-spacing: .05em; }
  .stamp {
    position: absolute; top: 6px; right: 6px; width: 34px; height: 34px; border-radius: 50%;
    background: var(--herb); color: var(--ink); border: var(--outline) solid var(--ink);
    display: grid; place-items: center; font-weight: 900; font-size: 19px;
    animation: pop 420ms var(--ease-pop) both;
  }
  @keyframes pop { 0% { transform: scale(.3) rotate(-35deg); opacity: 0; } 100% { transform: scale(1) rotate(-12deg); opacity: 1; } }
</style>
