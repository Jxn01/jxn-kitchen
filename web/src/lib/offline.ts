// One "are we connected?" flag for the badge, fed by the SSE channel and by every /api call.
import { writable } from 'svelte/store';
import { onApiStatus } from './api';

export const online = writable(true);
export function report(ok: boolean): void { online.set(ok); }
onApiStatus(report);
