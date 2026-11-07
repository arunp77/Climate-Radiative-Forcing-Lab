/**
 * TypeScript port of radforce.forcing.wmghg (physics/radforce/forcing/wmghg.py).
 *
 * The Python package is the source of truth.  This port exists only so sliders respond
 * instantly in the browser; tests/forcing.test.ts compares it with Python-generated
 * reference vectors (web/tests/forcing_vectors.json, produced by build/export_web_data.py).
 * Do not edit coefficients here without changing physics/radforce/constants.py.
 *
 * Units: CO2 in ppm, CH4 and N2O in ppb.  Results in W m-2 relative to 1750.
 */

export type Scheme = "meinshausen2020" | "etminan2016" | "myhre1998";

export const PI = { CO2: 278.3, CH4: 729.2, N2O: 270.1 } as const;

// IPCC AR6 WG1 Sect. 7.3.2 tropospheric adjustments: ERF = SARF x factor
export const ERF_FROM_SARF = { CO2: 1.05, CH4: 0.86, N2O: 1.07 } as const;

const MEIN = {
  a1: -2.4785e-7, b1: 0.00075906, c1: -0.0021492, d1: 5.2488,
  a2: -0.00034197, b2: 0.00025455, c2: -0.00024357, d2: 0.12173,
  a3: -8.9603e-5, b3: -0.00012462, d3: 0.045194,
};
const ETM = {
  a1: -2.4e-7, b1: 7.2e-4, c1: -2.1e-4, d1: 5.36,
  a2: -8.0e-6, b2: 4.2e-6, c2: -4.9e-6, d2: 0.117,
  a3: -1.3e-6, b3: -8.2e-6, d3: 0.043,
};
const MYH = { co2: 5.35, ch4: 0.036, n2o: 0.12, ov: 0.47, a1: 2.01e-5, e1: 0.75, a2: 5.31e-15, e2: 1.52 };

const f = (erf: boolean, gas: keyof typeof ERF_FROM_SARF) => (erf ? ERF_FROM_SARF[gas] : 1);

/** Myhre et al. (1998) CH4-N2O overlap function, W m-2. */
export function overlap(M: number, N: number): number {
  return MYH.ov * Math.log(1 + MYH.a1 * (M * N) ** MYH.e1 + MYH.a2 * M * (M * N) ** MYH.e2);
}

export function co2Forcing(C: number, N: number, scheme: Scheme, erf: boolean): number {
  const dC = C - PI.CO2;
  if (scheme === "myhre1998") return MYH.co2 * Math.log(C / PI.CO2);
  if (scheme === "etminan2016") {
    const p = ETM;
    return (p.a1 * dC * dC + p.b1 * Math.abs(dC) + p.c1 * 0.5 * (N + PI.N2O) + p.d1) *
      Math.log(C / PI.CO2) * f(erf, "CO2");
  }
  const p = MEIN;
  const dMax = -p.b1 / (2 * p.a1);
  const alpha = dC <= 0 ? p.d1
    : dC <= dMax ? p.d1 + p.a1 * dC * dC + p.b1 * dC
    : p.d1 - (p.b1 * p.b1) / (4 * p.a1);
  return (alpha + p.c1 * Math.sqrt(N)) * Math.log(C / PI.CO2) * f(erf, "CO2");
}

export function ch4Forcing(M: number, N: number, scheme: Scheme, erf: boolean): number {
  if (scheme === "myhre1998") {
    return MYH.ch4 * (Math.sqrt(M) - Math.sqrt(PI.CH4)) - (overlap(M, PI.N2O) - overlap(PI.CH4, PI.N2O));
  }
  const coeff = scheme === "etminan2016"
    ? ETM.a3 * 0.5 * (M + PI.CH4) + ETM.b3 * 0.5 * (N + PI.N2O) + ETM.d3
    : MEIN.a3 * Math.sqrt(M) + MEIN.b3 * Math.sqrt(N) + MEIN.d3;
  return coeff * (Math.sqrt(M) - Math.sqrt(PI.CH4)) * f(erf, "CH4");
}

export function n2oForcing(N: number, C: number, M: number, scheme: Scheme, erf: boolean): number {
  if (scheme === "myhre1998") {
    return MYH.n2o * (Math.sqrt(N) - Math.sqrt(PI.N2O)) - (overlap(PI.CH4, N) - overlap(PI.CH4, PI.N2O));
  }
  const coeff = scheme === "etminan2016"
    ? ETM.a2 * 0.5 * (C + PI.CO2) + ETM.b2 * 0.5 * (N + PI.N2O) + ETM.c2 * 0.5 * (M + PI.CH4) + ETM.d2
    : MEIN.a2 * Math.sqrt(C) + MEIN.b2 * Math.sqrt(N) + MEIN.c2 * Math.sqrt(M) + MEIN.d2;
  return coeff * (Math.sqrt(N) - Math.sqrt(PI.N2O)) * f(erf, "N2O");
}

export function wmghg(C: number, M: number, N: number, scheme: Scheme, erf: boolean) {
  const co2 = co2Forcing(C, N, scheme, erf);
  const ch4 = ch4Forcing(M, N, scheme, erf);
  const n2o = n2oForcing(N, C, M, scheme, erf);
  return { co2, ch4, n2o, total: co2 + ch4 + n2o };
}
