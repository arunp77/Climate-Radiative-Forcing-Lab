"""Physical and assessment constants with their sources.

Every number here carries a citation.  Do not add a constant without one.
"""
from __future__ import annotations

# --- Pre-industrial (1750) reference concentrations -------------------------
# IPCC AR6 WG1 Annex III / Dataset: LLGHG_history_AR6_v9 (Meinshausen et al. 2017
# updated by J. Ahn).  Units: CO2 in ppm, CH4 and N2O in ppb.
PREINDUSTRIAL_1750 = {"CO2": 278.3, "CH4": 729.2, "N2O": 270.1}

# --- Rapid (tropospheric) adjustments: ERF = SARF x factor ------------------
# IPCC AR6 WG1 Section 7.3.2: tropospheric adjustments of +5 % (CO2), -14 % (CH4)
# and +7 % (N2O) applied to the stratospheric-temperature-adjusted forcing
# computed from the Etminan/Meinshausen expressions.  Verified in
# tests/test_wmghg.py by reproducing the AR6 1750-2019 ERF series.
ERF_FROM_SARF = {"CO2": 1.05, "CH4": 0.86, "N2O": 1.07}

# --- Meinshausen et al. (2020, GMD 13, 3571) coefficients -------------------
# A re-fit of Etminan et al. (2016) that stays well behaved outside the range
# of validity.  Symbols follow the paper's Table 3 / AR6 Supplement 7.SM.1.3.1.
MEINSHAUSEN2020 = dict(
    a1=-2.4785e-07, b1=0.00075906, c1=-0.0021492, d1=5.2488,   # CO2
    a2=-0.00034197, b2=0.00025455, c2=-0.00024357, d2=0.12173,  # N2O
    a3=-8.9603e-05, b3=-0.00012462, d3=0.045194,                # CH4
)

# --- Etminan et al. (2016, GRL 43, 12614) coefficients ----------------------
ETMINAN2016 = dict(
    a1=-2.4e-7, b1=7.2e-4, c1=-2.1e-4, d1=5.36,   # CO2
    a2=-8.0e-6, b2=4.2e-6, c2=-4.9e-6, d2=0.117,  # N2O
    a3=-1.3e-6, b3=-8.2e-6, d3=0.043,             # CH4
)

# --- Myhre et al. (1998, GRL 25, 2715) / IPCC TAR ---------------------------
MYHRE1998 = dict(
    alpha_co2=5.35, alpha_ch4=0.036, alpha_n2o=0.12, alpha_overlap=0.47,
    a1=2.01e-5, exp1=0.75, a2=5.31e-15, exp2=1.52,
)

# --- Equivalent effective stratospheric chlorine (EESC) ----------------------
# Cl and Br atom counts and fractional release factors, as used for the AR6 ozone
# emulator (AR6 repo src/ar6/constants/gases.py; Daniel & Velders 2011, WMO Ozone
# Assessment; Newman et al. 2007, ACP 7, 4537).  Keys are AR6-repo species names.
# A species with fractional release 0 has no literature value and contributes nothing.
EESC_BR_FACTOR = 45  # Br is 45x more effective than Cl per atom (WMO 2011)
EESC_CL_ATOMS = {
    'CCl4': 4,
    'CFC11': 3,
    'CFC113': 3,
    'CFC114': 2,
    'CFC115': 1,
    'CFC12': 2,
    'CH2Cl2': 2,
    'CH3Br': 0,
    'CH3CCl3': 3,
    'CH3Cl': 1,
    'CHCl3': 3,
    'HCFC141b': 2,
    'HCFC142b': 1,
    'HCFC22': 1,
    'Halon1211': 0,
    'Halon1301': 0,
    'Halon2402': 0,
}
EESC_BR_ATOMS = {
    'CCl4': 0,
    'CFC11': 0,
    'CFC113': 0,
    'CFC114': 0,
    'CFC115': 0,
    'CFC12': 0,
    'CH2Cl2': 0,
    'CH3Br': 1,
    'CH3CCl3': 0,
    'CH3Cl': 0,
    'CHCl3': 0,
    'HCFC141b': 0,
    'HCFC142b': 0,
    'HCFC22': 0,
    'Halon1211': 1,
    'Halon1301': 1,
    'Halon2402': 2,
}
EESC_FRACREL = {
    'CCl4': 0.56,
    'CFC11': 0.47,
    'CFC113': 0.29,
    'CFC114': 0.12,
    'CFC115': 0.04,
    'CFC12': 0.23,
    'CH2Cl2': 0,
    'CH3Br': 0.6,
    'CH3CCl3': 0.67,
    'CH3Cl': 0.44,
    'CHCl3': 0,
    'HCFC141b': 0.34,
    'HCFC142b': 0.17,
    'HCFC22': 0.13,
    'Halon1211': 0.62,
    'Halon1301': 0.28,
    'Halon2402': 0.65,
}

# concentration-file column -> EESC species key
EESC_SPECIES = {
    'CFC-11': 'CFC11',
    'CFC-113': 'CFC113',
    'CFC-114': 'CFC114',
    'CFC-115': 'CFC115',
    'CFC-12': 'CFC12',
    'HCFC-141b': 'HCFC141b',
    'HCFC-142b': 'HCFC142b',
    'HCFC-22': 'HCFC22',
    'Halon-1211': 'Halon1211',
    'Halon-1301': 'Halon1301',
    'Halon-2402': 'Halon2402',
    'CCl4': 'CCl4',
    'CH2Cl2': 'CH2Cl2',
    'CH3Br': 'CH3Br',
    'CH3CCl3': 'CH3CCl3',
    'CH3Cl': 'CH3Cl',
    'CHCl3': 'CHCl3',
}

# --- Aerosol-cloud interaction shape factors ---------------------------------
# ERFaci ~ -ln(1 + SO2/n0 + (BC+OC)/n1)  (generalised Stevens 2015 / Ghan 2013 form used in
# AR6).  n0, n1 in Mt/yr.  The 12 CMIP6 models give shape factors that differ by orders of
# magnitude, and the AR6 median came from a 100,000-member ensemble that is not public, so
# these two numbers are a LEAST-SQUARES FIT of the form to the AR6 median ERFaci series
# 1750-2019 (max |error| 0.008 W m-2).  They are an emulator parameterisation, not an
# independent physical measurement.  tests/test_nonghg.py re-derives them.
ACI_N0_SO2 = 219.7335
ACI_N1_BCOC = 91.7674
