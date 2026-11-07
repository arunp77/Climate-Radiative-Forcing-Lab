import { describe, expect, it } from "vitest";
import { clampYear, netAt, nextYear, playbackAxis, valuesAt, type History } from "../src/history";
import balance from "../public/data/forcing_balance.json";

const h = balance.history as unknown as History;

describe("history helpers", () => {
  it("covers 1850-2019 for all 11 agents", () => {
    expect(h.years[0]).toBe(1850);
    expect(h.years[h.years.length - 1]).toBe(2019);
    expect(h.ids.length).toBe(11);
    for (const id of h.ids) expect(h.values[id].length).toBe(h.years.length);
  });
  it("axis contains every value", () => {
    const [lo, hi] = playbackAxis(h);
    for (const id of h.ids) for (const v of h.values[id]) { expect(v).toBeGreaterThanOrEqual(lo); expect(v).toBeLessThanOrEqual(hi); }
    expect(lo).toBeLessThan(0); expect(hi).toBeGreaterThan(2.1);
  });
  it("clamps and wraps years", () => {
    expect(clampYear(1200, h)).toBe(1850);
    expect(clampYear(3000, h)).toBe(2019);
    expect(clampYear(NaN, h)).toBe(2019);
    expect(clampYear(1950.4, h)).toBe(1950);
    expect(nextYear(2019, h)).toBe(1850);
    expect(nextYear(1900, h)).toBe(1901);
  });
  it("2019 values equal the AR6 balance sheet used on the first tab", () => {
    const v = valuesAt(h, 2019);
    for (const c of balance.components) expect(v[c.id]).toBeCloseTo(c.best, 4);
    expect(netAt(h, 2019)).toBeCloseTo(2.72, 2);
  });
  it("net equals the sum of agents every year (AR6 total_anthropogenic definition)", () => {
    h.years.forEach((y) => {
      const sum = h.ids.reduce((s, id) => s + valuesAt(h, y)[id], 0);
      expect(Math.abs(sum - netAt(h, y))).toBeLessThan(1e-3);
    });
  });
});
