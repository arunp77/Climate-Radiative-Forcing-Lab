import { describe, expect, it } from "vitest";
import vectors from "./forcing_vectors.json";
import { wmghg, type Scheme } from "../src/forcing";

describe("TypeScript forcing equals the Python reference (radforce)", () => {
  it("matches all exported vectors to 1e-9 W m-2", () => {
    expect(vectors.length).toBeGreaterThan(300);
    let worst = 0;
    for (const v of vectors) {
      const r = wmghg(v.C, v.M, v.N, v.scheme as Scheme, v.erf);
      worst = Math.max(worst, Math.abs(r.co2 - v.co2), Math.abs(r.ch4 - v.ch4), Math.abs(r.n2o - v.n2o));
    }
    expect(worst).toBeLessThan(1e-9);
  });

  it("2xCO2 ERF is 3.93 W m-2 (AR6)", () => {
    const r = wmghg(2 * 278.3, 729.2, 270.1, "meinshausen2020", true);
    expect(r.co2).toBeCloseTo(3.93, 1);
  });
});
