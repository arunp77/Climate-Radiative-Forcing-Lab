# Climate Radiative Forcing Lab

**An open, interactive tool for learning how greenhouse gases, aerosols and clouds change the energy balance of the Earth.**
It is aimed at undergraduate and postgraduate students, teachers and anyone curious about atmospheric physics. It runs entirely in the browser: no account, no server (anonymous visit statistics only: GoatCounter, plus Google Analytics if you accept cookies).

**Live site: <https://arunp77.github.io/Climate-Radiative-Forcing-Lab/>**

## What you can do with it

| Tab | You can… | Based on |
|---|---|---|
| **Forcing balance** | Change CO₂, CH₄, N₂O, halocarbons, ozone precursors, aerosols and see the effective radiative forcing of every agent, with AR6 uncertainty ranges. Equations are shown on request. | IPCC AR6 (Meinshausen et al. 2020 / Etminan et al. 2016 expressions, AR6 time series) |
| **History** | Play 1850–2019 year by year, or compare two years side by side. | IPCC AR6 time series |
| **Spectra** | See the infrared absorption of **22 molecules** (H₂O, CO₂, CH₄, N₂O, O₃ and 17 halocarbons), the spectrum leaving the Earth, saturation, a clear-sky / all-sky switch, and a worked example of why doubled CO₂ is about 2 W m⁻² instantaneously but 3.9 W m⁻² effectively. | HITRAN2020, MT_CKD continuum, own line-by-line and radiative-transfer code |
| **Warming** | Turn the forcing of five SSP scenarios into temperature, change the climate sensitivity and ocean mixing, and compare with thermometer records and the IPCC's assessed range. | FaIR v2, three-layer energy balance model, HadCRUT5, NOAA Mauna Loa |
| **GWP and GTP** | Compare 249 gases at 20, 100 and 500 years, see why lifetime and absorption decide the metric, and convert emissions to CO₂-equivalent. | IPCC AR6 method, recomputed |
| **Glossary** | Decode names such as CFC-11 or HFC-134a, look up the 22 molecules, and search about 80 terms. | IPCC AR6 and the Montreal Protocol texts |
| **About and sources** | Read the validation report, the cloud-model sensitivity study, the halocarbon check, the references and this project's notes. | |

## How accurate is it?

Every number comes from a published source or a documented calculation, and the code is checked against published values by automated tests (174 Python tests and 48 web tests at the time of writing). The headline comparisons are below; all of them, including the places where the model is off, are in [docs/validation.md](docs/validation.md).

| Check | Result |
|---|---|
| AR6 forcing expressions against the AR6 time series | CO₂, CH₄, N₂O < 0.001 W m⁻²; halogens within 0.6 % |
| Present-day outgoing radiation, clear / all-sky | 264.0 / 236.8 W m⁻² against 268.1 / 240.1 observed (CERES) |
| 2×CO₂ forcing: instantaneous → stratosphere-adjusted → effective (all-sky) | 2.01 → 3.82 → 4.02 W m⁻² against AR6 3.75 (adjusted) and 3.93 (effective) |
| 17 halocarbon radiative efficiencies against AR6 | 1.02–1.31 times AR6 (not used in tuning) |
| GWP / GTP for 136 halogenated gases with lifetime of at least a year | all within 1.6 % of AR6 Table 7.SM.7; CH₄ 27.9, N₂O 273 reproduced |
| Warming 2081–2100 for five SSPs | 1.36, 1.73, 2.59, 3.44, 4.27 K, inside the AR6 very likely ranges (about 0.1 K below the best estimates) |
| ECS and TCR of the energy balance model | 3.0 K and 1.7 K (AR6: 3 K and 1.8 K) |

**Known limitations** (also stated on the pages): one idealised atmospheric profile; one grey cloud deck whose opacity is tuned to the observed longwave cloud effect (27.9 W m⁻²), with the tuning target and the independent test named on the Spectra tab; methane forcing about 14 % below AR6's after stratospheric adjustment (cause not isolated); one deterministic FaIR run per scenario, so no ensemble spread; scenarios are not predictions.

## Run it locally

```bash
git clone https://github.com/arunp77/Climate-Radiative-Forcing-Lab.git
cd Climate-Radiative-Forcing-Lab/web
npm ci
npm run dev          # http://localhost:5173
```

The repository already contains every table the site needs, so no Python or data download is required to run or deploy it.

## Rebuild the data (optional)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r physics/requirements.txt
(cd physics && pytest)                  # about 80 s with the HITRAN data, a few seconds without (those tests skip)

python build/build_all.py               # forcing tables, metrics, observations, validation report, documents (fast)
python build/run_fair.py                # FaIR scenarios (downloads about 48 MB of RCMIP data on first use)
python build/stratospheric_adjustment.py   # needs the cached cross-sections below; about 2 minutes

# spectra: needs HITRAN data, see docs/hitran-data.md
python build/fetch_hitran.py
python build/build_spectra.py           # about 30 minutes, under 2 GB of memory
python build/halocarbon_check.py && python build/cloud_sensitivity.py
```

How to obtain the HITRAN files is explained step by step in **[docs/hitran-data.md](docs/hitran-data.md)**.

## Deploy

The site is static. The workflow in `.github/workflows/deploy-pages.yml` runs the Python and web tests, builds `web/` and publishes it to GitHub Pages on every push to `main`. `web/vercel.json` carries security headers for hosting on Vercel (root directory `web/`, build `npm run build`, output `dist`).

## Project layout

```
physics/            Python package "radforce": forcing, spectra, stratospheric adjustment, energy balance, metrics, with tests
build/              scripts that turn physics and data into the JSON tables the site loads, and the reports
data/               source data and data/MANIFEST.md (provenance and licence of every dataset)
docs/               validation report and other documents shown in the About tab
web/                the site (TypeScript, Vite, Plotly, KaTeX) and its tests
```

Design rules: physics lives in Python and is tested there; closed-form expressions are ported to TypeScript and cross-checked against the Python (to 1e-9, or to 0.002 K for the energy balance model against FaIR); expensive computation is done offline and shipped as tables; nothing shown is placeholder data.

## Data, licence and citation

- **Licence:** Creative Commons Attribution-NonCommercial-ShareAlike 4.0 (see [LICENSE](LICENSE)): free for teaching and learning, share and adapt with attribution, not for commercial use. Creative Commons recommends software licences for code, but this is the choice made for the project; if you prefer to reuse the code under a software licence, please write to arunp77@virta-ai.com.
- **Third-party data keep their own terms** (HITRAN and MT_CKD for research and teaching only; RCMIP-derived scenarios under CC BY-SA 4.0; HadCRUT5 under the Open Government Licence): see [NOTICE.md](NOTICE.md) and [data/MANIFEST.md](data/MANIFEST.md). The raw HITRAN files are not in the repository.
- **Cite** the tool with [CITATION.cff](CITATION.cff) (GitHub shows a "Cite this repository" button) and cite the data sources in [docs/references.md](docs/references.md).

## Feedback and contributions

Found an error, an unclear explanation or a gas that is missing? Please write to arunp77@virta-ai.com. A change that weakens a test tolerance or removes a check should say why in the commit message.

## What is not here yet

Policy and emissions-lever sandbox, carbon-cycle and remaining-budget calculator, one-dimensional radiative–convective model, other atmospheric profiles (tropical, sub-Arctic), non-uniform halocarbon profiles, lesson text with auto-checked problem sets. See the limitations above before using any result beyond teaching.
