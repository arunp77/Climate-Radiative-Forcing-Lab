"""Forcing of halogenated (F-gas / ozone-depleting) species.

These gases are present at ppt levels, absorb strongly (many in the 8-12 um
window) and are far from saturated, so their forcing is *linear* in the change
in concentration:

    ERF_i = RE_i * (C_i - C_i,1750)        [W m-2],  RE_i in W m-2 ppb-1

Radiative efficiencies RE_i are from AR6 Table 7.SM.7.  For the species that
dominate, the AR6 ERF series equals RE x dC to within 0.3 % (verified in tests).
"""
from __future__ import annotations

import numpy as np

from ..data import ar6_concentrations, ar6_metrics

_GROUPS = (
    ("CFC", lambda k: k.startswith("CFC")),
    ("HCFC", lambda k: k.startswith("HCFC")),
    ("HFC", lambda k: k.startswith("HFC")),
    ("Halon", lambda k: k.startswith("Halon")),
)


def group_of(species: str) -> str:
    """Display group: CFC, HCFC, HFC, Halon, or 'Other' (PFCs, SF6, NF3, ...)."""
    for name, test in _GROUPS:
        if test(species):
            return name
    return "Other"


def radiative_efficiency(species: str) -> float:
    """RE in W m-2 ppb-1 from AR6 Table 7.SM.7, or NaN if unavailable.

    Looks the species up by acronym first, then by chemical formula (the AR6
    concentration file uses formulas such as CF4, C2F6 for PFCs).
    """
    m = ar6_metrics()
    col = "Radiative efficiency (W m-2 ppb-1)"
    if species in m.index:
        return float(m.loc[species, col])
    by_formula = m.drop_duplicates("Formula").set_index("Formula")
    if species in by_formula.index:
        return float(by_formula.loc[species, col])
    return float("nan")


def halogen_forcing(concentrations_ppt: dict, baseline_ppt: dict | None = None) -> dict:
    """ERF (W m-2) of halogenated species.

    ``concentrations_ppt``: species -> mixing ratio in ppt.
    ``baseline_ppt``: reference mixing ratios (default 0 ppt, correct for
    synthetic species).

    Returns per-species values, per-group sums (``group:<name>``), ``total``,
    and ``skipped`` (species with no tabulated RE or a missing concentration,
    so nothing vanishes silently).
    """
    baseline_ppt = baseline_ppt or {}
    per, skipped = {}, []
    for sp, c in concentrations_ppt.items():
        re = radiative_efficiency(sp)
        if np.isnan(re) or np.isnan(float(c)):
            skipped.append(sp)
            continue
        per[sp] = re * (float(c) - float(baseline_ppt.get(sp, 0.0))) * 1e-3  # ppt -> ppb
    out = dict(per)
    for sp, v in per.items():
        g = f"group:{group_of(sp)}"
        out[g] = out.get(g, 0.0) + v
    out["total"] = sum(per.values())
    out["skipped"] = skipped
    return out


def halogen_forcing_year(year: int) -> dict:
    """Halogen ERF for a year of the AR6 concentration history (vs 1750)."""
    conc = ar6_concentrations()
    cols = [c for c in conc.columns if c not in ("CO2", "CH4", "N2O")]
    return halogen_forcing(conc.loc[year, cols].to_dict(), conc.loc[1750, cols].to_dict())
