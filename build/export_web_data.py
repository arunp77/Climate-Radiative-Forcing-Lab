"""Export precomputed tables and cross-check vectors for the web app.

Writes:
  web/public/data/forcing_balance.json   AR6 2019 balance sheet (best, 5%, 95%) + time series
  web/tests/forcing_vectors.json         Python reference values used by Vitest to
                                         verify the TypeScript port of the forcing equations
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from radforce import wmghg_forcing
from radforce.spectra import planck
from radforce.data import ar6_concentrations, ar6_erf
from radforce.forcing.halogens import halogen_forcing_year
from radforce.forcing.nonghg import load_params, non_ghg_erf, preindustrial_state

ROOT = Path(__file__).resolve().parents[1]
YEAR = 2019

# display name -> AR6 column; signs and groupings follow AR6 Fig. 7.6 / Table 7.8
COMPONENTS = [
    ("CO2", "co2", "Carbon dioxide (CO₂)"),
    ("CH4", "ch4", "Methane (CH₄)"),
    ("N2O", "n2o", "Nitrous oxide (N₂O)"),
    ("Halogenated", "other_wmghg", "Halogenated gases (CFCs, HFCs, ...)"),
    ("O3", "o3", "Ozone (troposphere + stratosphere)"),
    ("H2O_strat", "h2o_stratospheric", "Stratospheric water vapour"),
    ("Contrails", "contrails", "Contrails & aviation cirrus"),
    ("Aerosol_ari", "aerosol-radiation_interactions", "Aerosol–radiation interactions"),
    ("Aerosol_aci", "aerosol-cloud_interactions", "Aerosol–cloud interactions"),
    ("BC_snow", "bc_on_snow", "Black carbon on snow"),
    ("LandUse", "land_use", "Land-use (albedo)"),
]


def main() -> None:
    best, lo, hi = ar6_erf("best"), ar6_erf("pc05"), ar6_erf("pc95")
    conc = ar6_concentrations()
    comps = [
        dict(id=i, label=lab, best=float(best.loc[YEAR, c]),
             low=float(lo.loc[YEAR, c]), high=float(hi.loc[YEAR, c]))
        for i, c, lab in COMPONENTS
    ]
    years = [int(y) for y in best.index if y >= 1850]
    series = {
        "years": years,
        "total_anthropogenic": [float(best.loc[y, "total_anthropogenic"]) for y in years],
        "total_anthropogenic_low": [float(lo.loc[y, "total_anthropogenic"]) for y in years],
        "total_anthropogenic_high": [float(hi.loc[y, "total_anthropogenic"]) for y in years],
        "co2_ppm": [float(conc.loc[y, "CO2"]) for y in years],
    }
    hist_years = [int(y) for y in best.index if y >= 1850]
    history = {
        "years": hist_years,
        "ids": [i for i, _, _ in COMPONENTS],
        "values": {i: [round(float(best.loc[y, c]), 5) for y in hist_years] for i, c, _ in COMPONENTS},
        "net": [round(float(best.loc[y, "total_anthropogenic"]), 5) for y in hist_years],
    }
    out = {
        "year": YEAR,
        "reference_year": 1750,
        "source": "IPCC AR6 WG1 Ch.7; C. Smith et al. ERF time series (see data/MANIFEST.md)",
        "concentrations": {g: float(conc.loc[YEAR, g]) for g in ("CO2", "CH4", "N2O")},
        "preindustrial": {g: float(conc.loc[1750, g]) for g in ("CO2", "CH4", "N2O")},
        "components": comps,
        "halogen_computed": halogen_forcing_year(YEAR)["total"],
        "series": series,
        "history": history,
        "nonghg": load_params().to_json(),
        "preindustrial_state": preindustrial_state(),
    }
    p = ROOT / "web/public/data"
    p.mkdir(parents=True, exist_ok=True)
    (p / "forcing_balance.json").write_text(json.dumps(out, indent=1))

    # cross-check vectors: a grid including values outside the Etminan validity range
    vecs = []
    for C in (180, 278.3, 410, 560, 840, 1200, 2500):
        for M in (729.2, 1200, 1900, 3500):
            for N in (270.1, 332, 420, 525):
                for scheme in ("meinshausen2020", "etminan2016", "myhre1998"):
                    erf = scheme != "myhre1998"
                    f = wmghg_forcing(C, M, N, scheme=scheme, erf=erf)
                    vecs.append(dict(C=C, M=M, N=N, scheme=scheme, erf=erf,
                                     co2=float(f["CO2"]), ch4=float(f["CH4"]), n2o=float(f["N2O"])))
    # cross-check vectors for the non-GHG emulators (seeded, includes extremes and 1750)
    rng = np.random.default_rng(20261107)
    keys = ["so2", "bc", "oc", "nh3", "nox", "co", "voc", "ods", "landuse", "contrails"]
    nvecs = []
    for i in range(120):
        st = {k: float(rng.uniform(0, 2)) for k in keys}
        st["ch4"] = float(rng.uniform(400, 4000))
        st["n2o"] = float(rng.uniform(250, 600))
        if i < 3:
            st = [{}, preindustrial_state(), {k: 0.0 for k in keys} | {"ch4": 729.2, "n2o": 270.1}][i]
        nvecs.append(dict(state=st, erf={k: float(v) for k, v in non_ghg_erf(st).items()}))
    t = ROOT / "web/tests"
    t.mkdir(parents=True, exist_ok=True)
    pv = [dict(nu=float(n), T=float(T), B=float(planck.radiance(n, T)))
          for n in (5, 100, 300, 667, 1000, 1500, 2349, 3000, 4000) for T in (180, 220, 288.15, 320)]
    (t / "planck_vectors.json").write_text(json.dumps(pv))
    (t / "forcing_vectors.json").write_text(json.dumps(vecs))
    (t / "nonghg_vectors.json").write_text(json.dumps(nvecs))
    print(f"balance sheet: {len(comps)} components; {len(vecs)} cross-check vectors")


if __name__ == "__main__":
    main()
