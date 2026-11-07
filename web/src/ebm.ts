/**
 * Three-layer energy balance model (the physical core of FaIR v2; Leach et al. 2021, Cummins et al. 2020).
 * Port of physics/radforce/ebm.py; both are tested against the same FaIR run.
 *
 *   C0 dT0/dt = s - k0 T0 - k1 (T0 - T1)
 *   C1 dT1/dt = k1 (T0 - T1) - eps k2 (T1 - T2)
 *   C2 dT2/dt = k2 (T1 - T2)
 *   ds/dt     = gamma (F - s)                 (forcing filter, gamma = 2 per year in FaIR)
 */
export interface EbmParams {
  C: [number, number, number];      // W yr m-2 K-1
  kappa: [number, number, number];  // W m-2 K-1; kappa[0] is the climate-feedback parameter
  epsilon: number;                  // deep-ocean efficacy
  F4x: number;                      // W m-2, forcing of 4 x CO2
  gamma: number | null;             // yr-1, forcing filter; null = none
}

type Mat = number[][];
const eye = (n: number): Mat => Array.from({ length: n }, (_, i) => Array.from({ length: n }, (_, j) => (i === j ? 1 : 0)));
const mul = (A: Mat, B: Mat): Mat => A.map((r) => B[0].map((_, j) => r.reduce((s, v, k) => s + v * B[k][j], 0)));
const mv = (A: Mat, x: number[]): number[] => A.map((r) => r.reduce((s, v, k) => s + v * x[k], 0));
const scale = (A: Mat, c: number): Mat => A.map((r) => r.map((v) => v * c));
const add = (A: Mat, B: Mat): Mat => A.map((r, i) => r.map((v, j) => v + B[i][j]));

/** Matrix exponential by scaling and squaring with a Taylor series (the matrices here are 3x3 or 4x4 and well conditioned). */
export function expm(A: Mat): Mat {
  const n = A.length;
  const norm = Math.max(...A.map((r) => r.reduce((s, v) => s + Math.abs(v), 0)));
  const sq = Math.max(0, Math.ceil(Math.log2(Math.max(norm, 1e-12))) + 1);
  const As = scale(A, 1 / 2 ** sq);
  let term = eye(n), sum = eye(n);
  for (let k = 1; k <= 18; k++) { term = scale(mul(term, As), 1 / k); sum = add(sum, term); }
  for (let i = 0; i < sq; i++) sum = mul(sum, sum);
  return sum;
}

/** Solve A x = b by Gaussian elimination with partial pivoting. */
export function solve(A: Mat, b: number[]): number[] {
  const n = b.length;
  const M = A.map((r, i) => [...r, b[i]]);
  for (let c = 0; c < n; c++) {
    let p = c;
    for (let r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r;
    [M[c], M[p]] = [M[p], M[c]];
    for (let r = c + 1; r < n; r++) { const f = M[r][c] / M[c][c]; for (let k = c; k <= n; k++) M[r][k] -= f * M[c][k]; }
  }
  const x = new Array(n).fill(0);
  for (let r = n - 1; r >= 0; r--) { let s = M[r][n]; for (let k = r + 1; k < n; k++) s -= M[r][k] * x[k]; x[r] = s / M[r][r]; }
  return x;
}

export const f2x = (p: EbmParams) => p.F4x / 2;
export const ecs = (p: EbmParams) => f2x(p) / p.kappa[0];
export const withEcs = (p: EbmParams, target: number): EbmParams => ({ ...p, kappa: [f2x(p) / target, p.kappa[1], p.kappa[2]] });
export const withOceanMixing = (p: EbmParams, factor: number): EbmParams => ({ ...p, kappa: [p.kappa[0], p.kappa[1] * factor, p.kappa[2] * factor] });

function layerMatrix(p: EbmParams): Mat {
  const { C, kappa: k, epsilon: e } = p;
  return [
    [-(k[0] + k[1]) / C[0], k[1] / C[0], 0],
    [k[1] / C[1], -(k[1] + e * k[2]) / C[1], (e * k[2]) / C[1]],
    [0, k[2] / C[2], -k[2] / C[2]],
  ];
}

function stepper(p: EbmParams, dt: number) {
  const A3 = layerMatrix(p);
  const filtered = p.gamma !== null;
  const n = filtered ? 4 : 3;
  const A: Mat = Array.from({ length: n }, () => new Array(n).fill(0));
  const off = filtered ? 1 : 0;
  for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) A[i + off][j + off] = A3[i][j];
  const b = new Array(n).fill(0);
  if (filtered) { A[0][0] = -(p.gamma as number); A[1][0] = 1 / p.C[0]; b[0] = p.gamma as number; } else b[0] = 1 / p.C[0];
  const Ad = expm(scale(A, dt));
  const AdI = add(Ad, scale(eye(n), -1));
  const Bd = solve(scale(A, 1), mv(AdI, b));
  return { Ad, Bd, filtered };
}

/** Layer temperatures at the start of every step and after the last: array of length n+1, each [T0, T1, T2]. */
export function runEbm(p: EbmParams, forcing: ArrayLike<number>, dt = 1, s0 = 0): number[][] {
  const { Ad, Bd, filtered } = stepper(p, dt);
  let x = new Array(filtered ? 4 : 3).fill(0);
  if (filtered) x[0] = s0;
  const out: number[][] = [filtered ? x.slice(1) : x.slice()];
  for (let i = 0; i < forcing.length; i++) {
    const nx = mv(Ad, x);
    for (let k = 0; k < nx.length; k++) nx[k] += Bd[k] * forcing[i];
    x = nx;
    out.push(filtered ? x.slice(1) : x.slice());
  }
  return out;
}

/** Warming at CO2 doubling under a 1 %/yr increase (forcing rising linearly to F2x over ``years``). */
export function tcr(p: EbmParams, years = 70): number {
  const n = years * 20, dt = years / n;
  const f = Array.from({ length: n }, (_, i) => (f2x(p) * (i + 0.5)) / n);
  return runEbm(p, f, dt)[n][0];
}

/** Annual-mean surface temperature anomaly (relative to the mean of ``base``) from the layer states at the time bounds. */
export function annualAnomaly(states: number[][], years: number[], base: [number, number] = [1850, 1900]): number[] {
  const t = states.slice(0, -1).map((s, i) => 0.5 * (s[0] + states[i + 1][0]));
  const idx = years.map((y, i) => [y, i] as const).filter(([y]) => y >= base[0] && y <= base[1]).map(([, i]) => i);
  const m = idx.reduce((s, i) => s + t[i], 0) / idx.length;
  return t.map((v) => v - m);
}
