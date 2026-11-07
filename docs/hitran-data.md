# Getting the HITRAN data

**You do not need this to use the site or to run the web app.** The repository already contains the derived spectra
(`web/public/data/spectra/`). You only need HITRAN if you want to **rebuild** those spectra, for example to add a
molecule or change the atmosphere.

The raw HITRAN files are not in the repository, because the HITRAN terms allow free research and teaching use but do not
allow redistributing the raw data. Each person downloads them with their own account.

There are two kinds of data. Both end up under `data/raw/`, which git ignores.

| What | For which molecules | How you get it | Goes to |
|---|---|---|---|
| **Line lists** (individual spectral lines) | H₂O, CO₂, O₃, N₂O, CH₄ (CF₄ is fetched too but not used for the lines viewer) | Automatic, with a script | `data/raw/hitran/` |
| **Infrared cross-sections** (`.xsc` files) | The 17 halocarbons | Manual download from the HITRAN website | `data/raw/hitran_xsec/<MOLECULE>/` |

## 1. Line lists (automatic)

```bash
source .venv/bin/activate
pip install hitran-api            # also in physics/requirements.txt
python build/fetch_hitran.py
```

The script uses HAPI, the official HITRAN Python interface, to download H₂O (4 isotopologues), CO₂ (4), O₃ (3), N₂O (4),
CH₄ (2) and CF₄ (1) between 10 and 4000 cm⁻¹. It skips tables that already exist. It takes a few minutes and needs an
internet connection. At the time of writing it works without logging in; if HITRAN changes that, log in at
<https://hitran.org> and follow the HAPI instructions on the site to add an API key.

## 2. Cross-sections for the halocarbons (manual)

1. Create a free account at <https://hitran.org> and log in.
2. Open the **Cross-sections** (IR absorption cross-sections) page, at <https://hitran.org/xsc/>.
3. For each molecule in the table below, select it and download **all** of its files (the whole data set, every
   temperature and pressure). A download is a zip file that contains many `.xsc` files and one `.bib` file (the
   citation). If the site offers one archive for everything, use it.
4. Unzip each archive into its own folder with the exact name in the right-hand column, so that the layout is:

```
data/raw/hitran_xsec/
├── CFC-11/   CCl3F_191.5K-49.8Torr_710.0-1290.0_115.xsc  ...  one .bib
├── CFC-12/   ...
└── ... (17 folders)
```

| Molecule | Also called | Folder name |
|---|---|---|
| CCl₃F | CFC-11 | `CFC-11` |
| CCl₂F₂ | CFC-12 | `CFC-12` |
| C₂Cl₃F₃ | CFC-113 | `CFC-113` |
| C₂Cl₂F₄ | CFC-114 | `CFC-114` |
| CHClF₂ | HCFC-22 | `HCFC-22` |
| CH₃CCl₂F | HCFC-141b | `HCFC-141b` |
| CH₃CClF₂ | HCFC-142b | `HCFC-142b` |
| CHF₃ | HFC-23 | `HFC-23` |
| CH₂F₂ | HFC-32 | `HFC-32` |
| C₂HF₅ | HFC-125 | `HFC-125` |
| CH₂FCF₃ | HFC-134a | `HFC-134a` |
| CH₃CF₃ | HFC-143a | `HFC-143a` |
| SF₆ | sulphur hexafluoride | `SF6` |
| CF₄ | PFC-14, tetrafluoromethane | `CF4` |
| C₂F₆ | PFC-116, hexafluoroethane | `C2F6` |
| C₃F₈ | PFC-218, octafluoropropane | `C3F8` |
| CCl₄ | carbon tetrachloride | `CCl4` |

The code reads the temperature, pressure and wavenumber range from the first line of each `.xsc` file, so the file names
do not matter, only that the files sit inside the right folder. Keep only the `.xsc` and `.bib` files; you can delete
any `.html` or other files that came in the archive.

The build expects all 17 folders; it is not written to skip a missing one (it stops with a `KeyError`). If you only want some molecules, remove the others from `GAS_INFO` in `build/build_spectra.py`. To check what you have:

```bash
python - <<'PY'
from radforce.spectra.xsec import XscLibrary
lib = XscLibrary()
for m in lib.molecules():
    lo, hi = lib.coverage(m)
    print(f"{m:10s} {len(lib.files[m]):4d} files  {lo:7.1f}-{hi:7.1f} cm-1")
PY
```

Expect 17 molecules and about 650 files in total (about 1.3 GB). A few older data sets (CFC-113, CFC-114, HCFC-142b,
HFC-143a, C₃F₈) did not record the pressure; the code treats them as roughly 1 atm and says so on the Spectra tab.

## 3. Build the spectra

```bash
python build/build_spectra.py      # about 30 minutes, under 2 GB of memory
python build/halocarbon_check.py
python build/cloud_sensitivity.py
```

`build_spectra.py` writes the JSON tables in `web/public/data/spectra/`. Commit those, not the raw HITRAN files.

## 4. Water-vapour continuum

The MT_CKD 4.3 continuum file (`data/raw/mtckd/absco-ref_wv-mt-ckd.nc`) is already in the repository with its licence
(`LICENSE.md`). If you ever need it again, it is distributed by Atmospheric and Environmental Research (AER) in the
MT_CKD repository on GitHub (`AER-RC/MT_CKD_H2O`).

## Citing HITRAN

Please cite both when you publish or teach with derived data:

- Gordon, I. E. et al. (2022), *The HITRAN2020 molecular spectroscopic database*, J. Quant. Spectrosc. Radiat. Transf.
  277, 107949.
- Kochanov, R. V. et al. (2016), *HITRAN Application Programming Interface (HAPI)*, J. Quant. Spectrosc. Radiat.
  Transf. 177, 15–30.

Each cross-section folder also carries its own `.bib` file with the original laboratory references.
