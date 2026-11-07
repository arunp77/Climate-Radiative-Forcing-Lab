"""Stratospheric temperature adjustment by the fixed-dynamical-heating (FDH) method.

When a gas is added the stratosphere reaches a new radiative balance within a few months, long before the surface
responds.  The standard way to compute the resulting "stratosphere-adjusted" forcing (Fels et al. 1980; Hansen et al.
1997; Forster et al. 2021, Section 7.3.1) is to hold the troposphere and the surface fixed and change the
stratospheric temperatures until the longwave cooling of every stratospheric layer returns to its value in the
reference atmosphere, i.e. until the (fixed) solar and dynamical heating balances it again.

Approximations made here, all stated on the Spectra tab:
* only the longwave is recomputed; solar heating and dynamical heating are held at the reference values;
* the absorption cross-sections are kept at their reference-temperature values (only the emission changes with the new
  temperature), a small error for temperature changes of a few kelvin;
* clouds, when present, are the one grey deck of the all-sky estimate, combined as ``(1-f) clear + f cloudy``.
"""
from __future__ import annotations

import numpy as np

from . import rt


def _combined_net(nu, columns, T_layers, T_surface):
    """Weighted net flux at every interface for a list of ``(weight, tau)`` columns."""
    net = 0.0
    for w, tau in columns:
        net = net + w * rt.net_flux_profile(nu, tau, T_layers, T_surface)[2]
    return net


def cooling(net: np.ndarray) -> np.ndarray:
    """Longwave cooling of each layer, W m-2: net upward flux leaving the top minus the flux entering the bottom."""
    return net[1:] - net[:-1]


def adjust_stratosphere(nu, ref_columns, new_columns, T_layers, T_surface, first_layer: int, *,
                        tol: float = 1e-4, max_iter: int = 12, step_K: float = 0.5):
    """Adjust the temperature of layers ``first_layer`` and above so the cooling matches the reference atmosphere.

    ``ref_columns`` and ``new_columns`` are lists of ``(weight, tau)`` for the reference and the perturbed
    composition.  Returns ``(T_adjusted, iterations, residual)``; the residual is the largest remaining difference
    in layer cooling, W m-2.
    """
    T0 = np.asarray(T_layers, dtype=float)
    c_ref = cooling(_combined_net(nu, ref_columns, T0, T_surface))
    idx = np.arange(first_layer, len(T0))

    def resid(T):
        return (cooling(_combined_net(nu, new_columns, T, T_surface)) - c_ref)[idx]

    T = T0.copy()
    r = resid(T)
    # Jacobian by finite differences about the unadjusted state (cooling is nearly linear in temperature over a few K)
    J = np.zeros((idx.size, idx.size))
    for j, k in enumerate(idx):
        Tp = T.copy()
        Tp[k] += step_K
        J[:, j] = (resid(Tp) - r) / step_K
    it = 0
    while np.max(np.abs(r)) > tol and it < max_iter:
        dT = np.linalg.solve(J, -r)
        T[idx] += np.clip(dT, -30.0, 30.0)
        r = resid(T)
        it += 1
    return T, it, float(np.max(np.abs(r)))
