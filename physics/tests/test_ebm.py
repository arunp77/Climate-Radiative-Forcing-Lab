"""Three-layer energy balance model: sensitivity, consistency and agreement with the stored FaIR run."""
import json
from pathlib import Path

import numpy as np
import pytest

from radforce.ebm import EbmParams, run, tcr, toa_imbalance

DATA = Path(__file__).resolve().parents[2] / "web/public/data/scenarios.json"
d = json.loads(DATA.read_text())
P = EbmParams(tuple(d["params"]["c"]), tuple(d["params"]["kappa"]), d["params"]["epsilon"], d["params"]["F4x"], 2.0)


def test_equilibrium_response_is_forcing_over_lambda():
    x = run(EbmParams(P.C, P.kappa, P.epsilon, P.F4x, None), np.full(5000, 2.0))
    assert x[-1, 0] == pytest.approx(2.0 / P.kappa[0], rel=2e-3)
    assert x[-1, 2] == pytest.approx(2.0 / P.kappa[0], rel=2e-2)           # the deep ocean follows


def test_ecs_and_tcr_in_the_ar6_range():
    assert P.ecs == pytest.approx(3.0, abs=0.05)                            # AR6 best estimate 3 K
    assert 1.4 < tcr(P) < 2.2                                               # AR6 likely range for TCR
    assert tcr(P) < P.ecs


def test_with_ecs_changes_only_the_feedback():
    Q = P.with_ecs(4.5)
    assert Q.ecs == pytest.approx(4.5)
    assert Q.kappa[1:] == P.kappa[1:] and Q.C == P.C


def test_energy_conservation_at_equilibrium():
    x = run(EbmParams(P.C, P.kappa, P.epsilon, P.F4x, None), np.full(6000, 2.0))
    n = toa_imbalance(P, np.full(6000, 2.0), x)
    assert abs(n[-1]) < 0.01                                                # imbalance has closed


@pytest.mark.parametrize("scn", ["ssp119", "ssp126", "ssp245", "ssp370", "ssp585"])
def test_reproduces_the_fair_run(scn):
    b = np.array(d["scenarios"][scn]["erf_driving_bounds"])
    x = run(P, b[1:], s0=b[0])
    t = 0.5 * (x[:-1, 0] + x[1:, 0])
    t -= t[100:151].mean()
    assert np.abs(t - np.array(d["scenarios"][scn]["temperature"])).max() < 0.002   # K; stored values rounded to 0.001


def test_scenarios_agree_with_ar6_assessed_warming():
    """FaIR (median climate parameters) 2081-2100 warming against the AR6 SPM Table SPM.1 very-likely ranges."""
    for scn, (best, lo, hi) in d["ar6_2081_2100"].items():
        t = np.array(d["scenarios"][scn]["temperature"])[2081 - 1750: 2101 - 1750].mean()
        assert lo <= t <= hi, scn
        assert abs(t - best) < 0.25, scn                                    # and close to the best estimate
