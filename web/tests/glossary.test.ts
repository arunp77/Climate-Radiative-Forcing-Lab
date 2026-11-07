import { describe, expect, it } from "vitest";
import { decodeRule90 } from "../src/glossaryView";
import { TERMS, CATEGORIES } from "../src/glossary";

describe("rule of 90", () => {
  // halocarbon number -> [C, H, F, Cl, family], each checked against the known formula
  const known: [number, [number, number, number, number, string]][] = [
    [11, [1, 0, 1, 3, "CFC"]],      // CCl3F
    [12, [1, 0, 2, 2, "CFC"]],      // CCl2F2
    [113, [2, 0, 3, 3, "CFC"]],     // C2Cl3F3
    [114, [2, 0, 4, 2, "CFC"]],     // C2Cl2F4
    [22, [1, 1, 2, 1, "HCFC"]],     // CHClF2
    [141, [2, 3, 1, 2, "HCFC"]],    // CH3CCl2F
    [142, [2, 3, 2, 1, "HCFC"]],    // CH3CClF2
    [23, [1, 1, 3, 0, "HFC"]],      // CHF3
    [32, [1, 2, 2, 0, "HFC"]],      // CH2F2
    [125, [2, 1, 5, 0, "HFC"]],     // C2HF5
    [134, [2, 2, 4, 0, "HFC"]],     // C2H2F4
    [143, [2, 3, 3, 0, "HFC"]],     // C2H3F3
    [14, [1, 0, 4, 0, "PFC"]],      // CF4
    [116, [2, 0, 6, 0, "PFC"]],     // C2F6
    [218, [3, 0, 8, 0, "PFC"]],     // C3F8
  ];
  it.each(known)("decodes %i", (n, [C, H, F, Cl, fam]) => {
    const d = decodeRule90(n)!;
    expect([d.C, d.H, d.F, d.Cl, d.family]).toEqual([C, H, F, Cl, fam]);
  });
  it("formats formulas", () => {
    expect(decodeRule90(11)!.formula).toBe("CCl₃F");
    expect(decodeRule90(134)!.formula).toBe("C₂H₂F₄");
    expect(decodeRule90(14)!.formula).toBe("CF₄");
  });
  it("rejects impossible numbers", () => {
    expect(decodeRule90(0)).toBeNull();
    expect(decodeRule90(1000)).toBeNull();
    expect(decodeRule90(1.5)).toBeNull();
  });
});

describe("glossary content", () => {
  it("has unique terms with text and known categories", () => {
    const names = TERMS.map((t) => t.term);
    expect(new Set(names).size).toBe(names.length);
    for (const t of TERMS) { expect(t.def.length).toBeGreaterThan(30); expect(CATEGORIES).toContain(t.cat); }
  });
});
