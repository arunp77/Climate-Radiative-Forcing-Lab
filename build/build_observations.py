"""Observations for the Warming tab -> web/public/data/observations.json.

* HadCRUT5 global annual temperature anomaly with its 95 % interval (Met Office Hadley Centre / UEA CRU; Morice et al. 2021),
  re-based here to the mean of 1850-1900.
* NOAA GML Mauna Loa annual-mean CO2 (Keeling-curve record).

Run from the repo root:  python build/build_observations.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/obs"
OUT = ROOT / "web/public/data/observations.json"


def main():
    h = pd.read_csv(RAW / "HadCRUT.5.0.2.0.analysis.summary_series.global.annual.csv")
    h.columns = ["year", "anom", "lo", "hi"]
    base = h[(h.year >= 1850) & (h.year <= 1900)].anom.mean()
    for c in ("anom", "lo", "hi"):
        h[c] = h[c] - base
    r = lambda s, k=3: [round(float(x), k) for x in s]

    co2 = pd.read_csv(RAW / "noaa_co2_annmean_mlo.txt", comment="#", sep=r"\s+", names=["year", "mean", "unc"])
    w = h[(h.year >= 2011) & (h.year <= 2020)]
    out = {
        "temperature": {"source": "HadCRUT5 (HadCRUT.5.0.2.0) global annual mean, re-based to 1850-1900", "years": h.year.astype(int).tolist(),
                        "anomaly": r(h.anom), "lower": r(h.lo), "upper": r(h.hi), "baseline_1850_1900_raw": round(float(base), 4)},
        "co2": {"source": "NOAA GML Mauna Loa annual mean", "years": co2.year.astype(int).tolist(), "ppm": r(co2["mean"], 2)},
        "stats": {"hadcrut5_2011_2020_vs_1850_1900": round(float(w.anom.mean()), 3),
                  "ar6_assessed_2011_2020_vs_1850_1900": [1.09, 0.95, 1.20]},
    }
    OUT.write_text(json.dumps(out, separators=(",", ":")))
    print(f"wrote {OUT} ({OUT.stat().st_size/1e3:.0f} kB); HadCRUT5 2011-2020 vs 1850-1900 = {out['stats']['hadcrut5_2011_2020_vs_1850_1900']} K; last years {h.year.iloc[-1]}, CO2 {co2.year.iloc[-1]}")


if __name__ == "__main__":
    main()
