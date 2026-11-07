import katex from "katex";
import "katex/dist/katex.min.css";
import { PI, type Scheme } from "./forcing";

/** LaTeX for each forcing scheme.  Coefficients live in physics/radforce/constants.py. */
const TEX: Record<Scheme, { title: string; lines: string[]; note: string }> = {
  myhre1998: {
    title: "Myhre et al. (1998), IPCC TAR / AR4",
    lines: [
      String.raw`\Delta F_{\mathrm{CO_2}} = 5.35\,\ln\!\left(\frac{C}{C_0}\right)`,
      String.raw`\Delta F_{\mathrm{CH_4}} = 0.036\left(\sqrt{M}-\sqrt{M_0}\right) - \left[f(M,N_0)-f(M_0,N_0)\right]`,
      String.raw`\Delta F_{\mathrm{N_2O}} = 0.12\left(\sqrt{N}-\sqrt{N_0}\right) - \left[f(M_0,N)-f(M_0,N_0)\right]`,
      String.raw`f(M,N) = 0.47\,\ln\!\left[1 + 2.01\!\times\!10^{-5}(MN)^{0.75} + 5.31\!\times\!10^{-15}\,M\,(MN)^{1.52}\right]`,
    ],
    note: "M, N in ppb. f is the CH₄–N₂O band-overlap correction. No ERF adjustment factors exist for this fit.",
  },
  etminan2016: {
    title: "Etminan et al. (2016), IPCC AR5-era update",
    lines: [
      String.raw`\Delta F_{\mathrm{CO_2}} = \left[a_1 (C-C_0)^2 + b_1 |C-C_0| + c_1 \bar N + d_1\right]\ln\!\left(\frac{C}{C_0}\right)`,
      String.raw`\Delta F_{\mathrm{CH_4}} = \left[a_3 \bar M + b_3 \bar N + d_3\right]\left(\sqrt{M}-\sqrt{M_0}\right)`,
      String.raw`\Delta F_{\mathrm{N_2O}} = \left[a_2 \bar C + b_2 \bar N + c_2 \bar M + d_2\right]\left(\sqrt{N}-\sqrt{N_0}\right)`,
      String.raw`\mathrm{ERF} = \mathrm{SARF}\times\{1.05,\;0.86,\;1.07\}`,
    ],
    note: "Bars denote the mean of the present and 1750 values. Valid for 180–2000 ppm CO₂, 340–3500 ppb CH₄, 200–525 ppb N₂O. SARF = stratospherically adjusted forcing.",
  },
  meinshausen2020: {
    title: "Meinshausen et al. (2020), IPCC AR6",
    lines: [
      String.raw`\Delta F_{\mathrm{CO_2}} = \left[\alpha'(C) + c_1\sqrt{N}\right]\ln\!\left(\frac{C}{C_0}\right)`,
      String.raw`\alpha'(C) = d_1 + a_1 (C-C_0)^2 + b_1 (C-C_0)\quad\text{up to its maximum (at } C-C_0=-b_1/2a_1\text{), constant beyond}`,
      String.raw`\Delta F_{\mathrm{CH_4}} = \left[a_3\sqrt{M} + b_3\sqrt{N} + d_3\right]\left(\sqrt{M}-\sqrt{M_0}\right)`,
      String.raw`\Delta F_{\mathrm{N_2O}} = \left[a_2\sqrt{C} + b_2\sqrt{N} + c_2\sqrt{M} + d_2\right]\left(\sqrt{N}-\sqrt{N_0}\right)`,
      String.raw`\mathrm{ERF} = \mathrm{SARF}\times\{\mathrm{CO_2}\!:1.05,\;\mathrm{CH_4}\!:0.86,\;\mathrm{N_2O}\!:1.07\}`,
    ],
    note: "A re-fit of Etminan et al. that stays well behaved outside its range of validity. Doubling CO₂ gives ERF ≈ 3.93 W m⁻² (AR6 Sect. 7.3.2).",
  },
};

const tex = (t: string, display = true) => katex.renderToString(t, { displayMode: display, throwOnError: false, output: "htmlAndMathml" });

export function renderEquations(el: HTMLElement, s: Scheme): void {
  const e = TEX[s];
  const base = String.raw`C_0=${PI.CO2}\,\mathrm{ppm},\; M_0=${PI.CH4}\,\mathrm{ppb},\; N_0=${PI.N2O}\,\mathrm{ppb}\quad(1750)`;
  el.innerHTML =
    `<p><strong>${e.title}</strong></p>` +
    `<p class="note">${tex(base, false)}; ΔF in W m⁻².</p>` +
    e.lines.map((l) => `<div class="eq">${tex(l)}</div>`).join("") +
    `<p class="note">${e.note}</p>`;
}

/** Equilibrium-warming relation shown next to the KPI. */
export const EQ_LAMBDA = String.raw`\Delta T_{\mathrm{eq}} = \frac{\mathrm{ERF}}{\lambda},\qquad \lambda = \frac{F_{2\times}}{\mathrm{ECS}} = \frac{3.93}{3}\approx 1.31\ \mathrm{W\,m^{-2}\,K^{-1}}`;
export const renderTex = tex;

/** Non-GHG emulators (physics/radforce/forcing/nonghg.py). Each is normalised so 2019 drivers give the AR6 2019 value. */
export const NONGHG_TEX: string[] = [
  String.raw`\mathrm{ERF}_x = \mathrm{ERF}_x^{\mathrm{AR6},\,2019}\;\frac{R_x(\text{drivers})}{R_x(\text{2019 drivers})}\qquad R_x(1750)=0`,
  String.raw`R_{\mathrm{ari}} = \sum_{i\in\{\mathrm{SO_2,BC,OC,NH_3}\}} \beta_i\,(E_i - E_{i,1750})\quad(\text{linear; }\beta_i\text{ set by AR6's assessed 2005–14 contributions})`,
  String.raw`R_{\mathrm{aci}} = -\left[\ln\!\left(1+\frac{E_{\mathrm{SO_2}}}{n_0}+\frac{E_{\mathrm{BC}}+E_{\mathrm{OC}}}{n_1}\right) - (\text{same at 1750})\right]\quad(\text{saturating})`,
  String.raw`R_{\mathrm{BC\,snow}} \propto E_{\mathrm{BC}}-E_{\mathrm{BC},1750},\qquad \mathrm{ERF}_{\mathrm{H_2O,strat}} \propto \mathrm{ERF}_{\mathrm{CH_4}}`,
  String.raw`R_{\mathrm{O_3}} = r_{\mathrm{CH_4}}\Delta[\mathrm{CH_4}] + r_{\mathrm{N_2O}}\Delta[\mathrm{N_2O}] + r_{\mathrm{ODS}}\Delta\mathrm{EESC} + r_{\mathrm{CO}}\Delta E_{\mathrm{CO}} + r_{\mathrm{VOC}}\Delta E_{\mathrm{VOC}} + r_{\mathrm{NO_x}}\Delta E_{\mathrm{NO_x}}`,
];
export const NONGHG_NOTE = "n₀ and n₁ are a least-squares fit to the AR6 median aerosol–cloud series (the 12 CMIP6 models disagree widely); ozone coefficients are the AR6 authors' fit to the Skeie et al. (2020) models. Accuracy against the AR6 series is listed in docs/validation.md (ozone ≤ 0.08, black carbon on snow ≤ 0.013, aerosol–cloud ≤ 0.008 W m⁻²). Land use, contrails and halogenated gases are plain multipliers.";
