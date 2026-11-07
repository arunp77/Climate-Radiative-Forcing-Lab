"""The stored stratospheric-adjustment results (build/stratospheric_adjustment.py) against physical expectations and AR6."""
import json
from pathlib import Path

import pytest

d = json.loads((Path(__file__).resolve().parents[2] / "web/public/data/adjustment.json").read_text())
C = d["cases"]


@pytest.mark.parametrize("case", ["2xCO2", "CH4_2019", "N2O_2019"])
@pytest.mark.parametrize("sky", ["clear", "all"])
def test_energy_balance_after_adjustment(case, sky):
    r = C[case][sky]
    # with every stratospheric layer cooling as before, the forcing is the same at the top and at the tropopause
    assert r["toa_adjusted"] == pytest.approx(r["tropopause_adjusted"], abs=2e-3)
    assert r["residual_Wm2"] < 1e-3


def test_co2_adjustment_raises_top_of_atmosphere_but_lowers_tropopause_forcing():
    r = C["2xCO2"]["all"]
    assert r["toa_adjusted"] > r["toa_irf"] + 1.0            # stratospheric cooling: top-of-atmosphere forcing grows by > 1 W m-2
    assert r["tropopause_irf"] > r["tropopause_adjusted"]    # the same cooling reduces the tropopause forcing
    assert r["toa_irf"] < r["toa_adjusted"] < r["tropopause_irf"]


def test_co2_stratosphere_cools_more_aloft():
    dT = C["2xCO2"]["all"]["dT_strat"]
    assert min(dT) < -8.0 and max(dT[:9]) == 0.0              # upper stratosphere cools by many kelvin; troposphere held fixed
    assert dT[-2] < dT[10] < 0


def test_co2_sarf_agrees_with_ar6_within_five_percent():
    ar6 = d["ar6"]["2xCO2"]["sarf"]                           # 3.75 W m-2, the AR6 stratosphere-adjusted forcing
    assert C["2xCO2"]["all"]["toa_adjusted"] == pytest.approx(ar6, rel=0.05)
    erf = C["2xCO2"]["all"]["toa_adjusted"] * d["tropospheric_adjustment"]["CO2"]
    assert erf == pytest.approx(d["ar6"]["2xCO2"]["erf"], rel=0.05)


def test_ch4_and_n2o_adjustments_are_small():
    for g in ("CH4_2019", "N2O_2019"):
        r = C[g]["all"]
        assert 0.0 < r["toa_adjusted"] / r["toa_irf"] - 1.0 < 0.15


def test_clouds_reduce_the_forcing():
    for g in C:
        assert C[g]["all"]["toa_adjusted"] < C[g]["clear"]["toa_adjusted"]
