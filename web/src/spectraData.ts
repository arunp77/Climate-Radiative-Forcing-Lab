/** Types and pure helpers for the spectra views (unit-tested in tests/spectraData.test.ts). */

export type Gas = string;

export interface GasMeta {
  id: Gas; group: string; html: string; colour: string; name: string; source: "lines" | "xsec";
  bands: { nu: number; label: string }[]; n_atm: number; coverage: [number, number][];
  c1750_ppt?: number; c2019_ppt?: number; ar6_re?: number;
  datasets?: { range: [number, number]; files: number; T: [number, number]; p_torr: [number, number]; ref: string; broadener: string }[];
}

export interface LabData {
  gas: Gas; n_atm: number; log10_columns: number[]; nu_start: number; dnu: number;
  conditions: Record<string, { p_atm: number; T: number; label: string }>;
  t: Record<string, number[][]>;                 // [condition][column][bin], transmission x 1000
  covered: Record<string, [number, number][]>;   // measured wavenumber intervals per condition
}

export interface OlrEntry { value: number; olr: number; irf: number; olr_all: number; irf_all: number; spec: number[]; spec_all: number[] }
export interface CloudModel {
  cover: number; deck_km: [number, number]; tau_c: number; target_lw_cre: number; model_lw_cre: number;
  model_clear_olr: number; model_allsky_olr: number; ceres_clear_olr: number; ceres_allsky_olr: number; source: string;
}
export interface OlrData {
  nu_start: number; dnu: number; T_surface: number; notes: string; cloud: CloudModel;
  baseline: { olr: number; olr_all: number; spec: number[]; spec_all: number[]; gases: Record<string, number> };
  sweeps: Record<string, { unit: string; entries: OlrEntry[] }>;
  all_2019: OlrEntry;
}
export interface HaloEntry { value: number; olr: number; irf: number; olr_all: number; irf_all: number; dspec: number[]; dspec_all: number[] }
export interface HaloData {
  multiples: number[]; cloud: CloudModel;
  gases: Record<Gas, { unit: string; entries: HaloEntry[]; re_clear: number; re_all: number; re_ar6: number }>;
}
export type Sky = "clear" | "all";

export const binNu = (i: number, nuStart: number, dnu: number) => nuStart + i * dnu;
export const wavelengthUm = (nu: number) => 1e4 / nu;

export const inIntervals = (nu: number, iv: [number, number][]) => iv.some(([a, b]) => nu >= a && nu <= b);

/** Transmission (0-1) series of one gas/condition/column; bins outside the measured range are null (no data). */
export function transmission(d: LabData, cond: string, colIndex: number): (number | null)[] {
  const iv = d.covered[cond];
  return d.t[cond][colIndex].map((v, i) => (inIntervals(binNu(i, d.nu_start, d.dnu), iv) ? v / 1000 : null));
}

/** Absorber column (molecules cm-2) for a column index. */
export const columnAt = (d: LabData, k: number) => 10 ** d.log10_columns[k];

/** Format a column like 3.2×10²² */
export function formatColumn(n: number): string {
  const e = Math.floor(Math.log10(n));
  const m = n / 10 ** e;
  const sup = String(e).replace(/-/g, "⁻").replace(/\d/g, (c) => "⁰¹²³⁴⁵⁶⁷⁸⁹"[Number(c)]);
  return `${m.toFixed(1)}×10${sup}`;
}

/** How many times the atmospheric column an amount is, formatted readably (e.g. 0.001×, 3.2×, 1000×). */
export function formatMultiple(ratio: number): string {
  const txt = ratio >= 100 ? ratio.toFixed(0) : ratio >= 1 ? ratio.toFixed(Math.abs(ratio - Math.round(ratio)) < 0.05 ? 0 : 1)
    : ratio >= 0.01 ? ratio.toPrecision(2).replace(/0+$/, "").replace(/\.$/, "") : ratio.toExponential(0).replace("e-", "×10⁻").replace(/(⁻)(\d)/, (_, s, d) => s + "⁰¹²³⁴⁵⁶⁷⁸⁹"[Number(d)]);
  return ratio >= 0.01 ? `${txt}×` : txt;
}

/** Equivalent width (cm-1) of the absorption in a bin range: sum of (1 - T) x bin width, skipping missing bins. */
export function equivalentWidth(t: (number | null)[], lo: number, hi: number, nuStart: number, dnu: number): number {
  let w = 0;
  for (let i = 0; i < t.length; i++) {
    const nu = binNu(i, nuStart, dnu);
    const v = t[i];
    if (v !== null && nu >= lo && nu <= hi) w += (1 - v) * dnu;
  }
  return w;
}

/** Index of the entry closest to ``value`` (in log space for positive values). */
export function nearestEntry(entries: { value: number }[], value: number): number {
  let best = 0, bd = Infinity;
  entries.forEach((e, i) => {
    const d = value > 0 && e.value > 0 ? Math.abs(Math.log(e.value / value)) : Math.abs(e.value - value);
    if (d < bd) { bd = d; best = i; }
  });
  return best;
}

/** Outgoing spectrum of a line-gas entry for the chosen sky. */
export const entrySpec = (e: OlrEntry, sky: Sky) => (sky === "all" ? e.spec_all : e.spec);
export const entryOlr = (e: { olr: number; olr_all: number }, sky: Sky) => (sky === "all" ? e.olr_all : e.olr);
export const entryIrf = (e: { irf: number; irf_all: number }, sky: Sky) => (sky === "all" ? e.irf_all : e.irf);

/** Outgoing spectrum of a halocarbon entry: baseline + difference (stored in microW m-2 per cm-1). */
export function haloSpec(base: number[], e: HaloEntry, sky: Sky): number[] {
  const d = sky === "all" ? e.dspec_all : e.dspec;
  return base.map((b, i) => b + d[i] * 1e-6);
}

/** Difference of two spectra in mW m-2 per cm-1. */
export const diffMilli = (a: number[], b: number[]) => a.map((v, i) => (v - b[i]) * 1e3);

/** Linear forcing from the AR6 radiative efficiency (W m-2 ppb-1) for a mixing-ratio change in ppt. */
export const linearForcing = (re: number, dPpt: number) => (re * dPpt) / 1000;
