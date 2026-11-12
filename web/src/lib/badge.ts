// Is the offline badge on screen? One answer for the badge itself and for every overlay that must stay clear of it
// (the toast rises above it: on 2026-11-12 a long toast slid under the badge and lost its first words).
import { derived } from 'svelte/store';
import { online } from './offline';
import { outbox } from './queue';

export const badgeShown = derived([online, outbox.pending], ([o, waiting]) => !o || waiting > 0);
