"""Water-vapour continuum: MT_CKD 4.3 (Mlawer et al. 2012, Phil. Trans. R. Soc. A 370, 2520).

Implements the scaling used by the AER reference code (github.com/AER-RC/MT_CKD_H2O, ``mt_ckd_h2o_module.f90``):

    C_self(nu) = C_self_ref(nu) (T_ref/T)^texp(nu) x_h2o rho_rat
    C_for (nu) = C_for_ref(nu)               (1 - x_h2o) rho_rat
    rho_rat    = (p / p_ref)(T_ref / T),   p_ref = 1013 mbar, T_ref = 296 K
    sigma(nu)  = (C_self + C_for) R(nu, T),   R = nu tanh(h c nu / 2 k T)   [cm2 per H2O molecule]

so the continuum optical depth of a layer is sigma x (H2O molecules cm-2).  The reference coefficients
(2003 points, 10 cm-1 spacing) are interpolated with a cubic spline in wavenumber.

The continuum is *defined relative to water-vapour lines cut off 25 cm-1 from line centre* (as in LBLRTM), so the
line-by-line H2O cross-sections used with it must use the same 25 cm-1 cut-off (``lbl.cross_section(..., wing_hw=1e3)``).

Data licence (data/raw/mtckd/LICENSE.md): free for scientific and research use, redistribution allowed with the
AER copyright notice reproduced and acknowledgement given; not to be incorporated into commercial software.
Acknowledgement: Atmospheric and Environmental Research, Inc. (AER), MT_CKD_H2O 4.3.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "raw" / "mtckd" / "absco-ref_wv-mt-ckd.nc"
RADCN2 = 1.4387752       # second radiation constant hc/k, cm K (as in the reference code)


@lru_cache(maxsize=1)
def _reference():
    from scipy.interpolate import CubicSpline
    from scipy.io import netcdf_file

    with netcdf_file(str(DATA), mmap=False) as f:
        wv = np.array(f.variables["wavenumbers"][:], dtype=float)
        out = {
            "self": CubicSpline(wv, np.array(f.variables["self_absco_ref"][:], dtype=float)),
            "foreign": CubicSpline(wv, np.array(f.variables["for_absco_ref"][:], dtype=float)),
            "texp": CubicSpline(wv, np.array(f.variables["self_texp"][:], dtype=float)),
            "p_ref": float(f.variables["ref_press"].getValue()),
            "T_ref": float(f.variables["ref_temp"].getValue()),
            "range": (float(wv[0]), float(wv[-1])),
        }
    return out


def available() -> bool:
    return DATA.exists()


def radiation_term(nu, T):
    """R(nu, T) = nu tanh(nu / 2 xkt) with xkt = T / 1.4387752 (cm-1); exact tanh form of the reference code."""
    nu = np.asarray(nu, dtype=float)
    return nu * np.tanh(nu * RADCN2 / (2.0 * T))


def sigma(nu, T: float, p_pa: float, x_h2o: float):
    """Continuum absorption cross-section, cm2 per H2O molecule, on wavenumbers ``nu`` (cm-1)."""
    ref = _reference()
    nu = np.asarray(nu, dtype=float)
    p_mbar = p_pa / 100.0
    rho_rat = (p_mbar / ref["p_ref"]) * (ref["T_ref"] / T)
    c_self = ref["self"](nu) * (ref["T_ref"] / T) ** ref["texp"](nu) * x_h2o * rho_rat
    c_for = ref["foreign"](nu) * (1.0 - x_h2o) * rho_rat
    return np.clip(c_self + c_for, 0.0, None) * radiation_term(nu, T)
