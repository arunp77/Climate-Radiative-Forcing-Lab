import numpy as np
import pytest

from radforce.data import ar6_minor_ghg_erf
from radforce.forcing.halogens import group_of, halogen_forcing, halogen_forcing_year, radiative_efficiency


def test_linear_in_concentration():
    a = halogen_forcing({"CFC-12": 100.0})["total"]
    b = halogen_forcing({"CFC-12": 200.0})["total"]
    assert b == pytest.approx(2 * a)


def test_cfc12_value():
    # AR6 Table 7.SM.7: RE(CFC-12) = 0.358 W m-2 ppb-1 ; 500 ppt = 0.5 ppb
    assert halogen_forcing({"CFC-12": 500.0})["total"] == pytest.approx(0.358 * 0.5)


def test_missing_species_reported_not_dropped():
    out = halogen_forcing({"CFC-12": 100.0, "NOT-A-GAS": 5.0, "HFC-23": float("nan")})
    assert set(out["skipped"]) == {"NOT-A-GAS", "HFC-23"}


def test_groups():
    assert group_of("CFC-11") == "CFC" and group_of("HCFC-22") == "HCFC"
    assert group_of("HFC-134a") == "HFC" and group_of("SF6") == "Other"


def test_pfc_found_by_formula():
    assert not np.isnan(radiative_efficiency("CF4"))


@pytest.mark.parametrize("year", [1970, 1990, 2000, 2010, 2019])
def test_matches_ar6_per_species(year):
    """Per-species RE x dC reproduces the AR6 ERF for the dominant species."""
    ours = halogen_forcing_year(year)
    ar6 = ar6_minor_ghg_erf().loc[year]
    for sp in ("CFC-11", "CFC-12", "HCFC-22", "HFC-134a"):
        assert ours[sp] == pytest.approx(ar6[sp], rel=0.02, abs=2e-4)


def test_total_matches_ar6_2019_within_skipped_species():
    ours = halogen_forcing_year(2019)
    ar6 = ar6_minor_ghg_erf().loc[2019]
    skipped = ar6[ours["skipped"]].sum()          # what we cannot compute (no RE / no conc)
    assert skipped < 0.003                         # honest bound on what is missing
    assert ours["total"] + skipped == pytest.approx(ar6.sum(), abs=0.003)
