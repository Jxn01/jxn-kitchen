// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createIdle } from '../src/lib/idle';

describe('idle controller', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('goes idle after the timeout, and any touch resets it', () => {
    const onIdle = vi.fn();
    const idle = createIdle({ timeoutMs: 1000, onIdle, onWake: () => {}, target: document });
    vi.advanceTimersByTime(900);
    document.dispatchEvent(new Event('pointerdown', { bubbles: true, cancelable: true }));
    vi.advanceTimersByTime(900);
    expect(onIdle).not.toHaveBeenCalled();
    vi.advanceTimersByTime(100);
    expect(onIdle).toHaveBeenCalledOnce();
    idle.destroy();
  });

  it('the waking touch is consumed and its click is swallowed; a later click passes', () => {
    const onWake = vi.fn();
    const idle = createIdle({ timeoutMs: 1000, onIdle: () => {}, onWake, target: document });
    vi.advanceTimersByTime(1000);
    expect(idle.isIdle()).toBe(true);
    const btn = document.createElement('button');
    document.body.appendChild(btn);
    const clicked = vi.fn();
    btn.addEventListener('click', clicked);
    const down = new Event('pointerdown', { bubbles: true, cancelable: true });
    btn.dispatchEvent(down);
    expect(down.defaultPrevented).toBe(true);
    expect(onWake).toHaveBeenCalledOnce();
    vi.advanceTimersByTime(300);
    btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
    expect(clicked).not.toHaveBeenCalled();
    vi.advanceTimersByTime(600);
    btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
    expect(clicked).toHaveBeenCalledOnce();
    idle.destroy();
  });

  it('a touch while awake is never swallowed', () => {
    const idle = createIdle({ timeoutMs: 1000, onIdle: () => {}, onWake: () => {}, target: document });
    const down = new Event('pointerdown', { bubbles: true, cancelable: true });
    document.dispatchEvent(down);
    expect(down.defaultPrevented).toBe(false);
    idle.destroy();
  });
});

describe('idle screen without the idle flag (review I2: reload on #/idle, or Back into it, froze the kiosk)', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());
  it('a touch while the idle screen shows always wakes, even if the controller never went idle', () => {
    const onWake = vi.fn();
    const idle = createIdle({ timeoutMs: 60000, onIdle: () => {}, onWake, target: document, onIdleScreen: () => true });
    const down = new Event('pointerdown', { bubbles: true, cancelable: true });
    document.dispatchEvent(down);
    expect(onWake).toHaveBeenCalledOnce();
    expect(down.defaultPrevented).toBe(true);
    idle.destroy();
  });
});

describe('idle hold (cook mode keeps the screen)', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());
  it('does not go idle while held, and a touch then is a normal touch', () => {
    const onIdle = vi.fn(), onWake = vi.fn();
    let hold = true;
    const idle = createIdle({ timeoutMs: 1000, onIdle, onWake, target: document, holdIf: () => hold });
    vi.advanceTimersByTime(5000);
    expect(onIdle).not.toHaveBeenCalled();
    const down = new Event('pointerdown', { bubbles: true, cancelable: true });
    document.dispatchEvent(down);
    expect(down.defaultPrevented).toBe(false);            // not consumed: we were never idle
    expect(onWake).not.toHaveBeenCalled();
    hold = false;
    vi.advanceTimersByTime(1000);
    expect(onIdle).toHaveBeenCalledOnce();
    idle.destroy();
  });
});
