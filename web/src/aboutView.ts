const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

const DOCS: { id: string; title: string; blurb: string }[] = [
  { id: "about", title: "About this site", blurb: "What each tab teaches, how far to trust it, licence" },
  { id: "validation", title: "Validation report", blurb: "Every check against a published value" },
  { id: "cloud_sensitivity", title: "Cloud-model sensitivity", blurb: "How much the cloud assumption matters" },
  { id: "halocarbon_check", title: "Halocarbon check", blurb: "17 radiative efficiencies against AR6" },
  { id: "references", title: "References", blurb: "Papers, datasets and DOIs" },
  { id: "hitran-data", title: "Getting the HITRAN data", blurb: "To rebuild the spectra yourself" },
];

export function initAbout(initial = "about") {
  const nav = $("ab-nav"), body = $("ab-body");
  const cache = new Map<string, string>();
  nav.innerHTML = DOCS.map((d) => `<button type="button" data-doc="${d.id}" aria-pressed="false"><strong>${d.title}</strong><span>${d.blurb}</span></button>`).join("");

  async function show(id: string) {
    nav.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String((b as HTMLButtonElement).dataset.doc === id)));
    body.setAttribute("aria-busy", "true");
    try {
      if (!cache.has(id)) {
        const r = await fetch(`./docs/${id}.html`);
        if (!r.ok) throw new Error(String(r.status));
        cache.set(id, await r.text());
      }
      body.innerHTML = cache.get(id)!;   // our own build output (build/build_docs.py), not user input
      body.querySelectorAll<HTMLAnchorElement>("a[href^='http']").forEach((a) => { a.target = "_blank"; a.rel = "noopener noreferrer"; });
      body.querySelectorAll("table").forEach((t) => { const w = document.createElement("div"); w.className = "tablewrap"; t.replaceWith(w); w.appendChild(t); });
    } catch (e) {
      body.textContent = `Could not load this document: ${String(e)}`;
    } finally {
      body.removeAttribute("aria-busy");
    }
  }
  nav.addEventListener("click", (e) => {
    const b = (e.target as HTMLElement).closest("button[data-doc]") as HTMLButtonElement | null;
    if (b) void show(b.dataset.doc!);
  });
  return show(initial);
}
