"""Forcing of the three main well-mixed greenhouse gases: CO2, CH4, N2O.

Three published parameterisations are provided so students can compare how the
science evolved:

``"myhre1998"``        IPCC TAR / AR4 (Myhre et al. 1998).  CO2 is 5.35 ln(C/C0);
                       CH4 and N2O carry a CH4-N2O overlap term.  No CO2 overlap.
``"etminan2016"``      IPCC AR5 update (Etminan et al. 2016): adds CO2-N2O
                       overlap, stronger CH4 forcing, curvature in CO2 forcing.
                       Valid for 180-2000 ppm CO2, 340-3500 ppb CH4,
                       200-525 ppb N2O.
``"meinshausen2020"``  IPCC AR6 default: a re-fit of Etminan that remains
                       well behaved outside that range (e.g. high-CO2 worlds).

All functions return W m-2 relative to the baseline concentrations.

Instantaneous vs effective forcing
----------------------------------
The expressions above give a *stratospheric-temperature-adjusted* forcing
(SARF, essentially the IRF after the stratosphere has equilibrated).  Setting
``erf=True`` multiplies by the AR6 tropospheric-adjustment factors
(CO2 +5 %, CH4 -14 %, N2O +7 %; AR6 Sect. 7.3.2) to obtain the *effective*
radiative forcing.  ``erf=False`` returns the SARF.  For ``myhre1998`` no
adjustment factors have been published for that fit, so ``erf=True`` is
rejected rather than silently mixing frameworks.

Units: CO2 in ppm, CH4 and N2O in ppb.  Inputs may be scalars or numpy arrays
and broadcast together.
"""
from __future__ import annotations

import numpy as np

from ..constants import (
    ERF_FROM_SARF,
    ETMINAN2016,
    MEINSHAUSEN2020,
    MYHRE1998,
    PREINDUSTRIAL_1750,
)

SCHEMES = ("meinshausen2020", "etminan2016", "myhre1998")


def _baseline(baseline):
    b = dict(PREINDUSTRIAL_1750)
    if baseline:
        b.update(baseline)
    return b["CO2"], b["CH4"], b["N2O"]


def _check(scheme: str, erf: bool) -> None:
    if scheme not in SCHEMES:
        raise ValueError(f"unknown scheme {scheme!r}; choose from {SCHEMES}")
    if erf and scheme == "myhre1998":
        raise ValueError(
            "No published ERF adjustment factors exist for the Myhre (1998) fit; "
            "use erf=False or a different scheme."
        )


def _factor(gas: str, erf: bool) -> float:
    return ERF_FROM_SARF[gas] if erf else 1.0


# ----------------------------------------------------------------------------
# Myhre et al. (1998) overlap function f(M, N)
# ----------------------------------------------------------------------------
def overlap_f(M, N, p: dict | None = None):
    """CH4-N2O spectral-overlap function of Myhre et al. (1998), W m-2.

    f(M,N) = 0.47 ln[1 + 2.01e-5 (M N)^0.75 + 5.31e-15 M (M N)^1.52]
    with M, N in ppb.  It is subtracted from the square-root terms so that the
    two gases are not double counted where their bands (near 7.7-7.8 um) overlap.
    """
    p = p or MYHRE1998
    M = np.asarray(M, dtype=float)
    N = np.asarray(N, dtype=float)
    return p["alpha_overlap"] * np.log(
        1.0 + p["a1"] * (M * N) ** p["exp1"] + p["a2"] * M * (M * N) ** p["exp2"]
    )


# ----------------------------------------------------------------------------
# Individual gases
# ----------------------------------------------------------------------------
def co2_forcing(C, N2O=None, *, scheme="meinshausen2020", erf=True, baseline=None):
    """CO2 forcing in W m-2 for concentration ``C`` (ppm).

    ``N2O`` (ppb, default = baseline value) is used for the CO2-N2O overlap in
    the Etminan and Meinshausen schemes.
    """
    _check(scheme, erf)
    C0, _, N0 = _baseline(baseline)
    C = np.asarray(C, dtype=float)
    N = np.asarray(N0 if N2O is None else N2O, dtype=float)
    if scheme == "myhre1998":
        return MYHRE1998["alpha_co2"] * np.log(C / C0)

    dC = C - C0
    if scheme == "etminan2016":
        p = ETMINAN2016
        # N-bar is the mean of present and reference N2O (ppb)
        coeff = p["a1"] * dC**2 + p["b1"] * np.abs(dC) + p["c1"] * 0.5 * (N + N0) + p["d1"]
        return coeff * np.log(C / C0) * _factor("CO2", erf)

    p = MEINSHAUSEN2020
    # The quadratic in (C - C0) peaks at dC_max; beyond it the coefficient is
    # held constant so forcing keeps increasing logarithmically (monotonic).
    dC_max = -p["b1"] / (2.0 * p["a1"])
    alpha = np.where(
        dC <= 0.0,
        p["d1"],
        np.where(
            dC <= dC_max,
            p["d1"] + p["a1"] * dC**2 + p["b1"] * dC,
            p["d1"] - p["b1"] ** 2 / (4.0 * p["a1"]),
        ),
    )
    return (alpha + p["c1"] * np.sqrt(N)) * np.log(C / C0) * _factor("CO2", erf)


def ch4_forcing(M, N2O=None, *, scheme="meinshausen2020", erf=True, baseline=None):
    """CH4 forcing in W m-2 for concentration ``M`` (ppb)."""
    _check(scheme, erf)
    _, M0, N0 = _baseline(baseline)
    M = np.asarray(M, dtype=float)
    N = np.asarray(N0 if N2O is None else N2O, dtype=float)
    if scheme == "myhre1998":
        p = MYHRE1998
        return p["alpha_ch4"] * (np.sqrt(M) - np.sqrt(M0)) - (
            overlap_f(M, N0) - overlap_f(M0, N0)
        )
    if scheme == "etminan2016":
        p = ETMINAN2016
        coeff = p["a3"] * 0.5 * (M + M0) + p["b3"] * 0.5 * (N + N0) + p["d3"]
    else:
        p = MEINSHAUSEN2020
        coeff = p["a3"] * np.sqrt(M) + p["b3"] * np.sqrt(N) + p["d3"]
    return coeff * (np.sqrt(M) - np.sqrt(M0)) * _factor("CH4", erf)


def n2o_forcing(N, CO2=None, CH4=None, *, scheme="meinshausen2020", erf=True, baseline=None):
    """N2O forcing in W m-2 for concentration ``N`` (ppb)."""
    _check(scheme, erf)
    C0, M0, N0 = _baseline(baseline)
    N = np.asarray(N, dtype=float)
    C = np.asarray(C0 if CO2 is None else CO2, dtype=float)
    M = np.asarray(M0 if CH4 is None else CH4, dtype=float)
    if scheme == "myhre1998":
        p = MYHRE1998
        return p["alpha_n2o"] * (np.sqrt(N) - np.sqrt(N0)) - (
            overlap_f(M0, N) - overlap_f(M0, N0)
        )
    if scheme == "etminan2016":
        p = ETMINAN2016
        coeff = (
            p["a2"] * 0.5 * (C + C0)
            + p["b2"] * 0.5 * (N + N0)
            + p["c2"] * 0.5 * (M + M0)
            + p["d2"]
        )
    else:
        p = MEINSHAUSEN2020
        coeff = p["a2"] * np.sqrt(C) + p["b2"] * np.sqrt(N) + p["c2"] * np.sqrt(M) + p["d2"]
    return coeff * (np.sqrt(N) - np.sqrt(N0)) * _factor("N2O", erf)


# ----------------------------------------------------------------------------
# Combined
# ----------------------------------------------------------------------------
def wmghg_forcing(CO2, CH4, N2O, *, scheme="meinshausen2020", erf=True, baseline=None):
    """Forcing of CO2, CH4 and N2O together, as a dict of W m-2 values.

    Keys: ``CO2``, ``CH4``, ``N2O`` and ``total`` (their sum).  The overlap
    terms make each gas's forcing depend on the other two concentrations, so
    the split between gases is a convention (the same one AR6 uses).
    """
    out = {
        "CO2": co2_forcing(CO2, N2O, scheme=scheme, erf=erf, baseline=baseline),
        "CH4": ch4_forcing(CH4, N2O, scheme=scheme, erf=erf, baseline=baseline),
        "N2O": n2o_forcing(N2O, CO2, CH4, scheme=scheme, erf=erf, baseline=baseline),
    }
    out["total"] = out["CO2"] + out["CH4"] + out["N2O"]
    return out
