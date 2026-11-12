import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import { toast, showToast, dismissToast } from '../src/lib/toast';

describe('toast', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => { vi.useRealTimers(); dismissToast(); });
  it('one at a time: a new toast replaces the old one', () => {
    showToast({ text: 'a' });
    showToast({ text: 'b' });
    expect(get(toast)?.text).toBe('b');
  });
  it('undo and action call back and dismiss', () => {
    const undo = vi.fn(), act = vi.fn();
    showToast({ text: 'x', undo, action: { label: '+', run: act } });
    get(toast)!.undo!();
    expect(undo).toHaveBeenCalledOnce();
    expect(get(toast)).toBeNull();
    showToast({ text: 'y', action: { label: '+', run: act } });
    get(toast)!.action!.run();
    expect(act).toHaveBeenCalledOnce();
  });
  it('times out after 5 s, but a replacement restarts the clock', () => {
    showToast({ text: 'a' });
    vi.advanceTimersByTime(4000);
    showToast({ text: 'b' });
    vi.advanceTimersByTime(4000);
    expect(get(toast)?.text).toBe('b');
    vi.advanceTimersByTime(1001);
    expect(get(toast)).toBeNull();
  });
});
