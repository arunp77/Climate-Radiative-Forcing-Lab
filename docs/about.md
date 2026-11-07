# About this site

**Climate Radiative Forcing Lab** is a free, open tool for learning how greenhouse gases, aerosols and clouds change the energy balance of the Earth. It runs entirely in your browser; there is no account, no tracking and nothing is sent anywhere.

## What is in it

| Tab | What it teaches | Where the numbers come from |
|---|---|---|
| Forcing balance | How much each agent (CO₂, CH₄, N₂O, halocarbons, ozone, aerosols and others) has changed the energy balance since 1750, and what happens when you change them | IPCC AR6 forcing expressions and time series |
| History | The same, year by year from 1850 | IPCC AR6 time series |
| Spectra | Why gases differ: the infrared absorption of 22 molecules, the spectrum leaving the Earth, saturation, clouds, and the steps from instantaneous to effective forcing | HITRAN2020 line lists and cross-sections, MT_CKD continuum, our own line-by-line and radiative-transfer code |
| Warming | How forcing turns into temperature in five scenarios, compared with thermometer records | FaIR v2 and a three-layer energy balance model; HadCRUT5; NOAA Mauna Loa |
| GWP and GTP | How emissions of different gases are compared, over 249 gases | IPCC AR6 method, recomputed |
| Glossary | Names (CFC-11, HFC-134a, …), terms and units | IPCC AR6 and the Montreal Protocol texts |

## How far to trust it

- Every number comes from a published source or a documented calculation, and the code is tested against the published values. The **Validation report** in this section lists every comparison, including where the model is off.
- Where something is **tuned** (the cloud opacity, to the observed longwave cloud effect), the page says what it was tuned to and what independent quantity tests it.
- It is a teaching model, not a research model. Reduced-complexity climate models, one idealised atmospheric profile and a single cloud deck are used on purpose, and the limits are stated next to each result.
- Scenarios are not predictions.

## Use, licence and citation

Free to use, copy and adapt for teaching and learning (Creative Commons Attribution-NonCommercial-ShareAlike 4.0). Spectral data are used under the HITRAN and AER terms (research and teaching use only); see the notice file in the repository for every dataset. To cite the tool, use the citation file in the repository, and cite the data sources listed under References.

## Source code and feedback

Code, data notes and build instructions: <https://github.com/arunp77/Climate-Radiative-Forcing-Lab>. Found an error or have a suggestion? Please open an issue there: <https://github.com/arunp77/Climate-Radiative-Forcing-Lab/issues>.
