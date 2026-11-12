// One toast at a time (spec §6.2): "Wings → in · Undo", with an optional extra action ("+ shopping list"). 5 s.
import { writable } from 'svelte/store';

export interface ToastSpec { text: string; undo?: () => void; action?: { label: string; run: () => void }; tone?: 'ok' | 'warn' }
export interface Toast extends ToastSpec { id: number }

export const toast = writable<Toast | null>(null);
let seq = 0;
let timer: ReturnType<typeof setTimeout> | null = null;

export function dismissToast(): void {
  if (timer) clearTimeout(timer);
  timer = null;
  toast.set(null);
}

export function showToast(spec: ToastSpec, ms = 5000): void {
  if (timer) clearTimeout(timer);
  const id = ++seq;
  const wrap = (fn?: () => void) => (fn ? () => { dismissToast(); fn(); } : undefined);
  toast.set({ ...spec, id, undo: wrap(spec.undo), action: spec.action ? { label: spec.action.label, run: wrap(spec.action.run)! } : undefined });
  timer = setTimeout(() => { if (seq === id) dismissToast(); }, ms);
}
