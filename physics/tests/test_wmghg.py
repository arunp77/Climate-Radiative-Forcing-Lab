"""Validation of CO2/CH4/N2O forcing.

Sources of truth (all independent of the code under test):
  * AR6 WG1 Ch.7 ERF time series 1750-2019 (Smith et al., repo chrisroadmap/ar6,
    MIT licence) and AR6 Annex III concentrations (data/MANIFEST.md).
  * AR6 stated 2xCO2 ERF of 3.93 W m-2 (AR6 Sect. 7.3.2.1).
  * The FaIR v2 package's own implementation of the same published equations
    (an independent coding of Myhre 1998, Etminan 2016, Meinshausen 2020).
"""
import numpy as np
import pytest

from radforce import ch4_forcing, co2_forcing, n2o_forcing, wmghg_forcing
from radforce.constants import PREINDUSTRIAL_1750 as PI

C0, M0, N0 = PI["CO2"], PI["CH4"], PI["N2O"]


# ---------------------------------------------------------------- basic properties
@pytest.mark.parametrize("scheme", ["meinshausen2020", "etminan2016", "myhre1998"])
def test_zero_at_baseline(scheme):
    erf = scheme != "myhre1998"
    f = wmghg_forcing(C0, M0, N0, scheme=scheme, erf=erf)
    for k in ("CO2", "CH4", "N2O", "total"):
        assert abs(f[k]) < 1e-12


def test_myhre_rejects_erf():
    with pytest.raises(ValueError):
        co2_forcing(400, erf=True, scheme="myhre1998")


def test_unknown_scheme():
    with pytest.raises(ValueError):
        co2_forcing(400, scheme="nope")


def test_myhre_co2_is_pure_logarithm():
    # 5.35 ln(2) = 3.708 W m-2: the textbook doubling value of the TAR
    assert co2_forcing(2 * C0, scheme="myhre1998", erf=False) == pytest.approx(5.35 * np.log(2), rel=1e-12)


def test_2xco2_erf_matches_ar6_393():
    # AR6 7.3.2.1: ERF for doubled CO2 is 3.93 +/- 0.47 W m-2
    f2x = co2_forcing(2 * C0, scheme="meinshausen2020", erf=True)
    assert f2x == pytest.approx(3.93, abs=0.03)


def test_erf_vs_sarf_ratio_is_the_documented_adjustment():
    r = co2_forcing(560, erf=True) / co2_forcing(560, erf=False)
    assert r == pytest.approx(1.05)
    assert ch4_forcing(1900, erf=True) / ch4_forcing(1900, erf=False) == pytest.approx(0.86)
    assert n2o_forcing(330, erf=True) / n2o_forcing(330, erf=False) == pytest.approx(1.07)


def test_co2_monotonic_and_log_like_over_wide_range():
    C = np.linspace(C0 * 1.001, 10 * C0, 400)  # up to ~2800 ppm, beyond Etminan validity
    f = co2_forcing(C)
    assert np.all(np.diff(f) > 0)
    # each doubling adds a similar (not identical) amount: logarithmic, not linear
    d1 = co2_forcing(2 * C0) - co2_forcing(C0)
    d2 = co2_forcing(4 * C0) - co2_forcing(2 * C0)
    assert 0.8 < d2 / d1 < 1.2


def test_ch4_n2o_forcing_sqrt_like_and_increasing():
    M = np.linspace(M0 * 1.001, 5000, 300)
    assert np.all(np.diff(ch4_forcing(M)) > 0)
    N = np.linspace(N0 * 1.001, 600, 300)
    assert np.all(np.diff(n2o_forcing(N)) > 0)


def test_overlap_reduces_ch4_forcing_when_n2o_rises():
    # CH4 and N2O both absorb near 7.7-7.8 um: more N2O => less additional CH4 forcing
    assert ch4_forcing(1900, N2O=400) < ch4_forcing(1900, N2O=N0)


def test_broadcasting():
    out = co2_forcing(np.array([300.0, 400.0, 500.0]))
    assert out.shape == (3,)


# ---------------------------------------------------------------- AR6 time series
def _series(conc, scheme="meinshausen2020"):
    c = conc.loc[1850:2019]
    return wmghg_forcing(c.CO2.values, c.CH4.values, c.N2O.values, scheme=scheme, erf=True), c.index


def test_reproduces_ar6_2019_individual_gases(conc, erf_best):
    f = wmghg_forcing(*conc.loc[2019, ["CO2", "CH4", "N2O"]].values)
    ar6 = erf_best.loc[2019]
    assert f["CO2"] == pytest.approx(ar6.co2, rel=0.01)
    assert f["CH4"] == pytest.approx(ar6.ch4, rel=0.01)
    assert f["N2O"] == pytest.approx(ar6.n2o, rel=0.01)


def test_reproduces_ar6_whole_series(conc, erf_best):
    f, years = _series(conc)
    for gas, col in (("CO2", "co2"), ("CH4", "ch4"), ("N2O", "n2o")):
        err = np.abs(f[gas] - erf_best.loc[years, col].values)
        assert err.max() < 0.001, f"{gas}: max |error| {err.max():.4f} W m-2"


# ---------------------------------------------------------------- cross-check vs FaIR
def _fair_forcing(func, C, M, N, base):
    """Evaluate FaIR's implementation for one (CO2, CH4, N2O) state, SARF (scale 1)."""
    conc = np.array([C, M, N])
    ref = np.array(base)
    idx = np.array([[True, False, False], [False, True, False], [False, False, True]])
    none = np.zeros(3, dtype=bool)
    return func(conc, ref, np.ones(3), np.zeros(3), idx[0], idx[1], idx[2], none)


@pytest.mark.parametrize("scheme", ["meinshausen2020", "etminan2016", "myhre1998"])
@pytest.mark.parametrize("state", [(409.85, 1866.3, 332.1), (560.0, 2500.0, 400.0), (1000.0, 1200.0, 300.0)])
def test_matches_fair_implementation(scheme, state):
    fair_ghg = pytest.importorskip("fair.forcing.ghg")
    func = getattr(fair_ghg, scheme)
    theirs = _fair_forcing(func, *state, (C0, M0, N0))
    mine = wmghg_forcing(*state, scheme=scheme, erf=False)
    tol = 2e-4  # FaIR uses 5.32e-15 where Myhre (1998) tabulates 5.31e-15
    assert mine["CO2"] == pytest.approx(theirs[0], abs=tol)
    assert mine["CH4"] == pytest.approx(theirs[1], abs=tol)
    assert mine["N2O"] == pytest.approx(theirs[2], abs=tol)


def test_schemes_agree_to_tens_of_percent_but_not_identical():
    # Etminan's CH4 revision raised methane forcing by ~25 % relative to Myhre.
    m = ch4_forcing(1866.3, scheme="myhre1998", erf=False)
    e = ch4_forcing(1866.3, scheme="etminan2016", erf=False)
    assert 1.1 < e / m < 1.5
