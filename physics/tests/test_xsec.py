"""HITRAN cross-section library: parsing, selection, and band positions (needs the downloaded files)."""
import warnings

import numpy as np
import pytest

from radforce.spectra import xsec

lib_ok = xsec.XSC_DIR.exists() and any(xsec.XSC_DIR.glob("*/*.xsc"))
pytestmark = pytest.mark.skipif(not lib_ok, reason="HITRAN cross-section files not downloaded (data/raw/hitran_xsec)")

EXPECTED = {"C2F6", "C3F8", "CCl4", "CF4", "CFC-11", "CFC-113", "CFC-114", "CFC-12", "HCFC-141b", "HCFC-142b",
            "HCFC-22", "HFC-125", "HFC-134a", "HFC-143a", "HFC-23", "HFC-32", "SF6"}


@pytest.fixture(scope="module")
def lib():
    return xsec.XscLibrary()


def test_header_parser_on_known_line():
    h = xsec.parse_header(" " * 15 + "CCl3F 1050.0007 1120.0011  23232 190.00  37.5 2.058E-18 0.01         CFC-11    air 15")
    assert (h.molecule, h.n, h.T, h.p_torr, h.name, h.broadener, h.ref) == ("CCl3F", 23232, 190.0, 37.5, "CFC-11", "air", "15")
    assert h.nu_min == pytest.approx(1050.0007) and h.sigma_max == pytest.approx(2.058e-18)


def test_all_expected_molecules_present(lib):
    assert EXPECTED <= set(lib.molecules())


def test_every_molecule_has_a_pressure_resolved_or_fallback_set(lib):
    for m in EXPECTED:
        g = lib.groups(m)[0]
        assert len(g) >= 3, m          # even the weakest (older, temperature-only) data have >= 3 temperatures


@pytest.mark.parametrize("mol,lo,hi,peak,tol", [
    ("SF6", 900, 1000, 948, 3), ("CFC-12", 1100, 1200, 1161, 5), ("CCl4", 760, 830, 794, 6),
    ("CF4", 1250, 1320, 1283, 4), ("CFC-11", 1050, 1120, 1085, 6), ("CFC-11", 820, 880, 846, 6),
])
def test_strongest_feature_at_known_fundamental(lib, mol, lo, hi, peak, tol):
    nu = np.arange(lo, hi, 0.05)
    s, _ = lib.sigma(mol, 288.0, 101325.0, nu)
    assert abs(nu[np.argmax(s)] - peak) < tol


def test_files_match_headers_and_are_non_negative(lib):
    for m in ("CFC-11", "HFC-134a"):                                   # spot-check two molecules (full survey: 648 files OK)
        for f in lib.files[m][:6]:
            v = xsec.read_values(f.path)
            assert v.size == f.n and np.all(v >= 0)
            assert v.max() == pytest.approx(f.sigma_max, rel=0.02)


def test_trailing_padding_is_dropped(lib):
    f = next(x for x in lib.files["C2F6"] if x.n % 10 != 0)
    assert xsec.read_values(f.path).size == f.n


def test_corrupted_value_is_repaired_with_a_warning(lib):
    f = next(x for x in lib.files["C2F6"] if x.path.name == "C2F6_284.1_520.5_1061.0-1165.0_02.xsc")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        v = xsec.read_values(f.path)
    assert v.size == f.n and any("unparseable" in str(x.message) for x in w)


def test_selection_prefers_nearest_temperature_and_pressure(lib):
    cold = lib._nearest(lib.groups("CFC-11")[0], 217.0, 200.0 * 133.322 / 133.322)
    assert abs(cold.T - 217) < 20 and cold.p_torr < 400
    warm = lib._nearest(lib.groups("CFC-11")[0], 293.0, 760.0)
    assert warm.T > 270 and warm.p_torr > 500


def test_sigma_outside_coverage_is_flagged_zero(lib):
    nu = np.array([100.0, 2000.0])
    s, covered = lib.sigma("CCl4", 288.0, 101325.0, nu)
    assert not covered.any() and np.all(s == 0)


def test_cross_section_temperature_dependence_is_modest_for_window_band(lib):
    """Integrated strength of a heavy-molecule band changes by only a few tens of percent from 190 to 293 K."""
    nu = np.arange(780, 1100, 0.05)
    cold, _ = lib.sigma("SF6", 200.0, 20000.0, nu)
    warm, _ = lib.sigma("SF6", 293.0, 101325.0, nu)
    assert 0.7 < cold.sum() / warm.sum() < 1.3
