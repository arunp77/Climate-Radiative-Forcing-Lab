"""Three-layer energy balance model: the physical core of FaIR v2 (Leach et al. 2021; Cummins et al. 2020).

Layers: surface (air, land, upper ocean), mid ocean, deep ocean.  With kappa the heat-transfer coefficients
(kappa[0] is the climate-feedback parameter, positive for a stabilising feedback), C the heat capacities and
epsilon the deep-ocean efficacy:

    C0 dT0/dt = F - kappa0 T0 - kappa1 (T0 - T1)
    C1 dT1/dt = kappa1 (T0 - T1) - epsilon kappa2 (T1 - T2)
    C2 dT2/dt = kappa2 (T1 - T2)

The equilibrium response to a constant forcing F is T = F / kappa0 in every layer, so ECS = F2x / kappa0.
Earth's energy imbalance is N = F - kappa0 T0 + (1 - epsilon) kappa2 (T1 - T2).

Like FaIR, the forcing reaches the surface layer through a first-order low-pass filter, ds/dt = gamma (F - s), with
gamma = 2 per year (a 0.5 yr lag; this is the autocorrelated "stochastic forcing" state of Cummins et al. with the noise
switched off).  It matters only for sharp pulses such as volcanic eruptions.  Set ``gamma=None`` to feed F in directly.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import expm, solve


@dataclass(frozen=True)
class EbmParams:
    C: tuple[float, float, float]          # W yr m-2 K-1
    kappa: tuple[float, float, float]      # W m-2 K-1
    epsilon: float = 1.0
    F4x: float = 7.5                       # W m-2, forcing of 4 x CO2 (F2x = F4x / 2)
    gamma: float | None = 2.0              # yr-1, forcing-filter rate (FaIR default); None = no filter

    @property
    def F2x(self) -> float:
        return self.F4x / 2.0

    def matrix(self) -> np.ndarray:
        """3x3 matrix of the temperature layers (without the forcing filter)."""
        C, k, e = self.C, self.kappa, self.epsilon
        return np.array([
            [-(k[0] + k[1]) / C[0], k[1] / C[0], 0.0],
            [k[1] / C[1], -(k[1] + e * k[2]) / C[1], e * k[2] / C[1]],
            [0.0, k[2] / C[2], -k[2] / C[2]],
        ])

    def with_ecs(self, ecs: float) -> "EbmParams":
        """Same ocean, new climate-feedback parameter so that ECS = ``ecs`` (K)."""
        return EbmParams(self.C, (self.F2x / ecs, self.kappa[1], self.kappa[2]), self.epsilon, self.F4x, self.gamma)

    @property
    def ecs(self) -> float:
        return self.F2x / self.kappa[0]


def run(params: EbmParams, forcing: np.ndarray, dt: float = 1.0, s0: float = 0.0):
    """Layer temperatures (K) at the start of every step and at the end, from rest.

    ``forcing`` has one value per step (constant within the step); ``s0`` is the initial value of the filtered
    forcing (FaIR starts it at the first forcing value).  Returns an array (n+1, 3).
    """
    A3 = params.matrix()
    if params.gamma is None:
        A, b = A3, np.array([1.0 / params.C[0], 0.0, 0.0])
        Ad = expm(A * dt)
        Bd = solve(A, (Ad - np.eye(3)) @ b)
        x = np.zeros((len(forcing) + 1, 3))
        for i, f in enumerate(forcing):
            x[i + 1] = Ad @ x[i] + Bd * f
        return x
    g = params.gamma                       # augmented state: [filtered forcing s, T0, T1, T2]
    A = np.zeros((4, 4))
    A[0, 0] = -g
    A[1, 0] = 1.0 / params.C[0]
    A[1:, 1:] = A3
    b = np.array([g, 0.0, 0.0, 0.0])
    Ad = expm(A * dt)
    Bd = solve(A, (Ad - np.eye(4)) @ b)
    x = np.zeros((len(forcing) + 1, 4))
    x[0, 0] = s0
    for i, f in enumerate(forcing):
        x[i + 1] = Ad @ x[i] + Bd * f
    return x[:, 1:]


def toa_imbalance(params: EbmParams, forcing: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Net top-of-atmosphere imbalance (W m-2) at the start of each step."""
    k, e = params.kappa, params.epsilon
    return forcing - k[0] * x[:-1, 0] + (1.0 - e) * k[2] * (x[:-1, 1] - x[:-1, 2])


def tcr(params: EbmParams, years: float = 70.0) -> float:
    """Warming at the time of CO2 doubling under a 1 % per year increase (forcing grows linearly to F2x in ``years``)."""
    n = int(round(years * 20))
    dt = years / n
    f = params.F2x * (np.arange(n) + 0.5) / n
    return float(run(params, f, dt=dt)[-1, 0])
