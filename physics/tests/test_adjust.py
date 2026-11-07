"""Layer flux profiles and the fixed-dynamical-heating stratospheric adjustment (idealised cases with known answers)."""
import numpy as np
import pytest

from radforce.spectra import adjust, planck, rt

NU = np.arange(100.0, 2000.0, 1.0)


def _tau(n, scale):
    rng = np.random.default_rng(1)
    base = 1.0 + 0.5 * np.sin(NU / 80.0)
    return np.stack([scale * base * (1.0 + 0.2 * rng.random(NU.size)) for _ in range(n)])


def test_profile_top_equals_existing_upward_flux():
    tau, T = _tau(8, 0.4), np.linspace(280, 215, 8)
    up, down, net = rt.net_flux_profile(NU, tau, T, 288.0)
    ref = rt.total(NU, rt.upward_flux(NU, tau, T, 288.0))
    assert up[-1] == pytest.approx(ref, rel=1e-9)
    assert down[-1] == 0.0                                   # no radiation arrives from space


def test_deep_inside_an_opaque_isothermal_atmosphere_the_net_flux_vanishes():
    # up and down both equal pi B, so only the cold-space boundary near the top carries a net flux
    T = np.full(6, 250.0)
    up, _, net = rt.net_flux_profile(NU, _tau(6, 6.0), T, 250.0)
    assert abs(net[0]) < 1e-3 * up[0]
    assert net[-1] > 100 * abs(net[0])


def test_surface_flux_of_transparent_atmosphere_is_blackbody():
    up, down, _ = rt.net_flux_profile(NU, np.zeros((4, NU.size)), np.full(4, 230.0), 290.0)
    sb = np.pi * np.trapezoid(planck.radiance(NU, 290.0), NU)
    assert up[0] == pytest.approx(sb, rel=1e-9)
    assert up[-1] == pytest.approx(up[0], rel=1e-9) and np.max(down) == 0.0


def test_no_perturbation_means_no_adjustment():
    tau, T = _tau(8, 0.5), np.linspace(280, 215, 8)
    cols = [(1.0, tau)]
    Tn, it, res = adjust.adjust_stratosphere(NU, cols, cols, T, 288.0, 4)
    assert np.allclose(Tn, T) and res < 1e-9


def test_more_absorber_aloft_cools_the_stratosphere_and_restores_the_balance():
    T = np.array([285, 275, 265, 255, 245, 235, 225, 217, 217, 220, 228, 238], dtype=float)
    ref = [(1.0, _tau(12, 0.3))]
    new = [(1.0, _tau(12, 0.3) * 1.6)]
    Tn, it, res = adjust.adjust_stratosphere(NU, ref, new, T, 288.0, 7)
    assert res < 1e-3                                         # layer cooling restored to the reference values
    assert np.allclose(Tn[:7], T[:7])                         # the troposphere is held fixed
    # a more absorbing layer emits more at its own temperature than it absorbs from below, so it must cool
    assert np.mean(Tn[7:] - T[7:]) < 0


def test_adjustment_conserves_energy_between_tropopause_and_top():
    T = np.array([285, 275, 265, 255, 245, 235, 225, 217, 217, 220, 228, 238], dtype=float)
    ref = [(1.0, _tau(12, 0.3))]
    new = [(1.0, _tau(12, 0.3) * 1.6)]
    Tn, _, _ = adjust.adjust_stratosphere(NU, ref, new, T, 288.0, 7)
    n0 = adjust._combined_net(NU, ref, T, 288.0)
    n1 = adjust._combined_net(NU, new, Tn, 288.0)
    # once every stratospheric layer cools as before, the change in net flux is the same at the tropopause and the top
    assert (n1[-1] - n0[-1]) == pytest.approx(n1[7] - n0[7], abs=2e-3)
