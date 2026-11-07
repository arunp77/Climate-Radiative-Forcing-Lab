# Climate Radiative Forcing Lab

An open, interactive, scientifically rigorous web tool for teaching the atmospheric physics of greenhouse gases and climate change to undergraduate and postgraduate students, teachers and anyone else who wants to learn.

> **Status:** Phases 0, 1, 1b and 2 are built (forcing engine, balance sheet, year-by-year history, KaTeX equations, non-GHG forcers, spectra for 22 molecules with an all-sky estimate). Sections 3.1 and 3.2 give the exact implementation status; `docs/validation.md` lists every check against its published reference.

---

## 1. Goals and non-goals

**Goals**

- Teach *why* greenhouse gases warm the planet, from first principles (energy balance, radiative transfer, molecular spectra) up to AR6-level forcing, feedbacks, scenarios and policy.
- Every number the tool shows must be traceable to a published source or to a documented calculation, and must be checked by an automated test.
- Serve two audiences from one codebase: **Basic** mode (concepts, intuition, minimal equations) and **Advanced** mode (full derivations, units, uncertainties, parameter access).
- Be freely usable by the public: static hosting, no login, works on a laptop, a lecture projector and a phone.

**Non-goals**

- It is not a research-grade climate model. Reduced-complexity components (FaIR, two-layer energy balance, 1-D radiative-convective model) are used for teaching, and the interface says so wherever it matters.
- The policy module is a **stylised sandbox**, not a forecast.

**Inspiration (not a source of code or assets)**

- KCVS IR Windows (spectral windows and gas absorption): <https://applets.kcvs.ca/IRWindows/IRWindows.html>
- KCVS Radiative Forcing (forcing balance sheet): <https://applets.kcvs.ca/RadiativeForcing/index.html>
- En-ROADS (policy levers to climate outcomes): <https://en-roads.climateinteractive.org/scenario.html?v=26.11.0&p516=-50&p520=-100>
  (the `p516`/`p520` URL parameters encode slider settings, which is the model for our shareable-URL feature; see section 4)

All implementations here are original. Check each project's licence before reusing anything from them, and credit them as inspiration in the app's "About" page.

---

## 2. Architecture

```
Climate-Radiative-Forcing-Lab/
├── physics/                 # Python package "radforce": single source of truth
│   ├── radforce/forcing/    # AR6 ERF expressions, halogens, non-GHG emulators
│   ├── radforce/spectra/    # Planck, atmosphere, HITRAN line-by-line, cross-sections, MT_CKD continuum, RT
│   ├── (ebam, rcm, scenarios, policy: planned)
│   └── tests/               # validation against literature values
├── data/
│   ├── raw/                 # downloaded source data (HITRAN and caches are git-ignored; see data/MANIFEST.md)
│   └── MANIFEST.md          # every dataset: source, version, licence, retrieval date
├── build/                   # scripts: physics -> JSON tables for the web app, validation reports
├── web/                     # static front end (TypeScript + Plotly + KaTeX)
│   ├── public/data/         # precomputed tables produced by build/
│   └── src/                 # views, components
├── content/                 # lesson text, derivations, problem sets (planned)
├── docs/                    # validation.md, halocarbon_check.md, cloud_sensitivity.md
└── README.md
```

**Design rules**

1. **Physics lives in Python only** and is tested there. The web app never reimplements a formula that has no counterpart test; cheap closed-form expressions (CO₂/CH₄/N₂O forcing, non-GHG emulators, Planck) are ported to TypeScript, and cross-check tests compare the two implementations to 1e-9.
2. **Expensive computation happens offline.** Line-by-line spectra, radiative transfer and FaIR runs (planned) are precomputed into lookup tables shipped as static files. Sliders interpolate, so response is instant with no server.
3. **No placeholder data.** Anything shown to a student is real, cited data or a documented calculation.
4. **Reproducible builds.** Pinned dependency versions, a data manifest, and scripts that regenerate every table.

---

## 3. Scientific specification

### 3.1 Forcing balance sheet (IPCC AR6)

The tool computes **Effective Radiative Forcing (ERF)**, which includes rapid adjustments, relative to **1750**, and can also show **Instantaneous Radiative Forcing (IRF)** for CO₂ to teach the difference.

| Forcer | Treatment |
|---|---|
| CO₂, CH₄, N₂O | AR6 expressions (Meinshausen et al. 2020, based on Etminan et al. 2016), including CH₄/N₂O/CO₂ band overlap. The classic Myhre et al. 1998 (IPCC TAR) form is kept as a selectable "historical" option to show how the science evolved. |
| Halogenated gases (CFCs, HCFCs, HFCs, PFCs, SF₆) | Per-species radiative efficiency × concentration change (AR6 Table 7.SM.7), grouped for display. |
| Tropospheric ozone | Scaled from precursor emissions/concentrations per AR6 Section 6.4 and 7.3. |
| Stratospheric ozone | Scaled to equivalent effective stratospheric chlorine. |
| Aerosol-radiation and aerosol-cloud interactions | Present-day ERF (AR6) scaled by emissions of SO₂, BC, OC, NH₃ relative to baseline, with the nonlinearity documented. |
| Black carbon on snow, land-use albedo | Scaled per AR6 Chapter 7. |
| Contrails and aviation-induced cirrus; stratospheric water vapour | Included as small terms. |
| Solar and volcanic | Natural forcings from the CMIP6 forcing datasets; shown separately from anthropogenic. |

Rules:

- Every forcer has a **best estimate and a 5–95 % range**, drawn as uncertainty bands.
- The displayed AR6 baseline year is **2019** (the AR6 assessment year). Later years (to 2024 and beyond) come from the annual *Indicators of Global Climate Change* updates (Forster et al.), labelled as such.
- **Validation targets** are taken from the AR6 ERF time series bundled in `data/raw/ar6/` (see `data/MANIFEST.md`), not typed by hand. For 2019 vs 1750 that series gives CO₂ 2.156, CH₄ 0.544, N₂O 0.208, halogenated 0.408, total WMGHG 3.32, total anthropogenic 2.72 W m⁻², and ERF(2×CO₂) = 3.93 W m⁻². Its 2019 aerosol ERF is −1.06 W m⁻² (ari −0.22, aci −0.84). The −1.3 W m⁻² headline often quoted for AR6 is not an error: the AR6 construction scales aerosol forcing to the *assessed 2005–2014 mean* (ari −0.30, aci −1.00 W m⁻²) and SO₂ emissions have fallen since, so the 2019 value is smaller. Lesson text must state the period before quoting either number. The latest results are in `docs/validation.md`.

**Implementation status (Phase 1):** CO₂, CH₄, N₂O (three schemes) and halogenated species are implemented in `physics/radforce/forcing/` and reproduce the AR6 1850–2019 series to < 0.001 W m⁻² for the three gases and to ~0.002 W m⁻² (0.6 %) for halogens. Ozone, aerosols (ari and aci), black carbon on snow and stratospheric water vapour are computed by AR6-based emulators in `physics/radforce/forcing/nonghg.py`, normalised to reproduce AR6 exactly at 2019 drivers (documented accuracy in `docs/validation.md`; the aerosol–cloud shape factors are a least-squares fit to the AR6 median because the AR6 ensemble is not public); land use, contrails and halogenated gases are simple multipliers on the AR6 2019 value. The year-by-year history view (Phase 1b) and KaTeX equations are in place.

### 3.2 Spectral physics

**Implementation status (Phase 2):** implemented in `physics/radforce/spectra/` and shown in the *Spectra* tab.

- **Molecules (22):** H₂O, CO₂, CH₄, N₂O, O₃ from HITRAN2020 lines (own vectorised Voigt code validated against HAPI; H₂O with the MT_CKD 4.3 continuum and the 25 cm⁻¹ line cut-off it assumes) and 17 halocarbons from HITRAN cross-section files (CFC-11/12/113/114, HCFC-22/141b/142b, HFC-23/32/125/134a/143a, SF₆, CF₄, C₂F₆, C₃F₈, CCl₄; 97 % of the 2019 halogenated forcing). Lines are never drawn outside the laboratory-measured wavenumber range.
- **Views:** a molecule-by-molecule transmission viewer (absorber column 10¹⁵–10²⁴ molecules cm⁻², two pressure/temperature conditions, wavenumber or wavelength axis, band labels, window shading) and Earth's outgoing spectrum with one-gas sweeps, a difference spectrum showing where a gas removes radiation, a forcing-against-amount curve with the AR6 prediction overlaid, and a **clear-sky / all-sky toggle**.
- **All-sky estimate:** one grey cloud deck (cover 0.67, 5–6 km) whose opacity is tuned so the model's longwave cloud effect equals the observed 27.9 W m⁻² (CERES EBAF Ed4.0, Loeb et al. 2018, Table 5). The deck height is an assumption; its effect is reported in `docs/cloud_sensitivity.md`.
- **Validation (`docs/validation.md`, `docs/halocarbon_check.md`):** present-day clear/all-sky OLR 264.0/236.8 W m⁻² against 268.1/240.1 observed; 2×CO₂ top-of-atmosphere forcing 2.76 (clear) / 2.01 (all-sky) W m⁻² with equal steps per doubling; CH₄ and N₂O follow the √-law; the 17 halocarbon radiative efficiencies come out 1.02–1.31 (mean 1.15) times AR6's, with the AR6 values playing no part in the tuning.
- **Not yet done:** stratospheric adjustment (so forcings are instantaneous top-of-atmosphere values, not AR6 effective forcings), non-uniform halocarbon vertical profiles, other atmospheres (tropical, sub-Arctic), the 1-D radiative-convective model.
- **Build:** `python build/fetch_hitran.py`, download the `.xsc` files (see `data/MANIFEST.md`), then `python build/build_spectra.py` (about 30 minutes, under 2 GB RAM).

Students must see *why* gases differ in forcing efficiency.

- **Method:** line-by-line absorption cross-sections from **HITRAN** for H₂O, CO₂, CH₄, N₂O, O₃, and HITRAN infrared cross-sections for the halocarbons. Layer-by-layer Schwarzschild radiative transfer through a standard atmosphere produces the **outgoing longwave radiation (OLR) spectrum**, not a bare 288 K blackbody with overlays.
- **Views:**
  - Planck curves at selectable temperatures, with the surface (~288 K) and the cold emission level (~220 K) shown, so the CO₂ 15 µm "notch" is understood.
  - Per-gas optical depth/transmission with toggles.
  - The **8–12 µm atmospheric window** and which species fill it (O₃ at 9.6 µm, CFCs/HFCs/SF₆, water vapour continuum).
  - **Curve of growth:** change a gas amount and watch band centre saturate while the wings keep absorbing, which explains why CO₂ forcing is logarithmic and CH₄/N₂O forcing goes roughly as √concentration, while rare halocarbons stay linear.
  - Pressure and temperature broadening of lines (Lorentz/Voigt).
- **Teaching correctness note:** the common claim that N₂O is potent because it "absorbs in the window" is a misconception. N₂O's strong bands (~4.5, 7.8, 17 µm) sit at the window's edges. Its GWP comes from strong per-molecule absorption, a ~110-year lifetime and less-saturated bands. The window is where the halocarbons and ozone absorb. The lesson text must say this explicitly.

### 3.3 Energy balance, feedbacks and temperature (planned)

- **Zero-D model:** solar constant, albedo, emissivity; the 255 K versus 288 K greenhouse effect; Kiehl–Trenberth-style global energy budget.
- **Two-layer energy balance model** (Geoffroy et al. 2013; AR6-style calibration) for **transient** temperature response, ocean heat uptake, ECS vs TCR, Earth's energy imbalance.
- **Equilibrium shortcut** `ΔT_eq = ERF / λ` (λ = −feedback parameter, ≈ F₂ₓ/ECS) is shown only as *equilibrium/committed* warming and is never labelled "current temperature anomaly".
- **Feedback decomposition:** Planck, water vapour, lapse rate, surface albedo, cloud; with literature ranges.
- **1-D radiative-convective model:** surface temperature response to CO₂ and H₂O with and without convective adjustment (Manabe & Wetherald concept).

### 3.4 Carbon cycle and metrics (planned)

- Impulse-response carbon cycle (as in FaIR), airborne fraction, TCRE, remaining carbon budget.
- GWP and GTP calculator for 20/100/500-year horizons with species lifetimes and radiative efficiencies; students can reproduce the AR6 table.

### 3.5 Scenarios (planned)

- **Historical:** 1750 to the latest available year.
- **Future:** CMIP6 ScenarioMIP SSPs (SSP1-1.9, 1-2.6, 2-4.5, 3-7.0, 5-8.5) via **FaIR v2** with the AR6 calibrated ensemble, precomputed offline.
- **Comparison mode:** overlay any two scenarios on ERF, concentration, temperature and forcing-breakdown charts, with ensemble spread.

### 3.6 Policy sandbox (planned; clearly labelled "stylised")

- Levers: carbon price, renewable-energy support, deforestation/afforestation, methane regulation, F-gas phase-down, aerosol (air-quality) controls.
- Mechanism: lever → change in emissions relative to a chosen SSP baseline using documented, editable elasticities → FaIR-derived response tables → concentrations, ERF, temperature.
- The interface shows the elasticities used and states that they are illustrative. Co-benefits and trade-offs are displayed, notably that **cutting aerosols reduces cooling and raises ERF**.
- India-relevant content: regional aerosol loading and the Indo-Gangetic Plain, monsoon sensitivity, India's emission trajectory.

### 3.7 Observations module (planned)

Mauna Loa CO₂, NOAA global CH₄/N₂O, global temperature record (e.g. GISTEMP/HadCRUT5), and Earth's energy imbalance (CERES/ocean heat content). Students compare model output with observations.

### 3.8 Interaction patterns to adopt from the reference apps

Observed in the two KCVS applets (screenshots reviewed 2026-11-07). We reimplement the *ideas* only; **the visual design, icons and layout are our own**, and no code or assets are copied.

**From KCVS Radiative Forcing (year-by-year "forcing race")** *(built)*

- A **time slider with a Play/Pause button** that animates horizontal bars growing and shrinking per agent around a zero line, with a live **Net value** readout. A year box shows the exact year and can be typed into.
- Fixed axis limits during playback so bar lengths are comparable across years; an explanation for each agent.
- A **Scenarios / Case-study panel** with tabs per agent and guided questions (e.g. "cancel CO₂ warming with aerosols: which layer, what side effects?"). We make this a `content/` problem-set feature with answers checked against the model *(planned)*.
- *Our additions:* uncertainty whiskers, a compare-with-year overlay, and the same slider driving the historical AR6 series bundled in `data/`.

**From KCVS IR Windows (molecule-by-molecule spectra)** *(built)*

- A row of **molecule buttons** with our own molecule icons (SVG ball-and-stick drawings). Each click toggles a dedicated, colour-coded line; all lines can be shown together to see where the **window** is left open.
- Wavenumber axis (and a wavelength option); transmission on the y-axis.
- *Our additions:*
  - The Planck emission curves, the OLR spectrum and the shaded 8–12.5 µm window.
  - Per-gas column and temperature/pressure controls, so students see saturation and broadening.
  - Real HITRAN-derived data with the *source and conditions* labelled on screen; each curve states whether it is a lab-cell transmission or a top-of-atmosphere outgoing spectrum, since these answer different questions.
  - Band labels with the vibrational mode that causes them (e.g. CO₂ ν₂ bend at 667 cm⁻¹, O₃ ν₃ at 1042 cm⁻¹).
  - 17 halocarbons including the CFCs, HFCs and SF₆ that KCVS also shows, plus a clear-sky / all-sky toggle.

---

## 4. Pedagogy

- **Basic / Advanced toggle** on every module.
- Each module has: learning objectives, 5-minute guided exploration, derivation (collapsible), common misconceptions, and a short numerical problem set with auto-checked answers *(planned)*.
- Equations rendered with KaTeX, with symbols and units defined next to every slider.
- Every chart and number has an info (ℹ) panel with the formula, assumptions and a citation.
- Instructor mode: shareable URLs that encode slider state, so a lecturer can send students to an exact configuration (built for the balance sheet; tab deep links `#history`, `#spectra`).

---

## 5. Technical stack

| Layer | Choice | Reason |
|---|---|---|
| Physics and data build | Python ≥ 3.10; numpy, scipy, pandas, xarray; `fair` (FaIR v2, tests and planned scenarios); `hitran-api` (HAPI: line download and test reference) | Scientific standard, testable |
| Front end | TypeScript + Vite; Plotly.js for charts; KaTeX for math | Static, fast, no server |
| Tests | pytest (physics), Vitest (front end) | Automated verification |
| CI | GitHub Actions: lint, tests, rebuild tables, build site *(planned)* | Reproducibility |
| Hosting | Vercel (static) as the public site; same build also runs locally | Free, no server needed |

**Theme:** light mode, clean sans-serif typography, a consistent colour per gas across charts, responsive from phone to projector, keyboard-operable controls.

---

## 6. Development roadmap

Each phase ends with passing tests and a deployable build.

1. **Phase 0, scaffolding:** repo layout, pinned environments, data manifest. *(done)*
2. **Phase 1, forcing engine** *(done: engine, tests, balance-sheet page, KaTeX equations, non-GHG emulators)*; **Phase 1b** *(done)* adds the animated year slider with Play/Pause and net-value readout from section 3.8.
3. **Phase 2, spectral module** *(done for the 22 molecules, MT_CKD continuum and the all-sky estimate; stratospheric adjustment and other atmospheres remain)*: HITRAN pipeline, the molecule-toggle viewer of section 3.8, Schwarzschild RT, OLR/transmission tables, curve-of-growth and window views.
4. **Phase 3, scenarios:** FaIR ensemble runs for the SSPs, comparison mode, two-layer EBM, observations overlay.
5. **Phase 4, the rest:** zero-D and RCM modules, feedbacks, carbon cycle/GWP calculator, policy sandbox.
6. **Phase 5, content and polish:** lesson text, problem sets, accessibility audit, public launch.

---

## 7. Validation and quality bar

- Every physics function has a unit test against a published number with the tolerance and source stated in the test.
- A **validation report** (`docs/validation.md`) is generated from the built data and lists each check, the reference and the result; `docs/halocarbon_check.md` and `docs/cloud_sensitivity.md` document the halocarbon and cloud-model checks.
- Where a model component is *tuned*, the tuning target (an observation) and the independent test (a different quantity) are named, so the reader can tell calibration from validation.
- Dimensional/unit checks on all public functions; no unlabelled quantities in the UI.
- Any figure shown in lesson text is produced by the same code as the interactive version.
- A change that weakens a test tolerance or removes a check must be justified in the commit message.

---

## 8. Running locally

```bash
git clone <repo-url> && cd Climate-Radiative-Forcing-Lab

# Physics + tables (optional: prebuilt tables are committed)
python -m venv .venv && source .venv/bin/activate
pip install -r physics/requirements.txt
(cd physics && pytest)                         # ~70 s with the HITRAN data present; data-dependent tests skip otherwise
python build/build_all.py                      # forcing tables + validation report

# Spectra (optional; needs HITRAN data, see data/MANIFEST.md)
python build/fetch_hitran.py                   # line lists via HAPI
#   + download the HITRAN .xsc cross-section files by hand into data/raw/hitran_xsec/<MOLECULE>/
python build/build_spectra.py                  # ~30 min
python build/halocarbon_check.py && python build/cloud_sensitivity.py

# Web app
cd web && npm ci && npm run dev                # http://localhost:5173
```

Students who only want to explore can skip the Python steps, since the repo ships the prebuilt tables.

**Deployment:** push to GitHub and import the repository into Vercel with root directory `web/`, build command `npm run build`, output directory `dist`. No server-side code is required, so the same build can later be copied to an IIT Delhi web server.

**Note on the parent repository:** the parent repo's `.gitignore` ignores `data/`, `build/` and `*.csv`; this project's own `.gitignore` re-includes the needed files and still ignores the raw HITRAN data and the cache.

---

## 9. Data and licensing

- All datasets are listed in `data/MANIFEST.md` with source, version, licence and retrieval date: IPCC AR6 forcing time series and concentrations (C. Smith et al., MIT), HITRAN lines and cross-sections (not redistributed), MT_CKD 4.3 (AER licence: research use, keep the copyright notice), CERES EBAF Ed4.0 values read from Loeb et al. (2018).
- Check each licence before redistributing derived tables publicly; HITRAN requires citation of Gordon et al. (2022) and Kochanov et al. (2016).
- Code licence: to be chosen (suggest MIT for code and CC BY 4.0 for lesson content). Note the AER MT_CKD licence forbids incorporating its data into commercial software.

---

## 10. Key references

- IPCC AR6 WG1, Chapter 7 (Earth's energy budget, climate feedbacks and climate sensitivity) and Chapter 6 (SLCFs).
- Meinshausen et al. (2020), *The shared socio-economic pathway (SSP) greenhouse gas concentrations and their extensions to 2500*, GMD.
- Etminan et al. (2016), *Radiative forcing of CO₂, CH₄, and N₂O: a significant revision of the methane radiative forcing*, GRL.
- Myhre et al. (1998), *New estimates of radiative forcing due to well mixed greenhouse gases*, GRL.
- Smith et al. (2018) and Leach et al. (2021), FaIR v1.3 / v2.0, GMD.
- Geoffroy et al. (2013), *Transient climate response in a two-layer energy-balance model*, J. Climate.
- Gordon et al. (2022), *The HITRAN2020 molecular spectroscopic database*, JQSRT 277, 107949; Kochanov et al. (2016), HAPI, JQSRT 177, 15.
- Mlawer et al. (2012), *Development and recent evaluation of the MT_CKD model of continuum absorption*, Phil. Trans. R. Soc. A 370, 2520.
- Loeb et al. (2018), *CERES EBAF Ed4.0 TOA data product*, J. Climate 31, 895–918.
- Manabe & Wetherald (1967), *Thermal equilibrium of the atmosphere with a given distribution of relative humidity*, J. Atmos. Sci.
- Kiehl & Trenberth (1997) and Wild et al. (2013/2015) on the global energy budget.
- Forster et al., annual *Indicators of Global Climate Change*, ESSD.

(Verify each citation's volume, pages and DOI when adding it to `content/`.)
# Climate-Radiative-Forcing-Lab
