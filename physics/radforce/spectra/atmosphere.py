"""An idealised clear-sky model atmosphere for the spectral and forcing calculations.

Temperature and pressure: U.S. Standard Atmosphere 1976 (NOAA/NASA/USAF), 0-86 km.
Water vapour: fixed relative-humidity profile of Manabe & Wetherald (1967) in the
troposphere, constant 5 ppmv above the tropopause.
Ozone: idealised log-linear profile scaled to a chosen column in Dobson units.
CH4, N2O: constant in the troposphere, decaying exponentially above the tropopause
(idealised stratospheric loss).  CO2: well mixed.

These are teaching profiles, deliberately simple and documented; they are not a
substitute for a measured profile or for a reanalysis climatology.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# --- physical constants -------------------------------------------------------
G0 = 9.80665                 # m s-2
R_STAR = 8.31432             # J mol-1 K-1 (value used by the 1976 standard)
M_AIR = 0.0289644            # kg mol-1
N_A = 6.02214076e23          # mol-1
P0 = 101325.0                # Pa
DU = 2.6867e16               # molecules cm-2 per Dobson unit

# U.S. Standard Atmosphere 1976: geopotential base height (km), base temperature (K), lapse (K/km)
_BASE_H = np.array([0.0, 11.0, 20.0, 32.0, 47.0, 51.0, 71.0])
_BASE_T = np.array([288.15, 216.65, 216.65, 228.65, 270.65, 270.65, 214.65])
_LAPSE = np.array([-6.5, 0.0, 1.0, 2.8, 0.0, -2.8, -2.0])
_BASE_P = [P0]
for _i in range(len(_LAPSE)):
    _dz = 1000.0 * ((_BASE_H[_i + 1] if _i + 1 < len(_BASE_H) else 84.852) - _BASE_H[_i])
    _L = _LAPSE[_i] / 1000.0
    _T0 = _BASE_T[_i]
    if abs(_L) < 1e-12:
        _BASE_P.append(_BASE_P[-1] * np.exp(-G0 * M_AIR * _dz / (R_STAR * _T0)))
    else:
        _BASE_P.append(_BASE_P[-1] * ((_T0 + _L * _dz) / _T0) ** (-G0 * M_AIR / (R_STAR * _L)))
_BASE_P = np.array(_BASE_P[: len(_BASE_H)])

TROPOPAUSE_KM = 11.0


def temperature(z_km):
    """US Standard 1976 temperature (K) at geopotential height ``z_km`` (0-71 km here)."""
    z = np.asarray(z_km, dtype=float)
    i = np.clip(np.searchsorted(_BASE_H, z, side="right") - 1, 0, len(_BASE_H) - 1)
    return _BASE_T[i] + _LAPSE[i] * (z - _BASE_H[i])


def pressure(z_km):
    """US Standard 1976 pressure (Pa) at geopotential height ``z_km`` (0-71 km here)."""
    z = np.asarray(z_km, dtype=float)
    i = np.clip(np.searchsorted(_BASE_H, z, side="right") - 1, 0, len(_BASE_H) - 1)
    dz = 1000.0 * (z - _BASE_H[i])
    L = _LAPSE[i] / 1000.0
    T0 = _BASE_T[i]
    iso = np.abs(L) < 1e-12
    with np.errstate(divide="ignore", invalid="ignore"):
        poly = _BASE_P[i] * ((T0 + L * dz) / T0) ** (-G0 * M_AIR / (R_STAR * np.where(iso, 1.0, L)))
    expo = _BASE_P[i] * np.exp(-G0 * M_AIR * dz / (R_STAR * T0))
    return np.where(iso, expo, poly)


def saturation_vapour_pressure(T):
    """Saturation vapour pressure over liquid water (Pa), Bolton (1980); adequate for T > ~230 K."""
    T = np.asarray(T, dtype=float)
    return 611.2 * np.exp(17.67 * (T - 273.15) / (T - 29.65))


# idealised ozone mixing ratio profile (height km, ppmv); shape only, scaled to the requested column
_O3_Z = np.array([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60.0])
_O3_PPMV = np.array([0.03, 0.05, 0.15, 0.5, 2.0, 5.5, 8.0, 8.2, 5.5, 3.0, 1.8, 0.6])

DEFAULT_LAYER_EDGES_KM = (0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 24, 28, 32, 36, 40, 45, 50, 60)


@dataclass
class Layers:
    """Plane-parallel layers: mid-layer p (Pa), T (K), z (km) and molecule column amounts (cm-2)."""
    z_edges_km: np.ndarray
    z_mid_km: np.ndarray
    p_mid: np.ndarray
    p_top: np.ndarray
    p_bottom: np.ndarray
    T_mid: np.ndarray
    n_air: np.ndarray                 # total air column per layer, molecules cm-2
    columns: dict = field(default_factory=dict)   # gas -> molecules cm-2 per layer
    vmr: dict = field(default_factory=dict)       # gas -> volume mixing ratio per layer
    T_surface: float = 288.15


def air_column(p_bottom, p_top):
    """Air molecules per cm2 between two pressures (Pa): (p_b - p_t)/(M g) * N_A, per m2 -> cm2."""
    return (np.asarray(p_bottom) - np.asarray(p_top)) / (M_AIR * G0) * N_A / 1.0e4


def build_layers(co2_ppm=409.85, ch4_ppb=1866.3, n2o_ppb=332.1, o3_du=300.0, rh_surface=0.77,
                 h2o_scale=1.0, edges_km=DEFAULT_LAYER_EDGES_KM) -> Layers:
    """US Standard atmosphere with the stated gas amounts (defaults: AR6 2019 mixing ratios)."""
    e = np.asarray(edges_km, dtype=float)
    z_mid = 0.5 * (e[:-1] + e[1:])
    p_edges = pressure(e)
    p_mid = pressure(z_mid)
    T_mid = temperature(z_mid)
    n_air = air_column(p_edges[:-1], p_edges[1:])
    ps = p_edges[0]

    # water vapour: Manabe-Wetherald fixed RH in the troposphere, 5 ppmv floor above
    rh = rh_surface * np.clip((p_mid / ps - 0.02) / 0.98, 0.0, None)
    x_h2o = rh * saturation_vapour_pressure(T_mid) / p_mid
    x_h2o = np.where(z_mid < TROPOPAUSE_KM, x_h2o, 5.0e-6)
    x_h2o = np.maximum(x_h2o, 5.0e-6) * h2o_scale

    strat = np.clip(z_mid - TROPOPAUSE_KM, 0.0, None)
    x = {
        "CO2": np.full_like(z_mid, co2_ppm * 1e-6),
        "CH4": ch4_ppb * 1e-9 * np.exp(-strat / 15.0),
        "N2O": n2o_ppb * 1e-9 * np.exp(-strat / 9.0),
        "H2O": x_h2o,
    }
    o3 = np.interp(z_mid, _O3_Z, _O3_PPMV) * 1e-6
    scale = o3_du * DU / float(np.sum(o3 * n_air))
    x["O3"] = o3 * scale
    cols = {g: x[g] * n_air for g in x}
    return Layers(e, z_mid, p_mid, p_edges[1:], p_edges[:-1], T_mid, n_air, cols, x, float(temperature(0.0)))
