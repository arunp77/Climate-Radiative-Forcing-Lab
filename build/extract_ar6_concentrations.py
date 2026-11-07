"""Convert the AR6 WG1 Annex III greenhouse-gas history (xlsx) to a plain CSV.

Input : data/raw/ar6/LLGHG_history_AR6_v9_for_archive.xlsx  (sheet 'mixing_ratios')
Output: data/processed/ar6_ghg_concentrations.csv
        columns: year, then one column per gas.  Units row is written to
        data/processed/ar6_ghg_concentrations_units.json
Years present are 1750 and 1850-2019 (as in the source).
"""
from __future__ import annotations

import json
from pathlib import Path

import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/raw/ar6/LLGHG_history_AR6_v9_for_archive.xlsx"
OUT = ROOT / "data/processed"


def main() -> None:
    wb = openpyxl.load_workbook(SRC, read_only=True, data_only=True)
    rows = list(wb["mixing_ratios"].iter_rows(values_only=True))
    units_i = next(i for i, r in enumerate(rows) if r[0] == "UNITS:")
    header = [h for h in rows[units_i + 1] if h is not None]
    units = dict(zip(header, [u for u in rows[units_i][: len(header)]]))
    data = [r[: len(header)] for r in rows[units_i + 2 :] if isinstance(r[0], (int, float))]
    df = pd.DataFrame(data, columns=header).rename(columns={"YYYY": "year"})
    df["year"] = df["year"].astype(int)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "ar6_ghg_concentrations.csv", index=False)
    units.pop("YYYY", None)
    (OUT / "ar6_ghg_concentrations_units.json").write_text(json.dumps(units, indent=1))
    print(f"wrote {len(df)} rows x {df.shape[1]} columns; years {df.year.min()}..{df.year.max()}")


if __name__ == "__main__":
    main()
