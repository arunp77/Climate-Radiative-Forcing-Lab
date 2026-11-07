"""Physical consistency of the built spectral products (web/public/data/spectra/*.json).

Line-by-line (and HITRAN cross-section) TOA *instantaneous* forcings for the US-standard atmosphere,
with the MT_CKD water-vapour continuum, clear-sky and with a global-mean all-sky cloud estimate, but
without stratospheric adjustment.  They are therefore expected to differ from AR6's stratosphere-adjusted
forcings by tens of percent; the tests check physics (log/sqrt laws, signs, magnitudes, cloud calibration)
and agreement with independent observations/AR6 within stated tolerances, not a tight match.
Tolerances were fixed from physical reasoning before the results were inspected.
"""
import json
from pathlib import Path

import numpy as np
import pytest

from radforce import ch4_forcing, co2_forcing, n2o_forcing
from radforce.spectra import planck

D = Path(__file__).resolve().parents[2] / "web" / "public" / "data" / "spectra"
pytestmark = pytest.mark.skipif(not (D / "olr.json").exists(), reason="run build/build_spectra.py first")


@pytest.fixture(scope="module")
def olr():
    return json.loads((D / "olr.json").read_text())


def _irf(olr, gas, value):
    return next(e["irf"] for e in olr["sweeps"][gas]["entries"] if abs(e["value"] - value) < 1e-6)


def test_present_day_olr_matches_ceres_within_single_profile_error(olr):
    """Present-day clear/all-sky OLR (1750 baseline minus the 2019 GHG forcing) vs CERES EBAF Ed4.0 (268.1 / 240.1)."""
    clear = olr["baseline"]["olr"] - olr["all_2019"]["irf"]
    allsky = olr["baseline"]["olr_all"] - olr["all_2019"]["irf_all"]
    assert abs(clear - olr["cloud"]["ceres_clear_olr"]) < 10.0     # one US-standard profile, not a global mean
    assert abs(allsky - olr["cloud"]["ceres_allsky_olr"]) < 10.0


def test_cloud_model_is_calibrated_to_observed_longwave_cre(olr):
    c = olr["cloud"]
    assert c["target_lw_cre"] == 27.9                               # CERES EBAF Ed4.0, Loeb et al. (2018) Table 5
    assert c["model_lw_cre"] == pytest.approx(27.9, abs=1e-3)
    assert 0.0 < c["tau_c"] < 5.0 and c["cover"] == 0.67
    assert olr["baseline"]["olr_all"] < olr["baseline"]["olr"]


def test_spectrum_integrates_to_olr_and_below_surface_blackbody(olr):
    nu = olr["nu_start"] + olr["dnu"] * np.arange(len(olr["baseline"]["spec"]))
    spec = np.array(olr["baseline"]["spec"])
    assert np.trapezoid(spec, nu) == pytest.approx(olr["baseline"]["olr"], rel=0.01)  # bins cover 10-4000 cm-1
    spec_all = np.array(olr["baseline"]["spec_all"])
    assert np.trapezoid(spec_all, nu) == pytest.approx(olr["baseline"]["olr_all"], rel=0.01)
    assert np.all(spec_all <= spec * 1.0001 + 1e-9)               # clouds only ever reduce the outgoing flux
    assert np.all(spec <= planck.flux(nu, olr["T_surface"]) * 1.001)   # never exceeds the surface blackbody


def test_co2_doubling_toa_forcing_magnitude(olr):
    f2x = _irf(olr, "CO2", 556.6)
    assert 2.4 < f2x < 3.6   # clear-sky TOA IRF, no strat. adjustment (AR6 SARF 3.7, tropopause IRF higher)
    e = next(e for e in olr["sweeps"]["CO2"]["entries"] if abs(e["value"] - 556.6) < 1e-6)
    assert 1.6 < e["irf_all"] < f2x    # clouds reduce the TOA forcing of CO2, but not by more than ~half


def test_co2_forcing_is_logarithmic_across_successive_doublings(olr):
    d1 = _irf(olr, "CO2", 556.6) - _irf(olr, "CO2", 278.3)
    d2 = _irf(olr, "CO2", 1113.2) - _irf(olr, "CO2", 556.6)
    d3 = _irf(olr, "CO2", 2226.4) - _irf(olr, "CO2", 1113.2)
    assert 0.9 < d2 / d1 < 1.15 and 0.9 < d3 / d2 < 1.2   # line physics reproduces the log law
    # and it is clearly NOT linear: 8x the CO2 gives ~3x (not 8x) the doubling forcing
    assert _irf(olr, "CO2", 2226.4) / d1 < 4.0


def test_ch4_and_n2o_follow_square_root_law(olr):
    for gas, v0, v1, v2 in (("CH4", 729.2, 1866.3, 5000.0), ("N2O", 270.1, 332.1, 600.0)):
        sqrt_ratio = (np.sqrt(v2) - np.sqrt(v0)) / (np.sqrt(v1) - np.sqrt(v0))
        lbl_ratio = _irf(olr, gas, v2) / _irf(olr, gas, v1)
        assert lbl_ratio == pytest.approx(sqrt_ratio, rel=0.15), (gas, lbl_ratio, sqrt_ratio)


def test_forcing_signs_and_monotonicity(olr):
    for gas, sw in olr["sweeps"].items():
        irf = [e["irf"] for e in sw["entries"]]
        assert all(b > a for a, b in zip(irf, irf[1:])), gas       # more absorber -> larger forcing
        assert sw["entries"][[e["value"] for e in sw["entries"]].index(sw["entries"][0]["value"])]["irf"] < 0


def test_lbl_forcing_within_clear_sky_factor_of_ar6_formulas(olr):
    """1750 -> 2019 forcing of each gas vs the SARF from the AR6 equations (no ERF adjustment)."""
    sarf = {"CO2": float(co2_forcing(409.85, erf=False)), "CH4": float(ch4_forcing(1866.3, erf=False)),
            "N2O": float(n2o_forcing(332.1, erf=False))}
    for gas, v in (("CO2", 409.85), ("CH4", 1866.3), ("N2O", 332.1)):
        ratio = _irf(olr, gas, v) / sarf[gas]
        assert 0.7 < ratio < 1.6, (gas, ratio)


def test_combined_2019_ghg_forcing_is_sum_of_parts_within_overlap(olr):
    parts = _irf(olr, "CO2", 409.85) + _irf(olr, "CH4", 1866.3) + _irf(olr, "N2O", 332.1)
    assert olr["all_2019"]["irf"] == pytest.approx(parts, rel=0.08)   # band overlap makes it slightly less
    assert olr["all_2019"]["irf"] <= parts + 0.02


def test_co2_15um_notch_is_visible_in_outgoing_spectrum(olr):
    nu = olr["nu_start"] + olr["dnu"] * np.arange(len(olr["baseline"]["spec"]))
    spec = np.array(olr["baseline"]["spec"])
    notch = spec[(nu > 660) & (nu < 675)].mean()
    shoulder = spec[(nu > 720) & (nu < 760)].mean()
    # in the band centre emission comes from the cold stratosphere (~217-230 K): far below the warmer shoulder
    assert notch < 0.7 * shoulder
    bb220 = planck.flux(667.0, 217.0)
    assert notch == pytest.approx(bb220, rel=0.35)


def test_window_region_is_nearly_transparent(olr):
    nu = olr["nu_start"] + olr["dnu"] * np.arange(len(olr["baseline"]["spec"]))
    spec = np.array(olr["baseline"]["spec"])
    m = (nu > 880) & (nu < 980)       # clean window (between H2O lines and the 9.6 um ozone band)
    bb = planck.flux(nu[m], olr["T_surface"])
    assert (spec[m] / bb).mean() > 0.85   # most surface radiation escapes (no continuum in this model)


def test_lab_cell_transmission_behaves(olr):
    lab = json.loads((D / "lab_CO2.json").read_text())
    t = np.array(lab["t"]["surface"]) / 1000.0           # (column, bin)
    nu = lab["nu_start"] + lab["dnu"] * np.arange(t.shape[1])
    assert t.shape == (19, 3990)
    assert np.all(np.diff(t, axis=0) <= 1e-9)             # transmission falls monotonically with column
    k = int(np.argmin(np.abs(np.array(lab["log10_columns"]) - np.log10(lab["n_atm"]))))   # ~ the atmospheric column
    assert t[k][(nu > 640) & (nu < 700)].mean() < 0.05    # 15 um band opaque at the atmospheric column
    # window mostly clear; weak CO2 hot bands near 10 um (the 960 cm-1 'laser' bands) take a couple of percent
    assert t[k][(nu > 850) & (nu < 950)].mean() > 0.95
    # the smallest column (1e15 molecules cm-2) is transparent almost everywhere
    assert np.median(t[0]) > 0.99


# ----------------------------------------------------------------------------------------------------------------------
# halocarbons
# ----------------------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def halo():
    f = D / "olr_halo.json"
    if not f.exists():
        pytest.skip("olr_halo.json not built")
    return json.loads(f.read_text())


def test_all_17_halocarbons_present(halo):
    assert len(halo["gases"]) == 17


def test_halocarbon_radiative_efficiencies_vs_ar6(halo):
    """All-sky estimate vs AR6 Table 7.SM.7 (stratosphere-adjusted, all-sky): same order, no outlier."""
    ratios = {g: v["re_all"] / v["re_ar6"] for g, v in halo["gases"].items()}
    for g, r in ratios.items():
        assert 0.65 < r < 1.5, (g, r)
    assert 0.8 < np.mean(list(ratios.values())) < 1.3


def test_clear_sky_exceeds_all_sky_for_window_absorbers(halo):
    for g, v in halo["gases"].items():
        assert v["re_clear"] > v["re_all"], g
        # clouds remove a substantial but not overwhelming part of window forcing
        assert 1.1 < v["re_clear"] / v["re_all"] < 2.2, (g, v["re_clear"] / v["re_all"])


def test_halocarbon_forcing_is_linear_in_the_added_amount_at_small_amounts(halo):
    """Weak-absorption limit: forcing is proportional to the amount ADDED to the 1750 atmosphere.

    entries: 1750 level, 1x, 3x, 10x, 30x, ... of the 2019 level.  (CF4 has a natural 1750 level of 34 ppt, so its added
    amount is not exactly a multiple of that at 1x; the expected ratio uses the actual amounts.)  Departures grow with
    abundance: strong, abundant gases (CFC-11, CFC-12, CF4) bend first.
    """
    for g, v in halo["gases"].items():
        e = v["entries"]
        f0 = e[0]["irf"]
        added = lambda k: e[k]["value"] - e[0]["value"]
        r3 = (e[2]["irf"] - f0) / (e[1]["irf"] - f0) / (added(2) / added(1))
        r10 = (e[3]["irf"] - f0) / (e[1]["irf"] - f0) / (added(3) / added(1))
        assert 0.94 < r3 < 1.005, (g, r3)       # within ~6% of linear at 3x today's level
        assert 0.80 < r10 < 1.005, (g, r10)     # within ~20% at 10x today's level
        assert r10 <= r3 + 1e-6, g              # saturation only increases with amount


def test_clouds_remove_a_third_of_window_absorber_forcing(halo):
    r = [v["re_all"] / v["re_clear"] for v in halo["gases"].values()]
    assert 0.55 < min(r) and max(r) < 0.8 and 0.6 < np.mean(r) < 0.7      # measured: 0.62-0.72, mean 0.65


def test_halocarbon_forcing_saturates_sublinearly_at_very_large_amounts(halo):
    for g, v in halo["gases"].items():
        e = v["entries"]
        f0 = e[0]["irf"]
        expected = (e[-1]["value"] - e[0]["value"]) / (e[1]["value"] - e[0]["value"])    # straight-line prediction
        r = (e[-1]["irf"] - f0) / (e[1]["irf"] - f0) / expected
        assert 0.01 < r < 1.0, (g, r)


def test_halocarbon_forcing_increases_with_amount(halo):
    for g, v in halo["gases"].items():
        irf = [e["irf"] for e in v["entries"]]
        assert abs(irf[0]) < 1e-9 and all(b > a for a, b in zip(irf, irf[1:])), g


def test_halocarbon_difference_spectra_remove_radiation(halo):
    """Adding a gas removes outgoing radiation in its bands.  A few bins can gain a little (where the baseline emission
    comes from the warm stratosphere extra absorber raises the emission), but the gain must stay negligible."""
    for g, v in halo["gases"].items():
        d = np.array(v["entries"][-1]["dspec"], dtype=float)
        assert d.min() < -50, g                                       # micro-W m-2 per cm-1: a clear dip
        assert d[d > 0].sum() < 0.01 * (-d[d < 0].sum()), g          # measured worst case 0.14 %


def test_gas_metadata(halo):
    meta = json.loads((D / "gases.json").read_text())
    assert len(meta) == 22
    for g, m in meta.items():
        assert m["colour"].startswith("#") and m["coverage"]
        if m["source"] == "xsec":
            assert m["c2019_ppt"] > m["c1750_ppt"] >= 0 and m["ar6_re"] > 0
