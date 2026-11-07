/** Simple original ball-and-stick SVG icons (2-D projections), drawn from atom coordinates. */
import type { Gas } from "./spectraData";

type El = "O" | "C" | "H" | "N" | "F" | "Cl" | "S";
interface Atom { el: El; x: number; y: number }
interface Mol { atoms: Atom[]; bonds: [number, number][] }
const R: Record<El, number> = { O: 9, C: 7, N: 8, H: 4.5, F: 6, Cl: 8, S: 9 };
const FILL: Record<El, string> = { O: "#d94a4a", C: "#4a5560", N: "#4a6fd0", H: "#d9dee4", F: "#7bc96f", Cl: "#2e9e5b", S: "#e5c100" };

const simple = (atoms: Atom[], bonds: [number, number][]): Mol => ({ atoms, bonds });

const MAJOR: Record<string, Mol> = {
  H2O: simple([{ el: "O", x: 30, y: 26 }, { el: "H", x: 14, y: 40 }, { el: "H", x: 46, y: 40 }], [[0, 1], [0, 2]]),
  CO2: simple([{ el: "O", x: 8, y: 30 }, { el: "C", x: 30, y: 30 }, { el: "O", x: 52, y: 30 }], [[0, 1], [1, 2]]),
  CH4: simple([{ el: "C", x: 30, y: 30 }, { el: "H", x: 14, y: 16 }, { el: "H", x: 48, y: 18 }, { el: "H", x: 16, y: 46 }, { el: "H", x: 46, y: 44 }],
    [[0, 1], [0, 2], [0, 3], [0, 4]]),
  N2O: simple([{ el: "N", x: 8, y: 30 }, { el: "N", x: 30, y: 30 }, { el: "O", x: 52, y: 30 }], [[0, 1], [1, 2]]),
  O3: simple([{ el: "O", x: 30, y: 20 }, { el: "O", x: 12, y: 40 }, { el: "O", x: 48, y: 40 }], [[0, 1], [0, 2]]),
};

const P1: [number, number][] = [[14, 14], [46, 14], [14, 46], [46, 46]];
const oneC = (s: El[]): Mol => simple([{ el: "C", x: 30, y: 30 }, ...s.map((el, i) => ({ el, x: P1[i][0], y: P1[i][1] }))], s.map((_, i) => [0, i + 1] as [number, number]));

const PL: [number, number][] = [[9, 16], [9, 44], [20, 53]];
const PR: [number, number][] = [[51, 16], [51, 44], [40, 7]];
const twoC = (a: El[], b: El[]): Mol => {
  const atoms: Atom[] = [{ el: "C", x: 20, y: 30 }, { el: "C", x: 40, y: 30 }];
  const bonds: [number, number][] = [[0, 1]];
  a.forEach((el, i) => { atoms.push({ el, x: PL[i][0], y: PL[i][1] }); bonds.push([0, atoms.length - 1]); });
  b.forEach((el, i) => { atoms.push({ el, x: PR[i][0], y: PR[i][1] }); bonds.push([1, atoms.length - 1]); });
  return { atoms, bonds };
};

const C3F8: Mol = (() => {
  const atoms: Atom[] = [{ el: "C", x: 12, y: 36 }, { el: "C", x: 30, y: 24 }, { el: "C", x: 48, y: 36 }];
  const bonds: [number, number][] = [[0, 1], [1, 2]];
  const f: [number, [number, number]][] = [[0, [4, 24]], [0, [4, 48]], [0, [16, 52]], [1, [22, 8]], [1, [38, 8]], [2, [56, 24]], [2, [56, 48]], [2, [44, 52]]];
  for (const [c, [x, y]] of f) { atoms.push({ el: "F", x, y }); bonds.push([c, atoms.length - 1]); }
  return { atoms, bonds };
})();

const SF6: Mol = (() => {
  const atoms: Atom[] = [{ el: "S", x: 30, y: 30 }];
  const bonds: [number, number][] = [];
  for (const [x, y] of [[30, 7], [30, 53], [9, 18], [51, 18], [9, 42], [51, 42]] as [number, number][]) { atoms.push({ el: "F", x, y }); bonds.push([0, atoms.length - 1]); }
  return { atoms, bonds };
})();

const MOL: Record<string, Mol> = {
  ...MAJOR,
  "CFC-11": oneC(["Cl", "Cl", "Cl", "F"]), "CFC-12": oneC(["Cl", "Cl", "F", "F"]),
  "CFC-113": twoC(["Cl", "Cl", "F"], ["Cl", "F", "F"]), "CFC-114": twoC(["Cl", "F", "F"], ["Cl", "F", "F"]),
  "HCFC-22": oneC(["H", "Cl", "F", "F"]), "HCFC-141b": twoC(["H", "H", "H"], ["Cl", "Cl", "F"]),
  "HCFC-142b": twoC(["H", "H", "H"], ["Cl", "F", "F"]),
  "HFC-23": oneC(["H", "F", "F", "F"]), "HFC-32": oneC(["H", "H", "F", "F"]), "HFC-125": twoC(["H", "F", "F"], ["F", "F", "F"]),
  "HFC-134a": twoC(["H", "H", "F"], ["F", "F", "F"]), "HFC-143a": twoC(["H", "H", "H"], ["F", "F", "F"]),
  SF6, CF4: oneC(["F", "F", "F", "F"]), C2F6: twoC(["F", "F", "F"], ["F", "F", "F"]), C3F8, CCl4: oneC(["Cl", "Cl", "Cl", "Cl"]),
};

export function moleculeSvg(gas: Gas, size = 44): string {
  const m = MOL[gas];
  if (!m) return "";
  const bonds = m.bonds.map(([a, b]) =>
    `<line x1="${m.atoms[a].x}" y1="${m.atoms[a].y}" x2="${m.atoms[b].x}" y2="${m.atoms[b].y}" stroke="#7a8794" stroke-width="2.6" stroke-linecap="round"/>`).join("");
  const atoms = m.atoms.map((a) =>
    `<circle cx="${a.x}" cy="${a.y}" r="${R[a.el]}" fill="${FILL[a.el]}" stroke="#2b3540" stroke-width="1"/>`).join("");
  return `<svg viewBox="0 0 60 60" width="${size}" height="${size}" aria-hidden="true" focusable="false">${bonds}${atoms}</svg>`;
}
