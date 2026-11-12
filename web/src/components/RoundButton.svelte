<script lang="ts">
  import Icon from './Icon.svelte';
  let { icon, label, onclick, color = 'var(--paper)', badge = 0 }:
    { icon: string; label: string; onclick?: () => void; color?: string; badge?: number } = $props();
</script>

<button class="rb pressable" aria-label={label} title={label} {onclick} style:background={color}><Icon name={icon} size={34} />
  {#if badge > 0}<span class="badge">{badge > 99 ? '99+' : badge}</span>{/if}</button>

<style>
  .rb {
    width: var(--touch); height: var(--touch); border-radius: 50%; border: var(--outline) solid var(--ink); box-shadow: var(--shadow-sm);
    display: grid; place-items: center; padding: 0; flex: none; position: relative;
  }
  /* a count (open shopping items, running timers): white on ink, the one place white text is allowed */
  .badge { position: absolute; top: -6px; right: -6px; min-width: 26px; height: 26px; padding: 0 6px; border-radius: 13px;
           background: var(--ink); color: #fff; font-weight: 900; font-size: 13px; display: grid; place-items: center;
           border: 2px solid var(--paper); }
  @media (max-aspect-ratio: 1/1) { .rb :global(svg) { width: 26px; height: 26px; } }   /* phones: --touch is 48 px */
</style>
