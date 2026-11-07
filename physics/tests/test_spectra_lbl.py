"""Line-by-line cross-sections: agreement with HAPI, band positions, curve of growth, broadening.

Needs the HITRAN line lists (python build/fetch_hitran.py); skipped when they are absent.
"""
import numpy as np
import pytest

from radforce.spectra import lbl

pytestmark = pytest.mark.skipif(not lbl.available_gases(), reason="HITRAN line lists not downloaded")

hapi = pytest.importorskip("hapi")


def _centroid(gas, lo, hi, p=101325.0, T=296.0, step=0.02):
    nu, s = lbl.cross_section(gas, p, T, 0.0, lo, hi, step)
    return float(np.sum(nu * s) / np.sum(s))


# Vibrational fundamentals (cm-1): standard spectroscopy values; band envelope centroid must agree
@pytest.mark.parametrize("gas,lo,hi,nu0,tol", [
    ("CO2", 600, 740, 667, 15), ("CO2", 2250, 2450, 2349, 15),
    ("CH4", 1200, 1400, 1306, 15), ("N2O", 2100, 2350, 2224, 15), ("N2O", 1200, 1360, 1285, 15),
    ("O3", 1000, 1090, 1042, 15), ("H2O", 1400, 1900, 1595, 40),
])
# CF4 is excluded on purpose: its HITRAN line list peaks near 1255 cm-1, not at the true nu3 maximum
# (1283 cm-1), so it fails this check and is not used until HITRAN cross-section files are added.
def test_band_centroids_match_known_fundamentals(gas, lo, hi, nu0, tol):
    assert abs(_centroid(gas, lo, hi) - nu0) < tol


def test_agrees_with_hapi_reference():
    """Independent check of the whole line-shape/temperature/pressure treatment (HAPI is the reference)."""
    nu, a = lbl.cross_section("H2O", 101325.0, 288.15, 0.01, 1500, 1520, 0.01)
    _, b = lbl.cross_section_hapi("H2O", 101325.0, 288.15, 0.01, 1500, 1520, 0.01)
    assert a.sum() / b.sum() == pytest.approx(1.0, abs=0.01)
    assert a.max() == pytest.approx(b.max(), rel=1e-3)
    strong = b > 1e-3 * b.max()
    assert np.median(np.abs(a[strong] / b[strong] - 1)) < 0.02


def test_curve_of_growth_linear_then_square_root():
    """Equivalent width of the CO2 15 um band grows ~ linearly with amount, then much more slowly."""
    nu, s = lbl.cross_section("CO2", 101325.0, 296.0, 0.0, 600, 740, 0.02)
    W = lambda u: np.trapezoid(1 - np.exp(-s * u), nu)
    slope = lambda u1, u2: np.log(W(u2) / W(u1)) / np.log(u2 / u1)
    assert slope(1e16, 3e16) == pytest.approx(1.0, abs=0.02)      # optically thin
    assert slope(1e21, 1e22) < 0.6                                # saturated line centres
    assert slope(1e22, 1e23) < slope(1e20, 1e21) < 1.0           # keeps flattening


def test_pressure_broadening_conserves_area_and_lowers_peak():
    nu, hi = lbl.cross_section("CO2", 101325.0, 250.0, 0.0, 640, 700, 0.005)
    _, lo = lbl.cross_section("CO2", 25331.0, 250.0, 0.0, 640, 700, 0.005)
    assert lo.sum() / hi.sum() == pytest.approx(1.0, abs=0.05)    # line strength independent of pressure
    # narrower lines => the band is spikier: higher spectral contrast (std/mean) and a higher envelope peak
    # (the envelope peak rises by less than the 4x Lorentz narrowing because Q-branch lines overlap)
    assert lo.max() > 1.2 * hi.max()
    assert lo.std() / lo.mean() > 1.15 * hi.std() / hi.mean()   # measured ratio 1.29


def test_temperature_dependence_of_line_strength():
    """Hot-band and lower-state population: integrated strength changes with T but stays within 40 %."""
    _, a = lbl.cross_section("CO2", 101325.0, 220.0, 0.0, 600, 740, 0.02)
    _, b = lbl.cross_section("CO2", 101325.0, 300.0, 0.0, 600, 740, 0.02)
    assert 0.6 < a.sum() / b.sum() < 1.4


def test_grid_resolution_converged_in_stratosphere():
    """Narrow stratospheric lines (25 km) are resolved well enough: transmission differs < 2 %."""
    from radforce.spectra import atmosphere as A

    L = A.build_layers()
    i = int(np.argmin(np.abs(L.z_mid_km - 26.0)))
    col = float(L.columns["CO2"][i])
    out = []
    for step in (0.02, 0.0025):
        nu, s = lbl.cross_section("CO2", L.p_mid[i], L.T_mid[i], 0.0, 660, 680, step)
        out.append(np.mean(np.exp(-s * col)))
    assert abs(out[0] / out[1] - 1) < 0.02


def test_h2o_self_broadening_increases_absorption_in_wings():
    nu, a = lbl.cross_section("H2O", 101325.0, 296.0, 0.0, 1300, 1400, 0.01)
    _, b = lbl.cross_section("H2O", 101325.0, 296.0, 0.03, 1300, 1400, 0.01)
    # Line wings scale with the Lorentz width: gamma = gamma_air (1 - x) + gamma_self x, and HITRAN's
    # gamma_self / gamma_air is about 4-6 for H2O, so at x = 0.03 the inter-line absorption should rise by
    # about 1 + x (gamma_self/gamma_air - 1) = 1.09 - 1.15 (window median, with line mixing of neighbours)
    ratio = np.median(b) / np.median(a)
    assert 1.08 < ratio < 1.25
