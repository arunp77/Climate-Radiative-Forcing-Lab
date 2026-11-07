"""GWP/GTP calculator against IPCC AR6 WG1 Table 7.SM.7 (Forster et al. 2021)."""
import warnings

import numpy as np
import pytest

from radforce import metrics as M

warnings.filterwarnings("ignore")
SPECIES = {(s.acronym or s.formula): s for s in M.ar6_species()}


def test_molar_mass_of_known_gases():
    # g/mol from standard atomic weights; tolerance 0.05 g/mol
    for formula, grams in {"CCl3F": 137.37, "CCl2F2": 120.91, "CH2FCF3": 102.03, "SF6": 146.06, "CF4": 88.00, "CH4": 16.04}.items():
        assert M.molar_mass(formula) * 1e3 == pytest.approx(grams, abs=0.05), formula


def test_molar_mass_handles_groups_and_prefixes():
    assert M.molar_mass("(E)-CF3CH=CHCl") == pytest.approx(M.molar_mass("CF3CHCHCl"))
    assert M.molar_mass("CH3(CH2)2CH3") == pytest.approx(M.molar_mass("C4H10"))


def test_co2_absolute_metrics_match_ar6():
    co2 = M.co2_metrics()
    # AR6 Table 7.SM.7: AGWP20 2.43e-14, AGWP100 8.95e-14 W m-2 yr kg-1; AGTP100 3.95e-16 K kg-1
    assert co2.at(20)[0] == pytest.approx(2.43e-14, rel=0.005)
    assert co2.at(100)[0] == pytest.approx(8.95e-14, rel=0.005)
    assert co2.at(100)[1] == pytest.approx(3.95e-16, rel=0.005)


@pytest.mark.parametrize("key,metric,value", [
    ("CH4", "GWP20", 81.2), ("CH4", "GWP100", 27.9), ("CH4", "GWP500", 7.95),
    ("N2O", "GWP100", 273.0), ("CFC-11", "GWP100", 6230.0), ("CFC-12", "GWP100", 12500.0),
    ("HFC-134a", "GWP100", 1530.0), ("SF6", "GWP100", 25200.0), ("PFC-14", "GWP100", 7380.0),
])
def test_headline_gwps_match_ar6(key, metric, value):
    m = M.species_metrics(SPECIES[key])
    h = int(metric[3:])
    assert M.gwp(m, h) == pytest.approx(value, rel=0.01)


def test_gtp_values_match_ar6_for_key_gases():
    for key, gtp100 in {"CH4": 5.38, "N2O": 233.0, "CFC-12": 10400.0}.items():
        assert M.gtp(M.species_metrics(SPECIES[key]), 100) == pytest.approx(gtp100, rel=0.01), key


def test_long_lived_species_reproduce_ar6_table():
    """Every species with a lifetime of at least a year: all five metrics within 3 % of the AR6 table."""
    bad = []
    n = 0
    for s in SPECIES.values():
        if not s.lifetime or s.lifetime < M_MIN_LIFETIME or s.formula == "CO2":
            continue
        m = M.species_metrics(s)
        if m is None:
            continue
        n += 1
        ours = [M.gwp(m, 20), M.gwp(m, 100), M.gwp(m, 500), M.gtp(m, 50), M.gtp(m, 100)]
        ref = [s.ar6[k] for k in ("GWP20", "GWP100", "GWP500", "GTP50", "GTP100")]
        if any(abs(o / r - 1) > 0.03 for o, r in zip(ours, ref)):
            bad.append(s.acronym or s.name)
    assert n > 130
    assert not bad, bad


M_MIN_LIFETIME = 1.0


def test_physical_behaviour():
    ch4 = M.species_metrics(SPECIES["CH4"])
    assert M.gwp(ch4, 20) > M.gwp(ch4, 100) > M.gwp(ch4, 500)             # short-lived gas: GWP falls with horizon
    sf6 = M.species_metrics(SPECIES["SF6"])
    assert M.gwp(sf6, 500) > 0.5 * M.gwp(sf6, 20)                          # very long-lived gas: nearly flat
    assert M.gwp(M.co2_metrics(), 100) == pytest.approx(1.0)
    assert M.gtp(ch4, 100) < M.gwp(ch4, 100)                               # temperature metric forgets short-lived gases faster


def test_climate_carbon_feedback_adds_a_few_percent():
    s = SPECIES["CFC-12"]
    on = M.gwp(M.species_metrics(s, climate_carbon_feedback=True), 100)
    off = M.gwp(M.species_metrics(s, climate_carbon_feedback=False), 100)
    assert 1.02 < on / off < 1.10
