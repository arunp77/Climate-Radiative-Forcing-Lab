"""Run FaIR v2 for five SSP scenarios and write web/public/data/scenarios.json.

Run from the repo root:  python build/run_fair.py   (downloads the RCMIP v5.1.0 emissions on first use, ~48 MB)

One deterministic run per scenario: FaIR 2.2 default species configuration, with the energy-balance (climate)
parameters set to the MEDIAN of the AR6-constrained posterior (Smith et al. 2024, fair-calibrate v1.4.1, Zenodo
10566813). This is not the full 841-member constrained ensemble, so no uncertainty range is produced; the AR6
assessed ranges are shown for comparison instead.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from fair import FAIR
from fair.interface import fill, initialise
from fair.io import read_properties

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web/public/data/scenarios.json"
POST = ROOT / "data/raw/fair_calibration/calibrated_constrained_parameters.csv"
SCENARIOS = ["ssp119", "ssp126", "ssp245", "ssp370", "ssp585"]
LABELS = {"ssp119": "SSP1-1.9", "ssp126": "SSP1-2.6", "ssp245": "SSP2-4.5", "ssp370": "SSP3-7.0", "ssp585": "SSP5-8.5"}
BLURB = {"ssp119": "Very low emissions, net zero CO₂ around 2050", "ssp126": "Low emissions, net zero CO₂ in the second half of the century",
         "ssp245": "Intermediate: emissions roughly constant until mid-century", "ssp370": "High emissions, weak climate policy",
         "ssp585": "Very high, fossil-fuel-intensive emissions"}
# IPCC AR6 WG1 Summary for Policymakers, Table SPM.1: warming 2081-2100 relative to 1850-1900, best estimate [very likely range], K
AR6_2081_2100 = {"ssp119": [1.4, 1.0, 1.8], "ssp126": [1.8, 1.3, 2.4], "ssp245": [2.7, 2.1, 3.5], "ssp370": [3.6, 2.8, 4.6], "ssp585": [4.4, 3.3, 5.7]}
GROUPS = {
    "CO₂": ["CO2"], "CH₄": ["CH4"], "N₂O": ["N2O"],
    "Halogenated gases": None,   # filled from species types below
    "Ozone": ["Ozone"], "Aerosols": ["Aerosol-radiation interactions", "Aerosol-cloud interactions"],
    "Other human": ["Contrails", "Light absorbing particles on snow and ice", "Stratospheric water vapour", "Land use"],
    "Natural": ["Solar", "Volcanic"],
}
Y0, Y1 = 1750, 2100


def main():
    f = FAIR(ch4_method="Thornhill2021")
    f.define_time(Y0, Y1 + 1, 1)
    f.define_scenarios(SCENARIOS)
    f.define_configs(["median"])
    species, props = read_properties()
    f.define_species(species, props)
    f.allocate()
    f.fill_from_rcmip()
    f.fill_species_configs()
    m = pd.read_csv(POST, index_col=0).median()
    params = {"c": [m.clim_c1, m.clim_c2, m.clim_c3], "kappa": [m.clim_kappa1, m.clim_kappa2, m.clim_kappa3],
              "epsilon": m.clim_epsilon, "F4x": m.clim_F_4xCO2}
    fill(f.climate_configs["ocean_heat_capacity"], params["c"])
    fill(f.climate_configs["ocean_heat_transfer"], params["kappa"])
    fill(f.climate_configs["deep_ocean_efficacy"], params["epsilon"])
    fill(f.climate_configs["forcing_4co2"], params["F4x"])
    initialise(f.concentration, f.species_configs["baseline_concentration"])
    initialise(f.forcing, 0); initialise(f.temperature, 0); initialise(f.cumulative_emissions, 0); initialise(f.airborne_emissions, 0)
    f.run(progress=False)

    halogen_types = {"cfc-11", "f-gas", "other halogen"}
    groups = dict(GROUPS)
    groups["Halogenated gases"] = [s for s in species if props[s]["type"] in halogen_types]
    idx = {s: i for i, s in enumerate(species)}
    years = np.arange(Y0, Y1 + 1)
    n = years.size
    T = np.asarray(f.temperature)[:, :, 0, 0]               # (timebounds, scenario)
    Tmid = 0.5 * (T[:-1] + T[1:])                           # annual means (mid-year)
    base = Tmid[100:151].mean(axis=0)                       # 1850-1900
    mid = lambda a: 0.5 * (a[:-1] + a[1:])                  # forcing is defined at the time bounds; annual value = mean of the two
    forc_b = np.asarray(f.forcing)[:, :, 0, :]              # (timebounds, scenario, species)
    forc = mid(forc_b)
    fsum = mid(np.asarray(f.forcing_sum)[:, :, 0])
    eff = np.nan_to_num(np.asarray(f.species_configs["forcing_efficacy"])[0])        # (species,)
    fdrive_b = np.nansum(forc_b * eff[None, None, :], axis=2)                          # efficacy-weighted forcing that drives the EBM
    conc = np.asarray(f.concentration)[:n, :, 0, :]
    toa = np.asarray(f.toa_imbalance)[:n, :, 0]

    out = {"years": years.tolist(), "params": {"c": [float(x) for x in params["c"]], "kappa": [float(x) for x in params["kappa"]],
                                               "epsilon": float(params["epsilon"]), "F4x": float(params["F4x"])},
           "baseline_period": [1850, 1900], "scenarios": {}, "ar6_2081_2100": AR6_2081_2100, "groups": list(groups)}
    r = lambda a, k=3: [round(float(x), k) for x in a]
    summary = {}
    for i, s in enumerate(SCENARIOS):
        g = {name: r(forc[:, i, [idx[x] for x in members]].sum(axis=1)) for name, members in groups.items()}
        out["scenarios"][s] = {
            "label": LABELS[s], "blurb": BLURB[s], "erf_total": r(fsum[:, i]), "erf_driving_bounds": r(fdrive_b[:, i], 4), "erf_groups": g,
            "temperature": r(Tmid[:, i] - base[i]), "co2_ppm": r(conc[:, i, idx["CO2"]], 2),
            "ch4_ppb": r(conc[:, i, idx["CH4"]], 1), "n2o_ppb": r(conc[:, i, idx["N2O"]], 2), "toa_imbalance": r(toa[:, i]),
        }
        w = slice(2081 - Y0, 2101 - Y0)
        summary[s] = {"T_2081_2100": float(Tmid[w, i].mean() - base[i]), "T_2019": float(Tmid[2019 - Y0, i] - base[i])}
        grp_sum = sum(np.array(v) for v in g.values())
        summary[s]["max_group_vs_total_gap"] = float(np.max(np.abs(grp_sum - fsum[:, i])))
    out["summary"] = summary
    OUT.write_text(json.dumps(out, separators=(",", ":")))
    print(f"wrote {OUT} ({OUT.stat().st_size/1e3:.0f} kB)")
    for s in SCENARIOS:
        a = AR6_2081_2100[s]
        print(f"{LABELS[s]}: 2081-2100 warming {summary[s]['T_2081_2100']:.2f} K   AR6 {a[0]} [{a[1]}-{a[2]}]   group/total gap {summary[s]['max_group_vs_total_gap']:.3f}")


if __name__ == "__main__":
    main()
