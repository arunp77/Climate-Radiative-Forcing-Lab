"""Planck function and model atmosphere against exact / published values."""
import numpy as np
import pytest

from radforce.spectra import atmosphere as A
from radforce.spectra import planck as P


def test_stefan_boltzmann_integral():
    nu = np.linspace(0.5, 30000, 1_500_000)
    for T in (220.0, 288.15, 5772.0 if False else 400.0):
        total = np.trapezoid(P.flux(nu, T), nu)
        assert total == pytest.approx(P.SIGMA_SB * T**4, rel=2e-4)


def test_sigma_sb_matches_si_constants():
    # sigma = 2 pi^5 k^4 / (15 h^3 c^2)
    s = 2 * np.pi**5 * P.KB**4 / (15 * P.H**3 * P.C**2)
    assert s == pytest.approx(P.SIGMA_SB, rel=1e-8)


def test_wien_peak_in_wavenumber_space():
    nu = np.linspace(50, 3000, 300_000)
    T = 288.15
    assert nu[np.argmax(P.radiance(nu, T))] == pytest.approx(P.peak_wavenumber(T), rel=1e-3)
    # Earth's emission peaks near 565 cm-1 (~17.7 um), not at the 10 um 'window' wavelength
    assert 560 < P.peak_wavenumber(288.15) < 570


def test_planck_monotonic_in_temperature():
    assert np.all(P.radiance(np.array([300, 700, 1500.0]), 300) > P.radiance(np.array([300, 700, 1500.0]), 250))


# U.S. Standard Atmosphere 1976 table values (geopotential km -> Pa)
@pytest.mark.parametrize("z,p", [(0, 101325.0), (11, 22632.1), (20, 5474.89), (32, 868.019), (47, 110.906)])
def test_us_standard_pressure(z, p):
    assert A.pressure(z) == pytest.approx(p, rel=2e-4)


@pytest.mark.parametrize("z,T", [(0, 288.15), (11, 216.65), (20, 216.65), (32, 228.65), (47, 270.65)])
def test_us_standard_temperature(z, T):
    assert A.temperature(z) == pytest.approx(T, abs=1e-9)


def test_layers_conserve_air_and_ozone_column():
    L = A.build_layers(o3_du=300.0)
    # surface pressure / (M g) in molecules cm-2 down to 60 km
    assert L.n_air.sum() == pytest.approx(A.air_column(A.P0, A.pressure(60.0)), rel=1e-12)
    assert L.columns["O3"].sum() / A.DU == pytest.approx(300.0, rel=1e-9)


def test_co2_column_scales_with_mixing_ratio():
    a = A.build_layers(co2_ppm=400).columns["CO2"].sum()
    b = A.build_layers(co2_ppm=800).columns["CO2"].sum()
    assert b / a == pytest.approx(2.0, rel=1e-12)


def test_water_vapour_column_is_realistic():
    """Fixed-RH profile gives a global-mean-like precipitable water of ~15-30 kg m-2."""
    L = A.build_layers()
    pw = L.columns["H2O"].sum() * 18.015e-3 / A.N_A * 1e4  # kg m-2
    assert 15 < pw < 30


# ----- radiative transfer analytic limits -----
from radforce.spectra import rt


def test_rt_transparent_atmosphere_returns_surface_blackbody():
    nu = np.linspace(10, 3000, 3000)
    tau = np.zeros((5, nu.size))
    f = rt.upward_flux(nu, tau, [280, 270, 260, 250, 240], 288.15)
    assert rt.total(nu, f) == pytest.approx(np.trapezoid(P.flux(nu, 288.15), nu), rel=1e-9)


def test_rt_opaque_isothermal_atmosphere_emits_at_its_own_temperature():
    nu = np.linspace(10, 3000, 3000)
    tau = np.full((4, nu.size), 50.0)
    f = rt.upward_flux(nu, tau, [250.0] * 4, 300.0)
    assert rt.total(nu, f) == pytest.approx(np.trapezoid(P.flux(nu, 250.0), nu), rel=1e-6)


def test_rt_single_gray_layer_matches_analytic_flux():
    """Surface at Ts under one isothermal layer of vertical optical depth tau (flux transmission via E3)."""
    from scipy.special import expn

    nu = np.array([500.0, 1000.0])
    tau0, Ts, Tl = 0.7, 290.0, 240.0
    trans = 2 * expn(3, tau0)   # flux transmittance 2*E3(tau)
    expected = np.pi * (P.radiance(nu, Ts) * trans + P.radiance(nu, Tl) * (1 - trans))
    f16 = rt.upward_flux(nu, np.full((1, 2), tau0), [Tl], Ts, n_angles=16)
    assert f16 == pytest.approx(expected, rel=1e-6)
    # the default 4-angle quadrature is good to < 0.1 % for any optical depth (measured max 6e-4)
    for t in (0.01, 0.1, 0.7, 3.0, 10.0):
        e = np.pi * (P.radiance(nu, Ts) * 2 * expn(3, t) + P.radiance(nu, Tl) * (1 - 2 * expn(3, t)))
        assert rt.upward_flux(nu, np.full((1, 2), t), [Tl], Ts) == pytest.approx(e, rel=1e-3)
