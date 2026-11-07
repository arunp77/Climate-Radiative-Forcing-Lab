"""MT_CKD 4.3 water-vapour continuum: implementation of the reference-code scaling (needs data/raw/mtckd)."""
import numpy as np
import pytest
from scipy.io import netcdf_file

from radforce.spectra import continuum as C

pytestmark = pytest.mark.skipif(not C.available(), reason="MT_CKD data file not present")


@pytest.fixture(scope="module")
def ref():
    with netcdf_file(str(C.DATA), mmap=False) as f:
        return {k: np.array(f.variables[k][:], dtype=float) for k in ("wavenumbers", "self_absco_ref", "for_absco_ref", "self_texp")}


def test_reference_conditions_reproduce_tabulated_coefficients(ref):
    """At 296 K, 1013 mbar the scaling is the identity: sigma = (x C_self + (1-x) C_for) R at a grid node."""
    i = int(np.argmin(np.abs(ref["wavenumbers"] - 1000.0)))
    nu = ref["wavenumbers"][i]
    R = nu * np.tanh(nu * C.RADCN2 / (2 * 296.0))
    for x in (0.0, 0.3, 1.0):
        expected = (x * ref["self_absco_ref"][i] + (1 - x) * ref["for_absco_ref"][i]) * R
        assert C.sigma(nu, 296.0, 101300.0, x) == pytest.approx(expected, rel=1e-6)


def test_self_part_scales_with_vapour_fraction_and_density():
    nu = np.array([1000.0])
    a = C.sigma(nu, 296.0, 101300.0, 0.02) - C.sigma(nu, 296.0, 101300.0, 0.0)
    b = C.sigma(nu, 296.0, 101300.0, 0.04) - C.sigma(nu, 296.0, 101300.0, 0.0)
    assert 1.9 < b[0] / a[0] < 2.1                     # (self - foreign) difference is linear in x
    half = C.sigma(nu, 296.0, 50650.0, 0.02)
    full = C.sigma(nu, 296.0, 101300.0, 0.02)
    assert half[0] / full[0] == pytest.approx(0.5, rel=1e-6)   # proportional to total density at fixed T and x


def test_self_continuum_strengthens_strongly_toward_cold_temperatures():
    nu = np.array([1000.0])
    cold = C.sigma(nu, 260.0, 101300.0, 1.0)[0]
    warm = C.sigma(nu, 296.0, 101300.0, 1.0)[0]
    # (296/260)^texp with texp ~ 5.6 at 1000 cm-1, times the density factor (296/260): ~ 2.0 x 1.14 / R ratio
    assert 1.8 < cold / warm < 3.0


def test_radiation_term_limits():
    nu = np.array([100.0, 3000.0])
    R = C.radiation_term(nu, 296.0)
    assert R[1] == pytest.approx(3000.0, rel=1e-3)                   # tanh -> 1 at high wavenumber
    assert R[0] == pytest.approx(100.0 * np.tanh(100.0 * C.RADCN2 / 592.0))
    assert R[0] < 100.0


def test_window_optical_depth_of_us_standard_atmosphere_is_small_but_not_negligible():
    from radforce.spectra import atmosphere as A

    L = A.build_layers()
    nu = np.array([940.0, 1000.0, 1100.0])
    tau = sum(C.sigma(nu, L.T_mid[i], L.p_mid[i], float(L.vmr["H2O"][i])) * L.columns["H2O"][i] for i in range(len(L.p_mid)))
    assert np.all((tau > 0.02) & (tau < 0.4)), tau              # continuum-only window optical depth, mid-latitude-like humidity


def test_continuum_is_non_negative_and_finite_across_the_range():
    nu = np.linspace(10, 4000, 4000)
    s = C.sigma(nu, 288.0, 90000.0, 0.01)
    assert np.all(np.isfinite(s)) and np.all(s >= 0)
