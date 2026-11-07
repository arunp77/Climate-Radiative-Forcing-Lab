import Plotly from "plotly.js-basic-dist-min";
import { co2Forcing, ch4Forcing, n2oForcing, PI } from "./forcing";
import { moleculeSvg } from "./molecules";
import { flux } from "./planck";
import {
  binNu, columnAt, diffMilli, entryIrf, entryOlr, entrySpec, formatColumn, formatMultiple, haloSpec, linearForcing,
  nearestEntry, transmission, wavelengthUm,
  type Gas, type GasMeta, type HaloData, type LabData, type OlrData, type Sky,
} from "./spectraData";

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
type Axis = "nu" | "um";
interface Mark { nu: number; label: string; colour: string }

const WINDOW_NU: [number, number] = [800, 1250]; // about 8-12.5 um: the atmospheric window
const LAYOUT_BASE = {
  paper_bgcolor: "#fff", plot_bgcolor: "#fff", font: { family: "Roboto, Segoe UI, sans-serif", color: "#1c2733", size: 14 },
  margin: { t: 24, r: 20, b: 65, l: 105 },
};
const GRID = "#e8edf3";

const xAxisFor = (axis: Axis, kind: "lab" | "earth") =>
  axis === "nu"
    ? { title: { text: "Wavenumber (cm⁻¹)" }, range: kind === "lab" ? [1800, 500] : [1800, 100], gridcolor: GRID }
    : { title: { text: "Wavelength (µm)" }, range: kind === "lab" ? [Math.log10(5.5), Math.log10(20)] : [Math.log10(5.5), Math.log10(60)], type: "log", gridcolor: GRID };

const xs = (nus: number[], axis: Axis) => (axis === "nu" ? nus : nus.map(wavelengthUm));

function windowShape(axis: Axis) {
  const [a, b] = axis === "nu" ? WINDOW_NU : [wavelengthUm(WINDOW_NU[1]), wavelengthUm(WINDOW_NU[0])];
  return { type: "rect", xref: "x", yref: "paper", x0: a, x1: b, y0: 0, y1: 1, fillcolor: "rgba(250,204,21,.16)", line: { width: 0 }, layer: "below" };
}

function bandMarks(marks: Mark[], axis: Axis) {
  const shapes: unknown[] = [], annotations: unknown[] = [];
  marks.forEach((b) => {
    const x = axis === "nu" ? b.nu : wavelengthUm(b.nu);
    shapes.push({ type: "line", xref: "x", yref: "paper", x0: x, x1: x, y0: 0, y1: 1, line: { color: b.colour, width: 1, dash: "dot" }, layer: "below" });
    annotations.push({ x, y: 1, yref: "paper", text: b.label, textangle: -90, showarrow: false, xanchor: "left", yanchor: "top", font: { size: 13, color: b.colour }, yshift: -4 });
  });
  return { shapes, annotations };
}

async function getJson<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json();
}

const GROUP_ORDER = ["Major gases", "CFCs", "HCFCs", "HFCs", "PFCs and SF₆", "Other"];

export async function initSpectra() {
  const meta = await getJson<Record<Gas, GasMeta>>("./data/spectra/gases.json");
  const ids = Object.keys(meta);
  const labCache = new Map<Gas, LabData>();
  let olr: OlrData | null = null;
  let halo: HaloData | null = null;

  const setMode = (m: "lab" | "earth") => {
    $("sp-mode-lab").setAttribute("aria-pressed", String(m === "lab"));
    $("sp-mode-earth").setAttribute("aria-pressed", String(m === "earth"));
    $("sp-lab").hidden = m !== "lab"; $("sp-earth").hidden = m !== "earth";
    window.dispatchEvent(new Event("resize"));
    if (m === "earth") void earth.ensure();
  };
  $("sp-mode-lab").addEventListener("click", () => setMode("lab"));
  $("sp-mode-earth").addEventListener("click", () => setMode("earth"));

  // ------------------------------------------------------------------ lab-cell view
  const sel = new Set<Gas>(["CO2"]);
  let amt = 12;                          // 10^21 molecules cm-2
  let cond = "surface";
  let axis: Axis = "nu";

  $("sp-gases").innerHTML = GROUP_ORDER.map((grp) => {
    const members = ids.filter((g) => meta[g].group === grp);
    if (!members.length) return "";
    const small = grp !== "Major gases" ? " sm" : "";
    return `<div class="gasgroup"><h4>${grp}</h4><div class="row">` + members.map((g) =>
      `<button class="gasbtn${small}" data-gas="${g}" aria-pressed="${sel.has(g)}" style="--gc:${meta[g].colour}" title="${meta[g].name}">
         ${moleculeSvg(g, small ? 38 : 44)}<span class="nm">${meta[g].html}</span></button>`).join("") + `</div></div>`;
  }).join("");
  $("sp-gases").querySelectorAll<HTMLButtonElement>(".gasbtn").forEach((b) => b.addEventListener("click", async () => {
    const g = b.dataset.gas as Gas;
    if (sel.has(g)) sel.delete(g); else sel.add(g);
    b.setAttribute("aria-pressed", String(sel.has(g)));
    await drawLab();
  }));

  async function lab(g: Gas): Promise<LabData> {
    if (!labCache.has(g)) labCache.set(g, await getJson<LabData>(`./data/spectra/lab_${g}.json`));
    return labCache.get(g)!;
  }

  async function drawLab() {
    const gases = ids.filter((g) => sel.has(g));
    const data = await Promise.all(gases.map(lab));
    const condSel = $<HTMLSelectElement>("sp-cond");
    if (data.length && !condSel.options.length)
      for (const [k, v] of Object.entries(data[0].conditions)) condSel.add(new Option(v.label, k));
    const cols = (data[0] ?? labCache.values().next().value)?.log10_columns ?? [];
    const k = Math.min(amt, cols.length - 1);
    $("sp-amt-o").textContent = cols.length ? `${formatColumn(10 ** cols[k])} molecules cm⁻²` : "";
    const traces = data.map((d) => {
      const nus = d.t[cond][0].map((_, i) => binNu(i, d.nu_start, d.dnu));
      return { type: "scatter", mode: "lines", name: meta[d.gas].html, x: xs(nus, axis), y: transmission(d, cond, k), connectgaps: false,
        line: { color: meta[d.gas].colour, width: 1.4 }, hovertemplate: `${meta[d.gas].html}<br>%{x:.1f}<br>T = %{y:.3f}<extra></extra>` };
    });
    const marks = bandMarks($<HTMLInputElement>("sp-bands").checked
      ? gases.flatMap((g) => meta[g].bands.map((b) => ({ ...b, colour: meta[g].colour }))) : [], axis);
    const shapes = [...($<HTMLInputElement>("sp-win").checked ? [windowShape(axis)] : []), ...marks.shapes];
    await Plotly.react("sp-lab-chart", traces as never[], {
      ...LAYOUT_BASE, showlegend: data.length > 1, legend: { orientation: "h", y: 1.08 }, shapes, annotations: marks.annotations,
      xaxis: xAxisFor(axis, "lab"), yaxis: { title: { text: "Transmission" }, range: [0, 1.04], gridcolor: GRID },
    } as never, { responsive: true, displaylogo: false });
    $("sp-lab-info").innerHTML = data.length
      ? data.map((d) => {
        const m = meta[d.gas];
        const ratio = columnAt(d, k) / d.n_atm;
        const cov = m.source === "xsec" ? ` Measured range ${m.coverage.map(([a, b]) => `${a.toFixed(0)}–${b.toFixed(0)}`).join(", ")} cm⁻¹ (no line is drawn outside it).` : "";
        return `<strong>${m.html}</strong>: ${formatMultiple(ratio)} the atmospheric column (${formatColumn(d.n_atm)}).${cov}`;
      }).join("<br>") + `<br>Conditions: ${data[0].conditions[cond]?.label ?? ""}. Each point is a 1 cm⁻¹ average of the transmission.`
      : "Click a molecule above to show its absorption.";
  }
  $<HTMLInputElement>("sp-amt").addEventListener("input", (e) => { amt = Number((e.target as HTMLInputElement).value); void drawLab(); });
  $<HTMLInputElement>("sp-amt").value = String(amt);
  $<HTMLSelectElement>("sp-cond").addEventListener("change", (e) => { cond = (e.target as HTMLSelectElement).value; void drawLab(); });
  $<HTMLSelectElement>("sp-axis").addEventListener("change", (e) => { axis = (e.target as HTMLSelectElement).value as Axis; void drawLab(); });
  $("sp-bands").addEventListener("change", () => void drawLab());
  $("sp-win").addEventListener("change", () => void drawLab());

  // ------------------------------------------------------------------ Earth's outgoing spectrum
  let egas: Gas = "CO2";
  let eidx = 0;
  let eaxis: Axis = "nu";
  let sky: Sky = "all";
  let special = false;

  const isHalo = (g: Gas) => meta[g].source === "xsec";
  const entriesOf = (g: Gas) => (isHalo(g) ? halo!.gases[g].entries : olr!.sweeps[g].entries);

  const earth = {
    async ensure() {
      if (!olr) {
        olr = await getJson<OlrData>("./data/spectra/olr.json");
        const s2 = $<HTMLSelectElement>("sp-egas");
        for (const grp of GROUP_ORDER) {
          const og = document.createElement("optgroup"); og.label = grp;
          for (const g of ids.filter((x) => meta[x].group === grp)) og.appendChild(new Option(`${meta[g].name} (${meta[g].html})`, g));
          if (og.children.length) s2.appendChild(og);
        }
        s2.value = egas;
        this.setGas(egas, nearestEntry(olr.sweeps[egas].entries, PI.CO2));
      }
      await this.draw();
    },
    async setGas(g: Gas, idx: number) {
      egas = g;
      if (isHalo(g) && !halo) halo = await getJson<HaloData>("./data/spectra/olr_halo.json");
      const n = entriesOf(g).length;
      const s = $<HTMLInputElement>("sp-eval");
      s.max = String(n - 1); eidx = Math.min(idx, n - 1); s.value = String(eidx);
    },
    amountLabel(): string {
      if (special) return "2019 gases (all three)";
      const e = entriesOf(egas)[eidx];
      if (!isHalo(egas)) return `${e.value} ${olr!.sweeps[egas].unit}`;
      const c2019 = meta[egas].c2019_ppt!;
      const r = e.value / c2019;
      const amount = e.value >= 1000 ? `${(e.value / 1000).toPrecision(3)} ppb` : `${e.value < 10 ? e.value.toFixed(2) : e.value.toFixed(0)} ppt`;
      return eidx === 0 ? `${e.value.toFixed(1)} ppt (1750 level)` : `${amount} (${formatMultiple(r)} the 2019 level)`;
    },
    async draw() {
      if (!olr) return;
      if (isHalo(egas) && !halo) halo = await getJson<HaloData>("./data/spectra/olr_halo.json");
      const nus = olr.baseline.spec.map((_, i) => binNu(i, olr!.nu_start, olr!.dnu));
      const x = xs(nus, eaxis);
      const base = sky === "all" ? olr.baseline.spec_all : olr.baseline.spec;
      let spec: number[], olrVal: number, irfVal: number, label: string;
      if (special) {
        spec = entrySpec(olr.all_2019, sky); olrVal = entryOlr(olr.all_2019, sky); irfVal = entryIrf(olr.all_2019, sky);
        label = "2019: CO₂ 409.9 ppm, CH₄ 1866 ppb, N₂O 332 ppb";
      } else if (isHalo(egas)) {
        const e = halo!.gases[egas].entries[eidx];
        spec = haloSpec(base, e, sky); olrVal = entryOlr(e, sky); irfVal = entryIrf(e, sky); label = `${meta[egas].html} ${this.amountLabel()}`;
      } else {
        const e = olr.sweeps[egas].entries[eidx];
        spec = entrySpec(e, sky); olrVal = entryOlr(e, sky); irfVal = entryIrf(e, sky); label = `${meta[egas].html} = ${this.amountLabel()}`;
      }
      $("sp-eval-o").textContent = this.amountLabel();
      $("sp-olr").textContent = olrVal.toFixed(1);
      $("sp-olr-l").textContent = `W m⁻² · outgoing longwave radiation (${sky === "all" ? "all-sky estimate" : "clear sky"})`;
      $("sp-irf").textContent = (irfVal >= 0 ? "+" : "") + irfVal.toFixed(irfVal !== 0 && Math.abs(irfVal) < 0.1 ? 3 : 2);
      $("sp-sky-clear").setAttribute("aria-pressed", String(sky === "clear")); $("sp-sky-all").setAttribute("aria-pressed", String(sky === "all"));
      const c = olr.cloud;
      $("sp-sky-note").textContent = sky === "all"
        ? `All-sky estimate: grey cloud deck (cover ${c.cover}, ${c.deck_km[0]}–${c.deck_km[1]} km, opacity τ = ${c.tau_c.toFixed(2)}) tuned so the longwave cloud effect is ${c.target_lw_cre} W m⁻² (CERES). Model clear/all-sky OLR: ${c.model_clear_olr.toFixed(0)}/${c.model_allsky_olr.toFixed(0)} W m⁻² (observed ${c.ceres_clear_olr}/${c.ceres_allsky_olr}).`
        : "Clear sky: no clouds." + (isHalo(egas) && halo
          ? ` For ${meta[egas].html} the clear-sky radiative efficiency is ${(halo.gases[egas].re_clear / halo.gases[egas].re_all).toFixed(2)}× the all-sky estimate: clouds block part of the surface radiation these window absorbers act on.`
          : "");

      const marks = bandMarks($<HTMLInputElement>("sp-ebands").checked ? meta[egas].bands.map((b) => ({ ...b, colour: meta[egas].colour })) : [], eaxis);
      const shapes = [...($<HTMLInputElement>("sp-ewin").checked ? [windowShape(eaxis)] : []), ...marks.shapes];
      const traces = [
        { type: "scatter", mode: "lines", x, y: nus.map((n) => flux(n, olr!.T_surface)), name: "Blackbody 288 K", line: { color: "#98a4b0", width: 1.2, dash: "dash" }, hoverinfo: "skip" },
        { type: "scatter", mode: "lines", x, y: nus.map((n) => flux(n, 220)), name: "Blackbody 220 K", line: { color: "#b9c2cc", width: 1.2, dash: "dot" }, hoverinfo: "skip" },
        { type: "scatter", mode: "lines", x, y: base, name: "1750 atmosphere", fill: "tozeroy", fillcolor: "rgba(120,130,140,.16)", line: { color: "#7a8794", width: 1 }, hoverinfo: "skip" },
        { type: "scatter", mode: "lines", x, y: spec, name: label, line: { color: meta[egas].colour, width: 1.6 }, hovertemplate: "%{x:.1f}<br>%{y:.4f} W m⁻² per cm⁻¹<extra></extra>" },
      ];
      void Plotly.react("sp-earth-chart", traces as never[], {
        ...LAYOUT_BASE, showlegend: true, legend: { orientation: "h", y: 1.12 }, shapes, annotations: marks.annotations,
        xaxis: xAxisFor(eaxis, "earth"), yaxis: { title: { text: "Flux (W m⁻² per cm⁻¹)" }, rangemode: "tozero", gridcolor: GRID },
      } as never, { responsive: true, displaylogo: false });

      void Plotly.react("sp-diff-chart", [
        { type: "scatter", mode: "lines", x, y: diffMilli(spec, base), name: label, line: { color: meta[egas].colour, width: 1.4 }, fill: "tozeroy",
          fillcolor: "rgba(0,0,0,.05)", hovertemplate: "%{x:.1f}<br>%{y:.3f} mW m⁻² per cm⁻¹<extra></extra>" },
      ] as never[], {
        ...LAYOUT_BASE, showlegend: false, shapes: ($<HTMLInputElement>("sp-ewin").checked ? [windowShape(eaxis)] : []),
        xaxis: xAxisFor(eaxis, "earth"), yaxis: { title: { text: "Change in outgoing flux (mW m⁻² per cm⁻¹)" }, gridcolor: GRID, zeroline: true, zerolinecolor: "#44505c" },
      } as never, { responsive: true, displaylogo: false });
      this.drawGrowth(special ? null : eidx);
    },
    drawGrowth(idx: number | null) {
      const entries = entriesOf(egas);
      const m = meta[egas];
      const halos = isHalo(egas);
      const c1750 = halos ? m.c1750_ppt! : 0;
      const pos = entries.filter((en) => en.value > 0 && (!halos || en.value > c1750));
      const unit = halos ? "ppt" : olr!.sweeps[egas].unit;
      const traces: unknown[] = [{
        type: "scatter", mode: "lines+markers", name: `Line-by-line forcing (${sky === "all" ? "all-sky estimate" : "clear sky"})`,
        x: pos.map((en) => en.value), y: pos.map((en) => entryIrf(en, sky)), line: { color: m.colour, width: 2 }, marker: { size: 7 },
        hovertemplate: "%{x}: %{y:.3f} W m⁻²<extra>this model</extra>",
      }];
      const lo = Math.min(...pos.map((p) => p.value)), hi = Math.max(...pos.map((p) => p.value));
      const grid = Array.from({ length: 80 }, (_, i) => lo * (hi / lo) ** (i / 79));
      let formula: number[] | null = null, fname = "";
      if (halos) { formula = grid.map((c) => linearForcing(m.ar6_re!, c - c1750)); fname = "AR6 straight line (radiative efficiency × amount)"; }
      else if (egas === "CO2") { formula = grid.map((c) => co2Forcing(c, PI.N2O, "meinshausen2020", false)); fname = "AR6 equation (all-sky, stratosphere-adjusted)"; }
      else if (egas === "CH4") { formula = grid.map((v) => ch4Forcing(v, PI.N2O, "meinshausen2020", false)); fname = "AR6 equation (all-sky, stratosphere-adjusted)"; }
      else if (egas === "N2O") { formula = grid.map((v) => n2oForcing(v, PI.CO2, PI.CH4, "meinshausen2020", false)); fname = "AR6 equation (all-sky, stratosphere-adjusted)"; }
      if (formula) traces.push({ type: "scatter", mode: "lines", name: fname, x: grid, y: formula, line: { color: "#44505c", width: 1.5, dash: "dash" }, hoverinfo: "skip" });
      if (idx !== null && entries[idx].value > 0 && (!halos || entries[idx].value > c1750))
        traces.push({ type: "scatter", mode: "markers", name: "Selected", x: [entries[idx].value], y: [entryIrf(entries[idx], sky)], marker: { size: 13, color: "#111", symbol: "diamond" }, hoverinfo: "skip" });
      void Plotly.react("sp-growth-chart", traces as never[], {
        ...LAYOUT_BASE, showlegend: true, legend: { orientation: "h", y: 1.18 },
        xaxis: { title: { text: `${m.html} (${unit})` }, type: "log", gridcolor: GRID },
        yaxis: { title: { text: "Forcing vs 1750 (W m⁻²)" }, gridcolor: GRID, zeroline: true, ...(halos ? { type: "log" } : {}) },
      } as never, { responsive: true, displaylogo: false });

      $("sp-re-note").textContent = halos
        ? `Radiative efficiency of ${m.html}: this model ${halo!.gases[egas].re_all.toFixed(3)} (all-sky estimate) or ${halo!.gases[egas].re_clear.toFixed(3)} (clear sky) W m⁻² ppb⁻¹; AR6 Table 7.SM.7: ${m.ar6_re!.toFixed(3)} (all-sky, stratosphere-adjusted). Ratio all-sky/AR6 = ${(halo!.gases[egas].re_all / m.ar6_re!).toFixed(2)}.`
        : "";
      if (halos) {
        const e = entries as { value: number; irf: number; irf_all: number }[];
        const last = e[e.length - 1], f0 = entryIrf(e[0], sky), f1 = entryIrf(e[1], sky);
        const added = (k: number) => e[k].value - e[0].value;
        const frac = (entryIrf(last, sky) - f0) / (f1 - f0) / (added(e.length - 1) / added(1));
        const mult = Math.round(last.value / m.c2019_ppt!);
        $("sp-growth-note").textContent =
          `At today's tiny amounts halocarbons are in the weak-absorption limit: forcing grows in direct proportion to the amount (the dashed line). How soon the curve bends depends on how abundant the gas already is: at ${mult}× today's level ${m.html} delivers ${(100 * frac).toFixed(0)}% of the straight-line forcing. Abundant gases such as CFC-12 saturate first; rare ones such as C₃F₈ stay close to linear.`;
      } else if (egas === "CO2") {
        const f2 = olr!.sweeps.CO2.entries;
        const e2 = (v: number) => entryIrf(f2[nearestEntry(f2, v)], sky);
        $("sp-growth-note").textContent =
          `CO₂: doubling from 278 to 557 ppm adds ${(e2(556.6) - e2(278.3)).toFixed(2)} W m⁻² and the next doubling adds ${(e2(1113.2) - e2(556.6)).toFixed(2)} W m⁻²: equal steps per doubling, a logarithmic law that emerges from the line physics. This is the instantaneous top-of-atmosphere forcing; AR6's equation gives the effective forcing after the stratosphere has adjusted, so the two differ by tens of percent but share the same shape.`;
      } else if (egas === "CH4" || egas === "N2O") {
        $("sp-growth-note").textContent =
          `${m.html}: forcing grows roughly as the square root of the concentration because the band centres are partly saturated while the wings are not. The dashed AR6 curve is the all-sky, stratosphere-adjusted equation; the line-by-line values are clear-sky or all-sky top-of-atmosphere forcing, so the two differ in size but not in shape.`;
      } else {
        $("sp-growth-note").textContent =
          `${m.html}: the amount is scaled uniformly through the atmosphere, with no feedbacks (for water vapour this is a prescribed change, not the response to warming).`;
      }
    },
  };

  $<HTMLSelectElement>("sp-egas").addEventListener("change", async (e) => {
    special = false; await earth.setGas((e.target as HTMLSelectElement).value as Gas, isHalo((e.target as HTMLSelectElement).value) ? 2 : 0); await earth.draw();
  });
  $<HTMLInputElement>("sp-eval").addEventListener("input", (e) => { special = false; eidx = Number((e.target as HTMLInputElement).value); void earth.draw(); });
  $("sp-e1750").addEventListener("click", async () => {
    special = false;
    await earth.setGas(egas, isHalo(egas) ? 0 : nearestEntry(olr!.sweeps[egas].entries, olr!.baseline.gases[egas])); await earth.draw();
  });
  $("sp-e2019").addEventListener("click", () => { special = true; void earth.draw(); });
  $("sp-e2x").addEventListener("click", async () => {
    special = false; $<HTMLSelectElement>("sp-egas").value = "CO2"; await earth.setGas("CO2", nearestEntry(olr!.sweeps.CO2.entries, 2 * PI.CO2)); await earth.draw();
  });
  $("sp-sky-clear").addEventListener("click", () => { sky = "clear"; void earth.draw(); });
  $("sp-sky-all").addEventListener("click", () => { sky = "all"; void earth.draw(); });
  $<HTMLSelectElement>("sp-eaxis").addEventListener("change", (e) => { eaxis = (e.target as HTMLSelectElement).value as Axis; void earth.draw(); });
  $("sp-ebands").addEventListener("change", () => void earth.draw());
  $("sp-ewin").addEventListener("change", () => void earth.draw());

  await drawLab();
}
