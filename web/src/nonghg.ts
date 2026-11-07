/**
 * TypeScript port of radforce.forcing.nonghg (physics/radforce/forcing/nonghg.py).
 * Parameters come from public/data/forcing_balance.json ("nonghg"), generated from the
 * Python package; tests/nonghg.test.ts compares this port with Python-generated vectors.
 */
import { ch4Forcing } from "./forcing";

export interface NonGhgParams {
  emis_1750: Record<string, number>;
  emis_2019: Record<string, number>;
  ari_beta: Record<string, number>;
  aci_n0: number;
  aci_n1: number;
  ozone_coeff: Record<"CH4" | "N2O" | "ODS" | "CO" | "VOC" | "NOx", number>;
  ch4_1750: number; n2o_1750: number; ch4_2019: number; n2o_2019: number;
  eesc_2019: number; ch4_erf_2019: number;
  ar6_2019: Record<string, number>;
}

/** Drivers: emissions as multiples of 2019 (lower-case keys), ODS as multiple of 2019 EESC, gases in ppb. */
export interface DriverState {
  so2?: number; bc?: number; oc?: number; nh3?: number; nox?: number; co?: number; voc?: number;
  ods?: number; ch4?: number; n2o?: number; landuse?: number; contrails?: number;
}

const SPECIES = ["SO2", "BC", "OC", "NH3", "NOx", "CO", "VOC"] as const;
const g = (s: DriverState, k: keyof DriverState, d: number) => (s[k] ?? d);

function emis(p: NonGhgParams, s: DriverState): Record<string, number> {
  return Object.fromEntries(SPECIES.map((k) => [k, p.emis_2019[k] * g(s, k.toLowerCase() as keyof DriverState, 1)]));
}

function raw(p: NonGhgParams, s: DriverState) {
  const E = emis(p, s);
  const ari = Object.keys(p.ari_beta).reduce((a, k) => a + p.ari_beta[k] * (E[k] - p.emis_1750[k]), 0);
  const aciLog = (e: Record<string, number>) => Math.log(1 + e.SO2 / p.aci_n0 + (e.BC + e.OC) / p.aci_n1);
  const aci = -(aciLog(E) - aciLog(p.emis_1750));
  const bc = E.BC - p.emis_1750.BC;
  const c = p.ozone_coeff;
  const o3 = c.CH4 * (g(s, "ch4", p.ch4_2019) - p.ch4_1750) + c.N2O * (g(s, "n2o", p.n2o_2019) - p.n2o_1750)
    + c.ODS * p.eesc_2019 * g(s, "ods", 1) + c.CO * (E.CO - p.emis_1750.CO)
    + c.VOC * (E.VOC - p.emis_1750.VOC) + c.NOx * (E.NOx - p.emis_1750.NOx);
  return { Aerosol_ari: ari, Aerosol_aci: aci, BC_snow: bc, O3: o3 };
}

/** ERF (W m-2 vs 1750) of the non-CO2/CH4/N2O agents; equals AR6 2019 at default drivers. */
export function nonGhgErf(p: NonGhgParams, s: DriverState = {}): Record<string, number> {
  const now = raw(p, s), ref = raw(p, {});
  const out: Record<string, number> = {};
  for (const k of Object.keys(now) as (keyof typeof now)[]) out[k] = (p.ar6_2019[k] * now[k]) / ref[k];
  const ch4 = g(s, "ch4", p.ch4_2019), n2o = g(s, "n2o", p.n2o_2019);
  out.H2O_strat = (p.ar6_2019.H2O_strat * ch4Forcing(ch4, n2o, "meinshausen2020", true)) / p.ch4_erf_2019;
  out.Contrails = p.ar6_2019.Contrails * g(s, "contrails", 1);
  out.LandUse = p.ar6_2019.LandUse * g(s, "landuse", 1);
  return out;
}
