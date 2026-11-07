import Plotly from "plotly.js-basic-dist-min";
import { wmghg, PI, type Scheme } from "./forcing";
import { COLOURS } from "./agents";
import { renderEquations, renderTex, EQ_LAMBDA, NONGHG_TEX, NONGHG_NOTE } from "./equations";
import { initHistory } from "./historyView";
import type { History } from "./history";
import { nonGhgErf, type NonGhgParams, type DriverState } from "./nonghg";
import { ALL_DRIVERS, GROUPS } from "./drivers";
import { initSpectra } from "./spectraView";
import { initGlossary } from "./glossaryView";
import { initWarming } from "./warmView";
import { initAdjust } from "./adjustView";
import { initAbout } from "./aboutView";
import { initMetrics } from "./metricsView";

interface Component { id: string; label: string; best: number; low: number; high: number }
interface Balance {
  year: number;
  concentrations: { CO2: number; CH4: number; N2O: number };
  components: Component[];
  series: { years: number[]; total_anthropogenic: number[]; total_anthropogenic_low: number[];
            total_anthropogenic_high: number[] };
  history: History;
  nonghg: NonGhgParams;
  preindustrial_state: Record<string, number>;
}

const LAMBDA = 3.93 / 3; // W m-2 K-1: F_2x / ECS (AR6 central values) -> EQUILIBRIUM response
const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

let B: Balance;
interface State { c: number; m: number; n: number; s: Scheme; d: Record<string, number> } // d: driver percentages of 2019
const defaultD = () => Object.fromEntries(ALL_DRIVERS.map((x) => [x.key, 100]));
const defaults = (): State => ({ c: B.concentrations.CO2, m: B.concentrations.CH4, n: B.concentrations.N2O, s: "meinshausen2020", d: defaultD() });
let st: State = { c: 0, m: 0, n: 0, s: "meinshausen2020", d: {} };

const fmt = (x: number, d = 2) => x.toFixed(d);

function readURL() {
  const q = new URLSearchParams(location.search);
  const num = (k: string, lo: number, hi: number, dflt: number) => {
    const v = Number(q.get(k));
    return q.has(k) && Number.isFinite(v) && v >= lo && v <= hi ? v : dflt;
  };
  const d = defaults();
  const s = q.get("s");
  st = {
    c: num("c", 180, 1200, d.c), m: num("m", 400, 4000, d.m), n: num("n", 200, 600, d.n),
    s: s === "etminan2016" || s === "myhre1998" || s === "meinshausen2020" ? s : "meinshausen2020",
    d: Object.fromEntries(ALL_DRIVERS.map((x) => [x.key, num(x.key, 0, 200, 100)])),
  };
}

function writeURL() {
  const q = new URLSearchParams({ c: String(st.c), m: String(st.m), n: String(st.n), s: st.s });
  for (const x of ALL_DRIVERS) if (st.d[x.key] !== 100) q.set(x.key, String(st.d[x.key])); // only non-default drivers
  history.replaceState(null, "", `?${q}`);
}

function compute() {
  const erf = st.s !== "myhre1998"; // no published adjustment factors for the 1998 fit
  const g = wmghg(st.c, st.m, st.n, st.s, erf);
  const rel = (c: Component) => ({ lo: c.best !== 0 ? c.low / c.best : 1, hi: c.best !== 0 ? c.high / c.best : 1 });
  const ds: DriverState = { ch4: st.m, n2o: st.n };
  for (const x of ALL_DRIVERS) for (const k of x.state) (ds as Record<string, number>)[k] = st.d[x.key] / 100;
  const ng = nonGhgErf(B.nonghg, ds);
  const rows = B.components.map((c) => {
    let v = c.best;
    if (c.id === "CO2") v = g.co2;
    else if (c.id === "CH4") v = g.ch4;
    else if (c.id === "N2O") v = g.n2o;
    else if (c.id in ng) v = ng[c.id];
    else if (c.id === "Halogenated") v = c.best * (st.d.halo / 100);
    const scaled = true;
    const r = rel(c);
    const lo = scaled ? v * Math.min(r.lo, r.hi) : c.low;
    const hi = scaled ? v * Math.max(r.lo, r.hi) : c.high;
    return { ...c, value: v, lo: Math.min(lo, hi), hi: Math.max(lo, hi) };
  });
  const pick = (id: string) => rows.find((r) => r.id === id)!.value;
  const wm = pick("CO2") + pick("CH4") + pick("N2O") + pick("Halogenated");
  const tot = rows.reduce((s, r) => s + r.value, 0);
  return { rows, wm, tot, erf };
}

function render() {
  const { rows, wm, tot, erf } = compute();
  $("co2o").textContent = st.c.toFixed(1); $("ch4o").textContent = st.m.toFixed(1);
  $("n2oo").textContent = st.n.toFixed(1);
  for (const x of ALL_DRIVERS) { const o = document.getElementById(`${x.key}-o`); if (o) o.textContent = String(Math.round(st.d[x.key])); }
  $("k-wm").textContent = fmt(wm); $("k-tot").textContent = fmt(tot); $("k-eq").textContent = fmt(tot / LAMBDA, 1);
  $("schemenote").textContent = erf
    ? "Effective radiative forcing: includes the AR6 rapid tropospheric adjustments (CO₂ +5 %, CH₄ −14 %, N₂O +7 %)."
    : "Classic fit: an instantaneous-type forcing. No ERF adjustment factors exist for it, so the three gas bars are not strictly comparable with the AR6 ERF bars for the other agents.";
  renderEquations($("eqs"), st.s);
  $("eq-lambda").innerHTML = renderTex(EQ_LAMBDA);
  $("eq-nonghg").innerHTML = NONGHG_TEX.map((t) => `<div class="eq">${renderTex(t)}</div>`).join("") + `<p class="note">${NONGHG_NOTE}</p>`;

  const layout = { margin: { t: 10, r: 10, b: 120, l: 70 }, paper_bgcolor: "#fff", plot_bgcolor: "#fff",
    font: { family: "Roboto, Segoe UI, sans-serif", color: "#1c2733", size: 14 }, showlegend: false };
  Plotly.react("bars", [{
    type: "bar", x: rows.map((r) => r.label), y: rows.map((r) => r.value),
    marker: { color: rows.map((r) => COLOURS[r.id]) },
    error_y: { type: "data", symmetric: false, array: rows.map((r) => Math.max(r.hi - r.value, 0)),
               arrayminus: rows.map((r) => Math.max(r.value - r.lo, 0)), color: "#44505c", thickness: 1.2 },
    hovertemplate: "%{x}<br>%{y:.3f} W m⁻²<extra></extra>",
  }] as any, { ...layout, yaxis: { title: { text: "ERF (W m⁻²)" }, zeroline: true, zerolinecolor: "#44505c", gridcolor: "#e8edf3" },
    xaxis: { tickangle: -35, automargin: true } } as any, { responsive: true, displaylogo: false });

  const s = B.series;
  Plotly.react("ts", [
    { x: s.years, y: s.total_anthropogenic_high, mode: "lines", line: { width: 0 }, hoverinfo: "skip", showlegend: false },
    { x: s.years, y: s.total_anthropogenic_low, mode: "lines", fill: "tonexty", fillcolor: "rgba(43,123,208,.18)", line: { width: 0 }, hoverinfo: "skip", name: "5–95 % range" },
    { x: s.years, y: s.total_anthropogenic, mode: "lines", line: { color: "#2b7bd0", width: 2.5 }, name: "AR6 best estimate", hovertemplate: "%{x}: %{y:.2f} W m⁻²<extra>AR6</extra>" },
    { x: [B.year], y: [tot], mode: "markers", marker: { symbol: "diamond", size: 13, color: "#111" }, name: "Your setup", hovertemplate: "Your setup: %{y:.2f} W m⁻²<extra></extra>" },
  ] as any, { ...layout, showlegend: true, legend: { orientation: "h", y: 1.1 }, margin: { t: 10, r: 10, b: 55, l: 70 },
    xaxis: { title: { text: "Year" }, gridcolor: "#e8edf3" }, yaxis: { title: { text: "Total anthropogenic ERF (W m⁻²)" }, gridcolor: "#e8edf3" } } as any,
    { responsive: true, displaylogo: false });
}

function buildDrivers() {
  $("drivers").innerHTML = GROUPS.map((g) => `<details class="grp"><summary>${g.title}</summary>` + g.drivers.map((x) =>
    `<div class="ctl"><label for="${x.key}-r">${x.label} <output id="${x.key}-o"></output> % of 2019</label>
     <input type="range" id="${x.key}-r" min="0" max="200" step="1" />
     <details><summary>ℹ About this slider</summary><p>${x.info}</p></details></div>`).join("") + `</details>`).join("");
  for (const x of ALL_DRIVERS) $<HTMLInputElement>(`${x.key}-r`).addEventListener("input", (e) => {
    st.d[x.key] = Number((e.target as HTMLInputElement).value); update();
  });
}

function sync() {
  ($("co2") as HTMLInputElement).value = String(st.c); ($("ch4") as HTMLInputElement).value = String(st.m);
  ($("n2o") as HTMLInputElement).value = String(st.n);
  for (const x of ALL_DRIVERS) ($(`${x.key}-r`) as HTMLInputElement).value = String(st.d[x.key]);
  ($("scheme") as HTMLSelectElement).value = st.s;
}

function update() { writeURL(); render(); }

async function main() {
  const res = await fetch("./data/forcing_balance.json");
  B = await res.json();
  buildDrivers();
  readURL(); sync();
  const bind = (id: string, key: "c" | "m" | "n") =>
    $<HTMLInputElement>(id).addEventListener("input", (e) => { st[key] = Number((e.target as HTMLInputElement).value); update(); });
  bind("co2", "c"); bind("ch4", "m"); bind("n2o", "n");
  $<HTMLSelectElement>("scheme").addEventListener("change", (e) => { st.s = (e.target as HTMLSelectElement).value as Scheme; update(); });
  $("reset").addEventListener("click", () => { st = defaults(); sync(); update(); });
  $("pi").addEventListener("click", () => {
    const pi = B.preindustrial_state; // driver multiples of 2019 that correspond to 1750
    st = { ...st, c: PI.CO2, m: PI.CH4, n: PI.N2O,
      d: Object.fromEntries(ALL_DRIVERS.map((x) => [x.key, 100 * (pi[x.state[0]] ?? 0)])) };
    sync(); update();
  });
  $("x2").addEventListener("click", () => { st = { ...st, c: 2 * PI.CO2, m: PI.CH4, n: PI.N2O }; sync(); update(); });
  $("share").addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(location.href); $("status").textContent = "Link copied."; }
    catch { $("status").textContent = "Copy failed: copy the address bar instead."; }
  });
  $<HTMLInputElement>("adv").addEventListener("change", (e) => document.body.classList.toggle("adv", (e.target as HTMLInputElement).checked));
  initTabs();
  initHistory(B.history, B.components);
  render();
}

// Each tab: [button id, panel id, URL hash, optional loader that runs once, the first time the tab is shown]
type TabDef = readonly [string, string, string, (() => Promise<void>) | undefined];
function initTabs() {
  const tabs: TabDef[] = [
    ["tab-balance", "view-balance", "", undefined],
    ["tab-history", "view-history", "#history", undefined],
    ["tab-spectra", "view-spectra", "#spectra", async () => {
      void initAdjust().catch((e) => { $("sp-adj-text").textContent = `Could not load: ${String(e)}`; });
      await initSpectra().catch((e) => { $("sp-lab-info").textContent = `Could not load spectra data: ${String(e)}`; });
    }],
    ["tab-warming", "view-warming", "#warming", () => initWarming().catch((e) => { $("w-note").textContent = `Could not load: ${String(e)}`; })],
    ["tab-metrics", "view-metrics", "#metrics", () => initMetrics().catch((e) => { $("m-status").textContent = `Could not load: ${String(e)}`; })],
    ["tab-glossary", "view-glossary", "#glossary", () => initGlossary().catch((e) => { $("gl-count").textContent = `Could not load: ${String(e)}`; })],
    ["tab-about", "view-about", "#about", () => initAbout()],
  ];
  const started = new Set<string>();
  const show = (active: string) => {
    for (const [t, v] of tabs) {
      $(t).setAttribute("aria-selected", String(t === active));
      $(t).tabIndex = t === active ? 0 : -1;
      $(v).hidden = t !== active;
    }
    const def = tabs.find((d) => d[0] === active)!;
    if (def[3] && !started.has(active)) { started.add(active); void def[3](); }   // load heavy tables only when first needed
    window.dispatchEvent(new Event("resize")); // let Plotly size charts that were hidden
  };
  for (const [t, , h] of tabs) $(t).addEventListener("click", () => {
    show(t);
    history.replaceState(null, "", `${location.pathname}${t === "tab-balance" ? location.search : ""}${h}`);
  });
  // arrow keys move between tabs (WAI-ARIA tabs pattern)
  $("tab-balance").parentElement!.addEventListener("keydown", (e) => {
    const i = tabs.findIndex((d) => document.activeElement?.id === d[0]);
    if (i < 0 || !["ArrowRight", "ArrowLeft", "Home", "End"].includes(e.key)) return;
    e.preventDefault();
    const j = e.key === "Home" ? 0 : e.key === "End" ? tabs.length - 1 : (i + (e.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
    $(tabs[j][0]).focus(); $(tabs[j][0]).click();
  });
  $("skip").addEventListener("click", (e) => {
    e.preventDefault();
    const panel = document.querySelector<HTMLElement>('[role="tabpanel"]:not([hidden])');
    if (panel) { panel.tabIndex = -1; panel.focus(); }
  });
  document.querySelectorAll<HTMLAnchorElement>("footer a[data-tab]").forEach((a) =>
    a.addEventListener("click", (e) => { e.preventDefault(); $(a.dataset.tab!).click(); window.scrollTo({ top: 0, behavior: "smooth" }); }));
  const start = tabs.find((d) => d[2] && d[2] === location.hash);
  if (start) show(start[0]); else show("tab-balance");
}
// Plotly draws SVG that screen readers cannot read, so every chart gets a text label; the data are also in the hover text and tables
const CHART_LABELS: Record<string, string> = {
  bars: "Bar chart of effective radiative forcing by agent", ts: "Line chart of total anthropogenic forcing 1850 to 2019",
  hbars: "Horizontal bar chart of forcing by agent for the selected year", "sp-lab-chart": "Spectrum of the selected molecules: transmission against wavenumber",
  "sp-earth-chart": "Spectrum of radiation leaving the top of the atmosphere", "sp-diff-chart": "Change in outgoing radiation caused by the extra gas",
  "sp-growth-chart": "Forcing against amount of the selected gas", "sp-adj-chart": "Bar chart of the steps from instantaneous to effective forcing for doubled CO2",
  "w-temp": "Line chart of global warming for the selected scenario with the thermometer record", "w-erf": "Line chart of forcing by agent for the selected scenario",
  "w-co2": "Line chart of carbon dioxide concentration for the scenarios with the observed record", "m-curve": "Line chart of GWP or GTP against time horizon",
  "m-scatter": "Scatter plot of radiative efficiency against lifetime for all gases", "m-calc-chart": "Bar chart of CO2-equivalent emissions by gas",
};
for (const [id, label] of Object.entries(CHART_LABELS)) { const el = document.getElementById(id); if (el) { el.setAttribute("role", "img"); el.setAttribute("aria-label", label); } }

main().catch((e) => {
  const p = document.createElement("p"); // textContent, never HTML: error text is not trusted
  p.style.cssText = "color:#b00020;padding:16px"; p.textContent = `Failed to load: ${String(e)}`;
  document.body.prepend(p);
});
