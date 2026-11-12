<script lang="ts">
  import { now } from '../lib/clock';
  import { fmtDate, fmtTime, lang } from '../lib/i18n';
  let { size = 112 }: { size?: number } = $props();
</script>

<div class="clock" style:font-size="{size}px">{fmtTime($now)}</div>
<div class="date">{fmtDate($now, $lang)}</div>

<style>
  .clock { font-family: var(--font-display); line-height: .95; letter-spacing: -.01em; }
  .date { font-weight: 900; font-size: 19px; margin-top: 8px; text-transform: uppercase; letter-spacing: .04em; }
</style>
