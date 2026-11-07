/** Pure helpers for the history view (unit-tested in tests/history.test.ts). */

export interface History {
  years: number[];
  ids: string[];
  values: Record<string, number[]>;
  net: number[];
}

/** Fixed axis range covering every component in every year, padded and rounded outward to 0.2. */
export function playbackAxis(h: History): [number, number] {
  let lo = 0, hi = 0;
  for (const id of h.ids) for (const v of h.values[id]) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
  const r = (x: number, f: (n: number) => number) => f(x / 0.2) * 0.2;
  return [r(lo - 0.1, Math.floor), r(hi + 0.1, Math.ceil)];
}

export function clampYear(y: number, h: History): number {
  const lo = h.years[0], hi = h.years[h.years.length - 1];
  if (!Number.isFinite(y)) return hi;
  return Math.min(hi, Math.max(lo, Math.round(y)));
}

/** Next frame of the animation; wraps to the first year after the last. */
export function nextYear(y: number, h: History): number {
  const last = h.years[h.years.length - 1];
  return y >= last ? h.years[0] : y + 1;
}

export function valuesAt(h: History, year: number): Record<string, number> {
  const i = h.years.indexOf(clampYear(year, h));
  return Object.fromEntries(h.ids.map((id) => [id, h.values[id][i]]));
}

export function netAt(h: History, year: number): number {
  return h.net[h.years.indexOf(clampYear(year, h))];
}
