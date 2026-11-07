"""HITRAN infrared absorption cross-section files (.xsc) for halocarbons and other heavy molecules.

Heavy molecules (CFCs, HFCs, SF6, PFCs...) have thousands of overlapping hot-band lines, so HITRAN
distributes measured cross-sections sigma(nu; T, p) in cm2 molecule-1 instead of line lists.

File format (HITRAN .xsc), header (Fortran A20,2F10.4,I7,F7.2,F6.1,E10.3,F5.3,3X,A15,A5,I3):
  molecule, nu_min, nu_max, n_points, T (K), p (Torr), sigma_max, resolution (cm-1), common name,
  broadener, reference id;   then the values, 10 per line in E10.3, on a uniform grid from nu_min to nu_max.
A pressure of 0.0 means the measurement pressure was not recorded (older data sets).

Data selection for a requested (T, p) -- see ``XscLibrary.sigma``:
  1. groups with a recorded pressure and an air-like broadener (a proper temperature x pressure grid),
     widest range first;
  2. temperature-only groups (pressure not recorded; treated as ~1 atm);
  3. everything else.
Within each group the file nearest in (T, ln p) is used; each wavenumber takes the highest-priority
group that covers it.  Outside every file's range sigma is taken as zero (flagged by ``coverage``).
Negative values (measurement noise) are clipped to zero.
The last data line is zero-padded to ten values; ``read_values`` drops the padding.
"""
from __future__ import annotations

import re
import warnings
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
XSC_DIR = ROOT / "data" / "raw" / "hitran_xsec"
TORR_PA = 101325.0 / 760.0
_NUM = re.compile(r"[-+]?\d*\.\d+[Ee][-+]?\d+")


@dataclass(frozen=True)
class XscFile:
    path: Path
    molecule: str
    nu_min: float
    nu_max: float
    n: int
    T: float
    p_torr: float
    sigma_max: float
    resolution: str
    name: str
    broadener: str
    ref: str

    @property
    def air_like(self) -> bool:
        return self.broadener.lower().startswith(("air", "n2"))


def parse_header(line: str, path: Path = Path("?")) -> XscFile:
    return XscFile(
        path=path, molecule=line[0:20].strip(), nu_min=float(line[20:30]), nu_max=float(line[30:40]),
        n=int(line[40:47]), T=float(line[47:54]), p_torr=float(line[54:60]), sigma_max=float(line[60:70]),
        resolution=line[70:75].strip(), name=line[78:93].strip(), broadener=line[93:98].strip(), ref=line[98:101].strip(),
    )


def read_values(path: Path) -> np.ndarray:
    """Cross-section values (cm2 molecule-1) of one file, in file order.

    Numbers are E10.3, but some files are not strictly fixed width and negative values can touch their
    neighbour, so scientific-notation tokens are extracted rather than columns sliced.  A token that does not
    parse (one such corrupted value exists: C2F6_284.1_520.5_1061.0-1165.0_02.xsc has '6341E-21') is replaced
    by zero, which is conservative for wing values, and a warning is issued.
    """
    vals: list[float] = []
    repairs = 0
    with open(path) as f:
        header = parse_header(f.readline(), path)
        for line in f:
            nums = _NUM.findall(line)
            toks = line.split()
            if len(nums) == len(toks):
                vals.extend(map(float, nums))
                continue
            for t in toks:                       # irregular line: parse token by token
                found = _NUM.findall(t)
                if len(found) == 1 and found[0] == t:
                    vals.append(float(t))
                elif len(found) > 1:             # touching tokens, e.g. '1.0E-21-2.0E-22'
                    vals.extend(map(float, found))
                else:
                    vals.append(0.0)
                    repairs += 1
    if repairs:
        warnings.warn(f"{path.name}: {repairs} unparseable value(s) replaced by 0", stacklevel=2)
    arr = np.asarray(vals)
    # the last line is zero-padded to ten values, so up to 9 extra trailing values are legitimate
    if not (header.n <= arr.size < header.n + 10):
        raise ValueError(f"{path.name}: header says {header.n} points, found {arr.size}")
    return arr[: header.n]


@lru_cache(maxsize=64)
def _cached_values(path: str) -> np.ndarray:
    return read_values(Path(path))


class XscLibrary:
    """All .xsc files under ``root/<MOLECULE>/``."""

    def __init__(self, root: Path = XSC_DIR):
        self.root = Path(root)
        self.files: dict[str, list[XscFile]] = {}
        for d in sorted(p for p in self.root.glob("*") if p.is_dir()):
            fl = []
            for f in sorted(d.glob("*.xsc")):
                with open(f) as fh:
                    fl.append(parse_header(fh.readline(), f))
            if fl:
                self.files[d.name] = fl

    def molecules(self) -> list[str]:
        return list(self.files)

    def groups(self, molecule: str) -> list[list[XscFile]]:
        """Files grouped by (range, reference, broadener), in priority order."""
        g: dict[tuple, list[XscFile]] = {}
        for f in self.files[molecule]:
            g.setdefault((round(f.nu_min), round(f.nu_max), f.ref, f.broadener), []).append(f)

        def priority(items):
            f0 = items[0]
            tier = 0 if (f0.p_torr > 0 and f0.air_like and len(items) >= 6) else 1 if f0.p_torr == 0 else 2
            return (tier, -(f0.nu_max - f0.nu_min), -len(items))

        return sorted(g.values(), key=priority)

    def coverage(self, molecule: str) -> tuple[float, float]:
        fl = self.files[molecule]
        return min(f.nu_min for f in fl), max(f.nu_max for f in fl)

    @staticmethod
    def _nearest(files: list[XscFile], T: float, p_torr: float) -> XscFile:
        def dist(f: XscFile) -> float:
            pf = f.p_torr if f.p_torr > 0 else 760.0          # unrecorded pressure: assume ~1 atm
            return ((T - f.T) / 15.0) ** 2 + (np.log(max(p_torr, 1.0) / max(pf, 1.0)) / np.log(2.0)) ** 2
        return min(files, key=dist)

    def sigma(self, molecule: str, T: float, p_pa: float, nu: np.ndarray):
        """Cross-section (cm2 molecule-1) on the grid ``nu`` and a boolean mask of covered points."""
        nu = np.asarray(nu, dtype=float)
        out = np.zeros(nu.size)
        filled = np.zeros(nu.size, dtype=bool)
        p_torr = p_pa / TORR_PA
        for group in self.groups(molecule):
            f = self._nearest(group, T, p_torr)
            m = (~filled) & (nu >= f.nu_min) & (nu <= f.nu_max)
            if not m.any():
                continue
            vals = _cached_values(str(f.path))
            grid = np.linspace(f.nu_min, f.nu_max, f.n)
            out[m] = np.interp(nu[m], grid, vals)
            filled |= m
        return np.clip(out, 0.0, None), filled

    def integrated_strength(self, f: XscFile) -> float:
        """Band-integrated cross-section of one file, cm molecule-1 (trapezoid)."""
        v = np.clip(_cached_values(str(f.path)), 0.0, None)
        return float(np.trapezoid(v, np.linspace(f.nu_min, f.nu_max, f.n)))
