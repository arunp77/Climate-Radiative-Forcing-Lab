declare module "plotly.js-basic-dist-min" {
  const Plotly: { react: (el: string, data: unknown[], layout?: unknown, config?: unknown) => Promise<unknown> };
  export default Plotly;
}
