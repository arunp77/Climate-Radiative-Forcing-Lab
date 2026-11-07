"""Forcing from the non-CO2/CH4/N2O agents: ozone, aerosols, black carbon on snow,
stratospheric water vapour, land use and contrails.

Approach
--------
Each agent has a small *emulator* taken from the AR6 forcing construction
(C. Smith et al., repo ``chrisroadmap/ar6``; IPCC AR6 WG1 Ch. 6-7), which gives the
*shape* of the response to its drivers.  Each emulator is then normalised so that the
2019 drivers reproduce the AR6 2019 best-estimate ERF exactly:

    ERF_x(drivers) = ERF_x^AR6(2019) * raw_x(drivers) / raw_x(2019 drivers)

so default sliders equal AR6 and 1750 drivers give exactly zero.  The emulators are
checked against the full AR6 1750-2019 series in ``tests/test_nonghg.py``; their
documented accuracy is quoted next to each function.

Drivers (the ``state`` dict, all optional, default = 2019 values)
-----------------------------------------------------------------
``so2, bc, oc, nh3, nox, co, voc``  emissions as a multiple of their 2019 value
``ods``      equivalent effective stratospheric chlorine anomaly (vs 1750) as a multiple
             of its 2019 value
``ch4, n2o`` mixing ratios in ppb
``landuse, contrails``  simple multipliers on the 2019 AR6 forcing (no driver model yet)

Units of the bundled emissions: Mt per year (RCMIP/CEDS conventions: BC and OC as C,
SO2 as SO2, NOx as NO2, NH3 as NH3, VOC and CO as mass).
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import pandas as pd

from ..constants import (
    ACI_N0_SO2, ACI_N1_BCOC, EESC_BR_ATOMS, EESC_BR_FACTOR, EESC_CL_ATOMS, EESC_FRACREL, EESC_SPECIES, PREINDUSTRIAL_1750,
)
from ..data import RAW, ar6_concentrations, ar6_erf
from .wmghg import ch4_forcing

EMIS_SPECIES = ("SO2", "BC", "OC", "NH3", "NOx", "CO", "VOC")

# AR6 assessed ERFari contribution of each species, mean 2005-2014 vs 1750 (W m-2).
# From the AR6 ERF notebook (080_chapter7_AR6_ERF), based on AR6 Ch. 6 and 7:
# black carbon +0.3, organic carbon -0.09, sulphate -0.4, nitrate (NH3) -0.11.
ARI_ASSESSED_2005_2014 = {"BC": 0.3, "OC": -0.09, "SO2": -0.4, "NH3": -0.11}

# AR6 assigns 0.08 W m-2 (2019) to black carbon on snow, linear in BC emissions,
# 0.05 W m-2 to stratospheric water vapour from methane oxidation (proportional to
# CH4 ERF), and -0.20 W m-2 to land-use albedo change (AR6 Sect. 7.3.4).
BC_SNOW_2019 = 0.08
H2O_STRAT_2019 = 0.05
LAND_USE_2019 = -0.20


# ---------------------------------------------------------------------------
# Data assembly
# ---------------------------------------------------------------------------
@lru_cache(maxsize=None)
def emissions_history() -> pd.DataFrame:
    """Global annual emissions 1750-2019 (Mt/yr): CEDS 2020-09 updated, plus biomass burning."""
    return pd.read_csv(RAW / "emissions_ceds_update_plus_bb.csv", index_col="year")


def _concentration_series(col: str) -> pd.Series:
    """Annual concentrations 1750-2019; the source has 1750 and 1850+ only, so interpolate."""
    c = ar6_concentrations()[col].reindex(range(1750, 2020)).interpolate(limit_area="inside")
    return c.bfill().ffill() if col in ("CH3Cl", "CH3Br") else c.fillna(0.0)


def eesc_anomaly_series() -> pd.Series:
    """EESC (ppt of Cl-equivalent) relative to 1750, from the AR6 ODS concentration history.

    EESC = f_CFC11 * sum_i [ (n_Cl,i + 45 n_Br,i) * dC_i * f_i / f_CFC11 ]
    """
    out = pd.Series(0.0, index=range(1750, 2020))
    f11 = EESC_FRACREL["CFC11"]
    for col, sp in EESC_SPECIES.items():
        x = _concentration_series(col)
        d = x - x.iloc[0]
        out = out + (EESC_CL_ATOMS[sp] * d * EESC_FRACREL[sp] / f11
                     + EESC_BR_FACTOR * EESC_BR_ATOMS[sp] * d * EESC_FRACREL[sp] / f11) * f11
    return out


@dataclass(frozen=True)
class NonGhgParams:
    emis_1750: dict
    emis_2019: dict
    ari_beta: dict          # W m-2 per (Mt/yr)
    aci_n0: float           # SO2 shape factor, Mt/yr
    aci_n1: float           # BC+OC shape factor, Mt/yr
    ozone_coeff: dict       # CH4 [per ppb], N2O [per ppb], ODS [per ppt EESC], CO, VOC, NOx [per Mt/yr]
    ch4_1750: float
    n2o_1750: float
    ch4_2019: float
    n2o_2019: float
    eesc_2019: float
    ch4_erf_2019: float
    ar6_2019: dict          # AR6 best-estimate ERF in 2019 per agent id

    def to_json(self) -> dict:
        return {k: (dict(v) if isinstance(v, dict) else v) for k, v in self.__dict__.items()}


@lru_cache(maxsize=None)
def load_params() -> NonGhgParams:
    em = emissions_history()
    conc = ar6_concentrations()
    ar6 = ar6_erf("best").loc[2019]

    beta = {k: v / (em.loc[2005:2014, k].mean() - em.loc[1750, k]) for k, v in ARI_ASSESSED_2005_2014.items()}
    n0, n1 = ACI_N0_SO2, ACI_N1_BCOC  # fitted to the AR6 median ERFaci series (see constants.py)
    fit = pd.read_csv(RAW / "cmip6_ozone_skeie_fits.csv", index_col=0)["mean"]

    return NonGhgParams(
        emis_1750={k: float(em.loc[1750, k]) for k in EMIS_SPECIES},
        emis_2019={k: float(em.loc[2019, k]) for k in EMIS_SPECIES},
        ari_beta=beta, aci_n0=n0, aci_n1=n1,
        ozone_coeff={k: float(fit[k]) for k in ("CH4", "N2O", "ODS", "CO", "VOC", "NOx")},
        ch4_1750=float(conc.loc[1750, "CH4"]), n2o_1750=float(conc.loc[1750, "N2O"]),
        ch4_2019=float(conc.loc[2019, "CH4"]), n2o_2019=float(conc.loc[2019, "N2O"]),
        eesc_2019=float(eesc_anomaly_series().loc[2019]),
        ch4_erf_2019=float(ch4_forcing(conc.loc[2019, "CH4"], conc.loc[2019, "N2O"])),
        ar6_2019={
            "O3": float(ar6.o3), "H2O_strat": float(ar6.h2o_stratospheric), "Contrails": float(ar6.contrails),
            "Aerosol_ari": float(ar6["aerosol-radiation_interactions"]),
            "Aerosol_aci": float(ar6["aerosol-cloud_interactions"]),
            "BC_snow": float(ar6.bc_on_snow), "LandUse": float(ar6.land_use),
        },
    )


# ---------------------------------------------------------------------------
# Raw (un-normalised) emulators; every one is zero at 1750 drivers
# ---------------------------------------------------------------------------
def _emis(p: NonGhgParams, state: dict) -> dict:
    """Absolute emissions (Mt/yr) from multiples of 2019."""
    return {k: p.emis_2019[k] * state.get(k.lower(), 1.0) for k in EMIS_SPECIES}


def _raw_ari(p: NonGhgParams, E: dict) -> float:
    """Aerosol-radiation: linear in emissions (Smith et al., AR6 Ch. 6/7). Exact vs AR6 series."""
    return sum(p.ari_beta[k] * (E[k] - p.emis_1750[k]) for k in p.ari_beta)


def _aci_log(p: NonGhgParams, E: dict) -> float:
    return float(np.log(1.0 + E["SO2"] / p.aci_n0 + (E["BC"] + E["OC"]) / p.aci_n1))


def _raw_aci(p: NonGhgParams, E: dict) -> float:
    """Aerosol-cloud: -[ln(1 + SO2/n0 + (BC+OC)/n1) - same at 1750] (Ghan 2013 form).

    Saturating: the first emissions matter most, so cutting SO2 from today's level removes
    cooling more slowly than the pre-industrial build-up added it.
    """
    return -(_aci_log(p, E) - _aci_log(p, p.emis_1750))


def _raw_bc_snow(p: NonGhgParams, E: dict) -> float:
    return E["BC"] - p.emis_1750["BC"]


def _eesc(p: NonGhgParams, state: dict) -> float:
    return p.eesc_2019 * state.get("ods", 1.0)


def _raw_ozone(p: NonGhgParams, E: dict, state: dict) -> float:
    """Total (tropospheric + stratospheric) ozone ERF emulator, Skeie et al. (2020) fit.

    ERF = r_CH4 dCH4 + r_N2O dN2O + r_ODS dEESC + r_CO dCO + r_VOC dVOC + r_NOx dNOx
    (the ODS term is negative: chlorine/bromine destroy stratospheric ozone).
    """
    c = p.ozone_coeff
    ch4 = state.get("ch4", p.ch4_2019)
    n2o = state.get("n2o", p.n2o_2019)
    return (c["CH4"] * (ch4 - p.ch4_1750) + c["N2O"] * (n2o - p.n2o_1750)
            + c["ODS"] * _eesc(p, state)
            + c["CO"] * (E["CO"] - p.emis_1750["CO"]) + c["VOC"] * (E["VOC"] - p.emis_1750["VOC"])
            + c["NOx"] * (E["NOx"] - p.emis_1750["NOx"]))


def raw_terms(state: dict | None = None, p: NonGhgParams | None = None) -> dict:
    """Un-normalised emulator outputs for a driver state (see module docstring)."""
    p, state = p or load_params(), state or {}
    E = _emis(p, state)
    return {"Aerosol_ari": _raw_ari(p, E), "Aerosol_aci": _raw_aci(p, E),
            "BC_snow": _raw_bc_snow(p, E), "O3": _raw_ozone(p, E, state)}


def non_ghg_erf(state: dict | None = None, p: NonGhgParams | None = None) -> dict:
    """ERF (W m-2, vs 1750) of the non-CO2/CH4/N2O agents for a driver state.

    Keys: O3, H2O_strat, Contrails, Aerosol_ari, Aerosol_aci, BC_snow, LandUse.
    """
    p, state = p or load_params(), state or {}
    now, ref = raw_terms(state, p), raw_terms({}, p)
    out = {k: p.ar6_2019[k] * now[k] / ref[k] for k in now}
    ch4 = state.get("ch4", p.ch4_2019)
    n2o = state.get("n2o", p.n2o_2019)
    # AR6: stratospheric H2O ERF is proportional to the CH4 ERF (0.05 W m-2 in 2019)
    out["H2O_strat"] = p.ar6_2019["H2O_strat"] * float(ch4_forcing(ch4, n2o)) / p.ch4_erf_2019
    out["Contrails"] = p.ar6_2019["Contrails"] * state.get("contrails", 1.0)
    out["LandUse"] = p.ar6_2019["LandUse"] * state.get("landuse", 1.0)
    return out


def historical_state(year: int, p: NonGhgParams | None = None) -> dict:
    """Driver state for a historical year (1750-2019), for validation against AR6."""
    p = p or load_params()
    em = emissions_history().loc[year]
    st = {k.lower(): float(em[k]) / p.emis_2019[k] for k in EMIS_SPECIES}
    st["ods"] = float(eesc_anomaly_series().loc[year]) / p.eesc_2019
    st["ch4"] = float(_concentration_series("CH4").loc[year])
    st["n2o"] = float(_concentration_series("N2O").loc[year])
    return st


def preindustrial_state(p: NonGhgParams | None = None) -> dict:
    """Driver state with every driver at its 1750 value."""
    p = p or load_params()
    st = {k.lower(): p.emis_1750[k] / p.emis_2019[k] for k in EMIS_SPECIES}
    st.update(ods=0.0, ch4=p.ch4_1750, n2o=p.n2o_1750, landuse=0.0, contrails=0.0)
    return st
