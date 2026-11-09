import { CATEGORIES, TERMS, type Category } from "./glossary";
import { moleculeSvg } from "./molecules";

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

const SUB: Record<string, string> = { "0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉" };
export const sub = (s: string) => s.replace(/\d/g, (d) => SUB[d]);

interface Row { id: string; formula: string; family: string; uses: string; key: string }
const ROWS: Row[] = [
  { id: "H2O", formula: "H2O", family: "Natural", uses: "The strongest natural greenhouse gas; its amount is set by temperature, so it amplifies other forcing", key: "H2O" },
  { id: "CO2", formula: "CO2", family: "Major gases", uses: "Fossil fuels, cement and deforestation", key: "CO2" },
  { id: "CH4", formula: "CH4", family: "Major gases", uses: "Livestock, rice, wetlands, landfills and fossil-fuel leaks", key: "CH4" },
  { id: "N2O", formula: "N2O", family: "Major gases", uses: "Fertiliser use, agriculture and industry", key: "N2O" },
  { id: "O3", formula: "O3", family: "Major gases", uses: "Made by chemistry in the air; absorbs ultraviolet light in the stratosphere", key: "O3" },
  { id: "CFC-11", formula: "CCl3F", family: "CFC", uses: "Foam blowing and refrigeration; production banned", key: "CFC-11" },
  { id: "CFC-12", formula: "CCl2F2", family: "CFC", uses: "Refrigeration, air conditioning and aerosol propellant; production banned", key: "CFC-12" },
  { id: "CFC-113", formula: "C2Cl3F3", family: "CFC", uses: "Solvent for electronics and metal cleaning; production banned", key: "CFC-113" },
  { id: "CFC-114", formula: "C2Cl2F4", family: "CFC", uses: "Refrigerant and propellant; production banned", key: "CFC-114" },
  { id: "HCFC-22", formula: "CHClF2", family: "HCFC", uses: "Refrigerant and air conditioning (R-22); being phased out", key: "HCFC-22" },
  { id: "HCFC-141b", formula: "CH3CCl2F", family: "HCFC", uses: "Foam-blowing agent and solvent; being phased out", key: "HCFC-141b" },
  { id: "HCFC-142b", formula: "CH3CClF2", family: "HCFC", uses: "Foam-blowing agent and refrigerant blend component; being phased out", key: "HCFC-142b" },
  { id: "HFC-23", formula: "CHF3", family: "HFC", uses: "By-product of HCFC-22 manufacture; fire suppression and semiconductor etching", key: "HFC-23" },
  { id: "HFC-32", formula: "CH2F2", family: "HFC", uses: "Refrigerant (R-32) and a component of R-410A", key: "HFC-32" },
  { id: "HFC-125", formula: "CHF2CF3", family: "HFC", uses: "Component of the R-410A and R-404A refrigerant blends", key: "HFC-125" },
  { id: "HFC-134a", formula: "CH2FCF3", family: "HFC", uses: "Car air conditioning and refrigeration (R-134a)", key: "HFC-134a" },
  { id: "HFC-143a", formula: "CH3CF3", family: "HFC", uses: "Component of the R-404A and R-507 refrigerant blends", key: "HFC-143a" },
  { id: "SF6", formula: "SF6", family: "SF₆", uses: "Electrical insulation in high-voltage switchgear", key: "SF6" },
  { id: "CF4", formula: "CF4", family: "PFC", uses: "By-product of aluminium smelting; semiconductor etching (PFC-14)", key: "PFC-14" },
  { id: "C2F6", formula: "C2F6", family: "PFC", uses: "Aluminium-smelting by-product; semiconductor cleaning and etching (PFC-116)", key: "PFC-116" },
  { id: "C3F8", formula: "C3F8", family: "PFC", uses: "Semiconductor manufacturing (PFC-218)", key: "PFC-218" },
  { id: "CCl4", formula: "CCl4", family: "Other", uses: "Solvent and chemical feedstock; controlled by the Montreal Protocol", key: "Carbon tetrachloride" },
];

interface Species { acronym: string; formula: string; name: string; lifetime: number | null; re: number | null; ar6: { GWP100?: number | null } }

/** Decode a CFC/HCFC/HFC/PFC number with the "rule of 90". Returns null when the number cannot be a saturated halocarbon. */
export function decodeRule90(n: number): { C: number; H: number; F: number; Cl: number; formula: string; family: string } | null {
  if (!Number.isInteger(n) || n < 1 || n > 999) return null;
  const t = n + 90;
  const C = Math.floor(t / 100), H = Math.floor((t % 100) / 10), F = t % 10;
  if (C < 1) return null;
  const Cl = 2 * C + 2 - H - F;                          // every other bond on a saturated chain holds chlorine
  if (Cl < 0) return null;
  const part = (el: string, k: number) => (k === 0 ? "" : k === 1 ? el : el + sub(String(k)));
  const formula = part("C", C) + part("H", H) + part("Cl", Cl) + part("F", F);
  const family = Cl > 0 ? (H > 0 ? "HCFC" : "CFC") : H > 0 ? "HFC" : "PFC";
  return { C, H, F, Cl, formula, family };
}

function fmtLife(x: number | null): string {
  if (x == null) return "no single value";
  return x >= 1000 ? `${Math.round(x).toLocaleString("en")} yr` : `${x} yr`;
}

export async function initGlossary() {
  const mres = await fetch("./data/metrics.json").then((r) => r.json()).catch(() => null);
  const species: Species[] = mres?.species ?? [];
  const find = (key: string) => species.find((s) => s.acronym === key) ?? species.find((s) => s.formula === key.replace(/[^A-Za-z0-9]/g, "")) ?? species.find((s) => s.formula === key);

  // molecule table
  $("gl-mols").innerHTML = ROWS.map((r) => {
    const s = find(r.key);
    const gwp = s?.ar6?.GWP100;
    return `<tr><td class="ico">${moleculeSvg(r.id as never, 34)}</td><th scope="row">${r.id}</th><td>${sub(r.formula)}</td><td>${r.family}</td>` +
      `<td>${fmtLife(s?.lifetime ?? null)}</td><td>${s?.re != null ? s.re.toPrecision(3) : "–"}</td><td>${gwp != null ? Math.round(gwp).toLocaleString("en") : "–"}</td><td class="uses">${r.uses}</td></tr>`;
  }).join("");

  // name decoder
  const inp = $<HTMLInputElement>("gl-code"), out = $("gl-decoded");
  const update = () => {
    const m = /^\s*(\d{1,3})\s*[a-z]?\s*$/i.exec(inp.value);
    const d = m ? decodeRule90(Number(m[1])) : null;
    out.innerHTML = d
      ? `<strong>${d.family}-${m![1]}</strong> adds up to ${Number(m![1]) + 90}: <b>${d.C}</b> carbon, <b>${d.H}</b> hydrogen, <b>${d.F}</b> fluorine, and the remaining bonds hold <b>${d.Cl}</b> chlorine. Formula: <strong>${d.formula}</strong> (${d.family}).`
      : `Enter the number of a CFC, HCFC, HFC or PFC, for example 11, 22, 134 or 218.`;
  };
  inp.addEventListener("input", update);
  update();

  // terms with search and category filter
  let cat: Category | "All" = "All";
  const chips = $("gl-cats"), list = $("gl-terms"), q = $<HTMLInputElement>("gl-search"), count = $("gl-count");
  chips.innerHTML = ["All", ...CATEGORIES].map((c) => `<button type="button" data-cat="${c}" aria-pressed="${c === "All"}">${c}</button>`).join("");
  const draw = () => {
    const needle = q.value.trim().toLowerCase();
    const hits = TERMS.filter((t) => (cat === "All" || t.cat === cat) && (!needle || (t.term + " " + t.def).toLowerCase().includes(needle)))
      .sort((a, b) => a.term.localeCompare(b.term, "en"));
    count.textContent = `${hits.length} of ${TERMS.length} terms`;
    list.innerHTML = hits.length
      ? hits.map((t) => `<div class="term"><dt>${t.term}<span class="tag">${t.cat}</span></dt><dd>${t.def}</dd></div>`).join("")
      : `<p class="note">No term matches. Try a shorter word.</p>`;
  };
  chips.addEventListener("click", (e) => {
    const b = (e.target as HTMLElement).closest("button[data-cat]") as HTMLButtonElement | null;
    if (!b) return;
    cat = b.dataset.cat as Category | "All";
    chips.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    draw();
  });
  q.addEventListener("input", draw);
  draw();
}

/** Fill every "Key terms on this tab" box from the glossary, so each definition has a single source. */
export function renderTermBoxes(root: ParentNode = document) {
  const byName = new Map(TERMS.map((t) => [t.term, t]));
  root.querySelectorAll<HTMLElement>("details.termsbox[data-terms]").forEach((box) => {
    const names = (box.dataset.terms ?? "").split("|");
    const dl = box.querySelector("dl")!;
    dl.innerHTML = names.map((n) => {
      const t = byName.get(n);
      return t ? `<div class="term"><dt>${t.term}</dt><dd>${t.def}</dd></div>` : "";
    }).join("");
  });
}
