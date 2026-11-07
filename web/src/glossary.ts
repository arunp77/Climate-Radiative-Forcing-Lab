// Plain-language definitions used by the Glossary tab. Each entry is checked against the sources named in the
// footer (IPCC AR6 WG1 glossary and chapters 6-7, the Montreal Protocol texts, HITRAN documentation).

export type Category = "Gas families" | "Light and spectra" | "Forcing" | "Warming" | "Metrics" | "Scenarios and models" | "Policy" | "Units";

export interface Term { term: string; cat: Category; def: string }

export const CATEGORIES: Category[] = ["Gas families", "Light and spectra", "Forcing", "Warming", "Metrics", "Scenarios and models", "Policy", "Units"];

export const TERMS: Term[] = [
  // ---- gas families
  { term: "Greenhouse gas", cat: "Gas families", def: "A gas that absorbs infrared radiation emitted by the surface and atmosphere and re-emits it in all directions, so less heat escapes to space. Water vapour, CO₂, CH₄, N₂O and ozone are natural examples; halocarbons are almost entirely man-made." },
  { term: "WMGHG (well-mixed greenhouse gases)", cat: "Gas families", def: "Gases that live long enough to spread evenly around the globe: CO₂, CH₄, N₂O and the halogenated gases. Their forcing is calculated from a single global-mean concentration." },
  { term: "Halocarbon / halogenated gas", cat: "Gas families", def: "A carbon compound that contains fluorine, chlorine, bromine or iodine. The families below are all halocarbons (SF₆ and NF₃ are halogenated but contain no carbon)." },
  { term: "CFC (chlorofluorocarbon)", cat: "Gas families", def: "Contains chlorine, fluorine and carbon only (for example CFC-11, CCl₃F; CFC-12, CCl₂F₂). Used as refrigerants, foam-blowing agents, solvents and spray propellants. They destroy stratospheric ozone and are strong, long-lived greenhouse gases. Production was phased out under the Montreal Protocol." },
  { term: "HCFC (hydrochlorofluorocarbon)", cat: "Gas families", def: "Like a CFC but with some hydrogen, which lets the lower atmosphere break it down faster, so lifetimes are shorter and the ozone damage is smaller (for example HCFC-22, CHClF₂). Introduced as interim CFC replacements; being phased out under the Montreal Protocol." },
  { term: "HFC (hydrofluorocarbon)", cat: "Gas families", def: "Contains hydrogen, fluorine and carbon, with no chlorine, so it does not harm the ozone layer (for example HFC-134a, CH₂FCF₃). Widely used in air conditioning and refrigeration. Many are strong greenhouse gases, which is why the Kigali Amendment phases them down." },
  { term: "PFC (perfluorocarbon)", cat: "Gas families", def: "Carbon and fluorine only (for example CF₄, C₂F₆, C₃F₈). Extremely stable, with lifetimes of thousands of years. Sources include aluminium smelting and semiconductor manufacturing." },
  { term: "SF₆ (sulphur hexafluoride)", cat: "Gas families", def: "A very stable, very strong greenhouse gas used as an electrical insulator in high-voltage switchgear. Lifetime about 3 200 years in the AR6 table, with a very large radiative efficiency per molecule." },
  { term: "NF₃ (nitrogen trifluoride)", cat: "Gas families", def: "A strong, long-lived greenhouse gas used in semiconductor and flat-panel manufacturing. Not on the Spectra tab, but part of the AR6 halogenated-gas total." },
  { term: "Halon", cat: "Gas families", def: "A bromine-containing compound used in fire extinguishers (for example Halon-1301, CF₃Br). Halons destroy ozone far more per molecule than CFCs. Controlled by the Montreal Protocol." },
  { term: "HFO (hydrofluoroolefin)", cat: "Gas families", def: "A short-lived HFC-like gas with a carbon–carbon double bond that breaks down within days to weeks, so its greenhouse effect is small. Used as a low-warming replacement for HFCs." },
  { term: "ODS (ozone-depleting substance)", cat: "Gas families", def: "Any gas that destroys stratospheric ozone, mainly CFCs, HCFCs, halons, carbon tetrachloride and methyl chloroform. Their abundance is summarised by EESC." },
  { term: "EESC (equivalent effective stratospheric chlorine)", cat: "Gas families", def: "A measure of how much ozone-destroying chlorine and bromine reaches the stratosphere, weighted by how fast each source gas breaks down and how much more damaging bromine is than chlorine. The forcing of stratospheric ozone is scaled to it." },
  { term: "SLCF (short-lived climate forcer)", cat: "Gas families", def: "A substance that stays in the atmosphere for days to about a decade, so its effect depends on where it is emitted: aerosols, black carbon, ozone and its precursors, and methane (the longest-lived of the group)." },
  { term: "Aerosol", cat: "Gas families", def: "Tiny solid or liquid particles suspended in air, such as sulphate, black carbon and organic carbon. Most reflect sunlight and cool the planet; black carbon absorbs it." },
  { term: "Ozone (O₃)", cat: "Gas families", def: "A greenhouse gas. Near the ground it is a pollutant formed from NOₓ, CO, CH₄ and volatile organic compounds, and warms the climate. In the stratosphere it absorbs ultraviolet light; its depletion produces a small cooling." },

  // ---- naming
  { term: "Rule of 90 (naming CFCs, HCFCs and HFCs)", cat: "Gas families", def: "Add 90 to the number after the hyphen. The three digits are then the number of carbon, hydrogen and fluorine atoms; every remaining bond on the carbons holds chlorine. Examples: CFC-11 → 101 → 1 C, 0 H, 1 F, so CCl₃F. CFC-12 → 102 → CCl₂F₂. CFC-113 → 203 → 2 C, 0 H, 3 F → C₂Cl₃F₃. HCFC-22 → 112 → CHClF₂. HFC-134a → 224 → C₂H₂F₄. A letter (a, b, c) marks a different arrangement of the same atoms (an isomer). If only two digits are given, the missing leading digit is 0 (a single carbon atom)." },
  { term: "PFC numbering", cat: "Gas families", def: "PFC-14 is CF₄, PFC-116 is C₂F₆ and PFC-218 is C₃F₈. The same rule of 90 works for them: 14 + 90 = 104 → 1 C, 0 H, 4 F." },
  { term: "Halon numbering", cat: "Gas families", def: "Four digits: the number of carbon, fluorine, chlorine and bromine atoms in that order. Halon-1301 is CF₃Br (1 C, 3 F, 0 Cl, 1 Br); Halon-1211 is CF₂ClBr." },
  { term: "Refrigerant numbers (R-12, R-134a, …)", cat: "Gas families", def: "Trade names for the same gases: R-12 is CFC-12, R-22 is HCFC-22, R-134a is HFC-134a. Numbers in the 400 and 500 series, such as R-410A or R-404A, are blends of several gases." },

  // ---- light and spectra
  { term: "Wavenumber (cm⁻¹)", cat: "Light and spectra", def: "The number of wave crests per centimetre, 1 divided by the wavelength in cm. Spectroscopists use it because it is proportional to photon energy. 10 µm = 1000 cm⁻¹; 15 µm = 667 cm⁻¹." },
  { term: "Wavelength (µm)", cat: "Light and spectra", def: "Distance between wave crests. The Earth's thermal infrared lies roughly between 4 and 50 µm (about 200–2500 cm⁻¹)." },
  { term: "Infrared (thermal) radiation", cat: "Light and spectra", def: "Radiation at wavelengths longer than visible light that every warm object emits. The Earth loses energy to space mainly in this range; greenhouse gases absorb part of it." },
  { term: "Blackbody and the Planck function", cat: "Light and spectra", def: "A blackbody absorbs all radiation that hits it and emits the maximum possible at its temperature. The Planck function gives the emitted power at each wavelength; hotter bodies emit more and at shorter wavelengths. The dashed curves on the Spectra tab are blackbodies at 288 K and 220 K." },
  { term: "OLR (outgoing longwave radiation)", cat: "Light and spectra", def: "The thermal infrared energy leaving the top of the atmosphere, in W m⁻². The global-mean value is about 240 W m⁻² (CERES), balancing absorbed sunlight." },
  { term: "Atmospheric window", cat: "Light and spectra", def: "The range of about 8 to 12.5 µm (800–1250 cm⁻¹) where clean, dry air is almost transparent, so surface radiation escapes to space. Halocarbons, SF₆ and ozone absorb in it, which is why small amounts matter." },
  { term: "Absorption band and line", cat: "Light and spectra", def: "A molecule absorbs only at specific wavelengths where its vibrations and rotations can take up a photon. Each tiny feature is a line; a group of lines is a band, for example the CO₂ bend near 15 µm (667 cm⁻¹)." },
  { term: "Cross-section σ (cm² per molecule)", cat: "Light and spectra", def: "The effective area one molecule presents to radiation of a given wavenumber. Heavy molecules such as CFCs have so many overlapping lines that measured cross-sections are given instead of line lists." },
  { term: "Column (molecules cm⁻²)", cat: "Light and spectra", def: "The number of absorber molecules along the light's path, per square centimetre. Optical depth = σ × column." },
  { term: "Optical depth (τ) and transmission", cat: "Light and spectra", def: "τ measures how opaque a layer is. The fraction of light that passes through is e^−τ, so τ = 1 lets 37 % through and τ = 3 lets 5 % through." },
  { term: "Line broadening (Doppler, pressure, Voigt)", cat: "Light and spectra", def: "Lines are not infinitely sharp. Molecular motion widens them (Doppler) and collisions with other molecules widen them more at high pressure (Lorentz). The combined shape is the Voigt profile." },
  { term: "Saturation and the curve of growth", cat: "Light and spectra", def: "Once the centre of a band absorbs all the light, more gas only widens the band edges, so extra absorption slows down. That is why CO₂ forcing rises with the logarithm of concentration, CH₄ and N₂O with roughly the square root, and rare halocarbons almost linearly." },
  { term: "Water-vapour continuum", cat: "Light and spectra", def: "A slowly varying absorption by water vapour between its lines, strongest in the window. This site uses the MT_CKD 4.3 model for it." },
  { term: "Schwarzschild equation", cat: "Light and spectra", def: "The equation for radiation passing through an absorbing and emitting gas: each layer takes some radiation away and adds its own emission at its own temperature. Solved layer by layer, it gives the outgoing spectrum." },
  { term: "Clear sky and all sky", cat: "Light and spectra", def: "Clear-sky results ignore clouds. All-sky results include them; here as one grey cloud deck tuned to the observed longwave cloud effect." },
  { term: "Cloud radiative effect (CRE)", cat: "Light and spectra", def: "All-sky minus clear-sky net radiation. In the longwave, clouds trap heat: the observed global mean is about 27.9 W m⁻² (CERES EBAF)." },
  { term: "Tropopause and lapse rate", cat: "Light and spectra", def: "Temperature falls with height in the troposphere (the lapse rate, about 6.5 K per km) until the tropopause at about 11 km, then rises in the stratosphere. Most outgoing radiation comes from the cold upper troposphere." },
  { term: "Standard atmosphere", cat: "Light and spectra", def: "A fixed, idealised profile of temperature and pressure with height. This site uses the U.S. Standard Atmosphere 1976 with an idealised water-vapour profile." },
  { term: "HITRAN", cat: "Light and spectra", def: "The international database of molecular absorption lines and cross-sections that the spectra here are built from (Gordon et al. 2022). Free for research and teaching; the raw data is not redistributed." },

  // ---- forcing
  { term: "Radiative forcing (RF)", cat: "Forcing", def: "The change in the energy balance of the Earth, in W m⁻², caused by a change in a driver such as CO₂, relative to a reference year (here 1750). Positive values warm." },
  { term: "Instantaneous radiative forcing (IRF)", cat: "Forcing", def: "The change in net flux the moment a driver changes, before anything in the atmosphere responds. The Spectra tab computes this at the top of the atmosphere." },
  { term: "Stratospheric adjustment", cat: "Forcing", def: "When CO₂ rises, the stratosphere cools within months and so emits less radiation to space. That makes the top-of-atmosphere forcing grow, by more than 1 W m⁻² for doubled CO₂, from its instantaneous value to the stratosphere-adjusted value (SARF). The Spectra tab shows the instantaneous value, which is why it is smaller than AR6's." },
  { term: "Tropospheric rapid adjustments", cat: "Forcing", def: "Changes in clouds, water vapour, temperature profile and land surface that follow within weeks to months and are not caused by global-mean surface warming. AR6 scales CO₂ by +5 %, CH₄ by −14 % and N₂O by +7 % to include them." },
  { term: "Effective radiative forcing (ERF)", cat: "Forcing", def: "The forcing after all rapid adjustments, with ocean temperatures held fixed. It is the best predictor of eventual global warming and the quantity IPCC AR6 reports. ERF for doubled CO₂ is 3.93 W m⁻²." },
  { term: "Radiative efficiency (RE)", cat: "Forcing", def: "The forcing per unit increase in a gas's abundance, in W m⁻² ppb⁻¹. It is large for halocarbons because they absorb in the window and are present in tiny amounts." },
  { term: "Aerosol–radiation interactions (ERFari)", cat: "Forcing", def: "Aerosols scatter or absorb sunlight directly. Mostly a cooling." },
  { term: "Aerosol–cloud interactions (ERFaci)", cat: "Forcing", def: "Aerosols change cloud droplet number, size and lifetime, so clouds reflect more sunlight. The largest and most uncertain cooling term." },
  { term: "Black carbon on snow", cat: "Forcing", def: "Soot darkens snow and ice, so it absorbs more sunlight. A small warming." },
  { term: "Albedo and land-use change", cat: "Forcing", def: "Albedo is the fraction of sunlight a surface reflects. Replacing forest with brighter cropland raises albedo and cools slightly." },
  { term: "Contrails and aviation cirrus", cat: "Forcing", def: "Ice clouds that form behind aircraft. They trap more heat than they reflect." },
  { term: "Natural forcing", cat: "Forcing", def: "Changes in solar output and the cooling after large volcanic eruptions. Not part of the man-made total." },
  { term: "Pre-industrial and the 1750 baseline", cat: "Forcing", def: "AR6 measures forcing against 1750. Warming is measured against 1850–1900 (the first period with thermometer records worldwide); the two baselines differ slightly." },

  // ---- warming
  { term: "Climate feedback parameter (λ)", cat: "Warming", def: "How much extra energy the Earth loses to space per kelvin of warming, in W m⁻² K⁻¹. A larger λ means less warming for the same forcing. Equilibrium warming = forcing ÷ λ." },
  { term: "ECS (equilibrium climate sensitivity)", cat: "Warming", def: "The long-term warming after CO₂ doubles and the whole climate system, including the deep ocean, has reached balance. AR6: best estimate 3 K, likely range 2.5–4 K." },
  { term: "TCR (transient climate response)", cat: "Warming", def: "The warming at the moment CO₂ has doubled when it rises 1 % per year (about year 70). Lower than ECS because the ocean is still taking up heat. AR6: best estimate 1.8 K, likely range 1.4–2.2 K." },
  { term: "Earth's energy imbalance (EEI)", cat: "Warming", def: "The small difference between absorbed sunlight and outgoing radiation, positive today. Nearly all of it goes into heating the oceans." },
  { term: "Ocean heat uptake", cat: "Warming", def: "The ocean absorbs most of the excess heat, delaying surface warming. Models represent it with a thin surface layer exchanging heat with a deeper one." },
  { term: "Two-layer (energy balance) model", cat: "Warming", def: "A simple climate model with a fast surface layer (air, land, upper ocean) and a slow deep ocean. It turns forcing into temperature in milliseconds, which is why the Warming tab can respond instantly to sliders." },
  { term: "Temperature anomaly", cat: "Warming", def: "A temperature expressed as a difference from a reference period, here 1850–1900, rather than as an absolute value." },
  { term: "GMST / GSAT", cat: "Warming", def: "Global mean surface temperature (blend of near-surface air over land and sea-surface temperature over ocean) and global surface air temperature. AR6 treats them as nearly equal over the historical period." },
  { term: "Committed warming", cat: "Warming", def: "Further warming that will occur even if forcing stops rising, because the climate has not yet reached balance." },

  // ---- metrics
  { term: "GWP (global warming potential)", cat: "Metrics", def: "The total forcing, added up over a time horizon (20, 100 or 500 years), caused by a 1 kg pulse of a gas, divided by that of 1 kg CO₂. GWP-100 of CH₄ is 27.9, of N₂O 273, of CFC-12 12 500." },
  { term: "GTP (global temperature change potential)", cat: "Metrics", def: "The temperature change at a chosen year (for example 50 or 100 years) after a 1 kg pulse of a gas, divided by that of 1 kg CO₂. It reflects the climate response rather than accumulated forcing." },
  { term: "AGWP and AGTP", cat: "Metrics", def: "The absolute versions, before dividing by CO₂: forcing integrated over time per kg (W m⁻² yr kg⁻¹) and temperature per kg (K kg⁻¹)." },
  { term: "CO₂-equivalent (CO₂e)", cat: "Metrics", def: "An amount of CO₂ that would have the same GWP-weighted effect as an emission of another gas. It depends on the metric and time horizon chosen." },
  { term: "Gas lifetime", cat: "Metrics", def: "The time for a pulse of a gas to fall to 1/e (37 %) of its initial amount. CH₄ is about 12 years, N₂O about 109 years, CFC-12 about 102 years, CF₄ about 50 000 years. CO₂ has no single lifetime." },
  { term: "Climate–carbon feedback", cat: "Metrics", def: "Warming reduces the land and ocean uptake of CO₂, so a pulse of any gas indirectly adds a little CO₂. AR6 metrics include it." },

  // ---- scenarios and models
  { term: "AR6", cat: "Scenarios and models", def: "The Sixth Assessment Report of the Intergovernmental Panel on Climate Change (2021–2023). Working Group I Chapter 7 is the source for the forcing numbers here." },
  { term: "SSP (Shared Socioeconomic Pathway)", cat: "Scenarios and models", def: "A story of how society and the economy might develop, paired with a forcing level. SSP2-4.5 is the middle-of-the-road pathway whose forcing reaches about 4.5 W m⁻² in 2100; SSP1-2.6 is a low-emissions pathway; SSP5-8.5 is a very-high-emissions one." },
  { term: "RCP (Representative Concentration Pathway)", cat: "Scenarios and models", def: "The earlier set of scenarios labelled only by 2100 forcing (2.6, 4.5, 6.0, 8.5 W m⁻²). SSP scenarios update them." },
  { term: "FaIR", cat: "Scenarios and models", def: "The Finite-amplitude Impulse Response model (Leach et al. 2021): a small, fast climate model that turns emissions into concentrations, forcing and temperature. The scenarios on the Warming tab are FaIR runs." },
  { term: "Reduced-complexity model", cat: "Scenarios and models", def: "A model simple enough to run in seconds and understand in detail, calibrated to reproduce the behaviour of large climate models. Good for teaching and scenario exploration; it does not simulate weather, regional climate or circulation." },
  { term: "Pulse and step emission", cat: "Scenarios and models", def: "A pulse is a one-off emission; a step is a sustained constant emission. GWP and GTP are defined for a pulse." },
  { term: "Instantaneous versus equilibrium", cat: "Scenarios and models", def: "Instantaneous values hold at the moment of change; equilibrium values hold after the system has fully adjusted. The “equilibrium warming” on the Forcing balance tab is the latter and is not today's observed warming." },

  // ---- policy
  { term: "Montreal Protocol", cat: "Policy", def: "The 1987 treaty that phased out CFCs, halons, carbon tetrachloride and other ozone-depleting substances, and is phasing out HCFCs. It is often called the most successful environmental treaty and avoided a large amount of warming as a side effect." },
  { term: "Kigali Amendment", cat: "Policy", def: "A 2016 addition to the Montreal Protocol that phases down the production and use of HFCs, starting in 2019, because they are strong greenhouse gases." },
  { term: "Kyoto Protocol and the Kyoto basket", cat: "Policy", def: "The 1997 climate treaty that limited a basket of gases: CO₂, CH₄, N₂O, HFCs, PFCs and SF₆ (NF₃ was added later). CFCs are excluded because the Montreal Protocol already covers them." },
  { term: "Paris Agreement", cat: "Policy", def: "The 2015 agreement to hold global warming well below 2 °C above pre-industrial levels and pursue 1.5 °C." },

  // ---- units
  { term: "W m⁻² (watts per square metre)", cat: "Units", def: "Power per unit area. Forcing, OLR and energy imbalance are all in these units. Global-mean absorbed sunlight is about 240 W m⁻²." },
  { term: "ppm, ppb, ppt", cat: "Units", def: "Parts per million, billion and trillion by number of molecules (mole fraction). CO₂ is about 420 ppm, CH₄ about 1 900 ppb, CFC-12 about 500 ppt." },
  { term: "Mt, Gt, kg", cat: "Units", def: "Megatonne = 10⁹ kg, gigatonne = 10¹² kg. Emissions are often given in Mt per year; CO₂ emissions in Gt per year." },
  { term: "K versus °C", cat: "Units", def: "A change of 1 K equals a change of 1 °C, so temperature differences and sensitivities can be quoted in either." },
];
