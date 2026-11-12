// Svelte action: shrink a one-line label's font until it fits its box (long Hungarian words, e.g. "Konyhatudás",
// "Bevásárlólista"). Re-runs when the text changes (pass it as the parameter), on resize and once fonts load.
//
// It must never react to a resize it caused itself. If the observed container is shrink-to-fit, its width follows
// the text's font size: each fit resizes the container, the observer fires, fit runs again — on the real kiosk a
// home tile title re-fitted ~330×/s and kept Chrome 60 % busy. So the observer only re-fits when the
// container's width differs from the width it had right after our own last run.
//
// And it must never leave the text cut off. Below its floor (55 % of the size, at least 11 px) it used to
// stop and let `overflow: hidden` eat the end of the label — "Pasta, rice & gr", "Sauces & condi" on a phone held
// sideways (scripts/clip-audit.py checks this). Now, when the floor is not enough, a label whose element asks for
// `text-overflow: ellipsis` keeps it (a deliberate one-line title: the page header, Cook), and every other label WRAPS:
// the largest size from the top again at which it fits on at most two lines, then smaller still if it must, and a
// word longer than the box is broken as the last resort. The element carries `data-fit-wrapped` while it does.
export function fit(node: HTMLElement, _text?: unknown) {
  const cs = getComputedStyle(node);
  const max = parseFloat(cs.fontSize) || 23;
  const min = Math.max(11, Math.round(max * 0.55));
  const ellipsis = cs.textOverflow === 'ellipsis';
  const box = node.parentElement ?? node;
  let settledWidth = -1;
  const wide = () => node.scrollWidth > node.clientWidth + 0.5;
  const lines = (size: number) => {
    const lh = parseFloat(getComputedStyle(node).lineHeight);
    return node.scrollHeight / (Number.isFinite(lh) && lh > 0 ? lh : size * 1.2);
  };
  const setSize = (size: number) => { node.style.fontSize = `${size}px`; };
  function run() {
    node.style.fontSize = '';
    node.style.whiteSpace = '';
    node.style.overflowWrap = '';
    delete node.dataset.fitWrapped;
    let size = max;
    while (wide() && size > min) {
      size -= 1;
      setSize(size);
    }
    if (wide() && !ellipsis) {
      node.style.whiteSpace = 'normal';
      node.dataset.fitWrapped = '';
      size = max;
      setSize(size);
      while (size > min && (wide() || lines(size) > 2.05)) {
        size -= 1;
        setSize(size);
      }
      if (wide()) node.style.overflowWrap = 'anywhere';   // one word longer than the box, even at the floor
    }
    settledWidth = box.clientWidth;
  }
  run();
  // A web font arriving changes the text's width but not the box's, so the observer can't see it: re-fit when any
  // font finishes loading. (`fonts.ready` alone isn't enough — it can resolve before the display font even starts.)
  document.fonts?.ready.then(run);
  document.fonts?.addEventListener?.('loadingdone', run);
  const ro = typeof ResizeObserver !== 'undefined'
    ? new ResizeObserver(() => { if (box.clientWidth !== settledWidth) run(); })
    : null;
  ro?.observe(box);
  return { update: run, destroy: () => { ro?.disconnect(); document.fonts?.removeEventListener?.('loadingdone', run); } };
}
