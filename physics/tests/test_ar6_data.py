"""Integrity checks on the bundled AR6 reference data."""
import numpy as np
import pytest

from radforce.data import ar6_concentrations, ar6_erf


def test_components_sum_to_nonco2_wmghg():
    e = ar6_erf()
    assert np.allclose(e.ch4 + e.n2o + e.other_wmghg, e.nonco2_wmghg, atol=1e-6)


def test_anthropogenic_total():
    e = ar6_erf()
    parts = ["co2", "ch4", "n2o", "other_wmghg", "o3", "h2o_stratospheric", "contrails",
             "aerosol-radiation_interactions", "aerosol-cloud_interactions", "bc_on_snow",
             "land_use"]
    # 'chapter2_other_anthro' is a separate residual item NOT included in the total.
    # Percentile series (pc05/pc95) are not additive by construction, so only the
    # best estimate is checked.
    assert np.allclose(e[parts].sum(axis=1), e.total_anthropogenic, atol=1e-6)


def test_ar6_headline_2019():
    e = ar6_erf().loc[2019]
    assert e.total_anthropogenic == pytest.approx(2.72, abs=0.01)
    assert e.co2 + e.ch4 + e.n2o + e.other_wmghg == pytest.approx(3.32, abs=0.01)


def test_uncertainty_bounds_bracket_best():
    best, lo, hi = ar6_erf("best"), ar6_erf("pc05"), ar6_erf("pc95")
    y = 2019
    for col in ("co2", "ch4", "n2o", "aerosol", "total_anthropogenic"):
        assert lo.loc[y, col] <= best.loc[y, col] <= hi.loc[y, col], col


def test_concentration_anchors():
    c = ar6_concentrations()
    assert c.loc[1750, "CO2"] == pytest.approx(278.3)
    assert c.loc[2019, "CO2"] == pytest.approx(409.85)
    assert c.loc[2019, "CH4"] == pytest.approx(1866.3, abs=0.1)
    assert c.loc[2019, "N2O"] == pytest.approx(332.1, abs=0.1)
