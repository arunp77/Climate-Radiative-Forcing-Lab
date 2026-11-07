"""Validation of the non-CO2/CH4/N2O forcing emulators against the AR6 ERF series."""
import numpy as np
import pytest

from radforce.data import ar6_erf
from radforce.forcing.nonghg import (
    ARI_ASSESSED_2005_2014, EMIS_SPECIES, emissions_history, historical_state, load_params,
    non_ghg_erf, preindustrial_state,
)

YEARS = list(range(1750, 2020))
AR6 = ar6_erf("best")
COL = {"O3": "o3", "H2O_strat": "h2o_stratospheric", "Aerosol_ari": "aerosol-radiation_interactions",
       "Aerosol_aci": "aerosol-cloud_interactions", "BC_snow": "bc_on_snow"}


@pytest.fixture(scope="module")
def series():
    out = {k: [] for k in COL}
    for y in YEARS:
        r = non_ghg_erf(historical_state(y))
        for k in COL:
            out[k].append(r[k])
    return {k: np.array(v) for k, v in out.items()}


def test_default_state_reproduces_ar6_2019_exactly():
    p, r = load_params(), non_ghg_erf()
    for k, v in p.ar6_2019.items():
        assert r[k] == pytest.approx(v, abs=1e-12), k


def test_preindustrial_state_gives_zero_for_every_agent():
    r = non_ghg_erf(preindustrial_state())
    for k, v in r.items():
        assert abs(v) < 1e-9, (k, v)


def test_aerosol_radiation_matches_ar6_series_exactly(series):
    err = np.abs(series["Aerosol_ari"] - AR6[COL["Aerosol_ari"]].loc[1750:2019].values)
    assert err.max() < 1e-6


def test_strat_h2o_proportional_to_ch4_matches_ar6(series):
    err = np.abs(series["H2O_strat"] - AR6[COL["H2O_strat"]].loc[1750:2019].values)
    assert err.max() < 1e-6


# Documented accuracy of the emulators (max |difference| over 1750-2019, W m-2).
@pytest.mark.parametrize("agent,tol", [("Aerosol_aci", 0.01), ("BC_snow", 0.02), ("O3", 0.08)])
def test_emulator_accuracy_vs_ar6_series(series, agent, tol):
    err = np.abs(series[agent] - AR6[COL[agent]].loc[1750:2019].values)
    assert err.max() < tol, f"{agent}: max error {err.max():.3f}"


def test_ari_calibration_reproduces_assessed_species_contributions():
    em, p = emissions_history(), load_params()
    for sp, target in ARI_ASSESSED_2005_2014.items():
        mean = (em.loc[2005:2014, sp] - em.loc[1750, sp]).mean() * p.ari_beta[sp]
        assert mean == pytest.approx(target, rel=1e-9)
    # assessed ERFari 2005-2014 is -0.30 W m-2 in AR6
    assert sum(ARI_ASSESSED_2005_2014.values()) == pytest.approx(-0.30)


def test_sulphur_cuts_remove_cooling_and_raise_forcing():
    base = non_ghg_erf()
    clean = non_ghg_erf({"so2": 0.0})
    assert clean["Aerosol_ari"] > base["Aerosol_ari"] and clean["Aerosol_aci"] > base["Aerosol_aci"]
    # removing all of today's SO2 unmasks warming of order 1 W m-2 in AR6 terms
    assert 0.3 < (clean["Aerosol_ari"] + clean["Aerosol_aci"]) - (base["Aerosol_ari"] + base["Aerosol_aci"]) < 1.5


def test_aci_is_saturating_in_emissions():
    """Halving SO2 removes less than half of the cloud cooling (log response)."""
    full = non_ghg_erf()["Aerosol_aci"]
    half = non_ghg_erf({"so2": 0.5})["Aerosol_aci"]
    assert abs(half) > abs(full) / 2


def test_black_carbon_snow_is_linear_in_emissions():
    p = load_params()
    e19, e50 = p.emis_2019["BC"], p.emis_1750["BC"]
    for m in (0.25, 0.5, 1.5):
        expected = 0.08 * (m * e19 - e50) / (e19 - e50)
        assert non_ghg_erf({"bc": m})["BC_snow"] == pytest.approx(expected, rel=1e-9)


def test_ozone_drivers_have_expected_signs():
    base = non_ghg_erf()["O3"]
    assert non_ghg_erf({"nox": 0.5})["O3"] < base       # less NOx -> less ozone
    assert non_ghg_erf({"ch4": 1200.0})["O3"] < base    # less CH4 -> less ozone
    assert non_ghg_erf({"ods": 0.0})["O3"] > base       # no ODS -> no ozone-hole cooling


def test_strat_h2o_follows_ch4():
    base = non_ghg_erf()["H2O_strat"]
    assert non_ghg_erf({"ch4": 3000.0})["H2O_strat"] > 1.5 * base


def test_simple_multipliers():
    assert non_ghg_erf({"contrails": 2.0})["Contrails"] == pytest.approx(2 * load_params().ar6_2019["Contrails"])
    assert non_ghg_erf({"landuse": 0.0})["LandUse"] == 0.0


def test_emission_species_complete():
    assert set(load_params().emis_2019) == set(EMIS_SPECIES)


def test_aci_shape_factors_are_the_least_squares_fit():
    """Re-derive ACI_N0_SO2 / ACI_N1_BCOC from the AR6 median ERFaci series."""
    optimize = pytest.importorskip("scipy.optimize")
    from radforce.constants import ACI_N0_SO2, ACI_N1_BCOC
    em = emissions_history().loc[1750:2019]
    b = AR6["aerosol-cloud_interactions"].loc[1750:2019].values
    S, B = em["SO2"].values, (em["BC"] + em["OC"]).values

    def model(th):
        a, c = np.exp(th)
        r = -(np.log(1 + S / a + B / c) - np.log(1 + S[0] / a + B[0] / c))
        return r / r[-1] * b[-1]

    fits = [optimize.least_squares(lambda th: model(th) - b, np.log([a0, c0]))
            for a0 in (10, 100, 1000) for c0 in (10, 100, 1000)]
    best = min(fits, key=lambda f: f.cost)
    assert np.exp(best.x) == pytest.approx([ACI_N0_SO2, ACI_N1_BCOC], rel=1e-3)
