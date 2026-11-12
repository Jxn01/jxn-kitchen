// A press-and-hold on a touch screen: `onlong` after `ms` without lifting or sliding away (10 px). While held the
// node carries the class `holding` (a ring fills — a CSS animation the component draws, once), and the click that
// follows a completed hold is swallowed, so a hold never also counts as a tap.
export function longpress(node: HTMLElement, opts: { onlong: () => void; ms?: number }) {
  let o = opts, timer: ReturnType<typeof setTimeout> | null = null, x = 0, y = 0, fired = false;
  const clear = () => { if (timer) clearTimeout(timer); timer = null; node.classList.remove('holding'); };
  const down = (e: PointerEvent) => {
    fired = false; x = e.clientX; y = e.clientY;
    clear();
    node.classList.add('holding');
    timer = setTimeout(() => { timer = null; node.classList.remove('holding'); fired = true; o.onlong(); }, o.ms ?? 600);
  };
  const move = (e: PointerEvent) => { if (timer && Math.hypot(e.clientX - x, e.clientY - y) > 10) clear(); };
  const click = (e: MouseEvent) => { if (fired) { fired = false; e.preventDefault(); e.stopImmediatePropagation(); } };
  node.addEventListener('pointerdown', down);
  node.addEventListener('pointermove', move);
  for (const ev of ['pointerup', 'pointerleave', 'pointercancel']) node.addEventListener(ev, clear);
  node.addEventListener('click', click, true);
  node.addEventListener('contextmenu', (e) => e.preventDefault());
  return {
    update(next: typeof opts) { o = next; },
    destroy() {
      clear();
      node.removeEventListener('pointerdown', down);
      node.removeEventListener('pointermove', move);
      for (const ev of ['pointerup', 'pointerleave', 'pointercancel']) node.removeEventListener(ev, clear);
      node.removeEventListener('click', click, true);
    },
  };
}
