import Plotly from "plotly.js-basic-dist-min";

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
const FONT = { family: "Roboto, Segoe UI, sans-serif", color: "#1c2733", size: 14 };

interface Sky { toa_irf: number; tropopause_irf: number; toa_adjusted: number; tropopause_adjusted: number; dT_strat: number[] }
interface Adj {
  tropopause_km: number; z_mid_km: number[];
  cases: Record<string, { label: string; clear: Sky; all: Sky }>;
  ar6: Record<string, { sarf: number; erf: number }>; tropospheric_adjustment: Record<string, number>;
}

export async function initAdjust() {
  const D: Adj = await fetch("./data/adjustment.json").then((r) => r.json());
  let sky: "clear" | "all" = "all";
  const co2 = () => D.cases["2xCO2"][sky];
  const f = D.tropospheric_adjustment.CO2;

  function draw() {
    const r = co2();
    const adj = r.toa_adjusted - r.toa_irf;
    const erf = r.toa_adjusted * f;
    const steps = [
      { name: "Instantaneous, top of atmosphere<br>(the Spectra tab)", v: r.toa_irf, base: 0, c: "#2b7bd0" },
      { name: "Stratospheric<br>adjustment", v: adj, base: r.toa_irf, c: "#e8871e" },
      { name: "Stratosphere-adjusted<br>forcing (SARF)", v: r.toa_adjusted, base: 0, c: "#2b7bd0" },
      { name: `Tropospheric rapid<br>adjustments (+${Math.round((f - 1) * 100)} %)`, v: erf - r.toa_adjusted, base: r.toa_adjusted, c: "#e8871e" },
      { name: "Effective radiative<br>forcing (ERF), this model", v: erf, base: 0, c: "#1f6fc4" },
    ];
    const traces: unknown[] = [{ type: "bar", x: steps.map((s) => s.name), y: steps.map((s) => s.v), base: steps.map((s) => s.base),
      marker: { color: steps.map((s) => s.c) }, text: steps.map((s) => (s.base ? "+" : "") + s.v.toFixed(2)), textposition: "outside", cliponaxis: false,
      textfont: { size: 15 }, hovertemplate: "%{x}: %{y:.2f} W m⁻²<extra></extra>", showlegend: false }];
    if (sky === "all") {
      traces.push({ type: "bar", x: ["AR6<br>(ERF for 2 × CO₂)"], y: [D.ar6["2xCO2"].erf], marker: { color: "#111" }, text: [D.ar6["2xCO2"].erf.toFixed(2)], textposition: "outside",
        textfont: { size: 15 }, hovertemplate: "AR6: %{y:.2f} W m⁻²<extra></extra>", showlegend: false });
    }
    Plotly.react("sp-adj-chart", traces as never[], {
      font: FONT, paper_bgcolor: "#fff", plot_bgcolor: "#fff", margin: { t: 30, r: 20, b: 90, l: 70 }, bargap: 0.3,
      yaxis: { title: { text: "W m⁻²" }, gridcolor: "#e8edf3", range: [0, Math.max(erf, D.ar6["2xCO2"].erf) * 1.18] }, xaxis: { automargin: true },
    } as never, { responsive: true, displaylogo: false } as never);

    $("sp-adj-text").innerHTML =
      `Doubling CO₂ from 278 to 557 ppm changes the outgoing radiation by only <strong>${r.toa_irf.toFixed(2)} W m⁻²</strong> at the instant it is added, because the stratosphere, which is warm compared with the cold upper troposphere, also radiates more. ` +
      `Within a few months the stratosphere cools by up to ${Math.abs(Math.min(...r.dT_strat)).toFixed(0)} K and emits less to space, which raises the forcing by <strong>${adj.toFixed(2)} W m⁻²</strong> to ${r.toa_adjusted.toFixed(2)}. ` +
      `AR6 then adds the rapid changes in the troposphere (clouds, water vapour, temperature profile, +5 %).` +
      (sky === "all" ? ` The result, ${erf.toFixed(2)} W m⁻², is within ${Math.abs((erf / D.ar6["2xCO2"].erf - 1) * 100).toFixed(0)} % of the AR6 value of ${D.ar6["2xCO2"].erf.toFixed(2)}.` :
        ` Clear sky ignores clouds, so this is larger than AR6, which is an all-sky value.`);
  }

  // table for the three gases
  const rows = (["2xCO2", "CH4_2019", "N2O_2019"] as const).map((k) => {
    const c = D.cases[k], a = D.ar6[k];
    return `<tr><th scope="row">${c.label}</th><td class="r">${c.all.toa_irf.toFixed(2)}</td><td class="r">${c.all.toa_adjusted.toFixed(2)}</td><td class="r">${a.sarf.toFixed(2)}</td>` +
      `<td class="r">${(c.all.toa_adjusted / a.sarf * 100 - 100).toFixed(0)} %</td></tr>`;
  }).join("");
  $("sp-adj-rows").innerHTML = rows;

  $("sp-adj-sky").addEventListener("click", (e) => {
    const b = (e.target as HTMLElement).closest("button[data-sky]") as HTMLButtonElement | null;
    if (!b) return;
    sky = b.dataset.sky as "clear" | "all";
    $("sp-adj-sky").querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    draw();
  });
  draw();
}
