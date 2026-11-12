// The app's own on-screen keyboard (the kiosk has no Windows touch keyboard once Explorer is gone).
// Letter keys are strings; special keys are objects.
export type Special = 'shift' | 'back' | 'space' | 'enter' | 'mode' | 'lang';
export type KeyDef = string | { k: Special; w?: number };

const bottom: KeyDef[] = [{ k: 'mode', w: 1.5 }, { k: 'lang', w: 1.2 }, { k: 'space', w: 5 }, { k: 'enter', w: 2 }];

export const LAYOUTS: Record<'en' | 'hu' | 'num', KeyDef[][]> = {
  en: [
    [...'qwertyuiop'],
    [...'asdfghjkl'],
    [{ k: 'shift', w: 1.5 }, ...'zxcvbnm', { k: 'back', w: 1.5 }],
    bottom,
  ],
  hu: [
    [...'qwertzuiopőú'],
    [...'asdfghjkléáű'],
    [{ k: 'shift', w: 1.3 }, ...'íyxcvbnmöüó', { k: 'back', w: 1.3 }],
    bottom,
  ],
  num: [
    [...'1234567890'],
    [...'-/:;()&@"\''],
    [{ k: 'shift', w: 1.5 }, ...'.,?!½¼°', { k: 'back', w: 1.5 }],
    bottom,
  ],
};

export function applyKey(value: string, key: string, shift: boolean): string {
  if (key === 'back') return value.slice(0, -1);
  if (key === 'space') return value + ' ';
  return value + (shift ? key.toLocaleUpperCase('hu') : key);
}
