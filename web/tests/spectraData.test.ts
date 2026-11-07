import { describe, expect, it } from "vitest";
import { existsSync, readFileSync } from "node:fs";
import {
  binNu, columnAt, diffMilli, equivalentWidth, formatColumn, formatMultiple, haloSpec, inIntervals, linearForcing, nearestEntry,
  transmission, wavelengthUm, type GasMeta, type HaloData, type LabData, type OlrData,
} from "../src/spectraData";

const dir = new URL("../public/data/spectra/", import.meta.url);
const load = <T>(f: string) => JSON.parse(readFileSync(new URL(f, dir), "utf8")) as T;
const built = existsSync(new URL("olr_halo.json", dir)) && existsSync(new URL("gases.json", dir));

describe("spectra helpers", () => {
  it("formats columns and multiples readably", () => {
    expect(formatColumn(8.8e21)).toBe("8.8×10²¹");
    expect(formatMultiple(1)).toBe("1×");
    expect(formatMultiple(10)).toBe("10×");
    expect(formatMultiple(1000)).toBe("1000×");
    expect(formatMultiple(0.5)).toBe("0.5×");
    expect(wavelengthUm(667)).toBeCloseTo(14.99, 2);
    expect(binNu(0, 10.5, 1)).toBe(10.5);
  });
  it("finds the nearest entry in log space and handles zero", () => {
    const e = [{ value: 0 }, { value: 100 }, { value: 1000 }];
    expect(nearestEntry(e, 300)).toBe(1);
    expect(nearestEntry(e, 0)).toBe(0);
    expect(nearestEntry(e, 800)).toBe(2);
  });
  it("interval membership, halo reconstruction and linear forcing", () => {
    expect(inIntervals(900, [[800, 1000]])).toBe(true);
    expect(inIntervals(700, [[800, 1000]])).toBe(false);
    const e = { value: 1, olr: 0, irf: 0, olr_all: 0, irf_all: 0, dspec: [-1000, 0], dspec_all: [-500, 0] };
    expect(haloSpec([0.2, 0.3], e, "clear")).toEqual([0.2 - 0.001, 0.3]);
    expect(haloSpec([0.2, 0.3], e, "all")[0]).toBeCloseTo(0.2 - 0.0005, 12);
    expect(diffMilli([0.3, 0.1], [0.1, 0.1])).toEqual([0.19999999999999998 * 1000 / 1, 0]);
    expect(linearForcing(0.358, 500)).toBeCloseTo(0.179, 6);
  });
  it("equivalent width skips missing bins", () => {
    expect(equivalentWidth([0.5, null, 0.0], 0, 100, 10, 1)).toBeCloseTo(1.5, 12);
  });
});

describe.runIf(built)("shipped spectral tables", () => {
  const meta = load<Record<string, GasMeta>>("gases.json");
  const olr = load<OlrData>("olr.json");
  const halo = load<HaloData>("olr_halo.json");

  it("has all 22 molecules, unique colours, and a lab table for each", () => {
    const ids = Object.keys(meta);
    expect(ids.length).toBe(22);
    expect(new Set(ids.map((i) => meta[i].colour)).size).toBe(22);
    for (const id of ids) {
      expect(existsSync(new URL(`lab_${id}.json`, dir)), id).toBe(true);
      expect(meta[id].coverage.length).toBeGreaterThan(0);
      if (meta[id].source === "xsec") { expect(meta[id].ar6_re!).toBeGreaterThan(0); expect(meta[id].c2019_ppt!).toBeGreaterThan(0); }
    }
  });

  it("lab tables: 19 columns x 3990 bins, transmission falls with column", () => {
    for (const id of Object.keys(meta)) {
      const d = load<LabData>(`lab_${id}.json`);
      expect(d.log10_columns.length).toBe(19);
      for (const c of Object.keys(d.t)) {
        expect(d.t[c].length).toBe(19);
        expect(d.t[c][0].length).toBe(3990);
        for (let k = 1; k < 19; k++) for (let i = 0; i < 3990; i += 7)
          expect(d.t[c][k][i], `${id} ${c} k=${k} i=${i}`).toBeLessThanOrEqual(d.t[c][k - 1][i] + 1);   // x1000 rounding
      }
    }
  });

  it("CO2 band is opaque at the atmospheric column and the window is clear", () => {
    const d = load<LabData>("lab_CO2.json");
    const k = d.log10_columns.findIndex((v) => v >= Math.log10(d.n_atm) - 0.26);
    const t = transmission(d, "surface", k) as number[];
    const mean = (lo: number, hi: number) => { let s = 0, n = 0; t.forEach((v, i) => { const nu = binNu(i, d.nu_start, d.dnu); if (nu > lo && nu < hi) { s += v; n++; } }); return s / n; };
    expect(mean(640, 700)).toBeLessThan(0.05);
    expect(mean(850, 950)).toBeGreaterThan(0.95);
    expect(columnAt(d, k)).toBeGreaterThan(d.n_atm * 0.5);
  });

  it("halocarbon bands sit in the window and absorb strongly at a 1e19 column", () => {
    for (const [id, lo, hi] of [["SF6", 920, 980], ["CFC-12", 1140, 1180], ["HFC-134a", 1100, 1200], ["CF4", 1270, 1295]] as [string, number, number][]) {
      const d = load<LabData>(`lab_${id}.json`);
      const k = d.log10_columns.indexOf(19);
      const t = transmission(d, "surface", k);
      let m = 1; t.forEach((v, i) => { const nu = binNu(i, d.nu_start, d.dnu); if (v !== null && nu > lo && nu < hi) m = Math.min(m, v); });
      expect(m, id).toBeLessThan(0.2);
    }
  });

  it("uncovered wavenumbers are null, not transparent", () => {
    const d = load<LabData>("lab_CCl4.json");
    const t = transmission(d, "surface", 10);
    expect(t[binNu(0, d.nu_start, d.dnu) < 100 ? 0 : 0]).toBeNull();   // 10 cm-1 is outside the measured range
    expect(t.some((v) => v !== null)).toBe(true);
  });

  it("all-sky estimate is calibrated to the observed longwave cloud effect", () => {
    expect(olr.cloud.model_lw_cre).toBeCloseTo(27.9, 4);
    expect(olr.baseline.olr_all).toBeLessThan(olr.baseline.olr);
  });

  it("every halocarbon: forcing rises with amount and clear sky exceeds all-sky", () => {
    expect(Object.keys(halo.gases).length).toBe(17);
    for (const [id, g] of Object.entries(halo.gases)) {
      const irf = g.entries.map((e) => e.irf), all = g.entries.map((e) => e.irf_all);
      expect(Math.abs(irf[0]), id).toBeLessThan(1e-9);
      for (let i = 1; i < irf.length; i++) { expect(irf[i], id).toBeGreaterThan(irf[i - 1]); expect(all[i], id).toBeGreaterThan(all[i - 1]); }
      expect(g.re_clear, id).toBeGreaterThan(g.re_all);
      expect(g.entries[0].dspec.length).toBe(3990);
    }
  });
});
