"""Planck blackbody emission in wavenumber space.

All spectral quantities are per unit WAVENUMBER (cm-1), the natural variable for
molecular spectra.  SI constants are the exact 2019 SI-redefinition values.
"""
from __future__ import annotations

import numpy as np

H = 6.62607015e-34      # J s
C = 299792458.0         # m s-1
KB = 1.380649e-23       # J K-1
SIGMA_SB = 5.670374419e-8  # W m-2 K-4 (derived: 2 pi^5 k^4 / 15 h^3 c^2)

# Wien displacement in wavenumber space: sigma_max = 1.5985... K^-1 cm-1 * T  (x = 2.821439...)
WIEN_X_WAVENUMBER = 2.821439372122079


def radiance(nu_cm, T):
    """Spectral radiance B(nu, T) in W m-2 sr-1 (cm-1)-1 for wavenumber ``nu_cm`` in cm-1."""
    nu = np.asarray(nu_cm, dtype=float)
    nu_m = nu * 100.0                                   # m-1
    x = H * C * nu_m / (KB * T)
    with np.errstate(over="ignore", divide="ignore"):
        b = 2.0 * H * C**2 * nu_m**3 / np.expm1(x)      # W m-2 sr-1 per m-1
    b = np.where(nu > 0, b, 0.0)
    return b * 100.0                                    # per cm-1 (1 cm-1 = 100 m-1)


def flux(nu_cm, T):
    """Hemispheric spectral flux pi*B in W m-2 (cm-1)-1."""
    return np.pi * radiance(nu_cm, T)


def peak_wavenumber(T) -> float:
    """Wavenumber (cm-1) of the maximum of B(nu) at temperature T (Wien's law in wavenumber)."""
    return WIEN_X_WAVENUMBER * KB * T / (H * C * 100.0)


def wavelength_um(nu_cm):
    """Convert wavenumber (cm-1) to wavelength (micrometres)."""
    return 1.0e4 / np.asarray(nu_cm, dtype=float)
