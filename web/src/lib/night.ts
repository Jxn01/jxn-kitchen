// Mirrors server/kitchen/night.py exactly (same test table): [start, end) by hour, may wrap midnight, start == end = never.
export function isNight(hour: number, start: number, end: number): boolean {
  if (start === end) return false;
  if (start < end) return hour >= start && hour < end;
  return hour >= start || hour < end;
}

/** The hour of day in Europe/Budapest, whatever the device's own time zone. */
export function budapestHour(d: Date): number {
  return Number(new Intl.DateTimeFormat('en-GB', { hour: '2-digit', hour12: false, timeZone: 'Europe/Budapest' }).format(d)) % 24;
}

/** Whether the screen shows the DARK palette. Only the idle scene dims (spec §5 "Idle & night"); an awake screen at
 *  night keeps the light palette (the agent's lowered backlight does the dimming), or its text would be unreadable. */
export function darkScene(night: boolean, routeName: string): boolean {
  return night && routeName === 'idle';
}
