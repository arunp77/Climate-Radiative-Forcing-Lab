import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { annualAnomaly, ecs, expm, runEbm, solve, tcr, withEcs, withOceanMixing, type EbmParams } from "../src/ebm";

const data = JSON.parse(readFileSync("public/data/scenarios.json", "utf8"));
const P: EbmParams = { C: data.params.c, kappa: data.params.kappa, epsilon: data.params.epsilon, F4x: data.params.F4x, gamma: 2 };

describe("linear algebra helpers", () => {
  it("expm of a diagonal matrix is exp of the diagonal", () => {
    const E = expm([[-1, 0], [0, 0.5]]);
    expect(E[0][0]).toBeCloseTo(Math.exp(-1), 12);
    expect(E[1][1]).toBeCloseTo(Math.exp(0.5), 12);
    expect(Math.abs(E[0][1])).toBeLessThan(1e-14);
  });
  it("expm of a rotation generator is a rotation", () => {
    const E = expm([[0, -2], [2, 0]]);
    expect(E[0][0]).toBeCloseTo(Math.cos(2), 12);
    expect(E[1][0]).toBeCloseTo(Math.sin(2), 12);
  });
  it("solves a linear system", () => {
    const x = solve([[2, 1], [1, 3]], [5, 10]);
    expect(x[0]).toBeCloseTo(1, 12); expect(x[1]).toBeCloseTo(3, 12);
  });
});

describe("energy balance model", () => {
  it("reproduces the FaIR run it was calibrated from (all five SSPs)", () => {
    for (const [name, s] of Object.entries<any>(data.scenarios)) {
      const b: number[] = s.erf_driving_bounds;
      const T = annualAnomaly(runEbm(P, b.slice(1), 1, b[0]), data.years);
      let worst = 0;
      s.temperature.forEach((r: number, i: number) => { worst = Math.max(worst, Math.abs(T[i] - r)); });
      expect(worst, name).toBeLessThan(0.002);   // K; the stored FaIR values are rounded to 0.001
    }
  });
  it("has ECS = F2x / kappa0 and the equilibrium response equals ERF / lambda", () => {
    expect(ecs(P)).toBeCloseTo(3.0, 1);
    const T = runEbm({ ...P, gamma: null }, new Array(3000).fill(P.F4x / 2));
    expect(T[3000][0]).toBeCloseTo(ecs(P) * (P.F4x / 2) / (P.F4x / 2), 2); // = ECS for forcing F2x
  });
  it("TCR is below ECS and matches the Python reference", () => {
    expect(tcr(P)).toBeCloseTo(1.724, 2);          // radforce.ebm.tcr on the same parameters
    expect(tcr(P)).toBeLessThan(ecs(P));
  });
  it("withEcs sets the sensitivity exactly and raises warming monotonically", () => {
    expect(ecs(withEcs(P, 4.5))).toBeCloseTo(4.5, 12);
    const f = new Array(150).fill(3.0);
    const t = (e: number) => runEbm(withEcs(P, e), f)[150][0];
    expect(t(2)).toBeLessThan(t(3)); expect(t(3)).toBeLessThan(t(5));
  });
  it("faster ocean mixing delays surface warming", () => {
    const f = new Array(70).fill(3.0);
    expect(runEbm(withOceanMixing(P, 2), f)[70][0]).toBeLessThan(runEbm(withOceanMixing(P, 0.5), f)[70][0]);
  });
});
