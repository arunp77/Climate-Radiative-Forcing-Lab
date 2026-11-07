"""Download HITRAN line lists with HAPI into data/raw/hitran/ (git-ignored, not redistributed).

HITRAN terms of use: the database may be used freely for research and teaching, but the raw
line lists must not be redistributed; we ship only DERIVED spectra.  Cite:
  Gordon et al. (2022), The HITRAN2020 molecular spectroscopic database, JQSRT 277, 107949.
  Kochanov et al. (2016), HITRAN Application Programming Interface (HAPI), JQSRT 177, 15.

Run from the repo root:  python build/fetch_hitran.py
"""
from __future__ import annotations

from pathlib import Path

from hapi import db_begin, fetch

DB = Path(__file__).resolve().parents[1] / "data/raw/hitran"
NU_MIN, NU_MAX = 10.0, 4000.0   # cm-1

# name -> (HITRAN molecule id, [isotopologue local ids])  (most abundant isotopologues)
MOLECULES = {
    "H2O": (1, [1, 2, 3, 4]),     # H2(16)O, H2(18)O, H2(17)O, HD(16)O
    "CO2": (2, [1, 2, 3, 4]),     # 626, 636, 628, 627
    "O3":  (3, [1, 2, 3]),        # 666, 668, 686
    "N2O": (4, [1, 2, 3, 4]),     # 446, 456, 546, 448
    "CH4": (6, [1, 2]),           # 211, 311
    "CF4": (29, [1]),
}

if __name__ == "__main__":
    DB.mkdir(parents=True, exist_ok=True)
    db_begin(str(DB))
    for name, (mid, isos) in MOLECULES.items():
        for iso in isos:
            table = f"{name}_i{iso}"
            if (DB / f"{table}.data").exists():
                print("have", table)
                continue
            fetch(table, mid, iso, NU_MIN, NU_MAX)
