<script lang="ts">
  let { on }: { on: boolean } = $props();
</script>
<span class="sw" class:on aria-hidden="true"><i></i></span>
<style>
  .sw { position: relative; flex: none; width: 76px; height: 42px; border-radius: 999px; border: var(--outline) solid var(--ink); background: #CFC6BA; }
  .sw.on { background: var(--herb); }
  i { position: absolute; top: 3px; left: 4px; width: 30px; height: 30px; border-radius: 50%; background: #fff;
      border: var(--outline) solid var(--ink); transition: transform 160ms var(--ease-pop); }
  .on i { transform: translateX(34px); }
</style>
