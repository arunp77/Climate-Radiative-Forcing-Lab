import { describe, expect, it } from "vitest";
import vectors from "./planck_vectors.json";
import { radiance, flux } from "../src/planck";

describe("TypeScript Planck equals Python", () => {
  it("matches reference vectors to 1e-12 relative", () => {
    for (const v of vectors) expect(Math.abs(radiance(v.nu, v.T) / v.B - 1)).toBeLessThan(1e-12);
  });
  it("integrates to the Stefan-Boltzmann law", () => {
    let s = 0; const dn = 0.5;
    for (let n = dn / 2; n < 30000; n += dn) s += flux(n, 288.15) * dn;
    expect(s / (5.670374419e-8 * 288.15 ** 4)).toBeCloseTo(1, 3);
  });
});
