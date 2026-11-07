import Plotly from "plotly.js-basic-dist-min";
import { annualAnomaly, ecs, runEbm, tcr, withEcs, withOceanMixing, type EbmParams } from "./ebm";

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
const FONT = { family: "Roboto, Segoe UI, sans-serif", color: "#1c2733", size: 14 };
const GRID = "#e8edf3";
const COLOUR: Record<string, string> = { ssp119: "#00a9cf", ssp126: "#003466", ssp245: "#f69320", ssp370: "#df0000", ssp585: "#980002" };
const GROUP_COLOUR: Record<string, string> = {
  "CO₂": "#2b7bd0", "CH₄": "#e8871e", "N₂O": "#2e9e5b", "Halogenated gases": "#9467bd", "Ozone": "#c0566b",
  "Aerosols": "#44546a", "Other human": "#8c6d46", "Natural": "#9aa5b1",
};

interface Scenario {
  label: string; blurb: string; erf_total: number[]; erf_groups: Record<string, number[]>; erf_driving_bounds: number[];
  temperature: number[]; co2_ppm: number[]; toa_imbalance: number[];
}
interface Scenarios {
  years: number[]; params: { c: [number, number, number]; kappa: [number, number, number]; epsilon: number; F4x: number };
  scenarios: Record<string, Scenario>; ar6_2081_2100: Record<string, [number, number, number]>; groups: string[];
}
interface Obs {
  temperature: { source: string; years: number[]; anomaly: number[]; lower: number[]; upper: number[] };
  co2: { source: string; years: number[]; ppm: number[] }; stats: { hadcrut5_2011_2020_vs_1850_1900: number; ar6_assessed_2011_2020_vs_1850_1900: number[] };
}

const get = async <T,>(u: string): Promise<T> => { const r = await fetch(u); if (!r.ok) throw new Error(`${u}: ${r.status}`); return r.json(); };
const mean = (a: number[], years: number[], lo: number, hi: number) => {
  const v = a.filter((_, i) => years[i] >= lo && years[i] <= hi);
  return v.reduce((s, x) => s + x, 0) / v.length;
};

export async function initWarming() {
  const [S, O] = await Promise.all([get<Scenarios>("./data/scenarios.json"), get<Obs>("./data/observations.json")]);
  const base: EbmParams = { C: S.params.c, kappa: S.params.kappa, epsilon: S.params.epsilon, F4x: S.params.F4x, gamma: 2 };
  const defaultEcs = ecs(base);
  let scn = "ssp245";

  const slEcs = $<HTMLInputElement>("w-ecs"), slMix = $<HTMLInputElement>("w-mix");
  slEcs.value = defaultEcs.toFixed(1); slMix.value = "1";
  $("w-scn").innerHTML = Object.entries(S.scenarios).map(([id, s]) =>
    `<button type="button" data-scn="${id}" aria-pressed="${id === scn}" style="--sc:${COLOUR[id]}"><span class="dot"></span>${s.label}</button>`).join("");
  $("w-blurb").textContent = S.scenarios[scn].blurb;

  function model() {
    const p = withOceanMixing(withEcs(base, Number(slEcs.value)), Number(slMix.value));
    const sc = S.scenarios[scn], b = sc.erf_driving_bounds;
    const T = annualAnomaly(runEbm(p, b.slice(1), 1, b[0]), S.years);
    return { p, T, sc };
  }

  function draw() {
    const { p, T, sc } = model();
    const y = S.years;
    $("w-ecs-o").textContent = Number(slEcs.value).toFixed(1);
    $("w-mix-o").textContent = `${Number(slMix.value).toFixed(2)}×`;
    const tcrV = tcr(p);
    $("w-k-ecs").textContent = ecs(p).toFixed(2);
    $("w-k-tcr").textContent = tcrV.toFixed(2);
    const now = mean(T, y, 2011, 2020), end = mean(T, y, 2081, 2100);
    $("w-k-now").textContent = now.toFixed(2);
    $("w-k-end").textContent = end.toFixed(2);
    const ar6 = S.ar6_2081_2100[scn];
    $("w-k-now-l").textContent = `K · 2011–2020 vs 1850–1900 (observed: HadCRUT5 ${O.stats.hadcrut5_2011_2020_vs_1850_1900.toFixed(2)}, AR6 ${O.stats.ar6_assessed_2011_2020_vs_1850_1900[0].toFixed(2)})`;
    $("w-k-end-l").textContent = `K · 2081–2100 vs 1850–1900 (AR6 assessed for ${sc.label}: ${ar6[0]}, very likely ${ar6[1]}–${ar6[2]})`;
    const isDefault = Math.abs(Number(slEcs.value) - defaultEcs) < 0.051 && Number(slMix.value) === 1;
    $("w-note").textContent = isDefault
      ? "The solid line is the reference setting (ECS 3.0 K) and reproduces the FaIR run exactly. Move the sliders to see how the same forcing gives different warming."
      : `Same forcing as the FaIR run, but with ECS ${ecs(p).toFixed(1)} K and ocean mixing ${Number(slMix.value).toFixed(2)}×. Dashed grey is the reference FaIR temperature, for comparison.`;

    const showObs = $<HTMLInputElement>("w-obs").checked, showAr6 = $<HTMLInputElement>("w-ar6").checked;
    const traces: unknown[] = [];
    const xs = y.filter((v) => v >= 1850);
    const off = y.indexOf(1850);
    if (showObs) {
      const ot = O.temperature;
      traces.push({ x: ot.years, y: ot.upper, mode: "lines", line: { width: 0 }, hoverinfo: "skip", showlegend: false },
        { x: ot.years, y: ot.lower, mode: "lines", fill: "tonexty", fillcolor: "rgba(40,40,40,.15)", line: { width: 0 }, hoverinfo: "skip", name: "Observed 95 % range" },
        { x: ot.years, y: ot.anomaly, mode: "lines", line: { color: "#111", width: 2 }, name: "Observed (HadCRUT5)", hovertemplate: "%{x}: %{y:.2f} K<extra>HadCRUT5</extra>" });
    }
    traces.push({ x: xs, y: sc.temperature.slice(off), mode: "lines", line: { color: "#7b8794", width: 2, dash: "dash" }, name: "FaIR, reference setting", hovertemplate: "%{x}: %{y:.2f} K<extra>FaIR</extra>" },
      { x: xs, y: T.slice(off), mode: "lines", line: { color: COLOUR[scn], width: 3.5 }, name: `Your model, ${sc.label}`, hovertemplate: "%{x}: %{y:.2f} K<extra>your model</extra>" });
    if (showAr6) traces.push({ x: [2090], y: [ar6[0]], mode: "markers", marker: { symbol: "diamond", size: 11, color: "#111" },
      error_y: { type: "data", symmetric: false, array: [ar6[2] - ar6[0]], arrayminus: [ar6[0] - ar6[1]], color: "#111", thickness: 2, width: 7 },
      name: "AR6 assessed 2081–2100 (very likely range)", hovertemplate: `AR6 ${sc.label}: ${ar6[0]} K (${ar6[1]}–${ar6[2]})<extra></extra>` });
    const hline = (v: number, t: string) => ({ shape: { type: "line", xref: "paper", yref: "y", x0: 0, x1: 1, y0: v, y1: v, line: { color: "#9aa5b1", width: 1, dash: "dot" } },
      ann: { xref: "paper", x: 0.01, y: v, yref: "y", text: t, showarrow: false, yshift: 10, font: { size: 12, color: "#5b6b7c" } } });
    const refs = [hline(1.5, "1.5 K"), hline(2, "2 K")];
    Plotly.react("w-temp", traces as never[], {
      font: FONT, paper_bgcolor: "#fff", plot_bgcolor: "#fff", margin: { t: 10, r: 20, b: 55, l: 70 },
      legend: { orientation: "h", y: 1.12 }, shapes: refs.map((r) => r.shape), annotations: refs.map((r) => r.ann),
      xaxis: { range: [1850, 2100], gridcolor: GRID, title: { text: "Year" } },
      yaxis: { title: { text: "Warming since 1850–1900 (K)" }, gridcolor: GRID, zeroline: true, zerolinecolor: "#44505c" },
    } as never, { responsive: true, displaylogo: false } as never);

    // forcing by agent
    const ft: unknown[] = S.groups.map((g) => ({ x: xs, y: sc.erf_groups[g].slice(off), mode: "lines", name: g, line: { color: GROUP_COLOUR[g], width: 2 },
      hovertemplate: `${g}: %{y:.2f} W m⁻²<extra>%{x}</extra>` }));
    ft.push({ x: xs, y: sc.erf_total.slice(off), mode: "lines", name: "Total", line: { color: "#111", width: 4 }, hovertemplate: "Total: %{y:.2f} W m⁻²<extra>%{x}</extra>" });
    Plotly.react("w-erf", ft as never[], {
      font: FONT, paper_bgcolor: "#fff", plot_bgcolor: "#fff", margin: { t: 10, r: 20, b: 55, l: 70 }, legend: { orientation: "h", y: 1.2 },
      xaxis: { range: [1850, 2100], gridcolor: GRID, title: { text: "Year" } },
      yaxis: { title: { text: "Effective radiative forcing (W m⁻²)" }, gridcolor: GRID, zeroline: true, zerolinecolor: "#44505c" },
    } as never, { responsive: true, displaylogo: false } as never);

    // CO2
    const ct: unknown[] = Object.entries(S.scenarios).filter(([id]) => id !== scn).map(([id, s]) => ({
      x: y, y: s.co2_ppm, mode: "lines", name: s.label, line: { color: COLOUR[id], width: 1.2 }, opacity: 0.35, hovertemplate: `${s.label}: %{y:.0f} ppm<extra>%{x}</extra>` }));
    ct.push({ x: y, y: sc.co2_ppm, mode: "lines", name: sc.label, line: { color: COLOUR[scn], width: 3.5 }, hovertemplate: `${sc.label}: %{y:.0f} ppm<extra>%{x}</extra>` },
      { x: O.co2.years, y: O.co2.ppm, mode: "markers", name: "Observed (Mauna Loa)", marker: { color: "#111", size: 5 }, hovertemplate: "%{x}: %{y:.1f} ppm<extra>Mauna Loa</extra>" });
    Plotly.react("w-co2", ct as never[], {
      font: FONT, paper_bgcolor: "#fff", plot_bgcolor: "#fff", margin: { t: 10, r: 20, b: 55, l: 70 }, legend: { orientation: "h", y: 1.2 },
      xaxis: { range: [1900, 2100], gridcolor: GRID, title: { text: "Year" } }, yaxis: { title: { text: "CO₂ concentration (ppm)" }, gridcolor: GRID },
    } as never, { responsive: true, displaylogo: false } as never);
  }

  $("w-scn").addEventListener("click", (e) => {
    const b = (e.target as HTMLElement).closest("button[data-scn]") as HTMLButtonElement | null;
    if (!b) return;
    scn = b.dataset.scn!;
    $("w-scn").querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    $("w-blurb").textContent = S.scenarios[scn].blurb;
    draw();
  });
  slEcs.addEventListener("input", draw); slMix.addEventListener("input", draw);
  $("w-obs").addEventListener("change", draw); $("w-ar6").addEventListener("change", draw);
  $("w-reset").addEventListener("click", () => { slEcs.value = defaultEcs.toFixed(1); slMix.value = "1"; draw(); });
  draw();
}
