import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { TERMS } from "../src/glossary";

const html = readFileSync("index.html", "utf8");
const boxes = [...html.matchAll(/data-terms="([^"]*)"/g)].map((m) => m[1].replace(/&amp;/g, "&").replace(/&quot;/g, '"').split("|"));
const names = new Set(TERMS.map((t) => t.term));

describe("key-terms boxes", () => {
  it("there is one for every content tab", () => expect(boxes.length).toBe(5));
  it("every listed term is defined in the glossary", () => {
    for (const list of boxes) for (const n of list) expect(names.has(n), n).toBe(true);
  });
  it("no term is listed twice in a box", () => {
    for (const list of boxes) expect(new Set(list).size).toBe(list.length);
  });
});

describe("terms used in the interface text are defined somewhere on the site", () => {
  const visible = html.replace(/<[^>]+>/g, " ");
  const glossaryText = TERMS.map((t) => t.term + " " + t.def).join(" ");
  // abbreviations that appear in the page text and must therefore appear in the glossary
  const mustBeDefined = ["ERF", "ECS", "TCR", "SSP", "FaIR", "AR6", "OLR", "GWP", "GTP", "CFC", "HFC", "HCFC", "PFC", "HITRAN", "CERES", "RCMIP", "HadCRUT5", "NOₓ", "VOC", "SO₂", "NH₃"];
  it.each(mustBeDefined)("%s", (a) => {
    if (visible.includes(a)) expect(glossaryText.includes(a), a).toBe(true);
  });
});
