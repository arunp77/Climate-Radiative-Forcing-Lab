/** Display colours and short explanations for each forcing agent (one place, used by every view). */
export const COLOURS: Record<string, string> = {
  CO2: "#2b7bd0", CH4: "#e8871e", N2O: "#2e9e5b", Halogenated: "#8e6bbf", O3: "#c0566b",
  H2O_strat: "#7aa6c9", Contrails: "#9aa5b1", Aerosol_ari: "#4b5d73", Aerosol_aci: "#36485c",
  BC_snow: "#5a4a42", LandUse: "#b08a4f",
};

export const EXPLAIN: Record<string, string> = {
  CO2: "Long-lived and well mixed. Its absorption bands are saturated near line centres, so forcing grows roughly with the logarithm of concentration. By far the largest term.",
  CH4: "A potent but short-lived (about 12 years) gas. Forcing grows roughly as the square root of concentration; its band overlaps with N₂O and water vapour.",
  N2O: "Lifetime about 110 years. Bands at the edges of the 8–12 µm window; forcing grows roughly as the square root of concentration.",
  Halogenated: "CFCs, HCFCs, HFCs, PFCs, SF₆ and others. Present at parts-per-trillion levels but strong absorbers, many inside the 8–12 µm window, and far from saturated, so their forcing is linear in concentration. The Montreal Protocol ended the growth of CFCs.",
  O3: "Tropospheric ozone is a secondary pollutant formed from NOx, CO, VOCs and CH₄ and warms the climate. Stratospheric ozone depletion by chlorine and bromine gives a small cooling that is included in this total.",
  H2O_strat: "Methane oxidation in the stratosphere adds water vapour, a greenhouse gas there. Small and positive.",
  Contrails: "Contrails and the cirrus clouds they seed trap outgoing longwave radiation. Small, positive and highly uncertain.",
  Aerosol_ari: "Aerosol–radiation interactions: sulphate and other scattering particles cool by reflecting sunlight; black carbon absorbs and warms. Net cooling.",
  Aerosol_aci: "Aerosol–cloud interactions: more particles mean more, smaller cloud droplets and brighter clouds. The largest uncertainty in the whole forcing budget.",
  BC_snow: "Black carbon deposited on snow and ice darkens it, so it absorbs more sunlight and melts faster.",
  LandUse: "Deforestation and land-use change usually brighten the surface (forest to crop or grass), reflecting more sunlight. Small cooling.",
};

/** Short axis labels for narrow charts. */
export const SHORT: Record<string, string> = {
  CO2: "CO₂", CH4: "CH₄", N2O: "N₂O", Halogenated: "Halogenated gases", O3: "Ozone", H2O_strat: "Strat. water vapour",
  Contrails: "Contrails", Aerosol_ari: "Aerosol (radiation)", Aerosol_aci: "Aerosol (clouds)", BC_snow: "Soot on snow", LandUse: "Land use",
};
