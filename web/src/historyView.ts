import Plotly from "plotly.js-basic-dist-min";
import { COLOURS, EXPLAIN, SHORT } from "./agents";
import { clampYear, netAt, nextYear, playbackAxis, valuesAt, type History } from "./history";

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

export function initHistory(h: History, comps: { id: string; label: string }[]) {
  const labels = comps.map((c) => SHORT[c.id] ?? c.label);
  const ids = comps.map((c) => c.id);
  const [lo, hi] = playbackAxis(h);
  const slider = $<HTMLInputElement>("h-slider"), box = $<HTMLInputElement>("h-yearbox");
  const play = $<HTMLButtonElement>("h-play"), ghostChk = $<HTMLInputElement>("h-ghost");
  const ghostYr = $<HTMLInputElement>("h-ghostyear"), speed = $<HTMLSelectElement>("h-speed");
  let year = h.years[h.years.length - 1];
  let timer: number | undefined;

  function draw() {
    const v = valuesAt(h, year);
    const traces: unknown[] = [];
    const on = ghostChk.checked;
    const gy = clampYear(Number(ghostYr.value), h);
    const fmtv = (x: number) => x.toFixed(2);
    // current year first (upper lane), comparison year second (lower lane): both always visible side by side
    traces.push({ type: "bar", orientation: "h", y: labels, x: ids.map((i) => v[i]),
      marker: { color: ids.map((i) => COLOURS[i]) }, name: String(year),
      text: ids.map((i) => fmtv(v[i])), textposition: "outside", cliponaxis: false, textfont: { size: 13 },
      hovertemplate: `%{y}, ${year}<br>%{x:.3f} W m⁻²<extra></extra>` });
    if (on) {
      const g = valuesAt(h, gy);
      traces.push({ type: "bar", orientation: "h", y: labels, x: ids.map((i) => g[i]),
        marker: { color: "rgba(120,132,146,.45)", line: { color: "#2d3945", width: 1.5 } }, name: String(gy),
        text: ids.map((i) => fmtv(g[i])), textposition: "outside", cliponaxis: false, textfont: { size: 13, color: "#44505c" },
        hovertemplate: `%{y}, ${gy} (comparison)<br>%{x:.3f} W m⁻²<extra></extra>` });
    }
    $("h-key").innerHTML = `<span class="kk"><i style="background:#2b7bd0"></i>${year} (coloured bars, follows the slider)</span>` +
      (on ? `<span class="kk"><i class="gh"></i>${gy} (grey bars, comparison)</span>` : "");
    Plotly.react("hbars", traces, {
      barmode: "group", bargap: on ? 0.22 : 0.35, bargroupgap: 0.04,
      margin: { t: 10, r: 50, b: 65, l: 190 }, paper_bgcolor: "#fff", plot_bgcolor: "#fff",
      font: { family: "Roboto, Segoe UI, sans-serif", color: "#1c2733", size: 15 }, showlegend: false,
      xaxis: { range: [lo, hi], fixedrange: true, title: { text: "Effective radiative forcing since 1750 (W m⁻²)" },
               zeroline: true, zerolinecolor: "#111", zerolinewidth: 2, gridcolor: "#e8edf3" },
      yaxis: { autorange: "reversed", fixedrange: true },
      transition: { duration: 0 },
    }, { responsive: true, displaylogo: false, displayModeBar: false });
    $("h-year").textContent = String(year);
    $("h-net").textContent = netAt(h, year).toFixed(2);
    slider.value = String(year);
    if (document.activeElement !== box) box.value = String(year);
  }

  const setYear = (y: number) => { year = clampYear(y, h); draw(); };
  const stop = () => { if (timer !== undefined) { clearInterval(timer); timer = undefined; } play.textContent = "▶ Play"; play.setAttribute("aria-label", "Play animation"); };
  const start = () => {
    if (year >= h.years[h.years.length - 1]) year = h.years[0];
    play.textContent = "⏸ Pause"; play.setAttribute("aria-label", "Pause animation");
    timer = window.setInterval(() => { year = nextYear(year, h); draw(); if (year >= h.years[h.years.length - 1]) stop(); }, Number(speed.value));
  };

  slider.min = box.min = ghostYr.min = String(h.years[0]);
  slider.max = box.max = ghostYr.max = String(h.years[h.years.length - 1]);
  play.addEventListener("click", () => (timer === undefined ? start() : stop()));
  slider.addEventListener("input", () => { stop(); setYear(Number(slider.value)); });
  box.addEventListener("change", () => { stop(); setYear(Number(box.value)); });
  ghostChk.addEventListener("change", draw);
  ghostYr.addEventListener("change", () => { ghostYr.value = String(clampYear(Number(ghostYr.value), h)); draw(); });
  speed.addEventListener("change", () => { if (timer !== undefined) { stop(); start(); } });
  // animation must not keep running while the tab is hidden
  document.addEventListener("visibilitychange", () => { if (document.hidden) stop(); });
  $("tab-balance").addEventListener("click", stop);

  $("h-info").innerHTML = comps.map((c) =>
    `<details><summary><span class="sw" style="background:${COLOURS[c.id]}"></span>${c.label}</summary><p>${EXPLAIN[c.id]}</p></details>`).join("");
  draw();
}
