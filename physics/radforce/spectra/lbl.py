"""Line-by-line absorption cross-sections from HITRAN line parameters (via HAPI).

``cross_section`` returns sigma(nu) in cm2 per molecule for a gas at a given pressure,
temperature and self-broadening fraction, using Voigt line shapes with HITRAN air- and
self-broadening, temperature exponents, pressure shifts and TIPS partition functions.
It is a vectorised numpy/scipy implementation that reads the HITRAN line parameters
through HAPI's local tables (HAPI supplies only the partition sums and isotopologue
masses); ``cross_section_hapi`` is the slow reference implementation used in the tests.

Limitations (stated in the user interface too):
* No water-vapour continuum (MT_CKD) and no CO2 line mixing / sub-Lorentzian far wings.
* Wings truncated at ``wing_hw`` half-widths (default 50) from each line centre.
* Point-sampled on a uniform wavenumber grid; the grid must resolve line cores in the
  layers that matter (convergence is tested in tests/test_spectra_lbl.py).
"""
from __future__ import annotations

import contextlib
import io
from functools import lru_cache
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
HITRAN_DIR = ROOT / "data" / "raw" / "hitran"

# gas -> HAPI table names (isotopologues fetched by build/fetch_hitran.py)
TABLES = {
    "H2O": [f"H2O_i{i}" for i in (1, 2, 3, 4)],
    "CO2": [f"CO2_i{i}" for i in (1, 2, 3, 4)],
    "O3": [f"O3_i{i}" for i in (1, 2, 3)],
    "N2O": [f"N2O_i{i}" for i in (1, 2, 3, 4)],
    "CH4": [f"CH4_i{i}" for i in (1, 2)],
    "CF4": ["CF4_i1"],
}


@lru_cache(maxsize=1)
def _hapi():
    """Import HAPI lazily and silence its chatty stdout."""
    import hapi  # noqa: WPS433

    with contextlib.redirect_stdout(io.StringIO()):
        hapi.db_begin(str(HITRAN_DIR))
    return hapi


def available_gases() -> list[str]:
    return [g for g, tabs in TABLES.items() if all((HITRAN_DIR / f"{t}.data").exists() for t in tabs)]


def cross_section_hapi(gas: str, p_pa: float, T: float, x_self: float = 0.0, nu_min: float = 10.0,
                       nu_max: float = 4000.0, step: float = 0.01, wing_hw: float = 50.0):
    """Reference implementation through HAPI (slow; used to validate ``cross_section``).

    Returns ``(nu, sigma)``; ``nu`` in cm-1.  ``x_self`` is the absorber's own volume mixing
    ratio, which sets the self-broadening fraction (important for H2O only).
    """
    hapi = _hapi()
    with contextlib.redirect_stdout(io.StringIO()):
        nu, k = hapi.absorptionCoefficient_Voigt(
            SourceTables=TABLES[gas],
            Environment={"p": p_pa / 101325.0, "T": T},
            Diluent={"air": 1.0 - x_self, "self": x_self},
            WavenumberRange=(nu_min, nu_max), WavenumberStep=step,
            WavenumberWingHW=wing_hw, HITRAN_units=True,
        )
    return np.asarray(nu), np.asarray(k)


# ---------------------------------------------------------------------------
# Fast vectorised implementation
# ---------------------------------------------------------------------------
C2 = 1.4387769            # second radiation constant, cm K
T_REF = 296.0             # HITRAN reference temperature, K
P_ATM = 101325.0          # Pa


@lru_cache(maxsize=None)
def _line_arrays(gas: str):
    """All HITRAN lines of a gas as numpy arrays plus per-line isotopologue index."""
    hapi = _hapi()
    cols = ("nu", "sw", "gamma_air", "gamma_self", "n_air", "delta_air", "elower")
    parts = {c: [] for c in cols}
    iso_key, iso_idx = [], []
    for ti, table in enumerate(TABLES[gas]):
        d = hapi.LOCAL_TABLE_CACHE[table]["data"]
        for c in cols:
            parts[c].append(np.asarray(d[c], dtype=float))
        mol, iso = int(d["molec_id"][0]), int(d["local_iso_id"][0])
        iso_key.append((mol, iso))
        iso_idx.append(np.full(len(d["nu"]), ti, dtype=np.int32))
    arrs = {c: np.concatenate(v) for c, v in parts.items()}
    arrs["iso"] = np.concatenate(iso_idx)
    order = np.argsort(arrs["nu"])
    arrs = {k: v[order] for k, v in arrs.items()}
    arrs["iso_key"] = iso_key
    arrs["mass"] = np.array([hapi.ISO[k][hapi.ISO_INDEX["mass"]] for k in iso_key])
    return arrs


@lru_cache(maxsize=4096)
def _q_ratio(mol_iso: tuple, T: float) -> float:
    """Q(T_ref)/Q(T) from the HITRAN TIPS partition sums."""
    hapi = _hapi()
    out = []
    for t in (T_REF, T):
        r = hapi.partitionSum(mol_iso[0], mol_iso[1], [t, t])
        r = np.asarray(r[1] if isinstance(r, tuple) else r, dtype=float)
        out.append(float(r.ravel()[0]))
    return out[0] / out[1]


def line_parameters(gas: str, p_pa: float, T: float, x_self: float, nu_min: float, nu_max: float,
                    wing_hw: float, wing_max: float, s_min: float):
    """Line intensities, centres and widths at (p, T), restricted to lines that can reach the grid."""
    a = _line_arrays(gas)
    lo, hi = np.searchsorted(a["nu"], [nu_min - wing_max, nu_max + wing_max])
    sl = slice(lo, hi)
    nu0, sw = a["nu"][sl], a["sw"][sl]
    p_atm = p_pa / P_ATM
    p_self = x_self * p_atm
    qr = np.array([_q_ratio(k, float(T)) for k in a["iso_key"]])[a["iso"][sl]]
    S = (sw * qr * np.exp(-C2 * a["elower"][sl] * (1.0 / T - 1.0 / T_REF))
         * (-np.expm1(-C2 * nu0 / T)) / (-np.expm1(-C2 * nu0 / T_REF)))
    gam_l = (T_REF / T) ** a["n_air"][sl] * (a["gamma_air"][sl] * (p_atm - p_self) + a["gamma_self"][sl] * p_self)
    nu_c = nu0 + a["delta_air"][sl] * p_atm
    gam_d = 3.581165e-7 * nu0 * np.sqrt(T / a["mass"][a["iso"][sl]])   # Doppler HWHM, cm-1
    keep = S >= s_min
    return S[keep], nu_c[keep], gam_l[keep], gam_d[keep]


def cross_section(gas: str, p_pa: float, T: float, x_self: float = 0.0, nu_min: float = 10.0,
                  nu_max: float = 4000.0, step: float = 0.01, wing_hw: float = 50.0,
                  wing_max: float = 25.0, s_min: float = 1.0e-30, max_chunk: int = 3_000_000):
    """Absorption cross-section sigma (cm2 molecule-1) on the grid nu_min + i*step.

    Voigt profiles evaluated on +-``wing_hw`` Lorentz half-widths of each line (at most
    ``wing_max`` cm-1); lines weaker than ``s_min`` (cm molecule-1) are dropped.
    Returns ``(nu, sigma)``.
    """
    from scipy.special import voigt_profile

    n_pts = int(round((nu_max - nu_min) / step)) + 1
    nu = nu_min + step * np.arange(n_pts)
    S, nuc, gl, gd = line_parameters(gas, p_pa, T, x_self, nu_min, nu_max, wing_hw, wing_max, s_min)
    sig = np.zeros(n_pts)
    # half-window in grid points per line; bucket lines by next power of two to limit padding
    w = np.minimum(wing_hw * np.maximum(gl, 3.0 * gd), wing_max)
    n_half = np.maximum(np.ceil(w / step).astype(np.int64), 2)
    klass = np.ceil(np.log2(n_half)).astype(np.int64)
    sg = gd / np.sqrt(2.0 * np.log(2.0))
    for k in np.unique(klass):
        sel = np.nonzero(klass == k)[0]
        n = 2 ** int(k)
        offs = np.arange(-n, n + 1)
        per = max(1, max_chunk // offs.size)
        for a in range(0, sel.size, per):
            j = sel[a:a + per]
            ic = np.rint((nuc[j] - nu_min) / step).astype(np.int64)
            idx = ic[:, None] + offs[None, :]
            ok = (idx >= 0) & (idx < n_pts)
            x = nu_min + step * idx - nuc[j][:, None]
            prof = voigt_profile(x, sg[j][:, None], gl[j][:, None])
            sig += np.bincount(idx[ok], weights=(S[j][:, None] * prof)[ok], minlength=n_pts)
    return nu, sig
