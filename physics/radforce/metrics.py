"""Emission metrics: absolute and relative global warming and temperature-change potentials.

Implements the method behind IPCC AR6 WG1 Table 7.SM.7 (Forster et al. 2021, Section 7.6.1; Collins et al. 2013;
Hodnebrog et al. 2020 for the halocarbon inputs), rewritten here from the published equations.

For a 1 kg pulse of gas X at time zero:

* radiative forcing  F_X(t)  = A_X * exp(-t / tau_X)                          (single-exponential decay)
* AGWP_X(H)          = integral_0^H F_X(t) dt = A_X * tau_X * (1 - exp(-H / tau_X))
* AGTP_X(H)          = sum_j q_j integral_0^H F_X(s) exp(-(H - s) / d_j) / d_j ds   (two-timescale warming response)
* GWP_X(H) = AGWP_X(H) / AGWP_CO2(H),   GTP_X(H) = AGTP_X(H) / AGTP_CO2(H)

where A_X = RE_X / (kg of X per ppb) is the forcing per kg.  CO2 uses the multi-box impulse-response function of
Joos et al. (2013).  For every gas except CO2 the temperature change also feeds back on the carbon cycle
(Gasser et al. 2017), which adds a small CO2 pulse; AR6 includes this "climate-carbon feedback" and so does this
module.  CH4 and N2O carry the extra terms AR6 adds (ozone and stratospheric water vapour for CH4, ozone and the
CH4 lifetime change for N2O).  Everything is units of W m-2 yr kg-1 (AGWP) and K kg-1 (AGTP).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from .data import RAW
from .forcing import wmghg

# --- constants (as used for AR6 Table 7.SM.7) -----------------------------------------------------------------
M_ATMOS = 5.1352e18        # kg, mass of the atmosphere
M_AIR = 28.97e-3           # kg mol-1
M_CO2, M_C, M_CH4, M_N2O = 44.01e-3, 12.0e-3, 16.043e-3, 44.0e-3

# baseline atmosphere (AR6 2019), ppm / ppb / ppb
BASE_CO2, BASE_CH4, BASE_N2O = 409.9, 1866.3, 332.1

# climate response to forcing: impulse response T(t) = sum_j q_j/d_j exp(-t/d_j)  (K per W m-2 yr)
Q_RESP = np.array([0.443767728883447, 0.313998206372015])   # K (W m-2)-1
D_RESP = np.array([3.424102092311, 285.003477841911])       # yr

# CO2 impulse response (Joos et al. 2013): partition fractions and time constants (inf = permanent)
CO2_A = np.array([0.2173, 0.2240, 0.2824, 0.2763])
CO2_TAU = np.array([np.inf, 394.4, 36.54, 4.304])

# climate-carbon feedback (Gasser et al. 2017)
GASSER_A = np.array([0.6368, 0.3322, 0.0310])
GASSER_TAU = np.array([2.376, 30.14, 490.1])
GASSER_GAMMA = 3.015e12     # kg CO2 yr-1 K-1

# AR6 tropospheric adjustments and indirect terms
CO2_RA, CH4_RA, N2O_RA = 0.05, -0.14, 0.07
CH4_O3, CH4_H2O = 1.4e-4, 4.0e-5          # W m-2 ppb-1 added to the CH4 radiative efficiency
N2O_O3 = 5.5e-4                           # W m-2 ppb-1, ozone effect of N2O
F_N2O_CH4 = -1.7                          # ppb CH4 per ppb N2O: N2O lengthens the CH4 lifetime
TAU_CH4, TAU_N2O = 11.8, 109.0
DT = 0.1                                  # yr, time step of the convolution
H_MAX = 500


def time_grid() -> np.ndarray:
    return np.arange(0, H_MAX + 0.5 * DT, DT)


# --- molar masses from formulae ---------------------------------------------------------------------------------
_ATOMIC = {"H": 1.008, "C": 12.011, "N": 14.007, "O": 15.999, "F": 18.998, "S": 32.06, "Cl": 35.45, "Br": 79.904, "I": 126.904}
_TOKEN = re.compile(r"([A-Z][a-z]?)(\d*)|(\()|(\))(\d*)")


def molar_mass(formula: str) -> float:
    """Molar mass in kg mol-1 from a chemical formula (handles groups in parentheses and stereo prefixes)."""
    f = re.sub(r"^(trans|cis)\s+cyc\s*", "", formula.strip())
    f = re.sub(r"^\((?:E|Z|E/Z)\)-", "", f)
    f = f.replace("=", "").replace("-", "").replace(" ", "")
    stack: list[float] = [0.0]
    for m in _TOKEN.finditer(f):
        el, n, op, cl, k = m.groups()
        if el:
            if el not in _ATOMIC:
                raise ValueError(f"unknown element {el!r} in {formula!r}")
            stack[-1] += _ATOMIC[el] * (int(n) if n else 1)
        elif op:
            stack.append(0.0)
        elif cl:
            s = stack.pop()
            stack[-1] += s * (int(k) if k else 1)
    if len(stack) != 1:
        raise ValueError(f"unbalanced parentheses in {formula!r}")
    return stack[0] * 1e-3


def kg_per_ppb(mass_kg_mol: float) -> float:
    """Mass of the atmosphere's trace gas in a 1 ppb (mole fraction) enhancement, kg."""
    return 1e-9 * (mass_kg_mol / M_AIR) * M_ATMOS


# --- building blocks ----------------------------------------------------------------------------------------------
def _decay_responses(H: np.ndarray, tau: float, A: float):
    """RF, AGWP, AGTP, integrated AGTP of a single-exponential pulse of forcing amplitude A (per kg)."""
    rf = A * np.exp(-H / tau)
    agwp = A * tau * (1 - np.exp(-H / tau))
    agtp = np.zeros_like(H)
    iagtp = np.zeros_like(H)
    for q, d in zip(Q_RESP, D_RESP):
        agtp += A * tau * q * (np.exp(-H / tau) - np.exp(-H / d)) / (tau - d)
        iagtp += A * tau * q * (tau * (1 - np.exp(-H / tau)) - d * (1 - np.exp(-H / d))) / (tau - d)
    return rf, agwp, agtp, iagtp


def co2_re() -> float:
    """CO2 radiative efficiency per ppm at the AR6 baseline, W m-2 ppm-1, including the +5 % adjustment."""
    base = {"CO2": BASE_CO2, "CH4": BASE_CH4, "N2O": BASE_N2O}
    f1 = wmghg.co2_forcing(BASE_CO2 + 1.0, BASE_N2O, erf=False, baseline=base)
    return float(f1) * (1 + CO2_RA)


def _per_ppb_derivative(gas: str) -> float:
    """Unadjusted radiative efficiency per ppb of CH4 or N2O at the AR6 baseline, W m-2 ppb-1."""
    base = {"CO2": BASE_CO2, "CH4": BASE_CH4, "N2O": BASE_N2O}
    if gas == "CH4":
        return float(wmghg.ch4_forcing(BASE_CH4 + 1.0, BASE_N2O, erf=False, baseline=base))
    return float(wmghg.n2o_forcing(BASE_N2O + 1.0, BASE_CO2, BASE_CH4, erf=False, baseline=base))


@lru_cache(maxsize=1)
def co2_response():
    """RF, AGWP, AGTP and integrated AGTP of 1 kg of CO2 on the time grid."""
    H = time_grid()
    A = co2_re() / (1e-6 * (M_CO2 / M_AIR) * M_ATMOS)
    rf = np.zeros_like(H)
    agwp = np.zeros_like(H)
    agtp = np.zeros_like(H)
    iagtp = np.zeros_like(H)
    rf += A * CO2_A[0]
    agwp += A * CO2_A[0] * H
    for j, (q, d) in enumerate(zip(Q_RESP, D_RESP)):
        agtp += A * CO2_A[0] * q * (1 - np.exp(-H / d))
        iagtp += A * CO2_A[0] * q * (H - d * (1 - np.exp(-H / d)))
        for a, tau in zip(CO2_A[1:], CO2_TAU[1:]):
            if j == 0:
                rf += A * a * np.exp(-H / tau)
                agwp += A * a * tau * (1 - np.exp(-H / tau))
            agtp += A * a * tau * q * (np.exp(-H / tau) - np.exp(-H / d)) / (tau - d)
            iagtp += A * a * tau * q * (tau * (1 - np.exp(-H / tau)) - d * (1 - np.exp(-H / d))) / (tau - d)
    return rf, agwp, agtp, iagtp


def carbon_cycle_adjustment(agtp: np.ndarray):
    """Extra RF, AGWP and AGTP from the carbon released by the warming that a gas causes (Gasser et al. 2017)."""
    H = time_grid()
    rf_c, agwp_c, agtp_c, _ = co2_response()
    r = np.zeros_like(H)
    r[0] = GASSER_A.sum() / DT
    for a, tau in zip(GASSER_A, GASSER_TAU):
        r -= (a / tau) * np.exp(-H / tau)
    n = H.size
    flux = np.convolve(agtp, r)[:n] * GASSER_GAMMA * DT            # kg CO2 yr-1 per kg of gas
    scale = M_CO2 / M_C                                             # as in the AR6 implementation
    return tuple(np.convolve(flux, x)[:n] * DT * scale for x in (rf_c, agwp_c, agtp_c))


@dataclass(frozen=True)
class Metrics:
    """Absolute metrics on the 0.1 yr grid (index = H / 0.1)."""
    agwp: np.ndarray
    agtp: np.ndarray

    def at(self, H: float) -> tuple[float, float]:
        i = int(round(H / DT))
        return float(self.agwp[i]), float(self.agtp[i])


def _total(parts_agwp, parts_agtp, with_cc: bool, agtp_for_cc):
    agwp, agtp = parts_agwp, parts_agtp
    if with_cc:
        _, agwp_c, agtp_c = carbon_cycle_adjustment(agtp_for_cc)
        agwp = agwp + agwp_c
        agtp = agtp + agtp_c
    return Metrics(agwp, agtp)


def co2_metrics() -> Metrics:
    _, agwp, agtp, _ = co2_response()
    return Metrics(agwp, agtp)


def methane_metrics(*, climate_carbon_feedback: bool = True) -> Metrics:
    """CH4 with the +/- AR6 terms: -14 % adjustment, ozone and stratospheric water vapour."""
    H = time_grid()
    re_ = _per_ppb_derivative("CH4") * (1 + CH4_RA) + CH4_O3 + CH4_H2O
    A = re_ / kg_per_ppb(M_CH4)
    _, agwp, agtp, _ = _decay_responses(H, TAU_CH4, A)
    return _total(agwp, agtp, climate_carbon_feedback, agtp)


def nitrous_oxide_metrics(*, climate_carbon_feedback: bool = True) -> Metrics:
    """N2O with its +7 % adjustment, ozone term and the shortening-then-lengthening of the CH4 lifetime."""
    H = time_grid()
    re_n2o = _per_ppb_derivative("N2O") * (1 + N2O_RA) + N2O_O3
    re_ch4 = _per_ppb_derivative("CH4") * (1 + CH4_RA) + CH4_O3 + CH4_H2O
    A = (re_n2o + F_N2O_CH4 * re_ch4) / kg_per_ppb(M_N2O)
    _, agwp, agtp, _ = _decay_responses(H, TAU_N2O, A)
    return _total(agwp, agtp, climate_carbon_feedback, agtp)


def halogen_metrics(lifetime: float, radiative_efficiency: float, mass: float, *,
                    climate_carbon_feedback: bool = True) -> Metrics:
    """A halogenated gas: ``radiative_efficiency`` in W m-2 ppb-1 (already including any adjustment)."""
    H = time_grid()
    A = radiative_efficiency / kg_per_ppb(mass)
    _, agwp, agtp, _ = _decay_responses(H, lifetime, A)
    return _total(agwp, agtp, climate_carbon_feedback, agtp)


def gwp(m: Metrics, horizon: float) -> float:
    return m.at(horizon)[0] / co2_metrics().at(horizon)[0]


def gtp(m: Metrics, horizon: float) -> float:
    return m.at(horizon)[1] / co2_metrics().at(horizon)[1]


# --- the AR6 species list -------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Species:
    name: str
    acronym: str
    formula: str
    lifetime: float | None
    re: float | None            # W m-2 ppb-1 (AR6, includes the 12 % CFC-11/12 adjustment)
    mass: float | None          # kg mol-1, from the formula
    ar6: dict                   # AR6 Table 7.SM.7 values for comparison


def ar6_species() -> list[Species]:
    """All species of AR6 Table 7.SM.7 (CO2, CH4, N2O and 246 halogenated gases)."""
    import pandas as pd
    df = pd.read_csv(RAW / "metrics_supplement_cleaned.csv")
    out = []
    for _, r in df.iterrows():
        f = str(r["Formula"])
        life = None if pd.isna(r["Lifetime (yr)"]) else float(r["Lifetime (yr)"])
        re_ = None if pd.isna(r["Radiative efficiency (W m-2 ppb-1)"]) else float(r["Radiative efficiency (W m-2 ppb-1)"])
        ar6 = {k: (None if pd.isna(r[c]) else float(r[c])) for k, c in
               [("GWP20", "GWP20"), ("GWP100", "GWP100"), ("GWP500", "GWP500"), ("GTP50", "GTP50"), ("GTP100", "GTP100"),
                ("AGWP100", "AGWP100 (W m-2 yr kg-1)")]}
        try:
            mass = molar_mass(f)
        except ValueError:
            mass = None
        acr = "" if pd.isna(r["Acronym"]) else str(r["Acronym"])
        out.append(Species(str(r["Name"]), acr, f, life, re_, mass, ar6))
    return out


def species_metrics(sp: Species, *, climate_carbon_feedback: bool = True) -> Metrics | None:
    if sp.formula == "CO2":
        return co2_metrics()
    if sp.formula == "CH4":
        return methane_metrics(climate_carbon_feedback=climate_carbon_feedback)
    if sp.formula == "N2O":
        return nitrous_oxide_metrics(climate_carbon_feedback=climate_carbon_feedback)
    if sp.lifetime is None or sp.lifetime <= 0 or sp.re is None or sp.mass is None:
        return None
    return halogen_metrics(sp.lifetime, sp.re, sp.mass, climate_carbon_feedback=climate_carbon_feedback)
