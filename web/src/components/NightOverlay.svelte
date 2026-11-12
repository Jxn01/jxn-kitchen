<script lang="ts">
  // A static dimming layer at night, on top of the backlight dimming the agent does. Never animated.
  let { on }: { on: boolean } = $props();
</script>
{#if on}<div class="night" aria-hidden="true"></div>{/if}
<style>
  .night { position: fixed; inset: 0; z-index: 30; background: rgba(0, 0, 0, .32); pointer-events: none; }
</style>
