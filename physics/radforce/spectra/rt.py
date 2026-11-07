"""Clear-sky longwave radiative transfer in a plane-parallel layered atmosphere.

Schwarzschild equation with the flux obtained by Gauss-Legendre quadrature over zenith
angle (exact for the stated number of streams), black surface, no scattering, local
thermodynamic equilibrium, each layer isothermal at its mid-layer temperature.
"""
from __future__ import annotations

import numpy as np

from . import planck

_GL_CACHE: dict = {}


def _gauss_mu(n: int):
    if n not in _GL_CACHE:
        x, w = np.polynomial.legendre.leggauss(n)
        _GL_CACHE[n] = (0.5 * (x + 1.0), 0.5 * w)   # mu in (0,1), weights summing to 1
    return _GL_CACHE[n]


def upward_flux(nu, tau_layers, T_layers, T_surface, n_angles: int = 4, surface_emissivity: float = 1.0):
    """Spectral upwelling flux at the top of the atmosphere, W m-2 (cm-1)-1.

    ``tau_layers`` has shape (n_layers, n_nu), ordered from the SURFACE upward (vertical optical
    depth of each layer).  Flux = 2 pi * integral of I(mu) mu dmu.
    """
    tau = np.asarray(tau_layers, dtype=np.float64)
    nL, nN = tau.shape
    B_layers = np.stack([planck.radiance(nu, T) for T in T_layers])      # (nL, nN)
    B_surf = surface_emissivity * planck.radiance(nu, T_surface)
    mus, ws = _gauss_mu(n_angles)
    # cumulative optical depth from the top of the atmosphere down to the BOTTOM of each layer
    tau_above_top = np.concatenate([np.cumsum(tau[::-1], axis=0)[::-1][1:], np.zeros((1, nN))], axis=0)
    tau_above_bottom = tau_above_top + tau                                   # includes the layer itself
    out = np.zeros(nN)
    for mu, w in zip(mus, ws):
        t_top = np.exp(-tau_above_top / mu)        # transmission from layer top to space
        t_bot = np.exp(-tau_above_bottom / mu)     # from layer bottom to space
        I = B_surf * t_bot[0] + np.sum(B_layers * (t_top - t_bot), axis=0)
        out += 2.0 * np.pi * w * mu * I
    return out


def total(nu, spectral_flux) -> float:
    """Integrate a spectral flux over the grid -> W m-2 (trapezoid rule)."""
    return float(np.trapezoid(spectral_flux, nu))
