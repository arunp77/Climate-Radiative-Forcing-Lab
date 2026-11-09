import Plotly from "plotly.js-basic-dist-min";
import { sub } from "./glossaryView";
import { renderTex } from "./equations";

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
const FONT = { family: "Roboto, Segoe UI, sans-serif", color: "#1c2733", size: 14 };
const GRID = "#e8edf3";

type Metric = "GWP20" | "GWP100" | "GWP500" | "GTP50" | "GTP100";
const METRICS: Metric[] = ["GWP20", "GWP100", "GWP500", "GTP50", "GTP100"];
const LABEL: Record<Metric, string> = { GWP20: "GWP-20", GWP100: "GWP-100", GWP500: "GWP-500", GTP50: "GTP-50", GTP100: "GTP-100" };

interface Sp {
  name: string; acronym: string; formula: string; lifetime: number | null; re: number | null;
  ar6: Record<Metric, number | null>; ours: Record<Metric, number> | null; curve: { gwp: number[]; gtp: number[] } | null;
  status: "verified" | "ar6-only"; maxdev?: number;
}
interface Data { horizons: number[]; tolerance: number; min_lifetime: number; species: Sp[] }

const key = (s: Sp) => s.acronym || s.formula || s.name;
const labelOf = (s: Sp) => (s.formula === "CO2" || s.formula === "CH4" || s.formula === "N2O" || s.formula === "SF6" ? `${s.name} (${sub(s.formula)})` : `${s.acronym || s.name}  ·  ${sub(s.formula)}`);
const value = (s: Sp, m: Metric) => s.ours?.[m] ?? s.ar6[m];
const fmt = (x: number | null | undefined) => (x == null ? "–" : x >= 100 ? Math.round(x).toLocaleString("en") : x >= 10 ? x.toFixed(1) : x >= 1 ? x.toFixed(2) : x.toPrecision(2));
const PRESETS = ["CH4", "N2O", "CFC-12", "HFC-134a", "SF6", "PFC-14"];
const CALC_DEFAULT = ["CO2", "CH4", "N2O", "HFC-134a", "SF6", "CFC-12"];
const COLORS = ["#2b7bd0", "#e8871e", "#2e9e5b", "#9467bd", "#d62728", "#8c564b", "#17becf"];

const TEX_GWP = String.raw`\mathrm{GWP}_X(H)=\frac{\int_0^{H}\mathrm{RF}_X(t)\,dt}{\int_0^{H}\mathrm{RF}_{\mathrm{CO_2}}(t)\,dt}`;
const TEX_GTP = String.raw`\mathrm{GTP}_X(H)=\frac{\Delta T_X(H)}{\Delta T_{\mathrm{CO_2}}(H)}`;

export async function initMetrics() {
  $("m-tex-gwp").innerHTML = renderTex(TEX_GWP);   // fixed strings of our own
  $("m-tex-gtp").innerHTML = renderTex(TEX_GTP);
  const D: Data = await fetch("./data/metrics.json").then((r) => r.json());
  const byKey = new Map<string, Sp>();
  for (const s of D.species) byKey.set(key(s), s);
  const byName = (k: string) => byKey.get(k) ?? D.species.find((s) => s.formula === k)!;

  // ---- gas picker
  const sel = $<HTMLSelectElement>("m-gas");
  const major = ["CO2", "CH4", "N2O"].map(byName);
  const verified = D.species.filter((s) => s.status === "verified" && !major.includes(s)).sort((a, b) => key(a).localeCompare(key(b)));
  const rest = D.species.filter((s) => s.status !== "verified").sort((a, b) => key(a).localeCompare(key(b)));
  const opt = (s: Sp) => `<option value="${key(s)}">${labelOf(s)}</option>`;
  sel.innerHTML = `<optgroup label="Major gases">${major.map(opt).join("")}</optgroup>` +
    `<optgroup label="Halogenated gases: recomputed here and checked against AR6 (${verified.length})">${verified.map(opt).join("")}</optgroup>` +
    `<optgroup label="AR6 values only: very short-lived gases and incomplete entries (${rest.length})">${rest.map(opt).join("")}</optgroup>`;
  sel.value = "CH4";
  const compare = new Set<string>(["CH4", "N2O", "CFC-12"]);
  $("m-presets").innerHTML = PRESETS.map((k) => `<button type="button" data-k="${k}" aria-pressed="${compare.has(k)}">${labelOf(byName(k)).split("  ·")[0].replace(/ \(.*\)/, "")}</button>`).join("");

  function kpis(s: Sp) {
    const cell = (m: Metric) => {
      const ours = s.ours?.[m], a = s.ar6[m];
      $(`m-${m}`).textContent = fmt(value(s, m));
      $(`m-${m}-l`).textContent = ours != null && a != null ? `AR6 table: ${fmt(a)}` : "AR6 table value";
    };
    METRICS.forEach(cell);
    $("m-life").textContent = s.lifetime == null ? "no single value" : s.lifetime >= 1000 ? `${Math.round(s.lifetime).toLocaleString("en")} yr` : `${s.lifetime} yr`;
    $("m-re").textContent = s.re == null ? "–" : s.re.toPrecision(3);
    $("m-status").textContent = s.status === "verified"
      ? `Recomputed from lifetime, radiative efficiency and molar mass; all five metrics within ${(D.tolerance * 100).toFixed(0)} % of AR6 (largest difference ${((s.maxdev ?? 0) * 100).toFixed(1)} %).`
      : (s.lifetime ?? 0) >= D.min_lifetime
        ? "AR6 table values shown. The molar mass cannot be worked out from the formula given in the table, so this gas is not recomputed here."
        : "AR6 table values shown. This gas lives under a year, where the result is dominated by the carbon-cycle term and by inputs the public table rounds away, so it is not recomputed here.";
  }

  function curves(selected: Sp) {
    const keys = [key(selected), ...[...compare].filter((k) => k !== key(selected))];
    const traces: unknown[] = []; let ci = 0;
    for (const k of keys) {
      const s = byName(k); const c = COLORS[ci++ % COLORS.length];
      const metric = ($<HTMLSelectElement>("m-curve-kind").value as "gwp" | "gtp");
      const ys = s.curve ? s.curve[metric] : null;
      if (ys) traces.push({ x: D.horizons, y: ys, mode: "lines", name: labelOf(s).split("  ·")[0].replace(/ \(.*\)/, ""), line: { color: c, width: k === key(selected) ? 4 : 2.2 },
        hovertemplate: `${key(s)}<br>%{x} yr: %{y:.3g}<extra></extra>` });
      const pts = metric === "gwp" ? ([[20, "GWP20"], [100, "GWP100"], [500, "GWP500"]] as const) : ([[50, "GTP50"], [100, "GTP100"]] as const);
      traces.push({ x: pts.map((p) => p[0]), y: pts.map((p) => s.ar6[p[1] as Metric]), mode: "markers", marker: { symbol: "diamond", size: 10, color: c, line: { color: "#111", width: 1 } },
        showlegend: false, hovertemplate: `AR6 table, ${key(s)}<br>%{x} yr: %{y:.3g}<extra></extra>` });
    }
    const metric = $<HTMLSelectElement>("m-curve-kind").value;
    Plotly.react("m-curve", traces as never[], {
      font: FONT, paper_bgcolor: "#fff", plot_bgcolor: "#fff", margin: { t: 10, r: 20, b: 60, l: 80 }, legend: { orientation: "h", y: 1.15 },
      xaxis: { type: "log", title: { text: metric === "gwp" ? "Time horizon (years)" : "Years after the emission" }, gridcolor: GRID, tickvals: [1, 2, 5, 10, 20, 50, 100, 200, 500], ticktext: ["1", "2", "5", "10", "20", "50", "100", "200", "500"] },
      yaxis: { type: "log", title: { text: metric === "gwp" ? "Global warming potential" : "Global temperature change potential" }, gridcolor: GRID },
    } as never, { responsive: true, displaylogo: false } as never);
  }

  function scatter(selected: Sp) {
    const pts = D.species.filter((s) => s.lifetime && s.lifetime > 0 && s.re && s.ar6.GWP100 && s.ar6.GWP100 > 0);
    const traces: unknown[] = [
      { x: pts.map((s) => s.lifetime), y: pts.map((s) => s.re), mode: "markers", type: "scatter",
        marker: { size: 8, color: pts.map((s) => Math.log10(s.ar6.GWP100 as number)), colorscale: "Viridis", reversescale: false, opacity: 0.75,
                  colorbar: { title: { text: "log₁₀ GWP-100" }, thickness: 14, len: 0.9 } },
        text: pts.map((s) => `${key(s)} (${s.formula})<br>GWP-100 ${fmt(s.ar6.GWP100)}`),
        hovertemplate: "%{text}<br>lifetime %{x} yr<br>RE %{y:.3g} W m⁻² ppb⁻¹<extra></extra>", showlegend: false },
    ];
    if (selected.lifetime && selected.re) traces.push({ x: [selected.lifetime], y: [selected.re], mode: "markers+text", text: [key(selected)], textposition: "top center",
      marker: { size: 16, color: "#fff", line: { color: "#111", width: 3 } }, hoverinfo: "skip", showlegend: false, textfont: { size: 14, color: "#111" } });
    Plotly.react("m-scatter", traces as never[], {
      font: FONT, paper_bgcolor: "#fff", plot_bgcolor: "#fff", margin: { t: 10, r: 10, b: 60, l: 80 },
      xaxis: { type: "log", title: { text: "Atmospheric lifetime (years)" }, gridcolor: GRID },
      yaxis: { type: "log", title: { text: "Radiative efficiency (W m⁻² ppb⁻¹)" }, gridcolor: GRID },
    } as never, { responsive: true, displaylogo: false } as never);
  }

  // ---- calculator
  const rows = CALC_DEFAULT.map(byName);
  $("m-calc-rows").innerHTML = rows.map((s) => `<tr><th scope="row">${labelOf(s).split("  ·")[0]}</th><td><input type="number" min="0" step="any" value="1" data-k="${key(s)}" aria-label="Emission of ${key(s)} in megatonnes" /></td>` +
    `<td class="r" data-f="${key(s)}"></td><td class="r" data-e="${key(s)}"></td></tr>`).join("");
  function calc() {
    const m = $<HTMLSelectElement>("m-calc-metric").value as Metric;
    let total = 0; const names: string[] = [], vals: number[] = [];
    for (const s of rows) {
      const inp = document.querySelector<HTMLInputElement>(`input[data-k="${key(s)}"]`)!;
      const mt = Math.max(0, Number(inp.value) || 0), f = value(s, m) ?? 0, e = mt * f;
      document.querySelector(`[data-f="${key(s)}"]`)!.textContent = fmt(f);
      document.querySelector(`[data-e="${key(s)}"]`)!.textContent = fmt(e);
      total += e; names.push(key(s) === "CO2" ? "CO₂" : labelOf(s).split("  ·")[0].replace(/ \(.*\)/, "")); vals.push(e);
    }
    $("m-calc-total").textContent = `${fmt(total)} Mt CO₂-equivalent (${LABEL[m]})`;
    Plotly.react("m-calc-chart", [{ type: "bar", x: names, y: vals, marker: { color: COLORS.slice(0, names.length) }, hovertemplate: "%{x}: %{y:.3g} Mt CO₂e<extra></extra>" }] as never[], {
      font: FONT, paper_bgcolor: "#fff", plot_bgcolor: "#fff", margin: { t: 10, r: 10, b: 50, l: 80 },
      yaxis: { type: "log", title: { text: "Mt CO₂-equivalent" }, gridcolor: GRID }, xaxis: {},
    } as never, { responsive: true, displaylogo: false } as never);
  }

  const redraw = () => { const s = byName(sel.value); kpis(s); curves(s); scatter(s); };
  sel.addEventListener("change", redraw);
  $("m-curve-kind").addEventListener("change", redraw);
  $("m-presets").addEventListener("click", (e) => {
    const b = (e.target as HTMLElement).closest("button[data-k]") as HTMLButtonElement | null; if (!b) return;
    const k = b.dataset.k!; if (compare.has(k)) compare.delete(k); else compare.add(k);
    b.setAttribute("aria-pressed", String(compare.has(k))); curves(byName(sel.value));
  });
  $("m-calc-metric").addEventListener("change", calc);
  $("m-calc-rows").addEventListener("input", calc);
  redraw(); calc();
}
