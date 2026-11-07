"""Stratosphere-adjusted forcing (fixed dynamical heating) for 2 x CO2 and the 2019 CH4 and N2O -> adjustment.json.

Run from the repo root (needs the cached cross-sections written by build_spectra.py):
    python build/stratospheric_adjustment.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_spectra as BS                                       # noqa: E402
from radforce.spectra import adjust, rt                          # noqa: E402

OUT = BS.ROOT / "web/public/data/adjustment.json"
TROPOPAUSE_INTERFACE = 9        # interface below layer 9: z = 12 km, the lowest model layer wholly in the stratosphere


def ar6_reference() -> dict:
    """The AR6 expressions for the same changes: stratosphere-adjusted (SARF, no ERF factor) and effective forcing."""
    from radforce.forcing import wmghg
    pi = BS.PI
    sarf = lambda c, m, n: wmghg.wmghg_forcing(c, m, n, erf=False)
    erf = lambda c, m, n: wmghg.wmghg_forcing(c, m, n, erf=True)
    cases = {"2xCO2": (2 * pi["CO2"], pi["CH4"], pi["N2O"], "CO2"), "CH4_2019": (pi["CO2"], 1866.3, pi["N2O"], "CH4"),
             "N2O_2019": (pi["CO2"], pi["CH4"], 332.1, "N2O")}
    return {k: {"sarf": float(sarf(c, m, n)[g]), "erf": float(erf(c, m, n)[g])} for k, (c, m, n, g) in cases.items()}


def main():
    t0 = time.time()
    at = BS.Atmos()
    tau0 = at.tau(at.base_cols)
    cloud = at.calibrate_cloud(tau0)
    f, deck = BS.CLOUD_COVER, at.deck
    T, Ts, nu = at.ref.T_mid.copy(), at.ref.T_surface, at.nu
    z_edges = at.ref.z_edges_km

    def columns(tau, sky):
        if sky == "clear":
            return [(1.0, tau)]
        return [((1 - f), tau), (f, at._with_deck(tau, at.tau_c))]

    cases = {"2xCO2": {"CO2": 2.0 * BS.PI["CO2"], "label": "2 × CO₂ (278.3 → 556.6 ppm)"},
             "CH4_2019": {"CH4": 1866.3, "label": "CH₄ 1750 → 2019 (729 → 1866 ppb)"},
             "N2O_2019": {"N2O": 332.1, "label": "N₂O 1750 → 2019 (270 → 332 ppb)"}}
    out = {"tropopause_km": float(z_edges[TROPOPAUSE_INTERFACE]), "cloud": cloud, "z_mid_km": [float(z) for z in at.ref.z_mid_km], "cases": {}}
    for name, spec in cases.items():
        cols = {g: at.base_cols[g].copy() for g in BS.OLR_GASES}
        for g, v in spec.items():
            if g != "label":
                cols[g] = cols[g] * (v / BS.BASE[g])
        tau1 = at.tau(cols)
        rec = {"label": spec["label"]}
        for sky in ("clear", "all"):
            ref_c, new_c = columns(tau0, sky), columns(tau1, sky)
            n0 = adjust._combined_net(nu, ref_c, T, Ts)
            n1 = adjust._combined_net(nu, new_c, T, Ts)
            toa_irf, trop_irf = n0[-1] - n1[-1], n0[TROPOPAUSE_INTERFACE] - n1[TROPOPAUSE_INTERFACE]
            Tadj, it, res = adjust.adjust_stratosphere(nu, ref_c, new_c, T, Ts, TROPOPAUSE_INTERFACE)
            n2 = adjust._combined_net(nu, new_c, Tadj, Ts)
            rec[sky] = {"toa_irf": float(toa_irf), "tropopause_irf": float(trop_irf),
                        "toa_adjusted": float(n0[-1] - n2[-1]), "tropopause_adjusted": float(n0[TROPOPAUSE_INTERFACE] - n2[TROPOPAUSE_INTERFACE]),
                        "dT_strat": [float(x) for x in (Tadj - T)], "iterations": it, "residual_Wm2": res}
            print(f"{name:9s} {sky:5s}: TOA IRF {toa_irf:+.3f}  tropopause IRF {trop_irf:+.3f}  -> adjusted {n0[-1] - n2[-1]:+.3f} (TOA) "
                  f"{n0[TROPOPAUSE_INTERFACE] - n2[TROPOPAUSE_INTERFACE]:+.3f} (tropopause)  max dT {np.max(np.abs(Tadj - T)):.1f} K  "
                  f"it {it} res {res:.1e}  [{time.time() - t0:.0f}s]", flush=True)
        out["cases"][name] = rec
    out["ar6"] = ar6_reference()
    out["tropospheric_adjustment"] = {"CO2": 1.05, "CH4": 0.86, "N2O": 1.07}
    OUT.write_text(json.dumps(out, separators=(",", ":")))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
