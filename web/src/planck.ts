/** Planck emission per unit wavenumber; port of radforce.spectra.planck (cross-checked in tests/planck.test.ts). */
const H = 6.62607015e-34, C = 299792458.0, KB = 1.380649e-23;

/** Spectral radiance, W m-2 sr-1 (cm-1)-1, wavenumber in cm-1. */
export function radiance(nuCm: number, T: number): number {
  if (nuCm <= 0) return 0;
  const nuM = nuCm * 100;
  const x = (H * C * nuM) / (KB * T);
  return ((2 * H * C * C * nuM ** 3) / Math.expm1(x)) * 100;
}

/** Hemispheric flux pi*B, W m-2 (cm-1)-1. */
export const flux = (nuCm: number, T: number) => Math.PI * radiance(nuCm, T);

export const wavelengthUm = (nuCm: number) => 1e4 / nuCm;
