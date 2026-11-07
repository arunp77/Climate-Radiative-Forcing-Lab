"""Extra sections of docs/validation.md (metrics, stratospheric adjustment, warming), built from the shipped web tables."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

WEB = Path(__file__).resolve().parents[1] / "web/public/data"


def more_sections() -> list[str]:
    lines: list[str] = []
    mf = WEB / "metrics.json"
    if mf.exists():
        sp = json.loads(mf.read_text())["species"]
        ver = [x for x in sp if x["status"] == "verified"]
        hal = [x for x in ver if x["formula"] not in ("CO2", "CH4", "N2O")]
        dev = np.array([x["maxdev"] for x in hal])
        pick = {k: next(x for x in sp if (x["acronym"] or x["formula"]) == k) for k in ("CH4", "N2O", "CFC-12", "HFC-134a", "SF6")}
        lines += ["", "## Emission metrics (GWP and GTP), against AR6 Table 7.SM.7", "",
                  "Method: AR6 WG1 Section 7.6.1 (impulse-response CO2 of Joos et al. 2013, two-timescale temperature response, climate-carbon feedback "
                  "of Gasser et al. 2017, AR6 adjustments for CH4 and N2O). Code: `physics/radforce/metrics.py`; tests: `physics/tests/test_metrics.py`.", "",
                  f"* {len(hal)} halogenated gases with a lifetime of at least a year, recomputed from lifetime, radiative efficiency and a molar mass derived from the "
                  f"formula: all five metrics (GWP-20/100/500, GTP-50/100) within {dev.max()*100:.1f} % of AR6; {int(np.sum(dev < 0.01))} of {len(dev)} within 1 %.",
                  "* Gases living under a year (and two entries with no usable formula) are not recomputed; AR6 values are shown instead, because the result there is "
                  "dominated by the carbon-cycle term and by inputs the public table rounds away.", "",
                  "| Gas | metric | this model | AR6 |", "|---|---|---|---|"]
        for k, x in pick.items():
            lines.append(f"| {k} | GWP-100 | {x['ours']['GWP100']:.4g} | {x['ar6']['GWP100']:.4g} |")
        lines.append("")
    af = WEB / "adjustment.json"
    if af.exists():
        a = json.loads(af.read_text())
        c = a["cases"]
        lines += ["", "## Stratospheric adjustment (fixed dynamical heating)", "",
                  "Method and approximations: `physics/radforce/spectra/adjust.py`; computation: `build/stratospheric_adjustment.py`; "
                  "tests: `physics/tests/test_adjust.py`, `physics/tests/test_adjustment_results.py`.", "",
                  "| Change (all-sky) | instantaneous, top of atmosphere (W m-2) | stratosphere-adjusted, this model | AR6 stratosphere-adjusted | difference |",
                  "|---|---|---|---|---|"]
        for k, v in c.items():
            ar = a["ar6"][k]["sarf"]
            lines.append(f"| {v['label']} | {v['all']['toa_irf']:.2f} | {v['all']['toa_adjusted']:.2f} | {ar:.2f} | {(v['all']['toa_adjusted']/ar-1)*100:+.0f} % |")
        co2 = c["2xCO2"]["all"]
        lines += ["", f"For 2 x CO2 the adjustment adds {co2['toa_adjusted']-co2['toa_irf']:.2f} W m-2 at the top of the atmosphere and removes "
                  f"{co2['tropopause_irf']-co2['tropopause_adjusted']:.2f} W m-2 at the tropopause (instantaneous {co2['tropopause_irf']:.2f}); both ends agree after adjustment "
                  f"({co2['toa_adjusted']:.3f} and {co2['tropopause_adjusted']:.3f}). With AR6's +5 % tropospheric adjustment the model effective forcing is "
                  f"{co2['toa_adjusted']*1.05:.2f} W m-2 against AR6's {a['ar6']['2xCO2']['erf']:.2f}. The methane forcing is "
                  f"{abs(c['CH4_2019']['all']['toa_adjusted']/a['ar6']['CH4_2019']['sarf']-1)*100:.0f} % below AR6's; the cause was not isolated.", ""]
    sf, of = WEB / "scenarios.json", WEB / "observations.json"
    if sf.exists():
        from radforce.ebm import EbmParams, tcr
        d = json.loads(sf.read_text())
        p = d["params"]
        P = EbmParams(tuple(p["c"]), tuple(p["kappa"]), p["epsilon"], p["F4x"], 2.0)
        lines += ["", "## Warming and scenarios (FaIR v2 with the median AR6-constrained climate parameters)", "",
                  f"Climate response: three-layer energy balance model, ECS {P.ecs:.2f} K, TCR {tcr(P):.2f} K (AR6: 3 K [2.5-4], 1.8 K [1.4-2.2]). "
                  "The Python and TypeScript implementations both reproduce the FaIR run (`physics/tests/test_ebm.py`, `web/tests/ebm.test.ts`).", "",
                  "| Scenario | 2081-2100 warming, this run (K) | AR6 SPM Table SPM.1: best estimate [very likely range] |", "|---|---|---|"]
        for s, (b, lo, hi) in d["ar6_2081_2100"].items():
            t = np.array(d["scenarios"][s]["temperature"])[2081 - 1750: 2101 - 1750].mean()
            lines.append(f"| {d['scenarios'][s]['label']} | {t:.2f} | {b} [{lo}-{hi}] |")
        lines.append("")
        if of.exists():
            o = json.loads(of.read_text())
            t = np.array(d["scenarios"]["ssp245"]["temperature"])[2011 - 1750: 2021 - 1750].mean()
            co2o = dict(zip(o["co2"]["years"], o["co2"]["ppm"]))
            yr = 2024
            st = o["stats"]
            lines += [f"Present-day check: modelled 2011-2020 warming (1850-1900 baseline) {t:.2f} K; HadCRUT5 {st['hadcrut5_2011_2020_vs_1850_1900']:.2f} K; "
                      f"AR6 assessed {st['ar6_assessed_2011_2020_vs_1850_1900'][0]} K [{st['ar6_assessed_2011_2020_vs_1850_1900'][1]}-{st['ar6_assessed_2011_2020_vs_1850_1900'][2]}]. "
                      f"CO2 in {yr}: SSP2-4.5 {d['scenarios']['ssp245']['co2_ppm'][yr-1750]:.1f} ppm, Mauna Loa {co2o[yr]:.1f} ppm.", "",
                      "Limits: one deterministic run per scenario (no ensemble spread), global-mean series only, no regional climate.", ""]
    return lines
