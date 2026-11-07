"""Build the spectral tables for the web app from HITRAN line parameters and cross-sections.

Run (after build/fetch_hitran.py and downloading the HITRAN .xsc files), from the repository root:
    python build/build_spectra.py

Outputs (all derived products; raw HITRAN data are NOT redistributed)
  web/public/data/spectra/gases.json      metadata of the 22 molecules (names, groups, colours, coverage, AR6 values)
  web/public/data/spectra/lab_<GAS>.json  band-averaged transmission of an absorber column, 2 (p, T) conditions,
                                          19 columns (10^15 ... 10^24 molecules cm-2)
  web/public/data/spectra/olr.json        clear-sky and all-sky outgoing longwave spectra, one-gas sweeps (CO2, CH4,
                                          N2O, O3, H2O) + cloud-model metadata
  web/public/data/spectra/olr_halo.json   the same for the 17 halocarbons, stored as difference spectra
  web/public/data/spectra/bands.json      vibrational band annotations
  data/cache/spectra/                     cached cross-sections (git-ignored, regenerable)

Physics summary
  * H2O, CO2, CH4, N2O, O3: HITRAN2020 lines, Voigt profiles (radforce.spectra.lbl).  H2O lines are cut 25 cm-1 from
    line centre and combined with the MT_CKD 4.3 continuum (which is defined relative to that cut-off).
  * Halocarbons: HITRAN infrared cross-sections (radforce.spectra.xsec), nearest (T, p) file per layer.
  * All-sky: one grey cloud deck (cover 0.67, 5-6 km) whose optical depth is tuned so the model's longwave cloud radiative
    effect equals the CERES EBAF Ed4.0 value of 27.9 W m-2 (Loeb et al. 2018, J. Climate 31, Table 5).
Memory: peak about 2 GB.
"""
from __future__ import annotations

import json
import time
import warnings
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

from radforce.constants import PREINDUSTRIAL_1750 as PI
from radforce.data import ar6_concentrations
from radforce.forcing.halogens import radiative_efficiency
from radforce.spectra import atmosphere as A
from radforce.spectra import continuum, lbl, rt
from radforce.spectra.xsec import XscLibrary

warnings.simplefilter("ignore")
ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache" / "spectra"
OUT = ROOT / "web" / "public" / "data" / "spectra"

NU0, NU1 = 10.0, 4000.0
STEP = 0.02                 # cm-1; convergence tested (tests/test_spectra_lbl.py)
STEP_UPPER_CELL = 0.005     # narrower lines at low pressure
BIN = 1.0                   # cm-1, output bin width
NBINS = int(round((NU1 - NU0) / BIN))
OLR_GASES = ["H2O", "CO2", "O3", "N2O", "CH4"]
H2O_WING_HW = 1000.0        # => the 25 cm-1 line cut-off that the MT_CKD continuum assumes
LOG10_COLUMNS = np.arange(15.0, 24.01, 0.5)    # lab-cell absorber columns, molecules cm-2

LAB_CONDITIONS = {
    "surface": dict(p_atm=1.0, T=296.0, step=STEP, x_h2o=0.01, label="1 atm, 296 K"),
    "upper": dict(p_atm=0.25, T=220.0, step=STEP_UPPER_CELL, x_h2o=0.001, label="0.25 atm, 220 K (about 10 km)"),
}

# global-mean cloud model (see module docstring)
CLOUD_COVER = 0.67          # global-mean total cloud fraction (satellite climatologies)
CLOUD_DECK_KM = 5.5         # effective deck height (assumption; sensitivity reported in docs/validation.md)
LW_CRE_TARGET = 27.9        # W m-2, CERES EBAF Ed4.0 global mean, Jul 2005-Jun 2015 (Loeb et al. 2018, Table 5)

SWEEPS = {
    "CO2": dict(unit="ppm", values=[69.575, 139.15, 278.3, 409.85, 556.6, 834.9, 1113.2, 2226.4, 4452.8]),
    "CH4": dict(unit="ppb", values=[0.0, 729.2, 1866.3, 3000.0, 5000.0, 10000.0]),
    "N2O": dict(unit="ppb", values=[0.0, 270.1, 332.1, 450.0, 600.0, 1000.0]),
    "O3": dict(unit="DU", values=[0.0, 150.0, 300.0, 450.0]),
    "H2O": dict(unit="x US-standard column", values=[0.5, 1.0, 1.5, 2.0]),
}
BASE = dict(CO2=PI["CO2"], CH4=PI["CH4"], N2O=PI["N2O"], O3=300.0, H2O=1.0)
HALO_MULTIPLES = [1, 3, 10, 30, 100, 300, 1000]     # of the 2019 mixing ratio

# name -> (group, formula html, colour, long name); order = display order
GAS_INFO = {
    "H2O": ("Major gases", "H₂O", "#1b9aaa", "Water vapour"), "CO2": ("Major gases", "CO₂", "#2b7bd0", "Carbon dioxide"),
    "CH4": ("Major gases", "CH₄", "#e8871e", "Methane"), "N2O": ("Major gases", "N₂O", "#2e9e5b", "Nitrous oxide"),
    "O3": ("Major gases", "O₃", "#c0566b", "Ozone"),
    "CFC-11": ("CFCs", "CFC-11", "#7b3294", "CCl₃F"), "CFC-12": ("CFCs", "CFC-12", "#9e4fc0", "CCl₂F₂"),
    "CFC-113": ("CFCs", "CFC-113", "#5e3c99", "C₂Cl₃F₃"), "CFC-114": ("CFCs", "CFC-114", "#b48ad9", "C₂Cl₂F₄"),
    "HCFC-22": ("HCFCs", "HCFC-22", "#a6611a", "CHClF₂"), "HCFC-141b": ("HCFCs", "HCFC-141b", "#c98a3b", "CH₃CCl₂F"),
    "HCFC-142b": ("HCFCs", "HCFC-142b", "#8c510a", "CH₃CClF₂"),
    "HFC-23": ("HFCs", "HFC-23", "#01665e", "CHF₃"), "HFC-32": ("HFCs", "HFC-32", "#35978f", "CH₂F₂"),
    "HFC-125": ("HFCs", "HFC-125", "#80cdc1", "CHF₂CF₃"), "HFC-134a": ("HFCs", "HFC-134a", "#2c7fb8", "CH₂FCF₃"),
    "HFC-143a": ("HFCs", "HFC-143a", "#41b6c4", "CH₃CF₃"),
    "SF6": ("PFCs and SF₆", "SF₆", "#d62728", "SF₆"), "CF4": ("PFCs and SF₆", "CF₄", "#ff7f0e", "CF₄"),
    "C2F6": ("PFCs and SF₆", "C₂F₆", "#e377c2", "C₂F₆"), "C3F8": ("PFCs and SF₆", "C₃F₈", "#8c564b", "C₃F₈"),
    "CCl4": ("Other", "CCl₄", "#4d4d4d", "Carbon tetrachloride"),
}
HALOS = [g for g, v in GAS_INFO.items() if v[0] != "Major gases"]

# Vibrational fundamentals (cm-1) from standard spectroscopy references (Herzberg; Rothman et al.).
BANDS = {
    "H2O": [dict(nu=1595, label="ν₂ bend (6.3 µm)"), dict(nu=3657, label="ν₁ symmetric stretch"),
            dict(nu=3756, label="ν₃ asymmetric stretch"), dict(nu=300, label="pure rotation (far-IR)")],
    "CO2": [dict(nu=667, label="ν₂ bend (15 µm)"), dict(nu=2349, label="ν₃ asymmetric stretch (4.3 µm)")],
    "CH4": [dict(nu=1306, label="ν₄ bend (7.7 µm)"), dict(nu=3019, label="ν₃ stretch (3.3 µm)")],
    "N2O": [dict(nu=589, label="ν₂ bend (17 µm)"), dict(nu=1285, label="ν₁ stretch (7.8 µm)"),
            dict(nu=2224, label="ν₃ stretch (4.5 µm)")],
    "O3": [dict(nu=1042, label="ν₃ asymmetric stretch (9.6 µm)"), dict(nu=701, label="ν₂ bend (14 µm)"),
           dict(nu=1103, label="ν₁ symmetric stretch")],
    "SF6": [dict(nu=948, label="ν₃ S–F stretch (10.5 µm)")],
    "CF4": [dict(nu=1283, label="ν₃ C–F stretch (7.8 µm)")],
    "CFC-12": [dict(nu=1161, label="ν₁ (8.6 µm)"), dict(nu=922, label="ν₈ (10.8 µm)")],
    "CFC-11": [dict(nu=1085, label="ν₁ C–F (9.2 µm)"), dict(nu=846, label="ν₄ C–Cl (11.8 µm)")],
    "CCl4": [dict(nu=794, label="ν₃ C–Cl stretch (12.6 µm)")],
}

_LIB: XscLibrary | None = None


def xsc() -> XscLibrary:
    global _LIB
    if _LIB is None:
        _LIB = XscLibrary()
    return _LIB


def binned_mean(y: np.ndarray, step: float) -> np.ndarray:
    """Average a uniform-grid array (starting at NU0) into 1 cm-1 bins."""
    per = int(round(BIN / step))
    n = (y.size // per) * per
    return y[:n].reshape(-1, per).mean(axis=1)[:NBINS]


def grid(step: float) -> np.ndarray:
    return NU0 + step * np.arange(int(round((NU1 - NU0) / step)) + 1)


def sigma(gas: str, i: int, layers: A.Layers) -> np.ndarray:
    """Cached float32 line-by-line cross-section of ``gas`` in layer ``i`` (cm2/molecule), STEP grid.

    For H2O this is the LINE part only (25 cm-1 cut-off); the continuum is added separately.
    """
    tag = "_w25" if gas == "H2O" else ""
    f = CACHE / f"sigma_{gas}_{STEP}{tag}_L{i}.npy"
    if f.exists():
        return np.load(f)
    x_self = float(layers.vmr[gas][i]) if gas == "H2O" else 0.0
    wing = H2O_WING_HW if gas == "H2O" else 50.0
    _, s = lbl.cross_section(gas, layers.p_mid[i], layers.T_mid[i], x_self, NU0, NU1, STEP, wing_hw=wing)
    s = s.astype(np.float32)
    np.save(f, s)
    return s


def sigma_halo(mol: str, i: int, layers: A.Layers, nu: np.ndarray) -> np.ndarray:
    """Cached float32 halocarbon cross-section in layer ``i`` from the HITRAN .xsc library."""
    f = CACHE / f"sigmaX_{mol}_{STEP}_L{i}.npy"
    if f.exists():
        return np.load(f)
    s, _ = xsc().sigma(mol, float(layers.T_mid[i]), float(layers.p_mid[i]), nu)
    s = s.astype(np.float32)
    np.save(f, s)
    return s


def intervals(mask: np.ndarray, nu: np.ndarray) -> list[list[float]]:
    """Merge a boolean coverage mask into [lo, hi] wavenumber intervals."""
    out, start = [], None
    for k, m in enumerate(mask):
        if m and start is None:
            start = nu[k]
        if (not m) and start is not None:
            out.append([round(float(start), 2), round(float(nu[k - 1]), 2)])
            start = None
    if start is not None:
        out.append([round(float(start), 2), round(float(nu[-1]), 2)])
    return out


def conc_ppt(mol: str) -> tuple[float, float]:
    c = ar6_concentrations()
    return float(c.loc[1750, mol]), float(c.loc[2019, mol])


def build_meta(base: A.Layers) -> dict:
    meta = {}
    n_air = float(base.n_air.sum())
    for g, (grp, html, colour, name) in GAS_INFO.items():
        rec = {"id": g, "group": grp, "html": html, "colour": colour, "name": name,
               "source": "lines" if g in OLR_GASES else "xsec", "bands": BANDS.get(g, [])}
        if g in OLR_GASES:
            rec["n_atm"] = float(base.columns[g].sum())
            rec["coverage"] = [[NU0, NU1]]
        else:
            c1750, c2019 = conc_ppt(g)
            rec.update(c1750_ppt=c1750, c2019_ppt=c2019, n_atm=c2019 * 1e-12 * n_air, ar6_re=radiative_efficiency(g))
            lib = xsc()
            nu = grid(0.1)
            _, cov = lib.sigma(g, 288.0, A.P0, nu)
            rec["coverage"] = intervals(cov, nu)
            rec["datasets"] = [dict(range=[round(s_[0].nu_min), round(s_[0].nu_max)], files=len(s_),
                                    T=[round(min(f.T for f in s_)), round(max(f.T for f in s_))],
                                    p_torr=[round(min(f.p_torr for f in s_), 1), round(max(f.p_torr for f in s_), 1)],
                                    ref=s_[0].ref, broadener=s_[0].broadener) for s_ in lib.groups(g)[:4]]
        meta[g] = rec
    return meta


def lab_sigma(gas: str, cond: dict):
    """Cross-section on the condition's grid, plus a coverage mask."""
    step = cond["step"]
    nu = grid(step)
    if gas in OLR_GASES:
        x = cond["x_h2o"] if gas == "H2O" else 0.0
        wing = H2O_WING_HW if gas == "H2O" else 50.0
        _, s = lbl.cross_section(gas, cond["p_atm"] * A.P0, cond["T"], x, NU0, NU1, step, wing_hw=wing)
        if gas == "H2O":
            s = s + continuum.sigma(nu, cond["T"], cond["p_atm"] * A.P0, x)
        return nu, s, np.ones(nu.size, dtype=bool)
    s, cov = xsc().sigma(gas, cond["T"], cond["p_atm"] * A.P0, nu)
    return nu, s, cov


def build_lab_cell(meta: dict) -> None:
    for gas in GAS_INFO:
        t0 = time.time()
        rec = {"gas": gas, "n_atm": meta[gas]["n_atm"], "log10_columns": LOG10_COLUMNS.tolist(),
               "nu_start": NU0 + BIN / 2, "dnu": BIN, "conditions": {}, "t": {}, "covered": {}}
        for cname, c in LAB_CONDITIONS.items():
            nu, s, cov = lab_sigma(gas, c)
            rows = []
            for m in LOG10_COLUMNS:
                t = binned_mean(np.exp(-s * 10.0 ** m), c["step"])
                rows.append(np.rint(t * 1000).astype(int).tolist())
            rec["conditions"][cname] = {k: c[k] for k in ("p_atm", "T", "label")}
            rec["t"][cname] = rows
            rec["covered"][cname] = intervals(cov, nu)
        (OUT / f"lab_{gas}.json").write_text(json.dumps(rec, separators=(",", ":")))
        print(f"lab cell {gas}: {time.time() - t0:.0f}s", flush=True)


# ----------------------------------------------------------------------------------------------------------------------
# Outgoing spectra
# ----------------------------------------------------------------------------------------------------------------------
class Atmos:
    """Reference atmosphere with all cross-sections in memory; computes clear-sky and all-sky outgoing flux."""

    def __init__(self):
        self.ref = A.build_layers(co2_ppm=BASE["CO2"], ch4_ppb=BASE["CH4"], n2o_ppb=BASE["N2O"], o3_du=BASE["O3"])
        self.nu = grid(STEP)
        n = len(self.ref.p_mid)
        self.sig = {}
        for g in OLR_GASES:
            t0 = time.time()
            self.sig[g] = np.stack([sigma(g, i, self.ref) for i in range(n)])
            print(f"sigma {g}: {time.time() - t0:.0f}s", flush=True)
        self.base_cols = {g: self.ref.columns[g].copy() for g in OLR_GASES}
        self.deck = int(np.searchsorted(list(self.ref.z_edges_km), CLOUD_DECK_KM, side="right") - 1)
        self.tau_c = 0.0
        self.halo_sig: dict[str, np.ndarray] = {}
        self._cont: dict[float, np.ndarray] = {}

    def cont(self, scale: float) -> np.ndarray:
        """MT_CKD continuum cross-section per layer when all H2O amounts are multiplied by ``scale``."""
        if scale not in self._cont:
            r = self.ref
            self._cont[scale] = np.stack([continuum.sigma(self.nu, r.T_mid[i], r.p_mid[i], float(r.vmr["H2O"][i]) * scale)
                                          for i in range(len(r.p_mid))])
        return self._cont[scale]

    def tau(self, cols: dict, h2o_scale: float = 1.0, halo: dict | None = None) -> np.ndarray:
        t = np.zeros((len(self.ref.p_mid), self.nu.size))
        for g in OLR_GASES:
            if g == "H2O":
                t += (self.sig["H2O"] + self.cont(h2o_scale)) * cols["H2O"][:, None]
            else:
                t += self.sig[g] * cols[g][:, None]
        for mol, ppt in (halo or {}).items():
            if mol not in self.halo_sig:
                self.halo_sig[mol] = np.stack([sigma_halo(mol, i, self.ref, self.nu) for i in range(len(self.ref.p_mid))])
            t += self.halo_sig[mol] * (ppt * 1e-12 * self.ref.n_air)[:, None]
        return t

    def flux(self, tau: np.ndarray, cloudy: bool = False) -> np.ndarray:
        if cloudy:
            tau = self._with_deck(tau, self.tau_c)
        return rt.upward_flux(self.nu, tau, self.ref.T_mid, self.ref.T_surface)

    def _with_deck(self, tau, tc):
        t = tau.copy()
        t[self.deck] += tc
        return t

    def calibrate_cloud(self, tau_base: np.ndarray) -> dict:
        """Tune the deck's grey optical depth so the model LW CRE equals the observed value."""
        clear = rt.total(self.nu, self.flux(tau_base))

        def resid(tc):
            f = rt.upward_flux(self.nu, self._with_deck(tau_base, tc), self.ref.T_mid, self.ref.T_surface)
            return CLOUD_COVER * (clear - rt.total(self.nu, f)) - LW_CRE_TARGET

        self.tau_c = float(brentq(resid, 1e-4, 50.0))
        allsky = rt.total(self.nu, self.allsky(tau_base)[0])
        return {"cover": CLOUD_COVER,
                "deck_km": [float(self.ref.z_edges_km[self.deck]), float(self.ref.z_edges_km[self.deck + 1])],
                "tau_c": self.tau_c, "target_lw_cre": LW_CRE_TARGET, "model_lw_cre": clear - allsky,
                "model_clear_olr": clear, "model_allsky_olr": allsky, "ceres_clear_olr": 268.1, "ceres_allsky_olr": 240.1,
                "source": "CERES EBAF Ed4.0, Jul 2005-Jun 2015, Loeb et al. (2018) J. Climate 31, Table 5"}

    def allsky(self, tau: np.ndarray):
        """(all-sky spectral flux, clear spectral flux): (1 - f) clear + f deck."""
        clear = self.flux(tau)
        deck = self.flux(tau, cloudy=True)
        return (1 - CLOUD_COVER) * clear + CLOUD_COVER * deck, clear


def _bin(y: np.ndarray) -> np.ndarray:
    return binned_mean(y, STEP)


def build_olr(meta: dict) -> None:
    at = Atmos()
    tau0 = at.tau(at.base_cols)
    cloud = at.calibrate_cloud(tau0)
    print(f"cloud model: tau_c={cloud['tau_c']:.3f}; clear OLR {cloud['model_clear_olr']:.1f}, all-sky "
          f"{cloud['model_allsky_olr']:.1f} (CERES 268.1 / 240.1)", flush=True)

    def run(tau):
        allsky, clear = at.allsky(tau)
        return rt.total(at.nu, clear), rt.total(at.nu, allsky), clear, allsky

    olr0, olr0_all, c0, a0 = run(tau0)
    out = {"nu_start": NU0 + BIN / 2, "dnu": BIN, "T_surface": at.ref.T_surface, "cloud": cloud,
           "baseline": {"olr": olr0, "olr_all": olr0_all, "spec": np.round(_bin(c0), 5).tolist(),
                        "spec_all": np.round(_bin(a0), 5).tolist(), "gases": BASE},
           "sweeps": {}, "notes": "US-standard 1976 temperature; MT_CKD 4.3 continuum; clear-sky and cloud-model all-sky"}
    print(f"baseline clear OLR {olr0:.2f}, all-sky {olr0_all:.2f}", flush=True)

    def entry(value, cols, h2o_scale=1.0):
        o, oa, c, a = run(at.tau(cols, h2o_scale))
        return {"value": value, "olr": o, "irf": olr0 - o, "olr_all": oa, "irf_all": olr0_all - oa,
                "spec": np.round(_bin(c), 5).tolist(), "spec_all": np.round(_bin(a), 5).tolist()}

    for gas, sw in SWEEPS.items():
        entries = []
        for v in sw["values"]:
            cols = {g: at.base_cols[g].copy() for g in OLR_GASES}
            h2o = 1.0
            if gas == "H2O":
                cols["H2O"] = at.base_cols["H2O"] * v
                h2o = v
            else:
                cols[gas] = cols[gas] * (v / BASE[gas])
            e = entry(v, cols, h2o)
            entries.append(e)
            print(f"  {gas}={v:g}: forcing clear {e['irf']:+.3f}  all-sky {e['irf_all']:+.3f}", flush=True)
        out["sweeps"][gas] = {"unit": sw["unit"], "entries": entries}
    cols = {g: at.base_cols[g].copy() for g in OLR_GASES}
    for g, v in (("CO2", 409.85), ("CH4", 1866.3), ("N2O", 332.1)):
        cols[g] = cols[g] * v / BASE[g]
    out["all_2019"] = entry(None, cols)
    print(f"  all 3 GHG 2019: clear {out['all_2019']['irf']:+.3f}  all-sky {out['all_2019']['irf_all']:+.3f}", flush=True)
    (OUT / "olr.json").write_text(json.dumps(out, separators=(",", ":")))

    # ------------------------------------------------------------------ halocarbons (difference spectra, microW m-2 per cm-1)
    base_spec, base_all = _bin(c0), _bin(a0)
    halo_out = {"cloud": cloud, "multiples": HALO_MULTIPLES, "unit_dspec": "uW m-2 per cm-1", "gases": {}}
    re_rows = {}
    for mol in HALOS:
        c1750, c2019 = conc_ppt(mol)
        entries = []
        for v in [c1750] + [c2019 * m for m in HALO_MULTIPLES]:
            # the amount above the 1750 level is what is added to the (1750) reference atmosphere
            o, oa, c, a = run(at.tau(at.base_cols, 1.0, {mol: v - c1750}))
            entries.append({"value": v, "olr": o, "irf": olr0 - o, "olr_all": oa, "irf_all": olr0_all - oa,
                            "dspec": np.rint((_bin(c) - base_spec) * 1e6).astype(int).tolist(),
                            "dspec_all": np.rint((_bin(a) - base_all) * 1e6).astype(int).tolist()})
        o, oa, _, _ = run(at.tau(at.base_cols, 1.0, {mol: 10.0}))      # radiative efficiency from 10 ppt, per ppb
        re_clear, re_all = (olr0 - o) / 0.01, (olr0_all - oa) / 0.01
        halo_out["gases"][mol] = {"unit": "ppt", "entries": entries, "re_clear": re_clear, "re_all": re_all,
                                  "re_ar6": meta[mol]["ar6_re"]}
        re_rows[mol] = (re_clear, re_all, meta[mol]["ar6_re"])
        print(f"  {mol}: RE clear {re_clear:.3f}  all-sky {re_all:.3f}  AR6 {meta[mol]['ar6_re']:.3f}  "
              f"(ratio {re_all / meta[mol]['ar6_re']:.2f})", flush=True)
    (OUT / "olr_halo.json").write_text(json.dumps(halo_out, separators=(",", ":")))
    d = {e["value"]: e for e in out["sweeps"]["CO2"]["entries"]}
    summary = {"co2_2x_clear": d[556.6]["irf"] - d[278.3]["irf"], "co2_2x_all": d[556.6]["irf_all"] - d[278.3]["irf_all"],
               "re": re_rows, "cloud": cloud, "baseline_olr": [olr0, olr0_all]}
    (CACHE / "build_summary.json").write_text(json.dumps(summary))


if __name__ == "__main__":
    CACHE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    base = A.build_layers()
    meta = build_meta(base)
    (OUT / "gases.json").write_text(json.dumps(meta, separators=(",", ":")))
    (OUT / "bands.json").write_text(json.dumps(BANDS))
    build_lab_cell(meta)
    build_olr(meta)
    print("done")
