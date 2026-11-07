"""Compute GWP/GTP for the AR6 species and write web/public/data/metrics.json.

Run from the repo root:  python build/build_metrics.py
"""
from __future__ import annotations

import json
import math
import warnings
from pathlib import Path

import numpy as np

from radforce import metrics as M

OUT = Path(__file__).resolve().parents[1] / "web/public/data/metrics.json"
HORIZONS = [1, 2, 3, 5, 7, 10, 15, 20, 30, 40, 50, 60, 70, 80, 100, 125, 150, 200, 250, 300, 400, 500]
TOL = 0.03          # a species is "verified" when all five metrics are within 3 % of AR6 Table 7.SM.7
MIN_LIFETIME = 1.0  # yr: below this the value is dominated by inputs that the public table rounds away


def sig(x: float, n: int = 5):
    if x is None or not math.isfinite(x):
        return None
    return float(f"{x:.{n}g}")


def main():
    warnings.filterwarnings("ignore")
    species = []
    n_ok = n_short = n_off = 0
    for sp in M.ar6_species():
        m = M.species_metrics(sp)
        rec = {"name": sp.name, "acronym": sp.acronym, "formula": sp.formula, "lifetime": sig(sp.lifetime, 4) if sp.lifetime is not None else None,
               "re": sig(sp.re, 4) if sp.re is not None else None, "ar6": {k: sig(v) for k, v in sp.ar6.items() if k != "AGWP100"},
               "ours": None, "curve": None, "status": "ar6-only"}
        if m is not None and sp.lifetime and sp.lifetime >= MIN_LIFETIME or sp.formula in ("CO2", "CH4", "N2O"):
            try:
                ours = {"GWP20": M.gwp(m, 20), "GWP100": M.gwp(m, 100), "GWP500": M.gwp(m, 500), "GTP50": M.gtp(m, 50), "GTP100": M.gtp(m, 100)}
                dev = max(abs(ours[k] / sp.ar6[k] - 1) for k in ours)
            except (ZeroDivisionError, TypeError):
                ours, dev = None, 1.0
            if ours is not None and dev < TOL:
                rec["ours"] = {k: sig(v) for k, v in ours.items()}
                rec["maxdev"] = sig(dev, 2)
                rec["curve"] = {"gwp": [sig(M.gwp(m, h), 4) for h in HORIZONS], "gtp": [sig(M.gtp(m, h), 4) for h in HORIZONS]}
                rec["status"] = "verified"
                n_ok += 1
            else:
                n_off += 1
        else:
            n_short += 1
        species.append(rec)
    out = {"horizons": HORIZONS, "tolerance": TOL, "min_lifetime": MIN_LIFETIME, "species": species,
           "agwp_co2": {"AGWP20": sig(M.co2_metrics().at(20)[0]), "AGWP100": sig(M.co2_metrics().at(100)[0]),
                        "AGWP500": sig(M.co2_metrics().at(500)[0])}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, separators=(",", ":")))
    print(f"species {len(species)}: verified {n_ok}, ar6-only short-lived/other {n_short}, off-tolerance {n_off}; {OUT.stat().st_size/1e3:.0f} kB")


if __name__ == "__main__":
    main()
