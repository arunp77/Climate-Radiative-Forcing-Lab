import { describe, expect, it } from "vitest";
import vectors from "./nonghg_vectors.json";
import balance from "../public/data/forcing_balance.json";
import { nonGhgErf, type NonGhgParams } from "../src/nonghg";

const p = balance.nonghg as unknown as NonGhgParams;

describe("TypeScript non-GHG emulators equal the Python reference", () => {
  it("matches all exported vectors to 1e-9 W m-2", () => {
    expect(vectors.length).toBeGreaterThan(100);
    let worst = 0;
    for (const v of vectors) {
      const r = nonGhgErf(p, v.state);
      for (const k of Object.keys(v.erf)) worst = Math.max(worst, Math.abs(r[k] - (v.erf as Record<string, number>)[k]));
    }
    expect(worst).toBeLessThan(1e-9);
  });
  it("default drivers give AR6 2019 values", () => {
    const r = nonGhgErf(p);
    for (const [k, v] of Object.entries(p.ar6_2019)) expect(r[k]).toBeCloseTo(v, 10);
  });
});
