"""Convert the Markdown documents in docs/ to HTML fragments in web/public/docs/ for the About tab.

Run from the repo root:  python build/build_docs.py   (needs the `markdown` package)
"""
from __future__ import annotations

from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs"
OUT = ROOT / "web/public/docs"
DOCS = ["about", "validation", "cloud_sensitivity", "halocarbon_check", "references", "hitran-data"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name in DOCS:
        text = (SRC / f"{name}.md").read_text()
        html = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
        (OUT / f"{name}.html").write_text(html)
        print(f"{name}: {len(html)/1e3:.0f} kB")


if __name__ == "__main__":
    main()
