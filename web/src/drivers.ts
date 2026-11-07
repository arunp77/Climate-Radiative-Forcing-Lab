/** Slider definitions for the non-GHG drivers (all expressed as % of the 2019 value). */
export interface Driver { key: string; label: string; state: string[]; info: string }
export interface Group { title: string; drivers: Driver[] }

export const GROUPS: Group[] = [
  { title: "Aerosol precursors", drivers: [
    { key: "so2", label: "SO₂ emissions", state: ["so2"],
      info: "Sulphur dioxide forms sulphate particles that scatter sunlight and brighten clouds: the main aerosol cooling. Global emissions peaked around 2005–2010 and have since fallen; cutting them further removes cooling (an air-quality benefit with a warming side effect)." },
    { key: "bc", label: "Black carbon (soot)", state: ["bc"],
      info: "Soot absorbs sunlight, warming the air (aerosol–radiation term, positive), and darkens snow and ice when deposited (black-carbon-on-snow term, also positive)." },
    { key: "oc", label: "Organic carbon", state: ["oc"],
      info: "Mostly scattering particles from burning of fuels and biomass; net cooling, with some co-emitted absorbing components." },
    { key: "nh3", label: "Ammonia (nitrate proxy)", state: ["nh3"],
      info: "Ammonia from agriculture neutralises acids to form ammonium nitrate and sulphate particles. AR6 uses NH₃ emissions as the proxy for nitrate-aerosol cooling." },
  ]},
  { title: "Ozone precursors and ozone-depleting substances", drivers: [
    { key: "nox", label: "Nitrogen oxides (NOx)", state: ["nox"],
      info: "NOx drives tropospheric ozone formation, a warming agent. NOx also shortens methane's lifetime (cooling); that indirect effect is not in this slider: change the CH₄ concentration to explore it." },
    { key: "co", label: "Carbon monoxide (CO)", state: ["co"],
      info: "CO consumes the OH radical and promotes ozone formation, so it adds warming indirectly." },
    { key: "voc", label: "Volatile organic compounds", state: ["voc"],
      info: "Non-methane VOCs react to form tropospheric ozone and lengthen methane's lifetime; both add warming." },
    { key: "ods", label: "Ozone-depleting substances (EESC)", state: ["ods"],
      info: "Chlorine and bromine compounds destroy ozone and so reduce ozone forcing: in this emulator (AR6 authors' fit to the Skeie et al. models) about −0.1 W m⁻² at 2019. 100 % is the 2019 equivalent effective stratospheric chlorine above 1750. These gases are also greenhouse gases themselves; that effect is the halogenated-gases slider below, not this one." },
  ]},
  { title: "Other agents (simple multipliers on AR6 values)", drivers: [
    { key: "halo", label: "Halogenated gases (CFCs, HFCs, ...)", state: ["halo"],
      info: "Straight multiplier on the AR6 forcing of all halogenated gases (about 0.41 W m⁻² in 2019). It stands in for phase-outs such as the Montreal Protocol and the Kigali amendment on HFCs; it is not a concentration model. The ozone-depleting-substances slider above changes only the ozone-destruction effect of these gases." },
    { key: "landuse", label: "Land-use albedo change", state: ["landuse"],
      info: "Deforestation and agriculture usually brighten the surface, a small cooling. This is a straight multiplier on the AR6 value, not a land-use model." },
    { key: "contrails", label: "Aviation contrails", state: ["contrails"],
      info: "Contrails and induced cirrus scale with aviation activity. This is a straight multiplier on the AR6 value." },
  ]},
];

export const ALL_DRIVERS = GROUPS.flatMap((g) => g.drivers);
