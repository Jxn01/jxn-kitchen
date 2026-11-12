// Is the offline badge on screen? One answer for the badge itself and for every overlay that must stay clear of it
// (the toast rises above it, or a long one slides under the badge and loses its first words).
import { derived } from 'svelte/store';
import { online } from './offline';
import { outbox } from './queue';

export const badgeShown = derived([online, outbox.pending], ([o, waiting]) => !o || waiting > 0);
